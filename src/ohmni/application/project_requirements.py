"""Requirement outcomes from saved choices, circuit facts, and verifier reports.

MET describes the stated, narrow configuration or check. It does not promote
static wiring into firmware behavior, a cost estimate, or a hardware result.
"""

import re

from ..domain import ComponentCategory, Interface, Quantity
from ..verifier.context import VerificationContext
from .product import build_brief


def project_requirement_results(brief,compiled,circuit,semantic,board,catalog):
    if semantic.circuit_content_hash!=circuit.content_hash:
        raise ValueError("Requirement results must use verification of the same circuit")
    preview=build_brief(compiled)
    lines=[*preview.asked_for,*preview.assumed,*preview.needs_clarification]
    labels={line.field:line.label for line in lines}
    display_values={line.field:line.value for line in lines if line.field!="assumption"}
    rules={result.rule_id:result for result in semantic.results}
    sensors=[part for part in circuit.components if part.selected_i2c_address is not None]
    memories=[part for part in circuit.components if Interface.SPI in part.selected_interfaces
              and catalog.require(part.part_id).category is ComponentCategory.MEMORY]
    leds=[part for part in circuit.components if catalog.require(part.part_id).category is ComponentCategory.LED]
    buttons=[part for part in circuit.components if catalog.require(part.part_id).category is ComponentCategory.SWITCH]
    headers=[part for part in circuit.components if part.part_id=="HEADER_1X6_254"]
    context=VerificationContext(circuit,catalog,compiled.requirements)

    def checked(rule_ids,detail):
        results=[rules.get(rule_id) for rule_id in rule_ids]
        if any(result is not None and result.outcome.value=="fail" for result in results):
            return "VIOLATED",detail+" A relevant deterministic rule reported a violation.",list(rule_ids)
        if any(result is None or result.outcome.value!="pass" for result in results):
            return "UNKNOWN",detail+" The required checks did not establish a pass.",list(rule_ids)
        return "MET",detail+" These checks describe static circuitry, not hardware operation.",list(rule_ids)

    def configured(matches,detail):
        return ("MET" if matches else "VIOLATED"),detail,[]

    def outcome(statement):
        field=statement.field
        if field=="project_name":
            return configured(compiled.requirements.project_name==brief.project_name,"The confirmed project name is retained.")
        if field=="archetype":
            return "UNKNOWN","The family names the chosen compiler; detailed hardware choices are checked separately.",[]
        if field=="description":
            return "UNKNOWN","Your description is retained verbatim. Free text is not interpreted into additional hardware capabilities.",[]
        if field=="input_power":
            return checked(("PB-USB-001",),"USB-C power-sink termination was checked; USB data and Power Delivery are not supplied.")
        if field in {"input_voltage_v","logic_voltage_v"}:
            name,value=("VBUS",brief.input_voltage_v) if field=="input_voltage_v" else ("3V3",brief.logic_voltage_v)
            voltage=context.net_voltage(name).voltage
            if voltage is None:return "UNKNOWN",f"The {name} voltage could not be derived from its source.",["PB-PWR-001"]
            if not voltage.contains(Quantity.volts(value)):
                return "VIOLATED",f"The modeled {name} source range does not include the requested voltage.",["PB-PWR-001"]
            return checked(("PB-PWR-001",),f"The modeled {name} source range includes {value:g} V; no voltage has been measured.")
        if field=="mcu_part_id":
            parts=[part for part in circuit.components if catalog.require(part.part_id).category
                   in {ComponentCategory.MCU,ComponentCategory.MCU_MODULE}]
            return configured(len(parts)==1 and parts[0].part_id==brief.mcu_part_id,
                              "The circuit inventory contains the requested processor; firmware execution is unverified.")
        if field in {"sensor_count","status_led_count","button_count","spi_count"}:
            actual,wanted={"sensor_count":(len(sensors),len(brief.sensors)),
                           "status_led_count":(len(leds),brief.status_led_count),
                           "button_count":(len(buttons),brief.button_count),
                           "spi_count":(len(memories),len(brief.spi_devices))}[field]
            return configured(actual==wanted,f"Circuit inventory: {actual} requested-type component(s); expected {wanted}. Runtime behavior is unverified.")
        if match:=re.fullmatch(r"sensors\.(\d+)\.(part_id|address)",field):
            index=int(match[1])
            if index>=len(sensors):return "VIOLATED","The requested sensor instance is absent.",[]
            part=sensors[index];slot=brief.sensors[index]
            if match[2]=="part_id":
                return configured(part.part_id==slot.part_id,f"{part.ref} uses {part.part_id}; obtaining readings needs firmware and hardware testing.")
            if slot.address is not None and part.selected_i2c_address!=slot.address:
                return "VIOLATED","The circuit address differs from the requested sensor address.",["PB-I2C-003"]
            return checked(("PB-I2C-003",),f"{part.ref} is wired for address 0x{part.selected_i2c_address:02X}; address uniqueness and straps were checked.")
        if match:=re.fullmatch(r"spi_devices\.(\d+)\.part_id",field):
            index=int(match[1])
            if index>=len(memories) or memories[index].part_id!=brief.spi_devices[index].part_id:
                return "VIOLATED","The requested SPI device is absent from this slot.",[]
            return checked(("PB-SPI-001",),f"{memories[index].ref} has the requested memory and statically checked SPI wiring; reads and writes are unverified.")
        if field=="include_programming_header":
            if bool(headers)!=brief.include_programming_header:
                return "VIOLATED","The programming connector differs from the saved choice.",[]
            if not headers:return "MET","The programming header is omitted as requested; no supplied programming connector remains.",[]
            return checked(("PB-UART-001",),"A serial programming header is included; an external 3.3 V adapter and orientation review are required.")
        if field=="max_board_layers":
            return configured(board.layer_count<=brief.max_board_layers,
                              f"The generated board has {board.layer_count} copper layers against a limit of {brief.max_board_layers}.")
        if field=="hand_solderable_preferred":
            if not brief.hand_solderable_preferred:return "MET","Hand-solderability was not required; package assembly risks still apply.",[]
            return checked(("PB-ID-005",),"Catalog package suitability was checked against the hand-soldering preference.")
        if field=="budget_usd":
            return "UNKNOWN","Prices are synthetic; fabrication, delivery, tools, and total build cost are unknown. The budget is not verified.",[]
        if field=="safety_domains":
            return "UNKNOWN","No supported safety qualification is claimed; the saved declarations are not a safety assessment.",[]
        return "UNKNOWN","This is an explicit assumption or limitation, not an established hardware result.",[]

    rows=[]
    for statement in compiled.provenance:
        status,detail,rule_ids=outcome(statement)
        rows.append({**statement.model_dump(mode="json"),"label":labels.get(statement.field,statement.field),
                     "display_value":display_values.get(statement.field,statement.value),
                     "status":status,"detail":detail,"rule_ids":rule_ids,
                     "circuit_hash":circuit.content_hash,
                     "finding_ids":[finding.finding_id for rule_id in rule_ids for finding in rules.get(rule_id).findings]
                     if all(rule_id in rules for rule_id in rule_ids) else []})
    return rows
