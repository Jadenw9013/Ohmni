"""A native export failure must stop the release, even with output files present."""

import subprocess
from types import SimpleNamespace

import pytest

from ohmni.eda.pcb_models import DrcStatus
from ohmni.manufacturing.exporter import FabricationExportError, KiCadFabricationExporter


@pytest.mark.parametrize("failure", ["crash", "timeout", "missing"])
def test_failed_native_export_never_creates_manifest(tmp_path, monkeypatch, failure):
    fingerprint = SimpleNamespace(digest="a" * 64)
    pcb = SimpleNamespace(
        fingerprint=fingerprint, circuit_content_hash="c" * 64, lineage_is_current=True,
        path=tmp_path / "board.kicad_pcb",
        compilation=SimpleNamespace(routing_verification=SimpleNamespace(passed=True)),
    )
    profile = SimpleNamespace(content_hash="b" * 64)
    drc = SimpleNamespace(status=DrcStatus.PASS, findings=[], unconnected_items=[], pcb_fingerprint=fingerprint)
    manufacturing = SimpleNamespace(passed=True, routed_pcb_fingerprint=fingerprint.digest, profile=profile)
    destination = tmp_path / "fabrication"
    destination.mkdir()
    (destination / "board.gtl").write_text("output written before a native crash")
    calls = []

    def native(command, *, timeout):
        calls.append(command)
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, timeout)
        if failure == "missing":
            raise OSError("tool unavailable")
        return subprocess.CompletedProcess(command, 0xC0000005, "", "native failure")

    monkeypatch.setattr("ohmni.manufacturing.exporter.run_tool", native)
    with pytest.raises(FabricationExportError) as caught:
        KiCadFabricationExporter(executable="stub-only").export(pcb, drc, manufacturing, profile, destination)
    if failure == "crash":
        assert "0xC0000005" in str(caught.value)
    assert len(calls) == 1
    assert not (destination / "ohmni-fabrication-manifest.json").exists()
