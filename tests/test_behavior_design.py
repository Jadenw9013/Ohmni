"""Design-level behavior runs: a user's multi-part circuit, every part checked, nothing guessed."""

import shutil
from pathlib import Path

import pytest

from ohmni.application.component_behavior import (
    ComponentBehaviorService,
    DesignRunRequest,
    design_summary,
)
from ohmni.behavior.netlist import scope_shared_definitions
from ohmni.domain.circuit import CircuitComponent, CircuitIR, ExternalSource, Net, PinRef
from ohmni.domain.units import Quantity, ValueRange
from ohmni.eda.simulation import NgspiceAdapter

ROOT = Path(__file__).resolve().parents[1]
needs_ngspice = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("ngspice") is None, reason="ngspice 42 is not installed"),
]


class RecordingAdapter:
    def __init__(self):
        self.calls = []

    def behavior_circuit(self, compilation, **kwargs):
        self.calls.append((compilation, kwargs))
        return {"status": "not_run", "rating_status": "not_run", "analysis": compilation.analysis,
                "problems": ["Simulator unavailable"], "operating_point": None, "transient": None,
                "version_output": "", "ratings": None, "limitations": compilation.limitations}


@pytest.fixture(scope="module")
def service(tmp_path_factory):
    return ComponentBehaviorService(ROOT, tmp_path_factory.mktemp("design"), adapter=RecordingAdapter())


@pytest.fixture(scope="module")
def live(tmp_path_factory):
    return ComponentBehaviorService(ROOT, tmp_path_factory.mktemp("design-live"), adapter=NgspiceAdapter())


def two_leds(r1=150, r2=150, led1=("OHM-077", None), led2=("OHM-078", None), package2=None):
    """Two LED branches on one 5 V rail. Catalog pin 2 is the anode for the bound LED entries."""
    part1, part2 = led1[1] or led1[0], led2[1] or led2[0]
    return CircuitIR(ir_id="two-leds", name="Two indicator LEDs", components=[
        CircuitComponent(ref="R1", part_id="GENERIC_RESISTOR", package="0603", value=Quantity.ohms(r1)),
        CircuitComponent(ref="R2", part_id="GENERIC_RESISTOR", package="0603", value=Quantity.ohms(r2)),
        CircuitComponent(ref="D1", part_id=part1, package="0402 LED"),
        CircuitComponent(ref="D2", part_id=part2, package=package2 or "0603 LED"),
    ], nets=[
        Net(name="vin", kind="power", connections=[PinRef(component="R1", pin="1"), PinRef(component="R2", pin="1")],
            external_source=ExternalSource(kind="bench_supply", voltage=ValueRange.exact(Quantity.volts(5)))),
        Net(name="a1", connections=[PinRef(component="R1", pin="2"), PinRef(component="D1", pin="2")]),
        Net(name="a2", connections=[PinRef(component="R2", pin="2"), PinRef(component="D2", pin="2")]),
        Net(name="gnd", kind="ground", connections=[PinRef(component="D1", pin="1"), PinRef(component="D2", pin="1")]),
    ])


def request(circuit, **kwargs):
    selections = {c.ref: {"entry_id": c.part_id} for c in circuit.components if c.part_id.startswith("OHM-")}
    return DesignRunRequest(circuit=circuit, selections=kwargs.pop("selections", selections), **kwargs)


def test_shared_model_names_are_scoped_per_part_and_comments_kept():
    blocks = [
        ("c1", [], ["D1 a 0 LEDX", "* LEDX comment", ".model LEDX D (IS=1e-20 N=2)"], []),
        ("c2", [], ["D2 b 0 ledx", ".model LEDX D (IS=1e-12 N=1)"], []),
        ("c3", [], ["R1 a b 1k"], []),
    ]
    problems = []
    scoped = scope_shared_definitions(blocks, {}, problems)
    assert not problems
    assert scoped[0][2] == ["D1 a 0 LEDX_c1", "* LEDX comment", ".model LEDX_c1 D (IS=1e-20 N=2)"]
    assert scoped[1][2] == ["D2 b 0 ledx_c2", ".model LEDX_c2 D (IS=1e-12 N=1)"]
    assert scoped[2][2] == ["R1 a b 1k"]
    # A name used by one part only is never touched, so single-part reference decks keep their hashes.
    assert scope_shared_definitions(blocks[:1], {}, [])[0][2] == blocks[0][2]


