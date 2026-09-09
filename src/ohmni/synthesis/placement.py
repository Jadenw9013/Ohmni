"""Physical intent collected by electrical block compilers, never inferred from notes."""

from __future__ import annotations

from datetime import UTC, datetime

from ..domain import CircuitIR, ComponentSpec, Evidence, EvidenceKind
from ..physical.models import (
    BoardEdge,
    BoardOutline,
    DecouplingTarget,
    PlacementConstraint,
    PlacementConstraintKind,
    PlacementGroup,
    PlacementGroupKind,
    PlacementRegion,
    PlacementRequest,
)

# Authored policy metadata is stable across runs, unlike a runtime evidence timestamp.
POLICY_RECORDED_AT = datetime(2026, 9, 8, tzinfo=UTC)
ANTENNA_SOURCE_SHA256 = "e08a57b98669dbb126e5006854fdefad7226c6fceeb34c94d6449fd48db8cbc9"
ANTENNA_REGION = PlacementRegion(x_min_mm=-24, x_max_mm=24, y_min_mm=-30.74, y_max_mm=-9.8)


def policy_evidence(label: str, detail: str) -> Evidence:
    return Evidence(kind=EvidenceKind.ASSUMPTION, label=label, detail=detail,
                    recorded_at=POLICY_RECORDED_AT)


def rail_evidence(spec: ComponentSpec, rail: str) -> tuple[Evidence, ...]:
    return tuple(evidence for rule in spec.decoupling_rules if rule.rail == rail
                 for evidence in rule.evidence)


class PlacementIntentBuilder:
    """Mutable compiler accumulator; the published request is frozen and hash-bound."""

    def __init__(self) -> None:
        self.groups: list[PlacementGroup] = []
        self.decoupling: list[DecouplingTarget] = []
        self.constraints: list[PlacementConstraint] = []

    def group(self, kind: PlacementGroupKind | str, anchor: str, members,
              reason: str) -> None:
        self.groups.append(PlacementGroup(group_id=f"block-{anchor}", kind=kind,
                                          anchor_ref=anchor, member_refs=tuple(members), reason=reason))

    def join(self, anchor: str, members) -> None:
        matches = [i for i, group in enumerate(self.groups) if group.anchor_ref == anchor]
        if len(matches) != 1:
            raise ValueError(f"Placement block {anchor} must already exist exactly once")
        index = matches[0]
        group = self.groups[index]
        self.groups[index] = group.model_copy(update={"member_refs": (*group.member_refs, *members)})

    def capacitor(self, capacitor_ref: str, target_ref: str, target_pin: str,
                  *, bulk: bool = False, evidence=()) -> None:
        distance = 10.0 if bulk else 5.0
        policy = policy_evidence(
            "Authored capacitor placement distance",
            f"The {distance:g} mm capacitor-pad to target-supply-pad limit is a layout policy, "
            "not a manufacturer distance or a measured electrical/RF performance guarantee.",
        )
        self.decoupling.append(DecouplingTarget(
            capacitor_ref=capacitor_ref, target_ref=target_ref, target_pin=target_pin,
            maximum_distance_mm=distance,
            reason=f"Keep {capacitor_ref}.1 within {distance:g} mm of its authored supply owner {target_ref}.{target_pin}.",
            evidence=(*evidence, policy),
        ))

    def near_pin(self, component_ref: str, target_ref: str, target_pin: str) -> None:
        self.constraints.append(PlacementConstraint(
            constraint_id=f"near-{component_ref}-{target_ref}", kind=PlacementConstraintKind.NEAR_COMPONENT,
            component_ref=component_ref, component_pin="1", target_ref=target_ref, target_pin=target_pin,
            maximum_distance_mm=5,
            reason="Keep the authored enable-delay capacitor near the processor enable pin.",
            evidence=[policy_evidence("Enable RC placement policy",
                                      "A 5 mm pad-to-pad limit is an authored layout choice; the enable RC is not supply decoupling.")],
        ))

    def edge(self, component_ref: str, edge: BoardEdge) -> None:
        self.constraints.append(PlacementConstraint(
            constraint_id=f"edge-{component_ref}", kind=PlacementConstraintKind.BOARD_EDGE,
            component_ref=component_ref, preferred_edge=edge, maximum_distance_mm=3,
            reason=f"Place {component_ref} near the {edge.value} board edge for access or antenna orientation.",
            evidence=[policy_evidence("Board-edge placement policy",
                                      "A 3 mm footprint-boundary distance is an authored mechanical-access policy; enclosure clearance is not verified.")],
        ))

    def antenna(self, component_ref: str) -> None:
        self.constraints.append(PlacementConstraint(
            constraint_id=f"antenna-{component_ref}", kind=PlacementConstraintKind.KEEPOUT,
            component_ref=component_ref, keepout_region=ANTENNA_REGION, relative_to_component=True,
            reason="Reserve the source-derived antenna region from copper and other components; RF performance is not verified.",
            evidence=[policy_evidence(
                "Source-derived antenna exclusion, assumed module compatibility",
                "Rectangle x[-24,24], y[-30.74,-9.8] mm is transcribed from the all-copper-layer "
                "keepout polygon in KiCad RF_Module:ESP32-WROOM-32, file SHA256 "
                f"{ANTENNA_SOURCE_SHA256}. Upstream prohibits tracks, vias, pads, copper pours, and footprints. "
                "Applying that library policy to the catalog ESP32-WROOM-32E is an explicit compatibility assumption; "
                "the geometric checks do not establish antenna matching, RF performance, or enclosure compliance.",
            )],
        ))

    def finish(self, circuit: CircuitIR) -> PlacementRequest:
        request = PlacementRequest(
            circuit_content_hash=circuit.content_hash, outline=BoardOutline(width_mm=100, height_mm=70),
            groups=tuple(self.groups), decoupling=tuple(self.decoupling), constraints=tuple(self.constraints),
        )
        members = {ref for group in request.groups for ref in group.member_refs}
        if members != {component.ref for component in circuit.components}:
            raise ValueError("Compiler placement groups must cover exactly the emitted components")
        connections = {(pin.component, pin.pin): net.name
                       for net in circuit.nets for pin in net.connections}
        owners = {member: group.anchor_ref for group in request.groups for member in group.member_refs}
        for target in request.decoupling:
            if owners.get(target.capacitor_ref) != target.target_ref:
                raise ValueError("Capacitor ownership must agree with its authored placement block")
            capacitor_net = connections.get((target.capacitor_ref, target.capacitor_pin))
            target_net = connections.get((target.target_ref, target.target_pin))
            if capacitor_net is None or capacitor_net != target_net:
                raise ValueError("Authored capacitor owner must share its actual supply net")
        return request


