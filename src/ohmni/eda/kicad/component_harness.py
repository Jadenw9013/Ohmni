"""Bounded KiCad corroboration for generated component assets.

KiCad is an independent verifier here, exactly as it is for schematic ERC and
board DRC. It is asked to load the emitted library and render it; if it cannot,
that is a failure of the asset. If KiCad is absent, crashes or times out, the
result is ``UNAVAILABLE`` or ``FAILED`` -- never a pass. An empty SVG or a
missing output file is a failure too: a tool that reported success while writing
nothing has not corroborated anything.

Rendering is corroboration, not verification. A picture proves KiCad accepted
the syntax and could place the primitives; it proves nothing about whether the
geometry matches the datasheet. That is what
:mod:`ohmni.physical.component_asset_verifier` is for.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from ...adapters import ToolStatus
from ...adapters.process import ToolProcessError, ToolTimeoutError, describe_exit, run_tool
from ...adapters.tools import find_kicad_cli

#: Bounded: an asset export is a small, local operation.
EXPORT_TIMEOUT_SECONDS = 90
#: ERC and DRC over a one-component harness are small too, but they load more of
#: KiCad, so they get their own bound.
DESIGN_TIMEOUT_SECONDS = 180
GENERATOR_VERSION = "1.0.0"
NM_PER_MM = 1_000_000
HARNESS_UUID_NAMESPACE = uuid.UUID("1f0b4c9a-2d6e-5b71-8c3a-9e4d05f7a612")
#: An SVG shorter than this has no drawn content worth calling a render.
MIN_SVG_BYTES = 200


@dataclass(frozen=True)
class HarnessRun:
    """One native-tool run bound to the exact artifact it was given."""

    name: str
    status: ToolStatus
    artifact_sha256: str
    tool_version: str | None = None
    outputs: tuple[str, ...] = field(default=())
    output_sha256: tuple[str, ...] = field(default=())
    detail: str | None = None

    @property
    def corroborated(self) -> bool:
        return self.status is ToolStatus.OK


def _version(executable: str) -> str | None:
    try:
        completed = run_tool([executable, "--version"], timeout=EXPORT_TIMEOUT_SECONDS)
    except (OSError, ToolProcessError):
        return None
    if completed.returncode != 0:
        return None
    lines = (completed.stdout or completed.stderr).strip().splitlines()
    return lines[0][:100] if lines else None


def _is_drawn_svg(path: Path) -> bool:
    """Whether a file is an SVG that actually draws something.

    A tool that exits zero having written a stub, or having written nothing into
    a directory that already held an old render, has corroborated nothing. The
    check is deliberately structural rather than a size threshold.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if "<svg" not in text or "</svg>" not in text:
        return False
    return any(f"<{element}" in text for element in ("path", "rect", "circle", "polyline",
                                                     "polygon", "line", "text", "g "))


