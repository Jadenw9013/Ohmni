"""Real availability probes for external tools.

KiCad emission/ERC is implemented in :mod:`ohmni.eda.kicad`; simulation remains
behind spike S2.

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
from .process import describe_exit, run_tool

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
        completed = run_tool([executable, "--version"], timeout=_PROBE_TIMEOUT_SECONDS)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        return False, f"{describe_exit(completed.returncode)}: {detail}"[:200]
    lines = (completed.stdout or completed.stderr).strip().splitlines()
    if not lines:
        return False, "Tool returned no version information."
    return True, lines[0][:100]


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
    """Legacy availability facade retained for the original adapter protocol.

    Fingerprinted compilation and ERC use ``ohmni.eda.kicad``. The older path-only
    protocol cannot establish artifact integrity, so it deliberately remains
    unavailable rather than reporting an unsafe result.
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
                "Supports JSON schematic ERC and PCB DRC. Ohmni schematic emission "
                "and ERC are available through `compile-schematic`, `erc`, and `verify --eda`."
            ),
        )

    def emit_project(self, circuit, catalog, out_dir: Path) -> Path:
        raise NotImplementedError(
            "use KiCadSchematicCompiler.compile(), which returns a fingerprinted artifact"
        )

    def run_erc(self, schematic_path: Path) -> ErcRun:
        available = self.availability()
        return ErcRun(
            status=ToolStatus.UNAVAILABLE,
            run_id="erc-not-implemented",
            findings=[],
            tool_version=available.version,
            detail=(
                "the legacy path-only API cannot bind ERC to an artifact fingerprint; "
                "use ohmni.eda.kicad.KiCadCliAdapter with SchematicArtifact"
            ),
        )


def find_ngspice() -> str | None:
    return shutil.which("ngspice")


#: An explicit path to the Freerouting executable or its jar. Freerouting ships
#: as a Java application with no standard install location, so discovery cannot
#: be as simple as the other two tools.
FREEROUTING_ENV_VAR = "OHMNI_FREEROUTING"


def find_freerouting() -> str | None:
    """Locate Freerouting: a configured path, then PATH, then usual installs."""
    configured = os.environ.get(FREEROUTING_ENV_VAR, "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        return str(candidate) if candidate.is_file() else None
    if found := shutil.which("freerouting"):
        return found
    for base in _FREEROUTING_FALLBACK_DIRS:
        if not base.is_dir():
            continue
        for pattern in ("freerouting.jar", "freerouting.exe", "freerouting"):
            for candidate in sorted(base.glob(pattern), reverse=True):
                if candidate.is_file():
                    return str(candidate)
    return None


_FREEROUTING_FALLBACK_DIRS = (
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "freerouting",
    Path("C:/Program Files/freerouting"),
    Path("/usr/local/share/freerouting"),
    Path("/opt/freerouting"),
)


class FreeroutingCli:
    """Availability of the Freerouting autorouter.

    Deliberately does not execute the tool to answer. Freerouting is a Java
    application whose start-up is slow and whose version flag is not stable
    across releases, so a probe that ran it would be both expensive and prone
    to reporting FAILED for a working install. The detail says exactly that, so
    an OK here is never read as "this has been shown to run".
    """

    name = "freerouting"

    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable if executable is not None else find_freerouting()

    def availability(self) -> ToolAvailability:
        if self.executable is None:
            return ToolAvailability(
                name=self.name,
                status=ToolStatus.UNAVAILABLE,
                detail=(
                    "Freerouting was not found on PATH or in the usual install locations. "
                    f"Set {FREEROUTING_ENV_VAR} to its executable or jar. Ohmni routes with "
                    "its own deterministic router; this tool is not required."
                ),
            )
        needs_java = self.executable.lower().endswith(".jar")
        if needs_java and shutil.which("java") is None:
            return ToolAvailability(
                name=self.name, status=ToolStatus.UNAVAILABLE, executable=self.executable,
                detail="Freerouting is a jar and no java runtime was found to run it.",
            )
        return ToolAvailability(
            name=self.name, status=ToolStatus.OK, executable=self.executable,
            detail=("Found but not executed at probe time; Freerouting consumes a Specctra "
                    "DSN, which Ohmni does not export today."),
        )


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
            detail=(
                "Supports batch operating-point analysis through "
                "ohmni.eda.simulation.NgspiceAdapter."
            ),
        )

    def operating_point(self, netlist: str, run_id: str):
        from .fakes import UnavailableSpice

        return UnavailableSpice().operating_point(netlist, run_id)


def probe_all() -> list[ToolAvailability]:
    """Everything the system would like to use, and whether it can."""
    return [KicadCli().availability(), NgspiceCli().availability(),
            FreeroutingCli().availability()]


__all__ = [
    "FREEROUTING_ENV_VAR",
    "FreeroutingCli",
    "KicadCli",
    "NgspiceCli",
    "find_freerouting",
    "find_kicad_cli",
    "find_kicad_ngspice_library",
    "find_ngspice",
    "probe_all",
]
