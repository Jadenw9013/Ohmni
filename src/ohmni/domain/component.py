"""Component facts.

A :class:`ComponentSpec` is what the *part* is, as stated by its datasheet.
It is not what a particular instance on a board is doing -- that lives in
:mod:`ohmni.domain.circuit`. Keeping them apart is what makes the package
consistency rule and the passive-value rules expressible at all
(PRE_IMPLEMENTATION_REVIEW.md 5.3).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .evidence import DocumentRef, Evidence
from .units import Quantity, Unit, ValueRange


class Interface(StrEnum):
    """Buses and interfaces the MVP models. Free text belongs in `notes`."""

    I2C = "i2c"
    SPI = "spi"
    UART = "uart"
    GPIO = "gpio"
    ADC = "adc"
    PWM = "pwm"
    USB_DEVICE = "usb_device"
    USB_POWER_SINK = "usb_power_sink"
    ONE_WIRE = "one_wire"
    SWD = "swd"
    JTAG = "jtag"


class PinElectricalType(StrEnum):
    """Pin electrical types, using KiCad's exact vocabulary.

    Deliberate: our contention rules and KiCad ERC must not disagree about what
    an "output" is. Sharing the vocabulary means the compiler needs no lossy
    translation and the two checkers agree by construction
    (PRE_IMPLEMENTATION_REVIEW.md 5.7).
    """

    POWER_IN = "power_in"
    POWER_OUT = "power_out"
    INPUT = "input"
    OUTPUT = "output"
    BIDIRECTIONAL = "bidirectional"
    TRI_STATE = "tri_state"
    PASSIVE = "passive"
    OPEN_COLLECTOR = "open_collector"
    OPEN_EMITTER = "open_emitter"
    UNSPECIFIED = "unspecified"
    NO_CONNECT = "no_connect"
    FREE = "free"


#: Types that actively drive a net high and low, and therefore cannot share a
#: net with another such driver. Open-drain types are excluded on purpose: two
#: open-drain outputs with a pull-up is a normal, correct I2C bus.
PUSH_PULL_DRIVERS: frozenset[PinElectricalType] = frozenset(
    {PinElectricalType.OUTPUT, PinElectricalType.POWER_OUT}
)

#: Types that can source or sink a defined level onto a net.
DRIVING_TYPES: frozenset[PinElectricalType] = frozenset(
    {
        PinElectricalType.OUTPUT,
        PinElectricalType.POWER_OUT,
        PinElectricalType.BIDIRECTIONAL,
        PinElectricalType.TRI_STATE,
        PinElectricalType.OPEN_COLLECTOR,
        PinElectricalType.OPEN_EMITTER,
    }
)


class PinRole(StrEnum):
    """Semantic role of a pin. Drives which rules apply to it."""

    POWER = "power"
    GROUND = "ground"
    I2C_SDA = "i2c_sda"
    I2C_SCL = "i2c_scl"
    I2C_ADDRESS_SELECT = "i2c_address_select"
    SPI_MOSI = "spi_mosi"
    SPI_MISO = "spi_miso"
    SPI_SCK = "spi_sck"
    SPI_CS = "spi_cs"
    UART_TX = "uart_tx"
    UART_RX = "uart_rx"
    GPIO = "gpio"
    ANALOG_IN = "analog_in"
    ENABLE = "enable"
    RESET = "reset"
    BOOT_STRAP = "boot_strap"
    CRYSTAL = "crystal"
    USB_DP = "usb_dp"
    USB_DM = "usb_dm"
    USB_CC = "usb_cc"
    USB_VBUS = "usb_vbus"
    USB_SHIELD = "usb_shield"
    ANODE = "anode"
    CATHODE = "cathode"
    TERMINAL = "terminal"
    NOT_CONNECTED = "not_connected"
    OTHER = "other"


#: Roles whose pin must be driven to a defined level for the part to work.
#: Leaving one floating is a real, common, board-killing hobbyist mistake.
MUST_NOT_FLOAT_ROLES: frozenset[PinRole] = frozenset(
    {PinRole.ENABLE, PinRole.RESET, PinRole.BOOT_STRAP, PinRole.I2C_ADDRESS_SELECT}
)

I2C_BUS_ROLES: frozenset[PinRole] = frozenset({PinRole.I2C_SDA, PinRole.I2C_SCL})


class ComponentCategory(StrEnum):
    MCU_MODULE = "mcu_module"
    MCU = "mcu"
    SENSOR = "sensor"
    REGULATOR_LINEAR = "regulator_linear"
    REGULATOR_SWITCHING = "regulator_switching"
    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    LED = "led"
    DIODE = "diode"
    TRANSISTOR = "transistor"
    CONNECTOR = "connector"
    HEADER = "header"
    SWITCH = "switch"
    CRYSTAL = "crystal"
    MEMORY = "memory"
    OTHER = "other"


PASSIVE_CATEGORIES: frozenset[ComponentCategory] = frozenset(
    {
        ComponentCategory.RESISTOR,
        ComponentCategory.CAPACITOR,
        ComponentCategory.INDUCTOR,
    }
)


class Lifecycle(StrEnum):
    ACTIVE = "active"
    NRND = "nrnd"
    OBSOLETE = "obsolete"
    UNKNOWN = "unknown"


class PackageOption(BaseModel):
    """One package a part is actually offered in.

    Package suffixes change electrical characteristics and footprints; keeping
    the options explicit is what lets us reject an instance that asks for a
    package this part does not exist in.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    pin_count: int | None = Field(default=None, ge=1)
    hand_solderable: bool = True
    kicad_footprint: str | None = None
    notes: str | None = None


