"""SPI regressions: plausible-looking nets must not earn a structural pass."""

from __future__ import annotations

import pytest

from ohmni.adapters.fakes import InMemoryPartCatalog
from ohmni.catalog import default_catalog
from ohmni.domain import (
    CircuitComponent,
    CircuitIR,
    ComponentCategory,
    ComponentSpec,
    ExternalSource,
    ExternalSourceKind,
    Interface,
    Net,
    NetKind,
    PackageOption,
    PinElectricalType,
    PinRef,
    PinRole,
    PinSpec,
    Quantity,
    RuleOutcome,
    SupplyRail,
    ValueRange,
)
from ohmni.verifier import verify


def _pin(ref: str, number: str) -> PinRef:
    return PinRef(component=ref, pin=number)


def _example(count: int = 2) -> tuple[CircuitIR, InMemoryPartCatalog]:
    # A deliberately small test spec: these facts are supplied by the test,
    # not evidence created by the verifier or a dependency on catalog authoring.
    roles = {
        "1": ("CS", PinRole.SPI_CS, PinElectricalType.INPUT),
        "2": ("SO", PinRole.SPI_MISO, PinElectricalType.TRI_STATE),
        "3": ("WP", PinRole.OTHER, PinElectricalType.INPUT),
        "4": ("VSS", PinRole.GROUND, PinElectricalType.POWER_IN),
        "5": ("SI", PinRole.SPI_MOSI, PinElectricalType.INPUT),
        "6": ("SCK", PinRole.SPI_SCK, PinElectricalType.INPUT),
        "7": ("HOLD", PinRole.OTHER, PinElectricalType.INPUT),
        "8": ("VCC", PinRole.POWER, PinElectricalType.POWER_IN),
    }
    memory = ComponentSpec(
        part_id="25LC256-I/SN", mpn="25LC256-I/SN", category=ComponentCategory.MEMORY,
        description="Test SPI peripheral", packages=[PackageOption(name="SOIC-8")],
        interfaces=[Interface.SPI],
        pins=[
            PinSpec(
                number=number, name=name, roles=[role], electrical_type=electrical,
                supply_rail=None if role is PinRole.GROUND else "VCC",
                must_not_float=number in {"1", "3", "7"},
            )
            for number, (name, role, electrical) in roles.items()
        ],
        supply_rails=[SupplyRail(
            name="VCC", operating=ValueRange(
                minimum=Quantity.volts(2.5), maximum=Quantity.volts(5.5)
            ),
        )],
    )
    catalog = InMemoryPartCatalog([
        part.model_copy(deep=True) for part in default_catalog().all_parts()
    ])
    catalog.add(memory)
    components = [CircuitComponent(
        ref="U1", part_id="ESP32-WROOM-32E", selected_interfaces=[Interface.SPI]
    )]
    power = [_pin("U1", "2")]
    ground = [_pin("U1", "1"), _pin("U1", "15"), _pin("U1", "38")]
    nets = [
        Net(name="data_out", connections=[_pin("U1", "37")]),
        Net(name="data_in", connections=[_pin("U1", "31")]),
        Net(name="clock", connections=[_pin("U1", "30")]),
    ]
    for index in range(count):
        ref, resistor = f"U{index + 2}", f"R{index + 1}"
        components.extend([
            CircuitComponent(ref=ref, part_id=memory.part_id, selected_interfaces=[Interface.SPI]),
            CircuitComponent(ref=resistor, part_id="GENERIC_RESISTOR", value=Quantity.ohms(10_000)),
        ])
        power.extend([_pin(ref, "8"), _pin(ref, "3"), _pin(ref, "7"), _pin(resistor, "2")])
        ground.append(_pin(ref, "4"))
        for net, number in zip(nets[:3], ("5", "2", "6"), strict=True):
            net.connections.append(_pin(ref, number))
        nets.append(Net(name=f"select{index}", connections=[
            _pin("U1", str(10 + index)), _pin(ref, "1"), _pin(resistor, "1"),
        ]))
    nets.extend([
        Net(name="logic_supply", kind=NetKind.POWER, connections=power,
            external_source=ExternalSource(kind=ExternalSourceKind.BENCH_SUPPLY,
                voltage=ValueRange.exact(Quantity.volts(3.3)))),
        Net(name="return", kind=NetKind.GROUND, connections=ground),
    ])
    return CircuitIR(ir_id="spi-test", name="SPI test", components=components, nets=nets), catalog


