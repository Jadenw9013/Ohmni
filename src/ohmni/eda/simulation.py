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
from ..domain.units import Quantity, Unit
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


def transient_deck(netlist: str, tstep: str, tstop: str, signals: list[str]) -> str:
    """Add the transient command and the signals to print, and nothing else.

    Built the same way as the operating-point deck: the caller's first line
    stays first because a SPICE deck's first line is its title, existing
    commands are never duplicated, and the analysis goes in before `.end`.
    """
    lines = (netlist or "").splitlines()
    stripped = [line.strip() for line in lines]
    additions = []
    if not any(re.match(r"\.tran\b", line, re.IGNORECASE) for line in stripped):
        additions.append(f".tran {tstep} {tstop}")
    if not any(re.match(r"\.print\s+tran\b", line, re.IGNORECASE) for line in stripped):
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
    rows: list[list[float]] = []
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
            continue
        if not columns or _RULE_LINE.match(line):
            continue
        tokens = line.split()
        if len(tokens) != len(columns) + (1 if indexed else 0):
            continue
        if indexed:
            tokens = tokens[1:]
        try:
            values = [float(token) for token in tokens]
        except ValueError:
            continue
        rows.append(values)
    if not columns or not rows:
        return TransientData(analysis=analysis)
    total = len(rows)
    if total > limit:
        step = -(-total // limit)  # ceiling division keeps the last row reachable
        kept = rows[::step]
        if kept[-1] is not rows[-1]:
            kept.append(rows[-1])
        rows = kept
    series = []
    for position, name in enumerate(columns[1:], start=1):
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
        return NgspiceCli(self.executable).availability()

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
                    work_dir: Path | None, wanted: bool, tstep: str, tstop: str) -> SimulationRun:
    """Attach a time-domain result to a successful operating point, if one is owed."""
    analyse = getattr(spice, "transient_analysis", None)
    if (not wanted or run.status is not ToolStatus.OK or not callable(analyse)
            or not has_independent_source(netlist)):
        return run
    result = analyse(netlist, run_id, tstep, tstop, work_dir=work_dir)
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
                        tstep: str = DEFAULT_TSTEP,
                        tstop: str = DEFAULT_TSTOP) -> SimulationRun:
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
        run = spice.operating_point(export.text, run_id, work_dir=work_dir)
        return _with_transient(run, export.text, spice, run_id, work_dir,
                               transient, tstep, tstop)
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
]