class SupplyRail(BaseModel):
    """One independent supply domain of a part.

    Real parts have more than one. BME280 has VDD and VDDIO with different
    limits; a level shifter has two by definition. The flat
    ``supply_voltage_min_v / _max_v`` fields in DOMAIN_MODEL.md cannot express
    this (PRE_IMPLEMENTATION_REVIEW.md 4.2).

    ``operating`` and ``absolute_max`` are separate on purpose. Recommended
    operating conditions are where the part is specified to work. The absolute
    maximum is where it stops being destroyed. Treating the second as a design
    target is the mistake this product exists to catch.
    """

    name: str
    operating: ValueRange
    absolute_max: Quantity | None = None
    absolute_min: Quantity | None = None
    current_typical: Quantity | None = None
    current_max: Quantity | None = Field(
        default=None,
        description="Peak current this rail can draw. Used for regulator sizing.",
    )
    evidence: list[Evidence] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def _check_units(self) -> SupplyRail:
        if self.operating.unit is not Unit.VOLT:
            raise ValueError(f"supply rail {self.name!r} operating range must be in volts")
        for field_name in ("absolute_max", "absolute_min"):
            q: Quantity | None = getattr(self, field_name)
            if q is not None and q.unit is not Unit.VOLT:
                raise ValueError(f"supply rail {self.name!r} {field_name} must be in volts")
        for field_name in ("current_typical", "current_max"):
            q = getattr(self, field_name)
            if q is not None and q.unit is not Unit.AMPERE:
                raise ValueError(f"supply rail {self.name!r} {field_name} must be in amperes")
        if self.absolute_max is not None:
            top = self.operating.maximum
            if top is not None and top > self.absolute_max:
                raise ValueError(
                    f"supply rail {self.name!r}: recommended operating maximum "
                    f"{top} exceeds absolute maximum {self.absolute_max}"
                )
        return self


