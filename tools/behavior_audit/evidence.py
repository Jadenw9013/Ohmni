"""Shared real-record and canary validators. All failures carry a rule ID."""

from __future__ import annotations

import math
import re
from pathlib import Path

RULE_SOURCE = "AUD-SOURCE-001"


def source_errors(urls: set[str], ledger: list[dict], run_dir: Path) -> list[str]:
    import hashlib

    good = set()
    for row in ledger:
        status = row.get("http_status")
        digest = row.get("content_sha256", "")
        if (
            type(status) is int and 200 <= status < 300
            and re.fullmatch(r"[0-9a-f]{64}", str(digest))
            and row.get("timestamp") and row.get("tool_used")
        ):
            blob = run_dir / "fetched-sources" / f"{digest}.bin"
            if blob.is_file() and hashlib.sha256(blob.read_bytes()).hexdigest() == digest:
                good.add(row.get("url"))
    return [f"{RULE_SOURCE}: missing successful archived fetch: {url}" for url in sorted(urls-good)]


def field_errors(field: dict, ledger: list[dict], run_dir: Path) -> list[str]:
    errors = []
    if not field.get("field") or "value" not in field:
        errors.append(f"{RULE_SOURCE}: field name/value missing")
    if not field.get("basis") or not field.get("confidence"):
        errors.append(f"{RULE_SOURCE}: field basis/confidence missing")
    sources = field.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{RULE_SOURCE}: no source for new field {field.get('field')}")
    else:
        errors.extend(source_errors(set(sources), ledger, run_dir))
    return errors


def version_42(text: str) -> bool:
    return re.search(r"\bngspice(?:[-\s]+version)?[-\s]+42(?:\D|$)", text, re.IGNORECASE) is not None


def comparison_errors(result: dict, contract: dict) -> list[str]:
    """Expected values and tolerances come from the locked contract, never results."""
    errors = []
    for key in ("expected", "tolerance"):
        if result.get(key) != contract.get(key):
            errors.append(f"AUD-BENCH-001: {key} differs from locked expectation")
    expected = contract.get("expected")
    tolerance = contract.get("tolerance")
    measured = result.get("measured")
    if not all(
        type(value) in (float, int) and math.isfinite(value)
        for value in (expected, tolerance, measured)
    ):
        errors.append("AUD-BENCH-001: missing/non-finite numeric comparison")
    elif tolerance < 0 or abs(measured-expected) > tolerance:
        errors.append(f"AUD-BENCH-001: measured={measured}, expected={expected}, tolerance={tolerance}")
    return errors


def bench_errors(result: dict, contract: dict) -> list[str]:
    errors = comparison_errors(result, contract)
    if result.get("run_status") != "passed":
        errors.append("AUD-BENCH-001: bench did not run successfully")
    if not version_42(str(result.get("ngspice_version", ""))):
        errors.append("AUD-BENCH-001: actual ngspice 42 version output missing")
    if result.get("product_code_path") is not True:
        errors.append("AUD-BENCH-001: bench bypassed product code")
    return errors


def upgrade_errors(evidence: dict | None, ledger: list[dict], run_dir: Path) -> list[str]:
    if not evidence:
        return ["AUD-UPGRADE-001: gapfill evidence missing"]
    errors = []
    updates = evidence.get("field_updates")
    if not isinstance(updates, list) or not updates:
        errors.append("AUD-UPGRADE-001: field_updates missing")
    else:
        for field in updates:
            errors.extend(field_errors(field, ledger, run_dir))
    # A bench reference is resolved by the audit against this run's archived result.
    if not evidence.get("bench_result"):
        errors.append("AUD-UPGRADE-001: current-run bench result missing")
    return errors


def led_errors(order: dict) -> list[str]:
    if order.get("catalog_to_package_terminal") != {"1": "2", "2": "1"}:
        return ["AUD-SPEC-001: approved LED permutation changed or removed"]
    if order.get("catalog_pin_roles") != {"1": "A", "2": "K"}:
        return ["AUD-SPEC-001: LED catalog polarity changed"]
    if order.get("package_terminal_roles") != {"1": "K", "2": "A"}:
        return ["AUD-SPEC-001: LED package polarity changed"]
    return []


def honesty_errors(claim: dict) -> list[str]:
    status = str(claim.get("simulation_status", "")).lower()
    display = str(claim.get("display_status", "")).lower()
    if status not in {"ok", "passed"} and display in {"pass", "passed", "success"}:
        return ["AUD-HONESTY-001: non-run/error/unknown displayed as pass"]
    if claim.get("rating_status") == "violation" and display != "violation":
        return ["AUD-HONESTY-001: rating violation not displayed as violation"]
    return []
