"""A bounded deterministic two-layer grid router.

The router proposes copper.  It does not certify the result; verifier.py does.
"""

from __future__ import annotations

import hashlib
import heapq
import math
from dataclasses import dataclass

from ..domain import CircuitIR, EngineeringEvent, EventKind
from ..eda.pcb_models import PcbArtifact
from ..physical.footprints import footprint
from ..physical.models import BoardConstraints
from .models import (
    Point,
    RoutedNet,
    RoutePath,
    RoutingConstraints,
    RoutingFailure,
    RoutingFailureReason,
    RoutingPlan,
    RoutingStatistics,
    TrackSegment,
    Via,
)


@dataclass(frozen=True, order=True)
class _State:
    x: int
    y: int
    layer: int


class DeterministicRouter:
    """Deterministic A* router with fixed ordering and explicit search bounds."""

    def route(self, circuit: CircuitIR, pcb: PcbArtifact, board: BoardConstraints,
              constraints: RoutingConstraints | None = None) -> RoutingPlan:
        if not pcb.lineage_is_current:
            raise ValueError("placed PCB lineage is stale")
        if pcb.circuit_content_hash != circuit.content_hash or pcb.constraints_hash != board.content_hash:
            raise ValueError("routing inputs do not match placed PCB lineage")
        constraints = constraints or RoutingConstraints()
        profile = constraints.profile
        events=[_event(circuit,EventKind.ROUTING_STARTED,"Deterministic routing started"),_event(circuit,EventKind.ROUTING_PROFILE_SELECTED,f"Routing profile selected: {profile.name}",{"profile_hash":profile.content_hash})]
        pads = self._pad_centres(pcb, board)
        access = self._pad_access(pcb, board, pads, profile)
        net_pads = {}
        for net in circuit.nets:
            unique = {}
            for pin in sorted(net.connections, key=lambda p: (p.component, p.pin)):
                point = pads[(pin.component, pin.pin)]
                unique.setdefault((point.x_mm, point.y_mm), (f"{pin.component}.{pin.pin}", point, access[(pin.component,pin.pin)]))
            net_pads[net.name] = list(unique.values())
        # Route short/constrained nets before large power trees after reserving
        # every pad breakout. Stable names resolve ties. This is topology
        # priority, not a signal-integrity claim.
        def priority(name):
            role={"SDA":0,"SCL":1,"GND":2,"3V3":3,"VBUS":4}
            if name.upper() in role:return (role[name.upper()],name)
            if len(net_pads[name]) == 2:return (5,name)
            return (6,name)
        route_order = sorted(net_pads, key=priority)
        all_pad_obstacles = self._pad_obstacles(pcb, board, pads)
        # Reserve every pad breakout before routing any net. This prevents an
        # early route from sealing a later net's only legal pad-access corridor.
        occupied: dict[str, list[tuple[Point, Point, str, float]]] = {}
        default_width=float(profile.signal_width_mm.value)
        for net in circuit.nets:
            for pin in net.connections:
                actual=pads[(pin.component,pin.pin)];entry=access[(pin.component,pin.pin)]
                if actual != entry: occupied.setdefault(net.name,[]).append((actual,entry,"F.Cu",default_width))
        routed: list[RoutedNet] = []
        failures: list[RoutingFailure] = []
        expanded_total = attempts = 0
        for net_name in route_order:
            events.append(_event(circuit,EventKind.NET_ROUTING_STARTED,f"Routing net {net_name}",{"net_name":net_name}))
            terminals = net_pads[net_name]
            if len(terminals) < 2:
                routed.append(RoutedNet(net_name=net_name, terminal_pads=[p[0] for p in terminals], paths=[]))
                continue
            connected = [terminals[0]]
            remaining = terminals[1:]
            paths: list[RoutePath] = []
            while remaining:
                target = min(remaining, key=lambda p: min((self._distance(p[1], q[1]), q[0]) for q in connected))
                source = min(connected, key=lambda p: (self._distance(p[1], target[1]), p[0]))
                attempts += 1
                result = self._find(net_name, source[2], target[2], board, profile, all_pad_obstacles, occupied)
                if result is None:
                    failures.append(RoutingFailure(net_name=net_name, reason=RoutingFailureReason.NO_PATH,
                                                   detail=f"no bounded path from {source[0]} to {target[0]}"))
                    events.append(_event(circuit,EventKind.ROUTE_SEARCH_FAILED,f"Route search failed for {net_name}",{"source":source[0],"target":target[0]}))
                    break
                states, expanded = result
                expanded_total += expanded
                path = self._to_path(net_name, source, target, states, profile, attempts)
                paths.append(path)
                events.append(_event(circuit,EventKind.ROUTE_FOUND,f"Route found for {net_name}",{"source":source[0],"target":target[0],"tracks":len(path.tracks),"vias":len(path.vias)}))
                for via in path.vias: events.append(_event(circuit,EventKind.VIA_INSERTED,f"Through-via inserted for {net_name}",{"via_id":via.via_id,"x_mm":via.position.x_mm,"y_mm":via.position.y_mm}))
                for track in path.tracks:
                    occupied.setdefault(net_name, []).append((track.start, track.end, track.layer, track.width_mm))
                for via in path.vias:
                    occupied.setdefault(net_name, []).append((via.position,via.position,"F.Cu",via.diameter_mm))
                    occupied.setdefault(net_name, []).append((via.position,via.position,"B.Cu",via.diameter_mm))
                connected.append(target)
                remaining.remove(target)
            routed.append(RoutedNet(net_name=net_name, terminal_pads=[p[0] for p in terminals], paths=paths))
        tracks = [t for n in routed for p in n.paths for t in p.tracks]
        vias = [v for n in routed for p in n.paths for v in p.vias]
        stats = RoutingStatistics(
            required_connections=sum(max(0, len(p)-1) for p in net_pads.values()),
            routed_net_count=sum(1 for n in routed if len(n.paths) == max(0, len(n.terminal_pads)-1)),
            unresolved_net_count=len(failures), track_segment_count=len(tracks), via_count=len(vias),
            total_track_length_mm=round(sum(t.length_mm for t in tracks), 6), expanded_nodes=expanded_total,
            routing_attempts=attempts, route_order=route_order,
        )
        events.append(_event(circuit,EventKind.ROUTING_COMPLETED,"Deterministic routing completed",{"routed_nets":stats.routed_net_count,"unresolved_nets":stats.unresolved_net_count}))
        return RoutingPlan(source_pcb_fingerprint=pcb.fingerprint.digest,source_pcb_path=pcb.path,
                           source_constraints_hash=board.content_hash,
                           circuit_content_hash=circuit.content_hash, profile=profile,
                           routed_nets=routed, failures=failures, statistics=stats,events=events)

    @staticmethod
    def _power(name: str) -> bool:
        return name.upper() in {"GND", "VBUS", "+5V", "+3V3", "3V3"} or "VDD" in name.upper()

    @staticmethod
    def _distance(a: Point, b: Point) -> float:
        return abs(a.x_mm-b.x_mm)+abs(a.y_mm-b.y_mm)

    @staticmethod
    def _pad_centres(pcb: PcbArtifact, board: BoardConstraints) -> dict[tuple[str, str], Point]:
        places = {p.component_ref: p for p in board.placements}
        fps = {b.component_ref: footprint(b.footprint_id) for b in pcb.compilation.footprint_bindings}
        result = {}
        for binding in pcb.compilation.pad_bindings:
            pad = next(p for p in fps[binding.component_ref].pads if p.number == binding.pad_number)
            place = places[binding.component_ref]
            angle = math.radians(place.rotation_deg)
            x = place.x_mm + pad.x_mm*math.cos(angle) - pad.y_mm*math.sin(angle)
            y = place.y_mm + pad.x_mm*math.sin(angle) + pad.y_mm*math.cos(angle)
            result[(binding.component_ref, binding.pin_number)] = Point(x_mm=round(x, 6), y_mm=round(y, 6))
        return result

    @staticmethod
    def _pad_obstacles(pcb, board, centres):
        fps = {b.component_ref: footprint(b.footprint_id) for b in pcb.compilation.footprint_bindings}
        places={p.component_ref:p for p in board.placements}
        net_by_pad={(b.component_ref,b.pad_number):b.net_name for b in pcb.compilation.pad_bindings}
        result = []
        for ref,fp in fps.items():
            place=places[ref];angle=math.radians(place.rotation_deg)
            for pad in fp.pads:
                x=place.x_mm+pad.x_mm*math.cos(angle)-pad.y_mm*math.sin(angle)
                y=place.y_mm+pad.x_mm*math.sin(angle)+pad.y_mm*math.cos(angle)
                point=Point(x_mm=round(x,6),y_mm=round(y,6))
                layers=("F.Cu","B.Cu") if pad.kind=="thru_hole" else ("F.Cu",)
                result.append((net_by_pad.get((ref,pad.number)),point,pad.width_mm,pad.height_mm,layers))
        return result

    @staticmethod
    def _pad_access(pcb, board, centres, profile):
        fps={b.component_ref:footprint(b.footprint_id) for b in pcb.compilation.footprint_bindings}
        grid=float(profile.grid_mm.value);result={}
        for binding in pcb.compilation.pad_bindings:
            fp=fps[binding.component_ref];pad=next(p for p in fp.pads if p.number==binding.pad_number)
            centre=centres[(binding.component_ref,binding.pin_number)]
            if pad.kind=="thru_hole":result[(binding.component_ref,binding.pin_number)]=centre;continue
            if abs(pad.x_mm)>=abs(pad.y_mm):
                direction=1 if pad.x_mm>=0 else -1;x=centre.x_mm+direction*(pad.width_mm/2+.25);y=centre.y_mm
            else:
                direction=1 if pad.y_mm>=0 else -1;x=centre.x_mm;y=centre.y_mm+direction*(pad.height_mm/2+.25)
            result[(binding.component_ref,binding.pin_number)]=Point(x_mm=round(x/grid)*grid,y_mm=round(y/grid)*grid)
        return result

    def _find(self, net, start, goal, board, profile, pads, occupied):
        grid = float(profile.grid_mm.value)
        edge = float(profile.edge_clearance_mm.value)
        max_nodes = int(profile.maximum_expanded_nodes.value)
        sx, sy = round(start.x_mm/grid), round(start.y_mm/grid)
        gx, gy = round(goal.x_mm/grid), round(goal.y_mm/grid)
        starts = [_State(sx, sy, 0)]
        targets = {_State(gx, gy, 0)}
        queue = []
        serial = 0
        for state in starts:
            heapq.heappush(queue, (0, 0, state.x, state.y, state.layer, serial, state)); serial += 1
        came = {}; cost = {starts[0]: 0.0}; expanded = 0
        while queue and expanded < max_nodes:
            _, g, *_rest, current = heapq.heappop(queue)
            if g != cost.get(current): continue
            expanded += 1
            if current in targets:
                path = [current]
                while current in came:
                    current = came[current]; path.append(current)
                return list(reversed(path)), expanded
            neighbours = [(_State(current.x+1,current.y,current.layer),1.0),(_State(current.x,current.y+1,current.layer),1.0),
                          (_State(current.x-1,current.y,current.layer),1.0),(_State(current.x,current.y-1,current.layer),1.0),
                          (_State(current.x,current.y,1-current.layer),12.0)]
            for nxt, step in neighbours:
                preferred=1 if self._power(net) else 0
                if nxt.layer != preferred: step += 2.0
                point = Point(x_mm=nxt.x*grid, y_mm=nxt.y*grid)
                if not (edge <= point.x_mm <= board.outline.width_mm-edge and edge <= point.y_mm <= board.outline.height_mm-edge): continue
                candidate_radius=float(profile.via_diameter_mm.value)/2 if nxt.layer!=current.layer else float(profile.signal_width_mm.value)/2
                if self._blocked(net, point, nxt.layer, profile, pads, occupied, start, goal, candidate_radius): continue
                if nxt.layer!=current.layer and self._blocked(net, point, current.layer, profile, pads, occupied, start, goal, candidate_radius): continue
                new = g+step
                if new >= cost.get(nxt, float("inf")): continue
                cost[nxt]=new;came[nxt]=current
                heuristic=abs(nxt.x-gx)+abs(nxt.y-gy)+(0 if nxt.layer==0 else 2)
                heapq.heappush(queue,(new+heuristic,new,nxt.x,nxt.y,nxt.layer,serial,nxt));serial+=1
        return None

    @staticmethod
    def _blocked(net, point, layer_index, profile, pads, occupied, start, goal, candidate_radius):
        layer=("F.Cu","B.Cu")[layer_index]
        clearance=float(profile.clearance_mm.value)+candidate_radius
        for pad_net,centre,w,h,layers in pads:
            if layer not in layers or pad_net==net: continue
            if abs(point.x_mm-centre.x_mm) <= w/2+clearance and abs(point.y_mm-centre.y_mm) <= h/2+clearance: return True
        for other,segments in occupied.items():
            for a,b,track_layer,width in segments:
                if track_layer != layer: continue
                if other==net:
                    if a==b and candidate_radius >= float(profile.via_diameter_mm.value)/2:
                        distance=math.hypot(point.x_mm-a.x_mm,point.y_mm-a.y_mm)
                        if 1e-9 < distance < float(profile.via_drill_mm.value)+.25:return True
                    continue
                radius=clearance+width/2
                if _point_segment_distance(point,a,b) < radius: return True
        return False

    @staticmethod
    def _to_path(net, source, target, states, profile, attempt):
        grid=float(profile.grid_mm.value); width=float(profile.power_width_mm.value if DeterministicRouter._power(net) else profile.signal_width_mm.value)
        attempt_id=f"route-{attempt:04d}-{net}"
        points=[(Point(x_mm=s.x*grid,y_mm=s.y*grid),("F.Cu","B.Cu")[s.layer]) for s in states]
        # Exact pad centres are copper-connected to their snapped access nodes.
        if source[2] != points[0][0]: points.insert(0,(source[2],points[0][1]))
        points.insert(0,(source[1],points[0][1]))
        if target[2] != points[-1][0]: points.append((target[2],points[-1][1]))
        points.append((target[1],points[-1][1]))
        tracks=[];vias=[];run_start=points[0]
        for index in range(1,len(points)):
            prev=points[index-1];cur=points[index]
            if prev[1] != cur[1]:
                vias.append(Via(via_id=_id(attempt_id,f"via:{index}"),net_name=net,position=prev[0],diameter_mm=float(profile.via_diameter_mm.value),drill_mm=float(profile.via_drill_mm.value),source_layer=prev[1],destination_layer=cur[1],attempt_id=attempt_id));run_start=cur;continue
            next_changes = index==len(points)-1 or points[index+1][1]!=cur[1] or not _collinear(run_start[0],cur[0],points[index+1][0])
            if next_changes and run_start[0] != cur[0]:
                tracks.append(TrackSegment(segment_id=_id(attempt_id,f"track:{len(tracks)}"),net_name=net,layer=cur[1],start=run_start[0],end=cur[0],width_mm=width,attempt_id=attempt_id));run_start=cur
        return RoutePath(source_pad=source[0],target_pad=target[0],tracks=tracks,vias=vias,expanded_nodes=0)


def _id(seed, suffix): return hashlib.sha256(f"{seed}:{suffix}".encode()).hexdigest()[:20]
def _event(circuit,kind,summary,payload=None):
    identity=f"{kind.value}:{summary}:{payload!r}";return EngineeringEvent(event_id=hashlib.sha256(identity.encode()).hexdigest()[:16],kind=kind,summary=summary,circuit_content_hash=circuit.content_hash,payload=payload or {})
def _collinear(a,b,c): return abs((b.x_mm-a.x_mm)*(c.y_mm-b.y_mm)-(b.y_mm-a.y_mm)*(c.x_mm-b.x_mm)) < 1e-9
def _point_segment_distance(p,a,b):
    dx=b.x_mm-a.x_mm;dy=b.y_mm-a.y_mm
    if dx==dy==0:return math.hypot(p.x_mm-a.x_mm,p.y_mm-a.y_mm)
    t=max(0,min(1,((p.x_mm-a.x_mm)*dx+(p.y_mm-a.y_mm)*dy)/(dx*dx+dy*dy)))
    return math.hypot(p.x_mm-(a.x_mm+t*dx),p.y_mm-(a.y_mm+t*dy))
