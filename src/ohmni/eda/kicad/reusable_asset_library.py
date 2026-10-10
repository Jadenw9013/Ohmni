"""Reusable, immutable component assets and portable KiCad export.

The compiler consumes source-verified geometry records.  Family code contains
no MPN dimensions: adding another part in an implemented family is a data-row
operation.  Unsupported paste and thermal requirements fail before bytes are
emitted, and the resolver keys immutable bytes by both logical ID and digest.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from ...physical.land_patterns import (
    COURTYARD_MARGIN_NM,
    PIN1_MARKER_CLEARANCE_NM,
    PIN1_MARKER_RADIUS_NM,
    Circle,
    LandPad,
    LandPatternDefinition,
    LandPatternMethod,
    Rectangle,
    SymbolDefinition,
    SymbolPin,
)
from .component_asset_parser import AssetParseError, measure_footprint
from .component_assets import render_footprint, render_symbol_library

LIBRARY_POLICY_VERSION = "2.0.0"


class PackageFamily(StrEnum):
    DUAL_ROW = "dual_row"
    QFN = "qfn"
    QFP = "qfp"


class PastePolicy(StrEnum):
    PER_PAD = "per_pad"
    EXPOSED_PAD_SOLID = "exposed_pad_solid"


class ThermalPolicy(StrEnum):
    NONE = "none"
    EXPOSED_PAD_NO_VIAS = "exposed_pad_no_vias"


class AssetPolicyError(ValueError):
    """A record requests geometry or manufacturing policy this slice cannot prove."""


class SourcePad(BaseModel):
    """One pad exactly as established by the source/land-policy receipts."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    number: Annotated[str, StringConstraints(pattern=r"^[A-Z]?\d{1,4}$")]
    centre_x_nm: int
    centre_y_nm: int
    width_nm: int = Field(gt=0)
    height_nm: int = Field(gt=0)
    role: Literal["terminal", "exposed_pad"] = "terminal"