def _result(circuit, catalog):
    return verify(circuit, catalog, rule_subset=["PB-SPI-001"]).results[0]


def _move(circuit: CircuitIR, ref: str, number: str, destination: str | None) -> None:
    pin = _pin(ref, number)
    for net in circuit.nets:
        net.connections = [item for item in net.connections if item != pin]
    if destination is not None:
        next(net for net in circuit.nets if net.name == destination).connections.append(pin)


@pytest.mark.parametrize("count", [1, 2])
def test_supported_bus_checks_topology_but_keeps_firmware_limitations(count):
    circuit, catalog = _example(count)
    result = _result(circuit, catalog)
    assert result.outcome is RuleOutcome.PASS, result.model_dump_json()
    assert result.examined
    assert "Runtime select exclusivity" in " ".join(result.limitations)
    assert "frequency" in " ".join(result.limitations)


def test_i2c_selected_bme280_is_not_treated_as_spi(golden, catalog):
    assert _result(golden, catalog).outcome is RuleOutcome.NOT_APPLICABLE


@pytest.mark.parametrize("number", ["1", "2", "5", "6"])
def test_required_signal_cannot_be_unconnected(number):
    circuit, catalog = _example()
    _move(circuit, "U2", number, None)
    result = _result(circuit, catalog)
    assert result.outcome is RuleOutcome.FAIL
    assert any("not connected" in finding.title for finding in result.findings)


def test_swapped_controller_mosi_and_miso_are_blocking():
    circuit, catalog = _example()
    _move(circuit, "U1", "31", "data_out")
    _move(circuit, "U1", "37", "data_in")
    report = verify(circuit, catalog, rule_subset=["PB-SPI-001"])
    assert report.export_blocked
    assert report.results[0].outcome is RuleOutcome.FAIL


def test_short_between_peripheral_functions_is_not_a_bus():
    circuit, catalog = _example()
    _move(circuit, "U2", "5", "clock")
    result = _result(circuit, catalog)
    assert result.outcome is RuleOutcome.FAIL
    assert any("shorted SPI functions" in finding.title for finding in result.findings)


def test_shared_chip_select_cannot_hide_behind_tri_state_miso_types():
    circuit, catalog = _example()
    _move(circuit, "U3", "1", "select0")
    result = _result(circuit, catalog)
    assert result.outcome is RuleOutcome.FAIL
    assert any("share a chip select" in finding.title for finding in result.findings)


def test_always_driving_miso_is_rejected():
    circuit, catalog = _example()
    catalog.require("25LC256-I/SN").pin("2").electrical_type = PinElectricalType.OUTPUT
    assert _result(circuit, catalog).outcome is RuleOutcome.FAIL


def test_gpio_alone_does_not_establish_inactive_chip_select():
    circuit, catalog = _example()
    _move(circuit, "R1", "2", None)
    result = _result(circuit, catalog)
    assert result.outcome is RuleOutcome.FAIL
    assert any("no inactive pull-up" in finding.title for finding in result.findings)


def test_active_select_pull_down_is_rejected():
    circuit, catalog = _example()
    _move(circuit, "R1", "2", "return")
    assert _result(circuit, catalog).outcome is RuleOutcome.FAIL


def test_chip_select_pullup_must_use_the_peripheral_supply():
    circuit, catalog = _example()
    circuit.nets.append(Net(
        name="another_rail", kind=NetKind.POWER, external_source=ExternalSource(
            kind=ExternalSourceKind.BENCH_SUPPLY,
            voltage=ValueRange.exact(Quantity.volts(5)),
        ),
    ))
    _move(circuit, "R1", "2", "another_rail")
    result = _result(circuit, catalog)
    assert result.outcome is RuleOutcome.FAIL
    assert any("another supply" in finding.title for finding in result.findings)


def test_unknown_pullup_value_is_insufficient_data():
    circuit, catalog = _example()
    circuit.component("R1").value = None
    assert _result(circuit, catalog).outcome is RuleOutcome.INSUFFICIENT_DATA


def test_spi_signal_without_supply_role_cannot_silently_escape_voltage_coverage():
    circuit, catalog = _example()
    catalog.require("25LC256-I/SN").pin("5").supply_rail = None
    assert _result(circuit, catalog).outcome is RuleOutcome.INSUFFICIENT_DATA


def test_multiple_controller_pins_on_clock_are_rejected():
    circuit, catalog = _example()
    next(net for net in circuit.nets if net.name == "clock").connections.append(_pin("U1", "12"))
    result = _result(circuit, catalog)
    assert result.outcome is RuleOutcome.FAIL
    assert any("exactly one controller pin" in finding.title for finding in result.findings)


