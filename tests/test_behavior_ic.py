"""Reference functions and typed waveforms cannot bypass evidence or pin maps."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from ohmni.behavior.loader import BehaviorRegistry, BehaviorRegistryError
from ohmni.behavior.netlist import load_recipes, validate_reference_function
from ohmni.behavior.runtime_models import PWLExcitation
from ohmni.domain.units import Quantity
from tools.behavior_audit.audit import BehaviorAudit
from tools.behavior_audit.ic_benches import ic_definition

ROOT = Path(__file__).resolve().parents[1]
FIRST_IC_BATCH = (104, 105, 106, 110, 111, 112, 114, 115, 119, 120)


@pytest.fixture(scope="module")
def registry():
    return BehaviorRegistry(repo_root=ROOT)


@pytest.fixture(scope="module")
def recipes(registry):
    return load_recipes(registry, ROOT)


@pytest.mark.parametrize("number", FIRST_IC_BATCH)
def test_package_reference_keeps_every_sourced_terminal(number, registry, recipes):
    key = f"OHM-{number:03}"
    entry, recipe = registry.entry(key), recipes.entries[key]
    roles = next(f for f in entry.research.field_updates if f.field == "manufacturer_pin_roles")
    assert recipe.terminal_roles == roles.value
    compiled, identity = ic_definition(BehaviorAudit(ROOT), key)
    assert compiled.runnable, compiled.problems
    component = next(c for c in compiled.components if c.ref == "U1")
    assert set(component.terminal_nodes) == set(roles.value)
    assert component.parameter_evidence["terminal_roles"]["sources"] == roles.sources
    assert component.fidelity.value == "behavioural_approximation"
    assert identity["analytical_source"].startswith(recipe.behavior_id + "/")
    assert ".include" not in compiled.netlist
    assert ".options tnom=25\n.temp 25" in compiled.netlist


def test_package_cannot_acquire_a_function_by_class_name_alone(registry, recipes):
    recipe = recipes.entries["OHM-104"]
    with pytest.raises(BehaviorRegistryError, match="without a sourced reference"):
        validate_reference_function(registry.entry("OHM-104"), recipe.model_copy(update={"reference_function": None}))
    wrong = recipe.reference_function.model_copy(update={"value": "unresearched replacement"})
    with pytest.raises(BehaviorRegistryError, match="does not match"):
        validate_reference_function(registry.entry("OHM-104"), recipe.model_copy(update={"reference_function": wrong}))


def test_assumed_reference_is_not_a_sourced_function(registry, recipes):
    entry = registry.entry("OHM-104")
    facts = [f.model_copy(update={"basis": "ASSUMPTION"}) if f.field == "reference_part" else f
             for f in entry.research.field_updates]
    changed = entry.model_copy(update={"research": entry.research.model_copy(update={"field_updates": facts})})
    with pytest.raises(BehaviorRegistryError, match="does not match"):
        validate_reference_function(changed, recipes.entries[entry.entry_id])


def test_shared_package_models_keep_all_channels_and_ldo_nc():
    audit = BehaviorAudit(ROOT)
    nand, _ = ic_definition(audit, "OHM-105")
    dual, _ = ic_definition(audit, "OHM-119")
    ldo, _ = ic_definition(audit, "OHM-120")
    assert sum(line.startswith("X") and "hc_nand2" in line for line in nand.netlist.splitlines()) == 4
    assert sum(line.startswith("X") and "opamp_gp" in line for line in dual.netlist.splitlines()) == 2
    nc = ldo.components[0].role_nodes["NC"]
    assert all(nc not in line.split()[1:] for line in ldo.netlist.splitlines())
    assert ".nodeset" in ldo.netlist and "0.9*" not in ldo.netlist


def _point(time, value, unit="V"):
    return {"time": Quantity(value=time, unit="s"), "value": Quantity(value=value, unit=unit)}


@pytest.mark.parametrize("points", [
    [_point(1, 0), _point(2, 1)],
    [_point(0, 0), _point(0, 1)],
    [_point(0, 0), _point(-1, 1)],
    [_point(0, 0), _point(1, 1, "A")],
    [_point(0, 0), _point(float("inf"), 1)],
])
def test_waveforms_require_unambiguous_units_and_order(points):
    with pytest.raises(ValidationError):
        PWLExcitation(positive_net="clock", negative_net="return", points=points)


def test_shift_register_clock_is_typed_and_all_eight_bits_are_observed():
    compiled, identity = ic_definition(BehaviorAudit(ROOT), "OHM-106")
    assert len(compiled.excitations) == 5
    assert all(isinstance(x, PWLExcitation) for x in compiled.excitations)
    assert identity["observe_nets"] == ["Q" + c for c in "ABCDEFGH"]
    assert [r["expected"] for r in identity["comparison"]] == [0, 1, 0, 0, 1, 1, 0, 1]
    assert compiled.netlist.count(" PWL(") == 5
