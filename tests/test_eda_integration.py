import pytest

from ohmni.adapters.tools import find_kicad_cli
from ohmni.eda.kicad import KiCadCliAdapter, KiCadSchematicCompiler
from ohmni.eda.models import ErcStatus
from ohmni.fixtures.esp32_env_logger import broken_sensor_on_5v, requirements
from ohmni.verifier import verify

pytestmark = [pytest.mark.kicad, pytest.mark.skipif(find_kicad_cli() is None, reason="KiCad CLI unavailable")]


def test_golden_is_parsed_and_checked_by_real_kicad(tmp_path, golden, catalog):
    artifact = KiCadSchematicCompiler(catalog).compile(golden, tmp_path / "golden.kicad_sch")
    report = KiCadCliAdapter().run_erc(artifact)
    assert report.kicad_version.startswith("10.")
    assert report.status is ErcStatus.PASS_WITH_WARNINGS
    assert not [f for f in report.findings if not f.excluded and f.severity == "error"]
    assert report.artifact_fingerprint == artifact.fingerprint
    assert report.report_path.is_file()
    classes = [f.classification.value for f in report.findings]
    assert classes.count("library_configuration") == 21
    assert not [f for f in report.findings if f.classification.value == "electrical"]


def test_real_kicad_catches_missing_power_driver(tmp_path, golden, catalog):
    broken = golden.model_copy(deep=True)
    for net in broken.nets:
        net.external_source = None
    artifact = KiCadSchematicCompiler(catalog).compile(broken, tmp_path / "broken.kicad_sch")
    report = KiCadCliAdapter().run_erc(artifact)
    assert any(f.type == "power_pin_not_driven" for f in report.findings)


def test_ohmni_catches_datasheet_voltage_error_that_kicad_does_not(tmp_path, catalog):
    circuit = broken_sensor_on_5v()
    semantic = verify(circuit, catalog, requirements())
    artifact = KiCadSchematicCompiler(catalog).compile(circuit, tmp_path / "overvoltage.kicad_sch")
    erc = KiCadCliAdapter().run_erc(artifact)
    assert any(f.rule_id == "PB-PWR-001" and f.severity.value == "critical" for f in semantic.findings)
    assert not any(f.severity == "error" for f in erc.findings if not f.excluded)
