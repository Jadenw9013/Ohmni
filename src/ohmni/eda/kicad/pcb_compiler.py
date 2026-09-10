"""Deterministic, placed-but-unrouted KiCad PCB compiler."""

from __future__ import annotations

import hashlib
import math
import uuid
from pathlib import Path
from typing import Protocol, runtime_checkable

from ...adapters import PartCatalog
from ...domain import CircuitIR, EngineeringEvent, EventKind, Lesson
from ...physical.footprints import footprint
from ...physical.models import BoardConstraints, FootprintBinding, FootprintDefinition, PadBinding
from ...physical.rules import verify_physical
from ...routing.models import RoutingPlan
from ...routing.verifier import verify_routing
from ..models import ArtifactFingerprint, SchematicArtifact
from ..pcb_models import (
    CompiledTrackGeometry,
    CompiledViaGeometry,
    PcbArtifact,
    PcbCompilationReport,
    PcbCopperStatistics,
)
from .sexpr import number, quote

PCB_COMPILER_VERSION="0.2.0"
PCB_FORMAT_VERSION="20240108"
PCB_UUID_NAMESPACE=uuid.UUID("63af3592-6efd-5c14-9430-a5b827559c49")


class PcbCompilationError(ValueError): pass


@runtime_checkable
class PcbCompiler(Protocol):
    def compile(self,circuit:CircuitIR,schematic:SchematicArtifact,constraints:BoardConstraints,destination:Path,routing_plan:RoutingPlan|None=None)->PcbArtifact: ...


def _uuid(seed: str, identity: str) -> str:
    return str(uuid.uuid5(PCB_UUID_NAMESPACE,f"{seed}:{identity}"))


def _normalized_number(value: float) -> float:
    """Round exactly as the KiCad serializer does before binding geometry."""
    return float(number(value))