def _run(
    name: str, command: list[str], artifact: Path, expected: Path, executable: str,
    *, output_stem: str,
) -> HarnessRun:
    """Run one bounded export and accept only this run's own fresh output.

    Freshness is established three ways, because the audit showed that "the
    process exited zero" establishes none of them: the destination must hold no
    SVG before the run, every accepted file must be named for the artifact that
    was requested, and the input artifact must hash the same afterwards as it did
    before.
    """
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    version = _version(executable)
    preexisting = sorted(expected.glob("*.svg")) if expected.is_dir() else []
    if preexisting:
        return HarnessRun(
            name=name, status=ToolStatus.FAILED, artifact_sha256=digest, tool_version=version,
            detail=(
                f"the destination already contained {len(preexisting)} SVG file(s); an "
                "existing render cannot corroborate this run"
            ),
        )
    try:
        completed = run_tool(command, timeout=EXPORT_TIMEOUT_SECONDS)
    except ToolTimeoutError:
        return HarnessRun(name=name, status=ToolStatus.TIMED_OUT, artifact_sha256=digest,
                          tool_version=version,
                          detail=f"the export exceeded {EXPORT_TIMEOUT_SECONDS} s")
    except (OSError, ToolProcessError) as exc:
        return HarnessRun(name=name, status=ToolStatus.FAILED, artifact_sha256=digest,
                          tool_version=version, detail=f"{type(exc).__name__}: {exc}")
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()[:400]
        return HarnessRun(name=name, status=ToolStatus.FAILED, artifact_sha256=digest,
                          tool_version=version,
                          detail=f"{describe_exit(completed.returncode)}: {detail}")
    if not artifact.is_file() or hashlib.sha256(artifact.read_bytes()).hexdigest() != digest:
        return HarnessRun(name=name, status=ToolStatus.FAILED, artifact_sha256=digest,
                          tool_version=version,
                          detail="the input artifact changed while the tool was running")
    produced = sorted(expected.glob("*.svg")) if expected.is_dir() else []
    named = [path for path in produced if path.stem == output_stem
             or path.stem.startswith(f"{output_stem}_")]
    if not named:
        others = ", ".join(path.name for path in produced) or "nothing"
        return HarnessRun(
            name=name, status=ToolStatus.FAILED, artifact_sha256=digest, tool_version=version,
            detail=(
                f"the tool reported success but wrote no SVG named for {output_stem!r} "
                f"(found: {others})"
            ),
        )
    unusable = [
        path.name for path in named
        if path.stat().st_size < MIN_SVG_BYTES or not _is_drawn_svg(path)
    ]
    if unusable:
        return HarnessRun(
            name=name, status=ToolStatus.FAILED, artifact_sha256=digest, tool_version=version,
            detail=f"output is not a drawn SVG: {', '.join(unusable)}",
        )
    return HarnessRun(
        name=name, status=ToolStatus.OK, artifact_sha256=digest, tool_version=version,
        outputs=tuple(str(path) for path in named),
        output_sha256=tuple(
            hashlib.sha256(path.read_bytes()).hexdigest() for path in named
        ),
        detail=(completed.stdout or "").strip()[:200] or None,
    )


