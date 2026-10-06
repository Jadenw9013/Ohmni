"""Run locked author benches through the existing Ohmni ngspice adapter."""

from __future__ import annotations

import math
import re
from pathlib import Path

from .audit import AuditError, _atomic_json, _atomic_text, _now, _sha_bytes

NUMBER = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
# .meas adds an interval or crossing time after the numeric observation.
SCALAR = re.compile(
    rf"^\s*(\S+)\s*=\s*({NUMBER})(?:\s+(?:(?:from|to|at|trig|targ)\s*=\s*{NUMBER}\s*)+)?\s*$",
    re.MULTILINE | re.IGNORECASE,
)


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
        if isinstance(tolerance, str) and tolerance.strip() == "exact":
            tolerance = 0.0
        elif isinstance(tolerance, str) and re.fullmatch(r"\s*[\d.]+\s*(?:%|percent)\s*", tolerance):
            percentage = re.sub(r"(?:%|percent)\s*$", "", tolerance).strip()
            tolerance = abs(value) * float(percentage) / 100
        elif isinstance(tolerance, str) and (unit := re.fullmatch(
            rf"\s*({NUMBER})\s+(mV|V|ohm|C|ns|us|ms|s)\s*", tolerance
        )):
            tolerance = float(unit[1]) * {"mV": 1e-3, "V": 1, "ohm": 1,
                                         "C": 1, "ns": 1e-9, "us": 1e-6,
                                         "ms": 1e-3, "s": 1}[unit[2]]
        else:
            tolerance = float(tolerance)
    except (ValueError, TypeError):
        return {"expected": None, "tolerance": None}
    return {"expected": value, "tolerance": tolerance}


COMPOUND = re.compile(rf"\s*{NUMBER}(?:\s*/\s*{NUMBER})+\s*")


def compound_contracts(item: dict) -> list[dict] | None:
    """Split a locked slash-separated value ("10/8/5/2") into locked sub-contracts.

    Each component keeps the locked tolerance text verbatim; nothing is inferred.
    """
    value = item.get("value")
    if not isinstance(value, str) or not COMPOUND.fullmatch(value):
        return None
    return [numeric_contract(dict(item, value=part.strip())) for part in value.split("/")]


def measurement_binding(audit, identity: str, item: dict) -> dict:
    """Resolve an explicit label-to-observation binding, never by numeric proximity."""
    import json

    path = audit.root / "tools/behavior_audit/measurement_bindings.json"
    mapping = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    source = mapping.get(identity)
    if source is None:
        return {"scalar": str(item.get("measure", "")).casefold(), "scale": 1.0}
    contract = audit._bench_contracts()[identity]
    if source["netlist_sha256"] != contract["netlist_sha256"]:
        raise AuditError(f"measurement binding has a different source deck: {identity}")
    row = source["measurements"].get(item.get("measure"))
    if row is None:
        return {"scalar": str(item.get("measure", "")).casefold(), "scale": 1.0}
    deck = (audit.root / contract["file"]).read_text(encoding="utf-8")
    if "components" in row:
        parts = compound_contracts(item)
        if parts is None or len(parts) != len(row["components"]):
            raise AuditError(f"component binding does not match the locked compound value: {identity}")
        components = []
        for part in row["components"]:
            if not part.get("source_line") or part["source_line"] not in deck.splitlines():
                raise AuditError(f"measurement binding does not relocate to its source line: {identity}")
            components.append(dict(part, scalar=part["scalar"].casefold(), scale=part.get("scale", 1.0)))
        return dict(row, components=components)
    if not row.get("source_line") or row["source_line"] not in deck.splitlines():
        raise AuditError(f"measurement binding does not relocate to its source line: {identity}")
    return dict(row, scalar=row["scalar"].casefold(), scale=row.get("scale", 1.0))


