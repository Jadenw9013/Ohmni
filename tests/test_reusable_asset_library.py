"""CS-T05 reusable asset records, policy gates, resolver, and portable export."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ohmni.adapters import ToolStatus
from ohmni.eda.kicad.component_asset_parser import measure_footprint
from ohmni.eda.kicad.component_harness import export_footprint_svg
from ohmni.eda.kicad.reusable_asset_library import (
    AssetPolicyError,
    ImmutableAssetResolver,
    PackageFamily,
    PastePolicy,
    ReusableAssetRecord,
    SourcePad,
    ThermalPolicy,
    asset_mutation_errors,
    compile_asset,
    export_portable_library,
)

SOURCE = "1" * 64
CONSTRAINT = "2" * 64


def _dual(asset_id: str = "SOIC_8", *, pitch: int = 1_270_000) -> ReusableAssetRecord:
    pads = []
    for index in range(4):
        y = (2 * index - 3) * pitch // 2
        pads.append(SourcePad(number=str(index + 1), centre_x_nm=-3_000_000,
                              centre_y_nm=y, width_nm=600_000, height_nm=1_500_000))
        pads.append(SourcePad(number=str(8 - index), centre_x_nm=3_000_000,
                              centre_y_nm=y, width_nm=600_000, height_nm=1_500_000))
    return ReusableAssetRecord(
        asset_id=asset_id, family=PackageFamily.DUAL_ROW,
        source_constraint_hash=CONSTRAINT, source_document_hash=SOURCE,
        value=asset_id, pads=tuple(pads),
    )


def _quad(
    asset_id: str,
    family: PackageFamily,
    *,
    count: int,
    exposed: bool,
) -> ReusableAssetRecord:
    pads = []
    per_side = count // 4
    pitch = 500_000
    next_number = 1
    for side in range(4):
        for offset in range(per_side):
            axis = (2 * offset - (per_side - 1)) * pitch // 2
            if side == 0:
                x, y, w, h = axis, -3_000_000, 250_000, 700_000
            elif side == 1:
                x, y, w, h = 3_000_000, axis, 700_000, 250_000
            elif side == 2:
                x, y, w, h = -axis, 3_000_000, 250_000, 700_000
            else:
                x, y, w, h = -3_000_000, -axis, 700_000, 250_000
            pads.append(SourcePad(number=str(next_number), centre_x_nm=x, centre_y_nm=y,
                                  width_nm=w, height_nm=h))
            next_number += 1
    if exposed:
        pads.append(SourcePad(number=str(count + 1), centre_x_nm=0, centre_y_nm=0,
                              width_nm=3_000_000, height_nm=3_000_000,
                              role="exposed_pad"))
    return ReusableAssetRecord(
        asset_id=asset_id, family=family,
        source_constraint_hash=CONSTRAINT, source_document_hash=SOURCE,
        value=asset_id, pads=tuple(pads),
        paste_policy=PastePolicy.EXPOSED_PAD_SOLID if exposed else PastePolicy.PER_PAD,
        thermal_policy=(ThermalPolicy.EXPOSED_PAD_NO_VIAS if exposed else ThermalPolicy.NONE),
    )


def test_a_second_dual_row_part_is_only_another_data_record():
    first = compile_asset(_dual("SOIC_8"))
    second = compile_asset(_dual("TSSOP_8", pitch=650_000))
    assert first.asset_id != second.asset_id
    assert measure_footprint(second.footprint_text).pad("2").centre_y_nm == -325_000
    assert first.source_constraint_hash == second.source_constraint_hash


@pytest.mark.parametrize(
    "record",
    [
        _dual(),
        _quad("QFN_16_EP", PackageFamily.QFN, count=16, exposed=True),
        _quad("QFP_32", PackageFamily.QFP, count=32, exposed=False),
        _quad("QFP_32_EP", PackageFamily.QFP, count=32, exposed=True),
    ],
)
def test_supported_families_round_trip_every_pad(record):
    compiled = compile_asset(record)
    assert asset_mutation_errors(record, compiled.footprint_text) == ()
    measured = measure_footprint(compiled.footprint_text)
    assert len(measured.pads) == len(record.pads)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("(at -3 -1.905)", "(at -2.9 -1.905)"),
        ("(size 0.6 1.5)", "(size 0.7 1.5)"),
        ('(pad "1"', '(pad "99"'),
    ],
)
def test_pad_position_geometry_and_number_mutations_are_rejected(old, new):
    record = _dual()
    text = compile_asset(record).footprint_text
    mutated = text.replace(old, new, 1)
    assert mutated != text
    assert asset_mutation_errors(record, mutated)


def test_orientation_mutation_is_rejected_even_when_pitch_and_sizes_match():
    record = _dual()
    text = compile_asset(record).footprint_text
    mutated = text.replace("(at -3 -1.905)", "(at -3 1.905)", 1)
    assert any("position" in error for error in asset_mutation_errors(record, mutated))


def test_qfn_without_source_defined_exposed_pad_is_invalid():
    with pytest.raises(ValueError, match="requires"):
        _quad("QFN_BAD", PackageFamily.QFN, count=16, exposed=False)


def test_unsupported_paste_policy_blocks_the_affected_package():
    record = _quad("QFN_16_EP", PackageFamily.QFN, count=16, exposed=True)
    bad = record.model_copy(update={"paste_policy": PastePolicy.PER_PAD})
    with pytest.raises(AssetPolicyError, match="paste"):
        compile_asset(bad)


def test_unsupported_thermal_policy_blocks_the_affected_package():
    record = _quad("QFN_16_EP", PackageFamily.QFN, count=16, exposed=True)
    bad = record.model_copy(update={"thermal_policy": ThermalPolicy.NONE})
    with pytest.raises(AssetPolicyError, match="thermal"):
        compile_asset(bad)


def test_resolver_requires_the_exact_immutable_revision():
    compiled = compile_asset(_dual())
    resolver = ImmutableAssetResolver((compiled,))
    resolved = resolver.resolve(compiled.asset_id, record_hash=compiled.record_hash)
    assert hashlib.sha256(resolved.footprint_bytes).hexdigest() == compiled.footprint_sha256
    with pytest.raises(KeyError):
        resolver.resolve(compiled.asset_id, record_hash="f" * 64)


def test_resolver_refuses_ambiguous_ids_and_tampered_bytes():
    compiled = compile_asset(_dual())
    with pytest.raises(ValueError, match="ambiguous"):
        ImmutableAssetResolver((compiled, compiled))
    tampered = compiled.model_copy(update={"footprint_text": compiled.footprint_text + " "})
    with pytest.raises(ValueError, match="digest"):
        ImmutableAssetResolver((tampered,))


def test_portable_export_is_self_contained_and_does_not_touch_global_libraries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    assets = tuple(compile_asset(record) for record in (
        _dual(), _quad("QFN_16_EP", PackageFamily.QFN, count=16, exposed=True),
    ))
    resolver = ImmutableAssetResolver(assets)
    fake_home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("APPDATA", str(fake_home / "AppData"))
    destination = tmp_path / "project" / "generated-library"
    manifest_path = export_portable_library(
        resolver, tuple((asset.asset_id, asset.record_hash) for asset in assets), destination
    )
    manifest = json.loads(manifest_path.read_text())
    assert {item["asset_id"] for item in manifest["assets"]} == {a.asset_id for a in assets}
    assert (destination / "fp-lib-table").is_file()
    assert (destination / "sym-lib-table").is_file()
    assert not fake_home.exists()
    assert all(destination in path.parents for path in destination.rglob("*") if path.is_file())


@pytest.mark.kicad
def test_portable_footprint_is_loaded_by_real_kicad(tmp_path: Path):
    compiled = compile_asset(_quad("QFN_16_EP", PackageFamily.QFN, count=16, exposed=True))
    resolver = ImmutableAssetResolver((compiled,))
    destination = tmp_path / "portable"
    export_portable_library(
        resolver, ((compiled.asset_id, compiled.record_hash),), destination
    )
    run = export_footprint_svg(
        destination / "OhmniGenerated.pretty", compiled.footprint_name, tmp_path / "render"
    )
    if run.status is ToolStatus.UNAVAILABLE:
        pytest.skip(run.detail)
    assert run.status is ToolStatus.OK, run.detail
    assert run.artifact_sha256 == compiled.footprint_sha256
