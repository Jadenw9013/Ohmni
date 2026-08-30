"""Deterministic CircuitIR to self-contained KiCad 10 schematic compiler."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from ...adapters import PartCatalog
from ...domain import (
    CircuitIR,
    ComponentSpec,
    EngineeringEvent,
    EventKind,
    resolve_pin_behavior,
)
from ..models import (
    ArtifactFingerprint,
    CompilationReport,
    CompilationWarning,
    PinBinding,
    SchematicArtifact,
    SchematicDriverBinding,
    SymbolBinding,
)
from .sexpr import identifier, number, quote

COMPILER_VERSION = "0.1.0"
KICAD_FORMAT_VERSION = "20250114"
UUID_NAMESPACE = uuid.UUID("b4ed8e4a-7c27-52d3-aee4-f5eaec7ed84e")


class SchematicCompilationError(ValueError):
    def __init__(self, message: str, event: EngineeringEvent) -> None:
        super().__init__(message)
        self.event = event


def _uuid(circuit_hash: str, semantic_id: str) -> str:
    return str(uuid.uuid5(UUID_NAMESPACE, f"{circuit_hash}:{semantic_id}"))


def _effects(*, hide: bool = False) -> str:
    hidden = " (hide yes)" if hide else ""
    return f"(effects (font (size 1.27 1.27)){hidden})"


def _property(name: str, value: str, x: float, y: float, *, hide: bool = False) -> str:
    return f"(property {quote(name)} {quote(value)} (at {number(x)} {number(y)} 0) {_effects(hide=hide)})"


def _pin_position(index: int) -> tuple[float, float, int]:
    row = index // 2
    left = index % 2 == 0
    return (-7.62 if left else 7.62, row * 2.54, 0 if left else 180)


def _symbol_height(pin_count: int) -> float:
    return max(5.08, ((pin_count + 1) // 2) * 2.54)


class KiCadSchematicCompiler:
    """Compiles topology faithfully; it never adds missing circuit components."""

    def __init__(self, catalog: PartCatalog, *, layout_columns: int = 4) -> None:
        self.catalog = catalog
        self.layout_columns = layout_columns

    def compile(self, circuit: CircuitIR, destination: Path) -> SchematicArtifact:
        destination = destination.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        started = self._event(circuit, EventKind.SCHEMATIC_COMPILATION_STARTED, "Schematic compilation started")
        specs: dict[str, ComponentSpec] = {}
        warnings: list[CompilationWarning] = []
        for instance in sorted(circuit.components, key=lambda c: c.ref):
            spec = self.catalog.get(instance.part_id)
            if spec is None:
                raise self._failure(circuit, f"{instance.ref}: unresolved part {instance.part_id!r}")
            specs[instance.ref] = spec
            if not spec.pins:
                raise self._failure(circuit, f"{instance.ref}: catalog part has no pin definitions")
            for net in circuit.nets:
                for ref in net.connections:
                    if ref.component == instance.ref and spec.pin(ref.pin) is None:
                        raise self._failure(
                            circuit, f"{instance.ref}: CircuitIR connects unknown catalog pin {ref.pin!r}"
                        )
            if instance.package and spec.package(instance.package) is None:
                warnings.append(CompilationWarning(
                    code="PACKAGE_NOT_CATALOGED",
                    component_ref=instance.ref,
                    message=f"Package {instance.package!r} is not offered for {instance.part_id}; emitted unchanged.",
                ))

        root_uuid = _uuid(circuit.content_hash, "root")
        project = identifier(circuit.ir_id)
        lines = [
            "(kicad_sch", f"  (version {KICAD_FORMAT_VERSION})", '  (generator "ohmni")',
            f'  (generator_version "{COMPILER_VERSION}")', f'  (uuid "{root_uuid}")',
            '  (paper "A4")', "  (lib_symbols",
        ]
        for instance in sorted(circuit.components, key=lambda c: c.ref):
            spec = specs[instance.ref]
            lines.extend(self._library_symbol(
                spec, f"ohmni:{identifier(spec.part_id)}_{instance.ref}", instance,
            ))
        if any(net.external_source for net in circuit.nets):
            lines.extend(self._driver_library_symbol())
        lines.append("  )")

        bindings: list[SymbolBinding] = []
        connected = {(ref.component, ref.pin): net for net in circuit.nets for ref in net.connections}
        sorted_instances = sorted(circuit.components, key=lambda c: c.ref)
        for idx, instance in enumerate(sorted_instances):
            spec = specs[instance.ref]
            # Each symbol gets a generous fixed cell. Connectivity is label-based,
            # but labels at identical coordinates would also join physically in
            # KiCad, so cells must never overlap even for the 39-pin ESP32 module.
            x = 50.8 + (idx % self.layout_columns) * 50.8
            y = 76.2 + (idx // self.layout_columns) * 76.2
            rendered, binding = self._instance(
                circuit, instance, spec, x, y, root_uuid, project, connected,
            )
            lines.extend(rendered)
            bindings.append(binding)

        net_mapping = {net.name: net.name for net in sorted(circuit.nets, key=lambda n: n.name)}
        for binding in bindings:
            for pin in binding.pins:
                if pin.net_name is None:
                    lines.append(
                        f'  (no_connect (at {number(pin.x_mm)} {number(pin.y_mm)}) '
                        f'(uuid "{pin.endpoint_uuid}"))'
                    )
                else:
                    lines.extend(self._global_label(
                        pin.net_name, pin.x_mm, pin.y_mm,
                        pin.angle_degrees, pin.endpoint_uuid,
                    ))

        source_index = 0
        driver_bindings: list[SchematicDriverBinding] = []
        for net in sorted(circuit.nets, key=lambda n: n.name):
            if net.external_source is None:
                continue
            source_index += 1
            x, y = 25.4, 25.4 + source_index * 10.16
            rendered, driver = self._driver_instance(
                circuit, root_uuid, project, f"#SRC{source_index}", net.name, x, y,
                f"external-source:{net.name}", "external_source",
            )
            lines.extend(rendered)
            driver_bindings.append(driver)
        if source_index and circuit.ground_nets:
            ground = min(circuit.ground_nets, key=lambda n: n.name)
            rendered, driver = self._driver_instance(
                circuit, root_uuid, project, "#RET1", ground.name, 25.4, 25.4,
                f"external-return:{ground.name}", "external_return",
            )
            lines.extend(rendered)
            driver_bindings.append(driver)
            warnings.append(CompilationWarning(
                code="EXTERNAL_RETURN_INTENT",
                message=("A KiCad power-output marker represents the external source return on "
                         f"{ground.name}; it is EDA metadata, not an added CircuitIR component."),
            ))

        lines.extend([
            '  (sheet_instances (path "/" (page "1")))',
            "  (embedded_fonts no)", ")", "",
        ])
        payload = "\n".join(lines)
        destination.write_text(payload, encoding="utf-8", newline="\n")
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        report = CompilationReport(
            circuit_content_hash=circuit.content_hash,
            source_artifact_fingerprint=ArtifactFingerprint(digest=digest),
            compiler_version=COMPILER_VERSION,
            target="KiCad 10 schematic 20250114",
            symbol_bindings=bindings,
            driver_bindings=driver_bindings,
            net_mapping=net_mapping,
            warnings=warnings,
        )
        completed = self._event(
            circuit, EventKind.SCHEMATIC_COMPILED, "Schematic compiled",
            payload={"path": str(destination), "sha256": digest},
        )
        return SchematicArtifact(
            path=destination,
            fingerprint=ArtifactFingerprint(digest=digest),
            circuit_content_hash=circuit.content_hash,
            compiler_version=COMPILER_VERSION,
            target_eda="KiCad 10",
            compilation=report,
            events=[started, completed],
        )

    def _library_symbol(self, spec: ComponentSpec, lib_id: str, instance) -> list[str]:
        height = _symbol_height(len(spec.pins))
        ref_prefix = {"resistor": "R", "capacitor": "C", "led": "D", "connector": "J", "header": "J"}.get(spec.category.value, "U")
        out = [
            f"    (symbol {quote(lib_id)}", "      (pin_names (offset 0))",
            "      (exclude_from_sim no)", "      (in_bom yes)", "      (on_board yes)",
            f"      {_property('Reference', ref_prefix, 0, -height / 2 - 2.54)}",
            f"      {_property('Value', spec.display_name, 0, -height / 2)}",
            f"      {_property('Footprint', '', 0, 0, hide=True)}",
            f"      {_property('Datasheet', spec.datasheet.url if spec.datasheet and spec.datasheet.url else '', 0, 0, hide=True)}",
            f"      {_property('Description', spec.description, 0, 0, hide=True)}",
            f'      (symbol {quote(lib_id.split(":", 1)[1] + "_0_1")}',
            f"        (rectangle (start -5.08 -1.27) (end 5.08 {number(height)}) (stroke (width 0) (type default)) (fill (type background)))",
        ]
        for index, pin in enumerate(spec.pins):
            x, y, angle = _pin_position(index)
            electrical_type = resolve_pin_behavior(
                instance.ref, pin, instance.selected_interfaces
            ).electrical_type
            out.append(
                f"        (pin {electrical_type.value} line (at {number(x)} {number(y)} {angle}) "
                f"(length 2.54) (name {quote(pin.name)} {_effects()}) "
                f"(number {quote(pin.number)} {_effects()}))"
            )
        out.extend(["      )", "    )"])
        return out

    def _driver_library_symbol(self) -> list[str]:
        return [
            '    (symbol "ohmni:ExternalPowerDriver"', '      (pin_names (offset 0))',
            '      (exclude_from_sim yes)', '      (in_bom no)', '      (on_board no)',
            f"      {_property('Reference', '#SRC', 0, -2.54, hide=True)}",
            f"      {_property('Value', 'ExternalPowerDriver', 0, 0, hide=True)}",
            f"      {_property('Footprint', '', 0, 0, hide=True)}",
            f"      {_property('Datasheet', '', 0, 0, hide=True)}",
            f"      {_property('Description', 'Ohmni EDA power intent for a declared external source', 0, 0, hide=True)}",
            '      (symbol "ExternalPowerDriver_0_1"',
            f'        (pin power_out line (at 0 0 0) (length 0) (name "power" {_effects(hide=True)}) (number "1" {_effects(hide=True)}))',
            '      )', '    )',
        ]

    def _instance(self, circuit, instance, spec, x, y, root_uuid, project, connected):
        symbol_uuid = _uuid(circuit.content_hash, f"symbol:{instance.ref}")
        lib_id = f"ohmni:{identifier(spec.part_id)}_{instance.ref}"
        package = spec.package(instance.package) if instance.package else None
        # The real, provenance-bound footprint identity lives in the PCB
        # compilation report. A colon-qualified library link here makes KiCad
        # consult machine-global tables even though Ohmni emits project-local
        # footprint geometry, so use the deterministic local artifact identity.
        source_footprint = package.kicad_footprint if package and package.kicad_footprint else ""
        value = instance.value.engineering() if instance.value else spec.display_name
        out = [
            "  (symbol", f"    (lib_id {quote(lib_id)})", f"    (at {number(x)} {number(y)} 0)",
            "    (unit 1)", "    (exclude_from_sim no)", "    (in_bom yes)", "    (on_board yes)",
            "    (dnp no)", f'    (uuid "{symbol_uuid}")',
            f"    {_property('Reference', instance.ref, x, y - 5.08)}",
            f"    {_property('Value', value, x, y - 2.54)}",
            f"    {_property('Footprint', '', x, y, hide=True)}",
            f"    {_property('OhmniFootprintSource', source_footprint, x, y, hide=True)}",
            f"    {_property('Datasheet', '', x, y, hide=True)}",
            f"    {_property('Description', spec.description, x, y, hide=True)}",
        ]
        pin_bindings = []
        for index, pin in enumerate(spec.pins):
            pin_uuid = _uuid(circuit.content_hash, f"pin:{instance.ref}:{pin.number}")
            out.append(f'    (pin {quote(pin.number)} (uuid "{pin_uuid}"))')
            pin_x, pin_y, angle = _pin_position(index)
            net = connected.get((instance.ref, pin.number))
            pin_bindings.append(PinBinding(
                component_ref=instance.ref, circuit_pin=pin.number,
                kicad_pin=pin.number, pin_uuid=pin_uuid,
                pin_name=pin.name, x_mm=x + pin_x, y_mm=y - pin_y,
                angle_degrees=angle,
                endpoint_uuid=_uuid(circuit.content_hash, f"endpoint:{instance.ref}:{pin.number}"),
                net_name=net.name if net is not None else None,
            ))
        out.extend([
            f"    (instances (project {quote(project)} (path {quote('/' + root_uuid)} (reference {quote(instance.ref)}) (unit 1))))",
            "  )",
        ])
        return out, SymbolBinding(
            component_ref=instance.ref, part_id=spec.part_id, library_id=lib_id,
            symbol_uuid=symbol_uuid, x_mm=x, y_mm=y, width_mm=10.16,
            height_mm=_symbol_height(len(spec.pins)) + 1.27, pins=pin_bindings,
        )

    def _global_label(self, name: str, x: float, y: float, angle: int, item_uuid: str) -> list[str]:
        return [
            f"  (global_label {quote(name)} (shape bidirectional) (at {number(x)} {number(y)} {angle}) {_effects()} (uuid {quote(item_uuid)})",
            f"    {_property('Intersheetrefs', '${INTERSHEET_REFS}', x, y, hide=True)}",
            "  )",
        ]

    def _driver_instance(self, circuit, root_uuid, project, ref, net_name, x, y, seed, role):
        symbol_uuid = _uuid(circuit.content_hash, f"driver:{seed}")
        pin_uuid = _uuid(circuit.content_hash, f"driver-pin:{seed}")
        label_uuid = _uuid(circuit.content_hash, f"driver-label:{seed}")
        rendered = [
            "  (symbol", '    (lib_id "ohmni:ExternalPowerDriver")',
            f"    (at {number(x)} {number(y)} 0)", "    (unit 1)",
            "    (exclude_from_sim yes)", "    (in_bom no)", "    (on_board no)", "    (dnp no)",
            f'    (uuid "{symbol_uuid}")',
            f"    {_property('Reference', ref, x, y, hide=True)}",
            f"    {_property('Value', net_name, x, y, hide=True)}",
            f"    {_property('Footprint', '', x, y, hide=True)}",
            f"    {_property('Datasheet', '', x, y, hide=True)}",
            f"    {_property('Description', 'Declared CircuitIR external power intent', x, y, hide=True)}",
            f'    (pin "1" (uuid "{pin_uuid}"))',
            f"    (instances (project {quote(project)} (path {quote('/' + root_uuid)} (reference {quote(ref)}) (unit 1))))",
            "  )",
            *self._global_label(net_name, x, y, 0, label_uuid),
        ]
        return rendered, SchematicDriverBinding(
            reference=ref, net_name=net_name, role=role,
            symbol_uuid=symbol_uuid, pin_uuid=pin_uuid,
            endpoint_uuid=label_uuid, x_mm=x, y_mm=y,
        )

    @staticmethod
    def _event(circuit: CircuitIR, kind: EventKind, summary: str, payload=None) -> EngineeringEvent:
        event_id = _uuid(circuit.content_hash, f"event:{kind.value}")
        return EngineeringEvent(
            event_id=event_id, kind=kind, summary=summary,
            circuit_content_hash=circuit.content_hash, payload=payload or {},
        )

    def _failure(self, circuit: CircuitIR, message: str) -> SchematicCompilationError:
        return SchematicCompilationError(
            message,
            self._event(circuit, EventKind.SCHEMATIC_COMPILATION_FAILED,
                        "Schematic compilation failed", {"error": message}),
        )
