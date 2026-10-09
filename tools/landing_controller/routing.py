"""Bounded local copper repair for this authored board, never a PASS override.

Prior copper is an untrusted proposal. Rebinding after a serializer correction
requires identical semantic pad geometry, circuit, board and routing rules.
Every candidate is independently checked; unresolved routes remain failures.
"""
from __future__ import annotations

import argparse
import hashlib
import math
from itertools import pairwise
from pathlib import Path
from time import monotonic

from ohmni.domain import EventKind
from ohmni.eda.pcb_models import PcbArtifact
from ohmni.physical.footprints import footprint
from ohmni.routing.models import (
    Point,
    RoutedNet,
    RoutePath,
    RoutingFailure,
    RoutingFailureReason,
    RoutingPlan,
    RoutingStatistics,
    TrackSegment,
    Via,
)
from ohmni.routing.router import DeterministicRouter, _event, _id, _RoutingInterrupted
from ohmni.routing.verifier import verify_routing

DISPLACED_NETS = ("SR_DATA", "GPIO_PC11", "GPIO_PD3", "GPIO_PD7", "GPIO_PD5",
                  "GPIO_PD2", "GPIO_PB7", "GPIO_PB9")
MINIMUM_NPTH_COPPER_CLEARANCE_MM = .25


def _geometry(pcb, board):
    router = DeterministicRouter
    centres = router._pad_centres(pcb, board)
    return (centres, router._terminal_keys(pcb), router._pad_obstacles(pcb, board, centres))


def npth_search_obstacles(pcb, board, profile, pads):
    """Reserve the native 0.25-mm NPTH clearance without changing source pads."""
    places = {place.component_ref: place for place in board.placements}
    holes = set()
    for binding in pcb.compilation.footprint_bindings:
        place = places[binding.component_ref]
        angle = math.radians(place.rotation_deg)
        for pad in footprint(binding.footprint_id).pads:
            if pad.kind == "np_thru_hole":
                holes.add((round(place.x_mm + pad.x_mm*math.cos(angle)-pad.y_mm*math.sin(angle), 6),
                           round(place.y_mm + pad.x_mm*math.sin(angle)+pad.y_mm*math.cos(angle), 6)))
    extra = max(0, MINIMUM_NPTH_COPPER_CLEARANCE_MM-float(profile.clearance_mm.value))
    return [(net, point, width+2*extra, height+2*extra, layers)
            if net is None and (point.x_mm, point.y_mm) in holes else (net, point, width, height, layers)
            for net, point, width, height, layers in pads]


