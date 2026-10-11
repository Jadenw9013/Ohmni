"""SPICE netlist export and operating-point simulation.

Two external tools sit behind this module, and one rule governs both: *a
simulation that did not run is never a simulation that passed.* Every path that
cannot produce a real operating point returns a status saying so -- UNAVAILABLE,
FAILED or TIMED_OUT -- and an empty :class:`OperatingPoint` is never presented as
a result. That is the same reason :class:`~ohmni.adapters.fakes.UnavailableSpice`
exists: a run with no violations and a run that never happened must not look
alike to a caller (VERIFICATION.md, AGENTS.md).

Two further honesties are built in rather than documented and forgotten.

* **Fidelity is read off the deck, never assumed.** ``model_fidelity`` is derived
  from what the netlist actually contains. This module never reports
  ``vendor_model``, because it never attaches a vendor model: KiCad exports our
  generated schematic with passive values and bare references for everything
  else, so an operating point here describes ideal components unless the deck
  itself carries ``.model``/``.subckt`` definitions (PRE_IMPLEMENTATION_REVIEW
  6.2).
* **Corroboration, not verdict.** Nothing here decides whether a design passes.
  The deterministic verifier already stands on its own; a SPICE result is an
  extra observation recorded beside it, exactly as KiCad ERC is.

Processes are spawned only through :func:`~ohmni.adapters.process.run_tool`:
fixed argument vectors, no shell, bounded waiting (SECURITY.md).
"""

from __future__ import annotations

import hashlib
import math
import re
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel

from ..adapters import (
    OperatingPoint,
    SimulationRun,
    ToolAvailability,
    ToolStatus,
    TransientData,
    TransientSeries,
)
from ..adapters.process import ToolTimeoutError, describe_exit, run_tool
from ..adapters.tools import NgspiceCli, find_kicad_cli, find_ngspice
from ..domain.evidence import Evidence, EvidenceKind
from ..domain.units import Quantity, Unit, parse_quantity
from .models import SchematicArtifact

#: The one analysis this module runs. Named on every result so a reader never
#: has to infer which question the numbers answer.
OPERATING_POINT = "op"

#: Fidelity vocabulary from the SimulationRun contract. `vendor_model` is
#: deliberately absent: this module has no path that could earn it.
IDEAL_COMPONENTS = "ideal_components"
BEHAVIOURAL_APPROXIMATION = "behavioural_approximation"

NGSPICE_TIMEOUT_SECONDS = 60
NETLIST_TIMEOUT_SECONDS = 60

#: How much captured tool output is repeated into a report. Enough to debug a
#: deck; never the whole of a runaway log.
_MAX_DETAIL_CHARS = 600
_MAX_ERROR_LINES = 6

_NGSPICE_MISSING = (
    "ngspice was not found, so no operating point was computed. This is not a "
    "pass: the simulation subsystem stays UNSUPPORTED until a standalone "
    "ngspice executable is on PATH."
)

_NUMBER = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
#: `v(3v3) = 3.3`, `I(V1)=-1.0e-03`, with or without the equals sign.
_MARKED_VALUE = re.compile(
    rf"^(?P<kind>[vi])\s*\(\s*(?P<name>[^)\s]+)\s*\)\s*(?:=\s*)?(?P<value>{_NUMBER})$",
    re.IGNORECASE,
)
#: ngspice names a source's branch current `v1#branch`.
_BRANCH_VALUE = re.compile(
    rf"^(?P<name>\S+?)#branch\s*(?:=\s*)?(?P<value>{_NUMBER})$", re.IGNORECASE
)
#: Headers of the two tables `.op` prints in batch mode. Rows under them carry
#: bare names, so they are read only inside a table a header opened -- guessing
#: at bare `name value` lines anywhere would turn `TEMP 27.0` into a voltage.
_NODE_TABLE = re.compile(r"^node\s+voltage$", re.IGNORECASE)
_SOURCE_TABLE = re.compile(r"^source\s+current$", re.IGNORECASE)
_TABLE_ROW = re.compile(rf"^(?P<name>\S+)\s+(?P<value>{_NUMBER})$")
_RULE_LINE = re.compile(r"^[-\s]+$")
_ERROR_LINE = re.compile(r"^\s*\**\s*(?:error|fatal|aborted|can't|cannot)\b", re.IGNORECASE)

#: A deck carrying its own device models is a behavioural approximation at best;
#: one without them is ideal components. Neither is a vendor model.
_MODEL_DIRECTIVE = re.compile(r"^\s*\.(?:model|subckt|include|lib)\b", re.IGNORECASE)
#: An independent source is what makes an operating point meaningful at all.
_SOURCE_ELEMENT = re.compile(r"^\s*[vi][^\s]*\s+\S+\s+\S+", re.IGNORECASE)


def _not_run(run_id: str, status: ToolStatus, fidelity: str, detail: str,
             netlist_path: str | None = None,
             analysis: str = OPERATING_POINT) -> SimulationRun:
    """Every unhappy path lands here, and none of them carries a result."""
    return SimulationRun(
        status=status, run_id=run_id, analysis=analysis,
        model_fidelity=fidelity, operating_point=None, transient_data=None,
        netlist_path=netlist_path, detail=detail,
    )


def _clip(text: str | None, limit: int = _MAX_DETAIL_CHARS) -> str:
    value = " ".join((text or "").split())
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _error_summary(*captured: str) -> str:
    """The tool's own complaints, deduplicated and bounded."""
    lines: list[str] = []
    for text in captured:
        for raw in (text or "").splitlines():
            line = raw.strip()
            if line and _ERROR_LINE.match(line) and line not in lines:
                lines.append(line)
    return _clip("; ".join(lines[:_MAX_ERROR_LINES]))


def model_fidelity(netlist: str) -> str:
    """What a run of this deck could honestly claim, before it is run."""
    for line in (netlist or "").splitlines():
        if _MODEL_DIRECTIVE.match(line):
            return BEHAVIOURAL_APPROXIMATION
    return IDEAL_COMPONENTS


def has_independent_source(netlist: str) -> bool:
    """Whether anything in this deck drives it.

    A transient of a circuit with no source is a flat line at zero volts, which
    is a picture of nothing. It is also the state of every netlist KiCad exports
    from an Ohmni schematic today, so this is the check that keeps the pipeline
    from spending a simulation to draw one.
    """
    for raw in (netlist or "").splitlines():
        line = raw.strip()
        if line and not line.startswith((".", "*")) and _SOURCE_ELEMENT.match(line):
            return True
    return False


def describe_netlist(netlist: str) -> str:
    """State the two facts that decide whether an operating point means anything."""
    lines = [line.strip() for line in (netlist or "").splitlines() if line.strip()]
    elements = [line for line in lines if not line.startswith((".", "*"))]
    has_source = has_independent_source(netlist)
    return (
        f"{len(elements)} element line(s); "
        f"device models: {'present' if model_fidelity(netlist) == BEHAVIOURAL_APPROXIMATION else 'none'}; "
        f"independent source: {'present' if has_source else 'none'}"
    )


