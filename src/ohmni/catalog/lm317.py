"""Source-bound LM317/DCY data row and typed production inputs."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files

from ..domain.adjustable_regulator import AdjustableRegulatorLimits
from ..eda.kicad.reusable_asset_library import (
    PackageFamily,
    ReusableAssetRecord,
    SourcePad,
)


@lru_cache(maxsize=1)
def lm317_record() -> dict:
    path = files("ohmni.catalog").joinpath("data/synthesis/lm317-dcy.json")
    return json.loads(path.read_text(encoding="utf-8"))


def lm317_limits() -> AdjustableRegulatorLimits:
    values = lm317_record()["electrical"]
    return AdjustableRegulatorLimits(
        reference_voltage_v=values["reference_voltage_v"],
        adjust_current_a=values["adjust_current_typical_a"],
        output_min_v=values["output_min_v"],
        output_max_v=values["output_max_v"],
        differential_min_v=values["differential_min_v"],
        differential_max_v=values["differential_max_v"],
        load_min_a=values["load_min_a"],
        load_max_a=values["load_max_a"],
    )


def lm317_asset_record() -> ReusableAssetRecord:
    """Compile only the coordinates printed in TI's DCY board-layout drawing."""
    source_hash = lm317_record()["source"]["sha256"]
    return ReusableAssetRecord(
        asset_id="TI_LM317_DCY",
        family=PackageFamily.SOT223,
        source_constraint_hash=source_hash,
        source_document_hash=source_hash,
        value="LM317DCYR",
        reference_prefix="U",
        pads=(
            SourcePad(number="1", centre_x_nm=-2_900_000, centre_y_nm=2_300_000,
                      width_nm=2_150_000, height_nm=950_000),
            SourcePad(number="2", centre_x_nm=-2_900_000, centre_y_nm=0,
                      width_nm=2_150_000, height_nm=950_000),
            SourcePad(number="3", centre_x_nm=-2_900_000, centre_y_nm=-2_300_000,
                      width_nm=2_150_000, height_nm=950_000),
            SourcePad(number="4", centre_x_nm=2_900_000, centre_y_nm=0,
                      width_nm=2_150_000, height_nm=3_250_000),
        ),
        limitations=(
            "Pad dimensions and centres are from TI DCY0004A land-pattern example page 36.",
            "Thermal performance and stencil design require separate verification.",
        ),
    )


__all__ = ["lm317_asset_record", "lm317_limits", "lm317_record"]
