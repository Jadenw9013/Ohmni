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


def test_sensor_controller_flow_does_not_call_its_pullups_receivers(catalog):
    """Compiler-owned compute groups include passive support, not only processors."""
    from ohmni.synthesis import ArchetypeId, SynthesisBrief, synthesize

    result = synthesize(SynthesisBrief(
        archetype=ArchetypeId.A2_USB_GPIO_CONTROLLER,
        status_led_count=4, button_count=2,
        board_width_mm=90, board_height_mm=55,
    ), catalog)
    circuit = result.circuit
    grouping = group_components(circuit, catalog, {}, result.placement_request)
    by_ref = {item.component_ref: item for item in grouping}
    assert all(by_ref[ref].system is SystemId.COMPUTE for ref in ("U1", "R4", "R5"))

    bus = next(flow for flow in build_flows(circuit, catalog, grouping)
               if flow.flow_id == "sensor_data")
    receiver = next(stage for stage in bus.stages if stage.title == "The processor reads it")
    pullups = next(stage for stage in bus.stages if stage.title == "Resistors hold the wires high")
    assert receiver.component_refs == ["U1"]
    assert set(pullups.component_refs) == {"R4", "R5"}
    assert "main computer" in receiver.detail and "resistor" not in receiver.detail
    assert "main computer" in bus.summary and "resistor" not in bus.summary


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
    from ohmni.application.naming import net_driver_voltage as _net_driver_voltage

    assert _net_driver_voltage(golden, catalog, "3V3") == 3.3
    assert _net_driver_voltage(golden, catalog, "VBUS") == 5.0
    assert _net_driver_voltage(golden, catalog, "SDA") is None
    renamed = golden.model_copy(deep=True)
    for net in renamed.nets:
        if net.name == "3V3":
            net.name = "POTATO"
    # Renaming the net does not change what drives it.
    assert _net_driver_voltage(renamed, catalog, "POTATO") == 3.3


# ---------------------------------------------------------------------------
# Human-facing vocabulary
# ---------------------------------------------------------------------------

def test_a_passive_is_only_given_a_role_the_topology_establishes(golden, catalog):
    """A capacitor across the supply is unambiguous; every other shape is not.

    Filtering, coupling and timing capacitors are indistinguishable in a
    netlist, so the name states what the part is rather than guessing at what
    it is for.
    """
    from ohmni.application.naming import component_term

    assert component_term(golden, catalog, "C3").human == "100 nF power smoothing capacitor"
    assert component_term(golden, catalog, "C5").human == "100 nF capacitor"
    # A resistor passing a signal through from a connector is not a
    # termination, and must not be named as one.
    assert "configuration" in component_term(golden, catalog, "R1").human
    assert component_term(golden, catalog, "R6").human == "330 ohm current-limiting resistor"


def test_components_are_named_from_what_they_do_not_from_a_lookup_table(golden, catalog):
    from ohmni.application.naming import component_term

    expected = {
        "U1": "Main computer",
        "U2": "3.3 V voltage regulator",
        "U3": "Sensor",
        "J1": "USB power connector",
        "J2": "Programming header",
        "D1": "Indicator light",
        "R6": "330 ohm current-limiting resistor",
        "R4": "4.7 kohm pull-up resistor",
        "R1": "5.1 kohm connector configuration resistor",
        "C3": "100 nF power smoothing capacitor",
        "C5": "100 nF capacitor",
    }
    for ref, human in expected.items():
        assert component_term(golden, catalog, ref).human == human, ref


def test_every_component_name_keeps_its_identifier(golden, catalog):
    from ohmni.application.naming import component_term

    for instance in golden.components:
        term = component_term(golden, catalog, instance.ref)
        assert instance.ref in term.technical
        assert instance.part_id in term.technical
        assert term.human and term.human != instance.ref


def test_the_regulator_name_comes_from_its_datasheet_not_its_part_number(golden, catalog):
    """Rename the part and the name follows the regulator's own output voltage."""
    from ohmni.application.naming import component_term

    assert component_term(golden, catalog, "U2").human == "3.3 V voltage regulator"
    spec = catalog.require("AP2112K-3.3TRG1")
    assert spec.regulator.output_voltage.nominal.value == 3.3


def test_the_connector_is_a_power_connector_only_because_a_net_declares_a_source(golden, catalog):
    from ohmni.application.naming import component_term

    assert component_term(golden, catalog, "J1").human == "USB power connector"
    stripped = golden.model_copy(deep=True)
    for net in stripped.nets:
        net.external_source = None
    # Without a declared source the same part is just a connector: the name is
    # derived from the circuit, not from the part's name.
    assert component_term(stripped, catalog, "J1").human == "Connector"