def parse_operating_point(stdout: str) -> OperatingPoint:
    """Read node voltages and branch currents out of ngspice batch output.

    Deliberately conservative. Only values the output itself marks as a voltage
    or a current are read -- ``v(...)``/``i(...)``, a ``#branch`` name, or a row
    inside a table whose header said which it is. Anything else is left alone,
    because a parser that guesses turns an unrelated number into an electrical
    claim, and an invented volt is worse than a missing one.
    """
    voltages: dict[str, Quantity] = {}
    currents: dict[str, Quantity] = {}
    table: str | None = None
    for raw in (stdout or "").splitlines():
        line = raw.strip()
        if not line:
            table = None
            continue
        if _NODE_TABLE.match(line):
            table = "voltage"
            continue
        if _SOURCE_TABLE.match(line):
            table = "current"
            continue
        if _RULE_LINE.match(line):
            continue
        if marked := _MARKED_VALUE.match(line):
            target = voltages if marked["kind"].lower() == "v" else currents
            target[marked["name"].lower()] = _quantity(marked["kind"], marked["value"])
            continue
        if branch := _BRANCH_VALUE.match(line):
            currents[branch["name"].lower()] = Quantity.amps(float(branch["value"]))
            continue
        if table and (row := _TABLE_ROW.match(line)):
            name, value = row["name"].lower(), float(row["value"])
            if table == "voltage":
                voltages[name] = Quantity.volts(value)
            else:
                currents[name.removesuffix("#branch")] = Quantity.amps(value)
            continue
        table = None
    return OperatingPoint(node_voltages=voltages, branch_currents=currents)


def _quantity(kind: str, value: str) -> Quantity:
    return Quantity.volts(float(value)) if kind.lower() == "v" else Quantity.amps(float(value))


def operating_point_deck(netlist: str) -> str:
    """Add the operating-point commands a batch run needs, and nothing else.

    The caller's deck is otherwise untouched: its first line stays first,
    because a SPICE deck's first line is its title, and existing commands are
    never duplicated. ``.option`` is not ``.op``, and ``.ends`` is not ``.end``.
    """
    lines = (netlist or "").splitlines()
    stripped = [line.strip() for line in lines]
    additions = [
        directive
        for directive, present in (
            (".op", any(re.match(r"\.op(?:\s|$)", line, re.IGNORECASE) for line in stripped)),
            (".print op", any(re.match(r"\.print\s+op\b", line, re.IGNORECASE) for line in stripped)),
        )
        if not present
    ]
    end = next(
        (index for index in range(len(stripped) - 1, -1, -1)
         if re.fullmatch(r"\.end", stripped[index], re.IGNORECASE)),
        None,
    )
    if end is None:
        return "\n".join([*lines, *additions, ".end"]) + "\n"
    return "\n".join([*lines[:end], *additions, *lines[end:]]) + "\n"


#: The transient a pipeline run asks for: a millisecond at ten-microsecond
#: steps, which is long enough to show a supply settling and short enough that
#: nothing here becomes a long-running job.
DEFAULT_TSTEP = "10us"
DEFAULT_TSTOP = "1ms"

#: A transient can emit far more rows than belong in a report that is stored in
#: a database row and sent to a browser. Beyond this the result is thinned by
#: taking every nth row, and the original count is recorded.
MAX_TRANSIENT_SAMPLES = 400
#: Printing every node of a large netlist is a wide table nobody reads. The
#: signals are taken in the order the netlist introduces them.
MAX_TRANSIENT_SIGNALS = 12
#: Extra terminal voltages and probe currents a transient run may print for rating checks.
MAX_RATING_SIGNALS = 96

#: `Index time v(a) v(b)` and the rule beneath it, as ngspice pages its output.
_TRANSIENT_HEADER = re.compile(r"^index\s+time\b", re.IGNORECASE)
_DEVICE_NODE_COUNT = {"r": 2, "c": 2, "l": 2, "d": 2, "v": 2, "i": 2, "q": 3, "j": 3, "m": 4}
_GROUND_NODES = {"0", "gnd", "gnd!"}


def netlist_nodes(netlist: str, limit: int = MAX_TRANSIENT_SIGNALS) -> list[str]:
    """Name the nodes a transient should print, in the order they appear.

    Read from the element lines rather than guessed, and bounded by how many
    terminals each device letter actually has -- a resistor's third token is a
    value, not a node, and printing `v(4.7k)` would make ngspice reject the
    whole deck. Devices whose shape is not known here (a subcircuit call) are
    skipped rather than approximated. Ground is never printed: it is zero.
    """
    seen: list[str] = []
    for raw in (netlist or "").splitlines():
        line = raw.strip()
        if not line or line.startswith((".", "*")):
            continue
        tokens = line.split()
        count = _DEVICE_NODE_COUNT.get(tokens[0][:1].lower())
        if count is None:
            continue
        for node in tokens[1:1 + count]:
            name = node.lower()
            if name not in _GROUND_NODES and name not in seen:
                seen.append(name)
    return seen[:limit]


#: The reference for the supply ramp this module can add. SPICE reads the first
#: letter as the device type, so an independent voltage source must start with V.
STIMULUS_REFERENCE = "Vohmni_stimulus"
STIMULUS_NET = "VBUS"
STIMULUS_VOLTS = 5.0
STIMULUS_RISE = "1u"


def with_power_on_stimulus(netlist: str, net: str = STIMULUS_NET, *,
                           volts: float = STIMULUS_VOLTS,
                           rise: str = STIMULUS_RISE) -> tuple[str, str | None]:
    """Add an assumed supply ramp to a deck that nothing drives.

    Returns the deck and a sentence describing what was assumed, or the deck
    unchanged and ``None`` when nothing was added. The sentence is the point: a
    ramp is a *stimulus Ohmni invented*, not a measured or specified supply
    behaviour, and a curve produced from it means "if the rail came up like
    this" -- never "the rail comes up like this". Anything that displays the
    result has to be able to say so, which it cannot do if the assumption is
    silent.

    Nothing is added when the deck already has a source (two sources on one net
    is a short, not a better simulation) or when the named net is not in the
    deck (driving a node nothing connects to simulates a different circuit).
    """
    if has_independent_source(netlist):
        return netlist, None
    target = (net or "").strip()
    if not target or target.lower() not in netlist_nodes(netlist, limit=10 ** 6):
        return netlist, None
    lines = (netlist or "").splitlines()
    stripped = [line.strip() for line in lines]
    source = f"{STIMULUS_REFERENCE} {target} 0 PULSE(0 {volts} 0 {rise} {rise} 1 2)"
    note = (
        f"Supply ramp assumed, not measured: {target} driven from 0 to {volts} V with a "
        f"{rise}s rise. Ohmni added this source because the exported netlist has none; the "
        "result shows what would happen under that assumption."
    )
    end = next(
        (index for index in range(len(stripped) - 1, -1, -1)
         if re.fullmatch(r"\.end", stripped[index], re.IGNORECASE)),
        None,
    )
    if end is None:
        return "\n".join([*lines, source, ".end"]) + "\n", note
    return "\n".join([*lines[:end], source, *lines[end:]]) + "\n", note


