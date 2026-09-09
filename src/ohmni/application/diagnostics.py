"""A controlled learning exercise, evaluated by the actual electrical verifier."""

from ..catalog import default_catalog
from ..domain import CircuitIR, PinRef
from ..synthesis import SynthesisBrief, synthesize_a1
from ..verifier import verify

CHOICES = (
    ("leave_5v", "Leave both sensor supplies on 5 V"),
    ("move_vdd", "Move only VDD to the 3.3 V rail"),
    ("move_both", "Move VDD and VDDIO to the 3.3 V rail"),
)
LIMITATION = (
    "This is a separate practice circuit checked by electrical rules, not a simulation "
    "or a change to your saved project. Seed catalog limits have not been machine "
    "re-verified against the source PDF. No physical hardware was tested."
)


def sensor_exercise() -> dict:
    return {
        "id": "sensor-rail", "title": "Can you spot the power problem?",
        "prompt": "The sensor's two supply pins, VDD and VDDIO, are connected to USB's 5 V rail. Which change should we check?",
        "prediction_prompt": "Before checking: will the sensor's voltage limits allow this wiring?",
        "component_ref": "U3", "net_names": ["VBUS", "3V3"],
        "choices": [{"id": key, "label": label} for key, label in CHOICES],
        "limitation": LIMITATION,
    }


def _sensor_supply_variant(base: CircuitIR, pins_on_usb: set[str]) -> CircuitIR:
    data = base.model_dump(mode="json")
    for net in data["nets"]:
        net["connections"] = [pin for pin in net["connections"]
                              if not (pin["component"] == "U3" and pin["pin"] in {"6", "8"})]
        if net["name"] in {"VBUS", "3V3"}:
            pins = pins_on_usb if net["name"] == "VBUS" else {"6", "8"} - pins_on_usb
            net["connections"].extend(PinRef(component="U3", pin=pin).model_dump(mode="json")
                                      for pin in sorted(pins))
    return CircuitIR.model_validate(data)


def _snapshot(circuit, report):
    result = next(item for item in report.results if item.rule_id == "PB-PWR-001")
    return {
        "circuit_hash": circuit.content_hash, "rule_id": result.rule_id,
        "outcome": result.outcome.value,
        "findings": [{"severity": finding.severity.value, "title": finding.title,
                      "description": finding.description}
                     for finding in result.findings],
    }


def evaluate_sensor_exercise(choice: str) -> dict:
    if not isinstance(choice, str) or choice not in dict(CHOICES):
        raise ValueError("Choose one of the offered sensor-supply changes")
    catalog = default_catalog()
    synthesis = synthesize_a1(SynthesisBrief(), catalog)
    base = synthesis.circuit
    before = _sensor_supply_variant(base, {"6", "8"})
    remaining = {"leave_5v": {"6", "8"}, "move_vdd": {"6"}, "move_both": set()}[choice]
    after = _sensor_supply_variant(base, remaining)
    first = verify(before, catalog, synthesis.requirements)
    last = verify(after, catalog, synthesis.requirements)
    after_snapshot = _snapshot(after, last)
    correct = after_snapshot["outcome"] == "pass" and not last.export_blocked
    evidence = []
    for rail in catalog.require("BME280").supply_rails:
        for item in rail.evidence:
            evidence.append({"source": item.source_id, "page": item.page,
                             "status": item.status.value,
                             "value": f"{rail.name} operating maximum: {rail.operating.maximum.engineering()}"})
    return {
        "choice": choice, "correct": correct,
        "title": "Both supplies now pass the voltage check" if correct else "The voltage check still finds a problem",
        "explanation": (
            "Both sensor supply pins now connect to the regulated 3.3 V rail. The verifier rechecked the entire practice circuit."
            if correct else
            "At least one sensor supply remains on 5 V. VDD powers the sensor and VDDIO powers its interface; both must respect their own voltage limits."
        ),
        "before": _snapshot(before, first), "after": after_snapshot,
        "evidence": evidence, "limitation": LIMITATION,
    }
