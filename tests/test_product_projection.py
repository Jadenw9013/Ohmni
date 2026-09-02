"""The product projection derives grouping and flows from topology, not names."""

from __future__ import annotations

import pytest

from ohmni.application.systems import (
    LOCAL_NET_MAX_PINS,
    SystemId,
    build_flows,
    build_systems,
    group_components,
)
from ohmni.domain.circuit import NetKind
from ohmni.eda.kicad.placement import golden_board_constraints


@pytest.fixture(name="placements")
def _placements():
    return {p.component_ref: (p.x_mm, p.y_mm) for p in golden_board_constraints().placements}


@pytest.fixture(name="grouping")
def _grouping(golden, catalog, placements):
    return group_components(golden, catalog, placements)


def test_every_component_is_grouped_exactly_once(golden, grouping):
    refs = [g.component_ref for g in grouping]
    assert sorted(refs) == sorted(item.ref for item in golden.components)
    assert len(refs) == len(set(refs))


def test_anchors_come_from_part_category_and_declared_external_source(grouping):
    by_ref = {g.component_ref: g for g in grouping}
    assert by_ref["U1"].anchor and by_ref["U1"].system is SystemId.COMPUTE
    assert by_ref["U2"].anchor and by_ref["U2"].system is SystemId.POWER
    assert by_ref["U3"].anchor and by_ref["U3"].system is SystemId.SENSE
    assert by_ref["D1"].anchor and by_ref["J2"].anchor
    # J1 is a connector; it is a power anchor only because VBUS declares an
    # external source, not because the part is called USB_C_RECEPTACLE.
    assert by_ref["J1"].anchor and by_ref["J1"].system is SystemId.POWER


def test_passives_attach_to_the_part_they_actually_serve(grouping):
    by_ref = {g.component_ref: g for g in grouping}
    expected = {
        "C1": "U2", "C2": "U2", "R1": "J1", "R2": "J1",
        "C3": "U1", "C4": "U1", "C5": "U1", "R3": "U1",
        "C6": "U3", "C7": "U3", "R4": "U3", "R5": "U3",
        "R6": "D1",
    }
    for ref, anchor in expected.items():
        assert by_ref[ref].attached_to == anchor, f"{ref} attached to {by_ref[ref].attached_to}"
        assert not by_ref[ref].anchor
        assert by_ref[ref].basis


def test_local_net_attachment_is_preferred_over_distance(golden, grouping):
    """R4 shares the 14-pin 3V3 rail with four anchors but is wired to U3 by SDA."""
    by_ref = {g.component_ref: g for g in grouping}
    sda = golden.net("SDA")
    assert len(sda.connections) <= LOCAL_NET_MAX_PINS
    assert "SDA" in by_ref["R4"].basis and "U3" in by_ref["R4"].basis


def test_shared_rail_attachment_states_the_measured_distance(golden, grouping):
    """C2 is only distinguishable by placement, and the basis says exactly that."""
    by_ref = {g.component_ref: g for g in grouping}
    rail = golden.net("3V3")
    assert len(rail.connections) > LOCAL_NET_MAX_PINS
    assert "shared net 3V3" in by_ref["C2"].basis and "mm from U2" in by_ref["C2"].basis


def test_systems_partition_the_board(golden, grouping):
    systems = build_systems(grouping)
    assert [s.system for s in systems] == [
        SystemId.POWER, SystemId.COMPUTE, SystemId.SENSE, SystemId.IO,
    ]
    members = [ref for s in systems for ref in s.component_refs]
    assert sorted(members) == sorted(item.ref for item in golden.components)
    assert all(s.anchor_refs for s in systems)
    assert all(s.label and s.summary for s in systems)


def test_flows_only_name_nets_and_components_that_exist(golden, catalog, grouping):
    flows = build_flows(golden, catalog, grouping)
    known_nets = {net.name for net in golden.nets}
    known_refs = {item.ref for item in golden.components}
    assert {flow.flow_id for flow in flows} == {
        "power", "sensor_data", "status_led", "programming", "ground",
    }
    for flow in flows:
        assert flow.basis and flow.summary and flow.stages
        assert set(flow.net_names) <= known_nets
        assert set(flow.component_refs) <= known_refs
        for stage in flow.stages:
            assert set(stage.net_names) <= known_nets
            assert set(stage.component_refs) <= known_refs
            for label in stage.pin_labels:
                ref, pin = label.split(".", 1)
                net = next(n for n in golden.nets if n.name in stage.net_names and n.has(ref, pin))
                assert net is not None


def test_power_flow_follows_the_regulator_rather_than_naming_it(golden, catalog, grouping):
    power = next(f for f in build_flows(golden, catalog, grouping) if f.flow_id == "power")
    source = next(n for n in golden.nets if n.external_source is not None)
    assert source.name in power.net_names and "3V3" in power.net_names
    assert "U2" in power.component_refs
    assert power.stages[0].net_names == [source.name]


def test_i2c_flow_is_derived_from_the_peripheral_side(golden, catalog, grouping):
    bus = next(f for f in build_flows(golden, catalog, grouping) if f.flow_id == "sensor_data")
    assert sorted(bus.net_names) == ["SCL", "SDA"]
    assert "U3" in bus.component_refs and "U1" in bus.component_refs
    assert {"R4", "R5"} <= set(bus.component_refs)


def test_ground_flow_covers_the_declared_ground_net(golden, catalog, grouping):
    ground_net = next(n for n in golden.nets if n.kind is NetKind.GROUND)
    ground = next(f for f in build_flows(golden, catalog, grouping) if f.flow_id == "ground")
    assert ground.net_names == [ground_net.name]
    assert set(ground.component_refs) == ground_net.components()


def test_grouping_is_stable_across_runs(golden, catalog, placements):
    first = group_components(golden, catalog, placements)
    second = group_components(golden, catalog, placements)
    assert [g.model_dump() for g in first] == [g.model_dump() for g in second]


def test_net_driver_voltage_follows_the_driver_not_the_net_name(golden, catalog):
    """The repaired rail's voltage comes from the regulator, not from '3V3'."""
    from ohmni.application.product import _net_driver_voltage

    assert _net_driver_voltage(golden, catalog, "3V3") == 3.3
    assert _net_driver_voltage(golden, catalog, "VBUS") == 5.0
    assert _net_driver_voltage(golden, catalog, "SDA") is None
    renamed = golden.model_copy(deep=True)
    for net in renamed.nets:
        if net.name == "3V3":
            net.name = "POTATO"
    # Renaming the net does not change what drives it.
    assert _net_driver_voltage(renamed, catalog, "POTATO") == 3.3