def repair(circuit, pcb, board, constraints, proposal, prior_pcb, *,
           displaced_nets=DISPLACED_NETS, time_budget_seconds=240, escapes=None, retry_order=None):
    """Rip up selected nets, protect completed new routes, then replay displaced nets."""
    if (isinstance(time_budget_seconds, bool) or not math.isfinite(time_budget_seconds)
            or time_budget_seconds <= 0):
        raise ValueError("Repair requires a positive finite time budget")
    if (proposal.circuit_content_hash != circuit.content_hash
            or proposal.source_constraints_hash != board.content_hash
            or proposal.profile != constraints.profile
            or proposal.net_constraints != constraints.nets
            or proposal.source_pcb_fingerprint != prior_pcb.fingerprint.digest
            or any(item.circuit_content_hash != circuit.content_hash or item.constraints_hash != board.content_hash
                   for item in (prior_pcb, pcb))
            or not prior_pcb.is_current or not pcb.is_current):
        raise ValueError("Copper proposal has incompatible lineage or routing rules")
    if (prior_pcb.compilation.footprint_bindings != pcb.compilation.footprint_bindings
            or prior_pcb.compilation.pad_bindings != pcb.compilation.pad_bindings
            or _geometry(prior_pcb, board) != _geometry(pcb, board)):
        raise ValueError("Copper proposal semantic pad geometry differs from fresh PCB")
    prior_check = verify_routing(circuit, prior_pcb, board, proposal)
    if any(f.status.value == "fail" and f.rule_id not in {"PB-ROUTE-001", "PB-ROUTE-009"}
           for f in prior_check.findings):
        raise ValueError("Prior proposal has failures beyond incomplete connectivity")
    known = {net.name for net in circuit.nets}
    if set(displaced_nets) - known:
        raise ValueError("Unknown displaced net")
    router = DeterministicRouter()
    profile = constraints.profile
    overrides = {item.net_name: item for item in constraints.nets}

    def width_for(name):
        override = overrides.get(name)
        return (override.width_mm if override and override.width_mm is not None else
                float(profile.power_width_mm.value if router._power(name) else profile.signal_width_mm.value))

    centres, terminal_keys, pads = _geometry(pcb, board)
    pads = npth_search_obstacles(pcb, board, profile, pads)
    blocked = []
    access = router._pad_access(pcb, board, centres, profile,
                               width_for=width_for, on_blocked=blocked.append)
    if blocked:
        raise ValueError(f"Fresh pad access is blocked: {blocked}")
    escapes = escapes or {}
    for key, points in escapes.items():
        if key not in centres or len(points) < 2 or points[0] != centres[key]:
            raise ValueError("Authored escape must begin at its real terminal centre")
        access[key] = points[-1]
    net_pads, occupied = {}, {}
    for net in circuit.nets:
        unique = {}
        for pin in sorted(net.connections, key=lambda p: (p.component, p.pin)):
            for key in terminal_keys[(pin.component, pin.pin)]:
                point, entry = centres[key], access[key]
                unique.setdefault((point.x_mm, point.y_mm), (f"{key[0]}.{key[1]}", point, entry))
                for a, b in zip(escapes.get(key, [point, entry]), escapes.get(key, [point, entry])[1:]):
                    if a != b:
                        occupied.setdefault(net.name, []).append((a, b, "F.Cu", width_for(net.name)))
                if key in escapes:
                    # Reserve future via space. This is only a router obstacle;
                    # no copper/via is emitted unless an actual route uses it.
                    for layer in ("F.Cu", "B.Cu"):
                        occupied.setdefault(net.name, []).append((entry, entry, layer, float(profile.via_diameter_mm.value)))
        net_pads[net.name] = list(unique.values())
    failed = [failure.net_name for failure in proposal.failures]
    selected = list(dict.fromkeys([*failed, *displaced_nets]))
    if retry_order is not None:
        if set(retry_order) != set(selected) or len(retry_order) != len(set(retry_order)):
            raise ValueError("Retry order must contain every selected net exactly once")
        selected = list(retry_order)
    by_name = {net.net_name: net for net in proposal.routed_nets}
    paths = {name: [] if name in selected else list(by_name[name].paths) for name in sorted(known)}

    def occupy(name, path):
        for track in path.tracks:
            occupied.setdefault(name, []).append((track.start, track.end, track.layer, track.width_mm))
        for via in path.vias:
            for layer in ("F.Cu", "B.Cu"):
                occupied.setdefault(name, []).append((via.position, via.position, layer, via.diameter_mm))

    for name, preserved in paths.items():
        for path in preserved:
            occupy(name, path)
    attempt = max((int(t.attempt_id.split("-")[1]) for t in proposal.tracks), default=0)
    initial_attempt = attempt
    failures, expanded_total = {}, 0
    started = monotonic()

    def check():
        if monotonic() - started >= time_budget_seconds:
            raise _RoutingInterrupted("Bounded controller copper-repair deadline reached")

    for name in selected:
        connections = router._connections(net_pads, [name], shortest_first=True)
        for _, source, target in connections:
            if name in failures:
                break
            # A sealed MCU escape fails immediately when searched from that end.
            if target[0].startswith("U1.") and not source[0].startswith("U1."):
                source, target = target, source
            attempt += 1
            reason = []
            override = overrides.get(name)
            try:
                check()
                found = router._find(name, source[2], target[2], board, profile, pads, occupied,
                    check=check, width_mm=width_for(name),
                    preferred_layer=override.preferred_layer if override else None,
                    on_failure=lambda code, count, captured=reason: captured.append((code, count)))
                if found is None:
                    code, count = reason[-1]
                    expanded_total += count
                    failures[name] = RoutingFailure(net_name=name, reason=code,
                        detail=f"Local replay did not connect {source[0]} to {target[0]}")
                    continue
                states, count = found
                expanded_total += count
                start = (source[0], source[2], source[2]) if tuple(source[0].split(".")) in escapes else source
                end = (target[0], target[2], target[2]) if tuple(target[0].split(".")) in escapes else target
                path = router._to_path(name, start, end, states, profile, attempt,
                                       width_mm=width_for(name))
                for terminal in (source, target):
                    key = tuple(terminal[0].split("."))
                    if key in escapes:
                        points = escapes[key]
                        for i, (a, b) in enumerate(pairwise(points)):
                            path.tracks.append(TrackSegment(segment_id=_id(f"repair-{attempt}", f"{terminal[0]}:{i}"),
                                net_name=name, layer="F.Cu", start=a, end=b, width_mm=width_for(name),
                                attempt_id=f"route-{attempt:04d}-{name}"))
                paths[name].append(path)
                occupy(name, path)
            except _RoutingInterrupted as exc:
                expanded_total += exc.expanded_nodes
                failures[name] = RoutingFailure(net_name=name,
                    reason=RoutingFailureReason.ROUTING_INCOMPLETE, detail=str(exc))
        print(f"Repair {name}: {'unresolved' if name in failures else 'connected'}", flush=True)
    routed = [RoutedNet(net_name=name, terminal_pads=[item[0] for item in net_pads[name]],
                        paths=paths[name]) for name in sorted(known)]
    tracks = [t for net in routed for path in net.paths for t in path.tracks]
    vias = [v for net in routed for path in net.paths for v in path.vias]
    manifest = {"kind": "bounded_local_copper_repair", "proposal_hash": proposal.content_hash,
        "prior_source_pcb_fingerprint": prior_pcb.fingerprint.digest,
        "fresh_source_pcb_fingerprint": pcb.fingerprint.digest,
        "semantic_pad_geometry_equal": True, "displaced_nets": list(displaced_nets),
        "retry_order": selected, "time_budget_seconds": time_budget_seconds,
        "elapsed_seconds": round(monotonic()-started, 3),
        "preserved_path_count": sum(len(net.paths) for net in proposal.routed_nets if net.net_name not in selected),
        "rules_relaxed": False, "unresolved_nets": sorted(failures)}
    manifest["minimum_npth_copper_clearance_mm"] = MINIMUM_NPTH_COPPER_CLEARANCE_MM
    manifest["npth_policy"] = "Source pad/drill geometry unchanged; only search obstacles expand to enforce native 0.25 mm hole clearance. Native DRC still required."
    if escapes:
        manifest["authored_escapes"] = {".".join(key): [point.model_dump() for point in points]
                                        for key, points in escapes.items()}
        manifest["reserved_via_room_mm"] = profile.via_diameter_mm.value
    result = RoutingPlan(source_pcb_fingerprint=pcb.fingerprint.digest, source_pcb_path=pcb.path,
        source_constraints_hash=board.content_hash, circuit_content_hash=circuit.content_hash,
        profile=profile, net_constraints=constraints.nets, routed_nets=routed,
        failures=list(failures.values()), statistics=RoutingStatistics(
            required_connections=sum(max(0, len(p)-1) for p in net_pads.values()),
            routed_net_count=sum(len(paths[name]) == max(0, len(net_pads[name])-1)
                                 and name not in failures for name in known),
            unresolved_net_count=len(failures), track_segment_count=len(tracks), via_count=len(vias),
            total_track_length_mm=round(sum(t.length_mm for t in tracks), 6),
            expanded_nodes=expanded_total, routing_attempts=attempt-initial_attempt,
            reroute_count=1, route_order=selected),
        events=[*proposal.events, _event(circuit, EventKind.REROUTE_ATTEMPTED,
            "Bounded local rip-up/replay proposed new copper under unchanged rules", manifest)])
    return result, manifest


