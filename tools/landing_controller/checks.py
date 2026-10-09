"""Pure authored-design contracts. Passing is not a whole-system verification."""
from collections import Counter
from math import isclose

from ohmni.domain.component import ComponentCategory, PinElectricalType, PinRole
from ohmni.domain.units import Unit

from .catalog import MCU_GND, MCU_PIN_NAMES, MCU_VDD, SHIFT_PIN_NAMES
from .design import CAP_VALUES, CONTROL_PINS, HEADER_GPIO_PINS, PULLS, SHIFT_OUTPUT_PINS


def check_design(circuit, catalog):
    parts = {p.ref: p for p in circuit.components}
    findings = []

    def record(name, ok, detail):
        findings.append({"id": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    def net(ref, pin):
        result = circuit.net_of(ref, str(pin))
        return result.name if result else None

    def on(ref, mapping):
        return ref in parts and all(net(ref, pin) == name for pin, name in mapping.items())

    def spec(ref):
        return catalog.get(parts[ref].part_id) if ref in parts else None

    def passive(ref, value, unit, a, b):
        part = parts.get(ref)
        category = ComponentCategory.RESISTOR if unit == Unit.OHM else ComponentCategory.CAPACITOR
        return bool(part and spec(ref) and spec(ref).category == category and part.value
                    and part.value.unit == unit and isclose(part.value.value, value, rel_tol=1e-12)
                    and {net(ref, 1), net(ref, 2)} == {a, b})

    members = Counter((pin.component, pin.pin) for node in circuit.nets for pin in node.connections)
    record("PIN_MEMBERSHIP", all(count == 1 for count in members.values())
           and all(spec(ref) and spec(ref).pin(pin) for ref, pin in members),
           "Every connected pin exists in its catalog and has a unique net.")
    record("REAL_PART_REALIZATION", all(spec(ref) and spec(ref).mpn and not spec(ref).is_generic
           and not part.placeholder for ref, part in parts.items()),
           "Every electronic instance resolves to a manufacturer part number; no decorative IC or generic placeholder.")
    record("MCU_PINOUT", bool(spec("U1") and spec("U1").mpn == "STM32F103VBT6"
           and {int(p.number): p.name for p in spec("U1").pins} == MCU_PIN_NAMES),
           "All 100 LQFP pin identities match ST DS5319 Rev20 Figure4/Table5, including NC73.")
    record("MCU_SUPPLY_PINS", on("U1", {**{p: "3V3" for p in (*MCU_VDD, 6, 21, 22)},
                                       **{p: "GND" for p in MCU_GND}}),
           "Five VDD pairs, VBAT, VDDA, VREF+/- and VSSA must all be connected.")
    record("MCU_CONTROL_ASSIGNMENTS", on("U1", {pin: name for name, pin in CONTROL_PINS.items()}),
           "SPI1, reset/boot, SWD and discrete register controls use the selected physical pins.")
    record("MCU_NC_AND_INTERNAL_CLOCK", all(net("U1", pin) is None for pin in (12, 13, 73)),
           "Manufacturer NC73 and unused oscillator pins remain disconnected; HSI-only design.")
    record("DECOUPLING_AND_RESET_CAPS", all(passive(ref, value, Unit.FARAD,
           "VBUS" if ref == "C1" else "NRST" if ref == "C12" else "3V3", "GND")
           for ref, value in CAP_VALUES.items()),
           "15 specified capacitors: all five local digital bypasses, bulk, analog, VBAT, reset, LDO and support ICs. Placement is a separate check.")
    record("BOOT_AND_IDLE_PULLS", all(passive(ref, 10000, Unit.OHM, a, b)
                                      for ref, (a, b) in PULLS.items()),
           "Boot pins low; EEPROM CS and indicator OE high; all discrete logic controls have a defined idle level.")
    record("LDO_PINOUT", bool(spec("U2") and spec("U2").mpn == "AP2112K-3.3TRG1")
           and on("U2", {1: "VBUS", 2: "GND", 3: "VBUS", 5: "3V3"}) and net("U2", 4) is None,
           "VIN/EN on VBUS, GND grounded, VOUT=3V3 net; physical NC4 left open.")
    record("EEPROM_SPI", bool(spec("U3") and spec("U3").mpn == "25LC256-I/SN")
           and on("U3", {1: "EEPROM_CS", 2: "SPI_MISO", 3: "3V3", 4: "GND",
                         5: "SPI_MOSI", 6: "SPI_SCK", 7: "3V3", 8: "3V3"}),
           "EEPROM CS/MISO/MOSI/clock and inactive-high WP/HOLD match Microchip DS20001822H.")
    for ref in ("U4", "U5"):
        record(f"{ref}_SHIFT_PINOUT", bool(spec(ref) and spec(ref).mpn == "SN74HC595D"
               and {int(p.number): p.name for p in spec(ref).pins} == SHIFT_PIN_NAMES),
               "SOIC16 pin identities match TI SCLS041J p3; QA is pin15.")
        record(f"{ref}_SHIFT_CONTROLS", on(ref, {8: "GND", 16: "3V3", 10: "SR_CLR",
                                               11: "SR_CLK", 12: "SR_LATCH", 13: "SR_OE"}),
               "Shared clock/latch/clear/OE, supplies and ground.")
    record("SHIFT_CASCADE", on("U4", {14: "SR_DATA", 9: "SR_CHAIN"})
           and on("U5", {14: "SR_CHAIN"}) and net("U5", 9) is None,
           "Serial carry uses QH prime pin9, never parallel QH pin7; final carry is intentionally NC.")
    for index in range(16):
        ref, resistor, driver = f"D{index+1}", f"R{20+index}", "U4" if index < 8 else "U5"
        output, anode = f"LED{index}_DRIVE", f"LED{index}_ANODE"
        led = spec(ref)
        correct_polarity = bool(led and led.mpn == "APT1608SGC" and led.pin("1")
                               and PinRole.CATHODE in led.pin("1").roles and led.pin("2")
                               and PinRole.ANODE in led.pin("2").roles
                               and led.packages[0].pad_for_pin("1") == "1"
                               and led.packages[0].pad_for_pin("2") == "2")
        record(f"LED_{index}_CHANNEL", correct_polarity and on(ref, {1: "GND", 2: anode})
               and passive(resistor, 1000, Unit.OHM, output, anode)
               and net(driver, SHIFT_OUTPUT_PINS[index % 8]) == output,
               "Independent 1 kohm series resistor; actual LED cathode is physical pad1 at ground.")
    gpio_ok = all(net("U1", pin) == net("J2", index) == f"GPIO_{MCU_PIN_NAMES[pin]}"
                  for index, pin in enumerate(HEADER_GPIO_PINS, 3))
    record("HEADER_36_GPIO", gpio_ok and len(set(HEADER_GPIO_PINS)) == 36
           and on("J2", {1: "GND", 2: "GND", 39: "3V3", 40: "3V3"}),
           "36 independently connected GPIO contacts plus two grounds and two 3V3 outputs. This is a custom header.")
    record("SWD_AND_BUTTONS", on("J3", {1: "3V3", 2: "SWDIO", 3: "GND", 4: "SWCLK", 5: "NRST", 6: "GND"})
           and on("SW1", {1: "NRST", 2: "GND"}) and on("SW2", {1: "USER", 2: "GND"}),
           "Custom six-contact SWD reference-only power, reset and user button paths.")
    record("USB_CC", on("J1", {"A5": "CC1", "B5": "CC2"})
           and passive("R1", 5100, Unit.OHM, "CC1", "GND")
           and passive("R2", 5100, Unit.OHM, "CC2", "GND"),
           "Independent 5.1 kohm Rd resistors; no detected current advertisement.")
    record("USB_POWER_ONLY", on("J1", {**{p: "VBUS" for p in ("A4", "A9", "B4", "B9")},
                                       **{p: "GND" for p in ("A1", "A12", "B1", "B12")}})
           and all(net("J1", p) is None for p in ("A6", "A7", "B6", "B7", "A8", "B8")),
           "USB data and SBU pins remain unconnected; the connector is a power input.")
    external = [node for node in circuit.nets if node.external_source]
    record("NO_FABRICATED_POWER_SOURCE", len(external) == 1 and external[0].name == "VBUS"
           and external[0].external_source.current_limit is None,
           "3V3 is produced by the LDO, never a fabricated external source or USB current contract.")
    record("NO_CONNECTED_NC", all(spec(ref).pin(pin).electrical_type != PinElectricalType.NO_CONNECT
                                   for ref, pin in members if spec(ref) and spec(ref).pin(pin)),
           "No manufacturer's NC terminal has been wired.")
    unused = {ref: [p.number for p in spec(ref).pins if not net(ref, p.number)]
              for ref in parts if spec(ref)}
    failures = sum(f["status"] == "FAIL" for f in findings)
    return {"schema_version": 1, "scope": "Authored controller connectivity and realization only",
            "circuit_content_hash": circuit.content_hash, "status": "FAIL" if failures else "SCOPED_CHECKS_PASS_SYSTEM_UNKNOWN",
            "system_status": "UNKNOWN", "manufacturing_ready": False, "bench_run": False,
            "topology_checks": findings, "failed_checks": failures,
            "unconnected_catalog_pins": {ref: pins for ref, pins in unused.items() if pins},
            "calculations": {"led_current_upper_bound_A": 3.6 / 990,
                             "eight_channel_upper_bound_A": 8 * 3.6 / 990,
                             "status": "CONDITIONAL_OHMS_LAW_BOUND",
                             "assumptions": "3.6 V maximum design rail; 1% 1k resistors; nonnegative LED/drop voltage. Not a 3.3V output-drive guarantee or brightness prediction."},
            "remaining_checks": [{"id": key, "status": "UNKNOWN", "reason": reason} for key, reason in (
                ("FIRMWARE", "HSI clock setup, safe OE initialization, SPI timing, EEPROM programming and GPIO states untested."),
                ("POWER_CURRENT", "USB current entitlement and external-header loads are unknown."),
                ("DYNAMIC_THERMAL", "Effective capacitance, LDO startup/stability, transient and temperature rise require verification."),
                ("INDICATOR_DRIVE", "LED minimum Vf and 3.3V loaded HC595 output levels/brightness are not guaranteed by this calculation."),
                ("PHYSICAL_RELEASE", "Routing, mechanical fit, ESD, EMC and manufacturing review are separate; no release authorized."),
                ("SOURCE_RELOCATION", "Manufacturer sources manually reviewed; deterministic evidence re-verification not performed."))]}
