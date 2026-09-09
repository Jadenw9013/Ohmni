"""Bounded four-wire SPI topology checks; no firmware or timing verdict.

The ESP32 GPIO assignment is an authored A3 policy, not an assertion that
these are its only SPI-capable pins. Peripheral pin roles come from the
catalog. Active-low chip-select behavior is presently supported only for
the cataloged 25LC256; other polarities remain insufficient data.
"""

from __future__ import annotations

from ...domain.circuit import NetKind, PinRef
from ...domain.component import ComponentCategory, Interface, PinElectricalType, PinRole
from ...domain.units import Unit
from ...domain.verification import RuleCategory, Severity
from ..context import ResolvedPin, VerificationContext
from ..registry import ResultBuilder, rule

_SIGNALS = (PinRole.SPI_MOSI, PinRole.SPI_MISO, PinRole.SPI_SCK, PinRole.SPI_CS)
_CONTROLLERS = (ComponentCategory.MCU, ComponentCategory.MCU_MODULE)
_OUTPUT_CAPABLE = (PinElectricalType.OUTPUT, PinElectricalType.BIDIRECTIONAL)
_ESP32_ASSIGNMENT = {
    "IO18": PinRole.SPI_SCK,
    "IO19": PinRole.SPI_MISO,
    "IO23": PinRole.SPI_MOSI,
}


def _controller_role(pin: ResolvedPin) -> PinRole | None:
    assert pin.pin is not None and pin.spec is not None
    declared = [role for role in _SIGNALS if pin.pin.has_role(role)]
    if len(declared) == 1:
        return declared[0]
    if declared:
        return None
    if pin.spec.part_id == "ESP32-WROOM-32E":
        assigned = _ESP32_ASSIGNMENT.get(pin.pin.name)
        if assigned is not None and pin.pin.has_role(PinRole.GPIO):
            return assigned
    # A chip select may use a GPIO. The caller checks its electrical type.
    if pin.pin.has_role(PinRole.GPIO):
        return PinRole.SPI_CS
    return None


def _error(out: ResultBuilder, title: str, description: str, refs=(), nets=()) -> None:
    out.finding(
        severity=Severity.ERROR, title=title, description=description,
        components=refs, nets=nets, lesson_topic="spi-basics",
    )


def _inactive_select(ctx: VerificationContext, pin: ResolvedPin, out: ResultBuilder) -> None:
    assert pin.pin is not None and pin.spec is not None and pin.net is not None
    if pin.spec.part_id != "25LC256-I/SN":
        out.missing(f"{pin.ref.component}: SPI chip-select inactive polarity is not modeled")
        return
    domain = ctx.logic_domain(pin)
    if domain is None or domain.nominal is None:
        out.missing(f"{pin}: chip-select supply cannot be resolved")
        return
    pulls = ctx.pull_ups_on(pin.net.name)
    if not pulls:
        _error(
            out, f"{pin.ref.component} chip select has no inactive pull-up",
            "The supported 25LC256 chip select is active low. A GPIO connection alone "
            "does not hold it inactive while the controller resets; add a resistor "
            "from chip select to the peripheral's logic supply.",
            [pin.ref.component], [pin.net.name],
        )
    for bridge, voltage in pulls:
        out.examined(f"{bridge.ref}: inactive pull-up for {pin}")
        if voltage.net_name != domain.net_name:
            _error(
                out, f"{pin.ref.component} chip-select pull-up uses another supply",
                f"{bridge.ref} connects to {voltage.net_name!r}; the supported topology "
                f"requires the peripheral's own logic supply {domain.net_name!r}.",
                [pin.ref.component, bridge.ref], [pin.net.name, voltage.net_name],
            )
        if bridge.value is None:
            out.missing(f"{bridge.ref}: inactive pull-up resistance is unknown")
        elif bridge.value.unit is not Unit.OHM or bridge.value.value <= 0:
            _error(
                out, f"{bridge.ref} is not a positive chip-select pull-up resistance",
                "A selectable chip-select line needs a resistor, not a direct supply tie.",
                [pin.ref.component, bridge.ref], [pin.net.name],
            )
    if ctx.bridges_to_ground(
        pin.net.name, categories=frozenset({ComponentCategory.RESISTOR})
    ):
        _error(
            out, f"{pin.ref.component} chip select also has a pull-down",
            "The active-low select is biased toward its active state. This check does "
            "not treat competing pull resistors as a verified inactive level.",
            [pin.ref.component], [pin.net.name],
        )