class ReusableAssetRecord(BaseModel):
    """All per-part values; the family compiler itself has no MPN table."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_id: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,120}$")]
    family: PackageFamily
    source_constraint_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    source_document_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    value: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    reference_prefix: Annotated[str, StringConstraints(pattern=r"^[A-Z]{1,4}$")] = "U"
    pads: tuple[SourcePad, ...] = Field(min_length=2, max_length=257)
    pin1_number: str = "1"
    paste_policy: PastePolicy = PastePolicy.PER_PAD
    thermal_policy: ThermalPolicy = ThermalPolicy.NONE
    limitations: tuple[str, ...] = Field(default=(), max_length=16)

    @model_validator(mode="after")
    def _coherent(self) -> ReusableAssetRecord:
        numbers = [pad.number for pad in self.pads]
        if len(numbers) != len(set(numbers)):
            raise ValueError("duplicate pad number")
        if self.pin1_number not in numbers:
            raise ValueError("pin-1 pad is absent")
        exposed = [pad for pad in self.pads if pad.role == "exposed_pad"]
        if len(exposed) > 1:
            raise ValueError("at most one exposed pad is supported")
        if self.family is PackageFamily.DUAL_ROW and exposed:
            raise ValueError("dual-row family does not carry an exposed pad")
        if self.family is PackageFamily.QFN and not exposed:
            raise ValueError("QFN record requires a source-defined exposed pad")
        if self.family is PackageFamily.QFP and len(self.pads) < 8:
            raise ValueError("QFP record needs at least two terminals per side")
        return self

    @property
    def content_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


class CompiledAsset(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_id: str
    record_hash: str
    source_constraint_hash: str
    source_document_hash: str
    family: PackageFamily
    paste_policy: PastePolicy
    thermal_policy: ThermalPolicy
    footprint_name: str
    symbol_name: str
    footprint_text: str
    symbol_text: str
    footprint_sha256: str
    symbol_sha256: str


def _validate_policy(record: ReusableAssetRecord) -> None:
    exposed = any(pad.role == "exposed_pad" for pad in record.pads)
    if exposed and record.paste_policy is not PastePolicy.EXPOSED_PAD_SOLID:
        raise AssetPolicyError(
            "exposed-pad paste requires an explicitly supported policy; windowed/custom paste "
            "is not implemented"
        )
    if not exposed and record.paste_policy is not PastePolicy.PER_PAD:
        raise AssetPolicyError("exposed-pad paste policy requested without an exposed pad")
    expected_thermal = (
        ThermalPolicy.EXPOSED_PAD_NO_VIAS if exposed else ThermalPolicy.NONE
    )
    if record.thermal_policy is not expected_thermal:
        raise AssetPolicyError(
            "thermal-via/custom thermal policy is unsupported; affected package is blocked"
        )


def _land_pattern(record: ReusableAssetRecord) -> LandPatternDefinition:
    _validate_policy(record)
    pads = tuple(
        LandPad(
            number=pad.number,
            centre_x_nm=pad.centre_x_nm,
            centre_y_nm=pad.centre_y_nm,
            width_nm=pad.width_nm,
            height_nm=pad.height_nm,
            shape="roundrect" if pad.role == "terminal" else "rect",
            roundrect_ratio=0.25 if pad.role == "terminal" else 0,
        )
        for pad in record.pads
    )
    x0 = min(pad.x0_nm for pad in pads) - COURTYARD_MARGIN_NM
    y0 = min(pad.y0_nm for pad in pads) - COURTYARD_MARGIN_NM
    x1 = max(pad.x1_nm for pad in pads) + COURTYARD_MARGIN_NM
    y1 = max(pad.y1_nm for pad in pads) + COURTYARD_MARGIN_NM
    pin1 = next(pad for pad in pads if pad.number == record.pin1_number)
    marker = Circle(
        centre_x_nm=pin1.x0_nm - PIN1_MARKER_CLEARANCE_NM - PIN1_MARKER_RADIUS_NM,
        centre_y_nm=pin1.centre_y_nm,
        radius_nm=PIN1_MARKER_RADIUS_NM,
    )
    courtyard = Rectangle(
        x0_nm=min(x0, marker.centre_x_nm - marker.radius_nm - COURTYARD_MARGIN_NM),
        y0_nm=y0,
        x1_nm=x1,
        y1_nm=y1,
    )
    return LandPatternDefinition(
        name=record.asset_id,
        method=LandPatternMethod.MANUFACTURER_RECOMMENDED_TABLE,
        policy_version=LIBRARY_POLICY_VERSION,
        constraint_hash=record.source_constraint_hash,
        description=f"Source-verified {record.family.value} asset {record.value}",
        pads=pads,
        courtyard=courtyard,
        pin1_marker=marker,
        limitations=(
            "Geometry is source/land-policy bound; IPC compliance is not established.",
            "Paste and thermal support is limited to the policy named by the manifest.",
            *record.limitations,
        ),
    )


def _symbol(record: ReusableAssetRecord) -> SymbolDefinition:
    terminal_numbers = [pad.number for pad in record.pads if pad.role == "terminal"]
    ordered = sorted(terminal_numbers, key=lambda value: int(value.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")))
    split = (len(ordered) + 1) // 2
    pins: list[SymbolPin] = []
    pitch = 2_540_000
    half_width = 7_620_000
    for side, numbers in enumerate((ordered[:split], list(reversed(ordered[split:])))):
        top = ((max(len(numbers), 1) - 1) // 2) * pitch
        for index, number in enumerate(numbers):
            pins.append(SymbolPin(
                number=number,
                name=f"P{number}",
                x_nm=-half_width if side == 0 else half_width,
                y_nm=top - index * pitch,
                orientation_deg=0 if side == 0 else 180,
                length_nm=pitch,
            ))
    body_half_height = max(2_540_000, ((max(split, len(ordered) - split) + 1) // 2) * pitch)
    return SymbolDefinition(
        name=record.asset_id,
        reference_prefix=record.reference_prefix,
        value=record.value,
        description=f"Source-verified {record.family.value} asset; electrical types pending CS-T07",
        datasheet_note=f"source document sha256:{record.source_document_hash}",
        body=Rectangle(
            x0_nm=-(half_width - pitch), y0_nm=-body_half_height,
            x1_nm=half_width - pitch, y1_nm=body_half_height,
        ),
        pins=tuple(sorted(pins, key=lambda pin: int(pin.number.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")))),
        policy_version=LIBRARY_POLICY_VERSION,
        constraint_hash=record.source_constraint_hash,
        limitations=("Electrical pin types remain unspecified until CS-T07.",),
    )


def compile_asset(record: ReusableAssetRecord) -> CompiledAsset:
    """Compile any implemented family solely from its immutable data record."""
    footprint = render_footprint(_land_pattern(record))
    symbol = render_symbol_library(_symbol(record))
    return CompiledAsset(
        asset_id=record.asset_id,
        record_hash=record.content_hash,
        source_constraint_hash=record.source_constraint_hash,
        source_document_hash=record.source_document_hash,
        family=record.family,
        paste_policy=record.paste_policy,
        thermal_policy=record.thermal_policy,
        footprint_name=record.asset_id,
        symbol_name=record.asset_id,
        footprint_text=footprint,
        symbol_text=symbol,
        footprint_sha256=hashlib.sha256(footprint.encode()).hexdigest(),
        symbol_sha256=hashlib.sha256(symbol.encode()).hexdigest(),
    )


def asset_mutation_errors(record: ReusableAssetRecord, footprint_text: str) -> tuple[str, ...]:
    """Independently compare emitted bytes to the record; any mutation is an error."""
    try:
        measured = measure_footprint(footprint_text)
    except AssetParseError as exc:
        return (f"unreadable footprint: {exc}",)
    expected = {pad.number: pad for pad in record.pads}
    actual = {pad.number: pad for pad in measured.pads}
    errors: list[str] = []
    if set(actual) != set(expected):
        errors.append("pad set differs from the source record")
    for number in sorted(set(actual) & set(expected)):
        left, right = actual[number], expected[number]
        observed = (left.centre_x_nm, left.centre_y_nm, left.width_nm, left.height_nm)
        wanted = (right.centre_x_nm, right.centre_y_nm, right.width_nm, right.height_nm)
        if observed != wanted:
            errors.append(f"pad {number} position or geometry differs")
    return tuple(errors)


@dataclass(frozen=True)
class ResolvedAsset:
    asset_id: str
    record_hash: str
    source_constraint_hash: str
    source_document_hash: str
    family: PackageFamily
    paste_policy: PastePolicy
    thermal_policy: ThermalPolicy
    footprint_bytes: bytes
    symbol_bytes: bytes
    footprint_sha256: str
    symbol_sha256: str


class ImmutableAssetResolver:
    """A collision-refusing, read-only resolver for exact compiled revisions."""

    def __init__(self, assets: tuple[CompiledAsset, ...]):
        entries: dict[str, ResolvedAsset] = {}
        for asset in assets:
            if asset.asset_id in entries:
                raise ValueError(f"ambiguous asset id {asset.asset_id!r}")
            footprint = asset.footprint_text.encode()
            symbol = asset.symbol_text.encode()
            if hashlib.sha256(footprint).hexdigest() != asset.footprint_sha256:
                raise ValueError("footprint digest does not match immutable bytes")
            if hashlib.sha256(symbol).hexdigest() != asset.symbol_sha256:
                raise ValueError("symbol digest does not match immutable bytes")
            entries[asset.asset_id] = ResolvedAsset(
                asset_id=asset.asset_id,
                record_hash=asset.record_hash,
                source_constraint_hash=asset.source_constraint_hash,
                source_document_hash=asset.source_document_hash,
                family=asset.family,
                paste_policy=asset.paste_policy,
                thermal_policy=asset.thermal_policy,
                footprint_bytes=footprint,
                symbol_bytes=symbol,
                footprint_sha256=asset.footprint_sha256,
                symbol_sha256=asset.symbol_sha256,
            )
        self._entries: Mapping[str, ResolvedAsset] = MappingProxyType(entries)

    def resolve(self, asset_id: str, *, record_hash: str) -> ResolvedAsset:
        asset = self._entries.get(asset_id)
        if asset is None or asset.record_hash != record_hash:
            raise KeyError(f"no immutable asset revision {asset_id}@{record_hash}")
        return asset


def export_portable_library(
    resolver: ImmutableAssetResolver,
    revisions: tuple[tuple[str, str], ...],
    destination: Path,
) -> Path:
    """Write a self-contained KiCad package beneath ``destination`` only."""
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    pretty = destination / "OhmniGenerated.pretty"
    symbols = destination / "symbols"
    pretty.mkdir(exist_ok=True)
    symbols.mkdir(exist_ok=True)
    manifest: list[dict[str, str]] = []
    for asset_id, record_hash in sorted(revisions):
        asset = resolver.resolve(asset_id, record_hash=record_hash)
        footprint_path = pretty / f"{asset_id}.kicad_mod"
        symbol_path = symbols / f"{asset_id}.kicad_sym"
        footprint_path.write_bytes(asset.footprint_bytes)
        symbol_path.write_bytes(asset.symbol_bytes)
        manifest.append({
            "asset_id": asset_id,
            "record_hash": record_hash,
            "source_constraint_hash": asset.source_constraint_hash,
            "source_document_hash": asset.source_document_hash,
            "family": asset.family.value,
            "paste_policy": asset.paste_policy.value,
            "thermal_policy": asset.thermal_policy.value,
            "footprint_sha256": asset.footprint_sha256,
            "symbol_sha256": asset.symbol_sha256,
        })
    (destination / "fp-lib-table").write_text(
        '(fp_lib_table\n  (lib (name "OhmniGenerated")(type "KiCad")'
        '(uri "${KIPRJMOD}/OhmniGenerated.pretty")(options "")(descr ""))\n)\n',
        encoding="utf-8", newline="\n",
    )
    symbol_rows = "".join(
        f'  (lib (name "{item["asset_id"]}")(type "KiCad")'
        f'(uri "${{KIPRJMOD}}/symbols/{item["asset_id"]}.kicad_sym")(options "")(descr ""))\n'
        for item in manifest
    )
    (destination / "sym-lib-table").write_text(
        f"(sym_lib_table\n{symbol_rows})\n", encoding="utf-8", newline="\n"
    )
    manifest_path = destination / "asset-manifest.json"
    manifest_path.write_text(
        json.dumps({"schema_version": 1, "assets": manifest}, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    for path in destination.rglob("*"):
        if path.resolve() != destination and destination not in path.resolve().parents:
            raise RuntimeError("portable export escaped its destination")
    return manifest_path


__all__ = [
    "LIBRARY_POLICY_VERSION",
    "AssetPolicyError",
    "CompiledAsset",
    "ImmutableAssetResolver",
    "PackageFamily",
    "PastePolicy",
    "ResolvedAsset",
    "ReusableAssetRecord",
    "SourcePad",
    "ThermalPolicy",
    "asset_mutation_errors",
    "compile_asset",
    "export_portable_library",
]
