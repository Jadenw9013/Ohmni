"""Bounded deterministic circuit synthesis."""

from .a1 import synthesize_a1
from .a2 import synthesize_a2
from .a3 import synthesize_a3
from .models import (
    ArchetypeId,
    I2cSensorSlot,
    InputPower,
    RefusalCode,
    SpiPeripheralSlot,
    SynthesisBrief,
    SynthesisRefusal,
    SynthesisResult,
)


def synthesize(brief: SynthesisBrief, catalog=None) -> SynthesisResult:
    """Dispatch a validated brief to its deterministic archetype compiler."""
    compiler = {
        ArchetypeId.A1_USB_I2C_SENSOR: synthesize_a1,
        ArchetypeId.A2_USB_GPIO_CONTROLLER: synthesize_a2,
        ArchetypeId.A3_USB_SPI_PERIPHERAL: synthesize_a3,
    }[brief.archetype]
    return compiler(brief, catalog)

__all__ = [
    "ArchetypeId",
    "I2cSensorSlot",
    "InputPower",
    "RefusalCode",
    "SpiPeripheralSlot",
    "SynthesisBrief",
    "SynthesisRefusal",
    "SynthesisResult",
    "synthesize",
    "synthesize_a1",
    "synthesize_a2",
    "synthesize_a3",
]