def export_footprint_svg(
    pretty_dir: Path, footprint_name: str, out_dir: Path, *, executable: str | None = None
) -> HarnessRun:
    """Ask KiCad to load and render one generated footprint."""
    artifact = pretty_dir / f"{footprint_name}.kicad_mod"
    tool = executable or find_kicad_cli()
    if tool is None:
        return HarnessRun(
            name="kicad-cli fp export svg", status=ToolStatus.UNAVAILABLE,
            artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
            detail="kicad-cli was not found; the corroboration gate did not run",
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    command = [
        tool, "fp", "export", "svg", "--output", str(out_dir),
        "--footprint", footprint_name, "--black-and-white", str(pretty_dir),
    ]
    return _run("kicad-cli fp export svg", command, artifact, out_dir, tool,
                output_stem=footprint_name)


def export_symbol_svg(
    library: Path, symbol_name: str, out_dir: Path, *, executable: str | None = None
) -> HarnessRun:
    """Ask KiCad to load and render one generated symbol."""
    tool = executable or find_kicad_cli()
    if tool is None:
        return HarnessRun(
            name="kicad-cli sym export svg", status=ToolStatus.UNAVAILABLE,
            artifact_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),
            detail="kicad-cli was not found; the corroboration gate did not run",
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    command = [
        tool, "sym", "export", "svg", "--output", str(out_dir),
        "--symbol", symbol_name, "--black-and-white", str(library),
    ]
    return _run("kicad-cli sym export svg", command, library, out_dir, tool,
                output_stem=symbol_name)


__all__ = [
    "ASSET_DEFECT_DRC_TYPES",
    "ASSET_DEFECT_ERC_TYPES",
    "DESIGN_TIMEOUT_SECONDS",
    "EXPORT_TIMEOUT_SECONDS",
    "MIN_SVG_BYTES",
    "DesignHarnessRun",
    "HarnessRun",
    "build_harness_pcb",
    "build_harness_schematic",
    "export_footprint_svg",
    "export_symbol_svg",
    "run_harness_drc",
    "run_harness_erc",
]


# ---------------------------------------------------------------------------
# Connected harness: ERC on a generated schematic, DRC on a generated board
# ---------------------------------------------------------------------------
#
# COMPONENT_SYNTHESIS_PLAN.md's CS-KICAD criterion asks for more than a library
# render. It asks KiCad to load the generated assets *in a design* and report on
# them, because a symbol that plots correctly can still be rejected by ERC and a
# footprint that plots correctly can still be malformed to DRC.
#
# What this establishes is narrow and stated: KiCad parsed the generated symbol
# and footprint inside a real schematic and a real board, and reported no
# violation of the classes that indicate a malformed asset. It does not
# establish that the design works. The harness design is deliberately trivial --
# one component, labelled pins, a rectangular outline -- so that any violation
# is attributable to the asset rather than to the harness.

HARNESS_FORMAT_SCHEMATIC = "20250114"
HARNESS_FORMAT_PCB = "20240108"
#: Violation types that mean "this asset is malformed", as opposed to "this
#: trivial harness design is incomplete". Unconnected pins and missing power
#: flags are expected here and are recorded, not hidden.
ASSET_DEFECT_ERC_TYPES = frozenset({
    "lib_symbol_issues", "lib_symbol_mismatch", "extra_units", "duplicate_reference",
    "malformed_symbol", "unresolved_variable",
})
ASSET_DEFECT_DRC_TYPES = frozenset({
    "malformed_courtyard", "footprint_type_mismatch", "lib_footprint_issues",
    "lib_footprint_mismatch", "invalid_outline", "duplicate_footprints",
    "courtyards_overlap", "padstack", "shorting_items",
})


@dataclass(frozen=True)
class DesignHarnessRun:
    """One ERC or DRC run over a design built from the generated assets."""

    name: str
    status: ToolStatus
    design_sha256: str
    asset_sha256: str
    tool_version: str | None = None
    report_path: str | None = None
    report_sha256: str | None = None
    violation_counts: tuple[tuple[str, int], ...] = field(default=())
    asset_defects: tuple[str, ...] = field(default=())
    detail: str | None = None

    @property
    def corroborated(self) -> bool:
        """The tool ran, loaded the design, and found no asset-defect class."""
        return self.status is ToolStatus.OK and not self.asset_defects


def _symbol_body(symbol_text: str, symbol_name: str) -> str:
    """Lift the (symbol "<name>" ...) block out of a generated library.

    The schematic embeds the same bytes the library published, so ERC is reading
    the artifact under test rather than a re-serialisation of it.
    """
    marker = f'(symbol "{symbol_name}"'
    start = symbol_text.find(marker)
    if start < 0:
        raise ValueError(f"{symbol_name!r} is not in the generated library")
    depth = 0
    for index in range(start, len(symbol_text)):
        if symbol_text[index] == "(":
            depth += 1
        elif symbol_text[index] == ")":
            depth -= 1
            if depth == 0:
                return symbol_text[start:index + 1]
    raise ValueError("the generated symbol block is unbalanced")


def build_harness_schematic(
    symbol_text: str, symbol_name: str, pins: Sequence[tuple[str, int, int]],
    destination: Path,
) -> str:
    """Write a one-component schematic that uses the generated symbol.

    Every pin gets a global label, so the design is complete enough that any
    remaining ERC violation is about the symbol rather than about dangling wires.
    ``pins`` carries (number, x_nm, y_nm) in the symbol's own frame.
    """
    body = _symbol_body(symbol_text, symbol_name)
    embedded = body.replace(f'(symbol "{symbol_name}"', f'(symbol "ohmni:{symbol_name}"', 1)
    # On the 2.54 mm grid: an off-grid instance puts every pin off grid too,
    # and the resulting ERC violation would be about the harness.
    origin_x, origin_y = 101.6, 101.6
    lines = [
        "(kicad_sch",
        f"\t(version {HARNESS_FORMAT_SCHEMATIC})",
        '\t(generator "ohmni-component-harness")',
        f'\t(generator_version "{GENERATOR_VERSION}")',
        f'\t(uuid "{_stable_uuid(symbol_name, "sheet")}")',
        '\t(paper "A4")',
        "\t(lib_symbols",
        embedded,
        "\t)",
        "\t(symbol",
        f'\t\t(lib_id "ohmni:{symbol_name}")',
        f"\t\t(at {origin_x} {origin_y} 0)",
        "\t\t(unit 1)",
        "\t\t(exclude_from_sim yes)",
        "\t\t(in_bom yes)",
        "\t\t(on_board yes)",
        "\t\t(dnp no)",
        f'\t\t(uuid "{_stable_uuid(symbol_name, "instance")}")',
        f'\t\t(property "Reference" "U1" (at {origin_x} {origin_y - 12.7} 0))',
        f'\t\t(property "Value" "{symbol_name}" (at {origin_x} {origin_y - 10.16} 0))',
    ]
    for number, _, _ in pins:
        lines.append(f'\t\t(pin "{number}" (uuid "{_stable_uuid(symbol_name, "pin" + number)}"))')
    lines.append(
        '\t\t(instances (project "ohmni_component_harness" '
        f'(path "/{_stable_uuid(symbol_name, "sheet")}" (reference "U1") (unit 1))))'
    )
    lines.append("\t)")
    for number, x_nm, y_nm in pins:
        x = origin_x + x_nm / NM_PER_MM
        y = origin_y - y_nm / NM_PER_MM
        angle = 0 if x_nm < 0 else 180
        lines.append(
            f'\t(global_label "HARNESS_NET_{number}" (shape bidirectional) '
            f"(at {x} {y} {angle}) "
            f'(uuid "{_stable_uuid(symbol_name, "label" + number)}"))'
        )
    lines += ['\t(sheet_instances (path "/" (page "1")))', "\t(embedded_fonts no)", ")", ""]
    payload = "\n".join(lines)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload.encode("utf-8"))
    # A project-local library table beside the schematic, never the user's global
    # one. Without it KiCad reports that the 'ohmni' library is not in the
    # configuration, which wears the same violation type as a real symbol/library
    # mismatch. Shipping the table removes the ambiguity instead of teaching the
    # classifier to ignore that type.
    library = destination.parent / f"{destination.stem}.kicad_sym"
    library.write_bytes(symbol_text.encode("utf-8"))
    # KIPRJMOD resolves against a project file, so the harness ships one.
    (destination.parent / f"{destination.stem}.kicad_pro").write_bytes(
        json.dumps({
            "board": {"design_settings": {}},
            "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
            "meta": {"filename": f"{destination.stem}.kicad_pro", "version": 1},
            "schematic": {},
            "sheets": [],
        }, indent=2).encode("utf-8")
    )
    (destination.parent / "sym-lib-table").write_bytes(
        (
            "(sym_lib_table\n\t(version 7)\n"
            f'\t(lib (name "ohmni")(type "KiCad")(uri "${{KIPRJMOD}}/{library.name}")'
            '(options "")(descr "Ohmni generated component under test"))\n)\n'
        ).encode()
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_harness_pcb(footprint_text: str, footprint_name: str, destination: Path) -> str:
    """Write a one-footprint board that embeds the generated footprint bytes."""
    body = footprint_text.strip()
    if not body.startswith("(footprint"):
        raise ValueError("the generated footprint is not a (footprint ...) form")
    placed = body.replace(
        "(footprint " + f'"{footprint_name}"',
        f'(footprint "{footprint_name}"\n\t\t(at 50 50)\n\t\t(uuid '
        f'"{_stable_uuid(footprint_name, "fp")}")',
        1,
    )
    indented = "\n".join("\t" + line if line else line for line in placed.splitlines())
    lines = [
        "(kicad_pcb",
        f"\t(version {HARNESS_FORMAT_PCB})",
        '\t(generator "ohmni-component-harness")',
        f'\t(generator_version "{GENERATOR_VERSION}")',
        "\t(general (thickness 1.6) (legacy_teardrops no))",
        '\t(paper "A4")',
        "\t(layers",
        '\t\t(0 "F.Cu" signal)',
        '\t\t(31 "B.Cu" signal)',
        '\t\t(36 "B.SilkS" user "B.Silkscreen")',
        '\t\t(37 "F.SilkS" user "F.Silkscreen")',
        '\t\t(38 "B.Mask" user)',
        '\t\t(39 "F.Mask" user)',
        '\t\t(34 "B.Paste" user)',
        '\t\t(35 "F.Paste" user)',
        '\t\t(44 "Edge.Cuts" user)',
        '\t\t(41 "B.CrtYd" user "B.Courtyard")',
        '\t\t(40 "F.CrtYd" user "F.Courtyard")',
        '\t\t(42 "B.Fab" user)',
        '\t\t(43 "F.Fab" user)',
        "\t)",
        "\t(setup (pad_to_mask_clearance 0))",
    ]
    for start, end in (((40, 40), (60, 40)), ((60, 40), (60, 60)),
                       ((60, 60), (40, 60)), ((40, 60), (40, 40))):
        lines.append(
            f"\t(gr_line (start {start[0]} {start[1]}) (end {end[0]} {end[1]}) "
            '(stroke (width 0.1) (type solid)) (layer "Edge.Cuts") '
            f'(uuid "{_stable_uuid(footprint_name, f"edge{start}{end}")}"))'
        )
    lines.append(indented)
    lines += [")", ""]
    payload = "\n".join(lines)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload.encode("utf-8"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _stable_uuid(seed: str, role: str) -> str:
    return str(uuid.uuid5(HARNESS_UUID_NAMESPACE, f"{seed}:{role}"))


def _design_run(
    name: str, command: list[str], design: Path, report_path: Path, asset_sha256: str,
    executable: str, *, defect_types: frozenset[str], reader,
) -> DesignHarnessRun:
    design_digest = hashlib.sha256(design.read_bytes()).hexdigest()
    version = _version(executable)
    if report_path.exists():
        report_path.unlink()
    try:
        completed = run_tool(command, timeout=DESIGN_TIMEOUT_SECONDS)
    except ToolTimeoutError:
        return DesignHarnessRun(name=name, status=ToolStatus.TIMED_OUT,
                                design_sha256=design_digest, asset_sha256=asset_sha256,
                                tool_version=version,
                                detail=f"exceeded {DESIGN_TIMEOUT_SECONDS} s")
    except (OSError, ToolProcessError) as exc:
        return DesignHarnessRun(name=name, status=ToolStatus.FAILED,
                                design_sha256=design_digest, asset_sha256=asset_sha256,
                                tool_version=version, detail=f"{type(exc).__name__}: {exc}")
    # KiCad returns 5 when it completed and found violations; anything else is a
    # run that did not produce a usable report.
    if completed.returncode not in (0, 5):
        detail = (completed.stderr or completed.stdout).strip()[:400]
        return DesignHarnessRun(name=name, status=ToolStatus.FAILED,
                                design_sha256=design_digest, asset_sha256=asset_sha256,
                                tool_version=version,
                                detail=f"{describe_exit(completed.returncode)}: {detail}")
    if not report_path.is_file():
        return DesignHarnessRun(name=name, status=ToolStatus.FAILED,
                                design_sha256=design_digest, asset_sha256=asset_sha256,
                                tool_version=version,
                                detail="the tool reported completion but wrote no report")
    raw = report_path.read_bytes()
    try:
        counts, defects = reader(raw, defect_types)
    except (ValueError, KeyError, TypeError) as exc:
        return DesignHarnessRun(name=name, status=ToolStatus.FAILED,
                                design_sha256=design_digest, asset_sha256=asset_sha256,
                                tool_version=version,
                                detail=f"unreadable report: {exc}")
    if hashlib.sha256(design.read_bytes()).hexdigest() != design_digest:
        return DesignHarnessRun(name=name, status=ToolStatus.FAILED,
                                design_sha256=design_digest, asset_sha256=asset_sha256,
                                tool_version=version,
                                detail="the design changed while the tool was running")
    return DesignHarnessRun(
        name=name, status=ToolStatus.OK, design_sha256=design_digest,
        asset_sha256=asset_sha256, tool_version=version,
        report_path=str(report_path), report_sha256=hashlib.sha256(raw).hexdigest(),
        violation_counts=counts, asset_defects=defects,
    )


def _read_violations(raw: bytes, defect_types: frozenset[str]):
    report = json.loads(raw.decode("utf-8"))
    counts: dict[str, int] = {}
    defects: set[str] = set()
    for container in ("violations", "sheets"):
        entries = report.get(container) or []
        for entry in entries:
            items = entry.get("violations", []) if container == "sheets" else [entry]
            for item in items:
                kind = str(item.get("type", "unknown"))
                counts[kind] = counts.get(kind, 0) + 1
                # No message-based exemptions. The harness ships its own project
                # and library table, so "the library is not in your
                # configuration" cannot arise here -- and an exemption that is
                # never needed is just a hole waiting for a real defect to fall
                # through.
                if kind in defect_types:
                    defects.add(kind)
    return tuple(sorted(counts.items())), tuple(sorted(defects))


def run_harness_erc(
    schematic: Path, asset_sha256: str, *, executable: str | None = None
) -> DesignHarnessRun:
    """Run KiCad ERC over a schematic built from the generated symbol."""
    tool = executable or find_kicad_cli()
    if tool is None:
        return DesignHarnessRun(
            name="kicad-cli sch erc", status=ToolStatus.UNAVAILABLE,
            design_sha256=hashlib.sha256(schematic.read_bytes()).hexdigest(),
            asset_sha256=asset_sha256,
            detail="kicad-cli was not found; the connected ERC gate did not run",
        )
    report_path = schematic.with_suffix(".erc.json")
    command = [
        tool, "sch", "erc", "--format", "json", "--severity-all",
        "--exit-code-violations", "--output", str(report_path), str(schematic),
    ]
    return _design_run("kicad-cli sch erc", command, schematic, report_path, asset_sha256, tool,
                       defect_types=ASSET_DEFECT_ERC_TYPES, reader=_read_violations)


def run_harness_drc(
    board: Path, asset_sha256: str, *, executable: str | None = None
) -> DesignHarnessRun:
    """Run KiCad DRC over a board built from the generated footprint."""
    tool = executable or find_kicad_cli()
    if tool is None:
        return DesignHarnessRun(
            name="kicad-cli pcb drc", status=ToolStatus.UNAVAILABLE,
            design_sha256=hashlib.sha256(board.read_bytes()).hexdigest(),
            asset_sha256=asset_sha256,
            detail="kicad-cli was not found; the connected DRC gate did not run",
        )
    report_path = board.with_suffix(".drc.json")
    command = [
        tool, "pcb", "drc", "--format", "json", "--severity-all",
        "--exit-code-violations", "--output", str(report_path), str(board),
    ]
    return _design_run("kicad-cli pcb drc", command, board, report_path, asset_sha256, tool,
                       defect_types=ASSET_DEFECT_DRC_TYPES, reader=_read_violations)
