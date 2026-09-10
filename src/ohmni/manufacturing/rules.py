"""Deterministic checks against one stated manufacturing profile."""
import hashlib

from ..domain import EngineeringEvent, EventKind
from ..eda.pcb_models import PcbArtifact
from ..physical.models import BoardConstraints
from ..routing.models import RoutingPlan
from .models import (
    ManufacturingFinding,
    ManufacturingProfile,
    ManufacturingReport,
    ManufacturingStatus,
)
from .pad_geometry import measure_pads


def verify_manufacturing(pcb:PcbArtifact,board:BoardConstraints,plan:RoutingPlan,profile:ManufacturingProfile)->ManufacturingReport:
    out=[]
    def dimensional(rule,subject,designed,limit,minimum=True):
        margin=designed-limit if minimum else limit-designed;ok=margin>=-1e-9
        out.append(ManufacturingFinding(rule_id=rule,status=ManufacturingStatus.PASS if ok else ManufacturingStatus.FAIL,subject=subject,designed=designed,limit=limit,margin=round(margin,6),unit="mm",detail=f"{subject} {'meets' if ok else 'violates'} selected profile by {margin:+.3f} mm"))
    dimensional("PB-MFG-001","minimum track width",min(t.width_mm for t in plan.tracks),profile.minimum_track_width.value)
    dimensional("PB-MFG-002","required route clearance",float(plan.profile.clearance_mm.value),profile.minimum_clearance.value)
    pad_geometry = None
    try:
        pad_geometry = measure_pads(pcb, board)
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        out.append(ManufacturingFinding(rule_id="PB-MFG-011",status=ManufacturingStatus.UNKNOWN,
            subject="footprint copper and drills",detail=f"Emitted pad geometry could not be measured: {error}"))
    else:
        if pad_geometry.minimum_gap_mm is not None:
            dimensional("PB-MFG-011",f"pad clearance between {' and '.join(pad_geometry.closest_pair)}",
                        pad_geometry.minimum_gap_mm,profile.minimum_clearance.value)
        else:
            out.append(ManufacturingFinding(rule_id="PB-MFG-011",status=ManufacturingStatus.PASS,
                subject="footprint copper clearance",designed="not applicable: no distinct-net pad pair",
                detail=f"Measured {pad_geometry.copper_pad_count} lands; no pair requires mutual electrical clearance."))
        if pad_geometry.minimum_drill_mm is not None:
            dimensional("PB-MFG-012","minimum component hole width",pad_geometry.minimum_drill_mm,
                        profile.minimum_drill.value)
        else:
            out.append(ManufacturingFinding(rule_id="PB-MFG-012",status=ManufacturingStatus.PASS,
                subject="component holes",designed="not applicable: no component drills",
                detail="All measured footprint lands are surface mount."))
        if pad_geometry.slot_count:
            if not profile.supports_slots:
                out.append(ManufacturingFinding(rule_id="PB-MFG-013",status=ManufacturingStatus.FAIL,
                    subject="component slots",designed=pad_geometry.slot_count,
                    detail="This design contains slots, which the selected profile does not support."))
            elif profile.minimum_slot_width is None:
                out.append(ManufacturingFinding(rule_id="PB-MFG-013",status=ManufacturingStatus.UNKNOWN,
                    subject="component slots",designed=pad_geometry.slot_count,
                    detail="The selected profile supplies no minimum slot width."))
            else:
                dimensional("PB-MFG-013","minimum component slot width",pad_geometry.minimum_slot_width_mm,
                            profile.minimum_slot_width.value)
        else:
            out.append(ManufacturingFinding(rule_id="PB-MFG-013",status=ManufacturingStatus.PASS,
                subject="component slots",designed="not applicable: no slots",
                detail="No component slot geometry is present."))
    if plan.vias:
        dimensional("PB-MFG-003","minimum via drill",min(v.drill_mm for v in plan.vias),profile.minimum_drill.value)
        dimensional("PB-MFG-003","minimum via diameter",min(v.diameter_mm for v in plan.vias),profile.minimum_via_diameter.value)
    elif plan.statistics.via_count:
        out.append(ManufacturingFinding(
            rule_id="PB-MFG-003", status=ManufacturingStatus.UNKNOWN,
            subject="via requirements",
            detail="Routing statistics report vias but the plan contains no via geometry. "
                   "Via drill and diameter limits cannot be assessed.",
        ))
    else:
        # A known empty via set is not a zero-size drill or missing evidence.
        # These limits impose no constraint when the design contains no vias.
        out.append(ManufacturingFinding(
            rule_id="PB-MFG-003", status=ManufacturingStatus.PASS,
            subject="via requirements", designed="not applicable: no vias",
            detail="No vias are present, so via drill and diameter limits do not apply. "
                   "This check does not assess through-hole component drills.",
        ))
    dimensions_ok=profile.minimum_board_width_mm<=board.outline.width_mm<=profile.maximum_board_width_mm and profile.minimum_board_height_mm<=board.outline.height_mm<=profile.maximum_board_height_mm
    out.append(ManufacturingFinding(rule_id="PB-MFG-004",status=ManufacturingStatus.PASS if dimensions_ok else ManufacturingStatus.FAIL,subject="board dimensions",designed=f"{board.outline.width_mm} x {board.outline.height_mm}",limit=f"{profile.minimum_board_width_mm}-{profile.maximum_board_width_mm} x {profile.minimum_board_height_mm}-{profile.maximum_board_height_mm}",detail="board dimensions are supported" if dimensions_ok else "board dimensions are outside profile"))
    layers_ok=board.layer_count in profile.supported_layer_counts
    out.append(ManufacturingFinding(rule_id="PB-MFG-005",status=ManufacturingStatus.PASS if layers_ok else ManufacturingStatus.FAIL,subject="layer count",designed=board.layer_count,limit=str(profile.supported_layer_counts),detail="layer count supported" if layers_ok else "layer count unsupported"))
    dimensional("PB-MFG-006","copper-to-edge clearance",float(plan.profile.edge_clearance_mm.value),profile.minimum_edge_clearance.value)
    footprints_ok=all(x.footprint_id and x.source.upstream_file_sha256 for x in pcb.compilation.footprint_bindings)
    out.append(ManufacturingFinding(rule_id="PB-MFG-007",status=ManufacturingStatus.PASS if footprints_ok else ManufacturingStatus.FAIL,subject="footprint provenance",detail="all populated footprints resolved with provenance" if footprints_ok else "footprint provenance unresolved"))
    out.append(ManufacturingFinding(rule_id="PB-MFG-008",
        status=ManufacturingStatus.PASS if pad_geometry is not None else ManufacturingStatus.UNKNOWN,
        subject="fabrication features",
        detail=(f"Two-layer tracks, through-vias, rectangular outline, round holes, "
                f"{pad_geometry.slot_count} component slots and {pad_geometry.nonplated_hole_count} nonplated holes; "
                "dimensional and slot support are checked separately."
                if pad_geometry is not None else "Component fabrication features could not be measured.")))
    events=[_event(pcb,EventKind.MANUFACTURING_PROFILE_SELECTED,f"Manufacturing profile selected: {profile.profile_id}",{"profile_hash":profile.content_hash})]
    for finding in out:events.append(_event(pcb,EventKind.MANUFACTURING_CONSTRAINT_CHECKED if finding.status is ManufacturingStatus.PASS else EventKind.MANUFACTURING_CONSTRAINT_FAILED,f"{finding.rule_id}: {finding.subject}",finding.model_dump(mode="json")))
    return ManufacturingReport(profile=profile,routed_pcb_fingerprint=pcb.fingerprint.digest,routing_plan_fingerprint=plan.content_hash,findings=out,events=events)

def _event(pcb,kind,summary,payload):
    identity=f"{kind.value}:{summary}:{payload!r}";return EngineeringEvent(event_id=hashlib.sha256(identity.encode()).hexdigest()[:16],kind=kind,summary=summary,circuit_content_hash=getattr(pcb,"circuit_content_hash",None),payload=payload)
