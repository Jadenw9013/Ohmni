"""Human-readable names for engineering identifiers.

Reference designators, net names and category enums are the authoritative way
Ohmni talks to itself. They are a poor way to talk to someone building their
first board. This module derives a readable name for each one and keeps the
identifier beside it, so the interface can lead with the concept and disclose
the identifier.

Nothing here renames anything. `CircuitIR`, the catalog and every report keep
their identifiers unchanged; a `Term` is a presentation pair.

Every name is **derived from authoritative metadata** -- part category, the
regulator's own datasheet output voltage, a net's declared external source, the
pin names the part publishes, and the functional grouping already derived from
topology. There is deliberately no table keyed on this project's identifiers,
because such a table would silently mislabel the next project.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..domain.circuit import CircuitIR, NetKind
from ..domain.component import ComponentCategory

#: Standard bus pin names, and what a wire carrying them does. These are an
#: industry vocabulary published by parts themselves, not identifiers from this
#: project, so they generalise.
_BUS_PINS: dict[str, tuple[str, str | None]] = {
    "SDA": ("data line", "bus"), "SDI": ("data line", "bus"),
    "SCL": ("clock line", "bus"), "SCK": ("clock line", "bus"),
    "MOSI": ("data line", "bus"), "MISO": ("data line", "bus"),
    "TXD": ("serial line", "serial"), "TX": ("serial line", "serial"),
    "RXD": ("serial line", "serial"), "RX": ("serial line", "serial"),
    "EN": ("enable line", None),
}

_SOURCE_WORDS: dict[str, str] = {
    "usb_vbus": "USB",
    "dc_jack": "a DC jack",
    "battery": "a battery",
    "bench_supply": "a bench supply",
    "header_feed": "a header",
}

class Term(BaseModel):
    """A readable name and the identifier it stands for.

    `human` leads. `technical` is what the engineering layer calls it and is
    always carried, so progressive disclosure never loses the real name.
    """

    human: str
    technical: str
    detail: str | None = None

    def __str__(self) -> str:
        return self.human


def phrase(term: Term | str) -> str:
    """A term as it should read mid-sentence.

    Only an ordinary leading word is lowercased. "5 V from USB" and "USB power
    connector" keep their units and acronyms; "Sensor" becomes "sensor".
    """
    text = term.human if isinstance(term, Term) else str(term)
    if len(text) > 1 and text[0].isupper() and text[1].islower():
        return text[0].lower() + text[1:]
    return text


def _format_volts(value: float | None) -> str | None:
    return None if value is None else f"{value:g} V"


def net_driver_voltage(circuit: CircuitIR, catalog, net_name: str) -> float | None:
    """The voltage a net sits at, taken from whatever drives it.

    Mirrors the verifier's own derivation order rather than reading a label: a
    declared external source, else a regulator's datasheet output voltage.
    """
    net = circuit.net(net_name)
    if net is None:
        return None
    if net.external_source is not None:
        nominal = net.external_source.voltage.nominal
        return nominal.value if nominal else None
    for pin in net.connections:
        instance = circuit.component(pin.component)
        spec = catalog.get(instance.part_id) if instance else None
        if spec is None or spec.regulator is None:
            continue
        pin_spec = spec.pin(pin.pin)
        if pin_spec is not None and pin_spec.electrical_type.value == "power_out":
            nominal = spec.regulator.output_voltage.nominal
            return nominal.value if nominal else None
    return None


def _category(circuit: CircuitIR, catalog, ref: str) -> ComponentCategory | None:
    instance = circuit.component(ref)
    if instance is None:
        return None
    spec = catalog.get(instance.part_id)
    return spec.category if spec else None


def _private_partners(circuit: CircuitIR, catalog, ref: str) -> set[ComponentCategory]:
    """Categories reachable through a net small enough to be a private link."""
    partners: set[ComponentCategory] = set()
    for net in circuit.nets:
        if ref not in net.components() or len(net.connections) > 3:
            continue
        for pin in net.connections:
            if pin.component == ref:
                continue
            category = _category(circuit, catalog, pin.component)
            if category is not None:
                partners.add(category)
    return partners


def bus_role(pin_name: str) -> tuple[str, str | None] | None:
    """The documented role of a pin, matched by prefix.

    Parts publish pins as `TXD0`, `RXD0`, `IO21`. The role lives in the prefix,
    so an exact lookup would miss every numbered variant.
    """
    upper = pin_name.upper()
    if upper in _BUS_PINS:
        return _BUS_PINS[upper]
    for key, role in _BUS_PINS.items():
        if upper.startswith(key) and upper[len(key):].isdigit():
            return role
    return None


def component_term(circuit: CircuitIR, catalog, ref: str) -> Term:
    """Name one component by what it does on this board."""
    instance = circuit.component(ref)
    spec = catalog.get(instance.part_id) if instance else None
    if instance is None or spec is None:
        return Term(human=ref, technical=ref)

    technical = f"{instance.part_id} · {ref}"
    detail = spec.description or None
    category = spec.category
    nets = [net for net in circuit.nets if ref in net.components()]
    kinds = {net.kind for net in nets}
    value = instance.value.engineering() if instance.value else ""

    def term(human: str) -> Term:
        return Term(human=human, technical=technical, detail=detail)

    if category in {ComponentCategory.MCU, ComponentCategory.MCU_MODULE}:
        return term("Main computer")
    if category is ComponentCategory.SENSOR:
        return term("Sensor")
    if category is ComponentCategory.MEMORY:
        return term("Memory chip")
    if category in {ComponentCategory.REGULATOR_LINEAR, ComponentCategory.REGULATOR_SWITCHING}:
        output = spec.regulator.output_voltage.nominal if spec.regulator else None
        volts = _format_volts(output.value) if output else None
        return term(f"{volts} voltage regulator" if volts else "Voltage regulator")
    if category is ComponentCategory.CONNECTOR:
        for net in nets:
            if net.external_source is not None:
                source = _SOURCE_WORDS.get(net.external_source.kind.value, "External")
                return term(f"{source} power connector")
        return term("Connector")
    if category is ComponentCategory.HEADER:
        # A header is a programming header when it reaches the processor's
        # serial pins -- a fact about this board, not about the part.
        for net in nets:
            for pin in net.connections:
                other = circuit.component(pin.component)
                other_spec = catalog.get(other.part_id) if other else None
                if other_spec is None:
                    continue
                if other_spec.category not in {ComponentCategory.MCU, ComponentCategory.MCU_MODULE}:
                    continue
                pin_spec = other_spec.pin(pin.pin)
                role = bus_role(pin_spec.name) if pin_spec else None
                if role and role[1] == "serial":
                    return term("Programming header")
        return term("Connector header")
    if category is ComponentCategory.LED:
        return term("Indicator light")
    if category is ComponentCategory.SWITCH:
        return term("Button")
    if category is ComponentCategory.CAPACITOR:
        if NetKind.POWER in kinds and NetKind.GROUND in kinds:
            return term(f"{value} power smoothing capacitor".strip())
        return term(f"{value} timing capacitor".strip())
    if category is ComponentCategory.RESISTOR:
        partners = _private_partners(circuit, catalog, ref)
        if ComponentCategory.LED in partners:
            return term(f"{value} current-limiting resistor".strip())
        if ComponentCategory.CONNECTOR in partners:
            return term(f"{value} connector configuration resistor".strip())
        if NetKind.POWER in kinds and any(net.kind is NetKind.SIGNAL for net in nets):
            return term(f"{value} pull-up resistor".strip())
        return term(f"{value} resistor".strip())
    return term(category.value.replace("_", " ").capitalize())


def net_term(circuit: CircuitIR, catalog, name: str,
             systems_by_ref: dict[str, str] | None = None) -> Term:
    """Name one net by what it carries."""
    net = circuit.net(name)
    if net is None:
        return Term(human=name, technical=name)

    def term(human: str, detail: str | None = None) -> Term:
        return Term(human=human, technical=name, detail=detail)

    if net.kind is NetKind.GROUND:
        return term("Ground", "The common return path every part connects to.")

    volts = _format_volts(net_driver_voltage(circuit, catalog, name))
    if net.kind is NetKind.POWER:
        if net.external_source is not None:
            source = _SOURCE_WORDS.get(net.external_source.kind.value, "an external supply")
            return term(f"{volts or 'Power'} from {source}")
        return term(f"{volts} power" if volts else "A power rail")

    # A signal net is named from the peripheral side where possible: a sensor's
    # SDA pin is SDA in silicon, whereas a processor pin is only a bus pin
    # because firmware says so. This is the verifier's own reasoning.
    best: tuple[str, str | None, ComponentCategory] | None = None
    for pin in net.connections:
        instance = circuit.component(pin.component)
        spec = catalog.get(instance.part_id) if instance else None
        if spec is None:
            continue
        pin_spec = spec.pin(pin.pin)
        if pin_spec is None:
            continue
        role = bus_role(pin_spec.name)
        if role is None:
            continue
        peripheral = spec.category not in {ComponentCategory.MCU, ComponentCategory.MCU_MODULE}
        if best is None or (peripheral and best[2] in {ComponentCategory.MCU, ComponentCategory.MCU_MODULE}):
            best = (role[0], role[1], spec.category)
    if best is not None:
        label, kind, category = best
        if category is ComponentCategory.SENSOR:
            return term(f"Sensor {label}")
        if kind == "serial":
            return term("Programming connection")
        return term(label.capitalize())

    categories = {c for c in (_category(circuit, catalog, pin.component)
                             for pin in net.connections) if c is not None}
    if ComponentCategory.LED in categories:
        return term("Indicator connection")
    if ComponentCategory.HEADER in categories:
        return term("Programming connection")
    if ComponentCategory.CONNECTOR in categories:
        return term("Connector configuration line")
    # Fall back to the functional system this net lives in, which is itself
    # derived from topology rather than from the net's name.
    if systems_by_ref:
        systems = {systems_by_ref[ref] for ref in net.components() if ref in systems_by_ref}
        non_compute = systems - {"compute"}
        if len(non_compute) == 1:
            only = next(iter(non_compute))
            if only == "io":
                return term("Indicator connection")
            if only == "sense":
                return term("Sensor connection")
    return term("Signal connection")


def net_terms(circuit: CircuitIR, catalog, names, systems_by_ref=None) -> list[Term]:
    return [net_term(circuit, catalog, name, systems_by_ref) for name in names]


def humanise_refs(circuit: CircuitIR, catalog, refs) -> str:
    """A readable list of components, for prose."""
    names = [phrase(component_term(circuit, catalog, ref)) for ref in refs]
    unique: list[str] = []
    for name in names:
        if name not in unique:
            unique.append(name)
    if not unique:
        return "nothing"
    if len(unique) == 1:
        return unique[0]
    return ", ".join(unique[:-1]) + " and " + unique[-1]
