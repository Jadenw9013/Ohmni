"""The Freerouting autorouter, behind the :class:`~ohmni.adapters.Router` Protocol.

Ohmni already routes. :class:`~ohmni.routing.router.DeterministicRouter` produces
the copper on every board this project ships, ``verify_routing`` checks that
copper independently, and the compiled PCB is bound to the routing plan's
fingerprint before anything is released. This adapter is not a replacement for
that; it is the first half of an escape hatch for the boards the deterministic
search cannot finish, where today the run fails with ``RoutingIncompleteError``.

**It is not wired into the pipeline, and that is deliberate.** Two things have to
exist first, and neither is a detail:

* **Input.** Freerouting consumes a Specctra ``.dsn``. KiCad 10's ``kicad-cli pcb
  export`` offers 3dpdf, brep, drill, dxf, gencad, gerbers, glb, ipc2581,
  ipcd356, odb, pdf, ply, pos, ps, stats, step, stl, svg, u3d, vrml and xao --
  no Specctra. Exporting DSN is a GUI-only feature, so a pipeline that called
  this today would have nothing to hand it.
* **Verification.** A ``.ses`` file is copper Ohmni did not compute, and Ohmni's
  independent routing verification checks a ``RoutingPlan``, not a board. Laying
  foreign routes into a ``.kicad_pcb`` would produce released copper that
  ``verify_routing`` never saw -- corroboration replaced by trust, which is the
  one thing this codebase does not do (AGENTS.md). Reading a ``.ses`` back into a
  ``RoutingPlan``, so the existing verifier still decides, is the honest way in.

What this module does do is find the tool, say truthfully whether it could run,
and run it on a ``.dsn`` when handed one -- through the same bounded, shell-free
runner every other external tool uses (SECURITY.md).
"""

from __future__ import annotations

from pathlib import Path

from ..adapters import ToolAvailability, ToolStatus
from ..adapters.process import ToolTimeoutError, describe_exit, run_tool
from ..adapters.tools import FreeroutingCli, find_freerouting

#: Autorouting a prototype board is minutes, not seconds, but it is still bounded.
FREEROUTING_TIMEOUT_SECONDS = 600

#: What Freerouting reads. The extension is the contract: this adapter will not
#: hand it a file it cannot parse and call the result a routing failure.
DESIGN_SUFFIX = ".dsn"
SESSION_SUFFIX = ".ses"

_MAX_DETAIL_CHARS = 400


def _clip(text: str | None, limit: int = _MAX_DETAIL_CHARS) -> str:
    value = " ".join((text or "").split())
    return value if len(value) <= limit else value[: limit - 1] + "…"


class FreeroutingAdapter:
    """A :class:`~ohmni.adapters.Router` backed by the Freerouting CLI.

    Satisfies the Protocol exactly: ``availability`` says whether the tool could
    run, and ``route`` reports what happened as a :class:`ToolAvailability`. It
    never raises for a missing or failing tool, because an absent autorouter is
    a normal result here -- the deterministic router is the one that matters.
    """

    name = "freerouting"

    def __init__(self, executable: str | None = None, *,
                 timeout_seconds: float = FREEROUTING_TIMEOUT_SECONDS) -> None:
        self.executable = executable if executable is not None else find_freerouting()
        self.timeout_seconds = timeout_seconds

    def availability(self) -> ToolAvailability:
        return FreeroutingCli(self.executable).availability()

    def _command(self, design: Path, session: Path) -> list[str]:
        """Fixed argument vector. A jar is run by java; an executable directly."""
        if self.executable.lower().endswith(".jar"):
            return ["java", "-jar", self.executable, "-de", str(design), "-do", str(session)]
        return [self.executable, "-de", str(design), "-do", str(session)]

    def route(self, board_path: Path, out_dir: Path) -> ToolAvailability:
        """Autoroute one Specctra design, or say precisely why nothing was routed."""
        available = self.availability()
        if available.status is not ToolStatus.OK:
            return available
        design = Path(board_path)
        if design.suffix.lower() != DESIGN_SUFFIX:
            # Named rather than guessed: handing Freerouting a .kicad_pcb would
            # fail in a way that reads like a routing failure instead of the
            # missing export step it actually is.
            return ToolAvailability(
                name=self.name, status=ToolStatus.UNAVAILABLE, executable=self.executable,
                detail=(f"Freerouting reads a Specctra {DESIGN_SUFFIX}, and was given "
                        f"{design.suffix or 'a file with no suffix'}. KiCad 10 has no "
                        "Specctra export in kicad-cli, so Ohmni cannot produce one yet."),
            )
        if not design.is_file():
            return ToolAvailability(
                name=self.name, status=ToolStatus.FAILED, executable=self.executable,
                detail="the Specctra design to route does not exist",
            )
        session = Path(out_dir) / (design.stem + SESSION_SUFFIX)
        try:
            session.parent.mkdir(parents=True, exist_ok=True)
            completed = run_tool(self._command(design, session), timeout=self.timeout_seconds)
        except ToolTimeoutError:
            return ToolAvailability(
                name=self.name, status=ToolStatus.TIMED_OUT, executable=self.executable,
                detail=f"Freerouting exceeded {self.timeout_seconds}s and was stopped",
            )
        except OSError as exc:
            return ToolAvailability(
                name=self.name, status=ToolStatus.FAILED, executable=self.executable,
                detail=_clip(f"Freerouting could not run: {exc}"),
            )
        if completed.returncode != 0:
            return ToolAvailability(
                name=self.name, status=ToolStatus.FAILED, executable=self.executable,
                detail=_clip(f"Freerouting failed ({describe_exit(completed.returncode)}): "
                             f"{completed.stderr or completed.stdout}"),
            )
        if not session.is_file() or not session.stat().st_size:
            # A clean exit with no session is not a routed board.
            return ToolAvailability(
                name=self.name, status=ToolStatus.FAILED, executable=self.executable,
                detail="Freerouting reported success but wrote no routing session",
            )
        return ToolAvailability(
            name=self.name, status=ToolStatus.OK, executable=self.executable,
            detail=(f"wrote {session.name}. This session is not copper yet: reading it back "
                    "into a RoutingPlan is what would let Ohmni verify it."),
        )


__all__ = ["DESIGN_SUFFIX", "FREEROUTING_TIMEOUT_SECONDS", "SESSION_SUFFIX", "FreeroutingAdapter"]
