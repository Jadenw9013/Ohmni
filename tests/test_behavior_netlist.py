"""Behavior compilation preserves topology, evidence and non-run semantics."""

from pathlib import Path

import pytest

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import compile_circuit, load_recipes, terminal_nodes
from ohmni.behavior.runtime_models import BehaviorSelection
from ohmni.domain.circuit import CircuitComponent, CircuitIR, ExternalSource, Net, NetKind, PinRef
from ohmni.domain.units import Quantity, ValueRange
from ohmni.eda.simulation import NgspiceAdapter

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def registry():
    return BehaviorRegistry(repo_root=ROOT)


@pytest.fixture(scope="module")
def recipes(registry):
    return load_recipes(registry, ROOT)


def divider(entry_id="OHM-004", package="0603", part_id="GENERIC_RESISTOR"):
    return CircuitIR(ir_id="behavior-divider", name="Explicit divider", components=[
        CircuitComponent(ref=ref, part_id=part_id, package=package, value=Quantity.ohms(10000))
        for ref in ["R1", "R2"]
    ], nets=[
        Net(name="supply", kind="power", connections=[PinRef(component="R1", pin="1")],
            external_source=ExternalSource(kind="bench_supply", voltage=ValueRange.exact(Quantity.volts(5)))),
        Net(name="middle", connections=[PinRef(component="R1", pin="2"), PinRef(component="R2", pin="1")]),
        Net(name="return", kind="ground", connections=[PinRef(component="R2", pin="2")]),
    ])


def test_catalog_join_is_explicit_and_deterministic(registry, recipes):
    circuit = divider()
    a = compile_circuit(circuit, registry, recipes)
    b = compile_circuit(circuit.model_copy(update={"nets": list(reversed(circuit.nets))}), registry, recipes)
    assert a.runnable and b.runnable
    assert a.netlist == b.netlist
    assert a.netlist_sha256 == b.netlist_sha256
    assert ".options tnom=25\n.temp 25" in a.netlist
    assert ".include" not in a.netlist
    assert a.components[0].parameters["p_rated"] == 0.1
    assert a.components[0].parameter_evidence["p_rated"]["scope"].startswith("Vishay CRCW0603")
    assert a.components[0].source_status == "partial"
    assert a.components[0].confidence == "M"
    assert a.components[0].rating_confidence == "H"
    assert a.components[0].source_confidence == registry.behavior_class("BEH-RES-FIXED").canonical_payload["confidence"]


@pytest.mark.parametrize("entry_id", [f"OHM-{i:03}" for i in range(1, 11)])
def test_every_first_batch_entry_uses_its_sourced_fields(entry_id, registry, recipes):
    recipe = recipes.entries[entry_id]
    circuit = divider(entry_id, recipe.package, entry_id)
    choices = {c.ref: BehaviorSelection(entry_id=entry_id) for c in circuit.components}
    result = compile_circuit(circuit, registry, recipes, choices)
    assert result.runnable, result.problems
    for component in result.components:
        for alias, binding in recipe.critical_facts.items():
            fact = next(f for f in registry.entry(entry_id).research.field_updates if f.field == binding.field)
            assert component.parameters[alias] == fact.value
            assert component.parameter_evidence[alias]["sources"] == fact.sources


def test_missing_rating_refuses_entire_circuit(registry, recipes, monkeypatch):
    entry = registry.entry("OHM-004")
    research = entry.research.model_copy(update={"field_updates": [f for f in entry.research.field_updates
                                                                  if f.field != "reference.p_rated"]})
    monkeypatch.setitem(registry.entries, entry.entry_id, entry.model_copy(update={"research": research}))
    result = compile_circuit(divider(), registry, recipes)
    assert not result.runnable and result.netlist is None
    assert "critical field reference.p_rated" in ";".join(result.problems)


def test_assumed_rating_refuses_simulation(registry, recipes, monkeypatch):
    entry = registry.entry("OHM-004")
    facts = [f.model_copy(update={"basis": "ASSUMPTION"}) if f.field == "reference.p_rated" else f
             for f in entry.research.field_updates]
    monkeypatch.setitem(registry.entries, entry.entry_id,
                        entry.model_copy(update={"research": entry.research.model_copy(update={"field_updates": facts})}))
    assert "unsourced" in ";".join(compile_circuit(divider(), registry, recipes).problems)


