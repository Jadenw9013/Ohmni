"""Bounded, authored layout policy for the A1 sensor-board archetype.

The synthesis compiler owns these references. Optional blocks are omitted with
their constraints. This is an explicit template policy, not a placement optimizer
or a mechanical/RF sign-off. Physical checks and KiCad still check every result.
"""

from ..domain import CircuitIR
from .models import (
    BoardConstraints,
    BoardOutline,
    ComponentPlacement,
    PlacementConstraint,
    PlacementConstraintKind,
)


def sensor_board_constraints(circuit: CircuitIR) -> BoardConstraints:
    positions = {
        "J1": (50, 65, "USB power connector at the lower edge"),
        "R1": (45, 58, "USB CC termination"), "R2": (55, 58, "USB CC termination"),
        "U2": (20, 58, "Power regulator block"),
        "C1": (16, 58, "Regulator input bypass"), "C2": (24, 58, "Regulator output bypass"),
        "U1": (45, 35, "Processor block"),
        "C3": (32, 35, "Processor local decoupling"), "C4": (58, 35, "Processor bulk capacitance"),
        "C5": (45, 22, "Processor enable capacitor"), "R3": (14, 10, "Processor enable pull-up"),
        "U3": (80, 50, "Sensor block"),
        "C6": (76, 50, "Sensor VDD decoupling"), "C7": (84, 50, "Sensor VDDIO decoupling"),
        # Keep the data/clock pull-ups on the sensor's data-pin side. A data
        # trace approaching from the left can fence in the adjacent CSB power
        # escape when SDO is strapped high for address 0x77. This authored
        # ordering leaves room for that escape in every offered configuration.
        "R4": (82, 44, "Sensor data pull-up above the data-pin side"),
        "R5": (86, 44, "Sensor clock pull-up beside the data pull-up"),
        "D1": (10, 10, "Optional visible status light"),
        "R6": (18, 10, "Optional LED current limiting resistor"),
        "J2": (95, 25, "Optional programming header at the right edge"),
    }
    refs = {part.ref for part in circuit.components}
    if refs - positions.keys():
        raise ValueError("The circuit contains parts outside the A1 layout policy")
    placements = [
        ComponentPlacement(component_ref=ref, x_mm=positions[ref][0],
                           y_mm=positions[ref][1], reason=positions[ref][2])
        for ref in sorted(refs)
    ]
    constraints = [
        PlacementConstraint(constraint_id=f"EDGE-{ref}", kind=PlacementConstraintKind.BOARD_EDGE,
                            component_ref=ref, maximum_distance_mm=6,
                            reason="Cable access requires edge placement")
        for ref in ("J1", "J2") if ref in refs
    ]
    for cap, target in (("C1", "U2"), ("C2", "U2"), ("C3", "U1"),
                        ("C4", "U1"), ("C6", "U3"), ("C7", "U3")):
        if cap in refs and target in refs:
            constraints.append(PlacementConstraint(
                constraint_id=f"DECOUPLE-{cap}", kind=PlacementConstraintKind.NEAR_COMPONENT,
                component_ref=cap, target_ref=target,
                maximum_distance_mm=14 if target == "U1" else 6,
                reason="Local decoupling proximity within the stated template constraint",
            ))
    return BoardConstraints(outline=BoardOutline(width_mm=100, height_mm=70),
                            placements=placements, placement_constraints=constraints)
