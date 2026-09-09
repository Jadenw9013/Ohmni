"""A bounded deterministic two-layer grid router.

The router proposes copper.  It does not certify the result; verifier.py does.
"""

from __future__ import annotations

import hashlib
import heapq
import math
from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise
from time import monotonic

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


class _RoutingInterrupted(Exception):
    def __init__(self, detail: str):
        super().__init__(detail)
        self.expanded_nodes = 0


class DeterministicRouter:
    """Deterministic A* router with fixed ordering and explicit search bounds."""

    def route(self, circuit: CircuitIR, pcb: PcbArtifact, board: BoardConstraints,
              constraints: RoutingConstraints | None = None, *,
              time_budget_seconds: float | None = None,
              clock: Callable[[], float] = monotonic,
              cancelled: Callable[[], bool] | None = None) -> RoutingPlan:
        if not pcb.lineage_is_current:
            raise ValueError("placed PCB lineage is stale")
        if pcb.circuit_content_hash != circuit.content_hash or pcb.constraints_hash != board.content_hash:
            raise ValueError("routing inputs do not match placed PCB lineage")
        constraints = RoutingConstraints.model_validate((constraints or RoutingConstraints()).model_dump())
        if time_budget_seconds is not None and (isinstance(time_budget_seconds, bool)
                or not math.isfinite(time_budget_seconds) or time_budget_seconds < 0):
            raise ValueError("routing time budget must be finite and nonnegative")
        deadline = None if time_budget_seconds is None else clock() + time_budget_seconds
        def checkpoint():
            if cancelled is not None and cancelled():
                raise _RoutingInterrupted("routing cancelled before all connections were completed")
            if deadline is not None and clock() >= deadline:
                raise _RoutingInterrupted("routing wall-clock budget exhausted before all connections were completed")
        check = checkpoint if deadline is not None or cancelled is not None else None
        profile = constraints.profile
        unknown = {net.net_name for net in constraints.nets} - {net.name for net in circuit.nets}
        if unknown:
            raise ValueError(f"routing constraints reference unknown nets: {sorted(unknown)}")
        unsupported = [place.component_ref for place in board.placements
                       if place.side != "F.Cu" or not math.isfinite(place.rotation_deg)
                       or not math.isclose(place.rotation_deg % 90, 0, abs_tol=1e-9)]
        if unsupported:
            return self._unsupported_plan(circuit, pcb, board, constraints, unsupported)
        per_net = {net.net_name: net for net in constraints.nets}
        def width_for(name):
            specified = per_net.get(name)
            return float(specified.width_mm if specified and specified.width_mm is not None
                         else profile.power_width_mm.value if self._power(name) else profile.signal_width_mm.value)
        events=[_event(circuit,EventKind.ROUTING_STARTED,"Deterministic routing started"),_event(circuit,EventKind.ROUTING_PROFILE_SELECTED,f"Routing profile selected: {profile.name}",{"profile_hash":profile.content_hash})]
        pads = self._pad_centres(pcb, board)
        access = self._pad_access(pcb, board, pads, profile)
        terminal_keys = self._terminal_keys(pcb)
        net_pads = {}
        for net in circuit.nets:
            unique = {}
            for pin in sorted(net.connections, key=lambda p: (p.component, p.pin)):
                for key in terminal_keys[(pin.component, pin.pin)]:
                    point = pads[key]
                    unique.setdefault((point.x_mm, point.y_mm), (f"{key[0]}.{key[1]}", point, access[key]))
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
        for net in circuit.nets:
            for pin in net.connections:
                for key in terminal_keys[(pin.component, pin.pin)]:
                    actual=pads[key];entry=access[key]
                    if actual != entry: occupied.setdefault(net.name,[]).append((actual,entry,"F.Cu",width_for(net.name)))
        routed: list[RoutedNet] = []
        failures: list[RoutingFailure] = []
        expanded_total = attempts = 0
        interrupted = None
        for net_name in route_order:
            terminals = net_pads[net_name]
            try:
                if interrupted is None and check is not None: check()
            except _RoutingInterrupted as exc:
                interrupted = str(exc)
            if interrupted is not None:
                failures.append(RoutingFailure(net_name=net_name, reason=RoutingFailureReason.ROUTING_INCOMPLETE,
                                               detail=interrupted))
                routed.append(RoutedNet(net_name=net_name, terminal_pads=[p[0] for p in terminals], paths=[]))
                continue
            events.append(_event(circuit,EventKind.NET_ROUTING_STARTED,f"Routing net {net_name}",{"net_name":net_name}))
            if len(terminals) < 2:
                routed.append(RoutedNet(net_name=net_name, terminal_pads=[p[0] for p in terminals], paths=[]))
                continue
            connected = [terminals[0]]
            remaining = terminals[1:]
            paths: list[RoutePath] = []
            while remaining:
                target = min(remaining, key=lambda p: min((self._distance(p[1], q[1]), q[0]) for q in connected))
                source = min(connected, key=lambda p: (self._distance(p[1], target[1]), p[0]))
                try:
                    if check is not None: check()
                    attempts += 1
                    preferred = per_net.get(net_name)
                    result = self._find(net_name, source[2], target[2], board, profile, all_pad_obstacles, occupied,
                                        check=check, width_mm=width_for(net_name),
                                        preferred_layer=preferred.preferred_layer if preferred else None)
                except _RoutingInterrupted as exc:
                    expanded_total += exc.expanded_nodes
                    interrupted = str(exc)
                    failures.append(RoutingFailure(net_name=net_name, reason=RoutingFailureReason.ROUTING_INCOMPLETE,
                                                   detail=interrupted))
                    break
                if result is None:
                    failures.append(RoutingFailure(net_name=net_name, reason=RoutingFailureReason.NO_PATH,
                                                   detail=f"no bounded path from {source[0]} to {target[0]}"))
                    events.append(_event(circuit,EventKind.ROUTE_SEARCH_FAILED,f"Route search failed for {net_name}",{"source":source[0],"target":target[0]}))
                    break
                states, expanded = result
                expanded_total += expanded
                path = self._to_path(net_name, source, target, states, profile, attempts, width_mm=width_for(net_name))
                if _path_crosses_keepout(path, board):
                    failures.append(RoutingFailure(net_name=net_name, reason=RoutingFailureReason.BOARD_CONSTRAINT_VIOLATION,
                                                   detail="pad access or emitted copper enters a declared copper keepout"))
                    break
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
            routed_net_count=sum(1 for n in routed if len(n.paths) == max(0, len(n.terminal_pads)-1)
                                 and n.net_name not in {failure.net_name for failure in failures}),
            unresolved_net_count=len(failures), track_segment_count=len(tracks), via_count=len(vias),
            total_track_length_mm=round(sum(t.length_mm for t in tracks), 6), expanded_nodes=expanded_total,
            routing_attempts=attempts, route_order=route_order,
        )
        events.append(_event(circuit,EventKind.ROUTING_COMPLETED,
                             "Routing stopped before completion" if interrupted else "Deterministic routing completed",
                             {"routed_nets":stats.routed_net_count,"unresolved_nets":stats.unresolved_net_count}))
        return RoutingPlan(source_pcb_fingerprint=pcb.fingerprint.digest,source_pcb_path=pcb.path,
                           source_constraints_hash=board.content_hash,
                           circuit_content_hash=circuit.content_hash, profile=profile,
                           routed_nets=routed, failures=failures, statistics=stats,events=events,
                           net_constraints=constraints.nets)

    @staticmethod
    def _unsupported_plan(circuit, pcb, board, constraints, refs):
        names = sorted(net.name for net in circuit.nets)
        routed = [RoutedNet(net_name=net.name, terminal_pads=[str(pin) for pin in net.connections], paths=[])
                  for net in sorted(circuit.nets, key=lambda item: item.name)]
        detail = f"Only front-side orthogonal placements can be routed; unsupported components: {', '.join(refs)}"
        return RoutingPlan(source_pcb_fingerprint=pcb.fingerprint.digest, source_pcb_path=pcb.path,
                           source_constraints_hash=board.content_hash, circuit_content_hash=circuit.content_hash,
                           profile=constraints.profile, net_constraints=constraints.nets, routed_nets=routed,
                           failures=[RoutingFailure(net_name=name, reason=RoutingFailureReason.UNSUPPORTED_GEOMETRY,
                                                    detail=detail) for name in names],
                           statistics=RoutingStatistics(required_connections=sum(max(0,len(net.connections)-1) for net in circuit.nets),
                               routed_net_count=0, unresolved_net_count=len(names), track_segment_count=0, via_count=0,
                               total_track_length_mm=0, expanded_nodes=0, routing_attempts=0, route_order=names))

    @staticmethod
    def _power(name: str) -> bool:
        return name.upper() in {"GND", "VBUS", "+5V", "+3V3", "3V3"} or "VDD" in name.upper()

    @staticmethod
    def _distance(a: Point, b: Point) -> float:
        return abs(a.x_mm-b.x_mm)+abs(a.y_mm-b.y_mm)

    @staticmethod
    def _physical_pads(pcb):
        """Enumerate every physical land, including repeated electrical numbers.

        The first land retains the historical component/pin key. Further lands
        use a stable footprint-order suffix, e.g. SW1.1#2. A switch's internal
        contact does not substitute for a copper connection in a PCB artifact.
        """
        fps = {binding.component_ref: footprint(binding.footprint_id)
               for binding in pcb.compilation.footprint_bindings}
        for binding in pcb.compilation.pad_bindings:
            physical = [pad for pad in fps[binding.component_ref].pads if pad.number == binding.pad_number]
            if not physical:
                raise ValueError(f"no physical pad for {binding.component_ref}.{binding.pin_number}")
            for ordinal, pad in enumerate(physical, start=1):
                identity = binding.pin_number if ordinal == 1 else f"{binding.pin_number}#{ordinal}"
                yield (binding.component_ref, identity), binding, pad

    @staticmethod
    def _terminal_keys(pcb):
        result = {}
        for key, binding, _pad in DeterministicRouter._physical_pads(pcb):
            result.setdefault((binding.component_ref, binding.pin_number), []).append(key)
        return result

    @staticmethod
    def _pad_centres(pcb: PcbArtifact, board: BoardConstraints) -> dict[tuple[str, str], Point]:
        places = {p.component_ref: p for p in board.placements}
        result = {}
        for key, binding, pad in DeterministicRouter._physical_pads(pcb):
            place = places[binding.component_ref]
            angle = math.radians(place.rotation_deg)
            x = place.x_mm + pad.x_mm*math.cos(angle) - pad.y_mm*math.sin(angle)
            y = place.y_mm + pad.x_mm*math.sin(angle) + pad.y_mm*math.cos(angle)
            result[key] = Point(x_mm=round(x, 6), y_mm=round(y, 6))
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
                rotated = round(place.rotation_deg / 90) % 2
                width, height = (pad.height_mm, pad.width_mm) if rotated else (pad.width_mm, pad.height_mm)
                result.append((net_by_pad.get((ref,pad.number)),point,width,height,layers))
        for region in _copper_keepouts(board):
            result.append((None, Point(x_mm=(region.x_min_mm+region.x_max_mm)/2,
                                       y_mm=(region.y_min_mm+region.y_max_mm)/2),
                           region.x_max_mm-region.x_min_mm, region.y_max_mm-region.y_min_mm,
                           ("F.Cu", "B.Cu")))
        return result

    @staticmethod
    def _pad_access(pcb, board, centres, profile):
        placements = {place.component_ref: place for place in board.placements}
        grid=float(profile.grid_mm.value);result={}
        for key, binding, pad in DeterministicRouter._physical_pads(pcb):
            centre=centres[key]
            if pad.kind=="thru_hole":result[key]=centre;continue
            if abs(pad.x_mm)>=abs(pad.y_mm):
                dx=(1 if pad.x_mm>=0 else -1)*(pad.width_mm/2+.25);dy=0
            else:
                dx=0;dy=(1 if pad.y_mm>=0 else -1)*(pad.height_mm/2+.25)
            turn = round(placements[binding.component_ref].rotation_deg / 90) % 4
            dx, dy = ((dx,dy),(-dy,dx),(-dx,-dy),(dy,-dx))[turn]
            x=centre.x_mm+dx;y=centre.y_mm+dy
            result[key]=Point(x_mm=round(x/grid)*grid,y_mm=round(y/grid)*grid)
        return result

    def _find(self, net, start, goal, board, profile, pads, occupied, *, check=None,
              width_mm=None, preferred_layer=None):
        from .spatial import RoutingObstacles

        grid = float(profile.grid_mm.value)
        edge = float(profile.edge_clearance_mm.value)
        max_nodes = int(profile.maximum_expanded_nodes.value)
        max_vias = int(profile.maximum_vias_per_connection.value)
        width = float(width_mm if width_mm is not None else profile.power_width_mm.value if self._power(net) else profile.signal_width_mm.value)
        preferred = (1 if self._power(net) else 0) if preferred_layer is None else ("F.Cu", "B.Cu").index(preferred_layer)
        def inside(x,y,radius):
            inset=edge+radius
            return (inset-1e-6<=x<=board.outline.width_mm-inset+1e-6
                    and inset-1e-6<=y<=board.outline.height_mm-inset+1e-6)
        if not all(inside(point.x_mm,point.y_mm,width/2) for point in (start,goal)):
            return None
        obstacles = RoutingObstacles(net, profile, pads, occupied)
        blocked_cache: dict[tuple[int, int, int, float], bool] = {}

        def blocked(state, layer, radius):
            key = (state.x, state.y, layer, radius)
            result = blocked_cache.get(key)
            if result is None:
                result = obstacles.blocked(Point(x_mm=state.x * grid, y_mm=state.y * grid), layer, radius)
                blocked_cache[key] = result
            return result

        sx, sy = round(start.x_mm/grid), round(start.y_mm/grid)
        gx, gy = round(goal.x_mm/grid), round(goal.y_mm/grid)
        if not all(inside(x*grid,y*grid,width/2) for x,y in ((sx,sy),(gx,gy))):
            return None
        starts = [_State(sx, sy, 0)]
        targets = {_State(gx, gy, 0)}
        queue = []
        serial = 0
        for state in starts:
            heapq.heappush(queue, (0, 0, state.x, state.y, state.layer, serial, state)); serial += 1
        came = {}; cost = {starts[0]: 0.0}; via_counts = {starts[0]: 0}; expanded = 0
        while queue and expanded < max_nodes:
            if check is not None:
                try: check()
                except _RoutingInterrupted as exc:
                    exc.expanded_nodes = expanded
                    raise
            _, g, *_rest, current = heapq.heappop(queue)
            if g != cost.get(current): continue
            expanded += 1
            if current in targets:
                path = [current]
                while current in came:
                    current = came[current]; path.append(current)
                path.reverse()
                if sum(a.layer != b.layer for a,b in pairwise(path)) <= max_vias:
                    return path, expanded
                continue
            neighbours = [(_State(current.x+1,current.y,current.layer),1.0),(_State(current.x,current.y+1,current.layer),1.0),
                          (_State(current.x-1,current.y,current.layer),1.0),(_State(current.x,current.y-1,current.layer),1.0),
                          (_State(current.x,current.y,1-current.layer),12.0)]
            for nxt, step in neighbours:
                via_count = via_counts[current] + (nxt.layer != current.layer)
                if via_count > max_vias: continue
                if nxt.layer != preferred: step += 2.0
                new = g+step
                if new >= cost.get(nxt, float("inf")): continue
                candidate_radius=float(profile.via_diameter_mm.value)/2 if nxt.layer!=current.layer else width/2
                if not inside(nxt.x*grid,nxt.y*grid,candidate_radius): continue
                if blocked(nxt, nxt.layer, candidate_radius): continue
                if nxt.layer!=current.layer and blocked(nxt, current.layer, candidate_radius): continue
                cost[nxt]=new;came[nxt]=current;via_counts[nxt]=via_count
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
    def _to_path(net, source, target, states, profile, attempt, *, width_mm=None):
        grid=float(profile.grid_mm.value); width=float(width_mm if width_mm is not None else profile.power_width_mm.value if DeterministicRouter._power(net) else profile.signal_width_mm.value)
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


