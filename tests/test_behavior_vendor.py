"""Manufacturer simulation models bound as hashed assets (D074): TI TPS22810, TPS7A8001, TPS62160 and
Infineon IRLR8721."""

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.models import SourceAnchor
from ohmni.behavior.netlist import PSA_LIMITATION, compile_circuit, inline_asset, load_recipes
from ohmni.behavior.ratings import RatingContext, evaluate_ratings
from ohmni.behavior.runtime_models import BehaviorSelection, IdealTestInductor, RuntimeRecipe
from ohmni.domain.circuit import CircuitComponent, CircuitIR, ExternalSource, Net, PinRef
from ohmni.domain.units import Quantity, ValueRange
from ohmni.eda import simulation
from ohmni.eda.simulation import NgspiceAdapter, transient_deck

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ("OHM-100", "OHM-132", "OHM-133", "OHM-134")


@pytest.fixture(scope="module")
def registry():
    return BehaviorRegistry(repo_root=ROOT)


@pytest.fixture(scope="module")
def recipes(registry):
    return load_recipes(registry, ROOT)


def circuit(recipes, entry_id, role_nets, supplies):
    recipe = recipes.entries[entry_id]
    nets = {}
    for pin, role in recipe.terminal_roles.items():
        nets.setdefault(role_nets[role], []).append(PinRef(component="U1", pin=pin))
    return CircuitIR(ir_id=f"vendor-{entry_id}", name="vendor", components=[
        CircuitComponent(ref="U1", part_id=entry_id, package=recipe.package)], nets=[
        Net(name=name, kind="ground" if name == "gnd" else "power" if name in supplies else "signal", connections=pins,
            external_source=ExternalSource(kind="bench_supply", voltage=ValueRange.exact(Quantity.volts(supplies[name])))
            if name in supplies else None)
        for name, pins in sorted(nets.items())])


def ldo(recipes, registry, **kwargs):
    ir = circuit(recipes, "OHM-133", {"IN": "vin", "EN": "vin", "GND": "gnd", "OUT": "out", "FB": "fb", "NR": "nr"},
                 {"vin": 3.8})
    return compile_circuit(ir, registry, recipes, {"U1": BehaviorSelection(entry_id="OHM-133")}, **kwargs)


@pytest.mark.parametrize("entry_id", VENDOR)
def test_vendor_assets_are_hashed_manufacturer_bytes(entry_id, recipes):
    recipe = recipes.entries[entry_id]
    vendor = recipe.vendor_model
    assert vendor is not None and vendor.document.startswith("docs/behavior/vendor/")
    anchor = next(a for a in recipe.inline_assets if a.document == vendor.document)
    raw = (ROOT / vendor.document).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == anchor.document_sha256
    assert vendor.terms
    archive = ROOT / "out/component-behavior/run/fetched-sources" / f"{vendor.archive_sha256}.bin"
    ledger = [json.loads(line) for line in (ROOT / "out/component-behavior/run/FETCH_LEDGER.jsonl").read_text().splitlines()]
    assert any(row.get("url") == vendor.archive_url and row.get("content_sha256") == vendor.archive_sha256
               and row.get("http_status") == 200 for row in ledger)
    if not archive.is_file():
        pytest.skip("archived fetch bytes are not present in this checkout")
    data = archive.read_bytes()
    assert hashlib.sha256(data).hexdigest() == vendor.archive_sha256
    member = zipfile.ZipFile(io.BytesIO(data)).read(vendor.archive_member) if vendor.archive_member else data
    assert member == raw


def test_ti_models_quote_the_as_is_header(recipes):
    for entry_id in ("OHM-132", "OHM-133", "OHM-134"):
        recipe = recipes.entries[entry_id]
        assert '"as is" basis' in recipe.vendor_model.terms
        assert '"as is" basis' in (ROOT / recipe.vendor_model.document).read_text()
        assert recipe.ngspice_compatibility == "psa"
    assert recipes.entries["OHM-100"].ngspice_compatibility is None


