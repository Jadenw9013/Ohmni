"""Deterministic, placed-but-unrouted KiCad PCB compiler."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Protocol, runtime_checkable

from ...adapters import PartCatalog
from ...domain import CircuitIR, EngineeringEvent, EventKind, Lesson
from ...physical.footprints import footprint
from ...physical.models import BoardConstraints, FootprintBinding, PadBinding
from ...physical.rules import verify_physical
from ..models import ArtifactFingerprint, SchematicArtifact
from ..pcb_models import PcbArtifact, PcbCompilationReport
from .sexpr import number, quote

PCB_COMPILER_VERSION="0.1.0"
PCB_FORMAT_VERSION="20240108"
PCB_UUID_NAMESPACE=uuid.UUID("63af3592-6efd-5c14-9430-a5b827559c49")


class PcbCompilationError(ValueError): pass


@runtime_checkable
class PcbCompiler(Protocol):
    def compile(self,circuit:CircuitIR,schematic:SchematicArtifact,constraints:BoardConstraints,destination:Path)->PcbArtifact: ...


def _uuid(seed: str, identity: str) -> str:
    return str(uuid.uuid5(PCB_UUID_NAMESPACE,f"{seed}:{identity}"))


class KiCadPcbCompiler:
    def __init__(self,catalog:PartCatalog): self.catalog=catalog

    def compile(self,circuit,schematic,constraints,destination):
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
            available={p.number for p in fp.pads if not p.mechanical}
            required={p.number for p in spec.pins}
            if not required <= available: raise PcbCompilationError(f"{instance.ref}: missing physical pads {sorted(required-available)}")
            fp_ids[instance.ref]=fp.footprint_id
            footprint_bindings.append(FootprintBinding(component_ref=instance.ref,part_id=instance.part_id,package=instance.package,footprint_id=fp.footprint_id,source=fp.source))
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
        lines=["(kicad_pcb",f"  (version {PCB_FORMAT_VERSION})",'  (generator "ohmni")',f'  (generator_version "{PCB_COMPILER_VERSION}")',"  (general (thickness 1.6))",'  (paper "A4")',"  (layers",'    (0 "F.Cu" signal)','    (31 "B.Cu" signal)','    (36 "B.SilkS" user "b.silkscreen")','    (37 "F.SilkS" user "f.silkscreen")','    (44 "Edge.Cuts" user)',"  )","  (setup (pad_to_mask_clearance 0))"]
        for name,index in sorted(nets.items(),key=lambda x:x[1]): lines.append(f"  (net {index} {quote(name)})")
        binding_by_ref={b.component_ref:b for b in footprint_bindings}
        for instance in sorted(circuit.components,key=lambda c:c.ref):
            fp=footprint(binding_by_ref[instance.ref].footprint_id);place=placements[instance.ref]
            lines += self._render_footprint(seed,instance,fp,place,nets,connected)
            events.append(self._event(circuit,EventKind.COMPONENT_PLACED,f"{instance.ref} placed",{"x_mm":place.x_mm,"y_mm":place.y_mm,"reason":place.reason}))
        w,h=constraints.outline.width_mm,constraints.outline.height_mm
        for i,(a,b) in enumerate([((0,0),(w,0)),((w,0),(w,h)),((w,h),(0,h)),((0,h),(0,0))]):
            lines.append(f'  (gr_line (start {number(a[0])} {number(a[1])}) (end {number(b[0])} {number(b[1])}) (stroke (width 0.1) (type default)) (layer "Edge.Cuts") (uuid "{_uuid(seed,f"edge:{i}")}"))')
        lines += [")",""]
        payload="\n".join(lines);destination=destination.resolve();destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(payload,encoding="utf-8",newline="\n")
        digest=hashlib.sha256(payload.encode()).hexdigest();events.append(self._event(circuit,EventKind.PCB_ARTIFACT_COMPILED,"PCB artifact compiled",{"sha256":digest}))
        decoupling_ids=[event.event_id for constraint,event in constraint_events if constraint.kind.value=="near_component"]
        edge_ids=[event.event_id for constraint,event in constraint_events if constraint.kind.value=="board_edge"]
        lessons=[]
        if decoupling_ids: lessons.append(Lesson(topic="Decoupling placement",body="A decoupling capacitor needs both the correct electrical net and a short physical path to its target supply. Ohmni measured the configured capacitor-to-IC distances.",derived_from_event_ids=decoupling_ids))
        if edge_ids: lessons.append(Lesson(topic="Connector placement",body="USB-C and programming connectors are constrained near a board edge for physical access; this is a placement constraint, not an electrical claim.",derived_from_event_ids=edge_ids))
        report=PcbCompilationReport(circuit_content_hash=circuit.content_hash,schematic_fingerprint=schematic.fingerprint,source_schematic_path=schematic.path,constraints_hash=constraints.content_hash,footprint_bindings=footprint_bindings,pad_bindings=pad_bindings,net_mapping=nets,physical_verification=physical,lessons=lessons)
        return PcbArtifact(path=destination,fingerprint=ArtifactFingerprint(digest=digest),circuit_content_hash=circuit.content_hash,schematic_fingerprint=schematic.fingerprint,source_schematic_path=schematic.path,constraints_hash=constraints.content_hash,compiler_version=PCB_COMPILER_VERSION,compilation=report,events=events)

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
            if pad.kind=="thru_hole":
                out.append(f'    (pad {quote(pad.number)} thru_hole {pad.shape} (at {number(pad.x_mm)} {number(pad.y_mm)}) (size {number(pad.width_mm)} {number(pad.height_mm)}) (drill {number(min(pad.width_mm,pad.height_mm)*.55)}) (layers "*.Cu" "*.Mask"){net} (uuid "{_uuid(seed,f"pad:{instance.ref}:{i}")}"))')
            else:
                rr=" (roundrect_rratio 0.2)" if pad.shape=="roundrect" else ""
                out.append(f'    (pad {quote(pad.number)} smd {pad.shape} (at {number(pad.x_mm)} {number(pad.y_mm)}) (size {number(pad.width_mm)} {number(pad.height_mm)}) (layers "F.Cu" "F.Paste" "F.Mask"){rr}{net} (uuid "{_uuid(seed,f"pad:{instance.ref}:{i}")}"))')
        out.append("  )");return out

    @staticmethod
    def _event(circuit,kind,summary,payload=None):
        identity=f"{kind.value}:{summary}:{payload!r}";return EngineeringEvent(event_id=hashlib.sha256(identity.encode()).hexdigest()[:16],kind=kind,summary=summary,circuit_content_hash=circuit.content_hash,payload=payload or {})
