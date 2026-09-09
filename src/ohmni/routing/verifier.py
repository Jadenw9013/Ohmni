"""Independent verification of emitted copper geometry."""

from __future__ import annotations

import math

from ..domain import CircuitIR
from ..eda.pcb_models import PcbArtifact
from ..physical.footprints import footprint
from ..physical.models import BoardConstraints
from .models import (
    Point,
    RoutingConstraints,
    RoutingFinding,
    RoutingPlan,
    RoutingRuleStatus,
    RoutingVerificationReport,
)
from .router import DeterministicRouter, _path_crosses_keepout, _point_segment_distance


def verify_routing(circuit: CircuitIR, pcb: PcbArtifact, board: BoardConstraints,
                   plan: RoutingPlan) -> RoutingVerificationReport:
    findings=[]
    def add(rule, ok, text, nets=()):
        findings.append(RoutingFinding(rule_id=rule,status=RoutingRuleStatus.PASS if ok else RoutingRuleStatus.FAIL,description=text,net_names=list(nets)))
    known={n.name for n in circuit.nets}
    try:
        RoutingConstraints.model_validate({"profile":plan.profile.model_dump(),
                                          "nets":[constraint.model_dump() for constraint in plan.net_constraints]})
        constraint_intent_ok={constraint.net_name for constraint in plan.net_constraints}<=known
    except ValueError:
        constraint_intent_ok=False
    refs_ok=(plan.circuit_content_hash==circuit.content_hash and plan.source_pcb_fingerprint==pcb.fingerprint.digest and plan.source_constraints_hash==board.content_hash)
    pads=DeterministicRouter._pad_centres(pcb,board)
    terminal_keys=DeterministicRouter._terminal_keys(pcb)
    expected={n.name:{key for p in n.connections for key in terminal_keys[(p.component,p.pin)]}
              for n in circuit.nets}
    binding_errors=_net_binding_errors(plan,expected,pads)
    copper_nets={x.net_name for x in plan.tracks+plan.vias}
    add("PB-ROUTE-003",refs_ok and copper_nets<=known and constraint_intent_ok and not binding_errors,
        "all copper paths, physical terminals, and routing constraints bind to unique semantic nets and valid lineage",
        sorted(binding_errors | (copper_nets-known)))
    edge=float(plan.profile.edge_clearance_mm.value)
    def copper_inside(point,radius):
        inset=edge+radius
        return (inset-1e-6<=point.x_mm<=board.outline.width_mm-inset+1e-6
                and inset-1e-6<=point.y_mm<=board.outline.height_mm-inset+1e-6)
    inside=(all(copper_inside(point,track.width_mm/2) for track in plan.tracks
                for point in (track.start,track.end))
            and all(copper_inside(via.position,via.diameter_mm/2) for via in plan.vias))
    add("PB-ROUTE-004",inside,"track and via copper maintain the physical board-edge clearance")
    min_signal=float(plan.profile.signal_width_mm.value)
    overrides={constraint.net_name:constraint for constraint in plan.net_constraints}
    widths=all(t.width_mm>=max(min_signal,
                  overrides[t.net_name].width_mm if t.net_name in overrides and overrides[t.net_name].width_mm is not None
                  else float(plan.profile.power_width_mm.value) if DeterministicRouter._power(t.net_name) else min_signal)
               for t in plan.tracks)
    add("PB-ROUTE-005",widths,"track widths satisfy the active routing profile")
    vd=float(plan.profile.via_diameter_mm.value);dr=float(plan.profile.via_drill_mm.value)
    vias_ok=all(v.diameter_mm>=vd and v.drill_mm>=dr and v.drill_mm<v.diameter_mm and {v.source_layer,v.destination_layer}=={"F.Cu","B.Cu"} for v in plan.vias)
    add("PB-ROUTE-006",vias_ok,"through-via dimensions and layers satisfy the active profile")
    max_vias=int(plan.profile.maximum_vias_per_connection.value)
    via_counts_ok=all(len(path.vias)<=max_vias for net in plan.routed_nets for path in net.paths)
    add("PB-ROUTE-008",via_counts_ok,"via count remains within the bounded policy")
    unfinished={failure.net_name for failure in plan.failures}
    add("PB-ROUTE-009",not unfinished,"routing completed without unresolved failures",sorted(unfinished))
    keepout_nets={net.net_name for net in plan.routed_nets
                  if any(_path_crosses_keepout(path,board) for path in net.paths)}
    add("PB-ROUTE-010",not keepout_nets,"tracks and vias remain outside declared copper keepouts",sorted(keepout_nets))
    connected_ok=True;open_nets=[]
    for net in circuit.nets:
        routed=next((n for n in plan.routed_nets if n.net_name==net.name),None)
        path_edges={(p.source_pad,p.target_pad) for p in routed.paths} if routed else set()
        # Only coincident lands are connected by existing pad copper. Separate
        # lands with the same electrical number still require emitted tracks.
        names={f"{r}.{p}":pads[(r,p)] for r,p in expected[net.name]}
        groups={}
        for name,point in names.items():groups.setdefault((point.x_mm,point.y_mm),set()).add(name)
        vertices=set(names);reached=set(next(iter(groups.values()))) if groups else set()
        changed=True
        while changed:
            changed=False
            for a,b in path_edges:
                if a in reached and b not in reached: reached.add(b);changed=True
                if b in reached and a not in reached: reached.add(a);changed=True
            for group in groups.values():
                if reached & group and not group <= reached: reached |= group;changed=True
        geometry_ok=all(_path_continuous(path,pads) for path in (routed.paths if routed else []))
        if reached!=vertices or not geometry_ok:
            connected_ok=False;open_nets.append(net.name)
    add("PB-ROUTE-001",connected_ok,"all required pads on every net are connected by continuous copper",open_nets)
    shorts=[]
    tracks=plan.tracks
    clearance=float(plan.profile.clearance_mm.value)
    for i,a in enumerate(tracks):
        for b in tracks[i+1:]:
            if a.net_name==b.net_name or a.layer!=b.layer: continue
            if _segments_distance(a.start,a.end,b.start,b.end) < (a.width_mm+b.width_mm)/2+clearance-1e-6:
                shorts.append(f"{a.net_name}/{b.net_name}")
    for via in plan.vias:
        for track in tracks:
            if track.net_name==via.net_name:continue
            if _point_segment_distance(via.position,track.start,track.end) < via.diameter_mm/2+track.width_mm/2+clearance-1e-6:
                shorts.append(f"{via.net_name}/{track.net_name}")
    for i,a in enumerate(plan.vias):
        for b in plan.vias[i+1:]:
            if a.net_name!=b.net_name and math.hypot(a.position.x_mm-b.position.x_mm,a.position.y_mm-b.position.y_mm) < (a.diameter_mm+b.diameter_mm)/2+clearance-1e-6:
                shorts.append(f"{a.net_name}/{b.net_name}")
    shorts.extend(_pad_clearance_violations(pcb,board,plan,clearance))
    add("PB-ROUTE-002",not shorts,"no copper geometry joins foreign pads or violates inter-net clearance",sorted(set(shorts)))
    add("PB-ROUTE-007",not shorts,"routes avoid foreign-net, unassigned, and mechanical pad obstacles",sorted(set(shorts)))
    return RoutingVerificationReport(plan_fingerprint=plan.content_hash,findings=findings)


