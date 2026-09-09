"""Typed input and output contracts for deterministic circuit synthesis."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..domain import CircuitIR, RequirementsSpec, SafetyDomain
from ..physical.models import PlacementRequest


class ArchetypeId(StrEnum):
    """Bounded board families in the v1 product contract."""

    A1_USB_I2C_SENSOR = "a1_usb_i2c_sensor"
    A2_USB_GPIO_CONTROLLER = "a2_usb_gpio_controller"
    A3_USB_SPI_PERIPHERAL = "a3_usb_spi_peripheral"


class InputPower(StrEnum):
    """Input-power choices accepted by the form, including refusal cases."""

    USB_C_5V = "usb_c_5v"
    DC = "dc"
    BATTERY = "battery"
    MAINS = "mains"


class I2cSensorSlot(BaseModel):
    """One requested sensor instance on the A1 shared I2C bus."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    part_id: str = Field(min_length=1)
    address: int | None = Field(default=None, ge=0x00, le=0x7F)


class SpiPeripheralSlot(BaseModel):
    """One catalog peripheral; synthesis assigns a distinct chip-select pin."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    part_id: str = Field(min_length=1)


class SynthesisBrief(BaseModel):
    """A strict, versioned brief that can be synthesized without prose inference."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    schema_version: Literal[1] = 1
    project_name: str = Field(default="ESP32 sensor node", min_length=1, max_length=120)
    description: str = Field(
        default="USB-C powered ESP32 I2C sensor node.", min_length=1, max_length=1000
    )
    archetype: ArchetypeId = ArchetypeId.A1_USB_I2C_SENSOR
    input_power: InputPower = InputPower.USB_C_5V
    input_voltage_v: float = Field(default=5.0, gt=0)
    logic_voltage_v: float = Field(default=3.3, gt=0)
    mcu_part_id: str = Field(default="ESP32-WROOM-32E", min_length=1)
    sensors: tuple[I2cSensorSlot, ...] = Field(
        default_factory=lambda: (I2cSensorSlot(part_id="BME280"),)
    )
    status_led_count: int = Field(default=1, ge=0)
    button_count: int = Field(default=0, ge=0)
    spi_devices: tuple[SpiPeripheralSlot, ...] = Field(default_factory=tuple)
    include_programming_header: bool = True
    max_board_layers: int = Field(default=2, ge=1, le=8)
    hand_solderable_preferred: bool = True
    budget_usd: float | None = Field(default=20.0, ge=0)
    safety_domains: tuple[SafetyDomain, ...] = Field(default_factory=tuple)

    @property
    def fingerprint(self) -> str:
        """Stable identity for the complete input brief."""

        values = self.model_dump(mode="json")
        # Schema-v1 saved A1 inputs predate these optional slots. Empty new
        # slots preserve their existing fingerprint and artifact lineage.
        for name in ("button_count", "spi_devices"):
            if not values[name]:
                del values[name]
        payload = json.dumps(values, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RefusalCode(StrEnum):
    """Stable machine-readable reasons a well-formed brief is not synthesized."""

    SAFETY_DOMAIN_UNSUPPORTED = "safety_domain_unsupported"
    ARCHETYPE_NOT_IMPLEMENTED = "archetype_not_implemented"
    INPUT_POWER_UNSUPPORTED = "input_power_unsupported"
    INPUT_VOLTAGE_UNSUPPORTED = "input_voltage_unsupported"
    LOGIC_VOLTAGE_UNSUPPORTED = "logic_voltage_unsupported"
    LAYER_COUNT_UNSUPPORTED = "layer_count_unsupported"
    MCU_UNSUPPORTED = "mcu_unsupported"
    SENSOR_COUNT_UNSUPPORTED = "sensor_count_unsupported"
    SENSOR_UNAVAILABLE = "sensor_unavailable"
    SENSOR_INTERFACE_UNSUPPORTED = "sensor_interface_unsupported"
    SENSOR_ADDRESS_UNAVAILABLE = "sensor_address_unavailable"
    STATUS_LED_COUNT_UNSUPPORTED = "status_led_count_unsupported"
    BUTTON_COUNT_UNSUPPORTED = "button_count_unsupported"
    PERIPHERAL_SLOTS_UNSUPPORTED = "peripheral_slots_unsupported"
    SPI_COUNT_UNSUPPORTED = "spi_count_unsupported"
    SPI_UNAVAILABLE = "spi_unavailable"
    SENSOR_ADDRESS_CONFLICT = "sensor_address_conflict"
    PART_UNAVAILABLE = "part_unavailable"
    CATALOG_CAPABILITY_MISSING = "catalog_capability_missing"


class SynthesisRefusal(BaseModel):
    """A safe stop: predictable to callers and specific enough to resolve."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: RefusalCode
    message: str
    field_paths: tuple[str, ...] = Field(default_factory=tuple)
    context: dict[str, str] = Field(default_factory=dict)


class SynthesisResult(BaseModel):
    """Exactly one of an accepted design or a typed refusal."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    brief_fingerprint: str = Field(min_length=64, max_length=64)
    requirements: RequirementsSpec | None = None
    circuit: CircuitIR | None = None
    refusal: SynthesisRefusal | None = None
    placement_request: PlacementRequest | None = None

    @model_validator(mode="after")
    def _accepted_or_refused(self) -> SynthesisResult:
        accepted = self.requirements is not None and self.circuit is not None
        refused = self.refusal is not None
        if accepted == refused:
            raise ValueError("result must contain either requirements+circuit or a refusal")
        if not accepted and (self.requirements is not None or self.circuit is not None):
            raise ValueError("partial synthesis results are not allowed")
        if self.placement_request is not None and (
            self.circuit is None or self.placement_request.circuit_content_hash != self.circuit.content_hash
        ):
            raise ValueError("placement request must bind the accepted circuit fingerprint")
        return self

    @property
    def accepted(self) -> bool:
        return self.circuit is not None


__all__ = [
    "ArchetypeId",
    "I2cSensorSlot",
    "InputPower",
    "RefusalCode",
    "SpiPeripheralSlot",
    "SynthesisBrief",
    "SynthesisRefusal",
    "SynthesisResult",
]
