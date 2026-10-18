"""USB mono WAV recorder with explicit I2S/SPI wiring and separate SD supply."""
from ..catalog import default_catalog
from ..domain import (
    CircuitComponent,
    CircuitIR,
    FunctionalRequirement,
    Interface,
    Net,
    NetKind,
    Quantity,
)
from ..domain.recorder import MIC_PART, RECORDER_PINS, SD_PART
from .a1 import _CatalogCapabilityError, _package, _pins, _refuse
from .a2 import _build, _requirements, _safe_gpio
from .base import common_preflight
from .models import ArchetypeId, RefusalCode, SynthesisBrief, SynthesisResult
from .placement import PlacementIntentBuilder, policy_evidence

RECORDER_LIMITATIONS = (
    "Firmware source and a deterministic digital recording simulation are included; physical recording has not been tested.",
    "Audio is mono 16-bit PCM WAV on a separately purchased FAT32 SDHC card (4–32 GB); playback uses a computer/card reader.",
    "The microphone and microSD are preassembled Adafruit breakout modules fitted above the carrier with headers; bare microphone chips are not interchangeable.",
    "The microphone port must face away from the carrier and remain unobstructed; module height and card access need assembly review.",
    "The 2 mA microphone and 400 mA SD assembly peak allocations are design assumptions requiring measurement with the actual card; they are not vendor guarantees.",
    "Wi-Fi and Bluetooth are not started by recorder firmware. USB input-current compliance, regulator temperature, write-current transients and brownout behavior require bench testing.",
    "Power loss or card removal during writing can corrupt the current file or filesystem. Stop recording before removing the card or power.",
    "Acoustic response, I2S edge timing, SD latency, EMI and enclosure acoustics are not established by the behavioral simulation.",
)


def recorder_brief(**changes):
    defaults = {"archetype": ArchetypeId.A4_USB_VOICE_RECORDER,
        "project_name": "Voice recorder", "description": "USB-powered mono WAV voice recorder with I2S microphone and removable microSD.",
        "sensors": (), "button_count": 1, "status_led_count": 1, "budget_usd": None,
        "hand_solderable_preferred": False}
    return SynthesisBrief.model_validate({**defaults, **changes})


