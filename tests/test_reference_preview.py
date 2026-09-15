"""Saved previews bind reconstructed geometry to complete, checked source files.

Native checks and fabrication file generation are explicitly stubbed here. The
circuit, placement, deterministic routing, PCB emission and independent checks
are real; a separate real run exercises the guarded KiCad integration.
"""

import hashlib
import json
import shutil
from datetime import date

import pytest

from ohmni.application import reference_preview as preview
from ohmni.application.demo import current_pcb_policy
from ohmni.application.projects import _prepare_project
from ohmni.catalog import default_catalog
from ohmni.eda.kicad import KiCadPcbCompiler, KiCadSchematicCompiler
from ohmni.eda.models import ErcReport
from ohmni.eda.pcb_models import DrcReport
from ohmni.manufacturing import prototype_profile
from ohmni.physical.placement import generate_placement
from ohmni.routing.router import DeterministicRouter
from ohmni.routing.verifier import verify_routing
from ohmni.synthesis import SynthesisBrief

CAPTURED_ON = date(2026, 9, 14)


def _dump(directory, name, value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    (directory / name).write_text(json.dumps(value), encoding="utf-8")


def _erc(artifact):
    return ErcReport(status="pass", tool_status="ok", run_id="explicit-test-stub",
                     kicad_version="test-stub", artifact_fingerprint=artifact.fingerprint)


def _drc(artifact):
    return DrcReport(status="pass", tool_status="ok", run_id="explicit-test-stub",
                     kicad_version="test-stub", pcb_fingerprint=artifact.fingerprint,
                     source_schematic_fingerprint=artifact.schematic_fingerprint)


@pytest.fixture(scope="module")
def generated_source(tmp_path_factory):
    root = tmp_path_factory.mktemp("reference-source")
    brief = SynthesisBrief(project_name="A generated learning board", status_led_count=0,
                           include_programming_header=False)
    result, _ = _prepare_project(brief)
    catalog = default_catalog()
    placement = generate_placement(result.circuit, result.placement_request, catalog)
    schematic = KiCadSchematicCompiler(catalog).compile(result.circuit, root / "golden.kicad_sch")
    compiler = KiCadPcbCompiler(catalog)
    placed = compiler.compile(result.circuit, schematic, placement.board,
                              root / "golden.placed.kicad_pcb")
    plan = DeterministicRouter().route(result.circuit, placed, placement.board,
                                       time_budget_seconds=60)
    routing = verify_routing(result.circuit, placed, placement.board, plan)
    assert not plan.failures and routing.passed
    routed = compiler.compile(result.circuit, schematic, placement.board, root / "golden.kicad_pcb", plan)
    profile = prototype_profile()
    fabrication = root / "fabrication"
    fabrication.mkdir()
    files = []
    for index, kind in enumerate(("F.Cu", "B.Cu", "F.Mask", "B.Mask", "F.Silkscreen", "B.Silkscreen", "Edge.Cuts", "Drill")):
        name = f"explicit-test-stub-{index}.txt"
        data = f"Test fixture only: {kind}".encode()
        (fabrication / name).write_bytes(data)
        files.append({"relative_path": name, "sha256": hashlib.sha256(data).hexdigest(),
                      "size_bytes": len(data), "kind": kind})
    manifest = {
        "circuit_fingerprint": result.circuit.content_hash,
        "schematic_fingerprint": schematic.fingerprint.digest,
        "pcb_fingerprint": routed.fingerprint.digest,
        "routing_plan_fingerprint": plan.content_hash,
        "manufacturing_profile_fingerprint": profile.content_hash,
        "release_status": "ready_for_manufacturing_review", "files": files,
    }
    package_hash = hashlib.sha256(preview._json_bytes(manifest)).hexdigest()
    manifest["package_fingerprint"] = package_hash
    manifest_bytes = preview._json_bytes(manifest)
    manifest_name = "ohmni-fabrication-manifest.json"
    (fabrication / manifest_name).write_bytes(manifest_bytes)
    report = {
        "mode": "bounded_synthesis",
        "project": {"status": "READY_FOR_MANUFACTURING_REVIEW", "brief_fingerprint": brief.fingerprint,
                    "circuit_hash": result.circuit.content_hash,
                    "placement_request_fingerprint": result.placement_request.content_hash},
        "schematic": {"fingerprint": schematic.fingerprint.digest},
        "pcb": {**current_pcb_policy(), "fingerprint": routed.fingerprint.digest,
                "source_schematic_fingerprint": schematic.fingerprint.digest,
                "source_placed_pcb_fingerprint": placed.fingerprint.digest,
                "placement": {"algorithm": placement.algorithm,
                              "request_fingerprint": placement.request_fingerprint,
                              "constraints_hash": placement.board.content_hash}},
        "release": {"current": True, "status": "READY_FOR_MANUFACTURING_REVIEW",
                    "pcb_fingerprint": routed.fingerprint.digest, "package_fingerprint": package_hash,
                    "files": files, "manifest": {"relative_path": manifest_name,
                    "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                    "size_bytes": len(manifest_bytes), "kind": "Manifest"}},
        "experience": {"components": [{"ref": "INVENTED", "purpose": "Trust me"}]},
    }
    for name, value in {
        "confirmed-brief.json": brief, "circuit.json": result.circuit,
        "placement-request.json": result.placement_request, "placement.json": placement,
        "routing-plan.json": plan, "routing-verification.json": routing,
        "erc-report.json": _erc(schematic), "drc-report.json": _drc(routed),
        "report.json": report,
    }.items():
        _dump(root, name, value)
    return root


@pytest.fixture
def source(generated_source, tmp_path):
    root = tmp_path / "saved-run"
    shutil.copytree(generated_source, root)
    return root


@pytest.fixture
def native(monkeypatch):
    calls = []

    class ExplicitStub:
        def __init__(self, *, timeout_seconds):
            assert timeout_seconds == 60

        def run_erc(self, artifact):
            assert artifact.is_current
            calls.append("erc")
            return _erc(artifact)

        def run_drc(self, artifact):
            assert artifact.lineage_is_current
            calls.append("drc")
            return _drc(artifact)

    monkeypatch.setattr(preview, "KiCadCliAdapter", ExplicitStub)
    return calls


def test_preview_is_reproducible_and_reprojects_every_part_from_actual_source(source, native):
    before = {path.relative_to(source).as_posix(): path.read_bytes() for path in source.rglob("*") if path.is_file()}
    first = preview.build_reference_preview(source, captured_on=CAPTURED_ON)
    second = preview.build_reference_preview(source, captured_on=CAPTURED_ON)
    assert first == second
    assert native == ["erc", "drc", "erc", "drc"]
    assert first["schema_version"] == 1
    assert first["source"]["kind"] == "previously_generated_reference_preview"
    assert first["source"]["artifact_fingerprint"] == first["board"]["artifact_fingerprint"]
    assert first["source"]["routing_plan_fingerprint"] == first["board"]["routing_plan_fingerprint"]
    confirmed = SynthesisBrief.model_validate_json((source / "confirmed-brief.json").read_bytes())
    assert first["confirmed_brief"] == confirmed.model_dump(mode="json")
    assert first["brief"]["project_name"] == confirmed.project_name
    circuit = json.loads((source / "circuit.json").read_bytes())
    refs = {part["ref"] for part in circuit["components"]}
    assert {part["ref"] for part in first["components"]} == refs
    assert {part["ref"] for part in first["board"]["components"]} == refs
    assert "INVENTED" not in str(first)
    assert all(part["purpose"] for part in first["components"])
    assert first["flows"] and first["board"]["tracks"]
    assert first["checks"]["semantic"]["coverage"] == 1
    assert first["checks"]["routing"]["passed"]
    assert first["checks"]["simulation"] == "NOT_RUN"
    assert first["checks"]["bench"] == "NOT_VERIFIED"
    for name, data in before.items():
        assert (source / name).read_bytes() == data
        assert first["source"]["files"][name] == hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize("name", ["golden.kicad_sch", "golden.placed.kicad_pcb", "golden.kicad_pcb",
                                 "fabrication/explicit-test-stub-0.txt"])
def test_tampered_artifact_is_rejected_before_native_checks(source, native, name):
    with (source / name).open("ab") as stream:
        stream.write(b"tampered")
    with pytest.raises(preview.ReferencePreviewError):
        preview.build_reference_preview(source, captured_on=CAPTURED_ON)
    assert native == []


@pytest.mark.parametrize("name,field,value", [
    ("confirmed-brief.json", "status_led_count", 1),
    ("circuit.json", "components", []),
    ("routing-plan.json", "source_constraints_hash", "0" * 64),
    ("erc-report.json", "status", "unavailable"),
    ("drc-report.json", "status", "fail"),
])
def test_changed_inputs_and_failed_recorded_checks_are_rejected(source, native, name, field, value):
    data = json.loads((source / name).read_bytes())
    data[field] = value
    _dump(source, name, data)
    with pytest.raises(preview.ReferencePreviewError):
        preview.build_reference_preview(source, captured_on=CAPTURED_ON)
    assert native == []


def test_failed_or_incomplete_run_cannot_become_a_reference(source, native):
    (source / "failure.json").write_text('{"error":"routing_incomplete"}')
    with pytest.raises(preview.ReferencePreviewError, match="Failed runs"):
        preview.build_reference_preview(source, captured_on=CAPTURED_ON)
    (source / "failure.json").unlink()
    (source / "report.json").unlink()
    with pytest.raises(preview.ReferencePreviewError):
        preview.build_reference_preview(source, captured_on=CAPTURED_ON)
    assert native == []


@pytest.mark.parametrize("failure", ["erc", "drc"])
def test_saved_pass_never_overrides_failed_native_recheck(source, native, monkeypatch, failure):
    original = preview.KiCadCliAdapter

    class FailingNative(original):
        def run_erc(self, artifact):
            result = super().run_erc(artifact)
            return result.model_copy(update={"status": preview.ErcStatus.UNAVAILABLE}) if failure == "erc" else result

        def run_drc(self, artifact):
            result = super().run_drc(artifact)
            return result.model_copy(update={"status": preview.DrcStatus.UNAVAILABLE}) if failure == "drc" else result

    monkeypatch.setattr(preview, "KiCadCliAdapter", FailingNative)
    with pytest.raises(preview.ReferencePreviewError, match="completed"):
        preview.build_reference_preview(source, captured_on=CAPTURED_ON)
    assert native == (["erc"] if failure == "erc" else ["erc", "drc"])


def test_export_writes_only_verified_preview_and_rejects_source_destination(source, native, tmp_path):
    destination = tmp_path / "reference.json"
    result = preview.export_reference_preview(source, destination, captured_on=CAPTURED_ON)
    assert json.loads(destination.read_bytes()) == result
    with pytest.raises(preview.ReferencePreviewError, match="outside"):
        preview.export_reference_preview(source, source / "report.json", captured_on=CAPTURED_ON)
    previous = destination.read_bytes()
    (source / "failure.json").write_text("{}")
    with pytest.raises(preview.ReferencePreviewError):
        preview.export_reference_preview(source, destination, captured_on=CAPTURED_ON)
    assert destination.read_bytes() == previous


def test_source_mutation_during_native_recheck_prevents_publication(source, native, monkeypatch):
    original = preview.KiCadCliAdapter

    class MutatingNative(original):
        def run_drc(self, artifact):
            report = super().run_drc(artifact)
            with (source / "golden.kicad_pcb").open("ab") as stream:
                stream.write(b"changed during export")
            return report

    monkeypatch.setattr(preview, "KiCadCliAdapter", MutatingNative)
    with pytest.raises(preview.ReferencePreviewError, match="changed during"):
        preview.build_reference_preview(source, captured_on=CAPTURED_ON)


def test_cli_accepts_explicit_capture_date_and_writes_preview(source, native, tmp_path, capsys):
    output = tmp_path / "reference.json"
    assert preview.main(["--run-dir", str(source), "--output", str(output),
                         "--captured-on", CAPTURED_ON.isoformat()]) == 0
    assert output.exists() and "Saved" in capsys.readouterr().out