@rule(
    "PB-SPI-001",
    "Supported four-wire SPI signals and chip selects are independently connected",
    RuleCategory.INTERFACE,
    "Checks signal roles, controller ownership, tri-state MISO and inactive chip-select bias.",
)
def spi_topology(ctx: VerificationContext, out: ResultBuilder) -> None:
    participants = []
    for instance in ctx.circuit.components:
        spec = ctx.spec_of(instance.ref)
        selected = Interface.SPI in instance.selected_interfaces
        # A SPI-only peripheral cannot disappear from coverage by omitting its mode.
        spi_only = spec is not None and spec.interfaces == [Interface.SPI]
        if not selected and not spi_only:
            continue
        out.examined(f"{instance.ref}: SPI interface selection")
        if spec is None:
            out.missing(f"{instance.ref}: SPI part is absent from the catalog")
            continue
        if spec.category in _CONTROLLERS:
            continue
        participants.append(instance)
        if not selected:
            _error(
                out, f"{instance.ref} has no selected SPI interface",
                "The SPI-only peripheral is present but its instance does not select SPI.",
                [instance.ref],
            )
        if Interface.SPI not in spec.interfaces:
            out.missing(f"{instance.ref}: catalog does not declare SPI support")
        if Interface.I2C in instance.selected_interfaces:
            out.missing(f"{instance.ref}: simultaneous I2C/SPI peripheral modes are not modeled")

    if not participants:
        if any(Interface.SPI in c.selected_interfaces for c in ctx.circuit.components):
            out.missing("a selected SPI interface has no resolved SPI peripheral")
        else:
            out.not_applicable("no selected SPI interface or SPI-only peripheral")
        return

    controller_refs: set[str] = set()
    chip_selects: dict[str, list[str]] = {}
    shared_signals: dict[PinRole, set[str]] = {}
    for instance in participants:
        spec = ctx.spec_of(instance.ref)
        assert spec is not None
        signal_nets: dict[str, list[str]] = {}
        for role in _SIGNALS:
            pins = spec.pins_with_role(role)
            if len(pins) != 1:
                out.missing(f"{instance.ref}: expected one {role.value} pin, found {len(pins)}")
                continue
            pin = ctx.resolve(PinRef(component=instance.ref, pin=pins[0].number))
            assert pin is not None and pin.pin is not None
            out.examined(str(pin))
            required_type = (
                PinElectricalType.TRI_STATE if role is PinRole.SPI_MISO
                else PinElectricalType.INPUT
            )
            if pin.pin.electrical_type is not required_type:
                _error(
                    out, f"{pin} has incompatible SPI electrical behavior",
                    f"The supported peripheral topology requires {role.value} to be "
                    f"{required_type.value}; the catalog declares {pin.pin.electrical_type.value}. "
                    "Shared MISO needs each deselected peripheral to release the line.",
                    [instance.ref],
                )
            domain = ctx.logic_domain(pin)
            if domain is None or not domain.is_known:
                out.missing(f"{pin}: SPI logic supply is unknown")
            net = pin.net
            if net is None:
                _error(
                    out, f"{pin} is not connected", "A required SPI signal has no net.",
                    [instance.ref],
                )
                continue
            signal_nets.setdefault(net.name, []).append(role.value)
            if role is not PinRole.SPI_CS:
                shared_signals.setdefault(role, set()).add(net.name)
            if net.kind is not NetKind.SIGNAL or ctx.net_voltage(net.name).is_known:
                _error(
                    out, f"{pin} is tied to a supply instead of a SPI signal",
                    "Clock, data and independently selectable chip selects must be signal nets.",
                    [instance.ref], [net.name],
                )
            if role is PinRole.SPI_CS:
                chip_selects.setdefault(net.name, []).append(instance.ref)
                _inactive_select(ctx, pin, out)
            controllers = []
            for peer in ctx.pins_on(net):
                if peer.ref == pin.ref:
                    continue
                if peer.pin is None or peer.spec is None:
                    out.missing(f"{net.name}: unresolved peer {peer.ref}")
                    continue
                if peer.spec.category in _CONTROLLERS:
                    controllers.append(peer)
                    continue
                if peer.pin.electrical_type is PinElectricalType.PASSIVE:
                    continue
                if not (
                    Interface.SPI in peer.instance.selected_interfaces
                    and peer.pin.has_role(role)
                    and peer.pin.electrical_type is required_type
                ):
                    _error(
                        out, f"{net.name!r} includes a mismatched SPI peer",
                        f"{peer} does not match the peripheral {role.value} role and behavior.",
                        [instance.ref, peer.ref.component], [net.name],
                    )
            if len(controllers) != 1:
                _error(
                    out, f"{pin} needs exactly one controller pin",
                    f"Found {len(controllers)} controller pins on {net.name!r}; a shared "
                    "SPI line must have one controller connection.",
                    [instance.ref, *(p.ref.component for p in controllers)], [net.name],
                )
                continue
            controller = controllers[0]
            assert controller.pin is not None and controller.spec is not None
            controller_refs.add(controller.ref.component)
            if Interface.SPI not in controller.spec.interfaces:
                out.missing(f"{controller.ref.component}: catalog does not declare SPI support")
            valid_types = (
                (PinElectricalType.INPUT, PinElectricalType.BIDIRECTIONAL)
                if role is PinRole.SPI_MISO else _OUTPUT_CAPABLE
            )
            if (
                Interface.SPI not in controller.instance.selected_interfaces
                or _controller_role(controller) is not role
                or controller.pin.electrical_type not in valid_types
            ):
                _error(
                    out, f"{controller} does not match {role.value}",
                    "The controller must select SPI and use the matching catalog role or "
                    "the supported ESP32 assignment (IO18 clock, IO19 MISO, IO23 MOSI), "
                    "with a separate output-capable GPIO for each chip select.",
                    [instance.ref, controller.ref.component], [net.name],
                )
            controller_domain = ctx.logic_domain(controller)
            if controller_domain is None or not controller_domain.is_known:
                out.missing(f"{controller}: SPI controller logic supply is unknown")
        for net_name, roles in signal_nets.items():
            if len(roles) > 1:
                _error(
                    out, f"{instance.ref} has shorted SPI functions",
                    f"{', '.join(roles)} share {net_name!r}; four-wire SPI needs distinct nets.",
                    [instance.ref], [net_name],
                )
    if len(controller_refs) > 1:
        _error(
            out, "SPI signals are split across controllers",
            "The supported SPI topology has one controller for all data, clock and selects.",
            sorted(controller_refs),
        )
    for role, nets in shared_signals.items():
        if len(nets) > 1:
            _error(
                out, f"SPI peripherals do not share {role.value}",
                "The supported topology places every SPI peripheral on the same clock, "
                "MOSI and MISO nets, with separate chip selects.",
                [instance.ref for instance in participants], sorted(nets),
            )
    for net_name, refs in chip_selects.items():
        if len(refs) > 1:
            _error(
                out, "SPI peripherals share a chip select",
                "Each peripheral needs its own controller-driven select so shared MISO "
                "outputs can be selected independently.",
                refs, [net_name],
            )
    out.limitation(
        "SPI PASS covers the supported four-wire topology and presence of inactive "
        "chip-select pull-ups. Firmware must configure the stated GPIO functions, "
        "keep all other selects inactive and use compatible clock polarity, phase and "
        "frequency. Runtime select exclusivity, power-up sequencing, pull-up strength, "
        "signal integrity and data transfers are not verified."
    )
