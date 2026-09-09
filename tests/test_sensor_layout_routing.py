"""Every offered A1 option combination must leave routable physical escapes."""

import pytest

from ohmni.application.projects import prepare_project
from ohmni.eda.kicad import KiCadPcbCompiler, KiCadSchematicCompiler
from ohmni.physical.sensor_layout import sensor_board_constraints
from ohmni.routing.router import DeterministicRouter
from ohmni.routing.verifier import verify_routing
from ohmni.synthesis import I2cSensorSlot, SynthesisBrief


@pytest.mark.slow_integration
@pytest.mark.parametrize("led", [0, 1])
@pytest.mark.parametrize("header", [False, True])
@pytest.mark.parametrize("address", [0x76, 0x77])
def test_offered_sensor_board_options_route_every_connection(tmp_path, catalog, led, header, address):
    circuit, _ = prepare_project(SynthesisBrief(
        status_led_count=led, include_programming_header=header,
        sensors=(I2cSensorSlot(part_id="BME280", address=address),),
    ))
    board = sensor_board_constraints(circuit)
    schematic = KiCadSchematicCompiler(catalog).compile(circuit, tmp_path / "project.kicad_sch")
    compiler = KiCadPcbCompiler(catalog)
    placed = compiler.compile(circuit, schematic, board, tmp_path / "placed.kicad_pcb")
    assert placed.compilation.physical_verification.passed
    plan = DeterministicRouter().route(circuit, placed, board)
    report = verify_routing(circuit, placed, board, plan)
    assert report.passed, {"failures": [item.model_dump() for item in plan.failures],
                           "findings": [item.model_dump() for item in report.findings
                                        if item.status.value != "pass"]}
    assert plan.statistics.unresolved_net_count == 0
    routed = compiler.compile(circuit, schematic, board, tmp_path / "routed.kicad_pcb", plan)
    assert routed.compilation.routing_verification.passed
    assert routed.routing_plan_fingerprint == plan.content_hash
