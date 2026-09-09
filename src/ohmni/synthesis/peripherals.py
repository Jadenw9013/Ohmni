"""Catalog-derived I2C blocks shared by the bounded archetype compilers."""

from ..domain import CircuitComponent, ComponentSpec, Interface, Net, PinRole, Quantity
from .a1 import (
    CAPACITOR_PART_ID,
    I2C_PULLUP_OHM,
    RESISTOR_PART_ID,
    _CatalogCapabilityError,
    _one_pin_with_role,
    _package,
    _pin_named,
    _pins,
)
from .placement import PlacementIntentBuilder, rail_evidence

SUPPORTED_I2C_PARTS = frozenset({"BME280", "TMP102AIDRLR"})


def address_option(spec: ComponentSpec, requested: int | None, used=()):
    options = sorted(spec.i2c_addresses, key=lambda item: (not item.is_default, item.address))
    if requested is not None:
        options = [item for item in options if item.address == requested]
    options = [item for item in options if item.address not in used]
    if not options:
        raise _CatalogCapabilityError(f"{spec.part_id} has no available requested I2C address")
    option = options[0]
    if option.strap_pin is None or option.strap_level not in {"low", "high"}:
        raise _CatalogCapabilityError(f"{spec.part_id} address requires unsupported strap topology")
    return option


def add_i2c_bus(components, nets, catalog, prefer_hand, *, resistor_refs=("R6", "R7"),
                placement: PlacementIntentBuilder | None = None):
    """Add one 3.3 V bus with explicit authored 4.7k pull-up policy."""
    mcu = catalog.require("ESP32-WROOM-32E")
    logic = next(net for net in nets if net.name == "3V3")
    package = _package(catalog, RESISTOR_PART_ID, prefer_hand)
    for name, pin_name, ref in zip(("SDA", "SCL"), ("IO21", "IO22"), resistor_refs, strict=True):
        components.append(CircuitComponent(
            ref=ref, part_id=RESISTOR_PART_ID, package=package,
            value=Quantity.ohms(I2C_PULLUP_OHM), notes="Authored I2C bus pull-up policy.",
        ))
        logic.connections.extend(_pins((ref, "2")))
        nets.append(Net(name=name, connections=_pins(("U1", _pin_named(mcu, pin_name)), (ref, "1"))))
    if placement is not None:
        placement.join("U1", resistor_refs)


def add_i2c_sensor(components, nets, catalog, slot, prefer_hand, *, ref, cap_refs, used_addresses=(),
                   placement: PlacementIntentBuilder | None = None):
    """Resolve one supported sensor, supply decoupling, mode, and address straps."""
    if slot.part_id not in SUPPORTED_I2C_PARTS:
        raise _CatalogCapabilityError(f"Unsupported I2C sensor topology: {slot.part_id}")
    spec = catalog.require(slot.part_id)
    if Interface.I2C not in spec.interfaces:
        raise _CatalogCapabilityError(f"{slot.part_id} has no catalog I2C interface")
    option = address_option(spec, slot.address, used_addresses)
    components.append(CircuitComponent(
        ref=ref, part_id=slot.part_id, package=_package(catalog, slot.part_id, prefer_hand),
        selected_i2c_address=option.address, selected_interfaces=[Interface.I2C],
    ))
    logic = next(net for net in nets if net.name == "3V3")
    ground = next(net for net in nets if net.name == "GND")
    logic.connections.extend(_pins(*[(ref, pin.number) for pin in spec.pins_with_role(PinRole.POWER)]))
    ground.connections.extend(_pins(*[(ref, pin.number) for pin in spec.pins_with_role(PinRole.GROUND)]))
    target = ground if option.strap_level == "low" else logic
    target.connections.extend(_pins((ref, option.strap_pin)))
    # The BME280's documented I2C mode requires CSB high. TMP102 is I2C-only.
    if slot.part_id == "BME280":
        logic.connections.extend(_pins((ref, _pin_named(spec, "CSB"))))
    for name, role in (("SDA", PinRole.I2C_SDA), ("SCL", PinRole.I2C_SCL)):
        next(net for net in nets if net.name == name).connections.extend(
            _pins((ref, _one_pin_with_role(spec, role)))
        )
    if len(cap_refs) < len(spec.supply_rails):
        raise _CatalogCapabilityError("Not enough decoupling slots for all sensor rails")
    for rail, cap_ref in zip(spec.supply_rails, cap_refs):
        rules = [rule for rule in spec.decoupling_rules if rule.rail == rail.name]
        if len(rules) != 1 or rules[0].per_pin_capacitance is None:
            raise _CatalogCapabilityError(f"{slot.part_id} lacks decoupling evidence for {rail.name}")
        components.append(CircuitComponent(
            ref=cap_ref, part_id=CAPACITOR_PART_ID,
            package=_package(catalog, CAPACITOR_PART_ID, prefer_hand),
            value=rules[0].per_pin_capacitance,
            notes=f"Catalog-derived {ref} {rail.name} local decoupling.",
        ))
        logic.connections.extend(_pins((cap_ref, "1")))
        ground.connections.extend(_pins((cap_ref, "2")))
        if placement is not None:
            power_pins = [pin.number for pin in spec.pins_with_role(PinRole.POWER)
                          if pin.supply_rail == rail.name]
            if len(power_pins) != 1:
                raise _CatalogCapabilityError(f"{slot.part_id} requires one physical supply owner for {rail.name}")
            placement.capacitor(cap_ref, ref, power_pins[0], evidence=rail_evidence(spec, rail.name))
    if placement is not None:
        placement.group("sensor", ref, (ref, *cap_refs[:len(spec.supply_rails)]),
                        "I2C sensor and the capacitors authored for its individual supply pins.")
    return option.address