def structured_route(circuit, pcb, board, constraints, *, time_budget_seconds=600):
    """Expand dense LQFP pitch before unrestricted routing.

    Straight outward stubs clear the real lands, then monotonic traces widen
    pitch. Empty 0.6-mm via sites at the ends are reserved for every dense pin.
    The board's custom header connects top GPIO to the nearest header row.
    """
    from .design import HEADER_GPIO_PINS, HEADER_TOP_GPIO_PINS

    router = DeterministicRouter()
    centres = router._pad_centres(pcb, board)
    bindings = {(b.component_ref, b.pad_number): b for b in pcb.compilation.pad_bindings}
    escapes = {}
    for pin in range(26, 101):
        key = ("U1", str(pin))
        if bindings[key].net_name is None:
            continue
        point = centres[key]
        if pin >= 76:
            points = [Point(x_mm=point.x_mm, y_mm=26.25),
                      Point(x_mm=49+2*(point.x_mm-49), y_mm=16.25)]
        elif pin >= 51:
            points = [Point(x_mm=57.75, y_mm=point.y_mm),
                      Point(x_mm=62.75, y_mm=35+1.5*(point.y_mm-35))]
        else:
            points = [Point(x_mm=point.x_mm, y_mm=43.75),
                      Point(x_mm=49+1.5*(point.x_mm-49), y_mm=49.75)]
        escapes[key] = [point, *points]
    # The user button is the sole remaining left-edge signal below the analog
    # supply group. Preserve its bend past those adjacent supply lands.
    key = ("U1", "23")
    escapes[key] = [centres[key], Point(x_mm=40.25, y_mm=40), Point(x_mm=39.5, y_mm=42.5)]
    terminals = router._terminal_keys(pcb)
    routed = []
    completed = set()
    header_by_mcu = {str(pin): str(i) for i, pin in enumerate(HEADER_GPIO_PINS, 3)}
    for net in circuit.nets:
        keys = [key for pin in net.connections for key in terminals[(pin.component, pin.pin)]]
        paths = []
        for key in keys:
            if key not in escapes:
                continue
            points = escapes[key]
            top_gpio = key[0] == "U1" and int(key[1]) in HEADER_TOP_GPIO_PINS
            destination = ".".join(key)
            if top_gpio:
                destination = f"J2.{header_by_mcu[key[1]]}"
                contact = centres[("J2", header_by_mcu[key[1]])]
                points = [*points, Point(x_mm=contact.x_mm, y_mm=9.5), contact]
                completed.add(net.name)
            width = float(constraints.profile.power_width_mm.value if router._power(net.name)
                          else constraints.profile.signal_width_mm.value)
            tracks = [TrackSegment(segment_id=_id(f"seed-{key}",str(i)), net_name=net.name,
                layer="F.Cu", start=a, end=b, width_mm=width, attempt_id="route-0000-seed")
                for i, (a,b) in enumerate(pairwise(points))]
            # Self-terminal escape paths make no claim to connect another pad.
            # Only complete, checked top-GPIO paths may be retained as routes.
            # Candidate exit vias verify the reserved space as well as traces.
            # The final route only emits exits it actually uses.
            via = Via(via_id=_id(f"seed-{key}","exit"), net_name=net.name, position=points[-1],
                diameter_mm=float(constraints.profile.via_diameter_mm.value),
                drill_mm=float(constraints.profile.via_drill_mm.value), source_layer="F.Cu",
                destination_layer="B.Cu", attempt_id="route-0000-seed")
            paths.append(RoutePath(source_pad=".".join(key), target_pad=destination,
                                   tracks=tracks, vias=[] if top_gpio else [via], expanded_nodes=0))
        routed.append(RoutedNet(net_name=net.name, terminal_pads=[".".join(key) for key in keys], paths=paths))
    proposal = RoutingPlan(source_pcb_fingerprint=pcb.fingerprint.digest, source_pcb_path=pcb.path,
        source_constraints_hash=board.content_hash, circuit_content_hash=circuit.content_hash,
        profile=constraints.profile, net_constraints=constraints.nets, routed_nets=routed,
        failures=[RoutingFailure(net_name=net.name, reason=RoutingFailureReason.ROUTING_INCOMPLETE,
                                  detail="Authored escape geometry only; remaining connection not yet routed") for net in circuit.nets if net.name not in completed],
        statistics=RoutingStatistics(required_connections=sum(max(0,len(net.terminal_pads)-1) for net in routed),
            routed_net_count=len(completed), unresolved_net_count=len(circuit.nets)-len(completed),
            track_segment_count=sum(len(p.tracks) for n in routed for p in n.paths),
            via_count=sum(len(p.vias) for n in routed for p in n.paths),
            total_track_length_mm=sum(t.length_mm for n in routed for p in n.paths for t in p.tracks),
            expanded_nodes=0, routing_attempts=0, route_order=[]))
    seed_check = verify_routing(circuit, pcb, board, proposal)
    geometry_failures = [finding for finding in seed_check.findings
        if finding.status.value == "fail" and finding.rule_id not in {"PB-ROUTE-001", "PB-ROUTE-009"}]
    disconnected_seeded = {name for finding in seed_check.findings if finding.rule_id == "PB-ROUTE-001"
                           and finding.status.value == "fail" for name in finding.net_names} & completed
    if disconnected_seeded:
        raise ValueError(f"Seeded header paths are not continuously connected: {sorted(disconnected_seeded)}")
    if geometry_failures:
        raise ValueError(f"Authored escape geometry failed independent checks: {geometry_failures}")
    # Protect the local SPI path before the distant shared indicator controls.
    priority = ("SPI_SCK", "SPI_MISO", "SPI_MOSI", "EEPROM_CS", "3V3", "GND", "USER", "NRST", "SWDIO", "SWCLK",
                "SR_OE", "SR_CLR", "SR_CLK", "SR_LATCH", "SR_DATA", "SR_CHAIN")
    order = [*priority, *sorted(n.name for n in circuit.nets if n.name not in priority and n.name not in completed)]
    plan, manifest = repair(circuit, pcb, board, constraints, proposal, pcb, displaced_nets=(),
        time_budget_seconds=time_budget_seconds, escapes=escapes, retry_order=order)
    manifest["kind"] = "authored_lqfp_fanout_and_bounded_routing"
    manifest["seed_geometry_checked"] = True
    manifest["seeded_complete_gpio_nets"] = sorted(completed)
    manifest["complete_header_wiring"] = {str(i): str(pin) for i, pin in enumerate(HEADER_GPIO_PINS,3)}
    return plan, manifest