class PinSpec(BaseModel):
    """One pin of a part."""

    number: str = Field(description="Datasheet pin number or pad designator, as printed.")
    name: str
    roles: list[PinRole] = Field(default_factory=lambda: [PinRole.OTHER])
    electrical_type: PinElectricalType = PinElectricalType.UNSPECIFIED
    supply_rail: str | None = Field(
        default=None,
        description=(
            "Name of the SupplyRail that powers or references this pin. For a power pin, "
            "the rail it belongs to. For an I/O pin, the rail that sets its logic level. "
            "This is a datasheet fact about the part, not an assertion about the board."
        ),
    )
    absolute_max: Quantity | None = Field(
        default=None, description="Absolute maximum voltage on this pin, when stated outright."
    )
    absolute_max_above_supply: Quantity | None = Field(
        default=None,
        description=(
            "Absolute maximum expressed as an offset above the supply rail, the way "
            "datasheets usually state it: 'VDD + 0.3 V'."
        ),
    )
    must_not_float: bool | None = Field(
        default=None,
        description="Override. When None, derived from `roles` via MUST_NOT_FLOAT_ROLES.",
    )
    internal_pull: Literal["up", "down", "none"] | None = None
    notes: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)

    @property
    def requires_defined_level(self) -> bool:
        if self.must_not_float is not None:
            return self.must_not_float
        return any(role in MUST_NOT_FLOAT_ROLES for role in self.roles)

    def has_role(self, *roles: PinRole) -> bool:
        return any(role in self.roles for role in roles)

    def absolute_max_for_supply(self, supply_voltage: Quantity | None) -> Quantity | None:
        """Resolve this pin's absolute maximum, given its rail's actual voltage.

        Returns None when the datasheet value is unknown. The caller must then
        report INSUFFICIENT_DATA rather than assuming a limit.
        """
        if self.absolute_max is not None:
            return self.absolute_max
        if self.absolute_max_above_supply is not None and supply_voltage is not None:
            return supply_voltage + self.absolute_max_above_supply
        return None


class I2CAddressOption(BaseModel):
    """One 7-bit address the part can occupy, and how it is selected."""

    model_config = ConfigDict(frozen=True)

    address: int = Field(ge=0x00, le=0x7F, description="7-bit address, excluding the R/W bit.")
    selected_by: str | None = Field(
        default=None, description='Human description, e.g. "SDO tied to GND".'
    )
    strap_pin: str | None = None
    strap_level: Literal["low", "high"] | None = None
    is_default: bool = False

    def __str__(self) -> str:
        return f"0x{self.address:02X}"


class DecouplingRule(BaseModel):
    """A decoupling requirement stated by the part's datasheet.

    ``max_distance_mm`` is recorded because the datasheet states it, but note
    that a netlist can never verify it. See ``decoupling`` rule limitations.
    """

    rail: str
    per_pin_capacitance: Quantity | None = None
    bulk_capacitance: Quantity | None = None
    max_distance_mm: float | None = None
    note: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class DesignRule(BaseModel):
    """Advisory guidance from a datasheet that is not mechanically checkable yet.

    Recorded so it can be surfaced to the user and carried into the notebook,
    rather than silently dropped because we cannot verify it.
    """

    rule_id: str
    description: str
    category: Literal["layout", "thermal", "emc", "assembly", "firmware", "other"] = "other"
    evidence: list[Evidence] = Field(default_factory=list)