class KiCadPcbCompiler:
    def __init__(self,catalog:PartCatalog): self.catalog=catalog

    def compile(self,circuit,schematic,constraints,destination,routing_plan=None):
        if not schematic.is_current: raise PcbCompilationError("source schematic artifact is stale")
        if schematic.circuit_content_hash != circuit.content_hash: raise PcbCompilationError("schematic and CircuitIR fingerprints disagree")
        placements={p.component_ref:p for p in constraints.placements}
        if set(placements) != {c.ref for c in circuit.components}: raise PcbCompilationError("placements must cover exactly the CircuitIR components")
        footprint_bindings=[];pad_bindings=[];fp_ids={};events=[self._event(circuit,EventKind.PCB_COMPILATION_STARTED,"PCB compilation started")]
        connected={(p.component,p.pin):n.name for n in circuit.nets for p in n.connections}
        for instance in sorted(circuit.components,key=lambda c:c.ref):
            spec=self.catalog.get(instance.part_id)
            package=spec.package(instance.package) if spec and instance.package else None
            if not spec or not package or not package.kicad_footprint: raise PcbCompilationError(f"{instance.ref}: explicit footprint unavailable")
            fp=footprint(package.kicad_footprint)
            if fp is None: raise PcbCompilationError(f"{instance.ref}: project-local footprint geometry unavailable for {package.kicad_footprint}")
            try:
                fp = FootprintDefinition.model_validate(fp.model_dump())
            except ValueError as exc:
                raise PcbCompilationError(f"{instance.ref}: invalid project-local footprint geometry: {exc}") from exc
            available={p.number for p in fp.pads if not p.mechanical}
            required={p.number for p in spec.pins}
            if not required <= available: raise PcbCompilationError(f"{instance.ref}: missing physical pads {sorted(required-available)}")
            fp_ids[instance.ref]=fp.footprint_id
            footprint_bindings.append(FootprintBinding(component_ref=instance.ref,part_id=instance.part_id,package=instance.package,
                                                       footprint_id=fp.footprint_id,source=fp.source,
                                                       geometry_fingerprint=fp.content_hash))
            events.append(self._event(circuit,EventKind.FOOTPRINT_RESOLVED,f"{instance.ref} footprint resolved"))
            for pin in spec.pins:
                pad_bindings.append(PadBinding(component_ref=instance.ref,pin_number=pin.number,pad_number=pin.number,net_name=connected.get((instance.ref,pin.number))))
                events.append(self._event(circuit,EventKind.PAD_BINDING_RESOLVED,f"{instance.ref}.{pin.number} mapped to pad {pin.number}"))
        constraint_events=[]
        for constraint in constraints.placement_constraints:
            event=self._event(circuit,EventKind.PLACEMENT_CONSTRAINT_APPLIED,constraint.reason,{"constraint_id":constraint.constraint_id,"component_ref":constraint.component_ref,"target_ref":constraint.target_ref})
            events.append(event);constraint_events.append((constraint,event))
        physical=verify_physical(circuit,constraints,fp_ids,pad_bindings)
        events.append(self._event(circuit,EventKind.PHYSICAL_VALIDATION_RUN,"Physical validation run"))
        if not physical.passed:
            events.append(self._event(circuit,EventKind.PHYSICAL_VALIDATION_FAILED,"Physical validation failed"))
        self._validate_consistency(circuit,schematic,footprint_bindings,pad_bindings)
        nets={name:i+1 for i,name in enumerate(sorted(n.name for n in circuit.nets))}
        seed=hashlib.sha256(f"{circuit.content_hash}:{schematic.fingerprint.digest}:{constraints.content_hash}".encode()).hexdigest()
        lines=["(kicad_pcb",f"  (version {PCB_FORMAT_VERSION})",'  (generator "ohmni")',f'  (generator_version "{PCB_COMPILER_VERSION}")',"  (general (thickness 1.6))",'  (paper "A4")',"  (layers",'    (0 "F.Cu" signal)','    (31 "B.Cu" signal)','    (34 "B.Paste" user "b.paste")','    (35 "F.Paste" user "f.paste")','    (36 "B.SilkS" user "b.silkscreen")','    (37 "F.SilkS" user "f.silkscreen")','    (38 "B.Mask" user)','    (39 "F.Mask" user)','    (44 "Edge.Cuts" user)',"  )","  (setup (pad_to_mask_clearance 0))"]
        for name,index in sorted(nets.items(),key=lambda x:x[1]): lines.append(f"  (net {index} {quote(name)})")
        binding_by_ref={b.component_ref:b for b in footprint_bindings}
        for instance in sorted(circuit.components,key=lambda c:c.ref):
            fp=footprint(binding_by_ref[instance.ref].footprint_id);place=placements[instance.ref]
            lines += self._render_footprint(seed,instance,fp,place,nets,connected)
            events.append(self._event(circuit,EventKind.COMPONENT_PLACED,f"{instance.ref} placed",{"x_mm":place.x_mm,"y_mm":place.y_mm,"reason":place.reason}))
        w,h=constraints.outline.width_mm,constraints.outline.height_mm
        for i,(a,b) in enumerate([((0,0),(w,0)),((w,0),(w,h)),((w,h),(0,h)),((0,h),(0,0))]):
            lines.append(f'  (gr_line (start {number(a[0])} {number(a[1])}) (end {number(b[0])} {number(b[1])}) (stroke (width 0.1) (type default)) (layer "Edge.Cuts") (uuid "{_uuid(seed,f"edge:{i}")}"))')
        routing_verification=None
        source_placed=None
        emitted_tracks=[]
        emitted_vias=[]
        coalesced_layer_transitions=0
        reused_plated_through_hole_transitions=0
        if routing_plan is not None:
            if routing_plan.circuit_content_hash != circuit.content_hash or routing_plan.source_constraints_hash != constraints.content_hash:
                raise PcbCompilationError("routing plan lineage differs from CircuitIR or placement constraints")
            source_placed=ArtifactFingerprint(digest=routing_plan.source_pcb_fingerprint)
            placed_stub=PcbArtifact(path=destination,fingerprint=source_placed,circuit_content_hash=circuit.content_hash,schematic_fingerprint=schematic.fingerprint,source_schematic_path=schematic.path,constraints_hash=constraints.content_hash,compiler_version=PCB_COMPILER_VERSION,compilation=PcbCompilationReport(circuit_content_hash=circuit.content_hash,artifact_fingerprint=source_placed,schematic_fingerprint=schematic.fingerprint,source_schematic_path=schematic.path,constraints_hash=constraints.content_hash,footprint_bindings=footprint_bindings,pad_bindings=pad_bindings,net_mapping=nets,physical_verification=physical,copper_statistics=PcbCopperStatistics(modeled_track_segment_count=0,modeled_layer_transition_count=0,track_segment_count=0,via_count=0,coalesced_layer_transition_count=0,plated_through_hole_transition_count=0,total_track_length_mm=0)))
            routing_verification=verify_routing(circuit,placed_stub,constraints,routing_plan)
            if not routing_verification.passed:
                raise PcbCompilationError("routing plan failed independent Ohmni verification")
            for track in routing_plan.tracks:
                binding=CompiledTrackGeometry(source_segment_id=track.segment_id,emitted_uuid=_uuid(seed,"track:"+track.segment_id),net_name=track.net_name,net_number=nets[track.net_name],layer=track.layer,start_x_mm=_normalized_number(track.start.x_mm),start_y_mm=_normalized_number(track.start.y_mm),end_x_mm=_normalized_number(track.end.x_mm),end_y_mm=_normalized_number(track.end.y_mm),width_mm=_normalized_number(track.width_mm))
                emitted_tracks.append(binding)
                lines.append(self._render_track(binding))
            unique_vias={(via.net_name,via.position.x_mm,via.position.y_mm):via for via in routing_plan.vias}
            coalesced_layer_transitions=len(routing_plan.vias)-len(unique_vias)
            for via in unique_vias.values():
                # A plated through-hole pad already provides the requested
                # F.Cu/B.Cu transition; emitting a coincident drilled via would
                # create a duplicate hole without adding connectivity.
                reuse_pth=False
                for binding in footprint_bindings:
                    fp=footprint(binding.footprint_id);place=placements[binding.component_ref]
                    for pad in fp.pads:
                        if pad.kind!="thru_hole" or connected.get((binding.component_ref,pad.number))!=via.net_name:continue
                        angle=math.radians(place.rotation_deg)
                        px=place.x_mm+pad.x_mm*math.cos(angle)-pad.y_mm*math.sin(angle)
                        py=place.y_mm+pad.x_mm*math.sin(angle)+pad.y_mm*math.cos(angle)
                        if ((px-via.position.x_mm)**2+(py-via.position.y_mm)**2)**.5 <= min(pad.width_mm,pad.height_mm)/2:
                            reuse_pth=True;break
                    if reuse_pth:break
                if reuse_pth:
                    reused_plated_through_hole_transitions+=1
                    continue
                binding=CompiledViaGeometry(source_via_id=via.via_id,emitted_uuid=_uuid(seed,"via:"+via.via_id),net_name=via.net_name,net_number=nets[via.net_name],x_mm=_normalized_number(via.position.x_mm),y_mm=_normalized_number(via.position.y_mm),diameter_mm=_normalized_number(via.diameter_mm),drill_mm=_normalized_number(via.drill_mm))
                emitted_vias.append(binding)
                lines.append(self._render_via(binding))
        lines += [")",""]
        payload="\n".join(lines);destination=destination.resolve();destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(payload,encoding="utf-8",newline="\n")
        digest=hashlib.sha256(payload.encode()).hexdigest();events.append(self._event(circuit,EventKind.PCB_ARTIFACT_COMPILED,"PCB artifact compiled",{"sha256":digest}))
        decoupling_ids=[event.event_id for constraint,event in constraint_events if constraint.kind.value=="near_component"]
        edge_ids=[event.event_id for constraint,event in constraint_events if constraint.kind.value=="board_edge"]
        lessons=[]
        if decoupling_ids: lessons.append(Lesson(topic="Decoupling placement",body="A decoupling capacitor needs both the correct electrical net and a short physical path to its target supply. Ohmni measured the configured capacitor-to-IC distances.",derived_from_event_ids=decoupling_ids))
        if edge_ids: lessons.append(Lesson(topic="Connector placement",body="USB-C and programming connectors are constrained near a board edge for physical access; this is a placement constraint, not an electrical claim.",derived_from_event_ids=edge_ids))
        copper_statistics=PcbCopperStatistics(modeled_track_segment_count=len(routing_plan.tracks) if routing_plan else 0,modeled_layer_transition_count=len(routing_plan.vias) if routing_plan else 0,track_segment_count=len(emitted_tracks),via_count=len(emitted_vias),coalesced_layer_transition_count=coalesced_layer_transitions,plated_through_hole_transition_count=reused_plated_through_hole_transitions,total_track_length_mm=round(sum(track.length_mm for track in emitted_tracks),6))
        report=PcbCompilationReport(circuit_content_hash=circuit.content_hash,artifact_fingerprint=ArtifactFingerprint(digest=digest),schematic_fingerprint=schematic.fingerprint,source_schematic_path=schematic.path,constraints_hash=constraints.content_hash,footprint_bindings=footprint_bindings,pad_bindings=pad_bindings,net_mapping=nets,physical_verification=physical,lessons=lessons,routing_plan_fingerprint=routing_plan.content_hash if routing_plan else None,routing_verification=routing_verification,emitted_tracks=emitted_tracks,emitted_vias=emitted_vias,copper_statistics=copper_statistics)
        return PcbArtifact(path=destination,fingerprint=ArtifactFingerprint(digest=digest),circuit_content_hash=circuit.content_hash,schematic_fingerprint=schematic.fingerprint,source_schematic_path=schematic.path,constraints_hash=constraints.content_hash,compiler_version=PCB_COMPILER_VERSION,compilation=report,events=events,source_placed_pcb_fingerprint=source_placed,source_placed_pcb_path=routing_plan.source_pcb_path if routing_plan else None,routing_plan_fingerprint=routing_plan.content_hash if routing_plan else None)

    @staticmethod
    def _render_track(track):
        return f'  (segment (start {number(track.start_x_mm)} {number(track.start_y_mm)}) (end {number(track.end_x_mm)} {number(track.end_y_mm)}) (width {number(track.width_mm)}) (layer "{track.layer}") (net {track.net_number}) (uuid "{track.emitted_uuid}"))'

    @staticmethod
    def _render_via(via):
        return f'  (via (at {number(via.x_mm)} {number(via.y_mm)}) (size {number(via.diameter_mm)}) (drill {number(via.drill_mm)}) (layers "{via.layers[0]}" "{via.layers[1]}") (net {via.net_number}) (uuid "{via.emitted_uuid}"))'

    def _validate_consistency(self,circuit,schematic,footprints,pads):
        schematic_refs={b.component_ref for b in schematic.compilation.symbol_bindings}
        pcb_refs={b.component_ref for b in footprints};circuit_refs={c.ref for c in circuit.components}
        if schematic_refs != circuit_refs or pcb_refs != circuit_refs: raise PcbCompilationError("component references differ across CircuitIR, schematic, and PCB")
        schematic_pins={(p.component_ref,p.circuit_pin) for b in schematic.compilation.symbol_bindings for p in b.pins}
        pcb_pins={(p.component_ref,p.pin_number) for p in pads}
        if schematic_pins != pcb_pins: raise PcbCompilationError("pin/pad membership differs between schematic and PCB")
        if set(schematic.compilation.net_mapping) != {n.name for n in circuit.nets}: raise PcbCompilationError("schematic net mapping differs from CircuitIR")
        expected={(p.component,p.pin):n.name for n in circuit.nets for p in n.connections}
        actual={(p.component_ref,p.pin_number):p.net_name for p in pads if p.net_name is not None}
        if actual != expected: raise PcbCompilationError("PCB pad net membership differs from CircuitIR")

    def _render_footprint(self,seed,instance,fp,place,nets,connected):
        out=[f'  (footprint {quote("ohmni_generated_"+instance.ref)} (layer "F.Cu") (uuid "{_uuid(seed,"footprint:"+instance.ref)}") (at {number(place.x_mm)} {number(place.y_mm)} {number(place.rotation_deg)})',f'    (property "Reference" {quote(instance.ref)} (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1) (thickness 0.15))))',f'    (property "Value" {quote(instance.part_id)} (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1) (thickness 0.15))))',f'    (property "OhmniFootprintSource" {quote(fp.footprint_id)} (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))','    (attr smd)']
        out.append(f'    (fp_rect (start {number(-fp.width_mm/2)} {number(-fp.height_mm/2)}) (end {number(fp.width_mm/2)} {number(fp.height_mm/2)}) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))')
        for i,pad in enumerate(fp.pads):
            net_name=connected.get((instance.ref,pad.number));net=f' (net {nets[net_name]} {quote(net_name)})' if net_name else ""
            if pad.kind in {"thru_hole", "np_thru_hole"}:
                if pad.drill is None:
                    raise PcbCompilationError(f"{instance.ref}.{pad.number}: explicit drill geometry is required")
                drill = (f'oval {number(pad.drill.width_mm)} {number(pad.drill.height_mm)}'
                         if pad.drill.shape == "oval" else number(pad.drill.width_mm))
                out.append(f'    (pad {quote(pad.number)} {pad.kind} {pad.shape} (at {number(pad.x_mm)} {number(pad.y_mm)}) (size {number(pad.width_mm)} {number(pad.height_mm)}) (drill {drill}) (layers "*.Cu" "*.Mask"){net} (uuid "{_uuid(seed,f"pad:{instance.ref}:{i}")}"))')
            else:
                rr=" (roundrect_rratio 0.2)" if pad.shape=="roundrect" else ""
                out.append(f'    (pad {quote(pad.number)} smd {pad.shape} (at {number(pad.x_mm)} {number(pad.y_mm)}) (size {number(pad.width_mm)} {number(pad.height_mm)}) (layers "F.Cu" "F.Paste" "F.Mask"){rr}{net} (uuid "{_uuid(seed,f"pad:{instance.ref}:{i}")}"))')
        out.append("  )");return out

    @staticmethod
    def _event(circuit,kind,summary,payload=None):
        identity=f"{kind.value}:{summary}:{payload!r}";return EngineeringEvent(event_id=hashlib.sha256(identity.encode()).hexdigest()[:16],kind=kind,summary=summary,circuit_content_hash=circuit.content_hash,payload=payload or {})
