"""D075: programmable parts bound as electrical pins frozen in their datasheet reset state."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from ohmni.application.component_behavior import ComponentBehaviorService
from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import compile_circuit, load_recipes, pin_level_template
from ohmni.behavior.ratings import RatingContext, evaluate_ratings
from ohmni.behavior.runtime_models import BehaviorSelection, RuntimeRecipe
from ohmni.domain.circuit import CircuitComponent, CircuitIR, ExternalSource, Net, PinRef
from ohmni.domain.units import Quantity, ValueRange
from tools.behavior_audit.runtime_benches import dc_probe_definition, dc_probe_variants

ROOT = Path(__file__).resolve().parents[1]
BOUND = {
    "OHM-122": "ATmega328P-AU", "OHM-123": "ATmega32U4", "OHM-124": "STM32F405RGT6",
    "OHM-125": "STM32F407VGT6", "OHM-126": "STM32F407ZGT6", "OHM-131": "STM32F103CBU6", "OHM-138": "XC7A35T",
}
PHRASE = "electrical pins in reset state only; firmware not modeled"


@pytest.fixture(scope="module")
def registry():
    return BehaviorRegistry(repo_root=ROOT)


@pytest.fixture(scope="module")
def recipes(registry):
    return load_recipes(registry, ROOT)


@pytest.fixture(scope="module")
def audit():
    from tools.behavior_audit.audit import BehaviorAudit

    return BehaviorAudit(ROOT)


def _compile(registry, recipes, entry_id, nets, supplies):
    recipe = recipes.entries[entry_id]
    built = []
    for name, pins in nets.items():
        source = (ExternalSource(kind="bench_supply", voltage=ValueRange.exact(Quantity.volts(supplies[name])))
                  if name in supplies else None)
        built.append(Net(name=name, kind="ground" if name == "gnd" else "power" if source else "signal",
                         connections=[PinRef(component="U1", pin=pin) for pin in pins], external_source=source))
    circuit = CircuitIR(ir_id=f"d075-{entry_id}", name="D075 pin-level binding", nets=built, components=[
        CircuitComponent(ref="U1", part_id=entry_id, package=recipe.package)])
    return compile_circuit(circuit, registry, recipes, {"U1": BehaviorSelection(entry_id=entry_id)},
                           measure_currents=True)


def _by_role(recipe, assign, default="idle"):
    nets = {}
    for pin, role in recipe.terminal_roles.items():
        nets.setdefault(assign.get(role, default), []).append(pin)
    return nets


def _rows(registry, recipes, entry_id, assign, supplies, voltages, currents, context=None):
    recipe = recipes.entries[entry_id]
    compiled = _compile(registry, recipes, entry_id, _by_role(recipe, assign), supplies)
    assert compiled.runnable, compiled.problems
    component = compiled.components[0]
    nodes = {role: node.lower() for role, node in component.role_nodes.items()}
    probes = {role: probe.lower() for role, probe in component.role_current_probes.items()}
    observed = {role: 0.0 for role in probes}
    observed.update(currents)
    result = {"status": "ran", "analysis": "op", "operating_point": {
        "node_voltages": {nodes[r]: {"value": v, "unit": "V"} for r, v in voltages.items() if nodes[r] != "0"},
        "branch_currents": {probes[r]: {"value": i, "unit": "A"} for r, i in observed.items()}}}
    ratings = evaluate_ratings(compiled, result, registry, context or RatingContext(ambient_c=25))
    return {r["name"]: r for r in ratings["components"][0]["reference_checks"]}, ratings["components"][0]["status"]


def test_every_bound_part_is_a_simulable_pin_level_package(registry, recipes, tmp_path):
    service = ComponentBehaviorService(ROOT, tmp_path)
    for entry_id, part in BOUND.items():
        recipe = recipes.entries[entry_id]
        entry = registry.entry(entry_id)
        assert recipe.behavior_id == "BEH-IC-DIGITAL-IO" and recipe.pin_level is not None
        assert part in recipe.reference_part and entry.simulation_disposition.value == "simulable"
        assert PHRASE in entry.simulation_reason
        assert recipe.limitations[0].startswith("Electrical pins only, in the datasheet reset state; firmware not modeled")
        assert entry.research.simulation_blockers == []
        state, reason = service.behavior_state(entry_id)
        assert state == "simulated" and reason.endswith(f"{PHRASE}.") and part in reason


def test_atmega32u4_states_its_preliminary_dc_values(registry, recipes):
    recipe = recipes.entries["OHM-123"]
    assert any("PRELIMINARY" in item and "preliminary design target" in item for item in recipe.limitations)
    facts = {f.field: f for f in registry.entry("OHM-123").research.field_updates}
    assert facts["dc_characteristics_status"].page == 385
    for field in ("maximum_io_leakage", "reset_pullup_resistance_range", "io_pullup_resistance_range"):
        assert "PRELIMINARY" in facts[field].scope and facts[field].confidence == "M"


def test_research_corrections_are_applied(registry, recipes):
    stm32 = {f.field: f for f in registry.entry("OHM-124").research.field_updates}
    assert stm32["maximum_supply_current"].value == 240 and "Rev 12" in stm32["maximum_supply_current"].scope
    roles = stm32["manufacturer_pin_roles"].value
    assert [roles[str(p)] for p in range(47, 65)] == [
        "VCAP2", "VDD", "PA14", "PA15", "PC10", "PC11", "PC12", "PD2", "PB3", "PB4", "PB5", "PB6", "PB7",
        "BOOT0", "PB8", "PB9", "VSS", "VDD"]
    assert recipes.entries["OHM-124"].terminal_roles == roles
    avr = {f.field: f for f in registry.entry("OHM-122").research.field_updates}
    assert avr["output_low_voltage_max"].value == 0.9 and avr["output_low_test_current"].value == 20


def test_template_freezes_every_pad_in_the_reset_state(registry, recipes, audit):
    recipe = recipes.entries["OHM-122"]
    template = pin_level_template(recipe)
    pads = [line for line in template.splitlines() if line.startswith("X")]
    assert len(pads) == len(recipe.pin_level.pads) == 23
    for line in pads:
        tokens = line.split()
        assert tokens[4] == tokens[5] == tokens[8] == "{GND}"  # dout, oe and the pad ground on the ground role
        assert tokens[7] == "{VCC}"
    reset = next(line for line in pads if line.startswith("X{ref}_PC6_RESET "))
    assert reset.split()[6] == "{ref}_pu" and " dio_pin_ft " in reset and "rpu={rpu_rst}" in reset
    assert all(line.split()[6] == "{GND}" for line in pads if "PC6_RESET" not in line)
    compiled, identity = dc_probe_definition(audit, "OHM-122", "pullup_rpu_rst")
    instances = [line.split()[9] for line in compiled.netlist.splitlines() if line.startswith("Xc1_")]
    assert compiled.runnable and instances.count("dio_pin") == 22 and instances.count("dio_pin_ft") == 1
    assert ".subckt dio_pin_ft" in compiled.netlist and ".subckt dio_pin " in compiled.netlist
    assert identity["comparison"]["pin_role"] == "PC6_RESET"
    assert identity["comparison"]["minimum"] == pytest.approx(5.5 / 60e3)
    assert identity["comparison"]["maximum"] == pytest.approx(5.5 / 30e3)


def test_no_upper_clamp_variant_only_drops_the_supply_clamp():
    base = (ROOT / "docs/behavior/bench/ic-digital-io/dio.lib").read_text().splitlines()
    variant = (ROOT / "docs/behavior/models/dio_ft.lib").read_text().splitlines()
    code = [line for line in base if not line.startswith("*")]
    expected = [line.replace(".subckt dio_pin ", ".subckt dio_pin_ft ") for line in code if not line.startswith("Dh ")]
    assert [line for line in variant if not line.startswith("*")] == expected


def test_probe_variants_cover_each_pad_model_and_pull_kind(recipes):
    expected = {
        "OHM-122": ["hiz_dio_pin", "pullup_rpu_rst"],
        "OHM-123": ["hiz_dio_pin", "pullup_rpu_io", "pullup_rpu_rst"],
        "OHM-124": ["hiz_dio_pin_ft", "hiz_dio_pin", "pullup_nrst_rpu_typ"],
        "OHM-131": ["hiz_dio_pin", "hiz_dio_pin_ft", "pullup_nrst_rpu_typ", "pullup_rpu_io_typ"],
        "OHM-138": ["hiz_dio_pin"],
    }
    for entry_id, variants in expected.items():
        recipe = recipes.entries[entry_id]
        assert dc_probe_variants(recipe.behavior_id, recipe) == variants


def test_fpga_probe_honors_the_documented_mode_pins(audit):
    compiled, identity = dc_probe_definition(audit, "OHM-138", "hiz_dio_pin")
    assert compiled.runnable, compiled.problems
    comparison = identity["comparison"]
    assert comparison["maximum"] == pytest.approx(15e-6) and comparison["supply_voltages"]["VCCO_14"] == 3.465
    assert "M[2:0] = 101" in comparison["reset_state"]
    assert comparison["pin_role"] != "IO_L3P_T0_DQS_PUDC_B_14"


def test_pin_level_model_must_classify_every_role(recipes):
    data = recipes.entries["OHM-122"].model_dump(mode="json", exclude_none=True)
    broken = dict(data, pin_level=dict(data["pin_level"], unmodeled=["ADC6", "ADC7"]))
    with pytest.raises(ValidationError, match="classify exactly"):
        RuntimeRecipe.model_validate(broken)
    with pytest.raises(ValidationError, match="generates its template"):
        RuntimeRecipe.model_validate(dict(data, template_override="R1 a b 1"))
    with pytest.raises(ValidationError, match="exactly one of"):
        RuntimeRecipe.model_validate(dict(data, pin_level=dict(data["pin_level"], tied=["AVCC", "ADC6"])))


AVR = {"VCC": "vcc", "AVCC": "vcc", "GND": "gnd", "PB0": "pb0", "PC6_RESET": "reset"}


def test_avr_pin_and_supply_windows(registry, recipes):
    rows, status = _rows(registry, recipes, "OHM-122", AVR, {"vcc": 5.0}, {"VCC": 5.0, "PB0": 5.4, "PC6_RESET": 5.0}, {})
    assert rows["recommended supply VCC"]["status"] == "within_limit"
    assert rows["absolute supply VCC"]["status"] == "within_limit"
    assert rows["pin PB0 voltage"]["status"] == "within_limit"
    assert rows["supply current VCC"]["status"] == "unknown" and "lower bound" in rows["supply current VCC"]["reason"]
    assert rows["junction temperature"]["status"] == "unknown" and "publishes no thermal" in rows["junction temperature"]["reason"]
    assert rows["unmodeled pins"]["status"] == "unknown" and "ADC6" in rows["unmodeled pins"]["reason"]
    assert status == "unknown"
    rows, status = _rows(registry, recipes, "OHM-122", AVR, {"vcc": 5.0}, {"VCC": 5.0, "PB0": 5.6}, {"PB0": 0.041, "VCC": -0.201})
    assert rows["pin PB0 voltage"]["status"] == "violation" and rows["pin PB0 current"]["status"] == "violation"
    assert rows["supply current VCC"]["status"] == "violation" and status == "violation"
    rows, _ = _rows(registry, recipes, "OHM-122", AVR, {"vcc": 6.5}, {"VCC": 6.5}, {})
    assert rows["absolute supply VCC"]["status"] == "violation"


def test_avr_reset_above_the_supply_is_unknown_until_its_rating(registry, recipes):
    rows, _ = _rows(registry, recipes, "OHM-122", AVR, {"vcc": 5.0, "reset": 12.0}, {"VCC": 5.0, "PC6_RESET": 12.0}, {})
    assert rows["pin PC6_RESET voltage"]["status"] == "within_limit"
    assert rows["pin PC6_RESET reset-state condition"]["status"] == "unknown"
    assert "+13.0 V" in rows["pin PC6_RESET reset-state condition"]["reason"]
    rows, _ = _rows(registry, recipes, "OHM-122", AVR, {"vcc": 5.0, "reset": 13.5}, {"VCC": 5.0, "PC6_RESET": 13.5}, {})
    assert rows["pin PC6_RESET voltage"]["status"] == "violation"


STM = {"VDD": "vdd", "VDDA": "vdd", "VSS": "gnd", "VSSA": "gnd", "PA0": "ft", "PA4": "tta"}


def test_stm32_five_volt_tolerant_and_other_pins(registry, recipes):
    rows, _ = _rows(registry, recipes, "OHM-124", STM, {"vdd": 3.3}, {"VDD": 3.3, "PA0": 7.2, "PA4": 3.9},
                    {"PA0": 0.0, "PA4": 0.004})
    assert rows["pin PA0 voltage"]["status"] == "within_limit"  # FT: VDD + 4
    assert rows["pin PA4 voltage"]["status"] == "within_limit"  # TTa: 4.0 V absolute
    assert rows["pin PA4 injected current"]["status"] == "within_limit"
    assert rows["total injected current"]["status"] == "within_limit"
    rows, _ = _rows(registry, recipes, "OHM-124", STM, {"vdd": 3.3}, {"VDD": 3.3, "PA0": 7.4, "PA4": 4.1},
                    {"PA0": -0.006, "PA4": 0.006})
    assert rows["pin PA0 voltage"]["status"] == "violation" and rows["pin PA4 voltage"]["status"] == "violation"
    assert rows["pin PA0 injected current"]["status"] == "violation"  # FT: -5/+0 mA, negative side
    assert rows["pin PA4 injected current"]["status"] == "violation"
    rows, _ = _rows(registry, recipes, "OHM-124", STM, {"vdd": 3.3}, {"VDD": 3.3}, {"PA0": 0.02, "PA4": -0.007})
    assert rows["total injected current"]["status"] == "violation"
    rows, _ = _rows(registry, recipes, "OHM-124", STM, {"vdd": 3.3}, {"VDD": 3.3}, {"VDD": -0.25},
                    RatingContext(ambient_c=25, thermal_scope_confirmed=True))
    assert rows["supply current VDD"]["status"] == "violation"
    assert rows["junction temperature"]["status"] == "unknown"  # pin power is only a lower bound


def test_stm32f103_pulled_ft_pin_above_supply_is_unknown(registry, recipes):
    assign = {"VDD1": "vdd", "VDD2": "vdd", "VDD3": "vdd", "VDDA": "vdd", "VSS1": "gnd", "VSS2": "gnd",
              "VSS3": "gnd", "VSSA": "gnd", "EP": "gnd", "PA13": "swdio"}
    rows, _ = _rows(registry, recipes, "OHM-131", assign, {"vdd": 3.3}, {"VDD1": 3.3, "PA13": 3.5}, {})
    assert rows["pin PA13 reset-state condition"]["status"] == "within_limit"
    rows, _ = _rows(registry, recipes, "OHM-131", assign, {"vdd": 3.3}, {"VDD1": 3.3, "PA13": 4.0}, {})
    assert rows["pin PA13 reset-state condition"]["status"] == "unknown" and "0.3 V" in rows["pin PA13 reset-state condition"]["reason"]
    assert rows["pin PA13 voltage"]["status"] == "within_limit"


def test_fpga_pads_follow_their_own_bank_supply(registry, recipes):
    recipe = recipes.entries["OHM-138"]
    assign = {role: "gnd" for role in ("GND", "M1_0")}
    assign.update({"VCCINT": "core", "VCCBRAM": "core", "VCCAUX": "aux", "VCCO_0": "o33", "M0_0": "o33",
                   "M2_0": "o33", "CFGBVS_0": "o33", "VCCO_14": "o14", "IO_L3P_T0_DQS_PUDC_B_14": "o14",
                   "VCCO_15": "o33", "VCCO_34": "o18", "VCCO_35": "o33", "IO_0_14": "pin"})
    supplies = {"core": 1.0, "aux": 1.8, "o33": 3.3, "o14": 3.3, "o18": 1.8}
    rows, _ = _rows(registry, recipes, "OHM-138", assign, supplies,
                    {"VCCINT": 1.0, "VCCBRAM": 1.0, "VCCAUX": 1.8, "VCCO_0": 3.3, "VCCO_14": 3.3, "VCCO_15": 3.3,
                     "VCCO_34": 1.8, "VCCO_35": 3.3, "IO_0_14": 3.8}, {"IO_0_14": 0.004})
    assert rows["recommended supply VCCINT"]["status"] == "within_limit"
    assert rows["pin IO_0_14 voltage"]["status"] == "within_limit"  # VCCO_14 + 0.55
    assert rows["pin IO_0_14 injected current"]["status"] == "within_limit"
    assert rows["bank 14 clamp current"]["status"] == "within_limit"
    assert len([name for name in rows if name.endswith("clamp current")]) == 4
    rows, _ = _rows(registry, recipes, "OHM-138", assign, dict(supplies, core=1.2),
                    {"VCCINT": 1.2, "VCCO_14": 3.3, "IO_0_14": 3.9}, {"IO_0_14": 0.011})
    assert rows["absolute supply VCCINT"]["status"] == "violation"
    assert rows["pin IO_0_14 voltage"]["status"] == "violation" and rows["pin IO_0_14 injected current"]["status"] == "violation"
    assert recipe.pin_level.pads["IO_0_14"].supply == "VCCO_14"


def test_unsourced_limit_leaves_its_row_unknown(registry, recipes):
    recipe = recipes.entries["OHM-122"]
    compiled = _compile(registry, recipes, "OHM-122", _by_role(recipe, AVR), {"vcc": 5.0})
    component = compiled.components[0]
    evidence = dict(component.parameter_evidence)
    evidence["vpin_over_supply_max"] = dict(evidence["vpin_over_supply_max"], basis="ASSUMPTION")
    weakened = compiled.model_copy(update={"components": [component.model_copy(update={"parameter_evidence": evidence})]})
    nodes = {role: node.lower() for role, node in component.role_nodes.items()}
    result = {"status": "ran", "analysis": "op", "operating_point": {
        "node_voltages": {nodes["VCC"]: {"value": 5.0, "unit": "V"}, nodes["PB0"]: {"value": 9.0, "unit": "V"}},
        "branch_currents": {}}}
    rows = {r["name"]: r for r in evaluate_ratings(weakened, result, registry)["components"][0]["reference_checks"]}
    assert rows["pin PB0 voltage"]["status"] == "unknown" and "Missing sourced limit" in rows["pin PB0 voltage"]["reason"]