def main():
    from .build import write_json
    from .design import build_design
    from .physical import (
        ControllerPcbCompiler,
        build_board_constraints,
        routing_constraints,
        scoped_footprints,
    )
    from .schematic import ControllerSchematicCompiler
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposal", type=Path)
    parser.add_argument("--prior-artifact", type=Path)
    parser.add_argument("--structured", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=240)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError("Use an empty diagnostic output directory")
    args.output.mkdir(parents=True, exist_ok=True)
    if not args.structured and (not args.proposal or not args.prior_artifact):
        parser.error("Repair mode needs --proposal and --prior-artifact")
    if not args.structured:
        raw = args.proposal.read_bytes()
        proposal = RoutingPlan.model_validate_json(raw)
        prior = PcbArtifact.model_validate_json(args.prior_artifact.read_text())
    design = build_design()
    with scoped_footprints():
        board = build_board_constraints(design.circuit)
        schematic = ControllerSchematicCompiler(design.catalog).compile(
            design.circuit, args.output / "controller.kicad_sch")
        placed = ControllerPcbCompiler(design.catalog).compile(
            design.circuit, schematic, board, args.output / "controller-placed.kicad_pcb")
        if not placed.compilation.physical_verification.passed:
            raise ValueError("Fresh placement does not pass physical checks")
        write_json(args.output / "placed-artifact.json", placed)
        if args.structured:
            plan, manifest = structured_route(design.circuit, placed, board,
                routing_constraints(design.circuit), time_budget_seconds=args.seconds)
        else:
            plan, manifest = repair(design.circuit, placed, board, routing_constraints(design.circuit),
                                    proposal, prior, time_budget_seconds=args.seconds)
            manifest["proposal_file_sha256"] = hashlib.sha256(raw).hexdigest()
        report = verify_routing(design.circuit, placed, board, plan)
        manifest["independent_routing_passed"] = report.passed
        write_json(args.output / "routing-plan.json", plan)
        write_json(args.output / "routing-verification.json", report)
        write_json(args.output / "repair-manifest.json", manifest)
        print(f"Independent routing verification: {report.passed}; unresolved {len(plan.failures)}", flush=True)


if __name__ == "__main__":
    main()