def synthesize_a4(brief, catalog=None):
    catalog = catalog or default_catalog()
    if refusal := common_preflight(brief, catalog):
        return refusal
    if brief.archetype is not ArchetypeId.A4_USB_VOICE_RECORDER:
        return _refuse(brief, RefusalCode.ARCHETYPE_NOT_IMPLEMENTED, "Choose the voice recorder family.", "archetype")
    if brief.sensors or brief.spi_devices or brief.button_count != 1 or brief.status_led_count != 1 or not brief.include_programming_header:
        return _refuse(brief, RefusalCode.PERIPHERAL_SLOTS_UNSUPPORTED,
            "Recorder requires one record/stop button, one status LED and the programming header. Microphone and microSD are included; additional sensors and EEPROMs are unsupported.",
            "sensors", "spi_devices", "button_count", "status_led_count", "include_programming_header")
    if any(catalog.get(pid) is None for pid in (MIC_PART, SD_PART)):
        return _refuse(brief, RefusalCode.PART_UNAVAILABLE, "Recorder microphone or microSD module is unavailable.")
    try:
        placement = PlacementIntentBuilder(width_mm=brief.board_width_mm, height_mm=brief.board_height_mm)
        base = _build(brief, catalog, placement=placement)
        components, nets = base.components, base.nets
        gnd, logic, vbus = (next(n for n in nets if n.name == name) for name in ("GND", "3V3", "VBUS"))
        def component(ref, part, value=None):
            components.append(CircuitComponent(ref=ref, part_id=part,
                package=_package(catalog, part, brief.hand_solderable_preferred), value=value))
        component("MIC1", MIC_PART)
        component("SD1", SD_PART)
        component("U4", "AP2112K-3.3TRG1")
        for ref, cap in (("C8", 1e-6), ("C9", 1e-6), ("C10", 100e-9), ("C11", 22e-6), ("C12", 100e-9)):
            component(ref, "GENERIC_CAPACITOR", Quantity.farads(cap))
        component("R30", "GENERIC_RESISTOR", Quantity.ohms(10_000))
        logic.connections.extend(_pins(("MIC1", "1"), ("C12", "1")))
        vbus.connections.extend(_pins(("U4", "1"), ("U4", "3"), ("C8", "1")))
        gnd.connections.extend(_pins(("MIC1", "2"), ("MIC1", "6"), ("SD1", "2"), ("U4", "2"),
            *[(ref, "2") for ref in ("C8", "C9", "C10", "C11", "C12")]))
        nets.append(Net(name="SD_3V3", kind=NetKind.POWER,
            connections=_pins(("U4", "5"), ("C9", "1"), ("SD1", "1"), ("C10", "1"), ("C11", "1"), ("R30", "2"))))
        mcu = catalog.require(brief.mcu_part_id)
        for name, key, target, pin in (
            ("I2S_BCLK", "bclk", "MIC1", "3"), ("I2S_WS", "ws", "MIC1", "5"),
            ("I2S_DATA", "din", "MIC1", "4"), ("SPI_SCK", "sck", "SD1", "3"),
            ("SPI_MOSI", "mosi", "SD1", "5"), ("SPI_MISO", "miso", "SD1", "4"),
            ("SD_CS", "cs", "SD1", "6"), ("SD_DETECT", "detect", "SD1", "9")):
            gpio = _safe_gpio(mcu, f"IO{RECORDER_PINS[key]}", output=key not in {"din", "miso", "detect"})
            net = Net(name=name, connections=_pins(("U1", gpio), (target, pin)))
            if key == "cs": net.connections.extend(_pins(("R30", "1")))
            nets.append(net)
        for part in components:
            if part.ref == "U1": part.selected_interfaces = [Interface.GPIO, Interface.I2S, Interface.SPI]
            if part.ref == "MIC1": part.selected_interfaces = [Interface.I2S]
            if part.ref == "SD1": part.selected_interfaces = [Interface.SPI]
        placement.group("sensor", "MIC1", ("MIC1", "C12"), "I2S microphone with outward-facing acoustic port.")
        placement.capacitor("C12", "MIC1", "1")
        placement.group("spi", "SD1", ("SD1", "C10", "C11", "R30"), "Removable SD card storage with local bypass and bulk capacitance.")
        placement.capacitor("C10", "SD1", "1")
        placement.decoupling[-1] = placement.decoupling[-1].model_copy(update={
            "maximum_distance_mm": 6.0,
            "evidence": (policy_evidence("Carrier header bypass distance", "Authored 6 mm carrier bypass policy; module has an internal local bypass capacitor."),),
            "reason": "Carrier bypass within 6 mm of the module header; module also has its own local capacitor."})
        placement.capacitor("C11", "SD1", "1", bulk=True)
        placement.group("power", "U4", ("U4", "C8", "C9"), "Separate 3.3 V regulator for card write-current transients.")
        placement.capacitor("C8", "U4", "1")
        placement.capacitor("C9", "U4", "5")
        circuit = CircuitIR.model_validate({**base.model_dump(), "ir_id":f"a4-{brief.fingerprint[:16]}",
            "components":[c.model_dump() for c in components], "nets":[n.model_dump() for n in nets],
            "design_assumptions":list(RECORDER_LIMITATIONS), "notes":"Deterministic voice recorder carrier; included firmware uses the exact named GPIO assignment."})
        requirements = _requirements(brief).model_copy(update={
            "interfaces":[Interface.USB_POWER_SINK, Interface.GPIO, Interface.I2S, Interface.SPI, Interface.UART],
            "required_part_ids":[brief.mcu_part_id, MIC_PART, SD_PART],
            "assumptions":list(RECORDER_LIMITATIONS),
            "functional_requirements":[FunctionalRequirement(requirement_id="FR-REC", description=f"Record mono 16-bit WAV at {brief.recorder_sample_rate_hz} Hz for up to {brief.recorder_max_seconds} seconds per file, using a debounced record/stop button.")]})
        return SynthesisResult(brief_fingerprint=brief.fingerprint, circuit=circuit, requirements=requirements,
            placement_request=placement.finish(circuit))
    except (_CatalogCapabilityError, KeyError) as error:
        return _refuse(brief, RefusalCode.CATALOG_CAPABILITY_MISSING, str(error))