class RegulatorSpec(BaseModel):
    """Voltage regulator characteristics. Present only on regulator parts."""

    output_voltage: ValueRange
    output_current_max: Quantity
    input_voltage: ValueRange
    dropout_at_max_current: Quantity | None = None
    quiescent_current: Quantity | None = None
    fixed_output: bool = True
    evidence: list[Evidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_units(self) -> RegulatorSpec:
        if self.output_voltage.unit is not Unit.VOLT or self.input_voltage.unit is not Unit.VOLT:
            raise ValueError("regulator voltages must be in volts")
        if self.output_current_max.unit is not Unit.AMPERE:
            raise ValueError("regulator output_current_max must be in amperes")
        return self


class LedSpec(BaseModel):
    """LED characteristics. Present only on LED parts."""

    forward_voltage: ValueRange
    max_forward_current: Quantity
    test_current: Quantity | None = None
    colour: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_units(self) -> LedSpec:
        if self.forward_voltage.unit is not Unit.VOLT:
            raise ValueError("LED forward_voltage must be in volts")
        if self.max_forward_current.unit is not Unit.AMPERE:
            raise ValueError("LED max_forward_current must be in amperes")
        return self


class ComponentSpec(BaseModel):
    """Everything the catalog knows about a part.

    ``part_id`` is our catalog key and is always present. ``mpn`` is a real,
    orderable manufacturer part number and is **nullable**, because a generic
    4.7 kohm 0805 resistor has no meaningful MPN at design time and the product's
    hard target is "invented MPNs: 0" (PRE_IMPLEMENTATION_REVIEW.md 5.2).
    """

    part_id: str
    mpn: str | None = None
    manufacturer: str | None = None
    category: ComponentCategory
    description: str = ""
    is_generic: bool = False
    lifecycle: Lifecycle = Lifecycle.UNKNOWN

    packages: list[PackageOption] = Field(default_factory=list)
    pins: list[PinSpec] = Field(default_factory=list)
    supply_rails: list[SupplyRail] = Field(default_factory=list)
    interfaces: list[Interface] = Field(default_factory=list)
    i2c_addresses: list[I2CAddressOption] = Field(default_factory=list)

    regulator: RegulatorSpec | None = None
    led: LedSpec | None = None

    decoupling_rules: list[DecouplingRule] = Field(default_factory=list)
    design_rules: list[DesignRule] = Field(default_factory=list)

    datasheet: DocumentRef | None = None
    evidence: list[Evidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_internal_consistency(self) -> ComponentSpec:
        if not self.is_generic and not self.mpn:
            raise ValueError(
                f"part {self.part_id!r} is not generic and must carry a real MPN; "
                "if no orderable part number exists, mark it is_generic"
            )
        numbers = [pin.number for pin in self.pins]
        duplicates = {n for n in numbers if numbers.count(n) > 1}
        if duplicates:
            raise ValueError(f"part {self.part_id!r} has duplicate pin numbers: {sorted(duplicates)}")
        rail_names = {rail.name for rail in self.supply_rails}
        for pin in self.pins:
            if pin.supply_rail is not None and pin.supply_rail not in rail_names:
                raise ValueError(
                    f"part {self.part_id!r} pin {pin.number} references unknown supply rail "
                    f"{pin.supply_rail!r}; known rails: {sorted(rail_names)}"
                )
        package_names = [p.name for p in self.packages]
        dup_packages = {n for n in package_names if package_names.count(n) > 1}
        if dup_packages:
            raise ValueError(f"part {self.part_id!r} has duplicate packages: {sorted(dup_packages)}")
        if self.regulator is not None and self.category not in (
            ComponentCategory.REGULATOR_LINEAR,
            ComponentCategory.REGULATOR_SWITCHING,
        ):
            raise ValueError(f"part {self.part_id!r} carries a RegulatorSpec but is not a regulator")
        if self.led is not None and self.category is not ComponentCategory.LED:
            raise ValueError(f"part {self.part_id!r} carries a LedSpec but is not an LED")
        addresses = [opt.address for opt in self.i2c_addresses]
        if len(addresses) != len(set(addresses)):
            raise ValueError(f"part {self.part_id!r} lists the same I2C address twice")
        return self

    # -- lookups ---------------------------------------------------------

    def pin(self, number: str) -> PinSpec | None:
        for p in self.pins:
            if p.number == number:
                return p
        return None

    def pins_with_role(self, *roles: PinRole) -> list[PinSpec]:
        return [p for p in self.pins if p.has_role(*roles)]

    def rail(self, name: str) -> SupplyRail | None:
        for r in self.supply_rails:
            if r.name == name:
                return r
        return None

    def package(self, name: str) -> PackageOption | None:
        for p in self.packages:
            if p.name == name:
                return p
        return None

    def rail_for_pin(self, pin: PinSpec) -> SupplyRail | None:
        if pin.supply_rail is None:
            return None
        return self.rail(pin.supply_rail)

    @property
    def display_name(self) -> str:
        return self.mpn or self.part_id

    @property
    def total_current_max(self) -> Quantity | None:
        """Worst-case current across all rails, when every rail states one.

        Returns None if any rail is missing a figure -- an incomplete sum would
        understate the load, and a regulator sized against an understated load
        is exactly the failure we are trying to prevent.
        """
        if not self.supply_rails:
            return None
        total = 0.0
        for rail in self.supply_rails:
            if rail.current_max is None:
                return None
            total += rail.current_max.value
        return Quantity(value=total, unit=Unit.AMPERE)
