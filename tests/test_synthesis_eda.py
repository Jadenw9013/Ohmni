"""Real KiCad corroboration for the smallest and largest A2/A3 compositions."""

from collections import Counter

import pytest

from ohmni.adapters.tools import find_kicad_cli
from ohmni.catalog import default_catalog
from ohmni.eda.kicad import KiCadCliAdapter, KiCadSchematicCompiler
from ohmni.eda.models import ErcStatus
from ohmni.synthesis import (
    ArchetypeId,
    I2cSensorSlot,
    SpiPeripheralSlot,
    SynthesisBrief,
    synthesize,
)
from ohmni.verifier import verify

pytestmark = [
    pytest.mark.integration,
    pytest.mark.kicad,
    pytest.mark.skipif(find_kicad_cli() is None, reason="KiCad CLI unavailable"),
]


@pytest.mark.parametrize("family,brief", [
    pytest.param("A2 minimum", SynthesisBrief(
        archetype=ArchetypeId.A2_USB_GPIO_CONTROLLER, sensors=(), status_led_count=1,
        button_count=1, include_programming_header=False,
    ), id="a2-minimum"),
    pytest.param("A2 maximum", SynthesisBrief(
        archetype=ArchetypeId.A2_USB_GPIO_CONTROLLER, sensors=(), status_led_count=4,
        button_count=2, include_programming_header=True,
    ), id="a2-maximum"),
    pytest.param("A3 minimum", SynthesisBrief(
        archetype=ArchetypeId.A3_USB_SPI_PERIPHERAL, sensors=(), status_led_count=0,
        spi_devices=(SpiPeripheralSlot(part_id="25LC256-I/SN"),),
        include_programming_header=False,
    ), id="a3-minimum"),
    pytest.param("A3 maximum", SynthesisBrief(
        archetype=ArchetypeId.A3_USB_SPI_PERIPHERAL,
        sensors=(I2cSensorSlot(part_id="BME280"),), status_led_count=1,
        spi_devices=(SpiPeripheralSlot(part_id="25LC256-I/SN"),) * 2,
        include_programming_header=True,
    ), id="a3-maximum"),
])
def test_family_boundary_schematics_have_no_real_kicad_errors(tmp_path, family, brief):
    catalog = default_catalog()
    result = synthesize(brief)
    assert result.accepted, result.refusal
    semantic = verify(result.circuit, catalog, result.requirements)
    assert semantic.coverage == 1 and not semantic.export_blocked

    artifact = KiCadSchematicCompiler(catalog).compile(result.circuit, tmp_path / "controller.kicad_sch")
    erc = KiCadCliAdapter().run_erc(artifact)
    assert erc.kicad_version and erc.kicad_version.startswith("10."), erc.model_dump_json()
    assert erc.status in (ErcStatus.PASS, ErcStatus.PASS_WITH_WARNINGS), erc.model_dump_json()
    assert erc.artifact_fingerprint == artifact.fingerprint
    assert erc.report_path is not None and erc.report_path.is_file()

    # Retain warnings in the actual result; never turn "no errors" into a clean pass.
    errors = [finding for finding in erc.findings if finding.severity == "error"]
    warnings = [finding for finding in erc.findings if finding.severity == "warning"]
    assert not errors, [finding.model_dump() for finding in errors]
    if any(not finding.excluded for finding in warnings):
        assert erc.status is ErcStatus.PASS_WITH_WARNINGS
    classifications = dict(Counter(finding.classification.value for finding in warnings))
    print(f"{family}: KiCad {erc.kicad_version}; {len(result.circuit.components)} components; "
          f"{len(errors)} errors; {len(warnings)} warnings retained {classifications}; "
          f"report={erc.report_path}")
