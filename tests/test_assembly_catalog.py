"""Catalog hand-solderability and package difficulty must not contradict each other."""

from types import SimpleNamespace

import pytest

from ohmni.bom import classify_assembly, generate_bom
from ohmni.bom.models import AssemblyDifficulty, Bom, BomLine, ManufacturerPartIdentity
from ohmni.catalog import default_catalog
from ohmni.domain import PackageOption
from ohmni.synthesis import (
    ArchetypeId,
    I2cSensorSlot,
    SpiPeripheralSlot,
    SynthesisBrief,
    synthesize,
)
from ohmni.verifier import verify


def _one_part_bom(part_id):
    part=default_catalog().require(part_id)
    package=part.packages[0]
    line=BomLine(identity=ManufacturerPartIdentity(part_id=part.part_id,manufacturer=part.manufacturer,
        mpn=part.mpn,package=package.name),description=part.description,quantity_per_board=1,
        references=["U1"],footprint=package.kicad_footprint,evidence_status="CATALOG_REPORTED")
    return Bom(circuit_fingerprint="a"*64,lines=[line])


@pytest.mark.parametrize("part_id,difficulty,satisfied", [
    ("25LC256-I/SN",AssemblyDifficulty.MODERATE,True),
    ("TMP102AIDRLR",AssemblyDifficulty.DIFFICULT,False),
    ("BME280",AssemblyDifficulty.REFLOW_RECOMMENDED,False),
])
def test_catalog_package_guidance_controls_family_assembly(part_id,difficulty,satisfied):
    report=classify_assembly(_one_part_bom(part_id),catalog=default_catalog())
    assert report.risks[0].difficulty is difficulty
    assert report.hand_solder_requirement_satisfied is satisfied
    assert "exact catalog package" in report.risks[0].detail
    if part_id=="TMP102AIDRLR":
        assert report.risks[0].exposed_or_underside_pads is False
        assert "Fine-pitch" in report.risks[0].detail
    assert any("not machine-verified" in limitation for limitation in report.limitations)


@pytest.mark.parametrize("sensor", [None,"BME280","TMP102AIDRLR"])
def test_memory_project_semantic_and_assembly_preferences_agree(sensor):
    brief=SynthesisBrief(archetype=ArchetypeId.A3_USB_SPI_PERIPHERAL,
        sensors=(I2cSensorSlot(part_id=sensor),) if sensor else (),
        spi_devices=(SpiPeripheralSlot(part_id="25LC256-I/SN"),)*2)
    result=synthesize(brief)
    catalog=default_catalog()
    semantic=verify(result.circuit,catalog,result.requirements)
    assembly=classify_assembly(generate_bom(result.circuit,catalog),catalog=catalog)
    unsuitable=[finding for finding in semantic.findings if finding.rule_id=="PB-ID-005"]
    assert assembly.hand_solder_requirement_satisfied is (not unsuitable)
    assert not any(risk.difficulty is AssemblyDifficulty.UNKNOWN for risk in assembly.risks)


@pytest.mark.parametrize("field,value", [("part_id","missing"),("manufacturer","another manufacturer"),
                                        ("mpn","another order code"),("package","SOIC-16")])
def test_mismatched_identity_is_unknown_not_catalog_suitability(field,value):
    bom=_one_part_bom("25LC256-I/SN")
    bom.lines[0].identity=bom.lines[0].identity.model_copy(update={field:value})
    report=classify_assembly(bom,catalog=default_catalog())
    assert report.risks[0].difficulty is AssemblyDifficulty.UNKNOWN
    assert not report.hand_solder_requirement_satisfied
    assert "not hand-solderable" not in report.risks[0].detail


def test_mismatched_footprint_and_absent_catalog_flag_remain_unknown():
    bom=_one_part_bom("25LC256-I/SN")
    bom.lines[0].footprint="Unrelated:Footprint"
    assert classify_assembly(bom,catalog=default_catalog()).risks[0].difficulty is AssemblyDifficulty.UNKNOWN
    bom=_one_part_bom("25LC256-I/SN")
    part=default_catalog().require("25LC256-I/SN")
    values=part.packages[0].model_dump(exclude={"hand_solderable"})
    absent=part.model_copy(update={"packages":[PackageOption(**values)]})
    report=classify_assembly(bom,catalog=SimpleNamespace(get=lambda _:absent))
    assert report.risks[0].difficulty is AssemblyDifficulty.UNKNOWN
    assert "no explicitly recorded" in report.risks[0].detail
    assert not report.hand_solder_requirement_satisfied


def test_legacy_call_remains_available_without_catalog_assumptions():
    bom=_one_part_bom("25LC256-I/SN")
    legacy=classify_assembly(bom)
    assert legacy.risks[0].difficulty is AssemblyDifficulty.UNKNOWN
    assert not legacy.hand_solder_requirement_satisfied
    assert classify_assembly(bom,catalog=default_catalog()).hand_solder_requirement_satisfied
