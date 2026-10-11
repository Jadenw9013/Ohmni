"""SPICE models cross a hash, dialect, pin-map, and assertion boundary."""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from ohmni.catalog.loader import default_catalog
from ohmni.domain.circuit import CircuitComponent, CircuitIR, Net, PinRef
from ohmni.domain.spice_models import (
    AssertionKind,
    MeasuredAssertion,
    ModelFidelity,
    ModelFile,
    ModelPinBinding,
    ModelProvenance,
    SimulationAnalysis,
    SimulationEligibility,
    SimulationEligibilityState,
    SimulationPlan,
    SpiceDialect,
    SpiceModelBinding,
    SpiceModelManifest,
)
from ohmni.eda.model_harness import (
    BoundModelDeck,
    HarnessStatus,
    ModelBoundaryError,
    bind_model_to_design,
    evaluate_harness,
    resolve_model_files,
)
from ohmni.eda.simulation import NgspiceAdapter, parse_operating_point

NGSPICE_EXE = os.environ.get("OHMNI_NGSPICE") or shutil.which("ngspice")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fixture(fidelity=ModelFidelity.VENDOR, dialect=SpiceDialect.NGSPICE_42):
    core = b".subckt RMODEL P N\nRcore P N 1k\n.ends RMODEL\n"
    main = b'.include "models/core.lib"\n'
    blobs = {digest(main): main, digest(core): core}
    manifest = SpiceModelManifest(
        model_id="vendor-r-1k",
        entrypoint="models/main.lib",
        model_name="RMODEL",
        dialect=dialect,
        fidelity=fidelity,
        files=(
            ModelFile(path="models/main.lib", sha256=digest(main)),
            ModelFile(path="models/core.lib", sha256=digest(core)),
        ),
        provenance=ModelProvenance(
            provider="Example Semiconductor",
            source_url="https://example.invalid/rmodel.zip",
            acquired_sha256=digest(main + core),
            license="Redistribution terms recorded by owner",
        ),
        supported_analyses=(SimulationAnalysis.OP,),
    )
    binding = SpiceModelBinding(
        component_revision_id="1" * 32,
        part_id="GENERIC_RESISTOR",
        manifest_sha256=manifest.manifest_sha256,
        pins=(
            ModelPinBinding(symbol_pin="1", model_port="P", model_position=1),
            ModelPinBinding(symbol_pin="2", model_port="N", model_position=2),
        ),
    )
    eligibility = SimulationEligibility(
        component_revision_id=binding.component_revision_id,
        state=SimulationEligibilityState.ELIGIBLE,
        binding=binding,
        manifest_sha256=manifest.manifest_sha256,
    )
    plan = SimulationPlan(
        analysis=SimulationAnalysis.OP,
        assertions=(
            MeasuredAssertion(
                assertion_id="r-current",
                kind=AssertionKind.CURRENT,
                signal="i(R1)",
                minimum=0.0049,
                maximum=0.0051,
                unit="A",
            ),
        ),
    )
    circuit = CircuitIR(
        ir_id="model-bound",
        name="model-bound resistor",
        components=[CircuitComponent(ref="R1", part_id="GENERIC_RESISTOR", package="0603")],
        nets=[
            Net(name="vin", connections=[PinRef(component="R1", pin="1")]),
            Net(name="gnd", connections=[PinRef(component="R1", pin="2")]),
        ],
    )
    return manifest, binding, eligibility, plan, circuit, blobs


def bind(values=None):
    manifest, binding, eligibility, plan, circuit, blobs = values or fixture()
    deck = bind_model_to_design(
        circuit,
        "R1",
        default_catalog(),
        manifest,
        binding,
        eligibility,
        plan,
        blobs.__getitem__,
    )
    return deck, manifest, binding, eligibility, plan, circuit, blobs


@pytest.mark.parametrize("fidelity", [ModelFidelity.VENDOR, ModelFidelity.APPROXIMATION])
def test_vendor_and_approximation_models_bind_to_actual_design_nets(fidelity):
    deck, manifest, *_ = bind(fixture(fidelity=fidelity))
    assert "XR1 vin gnd RMODEL" in deck.text
    assert "begin manifest:models/core.lib" in deck.text
    assert deck.manifest_sha256 == manifest.manifest_sha256


def test_every_transitive_file_must_be_listed_reachable_and_hash_locked():
    manifest, *_rest, blobs = fixture()
    text = resolve_model_files(manifest, blobs.__getitem__)
    assert text.index("models/main.lib") < text.index("models/core.lib")

    altered = dict(blobs)
    altered[next(iter(altered))] = b"changed"
    with pytest.raises(ModelBoundaryError, match="hash mismatch"):
        resolve_model_files(manifest, altered.__getitem__)

    stray = ModelFile(path="models/stray.lib", sha256=digest(b"unused"))
    bad = manifest.model_copy(update={"files": (*manifest.files, stray)})
    blobs[stray.sha256] = b"unused"
    with pytest.raises(ModelBoundaryError, match="unreachable"):
        resolve_model_files(bad, blobs.__getitem__)


@pytest.mark.parametrize(
    "body, message",
    [
        (b'.include "models/not-listed.lib"\n', "not manifest-listed"),
        (b".control\nrun\n.endc\n", "restricted"),
    ],
)
def test_unlisted_includes_and_active_directives_are_rejected(body, message):
    values = fixture()
    manifest, blobs = values[0], values[-1]
    entry = manifest.files[0]
    replacement = ModelFile(path=entry.path, sha256=digest(body))
    changed = manifest.model_copy(update={"files": (replacement, *manifest.files[1:])})
    changed_blobs = dict(blobs)
    changed_blobs[replacement.sha256] = body
    with pytest.raises(ModelBoundaryError, match=message):
        resolve_model_files(changed, changed_blobs.__getitem__)


