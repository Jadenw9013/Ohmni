"""CS-T08 import/resume, functional placement and snapshot-lineage gates."""

from pathlib import Path

import pytest

from ohmni.application.component_resolution import (
    ComponentResolutionService,
    ResolutionBypassError,
    ResolutionState,
)
from ohmni.application.project_store import ProjectStore
from ohmni.catalog import ActivePartCatalog, default_catalog
from ohmni.catalog.component_store import ActiveRevision
from ohmni.mcp_server.schemas import InputModel
from ohmni.mcp_server.service import SemanticService
from ohmni.physical.placement import generate_placement
from ohmni.synthesis import ArchetypeId, I2cSensorSlot, SynthesisBrief, synthesize
from ohmni.verifier import verify


class ActiveFixtureStore:
    def __init__(self, values=()):
        self.values = tuple(values)

    def active_specs(self):
        return self.values


def _revision(part_id: str) -> ActiveRevision:
    return ActiveRevision(
        revision_id="1" * 32, component_key=part_id, record_digest="2" * 64,
        publication_digest="3" * 64, state="ACTIVE", assets=(), reports=(),
    )


def _new_sensor():
    seed = default_catalog().require("BME280")
    return seed.model_copy(update={
        "part_id": "ADMITTED-TEMP-1", "display_name": "Admitted temperature sensor",
        "mpn": "ADMITTED-TEMP-1",
    }, deep=True)


def _brief():
    return SynthesisBrief(
        archetype=ArchetypeId.A2_USB_GPIO_CONTROLLER,
        project_name="Imported sensor controller", description="Exercise admitted I2C part.",
        sensors=(I2cSensorSlot(part_id="ADMITTED-TEMP-1"),),
        status_led_count=1, button_count=1,
    )


def test_resolution_pauses_persists_and_cannot_be_bypassed(tmp_path: Path):
    projects = ProjectStore(tmp_path / "projects")
    before = ActivePartCatalog(default_catalog(), ActiveFixtureStore())
    service = ComponentResolutionService(projects, before)
    request = service.request(_brief())

    assert request.state is ResolutionState.WAITING_IMPORT
    assert request.missing_part_ids == ("ADMITTED-TEMP-1",)
    with pytest.raises(ResolutionBypassError, match="import is incomplete"):
        service.resume(request.resolution_id)
    with pytest.raises(ResolutionBypassError, match="does not exist"):
        service.resume("0" * 32)

    after = ActivePartCatalog(
        default_catalog(), ActiveFixtureStore(((_revision("ADMITTED-TEMP-1"), _new_sensor()),))
    )
    resumed = ComponentResolutionService(ProjectStore(tmp_path / "projects"), after)
    brief, resolution = resumed.resume(request.resolution_id)
    assert brief == _brief()
    assert resolution.state is ResolutionState.RESOLVED
    assert resolution.active_component_revisions == {"ADMITTED-TEMP-1": "1" * 32}
    assert resolution.catalog_snapshot_sha256 == after.snapshot_hash


def test_admitted_part_uses_functional_placement_and_real_semantic_lineage(tmp_path: Path):
    catalog = ActivePartCatalog(
        default_catalog(), ActiveFixtureStore(((_revision("ADMITTED-TEMP-1"), _new_sensor()),))
    )
    result = synthesize(_brief(), catalog)
    assert result.accepted and result.circuit is not None and result.placement_request is not None
    assert any(part.part_id == "ADMITTED-TEMP-1" for part in result.circuit.components)
    # Placement intent is an electrical function group; no authored x/y by refdes exists.
    sensor_group = next(group for group in result.placement_request.groups if group.kind.value == "sensor")
    assert sensor_group.anchor_ref == "U3" and set(sensor_group.member_refs) == {"U3", "C6", "C7"}
    semantic = verify(result.circuit, catalog, result.requirements)
    assert not semantic.export_blocked and semantic.coverage == 1
    placed = generate_placement(result.circuit, result.placement_request, catalog)
    assert placed.request_fingerprint == result.placement_request.content_hash
    assert placed.board.content_hash

    mcp = SemanticService(catalog)
    assert mcp.get_capabilities(InputModel()).catalog_hash == catalog.snapshot_hash
    assert mcp.get_part(type("Request", (), {"part_id": "ADMITTED-TEMP-1"})()).part.part_id == "ADMITTED-TEMP-1"


def test_active_catalog_rejects_shadowing_seed_identity():
    seed = default_catalog().require("BME280")
    with pytest.raises(ValueError, match="shadows catalog part"):
        ActivePartCatalog(default_catalog(), ActiveFixtureStore(((_revision(seed.part_id), seed),)))


@pytest.mark.integration
def test_admitted_part_traverses_real_project_release_with_exact_lineage(tmp_path: Path):
    catalog = ActivePartCatalog(
        default_catalog(), ActiveFixtureStore(((_revision("ADMITTED-TEMP-1"), _new_sensor()),))
    )
    projects = ProjectStore(tmp_path / "workspace")
    service = ComponentResolutionService(projects, catalog)
    resolution = service.request(_brief())
    assert resolution.state is ResolutionState.READY

    destination = tmp_path / "release"
    report = service.run(resolution.resolution_id, destination)
    assert report.project["component_resolution_id"] == resolution.resolution_id
    assert report.project["component_resolution_state"] == "RESOLVED"
    assert report.project["catalog_snapshot_sha256"] == catalog.snapshot_hash
    assert report.project["active_component_revisions"] == {"ADMITTED-TEMP-1": "1" * 32}
    assert report.release["status"] == "READY_FOR_MANUFACTURING_REVIEW"
    assert report.release["package_fingerprint"]
    assert report.release["pcb_fingerprint"]
    assert report.release["files"]
    assert report.release["current"] is True
    assert (destination / "golden.kicad_sch").is_file()
    assert (destination / "golden.kicad_pcb").is_file()
    assert (destination / "drc-report.json").is_file()
    assert (destination / "fabrication").is_dir()