def test_vendor_card_is_exempt_from_the_is0_rule_only_under_the_vendor_directory(tmp_path):
    folder = tmp_path / "docs/behavior/vendor/x"
    folder.mkdir(parents=True)
    path = folder / "card.lib"
    path.write_text(".model MM NMOS LEVEL=1 IS=1e-32\n")
    anchor = SourceAnchor(document="docs/behavior/vendor/x/card.lib", line=1,
                          document_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match="IS=0"):
        inline_asset(tmp_path, anchor)
    assert "IS=1e-32" in inline_asset(tmp_path, anchor, vendor=True)
    other = tmp_path / "card.lib"
    other.write_bytes(path.read_bytes())
    outside = SourceAnchor(document="card.lib", line=1, document_sha256=anchor.document_sha256)
    with pytest.raises(ValueError, match="vendor"):
        inline_asset(tmp_path, outside, vendor=True)


def test_vendor_provenance_is_required_for_vendor_assets(recipes):
    row = recipes.entries["OHM-133"].model_dump(mode="json")
    with pytest.raises(ValueError, match="vendor model provenance"):
        RuntimeRecipe.model_validate(dict(row, vendor_model=None))
    with pytest.raises(ValueError, match="docs/behavior/vendor"):
        RuntimeRecipe.model_validate(dict(row, vendor_model=dict(row["vendor_model"], document="docs/behavior/bench/x.lib")))
    with pytest.raises(ValueError, match="inline assets"):
        RuntimeRecipe.model_validate(dict(row, inline_assets=[]))


def test_psa_mode_is_scoped_to_decks_that_hold_a_pspice_model(registry, recipes):
    compiled = ldo(recipes, registry)
    assert compiled.runnable, compiled.problems
    assert compiled.ngspice_compatibility == "psa" and PSA_LIMITATION in compiled.limitations
    assert compiled.components[0].fidelity.value == "vendor_model"
    from tools.behavior_audit.runtime_benches import resistor_divider

    plain = compile_circuit(resistor_divider("OHM-004", "0603"), registry, recipes,
                            {r: BehaviorSelection(entry_id="OHM-004") for r in ("R1", "R2")})
    assert plain.ngspice_compatibility is None and PSA_LIMITATION not in plain.limitations


def test_bench_command_adds_psa_only_when_asked(tmp_path, monkeypatch):
    calls = []

    class Done:
        def __init__(self, out=""):
            self.returncode, self.stdout, self.stderr = 0, out, ""

    def fake(args, timeout):
        calls.append(args)
        return Done("ngspice-42 : Circuit level simulation program" if "-v" in args else "")

    monkeypatch.setattr(simulation, "run_tool", fake)
    adapter = NgspiceAdapter("ngspice")
    adapter.behavior_bench("t\n.end\n", work_dir=tmp_path / "a")
    adapter.behavior_bench("t\n.end\n", work_dir=tmp_path / "b", compatibility="psa")
    runs = [c for c in calls if "-b" in c]
    assert runs[0][1:3] != ["-D", "ngbehavior=psa"] and "-D" not in runs[0]
    assert runs[1][1:3] == ["-D", "ngbehavior=psa"]
    result = adapter.behavior_bench("t\n.end\n", work_dir=tmp_path / "c", compatibility="ps")
    assert result["status"] == "not_run" and "compatibility" in result["stderr"]


def test_transient_max_step_interpolates_only_when_requested():
    plain = transient_deck("t\nR1 a 0 1\n.end\n", "1u", "1m", ["a"])
    assert ".tran 1u 1m\n" in plain and "interp" not in plain
    stepped = transient_deck("t\nR1 a 0 1\n.end\n", "500n", "300u", ["a"], tmax="2e-08")
    assert ".options interp\n.tran 500n 300u 0 2e-08" in stepped