def test_manifest_paths_cannot_escape_the_model_boundary():
    with pytest.raises(ValidationError, match="manifest-relative"):
        ModelFile(path="../outside.lib", sha256="0" * 64)


def test_pin_map_is_complete_ordered_and_matches_declared_model_ports():
    values = fixture()
    manifest, binding, eligibility, plan, circuit, blobs = values
    reversed_binding = binding.model_copy(
        update={
            "pins": (
                ModelPinBinding(symbol_pin="1", model_port="N", model_position=1),
                ModelPinBinding(symbol_pin="2", model_port="P", model_position=2),
            )
        }
    )
    reversed_eligibility = eligibility.model_copy(update={"binding": reversed_binding})
    with pytest.raises(ModelBoundaryError, match="port declaration"):
        bind_model_to_design(
            circuit,
            "R1",
            default_catalog(),
            manifest,
            reversed_binding,
            reversed_eligibility,
            plan,
            blobs.__getitem__,
        )


def test_cad_admission_never_implies_simulation_eligibility():
    manifest, binding, _eligibility, plan, circuit, blobs = fixture()
    cad_only = SimulationEligibility(
        component_revision_id=binding.component_revision_id,
        state=SimulationEligibilityState.CAD_ONLY,
        reasons=("No approved model",),
    )
    with pytest.raises(ModelBoundaryError, match="CAD-only"):
        bind_model_to_design(
            circuit,
            "R1",
            default_catalog(),
            manifest,
            binding,
            cad_only,
            plan,
            blobs.__getitem__,
        )


def test_assertions_are_locked_before_run_and_evaluated_independently():
    deck, manifest, _binding, _eligibility, plan, *_ = bind()
    seen = []

    def passing(text):
        seen.append(text)
        return {"status": "ran", "measurements": {"r-current": 0.005}}

    result = evaluate_harness(deck, manifest, plan, passing)
    assert result.status is HarnessStatus.PASSED
    assert seen == [deck.text]
    failed = evaluate_harness(
        deck,
        manifest,
        plan,
        lambda _text: {"status": "ran", "measurements": {"r-current": 0.02}},
    )
    assert failed.status is HarnessStatus.ASSERTION_FAILED
    changed = plan.model_copy(
        update={"assertions": (plan.assertions[0].model_copy(update={"maximum": 1.0}),)}
    )
    with pytest.raises(ModelBoundaryError, match="changed"):
        evaluate_harness(deck, manifest, changed, passing)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ({"status": "ran", "stdout": ""}, HarnessStatus.EMPTY_RESULTS),
        ({"status": "failed", "stderr": "timestep too small"}, HarnessStatus.NONCONVERGENT),
        ({"status": "failed", "stderr": "process error"}, HarnessStatus.TOOL_FAILED),
    ],
)
def test_empty_nonconvergent_and_tool_failure_results_are_explicit(raw, expected):
    deck, manifest, _binding, _eligibility, plan, *_ = bind()
    assert evaluate_harness(deck, manifest, plan, lambda _text: raw).status is expected


def test_unsupported_dialect_is_an_explicit_result_without_invoking_tool():
    deck, manifest, _binding, _eligibility, plan, *_ = bind()
    unsupported = manifest.model_copy(update={"dialect": SpiceDialect.PSPICE})
    called = False

    def runner(_text):
        nonlocal called
        called = True
        return {"status": "ran"}

    result = evaluate_harness(
        BoundModelDeck(**deck.model_dump() | {"manifest_sha256": unsupported.manifest_sha256}),
        unsupported,
        plan,
        runner,
    )
    assert result.status is HarnessStatus.UNSUPPORTED_DIALECT
    assert not called


@pytest.mark.simulation_integration
@pytest.mark.skipif(NGSPICE_EXE is None, reason="ngspice 42 is not installed")
def test_predeclared_assertion_is_checked_against_a_real_ngspice_42_run(tmp_path: Path):
    deck, manifest, _binding, _eligibility, _plan, *_ = bind()
    live_text = """Ohmni model harness integration
V1 vin 0 5
R1 vin 0 1k
.op
.print op i(V1)
.end
"""
    plan = SimulationPlan(
        analysis=SimulationAnalysis.OP,
        assertions=(
            MeasuredAssertion(
                assertion_id="supply-current",
                kind=AssertionKind.CURRENT,
                signal="i(V1)",
                minimum=-0.0051,
                maximum=-0.0049,
                unit="A",
            ),
        ),
    )
    live = BoundModelDeck(
        **deck.model_dump()
        | {
            "text": live_text,
            "deck_sha256": digest(live_text.encode()),
            "plan_sha256": plan.plan_sha256,
        }
    )
    adapter = NgspiceAdapter(executable=NGSPICE_EXE)

    def run(text):
        raw = adapter.behavior_bench(text, work_dir=tmp_path)
        point = parse_operating_point(raw["stdout"])
        if current := point.branch_currents.get("v1"):
            raw["measurements"] = {"supply-current": current.value}
        return raw

    result = evaluate_harness(live, manifest, plan, run)
    assert result.status is HarnessStatus.PASSED