def test_wrong_package_and_unknown_selection_are_not_substituted(registry, recipes):
    result = compile_circuit(divider(package="0805"), registry, recipes,
                             {"R1": BehaviorSelection(entry_id="OHM-004")})
    assert not result.runnable
    assert "package differs" in ";".join(result.problems)
    bad = compile_circuit(divider(), registry, recipes, {"R1": BehaviorSelection(entry_id="OHM-083")})
    assert not bad.runnable and "primary-source" in ";".join(bad.problems)


def test_missing_pin_and_separate_ground_nets_are_not_shortened(registry, recipes):
    circuit = divider()
    circuit.nets[1].connections.pop()
    assert "connected pins" in ";".join(compile_circuit(circuit, registry, recipes).problems)
    circuit = divider()
    circuit.nets.append(Net(name="isolated_return", kind="ground"))
    assert "separate grounds" in ";".join(compile_circuit(circuit, registry, recipes).problems)


def test_led_catalog_permutation_reaches_the_correct_nodes(registry, monkeypatch):
    circuit = divider()
    component = circuit.components[0].model_copy(update={"part_id": "GENERIC_LED_GREEN", "package": "0603"})
    nodes = {net.name: net.name for net in circuit.nets}
    bound = terminal_nodes(circuit, component, "OHM-078", {"1": "K", "2": "A"}, registry, nodes)
    assert bound == {"1": "middle", "2": "supply"}
    monkeypatch.delitem(registry.bindings, "GENERIC_LED_GREEN")
    with pytest.raises(ValueError, match="permutation is missing"):
        terminal_nodes(circuit, component, "OHM-078", {"1": "K", "2": "A"}, registry, nodes)


def test_zero_resistance_is_not_silently_replaced(registry, recipes):
    circuit = divider()
    circuit.components[0].value = Quantity.ohms(0)
    assert "zero-value substitution" in ";".join(compile_circuit(circuit, registry, recipes).problems)


@pytest.mark.parametrize("analysis", ["op", "tran"])
def test_empty_tool_success_is_not_a_result(registry, recipes, tmp_path, monkeypatch, analysis):
    compiled = compile_circuit(divider(), registry, recipes, analysis=analysis)
    adapter = NgspiceAdapter(executable="fake")
    monkeypatch.setattr(adapter, "behavior_bench", lambda *_a, **_k: {
        "status": "ran", "stdout": "", "stderr": "", "version_output": "ngspice-42"})
    result = adapter.behavior_circuit(compiled, work_dir=tmp_path, analysis=analysis)
    assert result["status"] == "failed"
    assert result["operating_point"] is None and result["transient"] is None


def test_blocked_compile_never_invokes_the_solver(registry, recipes, tmp_path, monkeypatch):
    compiled = compile_circuit(divider(package="unknown"), registry, recipes)
    adapter = NgspiceAdapter(executable="fake")
    def unexpected(*args, **kwargs):
        raise AssertionError("must not run")
    monkeypatch.setattr(adapter, "behavior_bench", unexpected)
    result = adapter.behavior_circuit(compiled, work_dir=tmp_path)
    assert result["status"] == "not_run" and result["problems"]


def test_analysis_must_match_the_validated_compilation(registry, recipes, tmp_path):
    compiled = compile_circuit(divider(), registry, recipes)
    result = NgspiceAdapter(executable="fake").behavior_circuit(compiled, work_dir=tmp_path, analysis="tran")
    assert result["status"] == "not_run"


@pytest.mark.parametrize("step,stop", [("0s", "1ms"), ("-1us", "1ms"), ("1ms", "1us"),
                                      ("1us\n.shell whoami", "1ms")])
def test_invalid_time_arguments_never_reach_the_solver(registry, recipes, tmp_path, step, stop):
    compiled = compile_circuit(divider(), registry, recipes, analysis="tran")
    result = NgspiceAdapter(executable="fake").behavior_circuit(
        compiled, work_dir=tmp_path, analysis="tran", tstep=step, tstop=stop)
    assert result["status"] == "not_run"
    assert "Invalid transient" in ";".join(result["problems"])


