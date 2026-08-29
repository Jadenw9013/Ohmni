"""Real availability probes for the external tools.

Detection only. Emission, ERC and simulation are Phase 5 and 6 work behind
spikes S1 and S2; until those land, these adapters report what is actually on
the machine and return ``UNAVAILABLE`` for everything else.

That is the whole point of having them now: the difference between "ERC found
no violations" and "ERC never ran" has to be visible from the very first
version, not retrofitted once someone notices a report looked too clean.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from . import ErcRun, ToolAvailability, ToolStatus

#: Where KiCad puts kicad-cli on each platform. Checked after PATH.
_KICAD_FALLBACK_DIRS = (
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "KiCad",
    Path("C:/Program Files/KiCad"),
    Path("/Applications/KiCad/KiCad.app/Contents/MacOS"),
    Path("/usr/bin"),
    Path("/usr/local/bin"),
)

_PROBE_TIMEOUT_SECONDS = 20


def _run_version(executable: str) -> tuple[bool, str]:
    """Ask a tool for its version.

    Fixed argument vector, never a shell string. Nothing user-supplied reaches
    this function (SECURITY.md: no shell interpolation, argument arrays only).
    """
    try:
        completed = subprocess.run(  # noqa: S603 -- fixed argv, no shell
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    if completed.returncode != 0:
        return False, (completed.stderr or completed.stdout).strip()[:200]
    return True, (completed.stdout or completed.stderr).strip().splitlines()[0][:100]


def find_kicad_cli() -> str | None:
    """Locate kicad-cli on PATH, then in the usual install locations."""
    if found := shutil.which("kicad-cli"):
        return found
    for base in _KICAD_FALLBACK_DIRS:
        if not base.is_dir():
            continue
        for candidate in sorted(base.glob("*/bin/kicad-cli*"), reverse=True):
            if candidate.is_file():
                return str(candidate)
        for name in ("kicad-cli", "kicad-cli.exe"):
            candidate = base / name
            if candidate.is_file():
                return str(candidate)
    return None


class KicadCli:
    """Detects kicad-cli. Emission and ERC are not implemented yet.

    ``run_erc`` returns ``UNAVAILABLE`` rather than an empty pass even when the
    executable *is* present, because we have nothing to hand it yet. Reporting
    "no violations" for a check that never ran is the exact failure this
    product exists to prevent.
    """

    name = "kicad-cli"

    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable or find_kicad_cli()

    def availability(self) -> ToolAvailability:
        if self.executable is None:
            return ToolAvailability(
                name=self.name,
                status=ToolStatus.UNAVAILABLE,
                detail=(
                    "kicad-cli was not found on PATH or in the usual install locations. "
                    "Install KiCad 8 or newer for machine-readable ERC and DRC output."
                ),
            )
        ok, text = _run_version(self.executable)
        if not ok:
            return ToolAvailability(
                name=self.name,
                status=ToolStatus.FAILED,
                executable=self.executable,
                detail=text,
            )
        return ToolAvailability(
            name=self.name,
            status=ToolStatus.OK,
            version=text,
            executable=self.executable,
            detail=(
                "Supports `sch erc --format json` and `pcb drc --format json`. "
                "Schematic emission is not implemented yet (spike S1)."
            ),
        )

    def emit_project(self, circuit, catalog, out_dir: Path) -> Path:  # noqa: ANN001
        raise NotImplementedError(
            "Schematic emission is Phase 5 work; see spike S1 in PRE_IMPLEMENTATION_REVIEW.md"
        )

    def run_erc(self, schematic_path: Path) -> ErcRun:
        available = self.availability()
        return ErcRun(
            status=ToolStatus.UNAVAILABLE,
            run_id="erc-not-implemented",
            findings=[],
            tool_version=available.version,
            detail=(
                "ERC has not been wired up yet, so it did not run. An empty finding list "
                "here means 'not checked', not 'no violations'. The EDA subsystem stays "
                "UNSUPPORTED until spike S1 lands."
            ),
        )


def find_ngspice() -> str | None:
    return shutil.which("ngspice")


def find_kicad_ngspice_library() -> str | None:
    """KiCad bundles ngspice as a shared library rather than a CLI.

    Relevant to spike S2: on this platform the only ngspice present is
    ``ngspice.dll`` inside the KiCad install, which needs a shared-library
    binding rather than a subprocess.
    """
    cli = find_kicad_cli()
    if cli is None:
        return None
    bin_dir = Path(cli).parent
    for name in ("ngspice.dll", "libngspice.so", "libngspice.dylib", "libngspice.0.dylib"):
        candidate = bin_dir / name
        if candidate.is_file():
            return str(candidate)
    return None


class NgspiceCli:
    """Detects a standalone ngspice binary. Simulation is not implemented yet."""

    name = "ngspice"

    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable or find_ngspice()

    def availability(self) -> ToolAvailability:
        if self.executable is None:
            library = find_kicad_ngspice_library()
            detail = (
                "No standalone ngspice executable found."
            )
            if library:
                detail += (
                    f" KiCad ships ngspice as a shared library at {library}, which needs a "
                    "shared-library binding rather than a subprocess. See spike S2."
                )
            return ToolAvailability(
                name=self.name, status=ToolStatus.UNAVAILABLE, detail=detail
            )
        ok, text = _run_version(self.executable)
        if not ok:
            return ToolAvailability(
                name=self.name,
                status=ToolStatus.FAILED,
                executable=self.executable,
                detail=text,
            )
        return ToolAvailability(
            name=self.name,
            status=ToolStatus.OK,
            version=text,
            executable=self.executable,
            detail="Simulation is not implemented yet (spike S2).",
        )

    def operating_point(self, netlist: str, run_id: str):  # noqa: ANN201
        from .fakes import UnavailableSpice

        return UnavailableSpice().operating_point(netlist, run_id)


def probe_all() -> list[ToolAvailability]:
    """Everything the system would like to use, and whether it can."""
    return [KicadCli().availability(), NgspiceCli().availability()]


__all__ = [
    "KicadCli",
    "NgspiceCli",
    "find_kicad_cli",
    "find_kicad_ngspice_library",
    "find_ngspice",
    "probe_all",
]