def observed_value(audit, identity: str, item: dict, output: str) -> float | list[float] | None:
    binding = measurement_binding(audit, identity, item)
    if "components" in binding:
        found = scalars(output)
        values = [found.get(part["scalar"]) for part in binding["components"]]
        if any(value is None for value in values):
            return None
        return [value * part["scale"] for value, part in zip(values, binding["components"], strict=True)]
    if "occurrence" in binding:
        values = [float(number) for name, number in SCALAR.findall(output)
                  if name.casefold() == binding["scalar"]]
        if len(values) != binding["occurrence_count"]:
            return None
        value = values[binding["occurrence"]]
    else:
        value = scalars(output).get(binding["scalar"])
    return value * binding["scale"] if value is not None else None


def inline_deck(path: Path, boundary: Path, seen: tuple[Path, ...] = (), relocations: dict | None = None) -> str:
    path = path.resolve()
    if boundary.resolve() not in path.parents or path in seen:
        raise AuditError(f"include escapes bench directory or cycles: {path}")
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*\.(?:include|inc)\s+(.+?)\s*$", line, re.IGNORECASE)
        if match:
            reference = match.group(1).strip('"\'')
            relocation = (relocations or {}).get(reference)
            if relocation:
                target = (boundary / relocation["relative_path"]).resolve()
                if boundary.resolve() not in target.parents:
                    raise AuditError(f"relocated include escapes bench directory: {reference}")
                if _sha_bytes(target.read_bytes()) != relocation["sha256"]:
                    raise AuditError(f"relocated include content changed: {reference}")
            else:
                target = path.parent / reference
            lines.append(inline_deck(target, boundary, (*seen, path), relocations))
        else:
            lines.append(line)
    return "\n".join(lines)+"\n"


def run_benches(audit, ids: list[str] | None = None):
    from ohmni.eda.simulation import NgspiceAdapter

    state = audit._state()
    contracts = audit._bench_contracts()
    selected = ids or sorted(contracts)
    adapter = NgspiceAdapter()
    import json
    relocations_path = audit.root / "tools/behavior_audit/include_relocations.json"
    relocations = json.loads(relocations_path.read_text()) if relocations_path.exists() else {}
    receipts = []
    for identity in selected:
        if identity not in contracts:
            raise AuditError(f"unknown benchmark {identity}")
        contract = contracts[identity]
        slug = identity.replace("/", "--")
        folder = audit.run_dir / "bench-output" / slug
        folder.mkdir(parents=True, exist_ok=True)
        try:
            deck = inline_deck(audit.root / contract["file"], audit.root / "docs/behavior/bench", relocations=relocations)
            observation = adapter.behavior_bench(deck, work_dir=folder)
        except (AuditError, OSError) as exc:
            observation = {"status": "not_run", "stderr": str(exc), "stdout": "", "version_output": ""}
        output = observation["stdout"] + "\n" + observation["stderr"]
        version = observation["version_output"]
        output_path, version_path = folder / "output.txt", folder / "version.txt"
        _atomic_text(output_path, output)
        _atomic_text(version_path, version)
        comparisons = []
        expected = contract["expected"]
        if isinstance(expected, list):
            for item in expected:
                if not isinstance(item, dict):
                    continue
                measured = observed_value(audit, identity, item, observation["stdout"])
                parts = compound_contracts(item)
                if isinstance(measured, list) and parts is not None:
                    comparisons.append({
                        "measure": item.get("measure"),
                        "components": [dict(part, measured=value) for part, value in zip(parts, measured, strict=True)],
                    })
                else:
                    comparisons.append(dict(numeric_contract(item), measure=item.get("measure"),
                                            measured=None if isinstance(measured, list) else measured))
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
            "execution_status": observation["status"],
            "returncode": observation.get("returncode"),
        }
        errors = audit._bench_errors(record)
        if errors and record["run_status"] == "passed":
            record["run_status"] = "failed"
        record["errors"] = errors
        _atomic_json(audit.run_dir / "bench-results" / f"{slug}.json", record)
        receipts.append({"bench_id": identity, "status": record["run_status"]})
    return receipts
