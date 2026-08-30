"""Small deterministic geometry verifier for the supported golden board."""

from __future__ import annotations

import math

from ..domain import CircuitIR
from .footprints import footprint
from .models import (
    BoardConstraints,
    PhysicalFinding,
    PhysicalRuleStatus,
    PhysicalVerificationReport,
)


def verify_physical(circuit: CircuitIR, constraints: BoardConstraints, footprint_ids: dict[str, str], pad_bindings) -> PhysicalVerificationReport:
    findings = []
    placements = {p.component_ref: p for p in constraints.placements}
    boxes = {}
    for component in circuit.components:
        placement, fp_id = placements.get(component.ref), footprint_ids.get(component.ref)
        fp = footprint(fp_id) if fp_id else None
        if placement is None or fp is None:
            findings.append(PhysicalFinding(rule_id="PB-PCB-006", status=PhysicalRuleStatus.FAIL, description=f"{component.ref} lacks placement or footprint binding", component_refs=[component.ref]))
            continue
        half_w, half_h = fp.width_mm/2, fp.height_mm/2
        box=(placement.x_mm-half_w,placement.y_mm-half_h,placement.x_mm+half_w,placement.y_mm+half_h);boxes[component.ref]=box
        margin=constraints.minimum_edge_clearance_mm
        inside_outline=box[0]>=0 and box[1]>=0 and box[2]<=constraints.outline.width_mm and box[3]<=constraints.outline.height_mm
        clear=box[0]>=margin and box[1]>=margin and box[2]<=constraints.outline.width_mm-margin and box[3]<=constraints.outline.height_mm-margin
        findings.append(PhysicalFinding(rule_id="PB-PCB-002",status=PhysicalRuleStatus.PASS if inside_outline else PhysicalRuleStatus.FAIL,description=f"{component.ref} {'is inside the board outline' if inside_outline else 'extends outside the board outline'}",component_refs=[component.ref]))
        findings.append(PhysicalFinding(rule_id="PB-PCB-003",status=PhysicalRuleStatus.PASS if clear else PhysicalRuleStatus.FAIL,description=f"{component.ref} {'satisfies' if clear else 'violates'} board edge clearance",component_refs=[component.ref],limit_mm=margin))
    refs=sorted(boxes)
    for i,a in enumerate(refs):
        for b in refs[i+1:]:
            aa,bb=boxes[a],boxes[b]
            overlap=aa[0]<bb[2] and aa[2]>bb[0] and aa[1]<bb[3] and aa[3]>bb[1]
            if overlap:
                findings.append(PhysicalFinding(rule_id="PB-PCB-001",status=PhysicalRuleStatus.FAIL,description=f"{a} and {b} footprint bounds overlap",component_refs=[a,b]))
    bound={(b.component_ref,b.pin_number) for b in pad_bindings}
    missing_pads=0
    for net in circuit.nets:
        for pin in net.connections:
            if (pin.component,pin.pin) not in bound:
                missing_pads+=1
                findings.append(PhysicalFinding(rule_id="PB-PCB-006",status=PhysicalRuleStatus.FAIL,description=f"connected pin {pin} has no physical pad",component_refs=[pin.component]))
    if not missing_pads:
        findings.append(PhysicalFinding(rule_id="PB-PCB-006",status=PhysicalRuleStatus.PASS,description="all connected schematic pins resolve to physical pads"))
    for rule in constraints.placement_constraints:
        p=placements.get(rule.component_ref); target=placements.get(rule.target_ref) if rule.target_ref else None
        if rule.kind.value=="board_edge" and p:
            d=min(p.x_mm,p.y_mm,constraints.outline.width_mm-p.x_mm,constraints.outline.height_mm-p.y_mm)
            ok=d <= (rule.maximum_distance_mm or 0)
            findings.append(PhysicalFinding(rule_id="PB-PCB-005",status=PhysicalRuleStatus.PASS if ok else PhysicalRuleStatus.FAIL,description=rule.reason,component_refs=[rule.component_ref],measured_mm=d,limit_mm=rule.maximum_distance_mm))
        elif rule.kind.value=="near_component" and p and target:
            d=math.hypot(p.x_mm-target.x_mm,p.y_mm-target.y_mm);ok=d <= (rule.maximum_distance_mm or 0)
            findings.append(PhysicalFinding(rule_id="PB-PCB-004",status=PhysicalRuleStatus.PASS if ok else PhysicalRuleStatus.FAIL,description=rule.reason,component_refs=[rule.component_ref,rule.target_ref],measured_mm=d,limit_mm=rule.maximum_distance_mm))
    if not any(f.rule_id=="PB-PCB-001" for f in findings):
        findings.append(PhysicalFinding(rule_id="PB-PCB-001",status=PhysicalRuleStatus.PASS,description="no footprint bounding boxes overlap"))
    findings.append(PhysicalFinding(rule_id="PB-PCB-007",status=PhysicalRuleStatus.PASS,description="no routed copper emitted; unknown copper references impossible in this milestone"))
    return PhysicalVerificationReport(findings=findings)