def transient_deck(netlist: str, tstep: str, tstop: str, signals: list[str], *,
                   precision: int | None = None, currents: list[str] = (),
                   tmax: str | None = None) -> str:
    """Add the transient command and the signals to print, and nothing else.

    Built the same way as the operating-point deck: the caller's first line
    stays first because a SPICE deck's first line is its title, existing
    commands are never duplicated, and the analysis goes in before `.end`.
    """
    lines = (netlist or "").splitlines()
    stripped = [line.strip() for line in lines]
    additions = []
    if not any(re.match(r"\.tran\b", line, re.IGNORECASE) for line in stripped):
        if tmax is None:
            additions.append(f".tran {tstep} {tstop}")
        else:
            # A switching model needs short internal steps; printing every internal point would be millions
            # of rows, so the rows are interpolated to the print step (D074).
            additions.extend([".options interp", f".tran {tstep} {tstop} 0 {tmax}"])
    if precision is not None:
        if type(precision) is not int or not 6 <= precision <= 17:
            raise ValueError("transient print precision must be an integer from6 to17")
        if any(re.match(r"\.control\b", line, re.IGNORECASE) for line in stripped):
            raise ValueError("precise transient printing cannot replace an existing control block")
        printed = " ".join([*(f"v({name})" for name in signals), *(f"i({name})" for name in currents)])
        additions.extend([".control", f"set numdgt={precision}", "run",
                          f"print {printed}", "quit", ".endc"])
    elif not any(re.match(r"\.print\s+tran\b", line, re.IGNORECASE) for line in stripped):
        printed = " ".join(f"v({name})" for name in signals)
        additions.append(f".print tran {printed}" if printed else ".print tran")
    end = next(
        (index for index in range(len(stripped) - 1, -1, -1)
         if re.fullmatch(r"\.end", stripped[index], re.IGNORECASE)),
        None,
    )
    if end is None:
        return "\n".join([*lines, *additions, ".end"]) + "\n"
    return "\n".join([*lines[:end], *additions, *lines[end:]]) + "\n"


AC_LIMITATIONS = [
    "Small-signal AC solution of the bound models around their operating point; exact only for linear circuits.",
    ("Bound cards omit unsourced parasitics (ESL, self-resonance, and ESR where it is not sourced), so AC "
    "voltages and current sharing between parts can be non-conservative."),
    ("Only classes with an AC rating translation are checked at each frequency; every other part reports "
    "its AC checks unknown, so an AC run never passes on operating-point rows alone."),
    ("A KEMET T491 ripple or ESR-heating pass at 100 kHz and 25 C comes from a second solve with the card's "
    "ESR shorted (esr_zero) and holds for any passive part impedance, so it does not rely on the omitted ESL "
    "or the 100 kHz capacitance; no violation of those rows is proven for a card with a series ESR."),
]
MAX_AC_POINTS = 8
MAX_AC_SWEEP_POINTS = 401
_AC_POINT = re.compile(r"^OHMNI_AC_POINT\s+(?P<index>\d+)$")
_AC_VALUE = re.compile(rf"^(?P<part>real|imag)\((?P<kind>[vi])\((?P<name>[^()\s]+)\)\)\s*=\s*(?P<value>{_NUMBER})$",
                       re.IGNORECASE)
_AC_FREQUENCY = re.compile(rf"^real\(frequency\)\s*=\s*(?P<value>{_NUMBER})$", re.IGNORECASE)
_AC_SWEEP_HEADER = re.compile(r"^index\s+frequency\b", re.IGNORECASE)


def _display_cut(total):
    """The returned curves show at most MAX_TRANSIENT_SIGNALS nets; ratings still read every terminal."""
    return (f"Display shows {MAX_TRANSIENT_SIGNALS} of {total} nets (in net-name order); pass observe_nets to "
            "choose them. Rating checks still use every part terminal.")


def ac_deck(netlist: str, *, nodes: list[str], currents: list[str], points_hz: list[float],
            sweep: tuple[float, float, int] | None = None, sweep_nodes: list[str] = ()) -> str:
    """Operating point, then one single-frequency AC solve per requested point, then an optional sweep.

    Every printed block is preceded by an echoed marker naming the point's index, so a value is
    attributed to a frequency only by its own marker, never by its position in the output.
    """
    lines = (netlist or "").splitlines()
    stripped = [line.strip() for line in lines]
    if any(re.match(r"\.(?:control|ac|op|tran|save|meas|measure|print|plot)\b", line, re.IGNORECASE)
           for line in stripped):
        raise ValueError("an AC deck cannot replace existing analysis commands")
    if not 1 <= len(points_hz) <= MAX_AC_POINTS or any(not math.isfinite(f) or f <= 0 for f in points_hz):
        raise ValueError("AC analysis needs one to eight positive finite frequencies")
    op_print = " ".join([*(f"v({n})" for n in nodes), *(f"i({c})" for c in currents)])
    phasors = " ".join(f"real({q}) imag({q})" for q in [*(f"v({n})" for n in nodes), *(f"i({c})" for c in currents)])
    additions = [".control", "set numdgt=15", "op", "echo OHMNI_AC_OP"]
    if op_print:
        additions.append(f"print {op_print}")
    for index, frequency in enumerate(points_hz):
        # The solved frequency is printed with the phasors: a failed solve cannot pass off the previous
        # plot's vectors under this point's marker, because their frequency would not match.
        additions += [f"echo OHMNI_AC_POINT {index}", f"ac lin 1 {frequency:.17g} {frequency:.17g}",
                      f"print real(frequency) {phasors}".rstrip()]
    if sweep is not None:
        start, stop, per_decade = sweep
        if (not (math.isfinite(start) and math.isfinite(stop)) or not 0 < start < stop or type(per_decade) is not int
                or not 1 <= per_decade <= 50 or per_decade * math.log10(stop / start) + 1 > MAX_AC_SWEEP_POINTS
                or not sweep_nodes):
            raise ValueError("AC sweep needs 0 < start < stop, 1 to 50 points per decade and observed nets")
        additions += ["echo OHMNI_AC_SWEEP", f"ac dec {per_decade} {start:.17g} {stop:.17g}",
                      "print " + " ".join(f"vm({n}) vp({n})" for n in sweep_nodes)]
    additions += ["quit", ".endc"]
    end = next((i for i in range(len(stripped) - 1, -1, -1) if re.fullmatch(r"\.end", stripped[i], re.IGNORECASE)), None)
    if end is None:
        return "\n".join([*lines, *additions, ".end"]) + "\n"
    return "\n".join([*lines[:end], *additions, *lines[end:]]) + "\n"