@pytest.mark.parametrize("entry_id", ["OHM-011", "OHM-012", "OHM-013"])
def test_power_resistor_equations_come_from_explicit_binding(entry_id, registry, recipes):
    recipe = recipes.entries[entry_id]
    circuit = divider(entry_id, recipe.package, entry_id)
    choices = {c.ref: BehaviorSelection(entry_id=entry_id) for c in circuit.components}
    compiled = compile_circuit(circuit, registry, recipes, choices)
    assert compiled.runnable, compiled.problems
    if entry_id in {"OHM-012", "OHM-013"}:
        assert compiled.components[0].parameters["u_limit"] ** 2 == pytest.approx(5 * 10000)
        assert compiled.components[0].parameter_evidence["u_limit"]["basis"] == "DERIVED"


@pytest.mark.parametrize("entry_id", ["OHM-098", "OHM-099", "OHM-102"])
def test_mosfet_binding_selects_the_sourced_pins_and_inlines_assets(entry_id, registry, recipes):
    from tools.behavior_audit.runtime_benches import mosfet_case

    compiled, point = mosfet_case(registry, recipes, entry_id)
    assert compiled.runnable, compiled.problems
    assert ".include" not in compiled.netlist
    assert "IS=0" in compiled.netlist
    assert point["source_fact"]["basis"] == "MFR_DATASHEET"
    assert compiled.components[0].parameters["vds_max"] in {55, 200, 150}
    assert compiled.components[0].role_nodes == {"G": compiled.node_names["gate"],
                                                 "D": compiled.node_names["drain"],
                                                 "S": "0"}


def test_manufacturer_pin_permutation_is_checked_again(registry, recipes):
    from tools.behavior_audit.runtime_benches import mosfet_case

    row = recipes.entries["OHM-098"].model_copy(update={"terminal_roles": {"1": "S", "2": "D", "3": "G"}})
    changed = recipes.model_copy(update={"entries": dict(recipes.entries, **{"OHM-098": row})})
    compiled, _ = mosfet_case(registry, changed, "OHM-098")
    assert not compiled.runnable
    assert "manufacturer map" in ";".join(compiled.problems)


def test_mosfet_asset_requires_explicit_zero_is_and_matching_hash(tmp_path):
    import hashlib

    from ohmni.behavior.models import SourceAnchor
    from ohmni.behavior.netlist import inline_asset

    path = tmp_path / "fixture.lib"
    path.write_text(".model UNIT_NMOS NMOS(LEVEL=1 IS=1e-14)\n")
    anchor = SourceAnchor(document="fixture.lib", line=1, document_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match="IS=0"):
        inline_asset(tmp_path, anchor)
    path.write_text(".model UNIT_NMOS NMOS(LEVEL=1 IS=0)\n")
    with pytest.raises(ValueError, match="asset changed"):
        inline_asset(tmp_path, anchor)


def test_expression_evaluator_refuses_unknowns_and_code():
    from ohmni.behavior.expressions import ExpressionUnavailable, evaluate

    assert evaluate("sqrt(p*R)", {"p": 5, "R": 20}) == 10
    for expression in ("missing+1", "__import__('os').system('whoami')", "values[0]", "10**10000", "1/0"):
        with pytest.raises(ExpressionUnavailable):
            evaluate(expression, {})


def test_dc_excitations_are_explicit_and_cannot_override_declared_sources(registry, recipes):
    from ohmni.behavior.runtime_models import DCExcitation

    circuit = divider()
    duplicate = DCExcitation(positive_net="supply", negative_net="return", value=Quantity.volts(12))
    compiled = compile_circuit(circuit, registry, recipes, excitations=[duplicate])
    assert not compiled.runnable
    assert any("Duplicate ideal voltage" in p for p in compiled.problems)
    missing = duplicate.model_copy(update={"positive_net": "not-in-circuit"})
    assert not compile_circuit(circuit, registry, recipes, excitations=[missing]).runnable


def test_pin_strays_are_only_to_ground_and_require_capacitance_evidence():
    from ohmni.behavior.netlist import pin_ground_strays

    rows = pin_ground_strays({"A": "n1", "B": "n2", "GND": "0"}, {"cin": 2e-12},
                             {"cin": {"unit": "F"}}, {"A": "cin", "B": "cin", "GND": "cin"}, "c1")
    assert len(rows) == 2
    assert all(row.split()[2] == "0" for row in rows)
    with pytest.raises(ValueError, match="farads"):
        pin_ground_strays({"A": "n1"}, {"cin": 2}, {"cin": {"unit": "V"}}, {"A": "cin"}, "c1")


