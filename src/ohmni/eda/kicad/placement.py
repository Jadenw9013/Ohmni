"""Explicit deterministic placement for the supported golden board."""

from ...physical.models import (
    BoardConstraints,
    BoardOutline,
    ComponentPlacement,
    PlacementConstraint,
    PlacementConstraintKind,
)


def golden_board_constraints() -> BoardConstraints:
    positions = {
        "J1": (50, 65, "USB-C connector accessible at board edge"),
        "R1": (45, 58, "CC1 termination near USB-C"), "R2": (55, 58, "CC2 termination near USB-C"),
        "U2": (20, 58, "regulator near power input"), "C1": (16, 58, "input bypass near regulator"),
        "C2": (24, 58, "output bypass near regulator"),
        "U1": (45, 35, "ESP32 central functional block"), "C3": (32, 35, "ESP32 local decoupling"),
        "C4": (58, 35, "ESP32 local decoupling"), "C5": (32, 27, "enable timing capacitor beside the full module body"),
        "U3": (80, 50, "sensor separated from regulator heat"), "C6": (76, 50, "BME280 VDD decoupling"),
        "C7": (84, 50, "BME280 VDDIO decoupling"), "R4": (76, 44, "I2C SDA pull-up near sensor bus"),
        "R5": (84, 44, "I2C SCL pull-up near sensor bus"),
        "D1": (10, 10, "status LED visible near board edge"), "R3": (14, 10, "status LED series resistor"),
        "R6": (18, 10, "status LED support resistor"), "J2": (95, 25, "programming header accessible at edge"),
    }
    placements=[ComponentPlacement(component_ref=ref,x_mm=x,y_mm=y,reason=reason) for ref,(x,y,reason) in sorted(positions.items())]
    constraints=[
        PlacementConstraint(constraint_id="USB-EDGE",kind=PlacementConstraintKind.BOARD_EDGE,component_ref="J1",maximum_distance_mm=6,reason="USB-C cable access requires edge placement"),
        PlacementConstraint(constraint_id="HEADER-EDGE",kind=PlacementConstraintKind.BOARD_EDGE,component_ref="J2",maximum_distance_mm=6,reason="programming header must remain accessible"),
    ]
    for cap,target in [("C1","U2"),("C2","U2"),("C3","U1"),("C4","U1"),("C6","U3"),("C7","U3")]:
        constraints.append(PlacementConstraint(constraint_id=f"DECOUPLE-{cap}",kind=PlacementConstraintKind.NEAR_COMPONENT,component_ref=cap,target_ref=target,maximum_distance_mm=14 if target=="U1" else 6,reason=f"{cap} must provide a short local path near {target}"))
    return BoardConstraints(outline=BoardOutline(width_mm=100,height_mm=70),placements=placements,placement_constraints=constraints)
