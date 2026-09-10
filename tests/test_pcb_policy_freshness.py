"""Local geometry/compiler upgrades retire every saved build without native EDA."""

from types import SimpleNamespace

import pytest
from test_project_api import _personal_package, _seed_package, _wait

from ohmni.application.demo import current_pcb_policy, pcb_artifact_policy
from ohmni.eda.kicad import pcb_compiler
from ohmni.physical import footprints
from scripts.demo_server import JobStore


@pytest.mark.parametrize("personal", [False, True])
@pytest.mark.parametrize("field", ["compiler_version", "footprint_geometry_fingerprint", "footprint_geometry_scope"])
@pytest.mark.parametrize("missing", [False, True])
def test_old_policy_retires_legacy_and_personal_builds_and_survives_restart(tmp_path, personal, field, missing):
    if personal:
        store, job_id, directory, _, _ = _personal_package(tmp_path)
    else:
        store, job_id, directory = _seed_package(tmp_path)
        store.enable_persistence()
    assert store.get(job_id)["status"] == "complete"
    pcb = store.jobs[job_id]["report"]["pcb"]
    if missing:
        del pcb[field]
    else:
        pcb[field] = "obsolete-policy"
    store.project_store.save_job(store.jobs[job_id])
    before = {path.name: path.read_bytes() for path in directory.glob("*.kicad_*")}
    restored = JobStore(tmp_path)
    restored.enable_persistence()
    result = restored.get(job_id)
    assert result["status"] == "failed" and result["error_code"] == "job_state_invalid"
    assert result["report"] is None
    assert restored.read_build_package(job_id)[1] is None
    for name in ("golden.kicad_sch", "golden.kicad_pcb"):
        assert restored.read_artifact(job_id, name)[1] is None
    assert {path.name: path.read_bytes() for path in directory.glob("*.kicad_*")} == before
    again = JobStore(tmp_path)
    again.enable_persistence()
    assert again.get(job_id) == result


@pytest.mark.parametrize("change", ["compiler", "geometry"])
def test_dynamic_policy_changes_retire_already_cached_completed_jobs(tmp_path, monkeypatch, change):
    store, job_id, _, _, _ = _personal_package(tmp_path)
    assert store.get(job_id)["status"] == "complete"
    if change == "compiler":
        monkeypatch.setattr(pcb_compiler, "PCB_COMPILER_VERSION", "next-policy")
    else:
        identifier, definition = next(iter(footprints.FOOTPRINTS.items()))
        updated = definition.model_copy(deep=True)
        updated.width_mm += .01
        monkeypatch.setitem(footprints.FOOTPRINTS, identifier, updated)
    assert store.get(job_id)["status"] == "failed"
    assert store.read_build_package(job_id)[1] is None


def test_changed_policy_can_retry_without_first_polling(tmp_path, monkeypatch):
    store, job_id, _, project_id, revision_id = _personal_package(tmp_path)
    del store.jobs[job_id]["report"]["pcb"]["footprint_geometry_fingerprint"]
    store.project_store.save_job(store.jobs[job_id])
    launched = []
    monkeypatch.setattr(store, "_launch", lambda *args: launched.append(args))
    next_job_id = store.start_revision(project_id, revision_id)
    assert next_job_id != job_id and len(launched) == 1
    assert store.get(job_id)["status"] == "failed"
    assert store.get(next_job_id)["status"] == "queued"


@pytest.mark.parametrize("field", ["compiler_version", "footprint_geometry_fingerprint"])
def test_legacy_worker_cannot_publish_old_policy(tmp_path, field):
    class Pipeline:
        def __init__(self, progress):
            pass

        def run(self, destination, request):
            prepared, job_id, _ = _seed_package(destination.parent, destination.name)
            report = prepared.jobs[job_id]["report"]
            report["pcb"][field] = "obsolete"
            return SimpleNamespace(model_dump=lambda **_kwargs: report)

    store = JobStore(tmp_path, Pipeline)
    job_id = store.start("legacy example")
    result = _wait(store, job_id)
    assert result["status"] == "failed" and result["error_code"] == "pipeline_failed"
    assert result["report"] is None


def test_artifact_projection_checks_original_binding_and_compiler(monkeypatch):
    identifier, definition = next(iter(footprints.FOOTPRINTS.items()))
    artifact = SimpleNamespace(compiler_version=pcb_compiler.PCB_COMPILER_VERSION,
        compilation=SimpleNamespace(footprint_bindings=[SimpleNamespace(
            footprint_id=identifier, geometry_fingerprint=definition.content_hash)]))
    original = pcb_artifact_policy(artifact)
    assert original == current_pcb_policy()
    updated = definition.model_copy(deep=True)
    updated.width_mm += .01
    monkeypatch.setitem(footprints.FOOTPRINTS, identifier, updated)
    with pytest.raises(ValueError, match="geometry changed"):
        pcb_artifact_policy(artifact)
    monkeypatch.setitem(footprints.FOOTPRINTS, identifier, definition)
    monkeypatch.setattr(pcb_compiler, "PCB_COMPILER_VERSION", "changed")
    with pytest.raises(ValueError, match="compiler policy changed"):
        pcb_artifact_policy(artifact)