def test_authored_startup_nodeset_cannot_be_dropped(registry, recipes, monkeypatch):
    from copy import deepcopy

    original_lookup = registry.behavior_class
    behavior = original_lookup("BEH-RES-FIXED").model_copy(deep=True)
    behavior.canonical_payload["model"]["netlist_template"] += ".nodeset v({B})=2.5\n"
    monkeypatch.setattr(registry, "behavior_class", lambda key: behavior if key == behavior.behavior_id else original_lookup(key))
    compiled = compile_circuit(divider(), registry, recipes)
    assert compiled.runnable and ".nodeset v(n1)=2.5" in compiled.netlist
    override = deepcopy(recipes)
    row = override.entries["OHM-004"].model_copy(update={
        "template_override": original_lookup("BEH-RES-FIXED").canonical_payload["model"]["netlist_template"],
        "template_provenance": behavior.source,
    })
    override.entries["OHM-004"] = row
    result = compile_circuit(divider(), registry, override)
    assert not result.runnable and any("preserve its authored nodeset" in p for p in result.problems)


@pytest.mark.parametrize("entry_id", ["OHM-045", "OHM-046", "OHM-048", "OHM-049", "OHM-057", "OHM-058", "OHM-062", "OHM-063", "OHM-073", "OHM-097"])
def test_scoped_runtime_references_compile_with_provenance(entry_id):
    from tools.behavior_audit.audit import BehaviorAudit
    from tools.behavior_audit.runtime_benches import dc_probe_definition

    compiled, identity = dc_probe_definition(BehaviorAudit(ROOT), entry_id)
    assert compiled.runnable, compiled.problems
    assert compiled.components[0].reference_part
    assert compiled.components[0].fidelity == "behavioural_approximation"
    assert identity["entry_research_sha256"]
    assert ".include" not in compiled.netlist
    if entry_id in {"OHM-057", "OHM-058", "OHM-062", "OHM-063", "OHM-073"}:
        assert compiled.components[0].terminal_nodes["1"] == "0"
        assert compiled.components[0].role_nodes["K"] == "0"
    if entry_id == "OHM-097":
        # Geometric mean of the sourced ungraded hFE range 40..250 (onsemi BD139 Rev 3).
        assert compiled.components[0].parameters["BF"] == pytest.approx((40 * 250) ** 0.5)
        assert "Fairchild" in compiled.components[0].reference_part


def test_fixed_reference_cannot_accept_another_inductance(registry, recipes):
    recipe = recipes.entries["OHM-045"]
    circuit = divider("OHM-045", recipe.package, "OHM-045")
    # The divider factory deliberately supplies 10 kohm: dimensional mismatch
    # must be refused instead of silently using a fixed inductor value.
    choices = {c.ref: BehaviorSelection(entry_id="OHM-045") for c in circuit.components}
    assert not compile_circuit(circuit, registry, recipes, choices).runnable
    circuit = circuit.model_copy(update={"components": [c.model_copy(update={"value": Quantity(value=2.2e-6, unit="H")}) for c in circuit.components]})
    result = compile_circuit(circuit, registry, recipes, choices)
    assert not result.runnable
    assert any("differs from the fixed sourced reference" in p for p in result.problems)


def test_inductor_definitions_and_uncertainty_are_not_interchanged():
    from tools.behavior_audit.audit import BehaviorAudit
    from tools.behavior_audit.runtime_benches import dc_probe_definition

    for entry_id, drop in [("OHM-045", .2), ("OHM-046", .1), ("OHM-048", .1), ("OHM-049", 1-22.8/33)]:
        compiled, _ = dc_probe_definition(BehaviorAudit(ROOT), entry_id)
        component = compiled.components[0]
        assert component.parameters["drop"] == pytest.approx(drop)
        assert component.parameter_evidence["lr"]["basis"] == "ASSUMPTION"
        if entry_id == "OHM-048":
            assert "typical value" in component.parameter_evidence["irms"]["scope"]
        if entry_id == "OHM-049":
            assert component.parameter_evidence["cp_placeholder_pf"]["basis"] == "ASSUMPTION"