def _net_binding_errors(plan, expected, pads):
    """Bind physical paths to electrical intent before accepting geometry.

    Coincident pad aliases may be represented by any one of their identities,
    but separate lands of the same numbered terminal must each be declared.
    A net occupying at most one physical location needs no routing container.
    """
    errors=set();seen=set()
    for routed in plan.routed_nets:
        name=routed.net_name
        if name in seen or name not in expected:
            errors.add(name)
        seen.add(name)
        terminals={f"{ref}.{pin}":pads[(ref,pin)] for ref,pin in expected.get(name,())}
        declared=set(routed.terminal_pads)
        if len(declared)!=len(routed.terminal_pads) or not declared<=terminals.keys():
            errors.add(name)
        required_locations={(point.x_mm,point.y_mm) for point in terminals.values()}
        declared_locations={(terminals[key].x_mm,terminals[key].y_mm)
                            for key in declared if key in terminals}
        if declared_locations!=required_locations:
            errors.add(name)
        for path in routed.paths:
            if path.source_pad not in terminals or path.target_pad not in terminals:
                errors.add(name)
            if any(copper.net_name!=name for copper in path.tracks+path.vias):
                errors.add(name)
    for name,keys in expected.items():
        if name not in seen and len({(pads[key].x_mm,pads[key].y_mm) for key in keys})>1:
            errors.add(name)
    return errors


