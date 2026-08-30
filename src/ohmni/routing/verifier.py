"""Independent verification of emitted copper geometry."""

from __future__ import annotations

import math

from ..domain import CircuitIR
from ..eda.pcb_models import PcbArtifact
from ..physical.models import BoardConstraints
from .models import RoutingFinding, RoutingPlan, RoutingRuleStatus, RoutingVerificationReport
from .router import DeterministicRouter, _point_segment_distance


def verify_routing(circuit: CircuitIR, pcb: PcbArtifact, board: BoardConstraints,
                   plan: RoutingPlan) -> RoutingVerificationReport:
    findings=[]
    def add(rule, ok, text, nets=()):
        findings.append(RoutingFinding(rule_id=rule,status=RoutingRuleStatus.PASS if ok else RoutingRuleStatus.FAIL,description=text,net_names=list(nets)))
    known={n.name for n in circuit.nets}
    refs_ok=(plan.circuit_content_hash==circuit.content_hash and plan.source_pcb_fingerprint==pcb.fingerprint.digest and plan.source_constraints_hash==board.content_hash)
    copper_nets={x.net_name for x in plan.tracks+plan.vias}
    add("PB-ROUTE-003",refs_ok and copper_nets<=known,"all copper references valid lineage and semantic nets",copper_nets-known)
    edge=float(plan.profile.edge_clearance_mm.value)
    inside=all(edge<=p.x_mm<=board.outline.width_mm-edge and edge<=p.y_mm<=board.outline.height_mm-edge for t in plan.tracks for p in (t.start,t.end)) and all(edge<=v.position.x_mm<=board.outline.width_mm-edge and edge<=v.position.y_mm<=board.outline.height_mm-edge for v in plan.vias)
    add("PB-ROUTE-004",inside,"all route geometry remains within routing bounds")
    min_signal=float(plan.profile.signal_width_mm.value)
    widths=all(t.width_mm>=min_signal for t in plan.tracks)
    add("PB-ROUTE-005",widths,"track widths satisfy the active routing profile")
    vd=float(plan.profile.via_diameter_mm.value);dr=float(plan.profile.via_drill_mm.value)
    vias_ok=all(v.diameter_mm>=vd and v.drill_mm>=dr and v.drill_mm<v.diameter_mm and {v.source_layer,v.destination_layer}=={"F.Cu","B.Cu"} for v in plan.vias)
    add("PB-ROUTE-006",vias_ok,"through-via dimensions and layers satisfy the active profile")
    max_vias=int(plan.profile.maximum_vias_per_connection.value)
    via_counts_ok=all(len(path.vias)<=max_vias for net in plan.routed_nets for path in net.paths)
    add("PB-ROUTE-008",via_counts_ok,"via count remains within the bounded policy")
    pads=DeterministicRouter._pad_centres(pcb,board)
    expected={n.name:{(p.component,p.pin) for p in n.connections} for n in circuit.nets}
    connected_ok=True;open_nets=[]
    for net in circuit.nets:
        routed=next((n for n in plan.routed_nets if n.net_name==net.name),None)
        path_edges={(p.source_pad,p.target_pad) for p in routed.paths} if routed else set()
        # Pads sharing identical copper coordinates (notably duplicated USB-C A/B
        # power contacts) are already physically connected by the pad copper.
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
    add("PB-ROUTE-002",not shorts,"no copper geometry joins or violates clearance between semantic nets",sorted(set(shorts)))
    add("PB-ROUTE-007",not shorts,"routes avoid prohibited other-net copper obstacles",sorted(set(shorts)))
    return RoutingVerificationReport(plan_fingerprint=plan.content_hash,findings=findings)


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
