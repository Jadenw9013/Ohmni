"""Export the already-chosen routing policy for independent KiCad DRC.

KiCad's default project rules are not the authored routing profile. Shipping
explicit project/rule sidecars ensures that native DRC checks the same design
constraints. No finding is ignored, excluded, or assigned a weaker severity.
Rule syntax: https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#custom_design_rules
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from ohmni.eda.kicad.component_asset_parser import parse
from ohmni.routing.models import RoutingConstraints
from ohmni.routing.router import DeterministicRouter

GENERATOR = "ohmni-landing-redesign-routing-policy-v1"


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _identity(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{label} must be an explicit SHA256 fingerprint")


def write_native_rules(pcb_path, routing_constraints, *, circuit_hash, routing_plan_hash):
    """Write same-stem sidecars and return their exact provenance manifest.

Call ``verify_native_rules`` immediately before and after native DRC, and retain
the manifest with the report: existing DrcReport alone binds only PCB/schematic
bytes, not project settings or custom rule bytes.
    """
    _identity(circuit_hash, "circuit_hash")
    _identity(routing_plan_hash, "routing_plan_hash")
    constraints = RoutingConstraints.model_validate(routing_constraints.model_dump())
    pcb_path = Path(pcb_path).resolve(strict=True)
    if pcb_path.suffix != ".kicad_pcb":
        raise ValueError("Native rules require an existing .kicad_pcb artifact")
    pcb_bytes = pcb_path.read_bytes()
    root = parse(pcb_bytes.decode("utf-8"))
    if root.head != "kicad_pcb":
        raise ValueError("Native rules require PCB content")
    net_names = sorted({node.atoms()[1] for node in root.children("net")})
    per_net = {net.net_name: net for net in constraints.nets}
    if set(per_net) - set(net_names):
        raise ValueError("Routing policy names a net absent from the compiled PCB")
    # Restrict this bounded author's net expressions rather than interpolating
    # unescaped condition-language syntax from arbitrary project names.
    if any(not re.fullmatch(r"[A-Za-z0-9_+./-]+", name) for name in net_names):
        raise ValueError("Landing native-rule authoring received an unsupported net name")
    profile = constraints.profile
    signal = float(profile.signal_width_mm.value)
    clearance = float(profile.clearance_mm.value)
    via_diameter = float(profile.via_diameter_mm.value)
    via_drill = float(profile.via_drill_mm.value)
    edge = float(profile.edge_clearance_mm.value)
    widths = {}
    for name in net_names:
        specified = per_net.get(name)
        widths[name] = float(specified.width_mm if specified and specified.width_mm is not None
                             else profile.power_width_mm.value if DeterministicRouter._power(name)
                             else signal)
    project = {
        "meta": {"filename": pcb_path.with_suffix(".kicad_pro").name, "version": 1,
                 "generator": GENERATOR},
        "board": {"design_settings": {"rules": {
            "min_clearance": clearance, "min_track_width": signal,
            "min_copper_edge_clearance": edge,
            "min_via_diameter": via_diameter, "min_through_hole_diameter": via_drill,
        }}},
        "net_settings": {"meta": {"version": 4}, "classes": [{
            "name": "Default", "priority": 2147483647, "clearance": clearance,
            "track_width": signal, "via_diameter": via_diameter, "via_drill": via_drill,
        }], "netclass_patterns": []},
        "schematic": {}, "sheets": [],
    }
    rules = [f"# {GENERATOR}", f"# routing_profile_sha256={profile.content_hash}",
             f"# routing_plan_sha256={routing_plan_hash}",
             "# Same authored geometry policy as the router; fabricator capability unverified.",
             "(version 1)",
             '(rule "Authored routing geometry"',
             f"  (constraint clearance (min {clearance:g}mm))",
             f"  (constraint track_width (min {signal:g}mm))",
             f"  (constraint edge_clearance (min {edge:g}mm)))",
             '(rule "Authored through-via geometry"',
             '  (condition "A.Type == \'Via\'")',
             f"  (constraint via_diameter (min {via_diameter:g}mm))",
             f"  (constraint hole_size (min {via_drill:g}mm)))"]
    for name, width in widths.items():
        if width == signal:
            continue
        rules += [f'(rule "Authored width {name}"',
                  f'  (condition "A.NetName == \'{name}\'")',
                  f"  (constraint track_width (min {width:g}mm)))"]
    payloads = {".kicad_pro": _json(project), ".kicad_dru": ("\n".join(rules) + "\n").encode("utf-8")}
    # Do not overwrite a user project that happens to share the PCB stem.
    for suffix in payloads:
        path = pcb_path.with_suffix(suffix)
        if path.exists() and GENERATOR not in path.read_text(encoding="utf-8"):
            raise ValueError(f"Refusing to replace unowned KiCad sidecar: {path.name}")
    files = []
    for suffix, payload in payloads.items():
        path = pcb_path.with_suffix(suffix)
        path.write_bytes(payload)
        files.append({"path": str(path), "sha256": _hash(payload), "size_bytes": len(payload)})
    return {"schema_version": 1, "generator": GENERATOR,
            "pcb_path": str(pcb_path), "pcb_fingerprint": _hash(pcb_bytes),
            "circuit_fingerprint": circuit_hash, "routing_plan_fingerprint": routing_plan_hash,
            "routing_profile_fingerprint": profile.content_hash,
            "routing_constraints_sha256": _hash(_json(constraints.model_dump(mode="json"))),
            "routing_constraints": constraints.model_dump(mode="json"),
            "net_minimum_width_mm": widths, "files": files,
            "limitations": ["KiCad DRC corroborates this authored geometric profile; it does not qualify a fabrication process.",
                            "Source circuit, routing, and native reports remain separate evidence records."]}


def verify_native_rules(manifest):
    """Reject stale PCB/rule/project bytes rather than accepting old DRC truth."""
    pcb_path = Path(manifest["pcb_path"])
    if _hash(pcb_path.read_bytes()) != manifest["pcb_fingerprint"]:
        raise ValueError("PCB changed after native-rule binding")
    if {Path(item["path"]).suffix for item in manifest["files"]} != {".kicad_pro", ".kicad_dru"}:
        raise ValueError("Native-rule binding lacks both project and custom rules")
    for item in manifest["files"]:
        path = Path(item["path"])
        if path != pcb_path.with_suffix(path.suffix):
            raise ValueError("Native-rule sidecar is not beside the bound PCB")
        raw = path.read_bytes()
        if len(raw) != item["size_bytes"] or _hash(raw) != item["sha256"]:
            raise ValueError(f"Native-rule sidecar changed: {path.name}")
    constraints = RoutingConstraints.model_validate(manifest["routing_constraints"])
    if (constraints.profile.content_hash != manifest["routing_profile_fingerprint"]
            or _hash(_json(constraints.model_dump(mode="json"))) != manifest["routing_constraints_sha256"]):
        raise ValueError("Native-rule routing policy changed")
    return True