def test_nets_are_named_by_what_they_carry(golden, catalog):
    from ohmni.application.naming import net_term

    expected = {
        "VBUS": "5 V from USB",
        "3V3": "3.3 V power",
        "GND": "Ground",
        "SDA": "Sensor data line",
        "SCL": "Sensor clock line",
        "UART_TX": "Programming connection",
    }
    for name, human in expected.items():
        term = net_term(golden, catalog, name)
        assert term.human == human, f"{name} -> {term.human}"
        assert term.technical == name, "the identifier is always carried"


def test_renaming_a_net_does_not_change_the_name_it_is_given(golden, catalog):
    """The readable name follows the driver, exactly as the verifier's voltage does."""
    from ohmni.application.naming import net_term

    renamed = golden.model_copy(deep=True)
    for net in renamed.nets:
        if net.name == "3V3":
            net.name = "POTATO"
    assert net_term(renamed, catalog, "POTATO").human == "3.3 V power"


def test_bus_pin_roles_match_numbered_variants(golden, catalog):
    """Parts publish TXD0/IO21; the role lives in the prefix."""
    from ohmni.application.naming import bus_role

    assert bus_role("TXD0")[1] == "serial"
    assert bus_role("RXD0")[1] == "serial"
    assert bus_role("SDA")[0] == "data line"
    assert bus_role("IO21") is None


def test_phrase_lowercases_words_but_never_units_or_acronyms():
    from ohmni.application.naming import phrase

    assert phrase("Sensor") == "sensor"
    assert phrase("Programming header") == "programming header"
    assert phrase("5 V from USB") == "5 V from USB"
    assert phrase("USB power connector") == "USB power connector"
    assert phrase("3.3 V power") == "3.3 V power"


def test_flows_read_without_reference_designators(golden, catalog, grouping):
    """The flow a beginner reads must not require knowing what U2 or VBUS are."""
    from ohmni.application.systems import build_flows

    identifiers = {item.ref for item in golden.components} | {net.name for net in golden.nets}
    for flow in build_flows(golden, catalog, grouping):
        prose = flow.summary + " " + " ".join(stage.detail for stage in flow.stages)
        leaked = sorted(token for token in identifiers
                        if f" {token} " in f" {prose} " or f" {token}." in prose)
        assert not leaked, f"{flow.flow_id} leaks identifiers: {leaked}"


def test_check_families_separate_ohmni_rules_from_external_tools():
    """An Ohmni category with no rules must not be labelled after KiCad.

    The regression: "UNSUPPORTED | KiCad's own opinion" rendered two rows above
    "PASS | KiCad checked the board", telling a reader that KiCad both did and
    did not check the design.
    """
    from ohmni.application.product import CHECK_GROUPS, CheckFamily
    from ohmni.domain.verification import RuleCategory

    eda_label, eda_question = CHECK_GROUPS[RuleCategory.EDA]
    assert "KiCad's own opinion" != eda_label
    assert "Ohmni" in eda_label, "an empty Ohmni category is named after Ohmni"
    assert "KiCad" in eda_question, "and says where the external check actually reports"
    assert set(CheckFamily) == {CheckFamily.OHMNI, CheckFamily.EXTERNAL, CheckFamily.NOT_ANALYSED}


def test_checks_fail_loudly_when_the_verifier_subsystem_map_drifts(golden, catalog):
    """A category the verifier stops rolling up must not vanish from the screen."""
    import pytest as _pytest

    from ohmni.application import product
    from ohmni.fixtures.esp32_env_logger import requirements
    from ohmni.verifier import verify

    report = verify(golden, catalog, requirements())
    report.subsystem_status.pop("electrical")
    with _pytest.raises(ValueError, match="no status for subsystem"):
        product._checks(report, None, _StubRouted(), _StubDrc(), _StubManufacturing())


class _Stub:
    """Minimal stand-ins: _checks only reads counts and statuses off these."""

    def __init__(self, **values):
        self.__dict__.update(values)


_StubPhysical = lambda: _Stub(passed=True, findings=[])
_StubRouted = lambda: _Stub(compilation=_Stub(physical_verification=_StubPhysical()))
_StubDrc = lambda: _Stub(findings=[], unconnected_items=[], status=_Stub(value="pass"))
_StubManufacturing = lambda: _Stub(passed=True, findings=[])
