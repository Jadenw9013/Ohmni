"""Native regressions for ordinary-project configurations found during the audit."""
import pytest

from ohmni.application.projects import ProjectPipeline
from ohmni.synthesis import ArchetypeId, SpiPeripheralSlot, SynthesisBrief


@pytest.mark.integration
@pytest.mark.parametrize("brief", [
    SynthesisBrief(hand_solderable_preferred=False),
    SynthesisBrief(archetype=ArchetypeId.A2_USB_GPIO_CONTROLLER, sensors=(),
                   button_count=1, status_led_count=1, board_width_mm=50, board_height_mm=50,
                   hand_solderable_preferred=False),
    SynthesisBrief(archetype=ArchetypeId.A3_USB_SPI_PERIPHERAL,
                   spi_devices=(SpiPeripheralSlot(part_id="25LC256-I/SN"),),
                   hand_solderable_preferred=False),
    SynthesisBrief(board_width_mm=50, board_height_mm=50, hand_solderable_preferred=False),
], ids=["room-monitor", "compact-controller", "temperature-memory", "compact-room-monitor"])
def test_ordinary_configurations_reach_native_release(tmp_path, brief):
    report = ProjectPipeline().run(tmp_path, brief)
    assert report.project["status"] == "READY_FOR_MANUFACTURING_REVIEW"
    assert report.pcb["drc_status"] == "PASS"
    assert report.pcb["violations"] == report.pcb["unrouted"] == 0
    assert (tmp_path / "golden.kicad_pcb").is_file()
    assert (tmp_path / "golden.kicad_sch").is_file()
    assert (tmp_path / "fabrication" / "ohmni-fabrication-manifest.json").is_file()