def record_usb_core(
    intent: PlacementIntentBuilder, *, usb_ref: str, cc_refs: tuple[str, str],
    regulator_ref: str, regulator_spec: ComponentSpec, input_cap: str, input_pin: str,
    output_cap: str, output_pin: str, mcu_ref: str, mcu_spec: ComponentSpec,
    supply_pin: str, local_cap: str, bulk_cap: str, enable_cap: str, enable_pin: str,
    enable_pullup: str, header_ref: str | None,
) -> None:
    """Record exact members supplied by the USB/core compiler at assembly time."""
    intent.group("connector", usb_ref, (usb_ref, *cc_refs), "USB-C socket and its two sink configuration resistors.")
    intent.group("power", regulator_ref, (regulator_ref, input_cap, output_cap), "Regulator with its owned input and output capacitors.")
    intent.group("processor", mcu_ref, (mcu_ref, local_cap, bulk_cap, enable_pullup, enable_cap), "Processor with supply support and enable RC.")
    intent.capacitor(input_cap, regulator_ref, input_pin, evidence=rail_evidence(regulator_spec, "VIN"))
    intent.capacitor(output_cap, regulator_ref, output_pin)
    intent.capacitor(local_cap, mcu_ref, supply_pin, evidence=rail_evidence(mcu_spec, "VDD"))
    intent.capacitor(bulk_cap, mcu_ref, supply_pin, bulk=True, evidence=rail_evidence(mcu_spec, "VDD"))
    intent.near_pin(enable_cap, mcu_ref, enable_pin)
    intent.edge(usb_ref, BoardEdge.BOTTOM)
    intent.edge(mcu_ref, BoardEdge.TOP)
    intent.antenna(mcu_ref)
    if header_ref is not None:
        intent.group("connector", header_ref, (header_ref,), "Serial programming access.")
        intent.edge(header_ref, BoardEdge.RIGHT)