def test_ideal_test_inductor_is_an_explicit_fixture(registry, recipes):
    with pytest.raises(ValueError):
        IdealTestInductor(positive_net="a", negative_net="a", inductance=Quantity(value=1e-6, unit="H"))
    with pytest.raises(ValueError):
        IdealTestInductor(positive_net="a", negative_net="b", inductance=Quantity(value=1e-6, unit="F"))
    from tools.behavior_audit.runtime_benches import resistor_divider

    fixture = IdealTestInductor(positive_net="middle", negative_net="return", inductance=Quantity(value=2.2e-6, unit="H"))
    compiled = compile_circuit(resistor_divider("OHM-004", "0603"), registry, recipes,
                               {r: BehaviorSelection(entry_id="OHM-004") for r in ("R1", "R2")}, excitations=[fixture])
    assert compiled.runnable
    assert any(line.startswith("Ltest1 ") and line.endswith(" 2.2000000000000001e-06") for line in compiled.netlist.splitlines())
    assert any("Ideal test inductor" in x for x in compiled.limitations)


def test_switching_model_carries_its_maximum_step(registry, recipes):
    ir = circuit(recipes, "OHM-134", {"VIN": "vin", "EN": "vin", "AGND": "gnd", "PGND": "gnd", "SW": "sw",
                                      "VOS": "sw", "FB": "fb", "PG": "pg"}, {"vin": 12})
    compiled = compile_circuit(ir, registry, recipes, {"U1": BehaviorSelection(entry_id="OHM-134")}, analysis="tran")
    assert compiled.runnable, compiled.problems
    assert compiled.transient_max_step_s == 2e-08
    refused = compile_circuit(ir, registry, recipes, {"U1": BehaviorSelection(entry_id="OHM-134")})
    assert not refused.runnable and "analysis op" in ";".join(refused.problems)


def test_printed_typical_edge():
    from tools.behavior_audit.vendor_benches import printed_lower_edge

    assert printed_lower_edge(6.3) == pytest.approx(6.25)
    assert printed_lower_edge(79) == pytest.approx(78.5)
    assert printed_lower_edge(10.1) == pytest.approx(10.05)


def test_vendor_mosfet_check_uses_the_typical_to_maximum_interval(registry, recipes):
    from tools.behavior_audit.runtime_benches import mosfet_variants, vendor_mosfet_case

    class Audit:
        root = ROOT

        def _state(self):
            return {"run_id": "test"}

    recipe = recipes.entries["OHM-100"]
    assert mosfet_variants(recipe) == ["10V", "4V5"]
    assert mosfet_variants(recipes.entries["OHM-098"]) == [None]
    compiled, identity = vendor_mosfet_case(Audit(), "OHM-100", "10V")
    assert compiled.runnable, compiled.problems
    assert "IS=1e-32" in compiled.netlist
    row = identity["comparison"]
    assert row["minimum"] == pytest.approx(0.00625) and row["maximum"] == pytest.approx(0.0084)
    assert (row["gate_voltage"], row["test_current"]) == (10.0, 25.0)
    assert compiled.components[0].parameters["vgs_max"] == 20 and compiled.components[0].parameters["id_max"] == 50
    _, low = vendor_mosfet_case(Audit(), "OHM-100", "4V5")
    assert (low["comparison"]["gate_voltage"], low["comparison"]["test_current"]) == (4.5, 20.0)
    assert any("2.35 V" in x and "ABOVE" in x for x in recipe.limitations)


def _ratings(compilation, voltages, currents, context=None):
    c = compilation.components[0]
    op = {"node_voltages": {c.role_nodes[r].lower(): {"value": v, "unit": "V"} for r, v in voltages.items()
                            if c.role_nodes[r] != "0"},
          "branch_currents": {c.role_current_probes[r].lower(): {"value": i, "unit": "A"} for r, i in currents.items()}}
    result = {"status": "ran", "analysis": "op", "operating_point": op}
    ratings = evaluate_ratings(compilation, result, BehaviorRegistry(repo_root=ROOT), RatingContext(**(context or {})))
    return {r["name"]: r for r in ratings["components"][0]["reference_checks"]}