def test_entry_specific_assumption_requires_its_exact_source_fragment(registry, recipes):
    from ohmni.behavior.netlist import _parameter_defaults

    recipe = recipes.entries["OHM-057"]
    changed = recipe.model_copy(update={"quoted_parameters": {"TT_us": recipe.quoted_parameters["TT_us"].model_copy(update={"source_fragment": "invented 3 us data"})}})
    with pytest.raises(ValueError, match="does not relocate"):
        _parameter_defaults(registry.behavior_class(recipe.behavior_id), changed, {}, {}, ROOT)


@pytest.mark.parametrize("entry_id,variant", [
    ("OHM-014", None), ("OHM-016", None), ("OHM-064", None),
    ("OHM-071", "positive"), ("OHM-071", "negative"),
    ("OHM-074", None), ("OHM-077", None), ("OHM-079", None),
    ("OHM-080", None), ("OHM-081", None),
    ("OHM-082", "red"), ("OHM-082", "green"), ("OHM-082", "blue"),
])
def test_bound_network_bridge_and_led_probes(entry_id, variant):
    from tools.behavior_audit.audit import BehaviorAudit
    from tools.behavior_audit.runtime_benches import dc_probe_definition

    compiled, identity = dc_probe_definition(BehaviorAudit(ROOT), entry_id, variant)
    assert compiled.runnable, compiled.problems
    assert identity.get("variant") == variant
    assert compiled.components[0].source_status == ("research_required" if entry_id == "OHM-071" else "partial")
    if entry_id == "OHM-014":
        assert compiled.components[0].parameters["tcr"] == 110
        assert set(compiled.components[0].terminal_nodes) == {"1", "2"}
        assert identity["comparison"]["expected"] == .05
    if entry_id == "OHM-016":
        component = compiled.components[0]
        assert component.parameters["p_element"] == .2
        assert component.parameters["p_package"] == 1
        assert len(component.element_names) == 7
        assert identity["comparison"]["expected"] == .0035
        assert component.terminal_nodes["1"] == "0"
        assert all(component.terminal_nodes[str(i)] != "0" for i in range(2,9))
    if entry_id == "OHM-082":
        component = compiled.components[0]
        cathode_pin = {"red": "4", "green": "3", "blue": "2"}[variant]
        assert component.terminal_nodes[cathode_pin] == "0"
        assert component.terminal_nodes["1"] != "0"
        assert all(component.terminal_nodes[pin] == component.terminal_nodes["1"]
                   for pin in {"2", "3", "4"} - {cathode_pin})


def test_df10m_rotation_and_pin_permutation(registry, recipes):
    # Independently rotate the manufacturer marking view into the library's
    # top-left-first CCW convention. Diagonal AC pins would fail this test.
    entry = registry.entry("OHM-071")
    source = next(f.value for f in entry.research.field_updates if f.field == "source_drawing_roles")
    corners = {"upper_left": (-1,1), "upper_right": (1,1), "lower_left": (-1,-1), "lower_right": (1,-1)}
    rotated = {(-y,x): source[corner] for corner,(x,y) in corners.items()}
    library_order = [(-1,1),(-1,-1),(1,-1),(1,1)]
    assert [rotated[c] for c in library_order] == ["PLUS","MINUS","AC","AC"]
    recipe = recipes.entries["OHM-071"]
    assert recipe.terminal_roles == {"1":"PLUS","2":"MINUS","3":"AC1","4":"AC2"}
    nodes = [Net(name=name, kind="ground" if name == "return" else "signal",
                 connections=[PinRef(component="B1",pin=pin)])
             for pin,name in {"1":"plus","2":"minus","3":"supply","4":"return"}.items()]
    nodes[2].external_source = ExternalSource(kind="bench_supply",voltage=ValueRange.exact(Quantity.volts(10)))
    nodes[2].kind = NetKind.POWER
    circuit = CircuitIR(ir_id="bridge",name="pin permutation regression",
                        components=[CircuitComponent(ref="B1",part_id="OHM-071",package=recipe.package)],nets=nodes)
    bad = recipe.model_copy(update={"terminal_roles":{"1":"PLUS","2":"AC1","3":"MINUS","4":"AC2"}})
    changed = recipes.model_copy(update={"entries":dict(recipes.entries,**{"OHM-071":bad})})
    result = compile_circuit(circuit,registry,changed,{"B1":BehaviorSelection(entry_id="OHM-071")})
    assert not result.runnable
    assert any("manufacturer map" in reason for reason in result.problems)


