"""Run locked author benches through the existing Ohmni ngspice adapter."""

from __future__ import annotations

import math
import re
from pathlib import Path

from .audit import AuditError, _atomic_json, _atomic_text, _now, _sha_bytes

SCALAR = re.compile(r"^\s*(\S+)\s*=\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*$", re.MULTILINE)


def scalars(output: str) -> dict[str, float]:
    values = {}
    duplicate = set()
    for name, number in SCALAR.findall(output):
        name = name.casefold()
        if name in values:
            duplicate.add(name)
        value = float(number)
        if math.isfinite(value):
            values[name] = value
    return {key: value for key, value in values.items() if key not in duplicate}


def numeric_contract(item: dict) -> dict:
    value, tolerance = item.get("value"), item.get("tolerance")
    try:
        value = float(value)
        if isinstance(tolerance, str) and tolerance.endswith("%"):
            tolerance = abs(value) * float(tolerance[:-1]) / 100
        else:
            tolerance = float(tolerance)
    except (ValueError, TypeError):
        return {"expected": None, "tolerance": None}
    return {"expected": value, "tolerance": tolerance}


def inline_deck(path: Path, boundary: Path, seen: tuple[Path, ...] = ()) -> str:
    path = path.resolve()
    if boundary.resolve() not in path.parents or path in seen:
        raise AuditError(f"include escapes bench directory or cycles: {path}")
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*\.(?:include|inc)\s+(.+?)\s*$", line, re.IGNORECASE)
        if match:
            target = path.parent / match.group(1).strip('"\'')
            lines.append(inline_deck(target, boundary, (*seen, path)))
        else:
            lines.append(line)
    return "\n".join(lines)+"\n"


def run_benches(audit, ids: list[str] | None = None):
    from ohmni.eda.simulation import NgspiceAdapter

    state = audit._state()
    contracts = state["bench_contracts"]
    selected = ids or sorted(contracts)
    adapter = NgspiceAdapter()
    receipts = []
    for identity in selected:
        if identity not in contracts:
            raise AuditError(f"unknown benchmark {identity}")
        contract = contracts[identity]
        slug = identity.replace("/", "--")
        folder = audit.run_dir / "bench-output" / slug
        folder.mkdir(parents=True, exist_ok=True)
        try:
            deck = inline_deck(audit.root / contract["file"], audit.root / "docs/behavior/bench")
            observation = adapter.behavior_bench(deck, work_dir=folder)
        except (AuditError, OSError) as exc:
            observation = {"status": "not_run", "stderr": str(exc), "stdout": "", "version_output": ""}
        output = observation["stdout"] + "\n" + observation["stderr"]
        version = observation["version_output"]
        output_path, version_path = folder / "output.txt", folder / "version.txt"
        _atomic_text(output_path, output)
        _atomic_text(version_path, version)
        values = scalars(observation["stdout"])
        comparisons = []
        expected = contract["expected"]
        if isinstance(expected, list):
            for item in expected:
                if isinstance(item, dict):
                    comparisons.append(dict(numeric_contract(item), measure=item.get("measure"), measured=values.get(str(item.get("measure")).casefold())))
        record = {
            "bench_id": identity, "run_id": state["run_id"], "timestamp": _now(),
            "run_status": "passed" if observation["status"] == "ran" else observation["status"],
            "ngspice_version": version,
            "product_code_path": observation.get("product_code_path") == "ohmni.eda.simulation.NgspiceAdapter.behavior_bench",
            "netlist_sha256": contract["netlist_sha256"],
            "output_file": output_path.relative_to(audit.run_dir).as_posix(),
            "output_sha256": _sha_bytes(output.encode()),
            "version_file": version_path.relative_to(audit.run_dir).as_posix(),
            "version_sha256": _sha_bytes(version.encode()), "comparisons": comparisons,
        }
        errors = audit._bench_errors(record)
        if errors and record["run_status"] == "passed":
            record["run_status"] = "failed"
        record["errors"] = errors
        _atomic_json(audit.run_dir / "bench-results" / f"{slug}.json", record)
        receipts.append({"bench_id": identity, "status": record["run_status"]})
    return receipts