def _pad_clearance_violations(pcb,board,plan,clearance):
    """Check entire copper segments against every physical pad, not route nodes.

    Pad rectangles conservatively enclose round/oval/roundrect land copper.
    Work in the pad's local coordinates so rotated footprints retain their
    real envelope. Unused pins and mechanical lands remain obstacles even
    when they have no electrical terminal or routed-net container.
    """
    placements={place.component_ref:place for place in board.placements}
    net_by_pad={(binding.component_ref,binding.pad_number):binding.net_name
                for binding in pcb.compilation.pad_bindings}
    violations=set();tracks=plan.tracks;vias=plan.vias
    for binding in pcb.compilation.footprint_bindings:
        ref=binding.component_ref;place=placements[ref]
        angle=math.radians(place.rotation_deg);cos=math.cos(angle);sin=math.sin(angle)
        for pad in footprint(binding.footprint_id).pads:
            net=net_by_pad.get((ref,pad.number))
            layers={"F.Cu","B.Cu"} if pad.kind=="thru_hole" else {"F.Cu"}
            label=f"{ref}.{pad.number}"
            def local(point,place=place,pad=pad,cos=cos,sin=sin):
                x=point.x_mm-place.x_mm;y=point.y_mm-place.y_mm
                return Point(x_mm=x*cos+y*sin-pad.x_mm,y_mm=-x*sin+y*cos-pad.y_mm)
            for track in tracks:
                if track.net_name==net or track.layer not in layers:continue
                distance=_segment_rectangle_distance(local(track.start),local(track.end),
                                                       pad.width_mm/2,pad.height_mm/2)
                if distance<clearance+track.width_mm/2-1e-6:
                    violations.add(f"{track.net_name}/{label}")
            for via in vias:
                if via.net_name==net:continue
                point=local(via.position)
                distance=_segment_rectangle_distance(point,point,pad.width_mm/2,pad.height_mm/2)
                if distance<clearance+via.diameter_mm/2-1e-6:
                    violations.add(f"{via.net_name}/{label}")
    return sorted(violations)


def _segment_rectangle_distance(start,end,half_width,half_height):
    if any(abs(point.x_mm)<=half_width and abs(point.y_mm)<=half_height for point in (start,end)):
        return 0.0
    corners=[Point(x_mm=x,y_mm=y) for x,y in ((-half_width,-half_height),
        (half_width,-half_height),(half_width,half_height),(-half_width,half_height))]
    return min(_segments_distance(start,end,corners[i],corners[(i+1)%4]) for i in range(4))


def _path_continuous(path,pads):
    if not path.tracks:return False
    source_key=tuple(path.source_pad.split(".",1));target_key=tuple(path.target_pad.split(".",1))
    source=pads.get(source_key);target=pads.get(target_key)
    if source is None or target is None:return False
    # Build endpoint/layer graph from actual tracks and vias, not route intent.
    graph={}
    def edge(a,b):graph.setdefault(a,set()).add(b);graph.setdefault(b,set()).add(a)
    for track in path.tracks:
        a=(round(track.start.x_mm,6),round(track.start.y_mm,6),track.layer);b=(round(track.end.x_mm,6),round(track.end.y_mm,6),track.layer);edge(a,b)
    for via in path.vias:
        a=(round(via.position.x_mm,6),round(via.position.y_mm,6),via.source_layer);b=(a[0],a[1],via.destination_layer);edge(a,b)
    starts=[n for n in graph if n[2]=="F.Cu" and math.hypot(n[0]-source.x_mm,n[1]-source.y_mm)<1e-5]
    goals={n for n in graph if n[2]=="F.Cu" and math.hypot(n[0]-target.x_mm,n[1]-target.y_mm)<1e-5}
    seen=set(starts);stack=list(starts)
    while stack:
        node=stack.pop()
        for nxt in graph.get(node,()):
            if nxt not in seen:seen.add(nxt);stack.append(nxt)
    return bool(seen & goals)


def _segments_distance(a,b,c,d):
    if _intersect(a,b,c,d):return 0.0
    return min(_point_segment_distance(a,c,d),_point_segment_distance(b,c,d),_point_segment_distance(c,a,b),_point_segment_distance(d,a,b))


def _intersect(a,b,c,d):
    def orient(p,q,r):return (q.x_mm-p.x_mm)*(r.y_mm-p.y_mm)-(q.y_mm-p.y_mm)*(r.x_mm-p.x_mm)
    def on(p,q,r):return min(p.x_mm,r.x_mm)-1e-9<=q.x_mm<=max(p.x_mm,r.x_mm)+1e-9 and min(p.y_mm,r.y_mm)-1e-9<=q.y_mm<=max(p.y_mm,r.y_mm)+1e-9
    o1,o2,o3,o4=orient(a,b,c),orient(a,b,d),orient(c,d,a),orient(c,d,b)
    if o1*o2<0 and o3*o4<0:return True
    return (abs(o1)<1e-9 and on(a,c,b)) or (abs(o2)<1e-9 and on(a,d,b)) or (abs(o3)<1e-9 and on(c,a,d)) or (abs(o4)<1e-9 and on(c,b,d))