def test_hash_locked_assets_may_share_only_identical_definitions():
    same = {"a.lib": ".model DCLAMP D(IS=1f)\n", "b.lib": ".model dclamp  D(IS=1f)\n"}
    problems = []
    scope_shared_definitions([], same, problems)
    assert not problems
    differ = {"a.lib": ".model DCLAMP D(IS=1f)\n", "b.lib": ".model DCLAMP D(IS=2f)\n"}
    scope_shared_definitions([], differ, problems)
    assert problems and "dclamp" in problems[0]
    problems = []
    scope_shared_definitions([("c1", [], [".subckt DCLAMP a b", ".ends"], [])], same, problems)
    assert problems, "a part fragment may not redefine a hash-locked asset name"


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("ngspice") is None, reason="ngspice 42 is not installed")
def test_ngspice_silently_keeps_the_first_duplicate_card(tmp_path):
    """The reason for scoping: two same-named cards give both parts the first part's parameters."""
    body = ["V1 a 0 DC 5", "R1 a b 1k", "R2 a c 1k"]
    parts = [("c1", [], ["D1 b 0 LEDX", ".model LEDX D (IS=1e-20 N=2)"], []),
             ("c2", [], ["D2 c 0 LEDX", ".model LEDX D (IS=1e-12 N=1)"], [])]

    def run(blocks, name):
        lines = [line for block in blocks for line in block[2]]
        deck = "\n".join(["dup", *body, *lines, ".op", ".control", "run", "print v(b) v(c)", ".endc", ".end"]) + "\n"
        out = NgspiceAdapter().behavior_bench(deck, work_dir=tmp_path / name)
        assert out["status"] == "ran"
        return [float(line.split("=")[1]) for line in out["stdout"].splitlines() if line.startswith("v(")]

    unscoped = run(parts, "unscoped")
    assert unscoped[0] == unscoped[1]
    scoped = run(scope_shared_definitions(parts, {}, []), "scoped")
    assert abs(scoped[0] - scoped[1]) > 0.5


def test_generic_green_led_is_not_simulated_as_a_red_reference(service):
    circuit = two_leds(led2=("OHM-078", "GENERIC_LED_GREEN"))
    before = len(service.adapter.calls)
    result = service.run_design(request(circuit, selections={"D1": {"entry_id": "OHM-077"}}))
    assert result["status"] == "not_run" and result["rating_status"] == "not_run"
    assert len(service.adapter.calls) == before
    row = next(r for r in result["bindings"] if r["ref"] == "D2")
    assert row["entry_id"] == "OHM-078" and "green LED" in row["problem"] and "red" in row["problem"]
    # The catalog's own "0603" package name matches no bound recipe at all, which is also a refusal.
    circuit = two_leds(led2=("OHM-078", "GENERIC_LED_GREEN"), package2="0603")
    result = service.run_design(request(circuit, selections={"D1": {"entry_id": "OHM-077"}}))
    assert any(p.startswith("D2: No sourced behavior entry") for p in result["problems"])
    assert len(service.adapter.calls) == before