def parse_ac(stdout: str, points_hz: list[float]) -> dict:
    """Read the operating point, the RMS phasor at each requested frequency, and the optional sweep.

    A point whose block is missing or incomplete is dropped, never filled; a phasor needs both its
    real and its imaginary part.
    """
    section, point = None, None
    op_lines, raw, solved_at, conflicts = [], {}, {}, set()
    sweep_lines = []
    for line in (stdout or "").splitlines():
        text = line.replace("\f", " ").strip()
        if text == "OHMNI_AC_OP":
            section = "op"
            continue
        if marker := _AC_POINT.match(text):
            section, point = "point", int(marker["index"])
            continue
        if text == "OHMNI_AC_SWEEP":
            section = "sweep"
            continue
        if section == "op":
            op_lines.append(text)
        elif section == "point" and (solved := _AC_FREQUENCY.match(text)):
            if point in solved_at:
                conflicts.add(point)
            solved_at[point] = float(solved["value"])
        elif section == "point" and (value := _AC_VALUE.match(text)):
            key = ("v" if value["kind"].lower() == "v" else "i", value["name"].lower())
            parts = raw.setdefault(point, {}).setdefault(key, {})
            if value["part"].lower() in parts:
                conflicts.add(point)
            parts[value["part"].lower()] = float(value["value"])
        elif section == "sweep":
            sweep_lines.append(text)
    operating_point = parse_operating_point("\n".join(op_lines))
    points = []
    for index, frequency in enumerate(points_hz):
        values = raw.get(index, {})
        if (not values or index in conflicts or index not in solved_at
                or not math.isclose(solved_at[index], frequency, rel_tol=1e-9)
                or any(set(parts) != {"real", "imag"} for parts in values.values())):
            continue
        points.append({
            "frequency_hz": frequency,
            "node_voltages": {n: [p["real"], p["imag"]] for (k, n), p in sorted(values.items()) if k == "v"},
            "branch_currents": {n: [p["real"], p["imag"]] for (k, n), p in sorted(values.items()) if k == "i"},
        })
    # Wide tables are printed in column groups, each repeating every index: join by index and name.
    sweep = None
    columns, rows, order = [], {}, []
    for text in sweep_lines:
        if _AC_SWEEP_HEADER.match(text):
            columns = [c.lower() for c in text.split()[1:]]
            order.extend(c for c in columns[1:] if c not in order)
            continue
        tokens = text.split()
        if not columns or len(tokens) != len(columns) + 1:
            continue
        try:
            index, values = int(tokens[0]), [float(t) for t in tokens[1:]]
        except ValueError:
            continue
        row = rows.setdefault(index, {})
        for name, value in zip(columns, values, strict=True):
            if name in row and row[name] != value:
                return {"operating_point": operating_point, "points": points, "sweep": None}
            row[name] = value
    complete = [rows[k] for k in sorted(rows) if all(c in rows[k] for c in ["frequency", *order])]
    if order and complete and len(complete) == len(rows):
        series = []
        for name in order:
            if not name.startswith("vm("):
                continue
            phase = "vp(" + name[3:]
            if phase not in order:
                return {"operating_point": operating_point, "points": points, "sweep": None}
            series.append({"name": "v(" + name[3:], "unit": "V",
                           "magnitude": [row[name] for row in complete],
                           "phase_deg": [math.degrees(row[phase]) for row in complete]})
        sweep = {"frequency_hz": [row["frequency"] for row in complete], "series": series}
    return {"operating_point": operating_point, "points": points, "sweep": sweep}