def _copper_keepouts(board):
    constraints = [constraint for constraint in board.placement_constraints
                   if constraint.kind.value == "keepout"]
    if not constraints:
        return []
    from ..physical.rules import resolved_keepout_region
    places = {place.component_ref: place for place in board.placements}
    return [resolved_keepout_region(constraint, places) for constraint in constraints]


def _segment_in_keepout(start, end, region, radius=0.0):
    """Exact segment intersection with a rectangle expanded by copper radius."""
    lower, upper = 0.0, 1.0
    for a, b, minimum, maximum in (
        (start.x_mm, end.x_mm, region.x_min_mm-radius, region.x_max_mm+radius),
        (start.y_mm, end.y_mm, region.y_min_mm-radius, region.y_max_mm+radius),
    ):
        delta = b-a
        if abs(delta) < 1e-12:
            if a < minimum or a > maximum: return False
            continue
        first, last = sorted(((minimum-a)/delta, (maximum-a)/delta))
        lower, upper = max(lower,first), min(upper,last)
        if lower > upper: return False
    return True


def _path_crosses_keepout(path, board):
    regions = _copper_keepouts(board)
    return any(_segment_in_keepout(track.start, track.end, region, track.width_mm/2)
               for track in path.tracks for region in regions) or any(
                   _segment_in_keepout(via.position, via.position, region, via.diameter_mm/2)
                   for via in path.vias for region in regions)


def _id(seed, suffix): return hashlib.sha256(f"{seed}:{suffix}".encode()).hexdigest()[:20]
def _event(circuit,kind,summary,payload=None):
    identity=f"{kind.value}:{summary}:{payload!r}";return EngineeringEvent(event_id=hashlib.sha256(identity.encode()).hexdigest()[:16],kind=kind,summary=summary,circuit_content_hash=circuit.content_hash,payload=payload or {})
def _collinear(a,b,c): return abs((b.x_mm-a.x_mm)*(c.y_mm-b.y_mm)-(b.y_mm-a.y_mm)*(c.x_mm-b.x_mm)) < 1e-9
def _point_segment_distance(p,a,b):
    dx=b.x_mm-a.x_mm;dy=b.y_mm-a.y_mm
    if dx==dy==0:return math.hypot(p.x_mm-a.x_mm,p.y_mm-a.y_mm)
    t=max(0,min(1,((p.x_mm-a.x_mm)*dx+(p.y_mm-a.y_mm)*dy)/(dx*dx+dy*dy)))
    return math.hypot(p.x_mm-(a.x_mm+t*dx),p.y_mm-(a.y_mm+t*dy))
