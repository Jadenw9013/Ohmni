"""Display limits are stated, never silent; ratings still read every terminal."""

import shutil
from pathlib import Path

import pytest

from ohmni.application.component_behavior import ComponentBehaviorService, DesignRunRequest
from ohmni.domain.circuit import CircuitComponent, CircuitIR, ExternalSource, Net, PinRef
from ohmni.domain.units import Quantity, ValueRange

ROOT = Path(__file__).resolve().parents[1]
pytestmark = [pytest.mark.integration,
              pytest.mark.skipif(shutil.which("ngspice") is None, reason="ngspice 42 is not installed")]


def chain(count=14):
    parts = [CircuitComponent(ref=f"R{i}", part_id="GENERIC_RESISTOR", package="0603", value=Quantity.ohms(100))
             for i in range(1, count + 1)]
    nets = [Net(name="vin", kind="power", connections=[PinRef(component="R1", pin="1")],
                external_source=ExternalSource(kind="bench_supply", voltage=ValueRange.exact(Quantity.volts(1))))]
    nets += [Net(name=f"m{i:02}", connections=[PinRef(component=f"R{i}", pin="2"),
                                                PinRef(component=f"R{i + 1}", pin="1")]) for i in range(1, count)]
    nets.append(Net(name="gnd", kind="ground", connections=[PinRef(component=f"R{count}", pin="2")]))
    return CircuitIR(ir_id="chain", name="Resistor chain", components=parts, nets=nets)


@pytest.fixture(scope="module")
def live(tmp_path_factory):
    return ComponentBehaviorService(ROOT, tmp_path_factory.mktemp("display"))


def test_transient_display_cut_is_stated(live):
    result = live.run_design(DesignRunRequest(circuit=chain(), analysis="tran", tstep="1u", tstop="5u"))
    assert result["status"] == "ran", result["problems"]
    # compile_circuit numbers nodes over the nets sorted by name, so the first 12 non-ground nets are m01..m12.
    assert [s["name"] for s in result["transient"]["series"]] == [f"m{i:02}" for i in range(1, 13)]
    assert any("Display shows 12 of 14 nets" in x for x in result["limitations"])
    long = live.run_design(DesignRunRequest(circuit=chain(), analysis="tran", tstep="1u", tstop="5u",
                                            observe_nets=[f"m{i:02}" for i in range(1, 14)]))
    assert long["status"] == "not_run" and any("within the signal limit" in p for p in long["problems"])


def test_ac_sweep_display_cut_is_stated_and_long_observe_lists_are_refused(live):
    circuit = chain()
    excitation = {"positive_net": "gnd", "negative_net": "m01", "ac_rms": {"value": 1e-3, "unit": "A"}}
    sweep = {"start_hz": 10, "stop_hz": 1000, "points_per_decade": 1}
    result = live.run_design(DesignRunRequest(circuit=circuit, analysis="ac", excitations=[excitation],
                                              ac_points_hz=[100.0], ac_sweep=sweep))
    assert result["status"] == "ran", result["problems"]
    assert [s["name"] for s in result["ac"]["sweep"]["series"]] == [f"m{i:02}" for i in range(1, 13)]
    assert any("Display shows 12 of 14 nets" in x for x in result["limitations"])
    refused = live.run_design(DesignRunRequest(circuit=circuit, analysis="ac", excitations=[excitation],
                                               ac_points_hz=[100.0], ac_sweep=sweep,
                                               observe_nets=[f"m{i:02}" for i in range(1, 14)]))
    assert refused["status"] == "not_run"
    assert any("within the signal limit" in p for p in refused["problems"])
    for bad in ([], ["m01", "m01"], ["gnd"]):
        out = live.run_design(DesignRunRequest(circuit=circuit, analysis="ac", excitations=[excitation],
                                               ac_points_hz=[100.0], ac_sweep=sweep, observe_nets=bad))
        assert out["status"] == "not_run", bad
