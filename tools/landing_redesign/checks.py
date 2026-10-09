"""Pure, design-specific topology checks for the landing PCB redesign.

These checks neither run the product verifier nor establish a functioning buck,
USB current entitlement, physical fit, EMC, or manufacturing readiness. A clean
result always retains UNKNOWN system status. No network, file, or model access.
"""

from __future__ import annotations

from collections import Counter
from math import isclose, isfinite
from typing import Protocol

from ohmni.domain.circuit import CircuitIR, ExternalSourceKind
from ohmni.domain.component import ComponentCategory, ComponentSpec, PinElectricalType
from ohmni.domain.units import Unit

TI_BUCK = "https://www.ti.com/lit/ds/symlink/tlv62569.pdf"
TI_DIVIDER = "https://www.ti.com/lit/ug/tidued0/tidued0.pdf"
TI_TRANSLATOR = "https://www.ti.com/lit/ds/symlink/pca9306.pdf"


class Catalog(Protocol):
    def get(self, part_id: str) -> ComponentSpec | None: ...


def feedback_voltage_bounds(
    upper_ohms: float, lower_ohms: float, resistor_tolerance_fraction: float = 0.01
) -> dict[str, object]:
    """Conditional DC divider arithmetic, not a converter simulation.

    The 1% tolerance is a BOM requirement; generic resistor instances do not
    independently establish it. TI SLVSDG1C p4 supplies the reference limits.
    """
    values = (upper_ohms, lower_ohms, resistor_tolerance_fraction)
    if not all(isfinite(value) for value in values):
        raise ValueError("divider inputs must be finite")
    if upper_ohms <= 0 or lower_ohms <= 0 or not 0 <= resistor_tolerance_fraction < 1:
        raise ValueError("positive resistances and tolerance in [0, 1) are required")
    tolerance = resistor_tolerance_fraction
    return {
        "status": "CONDITIONAL_CALCULATION",
        "nominal_V": 0.6 * (1 + upper_ohms / lower_ohms),
        "minimum_V": 0.588 * (1 + upper_ohms * (1 - tolerance)
                              / (lower_ohms * (1 + tolerance))),
        "maximum_V": 0.612 * (1 + upper_ohms * (1 + tolerance)
                              / (lower_ohms * (1 - tolerance))),
        "resistor_tolerance_fraction": tolerance,
        "tolerance_status": "BOM_REQUIREMENT_NOT_COMPONENT_VERIFIED",
        "reference_V": {"minimum": 0.588, "typical": 0.6, "maximum": 0.612},
        "source": {"url": TI_BUCK, "pages": [4, 9]},
        "excludes": ["switching ripple", "load transients", "start-up", "PCB parasitics"],
    }