def test_reference_only_and_unbound_parts_stop_the_whole_design(service):
    before = len(service.adapter.calls)
    circuit = two_leds(led2=("OHM-062", None), package2="SOD-323")
    result = service.run_design(request(circuit))
    assert result["status"] == "not_run" and len(service.adapter.calls) == before
    assert any(p.startswith("D2:") and "not simulable" in p for p in result["problems"])
    circuit = two_leds(led2=("OHM-078", "BME280"))
    result = service.run_design(request(circuit, selections={"D1": {"entry_id": "OHM-077"}}))
    assert any("No sourced behavior entry" in p for p in result["problems"])
    result = service.run_design(request(two_leds(), selections={"D1": {"entry_id": "OHM-077"},
                                                                "D2": {"entry_id": "OHM-078"},
                                                                "Q9": {"entry_id": "OHM-004"}}))
    assert any(p.startswith("Q9:") for p in result["problems"])
    assert len(service.adapter.calls) == before


def test_bound_design_compiles_every_part_with_current_probes(service):
    result = service.run_design(request(two_leds(), rating_context={"ambient_c": 25}))
    compilation, kwargs = service.adapter.calls[-1]
    assert [c.entry_id for c in compilation.components] == ["OHM-077", "OHM-078", "OHM-004", "OHM-004"]
    assert all(c.role_current_probes for c in compilation.components)
    assert kwargs["analysis"] == "op" and kwargs["rating_context"]["ambient_c"] == 25
    assert result["status"] == "not_run" and result["design_summary"] is None
    assert [r["reference_part"] for r in result["bindings"]][:2] == [
        "Kingbright APHHS1005SURCK red", "Kingbright APT1608SURCK red"]
    assert any("source current capability" in x for x in result["limitations"])


def test_design_summary_never_promotes_an_unknown_part():
    ratings = {"status": "unknown", "components": [{"ref": "R1", "status": "within_model_limits"},
                                                   {"ref": "D1", "status": "unknown"}]}
    summary = design_summary(ratings)
    assert summary["status"] == "unknown" and summary["unknown_parts"] == ["D1"]
    assert summary["counts"] == {"within_model_limits": 1, "unknown": 1, "violation": 0}
    assert design_summary(None) is None


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("ngspice") is None, reason="ngspice 42 is not installed")
def test_two_part_design_runs_each_part_on_its_own_sourced_model(live):
    result = live.run_design(request(two_leds(), rating_context={"ambient_c": 25}))
    assert result["status"] == "ran", result["problems"]
    vf = {c["ref"]: next(m["voltage"]["value"] for m in c["measurements"] if m["role"] == "A")
          for c in result["components"] if c["ref"].startswith("D")}
    assert abs(vf["D1"] - vf["D2"]) > 0.01, "two different LEDs must not share one model card"
    # Thermal scope is not confirmed, so power and current ceilings stay unknown: never a pass.
    assert result["rating_status"] == "unknown"
    assert set(result["design_summary"]["unknown_parts"]) == {"D1", "D2", "R1", "R2"}


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("ngspice") is None, reason="ngspice 42 is not installed")
def test_one_overdriven_part_makes_the_design_a_violation(live):
    context = {"ambient_c": 25, "thermal_scope_confirmed": True}
    safe = live.run_design(request(two_leds(), rating_context=context))
    hot = live.run_design(request(two_leds(r2=22), rating_context=context))
    assert safe["status"] == hot["status"] == "ran"
    assert "D2" not in safe["design_summary"]["violating_parts"]
    assert hot["rating_status"] == "violation" and "D2" in hot["design_summary"]["violating_parts"]
    rows = {r["ref"]: r for r in hot["ratings"]["components"]}
    assert rows["D1"]["status"] != "violation"
    assert any(c["name"] == "forward current" and c["status"] == "violation" for c in rows["D2"]["reference_checks"])


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("ngspice") is None, reason="ngspice 42 is not installed")
def test_design_transient_checks_every_part(live):
    result = live.run_design(request(two_leds(), analysis="tran", tstep="1u", tstop="100u",
                                     rating_context={"ambient_c": 25}))
    assert result["status"] == "ran", result["problems"]
    rows = result["ratings"]["components"]
    assert len(rows) == 4 and all(r["basis"] and r["basis"].startswith("transient") for r in rows)
