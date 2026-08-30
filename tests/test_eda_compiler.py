
import pytest

from ohmni.domain import CircuitComponent
from ohmni.eda.kicad import KiCadCliAdapter, KiCadSchematicCompiler, SchematicCompilationError
from ohmni.eda.models import ErcStatus


def test_compilation_is_byte_deterministic(tmp_path, golden, catalog):
    compiler = KiCadSchematicCompiler(catalog)
    first = compiler.compile(golden, tmp_path / "a.kicad_sch")
    second = compiler.compile(golden, tmp_path / "b.kicad_sch")
    assert first.path.read_bytes() == second.path.read_bytes()
    assert first.fingerprint == second.fingerprint
    assert first.compilation.symbol_bindings == second.compilation.symbol_bindings


def test_bindings_are_sorted_and_cover_every_catalog_pin(tmp_path, golden, catalog):
    artifact = KiCadSchematicCompiler(catalog).compile(golden, tmp_path / "x.kicad_sch")
    assert [b.component_ref for b in artifact.compilation.symbol_bindings] == sorted(c.ref for c in golden.components)
    for binding in artifact.compilation.symbol_bindings:
        assert len(binding.pins) == len(catalog.get(binding.part_id).pins)
        assert len({p.pin_uuid for p in binding.pins}) == len(binding.pins)
        assert binding.x_mm > 0 and binding.y_mm > 0
        assert all(pin.endpoint_uuid and pin.x_mm > 0 and pin.y_mm > 0 for pin in binding.pins)
    expected_connections = {
        (net.name, ref.component, ref.pin) for net in golden.nets for ref in net.connections
    }
    projected_connections = {
        (pin.net_name, pin.component_ref, pin.circuit_pin)
        for binding in artifact.compilation.symbol_bindings
        for pin in binding.pins if pin.net_name
    }
    assert projected_connections == expected_connections
    assert artifact.compilation.source_artifact_fingerprint == artifact.fingerprint
    assert artifact.compilation.connection_method == "global_labels"
    text=artifact.path.read_text(encoding="utf-8")
    for binding in artifact.compilation.symbol_bindings:
        assert binding.symbol_uuid in text
        for pin in binding.pins:
            assert pin.endpoint_uuid in text
    assert {driver.reference for driver in artifact.compilation.driver_bindings}=={"#SRC1","#RET1"}
    for driver in artifact.compilation.driver_bindings:
        assert driver.symbol_uuid in text and driver.endpoint_uuid in text


def test_multi_rail_sensor_pins_remain_distinct(tmp_path, golden, catalog):
    artifact = KiCadSchematicCompiler(catalog).compile(golden, tmp_path / "x.kicad_sch")
    sensor = next(b for b in artifact.compilation.symbol_bindings if b.component_ref == "U3")
    spec = catalog.get(sensor.part_id)
    supply_names = {p.name for p in spec.pins if p.number in {b.circuit_pin for b in sensor.pins}}
    assert {"VDD", "VDDIO"} <= supply_names


def test_layout_changes_graphics_not_connectivity(tmp_path, golden, catalog):
    a = KiCadSchematicCompiler(catalog, layout_columns=3).compile(golden, tmp_path / "a.kicad_sch")
    b = KiCadSchematicCompiler(catalog, layout_columns=5).compile(golden, tmp_path / "b.kicad_sch")
    assert a.compilation.net_mapping == b.compilation.net_mapping
    topology = lambda artifact: {
        (pin.net_name, pin.component_ref, pin.circuit_pin)
        for binding in artifact.compilation.symbol_bindings for pin in binding.pins
    }
    assert topology(a) == topology(b)
    assert a.compilation.symbol_bindings != b.compilation.symbol_bindings
    assert a.path.read_bytes() != b.path.read_bytes()


def test_unknown_connected_pin_fails_with_event(tmp_path, golden, catalog):
    broken = golden.model_copy(deep=True)
    broken.nets[0].connections[0] = broken.nets[0].connections[0].model_copy(update={"pin": "NO_SUCH_PIN"})
    with pytest.raises(SchematicCompilationError) as caught:
        KiCadSchematicCompiler(catalog).compile(broken, tmp_path / "x.kicad_sch")
    assert caught.value.event.kind.value == "schematic_compilation_failed"


def test_unresolved_part_is_not_guessed(tmp_path, golden, catalog):
    broken = golden.model_copy(deep=True)
    broken.components.append(CircuitComponent(ref="U99", part_id="UNKNOWN"))
    with pytest.raises(SchematicCompilationError, match="unresolved part"):
        KiCadSchematicCompiler(catalog).compile(broken, tmp_path / "x.kicad_sch")


def test_artifact_fingerprint_detects_stale_file(tmp_path, golden, catalog):
    artifact = KiCadSchematicCompiler(catalog).compile(golden, tmp_path / "x.kicad_sch")
    artifact.path.write_text(artifact.path.read_text() + "\n; changed", encoding="utf-8")
    report = KiCadCliAdapter(executable="never-run").run_erc(artifact)
    assert report.status is ErcStatus.STALE_ARTIFACT
    assert report.artifact_fingerprint == artifact.fingerprint
    assert report.events[0].kind.value == "artifact_invalidated"


def test_output_identifies_ohmni_and_embeds_symbols(tmp_path, golden, catalog):
    artifact = KiCadSchematicCompiler(catalog).compile(golden, tmp_path / "x.kicad_sch")
    text = artifact.path.read_text(encoding="utf-8")
    assert '(generator "ohmni")' in text
    assert "(lib_symbols" in text
    assert '(generator "eeschema")' not in text
    assert ".kicad_pcb" not in text