def check_design(
    circuit: CircuitIR, catalog: Catalog, *, include_i2c_extension: bool = False
) -> dict[str, object]:
    """Return deterministic JSON-safe findings for this specific authored design."""
    components = {part.ref: part for part in circuit.components}
    findings: list[dict[str, object]] = []

    def record(identifier: str, ok: bool, detail: str, source: str | None = None) -> bool:
        findings.append({"id": identifier, "status": "PASS" if ok else "FAIL",
                         "detail": detail, "source_url": source})
        return ok

    def part_spec(ref: str) -> ComponentSpec | None:
        part = components.get(ref)
        return catalog.get(part.part_id) if part else None

    def net_name(ref: str, pin: str) -> str | None:
        net = circuit.net_of(ref, pin)
        return net.name if net else None

    def on(ref: str, mapping: dict[str, str]) -> bool:
        return ref in components and all(net_name(ref, p) == n for p, n in mapping.items())

    def pins(net: str) -> set[tuple[str, str]]:
        node = circuit.net(net)
        return {(pin.component, pin.pin) for pin in node.connections} if node else set()

    def passive(ref: str, category: ComponentCategory, unit: Unit,
                value: float, first: str, second: str) -> bool:
        part, spec = components.get(ref), part_spec(ref)
        return bool(part and spec and spec.category == category and part.value
                    and part.value.unit == unit and isclose(part.value.value, value, rel_tol=1e-9)
                    and {net_name(ref, "1"), net_name(ref, "2")} == {first, second})

    def resistor(ref: str, ohms: float, first: str, second: str) -> bool:
        return passive(ref, ComponentCategory.RESISTOR, Unit.OHM, ohms, first, second)

    def capacitor(ref: str, farads: float, first: str, second: str = "GND") -> bool:
        return passive(ref, ComponentCategory.CAPACITOR, Unit.FARAD, farads, first, second)

    memberships = Counter((p.component, p.pin) for n in circuit.nets for p in n.connections)
    integrity = (len(components) == len(circuit.components)
                 and len({net.name for net in circuit.nets}) == len(circuit.nets)
                 and all(count == 1 for count in memberships.values())
                 and all(ref in components and part_spec(ref) and part_spec(ref).pin(pin)
                         for ref, pin in memberships))
    record("IR_PIN_MEMBERSHIP", integrity,
           "Each connected catalog pin belongs to one net and an existing component.")

    buck = part_spec("U2")
    buck_names = {pin.number: pin.name for pin in buck.pins} if buck else {}
    record("BUCK_CATALOG_PINOUT", bool(buck and buck.part_id == "TLV62569DBVR"
           and buck_names == {"1": "EN", "2": "GND", "3": "SW", "4": "VIN", "5": "FB"}),
           "TLV62569 DBV pin identities must match the manufacturer table, p3.", TI_BUCK)
    buck_topology = record("BUCK_PIN_NETS", on("U2", {
        "1": "VBUS", "2": "GND", "3": "SW_NODE", "4": "VBUS", "5": "FB_REFB"}),
        "EN/VIN use VBUS; SW feeds the inductor; FB reads the divider, p3.", TI_BUCK)
    record("BUCK_NOT_FIXED_DC_SOURCE", bool(buck and buck.regulator is None
           and buck.pin("3") and buck.pin("3").electrical_type != PinElectricalType.POWER_OUT),
           "SW must not masquerade as a verified fixed DC regulator output.")
    inductor_ok = passive("L1", ComponentCategory.INDUCTOR, Unit.HENRY,
                          2.2e-6, "SW_NODE", "3V3")
    sw_members = pins("SW_NODE")
    inductor_ok = (inductor_ok and components["L1"].part_id == "XAL4020-222MEB"
                   and len(sw_members) == 2 and ("U2", "3") in sw_members)
    record("BUCK_OUTPUT_FILTER", inductor_ok,
           "A 2.2 uH inductor connects the sole SW pin to 3V3; no direct SW-to-rail join.",
           TI_BUCK)
    filter_caps_ok = capacitor("C1", 4.7e-6, "VBUS") and capacitor("C2", 10e-6, "3V3")
    record("BUCK_FILTER_CAPACITORS", filter_caps_ok,
           "Required local 4.7 uF input and 10 uF output capacitor connectivity, pp8-10.", TI_BUCK)
    feedback_ok = (resistor("R6", 453000, "3V3", "FB_REFB")
                   and resistor("R7", 100000, "FB_REFB", "GND")
                   and len(pins("FB_REFB")) == 3)
    record("BUCK_FEEDBACK_DIVIDER", feedback_ok,
           "453 kohm upper / 100 kohm lower divider with no additional FB connection, p18.",
           TI_DIVIDER)

    record("ESP32_SUPPLY_DECOUPLING", on("U1", {"2": "3V3"})
           and capacitor("C3", 100e-9, "3V3") and capacitor("C4", 22e-6, "3V3"),
           "Retained authored 100 nF local plus 22 uF bulk; proximity and effective C unknown.")
    record("ESP32_ENABLE_RC", on("U1", {"3": "EN"})
           and resistor("R3", 10000, "3V3", "EN") and capacitor("C5", 1e-6, "EN"),
           "The authored module enable uses 10 kohm / 1 uF; actual reset timing remains unknown.")
    record("SENSOR_LOW_VOLTAGE_DOMAIN", on("U3", {
        "1": "GND", "5": "GND", "7": "GND", "2": "3V3", "6": "3V3", "8": "3V3",
        "3": "SDA_3V3", "4": "SCL_3V3"})
        and capacitor("C6", 100e-9, "3V3") and capacitor("C7", 100e-9, "3V3"),
        "BME280 supplies, CSB, data and clock remain on their authored low-voltage domains.")
    record("LOW_I2C_PULLUPS", on("U1", {"33": "SDA_3V3", "36": "SCL_3V3"})
           and resistor("R4", 4700, "SDA_3V3", "3V3")
           and resistor("R5", 4700, "SCL_3V3", "3V3"),
           "Each low-side signal has its 4.7 kohm pull-up to 3V3, never VBUS.")
    cross_domain_resistors = []
    for ref in components:
        spec = part_spec(ref)
        ends = {net_name(ref, "1"), net_name(ref, "2")}
        if (spec and spec.category == ComponentCategory.RESISTOR
                and ends & {"SDA_3V3", "SCL_3V3"}
                and ends & {"VBUS", "SDA_5V", "SCL_5V", "I2C_BIAS"}):
            cross_domain_resistors.append(ref)
    record("I2C_RESISTIVE_DOMAIN_ISOLATION", not cross_domain_resistors,
           "No resistor bypasses translation or adds a high-voltage pull-up to a low-side signal.")

    cc_ok = True
    for net, usb_pin in (("CC1", "A5"), ("CC2", "B5")):
        rd_refs = [ref for ref in components if resistor(ref, 5100, net, "GND")]
        cc_ok = cc_ok and on("J1", {usb_pin: net}) and len(rd_refs) == 1 and len(pins(net)) == 2
    record("USB_SEPARATE_CC_RD", cc_ok,
           "CC1 and CC2 each retain a separate 5.1 kohm Rd to ground; no current contract inferred.")
    usb_mapping = {pin: "VBUS" for pin in ("A4", "A9", "B4", "B9")}
    usb_mapping.update({pin: "GND" for pin in ("A1", "A12", "B1", "B12")})
    record("USB_POWER_ONLY", bool(components.get("J1")
           and components["J1"].part_id == "USB_C_RECEPTACLE_16P") and on("J1", usb_mapping)
           and all(net_name("J1", pin) is None for pin in ("A6", "A7", "B6", "B7", "A8", "B8")),
           "USB-C carries power only; USB data and SBU pins are not repurposed as I2C.")
    external = [(net.name, net.external_source) for net in circuit.nets if net.external_source]
    source_ok = bool(len(external) == 1 and external[0][0] == "VBUS"
                     and external[0][1].kind == ExternalSourceKind.USB_VBUS
                     and external[0][1].current_limit is None)
    record("USB_CURRENT_NOT_INFERRED", source_ok,
           "Only VBUS is external; its current entitlement remains unspecified, not 2 A.")
    vbus = circuit.net("VBUS")
    voltage = vbus.external_source.voltage if vbus and vbus.external_source else None
    record("BUCK_INPUT_DESIGN_RANGE", bool(voltage and voltage.minimum and voltage.maximum
           and voltage.minimum.value >= 4.75 and voltage.maximum.value <= 5.25),
           "This design assumes 4.75-5.25 V input within IC limits; source behavior is untested.",
           TI_BUCK)

    if include_i2c_extension:
        translator = part_spec("U4")
        names = {p.number: p.name.replace("_", "").upper() for p in translator.pins} if translator else {}
        record("PCA_CATALOG_PINOUT", bool(translator and translator.part_id == "PCA9306DCUT"
               and names == {"1": "GND", "2": "VREF1", "3": "SCL1", "4": "SDA1",
                             "5": "SDA2", "6": "SCL2", "7": "VREF2", "8": "EN"}),
               "PCA9306 DCU physical pin identities match the manufacturer, p4.", TI_TRANSLATOR)
        record("PCA_DOMAIN_PINOUT", on("U4", {
            "1": "GND", "2": "3V3", "3": "SCL_3V3", "4": "SDA_3V3",
            "5": "SDA_5V", "6": "SCL_5V", "7": "I2C_BIAS", "8": "I2C_BIAS"}),
            "Low/high buses are distinct; EN and VREF2 share the dedicated bias node.", TI_TRANSLATOR)
        record("PCA_BIAS_NETWORK", resistor("R14", 200000, "VBUS", "I2C_BIAS")
               and capacitor("C8", 100e-12, "I2C_BIAS") and len(pins("I2C_BIAS")) == 4,
               "A 200 kohm feed biases EN/VREF2 with the selected 100 pF ground bypass.", TI_TRANSLATOR)
        record("HIGH_I2C_PULLUPS", resistor("R8", 4700, "SDA_5V", "VBUS")
               and resistor("R9", 4700, "SCL_5V", "VBUS"),
               "High-side signals each have 4.7 kohm pull-ups to VBUS; timing remains unknown.")
        record("I2C_EXTENSION_HEADER", on("J3", {
            "1": "GND", "2": "VBUS", "3": "SDA_5V", "4": "SCL_5V"}),
            "Dedicated J3 carries ground, VBUS and translated signals; no external power source.")
    else:
        record("NO_UNREQUESTED_I2C_EXTENSION", not ({"U4", "J3", "R8", "R9", "R14", "C8"}
               & set(components)) and not any(circuit.net(n) for n in ("SDA_5V", "SCL_5V", "I2C_BIAS")),
               "The base variant does not silently include an external 5 V bus.")

    unknowns = [
        ("USB_CURRENT_ENTITLEMENT", "No advertised-source-current detection or negotiated contract."),
        ("DYNAMIC_REGULATION", "Switching stability, startup, ripple and ESP32 load steps untested."),
        ("THERMAL_EMC", "Temperature rise, switching-node emissions and radio coupling untested."),
        ("PHYSICAL_LAYOUT", "Net connectivity does not prove placement, routing or antenna clearance."),
        ("PASSIVE_REALIZATION", "Actual resistor tolerances and MLCC bias/temperature capacitance unverified."),
        ("SYSTEM_CURRENT_BUDGET", "Converter 2 A rating is not a verified board or USB current budget."),
        ("SOURCE_REVERIFICATION", "Web/manual source review is not deterministic source relocation."),
    ]
    if include_i2c_extension:
        unknowns.append(("EXTERNAL_I2C_TIMING", "External capacitance, pull-ups, sink current and cable unspecified."))
    failures = sum(finding["status"] == "FAIL" for finding in findings)
    capacitance = sum(part.value.value for part in circuit.components
                      if part.value and part.value.unit == Unit.FARAD
                      and part_spec(part.ref) and part_spec(part.ref).category == ComponentCategory.CAPACITOR
                      and {net_name(part.ref, "1"), net_name(part.ref, "2")} == {"3V3", "GND"})
    return {
        "schema_version": 1,
        "scope": "Authored landing redesign topology and conditional arithmetic only",
        "circuit_content_hash": circuit.content_hash,
        "include_i2c_extension": include_i2c_extension,
        "status": "FAIL" if failures else "SCOPED_CHECKS_PASS_SYSTEM_UNKNOWN",
        "system_status": "UNKNOWN",
        "manufacturing_ready": False,
        "bench_run": False,
        "board_current_capability_A": None,
        "topology_checks": findings,
        "failed_checks": failures,
        "calculations": {
            "feedback": feedback_voltage_bounds(453000, 100000)
            if feedback_ok and buck_topology and integrity else None,
            "nominal_3V3_ground_capacitance_F": capacitance,
            "capacitance_status": "NOMINAL_NETLIST_SUM_NOT_EFFECTIVE_CAPACITANCE",
        },
        "remaining_checks": [{"id": key, "status": "UNKNOWN", "reason": reason}
                             for key, reason in unknowns],
    }
