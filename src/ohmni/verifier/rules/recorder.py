"""Static recorder pin and mode contract; never a physical audio verdict."""
from ...domain import Interface
from ...domain.recorder import MIC_PART, RECORDER_PINS, SD_PART
from ...domain.verification import RuleCategory, Severity
from ..registry import rule


@rule("PB-AUDIO-001", "Recorder interfaces match the firmware GPIO contract",
      RuleCategory.INTERFACE, "Checks I2S clocks/data/channel, SD detect and record controls against the authored recorder pin policy.")
def recorder_topology(ctx, out):
    microphones = [c for c in ctx.circuit.components if c.part_id == MIC_PART]
    if not microphones:
        if any(Interface.I2S in c.selected_interfaces for c in ctx.circuit.components):
            out.missing("Selected I2S interface has no supported microphone")
        else:
            out.not_applicable("No recorder microphone")
        return
    def error(message, refs=()):
        out.finding(severity=Severity.ERROR, title=message, description=message,
                    components=list(refs), lesson_topic="digital-audio")
    if len(microphones) != 1:
        error("Recorder supports exactly one microphone")
    mcu = ctx.circuit.component("U1")
    if mcu is None or mcu.part_id != "ESP32-WROOM-32E":
        error("Recorder processor is absent or unsupported")
        return
    spec = ctx.spec_of("U1")
    if spec is None:
        out.missing("Recorder MCU catalog evidence unavailable")
        return
    by_name = {p.name:p.number for p in spec.pins}
    for ref, part_id, interface in (("MIC1", MIC_PART, Interface.I2S), ("SD1", SD_PART, Interface.SPI)):
        part = ctx.circuit.component(ref)
        if part is None or part.part_id != part_id or interface not in part.selected_interfaces:
            error(f"{ref} does not select the required recorder part/interface", (ref,))
    for key, ref, pin in (("bclk","MIC1","3"),("ws","MIC1","5"),("din","MIC1","4"),
                         ("sck","SD1","3"),("mosi","SD1","5"),("miso","SD1","4"),
                         ("cs","SD1","6"),("detect","SD1","9"),("button","SW1","1"),("led","R10","1")):
        gpio = by_name.get(f"IO{RECORDER_PINS[key]}")
        expected = ctx.circuit.net_of("U1", gpio) if gpio else None
        actual = ctx.circuit.net_of(ref, pin)
        out.examined(f"{ref}.{pin} to GPIO{RECORDER_PINS[key]}")
        if expected is None or actual is None or expected.name != actual.name:
            error(f"Recorder {key} does not match firmware GPIO{RECORDER_PINS[key]}", ("U1", ref))
    channel = ctx.circuit.net_of("MIC1", "6")
    if channel is None or channel.kind.value != "ground":
        error("Microphone SEL must be grounded for the left I2S slot", ("MIC1",))
    if not {Interface.SPI, Interface.I2S}.issubset(mcu.selected_interfaces):
        error("Recorder MCU must select SPI and I2S", ("U1",))
    out.limitation("Static GPIO contract only. Acoustic response, edge timing, card speed, peak power and firmware execution require physical tests.")