def test_network_and_bridge_probe_contracts_refuse_changed_source_decks(tmp_path):
    from types import SimpleNamespace

    from tools.behavior_audit.runtime_benches import _locked_probe_deck

    (tmp_path / "original.cir").write_text("V1 in 0 500\n")
    contracts = {"example": {"file": "original.cir", "netlist_sha256": "0"*64}}
    # The probe reads re-pin-aware contracts; the fake exposes both views identically.
    audit = SimpleNamespace(root=tmp_path, _state=lambda: {"bench_contracts": contracts},
                            _bench_contracts=lambda **_: contracts)
    with pytest.raises(ValueError,match="source deck changed"):
        _locked_probe_deck(audit,"example")


@pytest.mark.parametrize("entry_id", ["OHM-044", "OHM-065", "OHM-067", "OHM-068", "OHM-069"])
def test_explicit_alternatives_and_clamp_bindings(entry_id):
    from tools.behavior_audit.audit import BehaviorAudit
    from tools.behavior_audit.runtime_benches import dc_probe_definition

    compiled, identity = dc_probe_definition(BehaviorAudit(ROOT), entry_id)
    assert compiled.runnable, compiled.problems
    component = compiled.components[0]
    assert component.reference_part
    if entry_id in {"OHM-068", "OHM-069"}:
        assert component.terminal_nodes["1"] == compiled.node_names["cathode"]
        assert component.terminal_nodes["2"] == "0"
        assert identity["comparison"]["analytical_source"].endswith("/B1")
    if entry_id == "OHM-044":
        assert "isat" not in component.parameters
        assert "not absolute maximum" in component.parameter_evidence["irms"]["scope"]
    if entry_id == "OHM-065":
        assert "S2M PN" in component.reference_part
        assert component.parameters["vr_max"] == 1000
        assert "SS24" in component.limitations[0]
    if entry_id == "OHM-067":
        assert component.parameter_evidence["IS"]["basis"] == "ASSUMPTION"
        assert component.parameters["vr_max"] == 30
        assert component.parameters["BV"] == 56
    if entry_id == "OHM-068":
        assert component.parameters["p_rated"] == .37
        assert component.parameters["rth_ja"] == 338


def test_tvs_source_bound_is_not_relaxed_to_legacy_numerical_tolerance():
    from tools.behavior_audit.audit import BehaviorAudit
    from tools.behavior_audit.runtime_benches import _dc_matches, dc_probe_definition

    _, legacy = dc_probe_definition(BehaviorAudit(ROOT), "OHM-069", "legacy")
    _, sourced = dc_probe_definition(BehaviorAudit(ROOT), "OHM-069", "source_bound")
    assert _dc_matches(legacy["comparison"], 24.40568)
    assert not _dc_matches(sourced["comparison"], 24.40568)
    assert sourced["comparison"]["maximum"] == 24.4
    assert legacy["comparison"]["expected"] == 24.4


def test_tvs_calibration_requires_raw_trials_and_unchanged_source(registry):
    import json

    from tools.behavior_audit.audit import BehaviorAudit
    from tools.behavior_audit.calibration import tvs_calibration_errors

    audit = BehaviorAudit(ROOT)
    assert not tvs_calibration_errors(audit)
    assert registry.behavior_class("BEH-DIO-TVS").canonical_payload["parameters"]["RDYN"]["default"] == .266
    record = json.loads((ROOT / "docs/behavior/calibration/OHM-069.json").read_text())
    record["trials"][-1]["observed_voltage"] = 24.40568
    errors = tvs_calibration_errors(audit, record)
    assert any("observation changed" in e for e in errors)
    assert any("unchanged source maximum" in e for e in errors)


def test_calibration_fails_closed_without_a_bracket_or_convergence():
    from scripts.calibrate_behavior_tvs import bracket_fit

    assert bracket_fit(lambda x:2*x, 0, 2, 2) == 1
    with pytest.raises(ValueError, match="not bracketed"):
        bracket_fit(lambda x:2*x, 0, 1, 3)
    with pytest.raises(ValueError, match="did not reach"):
        bracket_fit(lambda x:0 if x < .2 else 1, 0, 1, .5, max_trials=3)
