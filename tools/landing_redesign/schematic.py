"""Scoped KiCad power-intent annotation after the authored buck topology gate.

KiCad cannot propagate a power-output pin through a passive inductor. The marker
here declares the intended supply path at L1's output for ERC only. It neither
adds an external source nor establishes regulation, current capacity or startup.
The product compiler and catalog are untouched.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ohmni.domain import EventKind
from ohmni.eda.kicad.compiler import (
    COMPILER_VERSION,
    KiCadSchematicCompiler,
    _effects,
    _property,
    _uuid,
)
from ohmni.eda.kicad.component_asset_parser import parse
from ohmni.eda.kicad.sexpr import identifier, quote
from ohmni.eda.models import (
    ArtifactFingerprint,
    CompilationWarning,
    SchematicArtifact,
    SchematicDriverBinding,
)

from .checks import check_design
from .design import LandingDesign

ANNOTATION_VERSION = COMPILER_VERSION + "+landing-buck-intent.1"
LIBRARY_ID = "ohmni:DerivedBuckPowerIntent"
DRIVER_ROLE = "derived_buck_power_intent"
LIMITATION = (
    "Expected internal supply path U2.SW -> L1 -> 3V3 after exact topology checks; "
    "ERC annotation only, not external power, DC voltage, current capacity, "
    "dynamic regulation or hardware verification."
)


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _gate(design: LandingDesign, topology_report: dict[str, object]) -> str:
    """A supplied PASS is insufficient: reconstruct and compare the exact report."""
    if not isinstance(topology_report, dict):
        raise TypeError("A complete topology report is required before power annotation")
    extension = topology_report.get("include_i2c_extension")
    if type(extension) is not bool:
        raise ValueError("Topology report must identify an explicit design variant")
    current = check_design(design.circuit, design.catalog, include_i2c_extension=extension)
    if topology_report.get("circuit_content_hash") != design.circuit.content_hash:
        raise ValueError("Topology report belongs to a different or stale circuit")
    if _canonical(current) != _canonical(topology_report):
        raise ValueError("Topology report does not match freshly recomputed checks")
    if (current.get("failed_checks") != 0
            or current.get("status") != "SCOPED_CHECKS_PASS_SYSTEM_UNKNOWN"
            or current.get("system_status") != "UNKNOWN"
            or not current.get("topology_checks")
            or any(item.get("status") != "PASS" for item in current["topology_checks"])):
        raise ValueError("All scoped topology checks must pass; system status must remain UNKNOWN")
    output = design.circuit.net("3V3")
    if output is None or output.external_source is not None:
        raise ValueError("Derived 3V3 must not be declared as an external source")
    # These explicit assertions document the narrow annotation contract even
    # if a future topology checker changes its acceptance criteria.
    paths = {(ref, pin): design.circuit.net_of(ref, pin).name
             if design.circuit.net_of(ref, pin) else None
             for ref, pin in (("U2", "3"), ("L1", "1"), ("L1", "2"))}
    if paths != {("U2", "3"): "SW_NODE", ("L1", "1"): "SW_NODE", ("L1", "2"): "3V3"}:
        raise ValueError("Power annotation requires the exact U2-SW/L1/output path")
    return hashlib.sha256(_canonical(current).encode("utf-8")).hexdigest()


class _LandingSchematicCompiler(KiCadSchematicCompiler):
    """An authoring-local compiler; never imported by the product runtime."""

    def _driver_library_symbol(self) -> list[str]:
        return [*super()._driver_library_symbol(),
            f"    (symbol {quote(LIBRARY_ID)}", "      (pin_names (offset 0))",
            "      (exclude_from_sim yes)", "      (in_bom no)", "      (on_board no)",
            f"      {_property('Reference', '#PWR', 0, -2.54, hide=True)}",
            f"      {_property('Value', 'DerivedBuckPowerIntent', 0, 0, hide=True)}",
            f"      {_property('Footprint', '', 0, 0, hide=True)}",
            f"      {_property('Datasheet', '', 0, 0, hide=True)}",
            f"      {_property('Description', LIMITATION, 0, 0, hide=True)}",
            '      (symbol "DerivedBuckPowerIntent_0_1"',
            (f'        (pin power_out line (at 0 0 0) (length 0) '
             f'(name "expected_power" {_effects(hide=True)}) (number "1" {_effects(hide=True)}))'),
            "      )", "    )",
        ]

    def append_derived_intent(self, circuit, artifact, report_sha256):
        """Append a distinct marker and refresh every final-byte lineage field."""
        payload = artifact.path.read_text(encoding="utf-8")
        root = parse(payload)
        if root.head != "kicad_sch" or not payload.endswith(")\n"):
            raise ValueError("Unexpected base schematic structure")
        base_version = f"  (generator_version {quote(COMPILER_VERSION)})"
        if payload.count(base_version) != 1:
            raise ValueError("Unexpected base compiler version declaration")
        payload = payload.replace(base_version, f"  (generator_version {quote(ANNOTATION_VERSION)})", 1)
        library = root.child("lib_symbols")
        if sum(node.atoms() == [LIBRARY_ID] for node in library.children("symbol")) != 1:
            raise ValueError("Derived power-intent library symbol was not emitted exactly once")
        circuit_hash = circuit.content_hash
        ref = "#PWR_LP1"
        seed = "landing-derived-buck-output:3V3"
        symbol_uuid = _uuid(circuit_hash, f"driver:{seed}")
        pin_uuid = _uuid(circuit_hash, f"driver-pin:{seed}")
        endpoint_uuid = _uuid(circuit_hash, f"driver-label:{seed}")
        root_uuid = _uuid(circuit_hash, "root")
        project = identifier(circuit.ir_id)
        # Separate from the base compiler's source/return markers and component
        # cells, preventing accidental coordinate-based net joins in KiCad.
        x, y = 25.4, 55.88
        rendered = [
            "  (symbol", f"    (lib_id {quote(LIBRARY_ID)})",
            f"    (at {x} {y} 0)", "    (unit 1)",
            "    (exclude_from_sim yes)", "    (in_bom no)", "    (on_board no)", "    (dnp no)",
            f"    (uuid {quote(symbol_uuid)})",
            f"    {_property('Reference', ref, x, y, hide=True)}",
            f"    {_property('Value', '3V3 supply path: topology only', x, y - 2.54)}",
            f"    {_property('Footprint', '', x, y, hide=True)}",
            f"    {_property('Datasheet', '', x, y, hide=True)}",
            f"    {_property('Description', LIMITATION, x, y, hide=True)}",
            f"    {_property('OhmniCircuitHash', circuit_hash, x, y, hide=True)}",
            f"    {_property('OhmniTopologyReportSHA256', report_sha256, x, y, hide=True)}",
            f'    (pin "1" (uuid {quote(pin_uuid)}))',
            (f"    (instances (project {quote(project)} (path {quote('/' + root_uuid)} "
             f"(reference {quote(ref)}) (unit 1))))"), "  )",
            *self._global_label("3V3", x, y, 0, endpoint_uuid),
        ]
        payload = payload[:-2] + "\n".join(rendered) + "\n)\n"
        parse(payload)  # fail closed before publishing malformed derived bytes
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        fingerprint = ArtifactFingerprint(digest=digest)
        driver = SchematicDriverBinding(
            reference=ref, net_name="3V3", role=DRIVER_ROLE,
            symbol_uuid=symbol_uuid, pin_uuid=pin_uuid, endpoint_uuid=endpoint_uuid,
            x_mm=x, y_mm=y,
        )
        compilation = artifact.compilation.model_copy(deep=True)
        compilation.source_artifact_fingerprint = fingerprint
        compilation.compiler_version = ANNOTATION_VERSION
        compilation.driver_bindings.append(driver)
        compilation.warnings.append(CompilationWarning(
            code="DERIVED_BUCK_POWER_INTENT", component_ref="L1",
            message=f"{LIMITATION} Gate report SHA-256: {report_sha256}.",
        ))
        events = [event.model_copy(deep=True) for event in artifact.events]
        for event in events:
            if event.kind is EventKind.SCHEMATIC_COMPILED:
                event.summary = "Landing schematic compiled with scoped internal power intent"
                event.payload = {
                    "path": str(artifact.path), "sha256": digest,
                    "base_artifact_sha256": artifact.fingerprint.digest,
                    "topology_report_sha256": report_sha256,
                    "power_intent_role": DRIVER_ROLE, "system_status": "UNKNOWN",
                }
        artifact.path.write_text(payload, encoding="utf-8", newline="\n")
        final = artifact.model_copy(update={
            "fingerprint": fingerprint, "compiler_version": ANNOTATION_VERSION,
            "compilation": compilation, "events": events,
        })
        if not final.is_current or final.compilation.source_artifact_fingerprint != final.fingerprint:
            raise ValueError("Final schematic lineage does not match emitted bytes")
        return final


def build_schematic(
    design: LandingDesign, destination: Path, topology_report: dict[str, object],
) -> SchematicArtifact:
    """Compile only after reconstructing the exact successful topology gate."""
    report_sha256 = _gate(design, topology_report)
    compiler = _LandingSchematicCompiler(design.catalog)
    artifact = compiler.compile(design.circuit, destination)
    return compiler.append_derived_intent(design.circuit, artifact, report_sha256)