def test_splitting_chip_select_onto_another_controller_is_rejected():
    circuit, catalog = _example()
    circuit.components.append(CircuitComponent(
        ref="U4", part_id="ESP32-WROOM-32E", selected_interfaces=[Interface.SPI]
    ))
    next(net for net in circuit.nets if net.name == "logic_supply").connections.append(_pin("U4", "2"))
    _move(circuit, "U1", "11", None)
    next(net for net in circuit.nets if net.name == "select1").connections.append(_pin("U4", "11"))
    result = _result(circuit, catalog)
    assert result.outcome is RuleOutcome.FAIL
    assert any("split across controllers" in finding.title for finding in result.findings)


def test_spi_only_peripheral_cannot_avoid_checks_by_omitting_selected_interface():
    circuit, catalog = _example()
    circuit.component("U2").selected_interfaces = []
    assert _result(circuit, catalog).outcome is RuleOutcome.FAIL


def test_unknown_select_polarity_does_not_assume_active_low():
    circuit, catalog = _example()
    memory = catalog.require("25LC256-I/SN").model_copy(deep=True)
    memory.part_id = "UNMODELED-SPI"
    catalog.add(memory)
    circuit.component("U2").part_id = memory.part_id
    result = _result(circuit, catalog)
    assert result.outcome is RuleOutcome.INSUFFICIENT_DATA
    assert any("inactive polarity" in missing for missing in result.missing_data)


def test_net_labels_do_not_determine_spi_function():
    circuit, catalog = _example()
    for index, net in enumerate(circuit.nets):
        net.name = f"arbitrary_{index}"
    assert _result(circuit, catalog).outcome is RuleOutcome.PASS


def test_unknown_peripheral_role_does_not_become_a_pass():
    circuit, catalog = _example()
    catalog.require("25LC256-I/SN").pin("5").roles = [PinRole.OTHER]
    assert _result(circuit, catalog).outcome is RuleOutcome.INSUFFICIENT_DATA


def test_unsupported_controller_spi_capability_is_insufficient_data():
    circuit, catalog = _example()
    controller = catalog.require("ESP32-WROOM-32E")
    controller.interfaces = [Interface.GPIO]
    assert _result(circuit, catalog).outcome is RuleOutcome.INSUFFICIENT_DATA


def test_unknown_selected_spi_part_is_insufficient_data():
    circuit, catalog = _example(1)
    circuit.component("U2").part_id = "MISSING-SPI"
    assert _result(circuit, catalog).outcome is RuleOutcome.INSUFFICIENT_DATA


def test_arbitrary_output_gpio_is_valid_for_select_but_not_clock():
    circuit, catalog = _example()
    _move(circuit, "U1", "10", None)
    next(net for net in circuit.nets if net.name == "select0").connections.append(_pin("U1", "12"))
    assert _result(circuit, catalog).outcome is RuleOutcome.PASS
    _move(circuit, "U1", "12", "clock")
    _move(circuit, "U1", "30", "select0")
    assert _result(circuit, catalog).outcome is RuleOutcome.FAIL


def test_zero_ohm_chip_select_pullup_is_not_selectable():
    circuit, catalog = _example()
    circuit.component("R1").value = Quantity.ohms(0)
    assert _result(circuit, catalog).outcome is RuleOutcome.FAIL


def test_separate_clock_nets_are_outside_the_shared_bus_contract():
    circuit, catalog = _example()
    # A controller may have several cataloged SCK-capable pins, but the
    # supported one-bus topology still requires one shared clock connection.
    catalog.require("ESP32-WROOM-32E").pin("12").roles = [PinRole.SPI_SCK]
    circuit.nets.append(Net(name="second_clock", connections=[_pin("U1", "12")]))
    _move(circuit, "U3", "6", "second_clock")
    result = _result(circuit, catalog)
    assert result.outcome is RuleOutcome.FAIL
    assert any("do not share spi_sck" in finding.title for finding in result.findings)


@pytest.mark.parametrize("number", ["3", "7", "8"])
def test_existing_rules_reject_missing_required_control_or_power_pins(number):
    circuit, catalog = _example()
    _move(circuit, "U2", number, None)
    report = verify(circuit, catalog, rule_subset=["PB-PIN-002", "PB-CONN-003"])
    assert report.export_blocked
    assert any("U2" in finding.affected_components for finding in report.findings)