def parse_transient(stdout: str, *, analysis: str,
                    limit: int = MAX_TRANSIENT_SAMPLES) -> TransientData:
    """Read ngspice's column output into a time axis and one series per signal.

    ngspice pages a transient table, repeating the header every screenful, so
    the header is what defines the columns and every repeat of it is skipped
    rather than parsed as data. A row is only data when it has exactly as many
    numbers as the header had columns: a partial row at a page break is dropped,
    because half a sample is not a measurement.
    """
    columns: list[str] = []
    indexed = False
    signal_names: list[str] = []
    samples: dict[tuple[int | None, float], dict[str, float]] = {}
    for raw in (stdout or "").splitlines():
        line = raw.replace("\f", " ").strip()
        if not line:
            continue
        if _TRANSIENT_HEADER.match(line):
            # The header decides the shape of every row beneath it, including
            # whether ngspice is numbering them. Deciding per row instead reads
            # a truncated line as a complete one with the row number in the time
            # column -- a sample at t=1 second on a millisecond plot.
            heading = line.split()
            indexed = heading[0].lower() == "index"
            columns = heading[1:] if indexed else heading
            for name in columns[1:]:
                if name.lower() not in signal_names:
                    signal_names.append(name.lower())
            continue
        if not columns or _RULE_LINE.match(line):
            continue
        tokens = line.split()
        if len(tokens) != len(columns) + (1 if indexed else 0):
            continue
        try:
            index = int(tokens[0]) if indexed else None
            if indexed:
                tokens = tokens[1:]
            values = [float(token) for token in tokens]
        except ValueError:
            continue
        sample = samples.setdefault((index, values[0]), {})
        for name, value in zip(columns[1:], values[1:], strict=True):
            name = name.lower()
            if name in sample and sample[name] != value:
                return TransientData(analysis=analysis)
            sample[name] = value
    # Wide ngspice print tables repeat all sample indices for the next group
    # of columns. Join by sample identity before thinning; never relabel an
    # earlier group's values with the final group's header.
    rows = [[time, *(sample[name] for name in signal_names)]
            for (_, time), sample in sorted(samples.items(), key=lambda item: item[0][1])
            if all(name in sample for name in signal_names)]
    if not signal_names or not rows:
        return TransientData(analysis=analysis)
    total = len(rows)
    if total > limit:
        step = -(-total // limit)  # ceiling division keeps the last row reachable
        kept = rows[::step]
        if kept[-1] is not rows[-1]:
            kept.append(rows[-1])
        rows = kept
    series = []
    for position, name in enumerate(signal_names, start=1):
        series.append(TransientSeries(
            name=name.lower(), unit=_series_unit(name),
            values=[row[position] for row in rows],
        ))
    return TransientData(
        analysis=analysis,
        time_s=[row[0] for row in rows],
        series=series,
        decimated_from=total if total > len(rows) else None,
    )


def _series_unit(name: str) -> Unit:
    """A column says which quantity it is; nothing else decides."""
    return Unit.AMPERE if name.strip().lower().startswith("i") else Unit.VOLT


class SpiceNetlist(BaseModel):
    """One netlist export attempt. Missing text is missing, never an empty circuit."""

    status: ToolStatus
    text: str | None = None
    path: str | None = None
    detail: str | None = None

    @property
    def usable(self) -> bool:
        return self.status is ToolStatus.OK and bool(self.text and self.text.strip())


class KiCadNetlistExporter:
    """Exports a SPICE netlist from a compiled schematic artifact.

    Bound to the artifact's fingerprint, like every other external check here: a
    netlist exported from a schematic that changed underneath it describes a
    circuit nobody proposed.
    """

    name = "kicad-cli"

    def __init__(self, executable: str | None = None, *,
                 timeout_seconds: float = NETLIST_TIMEOUT_SECONDS) -> None:
        self.executable = executable if executable is not None else find_kicad_cli()
        self.timeout_seconds = timeout_seconds

    def availability(self) -> ToolAvailability:
        if self.executable is None:
            return ToolAvailability(
                name=self.name, status=ToolStatus.UNAVAILABLE,
                detail="kicad-cli was not found; no SPICE netlist can be exported.",
            )
        return ToolAvailability(name=self.name, status=ToolStatus.OK, executable=self.executable)

    def export(self, artifact: SchematicArtifact, destination: Path | None = None) -> SpiceNetlist:
        if self.executable is None:
            return SpiceNetlist(status=ToolStatus.UNAVAILABLE,
                                detail="kicad-cli was not found; no SPICE netlist was exported.")
        if not artifact.is_current:
            return SpiceNetlist(
                status=ToolStatus.FAILED,
                detail="the schematic changed after compilation; no netlist was exported from it",
            )
        destination = destination or artifact.path.with_suffix(".cir")
        command = [self.executable, "sch", "export", "netlist",
                   "--format", "spice", "--output", str(destination), str(artifact.path)]
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            completed = run_tool(command, timeout=self.timeout_seconds)
        except ToolTimeoutError:
            return SpiceNetlist(status=ToolStatus.TIMED_OUT,
                                detail=f"kicad-cli netlist export exceeded {self.timeout_seconds}s")
        except OSError as exc:
            return SpiceNetlist(status=ToolStatus.FAILED,
                                detail=_clip(f"kicad-cli could not run: {exc}"))
        if completed.returncode != 0:
            return SpiceNetlist(
                status=ToolStatus.FAILED,
                detail=_clip(f"kicad-cli netlist export failed ({describe_exit(completed.returncode)}): "
                             f"{_error_summary(completed.stderr, completed.stdout)}"),
            )
        try:
            text = destination.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return SpiceNetlist(status=ToolStatus.FAILED,
                                detail=_clip(f"the exported netlist could not be read: {exc}"))
        if not text.strip():
            return SpiceNetlist(status=ToolStatus.FAILED,
                                detail="kicad-cli reported success but wrote an empty netlist")
        return SpiceNetlist(status=ToolStatus.OK, text=text, path=str(destination))


@contextmanager
def _deck_file(deck: str, run_id: str, work_dir: Path | None) -> Iterator[Path]:
    """Write the deck where the caller can keep it, or somewhere temporary."""
    if work_dir is not None:
        work_dir.mkdir(parents=True, exist_ok=True)
        path = work_dir / f"{run_id}.op.cir"
        path.write_text(deck, encoding="utf-8")
        yield path
        return
    with tempfile.TemporaryDirectory(prefix="ohmni-spice-") as directory:
        path = Path(directory) / f"{run_id}.op.cir"
        path.write_text(deck, encoding="utf-8")
        yield path


class NgspiceAdapter:
    """A :class:`~ohmni.adapters.SpiceTool` backed by the standalone ngspice CLI.

    KiCad ships ngspice as a shared library rather than an executable on some
    platforms; that binding is spike S2 and is not this. When no standalone
    executable is found, every call reports UNAVAILABLE without touching disk.
    """

    name = "ngspice"

    def __init__(self, executable: str | None = None, *,
                 timeout_seconds: float = NGSPICE_TIMEOUT_SECONDS) -> None:
        self.executable = executable if executable is not None else find_ngspice()
        self.timeout_seconds = timeout_seconds

    def availability(self) -> ToolAvailability:
        # The existing probe already runs `--version` and explains the KiCad
        # shared-library case; re-deriving that here would be a second answer to
        # the same question.
        if self.executable is None:
            return ToolAvailability(
                name=self.name, status=ToolStatus.UNAVAILABLE, detail=_NGSPICE_MISSING,
            )
        return NgspiceCli(self.executable).availability()

    def behavior_bench(self, deck: str, *, work_dir: Path, compatibility: str | None = None) -> dict:
        """Execute an authored, fully inlined bench with version and raw output.

        A successful process is only an observation. Analytical comparisons are
        performed separately; this method never declares an electrical pass.
        """
        result = {"status": "not_run", "version_output": "", "stdout": "", "stderr": "",
                  "returncode": None, "product_code_path": "ohmni.eda.simulation.NgspiceAdapter.behavior_bench"}
        if self.executable is None:
            result["stderr"] = "ngspice executable unavailable"
            return result
        try:
            version = run_tool([self.executable, "-v"], timeout=self.timeout_seconds)
            result["version_output"] = version.stdout + version.stderr
            if version.returncode != 0 or not re.search(r"\bngspice(?:[-\s]+version)?[-\s]+42(?:\D|$)", result["version_output"], re.IGNORECASE):
                result["stderr"] = "ngspice 42 version gate failed"
                return result
            # This path accepts trusted authored decks, never file/shell control commands.
            unsafe = re.compile(r"^\s*(?:\.(?:include|inc|lib)\b|(?:shell|source|cd|write|wrdata|hardcopy)\b)", re.IGNORECASE | re.MULTILINE)
            if unsafe.search(deck):
                result["stderr"] = "bench must be inlined and cannot issue file or shell commands"
                return result
            work_dir.mkdir(parents=True, exist_ok=True)
            path = work_dir / "bench.cir"
            path.write_text(deck, encoding="utf-8", newline="\n")
            # Only a deck holding a manufacturer model written in PSpice syntax runs in PSpice compatibility
            # mode; every other deck keeps the plain command line (D074).
            if compatibility not in (None, "psa"):
                result["stderr"] = f"unsupported ngspice compatibility mode {compatibility}"
                return result
            mode = ["-D", f"ngbehavior={compatibility}"] if compatibility else []
            completed = run_tool([self.executable, *mode, "-b", str(path.resolve())], timeout=self.timeout_seconds)
            result.update(stdout=completed.stdout, stderr=completed.stderr, returncode=completed.returncode)
            result["status"] = "ran" if completed.returncode == 0 and not _error_summary(completed.stdout, completed.stderr) else "failed"
        except ToolTimeoutError:
            result.update(status="timed_out", stderr="ngspice timed out")
        except OSError as exc:
            result.update(status="failed", stderr=str(exc))
        return result

    def behavior_circuit(self, compilation, *, work_dir: Path, analysis: str = "op",
                         tstep: str = DEFAULT_TSTEP, tstop: str = DEFAULT_TSTOP,
                         observe_nets: list[str] | None = None, rating_context=None,
                         rating_registry=None, apply_failures: bool = True,
                         ac_points_hz: list[float] | None = None,
                         ac_sweep: tuple[float, float, int] | None = None) -> dict:
        """Run a compiled CircuitIR model with the same version-gated adapter.

        `ran` records observations, never a design pass. Rating checks are a
        separate deterministic step and retain the original simulation data.
        """
        result = {
            "status": "not_run", "analysis": analysis, "version_output": "",
            "netlist_sha256": compilation.netlist_sha256,
            "circuit_hash": compilation.circuit_hash,
            "components": [c.model_dump(mode="json") for c in compilation.components],
            "node_names": compilation.node_names,
            "source_elements": compilation.source_elements,
            "limitations": compilation.limitations,
            "problems": list(compilation.problems), "rating_status": "not_run",
            "operating_point": None, "transient": None, "ac": None,
        }
        if not compilation.runnable:
            return result
        if analysis != compilation.analysis:
            result["problems"].append("Requested analysis differs from the validated compilation")
            return result
        if analysis == "op":
            deck = operating_point_deck(compilation.netlist)
        elif analysis == "tran":
            # Reuse the bounded existing transient builder and parser.
            try:
                step = parse_quantity(tstep, Unit.SECOND)
                stop = parse_quantity(tstop, Unit.SECOND)
                if step.value <= 0 or stop.value < step.value:
                    raise ValueError("transient requires 0 < step <= stop")
            except ValueError:
                result["problems"].append("Invalid transient time value")
                return result
            if observe_nets is not None:
                if (not observe_nets or len(observe_nets) > MAX_TRANSIENT_SIGNALS
                        or len(set(observe_nets)) != len(observe_nets)
                        or any(n not in compilation.node_names or compilation.node_names[n] == "0" for n in observe_nets)):
                    result["problems"].append("Observed nets must be distinct known non-ground nets within the signal limit")
                    return result
                signals = [compilation.node_names[n] for n in observe_nets]
            else:
                signals = [node for node in compilation.node_names.values() if node != "0"]
            shown = signals[:MAX_TRANSIENT_SIGNALS]
            if len(signals) > len(shown):
                result["limitations"] = [*result["limitations"], _display_cut(len(signals))]
            # Ratings need every terminal voltage and probe current of each part; they are printed after the
            # requested signals and kept out of the returned display curve.
            rating_nodes = [node for c in compilation.components for node in c.role_nodes.values()
                            if node != "0" and node not in shown]
            rating_nodes = list(dict.fromkeys(rating_nodes))
            probes = [probe for c in compilation.components for probe in c.role_current_probes.values()]
            if len(shown) + len(rating_nodes) + len(probes) > MAX_RATING_SIGNALS:
                rating_nodes, probes = [], []
            tmax = compilation.transient_max_step_s
            deck = transient_deck(compilation.netlist, format(step.value, ".17g"),
                                  format(stop.value, ".17g"), [*shown, *rating_nodes], precision=15,
                                  currents=probes, tmax=format(min(tmax, step.value), ".17g") if tmax else None)
        elif analysis == "ac":
            points = list(ac_points_hz or [])
            nodes = list(dict.fromkeys(node for c in compilation.components for node in c.role_nodes.values()
                                       if node != "0"))
            probes = [probe for c in compilation.components for probe in c.role_current_probes.values()]
            if observe_nets is not None and (
                    not observe_nets or len(observe_nets) > MAX_TRANSIENT_SIGNALS
                    or len(set(observe_nets)) != len(observe_nets)
                    or any(n not in compilation.node_names or compilation.node_names[n] == "0" for n in observe_nets)):
                result["problems"].append("Observed nets must be distinct known non-ground nets within the signal limit")
                return result
            candidates = ([compilation.node_names[n] for n in observe_nets] if observe_nets is not None
                          else [n for n in compilation.node_names.values() if n != "0"])
            sweep_nodes = candidates[:MAX_TRANSIENT_SIGNALS]
            if ac_sweep is not None and len(candidates) > len(sweep_nodes):
                result["limitations"] = [*result["limitations"], _display_cut(len(candidates))]
            try:
                deck = ac_deck(compilation.netlist, nodes=nodes, currents=probes, points_hz=points,
                               sweep=ac_sweep, sweep_nodes=sweep_nodes)
            except ValueError as exc:
                result["problems"].append(str(exc))
                return result
        else:
            result["problems"].append(f"Unsupported circuit analysis: {analysis}")
            return result
        observation = self.behavior_bench(deck, work_dir=work_dir, compatibility=compilation.ngspice_compatibility)
        result.update(observation)
        result["product_code_path"] = "ohmni.eda.simulation.NgspiceAdapter.behavior_circuit"
        if observation["status"] != "ran":
            return result
        if analysis == "op":
            point = parse_operating_point(observation["stdout"])
            if not point.node_voltages and not point.branch_currents:
                result.update(status="failed", problems=["ngspice returned no operating-point observations"])
            else:
                result["operating_point"] = point.model_dump(mode="json")
        elif analysis == "ac":
            parsed = parse_ac(observation["stdout"], points)
            point = parsed["operating_point"]
            if (not point.node_voltages and not point.branch_currents) or len(parsed["points"]) != len(points):
                result.update(status="failed", problems=["ngspice returned incomplete AC observations"])
            else:
                result["operating_point"] = point.model_dump(mode="json")
                names = {node: name for name, node in compilation.node_names.items()}
                sweep = parsed["sweep"]
                if sweep:
                    sweep = {**sweep, "series": [{**x, "name": names.get(x["name"][2:-1], x["name"])}
                                                 for x in sweep["series"]]}
                missing = [q for q in [*nodes, *probes] if not all(
                    q.lower() in {**p["node_voltages"], **p["branch_currents"]} for p in parsed["points"])]
                if missing:
                    result.update(status="failed", problems=["ngspice did not print every requested AC vector"])
                    return result
                result["ac"] = {"points": parsed["points"], "sweep": sweep,
                                "amplitude": "RMS phasors of the declared AC excitations",
                                "limitations": AC_LIMITATIONS}
                esr_zero = self._esr_zero_solve(compilation, work_dir, points, nodes, probes)
                if esr_zero is not None:
                    result["ac"]["esr_zero"] = esr_zero
        else:
            curve = parse_transient(observation["stdout"], analysis="tran")
            display = {f"v({name})" for name in shown}
            curve = curve.model_copy(update={"series": [x for x in curve.series if x.name.lower() in display]})
            if not curve.sample_count or not curve.series:
                result.update(status="failed", problems=["ngspice returned no transient observations"])
            else:
                result["transient"] = curve.model_dump(mode="json")
        from ..behavior.loader import default_behavior_registry
        from ..behavior.ratings import RatingContext, apply_open_faults, evaluate_ratings

        registry = rating_registry or default_behavior_registry()
        context = RatingContext.model_validate(rating_context or {})
        result["ratings"] = evaluate_ratings(compilation, result, registry, context)
        result["rating_status"] = result["ratings"]["status"]
        if apply_failures and result["ratings"]["fault_requests"]:
            faulted = apply_open_faults(compilation, result["ratings"]["fault_requests"])
            failure = self.behavior_circuit(faulted, work_dir=work_dir / "failure", analysis=analysis,
                                          rating_context=context, rating_registry=registry, apply_failures=False,
                                          tstep=tstep, tstop=tstop, observe_nets=observe_nets,
                                          ac_points_hz=ac_points_hz, ac_sweep=ac_sweep)
            failure.update(ratings=None, rating_status="failure_approximation",
                           limitation="Authored open-circuit substitution; not a physical damage prediction")
            result["failure_rerun"] = failure
        return result

    def _esr_zero_solve(self, compilation, work_dir: Path, points: list[float], nodes: list[str],
                        probes: list[str]) -> dict | None:
        """Second AC solve at the tantalum ripple rating frequency with each bound series ESR shorted (D064).

        Only an observation: the rating step decides what the two solves prove. A failed or incomplete
        second solve is recorded as such and never replaced by values from the first.
        """
        from ..behavior.ratings import RIPPLE_RATING_HZ, esr_dual_solve_elements, short_elements

        rated = [f for f in points if math.isclose(f, RIPPLE_RATING_HZ, rel_tol=1e-9)]
        elements = esr_dual_solve_elements(compilation) if rated else []
        if not elements:
            return None
        # Both hashes are of the netlist before the control block: the first solve's is the compilation's
        # own netlist hash, and the second's is that netlist with the listed elements shorted. The rating
        # step recomputes both and refuses a second solve that does not match.
        variant = {"status": "failed", "elements": elements, "points": [],
                   "source_netlist_sha256": hashlib.sha256(compilation.netlist.encode()).hexdigest(),
                   "description": "Same AC solve with each listed series-ESR element replaced by a 0 V short"}
        try:
            netlist = short_elements(compilation.netlist, elements)
            deck = ac_deck(netlist, nodes=nodes, currents=probes, points_hz=rated)
        except ValueError as exc:
            variant["problems"] = [str(exc)]
            return variant
        variant["netlist_sha256"] = hashlib.sha256(netlist.encode()).hexdigest()
        observation = self.behavior_bench(deck, work_dir=work_dir / "esr_zero",
                                          compatibility=compilation.ngspice_compatibility)
        if observation["status"] != "ran":
            variant["problems"] = [f"ngspice {observation['status']}"]
            return variant
        parsed = parse_ac(observation["stdout"], rated)
        if len(parsed["points"]) != len(rated) or any(
                q.lower() not in {**p["node_voltages"], **p["branch_currents"]}
                for p in parsed["points"] for q in [*nodes, *probes]):
            variant["problems"] = ["ngspice returned incomplete AC observations"]
            return variant
        variant.update(status="ran", points=parsed["points"])
        return variant

    def operating_point(self, netlist: str, run_id: str, *,
                        work_dir: Path | None = None) -> SimulationRun:
        fidelity = model_fidelity(netlist)
        if self.executable is None:
            return _not_run(run_id, ToolStatus.UNAVAILABLE, fidelity, _NGSPICE_MISSING)
        if not isinstance(netlist, str) or not netlist.strip():
            return _not_run(run_id, ToolStatus.FAILED, fidelity,
                                 "no netlist was supplied, so nothing was simulated")
        deck = operating_point_deck(netlist)
        try:
            with _deck_file(deck, run_id, work_dir) as path:
                netlist_path = str(path) if work_dir is not None else None
                try:
                    completed = run_tool([self.executable, "-b", str(path)],
                                         timeout=self.timeout_seconds)
                except ToolTimeoutError:
                    return _not_run(run_id, ToolStatus.TIMED_OUT, fidelity,
                                         f"ngspice exceeded {self.timeout_seconds}s",
                                         netlist_path)
                except OSError as exc:
                    return _not_run(run_id, ToolStatus.FAILED, fidelity,
                                         _clip(f"ngspice could not run: {exc}"), netlist_path)
        except OSError as exc:
            return _not_run(run_id, ToolStatus.FAILED, fidelity,
                                 _clip(f"the netlist could not be written: {exc}"))
        summary = describe_netlist(netlist)
        errors = _error_summary(completed.stderr, completed.stdout)
        if completed.returncode != 0:
            return _not_run(
                run_id, ToolStatus.FAILED, fidelity,
                _clip(f"ngspice failed ({describe_exit(completed.returncode)}): {errors or summary}"),
                netlist_path,
            )
        point = parse_operating_point(completed.stdout)
        if not point.node_voltages and not point.branch_currents:
            # A clean exit with nothing to read is not a passing simulation.
            return _not_run(
                run_id, ToolStatus.FAILED, fidelity,
                _clip("ngspice completed without reporting an operating point"
                      + (f": {errors}" if errors else f" ({summary})")),
                netlist_path,
            )
        detail = _clip(
            f"{len(point.node_voltages)} node voltage(s), "
            f"{len(point.branch_currents)} branch current(s); {summary}"
            + (f"; ngspice reported: {errors}" if errors else "")
        )
        return SimulationRun(
            status=ToolStatus.OK, run_id=run_id, analysis=OPERATING_POINT,
            model_fidelity=fidelity, operating_point=point, netlist_path=netlist_path,
            detail=detail,
            evidence=[Evidence(
                kind=EvidenceKind.SIMULATION,
                label="ngspice DC operating point",
                source_id=run_id,
                text_value=f"{len(point.node_voltages)} node voltages",
                detail=f"analysis={OPERATING_POINT}; model_fidelity={fidelity}; {summary}",
            )],
        )


    def transient_analysis(self, netlist: str, run_id: str, tstep: str = DEFAULT_TSTEP,
                           tstop: str = DEFAULT_TSTOP, *, signals: list[str] | None = None,
                           work_dir: Path | None = None) -> SimulationRun:
        """Run one time-domain analysis and return the curves it produced.

        The same rule as the operating point governs the result: a run that
        produced no samples is FAILED, never an empty graph. An empty graph is
        the most misleading thing this could return, because it looks like a
        measurement of a circuit that does nothing.
        """
        analysis = f".tran {tstep} {tstop}"
        fidelity = model_fidelity(netlist)
        if self.executable is None:
            return _not_run(run_id, ToolStatus.UNAVAILABLE, fidelity, _NGSPICE_MISSING,
                            analysis=analysis)
        if not isinstance(netlist, str) or not netlist.strip():
            return _not_run(run_id, ToolStatus.FAILED, fidelity,
                            "no netlist was supplied, so nothing was simulated",
                            analysis=analysis)
        printed = netlist_nodes(netlist) if signals is None else list(signals)
        if not printed:
            return _not_run(run_id, ToolStatus.FAILED, fidelity,
                            "no nodes could be named to print, so there is nothing to plot",
                            analysis=analysis)
        deck = transient_deck(netlist, tstep, tstop, printed)
        try:
            with _deck_file(deck, f"{run_id}.tran", work_dir) as path:
                netlist_path = str(path) if work_dir is not None else None
                try:
                    completed = run_tool([self.executable, "-b", str(path)],
                                         timeout=self.timeout_seconds)
                except ToolTimeoutError:
                    return _not_run(run_id, ToolStatus.TIMED_OUT, fidelity,
                                    f"ngspice exceeded {self.timeout_seconds}s",
                                    netlist_path, analysis)
                except OSError as exc:
                    return _not_run(run_id, ToolStatus.FAILED, fidelity,
                                    _clip(f"ngspice could not run: {exc}"),
                                    netlist_path, analysis)
        except OSError as exc:
            return _not_run(run_id, ToolStatus.FAILED, fidelity,
                            _clip(f"the netlist could not be written: {exc}"), analysis=analysis)
        errors = _error_summary(completed.stderr, completed.stdout)
        if completed.returncode != 0:
            return _not_run(
                run_id, ToolStatus.FAILED, fidelity,
                _clip(f"ngspice failed ({describe_exit(completed.returncode)}): "
                      f"{errors or describe_netlist(netlist)}"),
                netlist_path, analysis,
            )
        data = parse_transient(completed.stdout, analysis=analysis)
        if not data.series or not data.time_s:
            return _not_run(
                run_id, ToolStatus.FAILED, fidelity,
                _clip("ngspice completed without reporting a transient"
                      + (f": {errors}" if errors else "")),
                netlist_path, analysis,
            )
        detail = _clip(
            f"{len(data.series)} signal(s) over {data.sample_count} sample(s); "
            f"{describe_netlist(netlist)}"
            + (f"; thinned from {data.decimated_from} rows" if data.decimated_from else "")
            + (f"; ngspice reported: {errors}" if errors else "")
        )
        return SimulationRun(
            status=ToolStatus.OK, run_id=run_id, analysis=analysis,
            model_fidelity=fidelity, transient_data=data, netlist_path=netlist_path,
            detail=detail,
            evidence=[Evidence(
                kind=EvidenceKind.SIMULATION,
                label="ngspice transient analysis",
                source_id=run_id,
                text_value=f"{len(data.series)} signals over {data.sample_count} samples",
                detail=f"analysis={analysis}; model_fidelity={fidelity}; "
                       f"{describe_netlist(netlist)}",
            )],
        )


def _with_transient(run: SimulationRun, netlist: str, spice, run_id: str,
                    work_dir: Path | None, wanted: bool, tstep: str, tstop: str,
                    stimulus: bool = False) -> SimulationRun:
    """Attach a time-domain result to a successful operating point, if one is owed."""
    analyse = getattr(spice, "transient_analysis", None)
    if not wanted or run.status is not ToolStatus.OK or not callable(analyse):
        return run
    deck, assumption = (with_power_on_stimulus(netlist) if stimulus else (netlist, None))
    if not has_independent_source(deck):
        return run
    result = analyse(deck, run_id, tstep, tstop, work_dir=work_dir)
    if assumption is not None and result.transient_data is not None:
        result = result.model_copy(update={
            "detail": _clip(f"{assumption} {result.detail or ''}"),
        })
    if result.status is not ToolStatus.OK or result.transient_data is None:
        # Said plainly rather than passed over: a reader comparing two reports
        # should be able to see that one of them tried and did not get a curve.
        return run.model_copy(update={
            "detail": _clip(f"{run.detail or ''}; transient {result.status.value}: "
                            f"{result.detail or 'no detail'}"),
        })
    return run.model_copy(update={
        "transient_data": result.transient_data,
        "evidence": [*run.evidence, *result.evidence],
        "detail": _clip(f"{run.detail or ''}; transient: {result.detail or ''}"),
    })


def simulation_run_id(artifact: SchematicArtifact) -> str:
    """Stable per artifact, so the same schematic names the same run."""
    return hashlib.sha256(f"{artifact.fingerprint.digest}:ngspice-op".encode()).hexdigest()[:16]


def operating_point_for(artifact: SchematicArtifact, *, exporter: KiCadNetlistExporter | None = None,
                        spice: NgspiceAdapter | None = None,
                        work_dir: Path | None = None, transient: bool = True,
                        tstep: str = DEFAULT_TSTEP, tstop: str = DEFAULT_TSTOP,
                        stimulus: bool = False) -> SimulationRun:
    """Export and simulate one compiled schematic, degrading instead of raising.

    Availability is checked before anything is exported. Without ngspice there
    is nothing that could read a netlist, so spending a subprocess writing one
    would buy a file nobody can use.

    A transient runs beside the operating point, and only when it would mean
    something: after the DC solution succeeded, and only if the deck has a
    source to drive it. A curve of an undriven circuit is a flat line at zero,
    and drawing one would be the simulation equivalent of a fabricated pass.
    The transient never changes the operating point's verdict -- it is a second
    observation attached to the first, and a transient that fails leaves a
    successful operating point exactly as successful as it was.
    """
    run_id = simulation_run_id(artifact)
    spice = spice or NgspiceAdapter()
    available = spice.availability()
    if available.status is not ToolStatus.OK:
        return _not_run(
            run_id,
            available.status if available.status is ToolStatus.UNAVAILABLE else ToolStatus.FAILED,
            IDEAL_COMPONENTS,
            _clip(available.detail or _NGSPICE_MISSING),
        )
    destination = None if work_dir is None else work_dir / f"{run_id}.cir"
    try:
        export = (exporter or KiCadNetlistExporter()).export(artifact, destination)
        if not export.usable:
            return _not_run(
                run_id,
                export.status if export.status in {ToolStatus.UNAVAILABLE, ToolStatus.TIMED_OUT}
                else ToolStatus.FAILED,
                IDEAL_COMPONENTS,
                _clip(export.detail or "no SPICE netlist was exported"),
            )
        # The operating point always uses the netlist as exported. A stimulus
        # may only ever reach the transient: a DC solution computed from a deck
        # Ohmni altered would be a solution to a circuit nobody drew.
        run = spice.operating_point(export.text, run_id, work_dir=work_dir)
        return _with_transient(run, export.text, spice, run_id, work_dir,
                               transient, tstep, tstop, stimulus)
    except Exception as exc:  # noqa: BLE001 - corroboration never fails a design
        # The deterministic verdict already stands without this. An unexpected
        # failure in an optional external tool is recorded, not propagated.
        return _not_run(run_id, ToolStatus.FAILED, IDEAL_COMPONENTS,
                        _clip(f"the simulation boundary failed with {type(exc).__name__}"))


__all__ = [
    "BEHAVIOURAL_APPROXIMATION",
    "DEFAULT_TSTEP",
    "DEFAULT_TSTOP",
    "IDEAL_COMPONENTS",
    "MAX_TRANSIENT_SAMPLES",
    "MAX_TRANSIENT_SIGNALS",
    "OPERATING_POINT",
    "STIMULUS_NET",
    "STIMULUS_REFERENCE",
    "KiCadNetlistExporter",
    "NgspiceAdapter",
    "SpiceNetlist",
    "describe_netlist",
    "has_independent_source",
    "model_fidelity",
    "netlist_nodes",
    "operating_point_deck",
    "operating_point_for",
    "parse_operating_point",
    "parse_transient",
    "simulation_run_id",
    "transient_deck",
    "with_power_on_stimulus",
]