def test_load_switch_ratings_fail_closed(registry, recipes):
    ir = circuit(recipes, "OHM-132", {"VIN": "vin", "EN_UVLO": "vin", "GND": "gnd", "VOUT": "out", "CT": "ct",
                                      "QOD": "qod"}, {"vin": 12})
    compiled = compile_circuit(ir, registry, recipes, {"U1": BehaviorSelection(entry_id="OHM-132")}, measure_currents=True)
    assert compiled.runnable, compiled.problems
    volts = {"VIN": 12, "EN_UVLO": 12, "VOUT": 11.9, "CT": 1, "QOD": 0, "GND": 0}
    amps = {"VIN": 2.5, "VOUT": -2.5, "EN_UVLO": 0, "CT": 0, "QOD": 0, "GND": 0}
    rows = _ratings(compiled, volts, amps)
    assert rows["recommended supply"]["status"] == "within_limit"
    assert rows["continuous switch current"]["status"] == "unknown"
    assert "65 C" in rows["continuous switch current"]["reason"]
    rows = _ratings(compiled, volts, amps, {"ambient_c": 25, "thermal_scope_confirmed": True})
    assert rows["continuous switch current"]["status"] == "within_limit"
    rows = _ratings(compiled, dict(volts, VIN=19, EN_UVLO=19, VOUT=19.2), dict(amps, VIN=3.6, VOUT=-3.5),
                    {"ambient_c": 25, "thermal_scope_confirmed": True})
    assert rows["recommended supply"]["status"] == "violation"
    assert rows["recommended enable voltage"]["status"] == "violation"
    assert rows["recommended output voltage"]["status"] == "violation"
    assert rows["absolute output voltage"]["status"] == "within_limit"
    assert rows["continuous switch current"]["status"] == "violation"


def test_adjustable_ldo_ratings(registry, recipes):
    compiled = ldo(recipes, registry, measure_currents=True)
    volts = {"IN": 3.8, "EN": 3.8, "OUT": 3.3, "FB": 0.8, "NR": 0, "GND": 0}
    amps = {"IN": 0.1, "OUT": -0.1, "EN": 0, "FB": 0, "NR": 0, "GND": 0}
    rows = _ratings(compiled, volts, amps)
    assert rows["output voltage range"]["status"] == "within_limit"
    assert rows["dropout headroom"]["status"] == "within_limit"
    assert rows["recommended supply"]["status"] == "within_limit"
    rows = _ratings(compiled, dict(volts, IN=3.6, EN=3.6), amps)
    assert rows["dropout headroom"]["status"] == "unknown"
    rows = _ratings(compiled, dict(volts, FB=3.7), dict(amps, OUT=-1.2))
    assert rows["absolute FB and NR voltage"]["status"] == "violation"
    assert rows["recommended output current"]["status"] == "violation"


def test_buck_ratings(registry, recipes):
    ir = circuit(recipes, "OHM-134", {"VIN": "vin", "EN": "vin", "AGND": "gnd", "PGND": "gnd", "SW": "sw",
                                      "VOS": "out", "FB": "fb", "PG": "pg"}, {"vin": 12})
    compiled = compile_circuit(ir, registry, recipes, {"U1": BehaviorSelection(entry_id="OHM-134")},
                               analysis="tran", measure_currents=True)
    assert compiled.runnable, compiled.problems
    volts = {"VIN": 12, "EN": 12, "SW": 3.3, "VOS": 3.3, "FB": 0.8, "PG": 3.3, "AGND": 0, "PGND": 0}
    amps = {r: 0.0 for r in compiled.components[0].role_current_probes}
    rows = _ratings(compiled, volts, dict(amps, SW=-0.5, VIN=0.15))
    assert rows["recommended supply"]["status"] == "within_limit"
    assert rows["recommended output voltage"]["status"] == "within_limit"
    assert rows["power-good sink current"]["status"] == "within_limit"
    rows = _ratings(compiled, dict(volts, VOS=7.5, PG=7.5), dict(amps, SW=-1.5, PG=0.02, VIN=0.6),
                    {"ambient_c": 25, "thermal_scope_confirmed": True})
    assert rows["absolute FB, PG and VOS voltage"]["status"] == "violation"
    assert rows["recommended output voltage"]["status"] == "violation"
    assert rows["power-good sink current"]["status"] == "violation"
    assert rows["recommended output current"]["status"] == "violation"
