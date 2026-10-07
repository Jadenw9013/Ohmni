"""Machine-checkable audit and resumable checkpoint support for behavior work.

This module is repository tooling. It does not participate in Ohmni runtime
decisions and cannot turn research claims into product evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import evidence

_LEDGER_LOCK = threading.Lock()


class AuditError(RuntimeError):
    """The audit cannot establish a required invariant."""


@dataclass(frozen=True)
class CheckResult:
    rule_id: str
    passed: bool
    summary: str
    details: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _record_checkpoint_failure(state, identity, summary, limit):
    """Mandatory rechecks of a parked gate do not create more repair attempts."""
    previous = state["attempts"].get(identity, 0)
    observations = state.setdefault("failed_gate_observations", {})
    observations[identity] = observations.get(identity, previous) + 1
    if previous > limit:
        # Earlier checkpoints counted every observation as an attempt. Preserve
        # that history explicitly while enforcing the locked repair ceiling.
        state.setdefault("legacy_checkpoint_attempt_counts", {}).setdefault(identity, previous)
    attempt = min(previous + 1, limit)
    state["attempts"][identity] = attempt
    if attempt >= limit:
        state["blocked_entries"][identity] = (
            f"Parked at the {limit}-attempt ceiling; {observations[identity]} failed gate observations: {summary}"
        )
    return attempt


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot read JSON {path}: {exc}") from exc


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", delete=False, dir=path.parent
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", delete=False, dir=path.parent
    ) as handle:
        handle.write(value)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def _git(root: Path, *args: str, worktree: Path | None = None) -> str:
    completed = _run(["git", *args], worktree or root)
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise AuditError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout


def _command_tokens(command: str) -> list[str]:
    # Locked regression commands are deliberately simple and contain no shell syntax.
    return command.split()


def _entry_files(root: Path) -> list[Path]:
    return sorted((root / "src/ohmni/behavior/data/entries").glob("OHM-*.json"))


def _entries(root: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path in _entry_files(root):
        record = _json(path)
        entry_id = record.get("entry_id")
        if not isinstance(entry_id, str) or entry_id in records:
            raise AuditError(f"invalid or duplicate behavior entry in {path}")
        records[entry_id] = record
    return records


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)


URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")


def _normalise_url(value: str) -> str:
    value = value.rstrip(".,;]:")
    while value.endswith(")") and value.count(")") > value.count("("):
        value = value[:-1]
    return value


def _urls_in(value: Any) -> set[str]:
    if isinstance(value, dict):
        found = set()
        for key, child in value.items():
            if key == "url" and isinstance(child, str) and child.startswith(("http://", "https://")):
                found.add(child)
            else:
                found.update(_urls_in(child))
        return found
    if isinstance(value, list):
        return set().union(*(_urls_in(child) for child in value)) if value else set()
    found: set[str] = set()
    for text in _walk_strings(value):
        found.update(_normalise_url(item) for item in URL_PATTERN.findall(text))
    return found


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AuditError(f"invalid JSONL at {path}:{number}: {exc}") from exc
        if not isinstance(value, dict):
            raise AuditError(f"non-object JSONL row at {path}:{number}")
        rows.append(value)
    return rows


class BehaviorAudit:
    def __init__(self, root: Path, run_dir: Path | None = None) -> None:
        self.root = root.resolve()
        self.tool_dir = Path(__file__).resolve().parent
        self.rules_path = self.tool_dir / "rules.yaml"
        self.rules_doc_path = self.tool_dir / "RULES.md"
        self.fixtures_dir = self.tool_dir / "fixtures"
        self.run_dir = (run_dir or self.root / "out/component-behavior/run").resolve()
        self.state_path = self.run_dir / "STATE.json"
        self.rules = _json(self.rules_path)

    @property
    def rule_hash(self) -> str:
        payload = (
            b"RULES.md\0"
            + self.rules_doc_path.read_bytes()
            + b"\0rules.yaml\0"
            + self.rules_path.read_bytes()
        )
        return _sha_bytes(payload)

    def _state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            raise AuditError("run/STATE.json is missing; run init first")
        state = _json(self.state_path)
        if state.get("schema_version") != 1:
            raise AuditError("unsupported audit state schema")
        return state

    def bench_repins(self) -> dict[str, Any]:
        path = self.root / "docs/behavior/BENCH_REPINS.json"
        return _json(path) if path.exists() else {"schema_version": 1, "repins": []}

    def _apply_repins(self, locked: dict[str, dict], *, corrections: bool = True,
                      additions: bool = True) -> tuple[dict[str, dict], list[str]]:
        """Apply human-approved bench ledger entries in a fixed order.

        repins:      move only a locked deck hash (expected, tolerance, labels, file stay).
        corrections: replace a locked expected list; each entry must quote the exact
                     list it replaces and every new item must be numerically checkable.
        additions:   add a new bench identity that the baseline did not have.
        Every entry carries a recorded human approval; unapproved entries are refused.
        """
        from .benches import numeric_contract

        effective = {key: dict(value) for key, value in locked.items()}
        errors: list[str] = []
        ledger = self.bench_repins()
        seen_ids: set[str] = set()

        def approved(entry: dict) -> bool:
            entry_id = entry.get("id")
            if not entry_id or entry_id in seen_ids:
                errors.append(f"bench ledger entry has a missing or duplicate id: {entry_id}")
            seen_ids.add(entry_id)
            if not entry.get("approved_by") or not entry.get("approved_on"):
                errors.append(f"{entry_id}: bench ledger entry lacks a recorded human approval")
                return False
            return True

        def checkable(entry_id: str, bench_id: str, expected) -> bool:
            if not isinstance(expected, list) or not expected:
                errors.append(f"{entry_id}: {bench_id}: expected list missing")
                return False
            for item in expected:
                if (not isinstance(item, dict) or not item.get("measure") or not item.get("basis")
                        or numeric_contract(item)["expected"] is None):
                    errors.append(f"{entry_id}: {bench_id}: item is not numerically checkable or lacks a basis: {item}")
                    return False
            return True

        allowed = {"file", "baseline_netlist_sha256", "netlist_sha256", "reason"}
        for repin in ledger.get("repins", []):
            if not approved(repin):
                continue
            repin_id = repin["id"]
            for bench_id, row in repin.get("benches", {}).items():
                if bench_id not in effective:
                    errors.append(f"{repin_id}: unknown locked bench {bench_id}")
                    continue
                if set(row) - allowed:
                    errors.append(f"{repin_id}: {bench_id}: a re-pin may only move the deck hash")
                    continue
                if row.get("file") != effective[bench_id]["file"]:
                    errors.append(f"{repin_id}: {bench_id}: re-pin changes the locked file path")
                    continue
                if row.get("baseline_netlist_sha256") != effective[bench_id]["netlist_sha256"]:
                    errors.append(f"{repin_id}: {bench_id}: re-pin does not start from the locked deck hash")
                    continue
                if not re.fullmatch(r"[0-9a-f]{64}", str(row.get("netlist_sha256", ""))):
                    errors.append(f"{repin_id}: {bench_id}: re-pin target hash invalid")
                    continue
                effective[bench_id]["netlist_sha256"] = row["netlist_sha256"]
        if corrections:
            for correction in ledger.get("corrections", []):
                if not approved(correction):
                    continue
                correction_id = correction["id"]
                for bench_id, row in correction.get("benches", {}).items():
                    if bench_id not in effective:
                        errors.append(f"{correction_id}: unknown locked bench {bench_id}")
                        continue
                    if row.get("baseline_expected") != effective[bench_id]["expected"]:
                        errors.append(f"{correction_id}: {bench_id}: correction does not quote the locked expected list")
                        continue
                    if not row.get("derivation"):
                        errors.append(f"{correction_id}: {bench_id}: correction lacks a derivation")
                        continue
                    if not checkable(correction_id, bench_id, row.get("expected")):
                        continue
                    effective[bench_id]["expected"] = row["expected"]
        if additions:
            for addition in ledger.get("additions", []):
                if not approved(addition):
                    continue
                addition_id = addition["id"]
                for bench_id, row in addition.get("benches", {}).items():
                    if bench_id in effective:
                        errors.append(f"{addition_id}: {bench_id}: an addition cannot replace an existing bench")
                        continue
                    file = str(row.get("file", ""))
                    if not file.startswith("docs/behavior/bench/") or not file.endswith(".cir"):
                        errors.append(f"{addition_id}: {bench_id}: addition file must be an authored bench deck")
                        continue
                    if not re.fullmatch(r"[0-9a-f]{64}", str(row.get("netlist_sha256", ""))):
                        errors.append(f"{addition_id}: {bench_id}: addition hash invalid")
                        continue
                    if not row.get("derivation") or not checkable(addition_id, bench_id, row.get("expected")):
                        if not row.get("derivation"):
                            errors.append(f"{addition_id}: {bench_id}: addition lacks a derivation")
                        continue
                    effective[bench_id] = {"file": file, "expected": row["expected"],
                                           "netlist_sha256": row["netlist_sha256"]}
        return effective, errors

    def _bench_contracts(self, *, corrected: bool = True) -> dict[str, dict]:
        """Locked contracts with ledger entries applied.

        corrected=False applies only deck re-pins, so model/runtime receipts that
        parse the original spec expectation text keep reading exactly that text.
        """
        return self._apply_repins(self._state()["bench_contracts"],
                                  corrections=corrected, additions=corrected)[0]

    def _write_state(self, state: dict[str, Any]) -> None:
        state["heartbeat_time"] = _now()
        _atomic_json(self.state_path, state)

    def _protected_snapshot(self) -> dict[str, Any]:
        main_ref = _git(self.root, "rev-parse", "refs/heads/main").strip()
        remote_refs = _git(
            self.root, "for-each-ref", "--format=%(refname) %(objectname)", "refs/remotes"
        )
        worktrees = _git(self.root, "worktree", "list", "--porcelain")
        paths = [
            Path(line.removeprefix("worktree "))
            for line in worktrees.splitlines()
            if line.startswith("worktree ")
        ]
        # Git lists the primary checkout first, including from a linked worktree.
        production = paths[0] if paths else self.root
        if production.resolve() == self.root:
            raise AuditError("audit must run in an isolated linked worktree")
        production_status = _git(self.root, "status", "--porcelain=v1", "-z", worktree=production)
        tracked = _git(self.root, "ls-files", "-z", worktree=production)
        untracked = _git(self.root, "ls-files", "--others", "--exclude-standard", "-z", worktree=production)
        file_hashes = {}
        for relative in sorted(set((tracked + untracked).split("\0")) - {""}):
            path = production / relative
            if path.is_file():
                file_hashes[relative] = _sha_bytes(path.read_bytes())
            else:
                file_hashes[relative] = "MISSING"
        protected_files = {
            relative: _sha_bytes((self.root / relative).read_bytes())
            for relative in self.rules["protected_paths"]
        }
        return {
            "main_ref": main_ref,
            "remote_refs_sha256": _sha_bytes(remote_refs.encode()),
            "production_checkout": str(production.resolve()),
            "production_status_sha256": _sha_bytes(production_status.encode()),
            "production_status_entry_count": production_status.count("\0"),
            "production_content_sha256": _sha_bytes(json.dumps(file_hashes, sort_keys=True).encode()),
            "production_head": _git(self.root, "rev-parse", "HEAD", worktree=production).strip(),
            "production_index_sha256": _sha_bytes(_git(self.root, "diff", "--cached", "--binary", worktree=production).encode()),
            "protected_files": protected_files,
        }

    def initialize(self) -> dict[str, Any]:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        if self.state_path.exists():
            state = self._state()
            return state
        records = _entries(self.root)
        state = {
            "schema_version": 1,
            "run_id": f"behavior-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
            "current_stage": "audit",
            "stage_status": "in_progress",
            "rule_hash": self.rule_hash,
            "last_checkpoint": None,
            "heartbeat_time": _now(),
            "attempts": {},
            "completed_steps": [],
            "completed_research_stages": [],
            "blocked_entries": {},
            "entry_status": {
                entry_id: {"before": row["status"], "current": row["status"]}
                for entry_id, row in sorted(records.items())
            },
            "protected_baseline": self._protected_snapshot(),
            "rules_baseline": self.rules,
            "canary_hashes": {
                path.name: _sha_bytes(path.read_bytes()) for path in sorted(self.fixtures_dir.glob("*.json"))
            },
            "baseline_commit": _git(self.root, "rev-parse", "HEAD").strip(),
            "bench_contracts": self.bench_contracts(),
        }
        self._write_state(state)
        _atomic_json(self.run_dir / "BASELINE.json", state)
        _atomic_json(self.run_dir / "BASELINE.sha256.json", {"sha256": _sha_bytes((self.run_dir / "BASELINE.json").read_bytes())})
        for name, title in (
            ("FETCH_LEDGER.jsonl", None),
            ("DECISIONS.md", "# Behavior audit decisions\n\n"),
            (
                "RULE_CHANGES.md",
                ("# Behavior audit rule changes\n\n"
                "Changes use a fenced `rule-change` JSON object containing old_sha256, "
                "new_sha256, classification (`add` or `tighten`), reason and reviewer.\n"),
            ),
        ):
            path = self.run_dir / name
            if not path.exists():
                _atomic_text(path, "" if title is None else title)
        return state

    def _rule_change_entries(self) -> list[dict[str, Any]]:
        path = self.run_dir / "RULE_CHANGES.md"
        if not path.exists():
            return []
        blocks = re.findall(
            r"```rule-change\s*\n(.*?)\n```", path.read_text(encoding="utf-8"), re.DOTALL
        )
        entries: list[dict[str, Any]] = []
        for block in blocks:
            try:
                value = json.loads(block)
            except json.JSONDecodeError as exc:
                raise AuditError(f"invalid rule-change block: {exc}") from exc
            if not isinstance(value, dict):
                raise AuditError("rule-change entry must be an object")
            entries.append(value)
        return entries

    def check_rule_hash(self) -> CheckResult:
        state = self._state()
        baseline_record = _json(self.run_dir / "BASELINE.json")
        old_hash = baseline_record["rule_hash"]
        if state.get("rule_hash") != old_hash:
            return CheckResult("AUD-RULE-001", False, "STATE.json rule hash was changed from the locked original")
        if old_hash == self.rule_hash:
            return CheckResult("AUD-RULE-001", True, f"rule hash {self.rule_hash} matches state")
        matching = [
            item
            for item in self._rule_change_entries()
            if item.get("old_sha256") == old_hash and item.get("new_sha256") == self.rule_hash
        ]
        allowed = bool(matching) and all(
            item.get("classification") in {"add", "tighten"} for item in matching
        )
        # A prose assertion of 'tighten' is insufficient. Existing assertions and
        # scalar settings must be identical; only new assertions/regressions may be added.
        baseline = state.get("rules_baseline", {})
        for key, value in baseline.items():
            if key in {"rules", "regression_commands"}:
                allowed = allowed and all(item in self.rules.get(key, []) for item in value)
            else:
                allowed = allowed and self.rules.get(key) == value
        return CheckResult(
            "AUD-RULE-001",
            allowed,
            "rule change is explicitly recorded as non-loosening" if allowed else "rule hash changed",
            () if allowed else (f"state={old_hash}", f"current={self.rule_hash}"),
        )

    def cited_urls(self) -> set[str]:
        from .sources import source_catalog

        urls: set[str] = set()
        locations = [
            self.root / "src/ohmni/behavior/data",
            self.root / "docs/behavior/gapfill",
        ]
        for location in locations:
            for path in sorted(location.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".yaml", ".yml"}:
                    continue
                if path.suffix.lower() == ".json":
                    urls.update(_urls_in(_json(path)))
                else:
                    urls.update(_urls_in(path.read_text(encoding="utf-8")))
        for record in source_catalog(self.root).values():
            for source in record["sources"]:
                urls.update(source["urls"])
        return urls

    def source_bindings(self) -> dict[str, Any]:
        path = self.root / "docs/behavior/SOURCE_BINDINGS.json"
        return _json(path) if path.exists() else {}

    def _superseded(self, missing: list[str], ledger: list[dict]) -> tuple[list[str], list[str]]:
        """An unfetchable cited URL is satisfied only by an approved supersession
        whose replacement document has its own successful archived fetch."""
        bindings = self.source_bindings()
        table = bindings.get("supersessions", {})
        approved = bool(bindings.get("approved_by")) and bool(bindings.get("approved_on"))
        remaining, errors = [], []
        prefix = "AUD-SOURCE-001: missing successful archived fetch: "
        for line in missing:
            url = line[len(prefix):] if line.startswith(prefix) else None
            entry = table.get(url) if url else None
            if not entry:
                remaining.append(line)
                continue
            replacement = entry.get("archive_url")
            if not approved or not replacement or replacement == url:
                errors.append(f"{url}: supersession lacks approval or a distinct replacement")
                remaining.append(line)
                continue
            if entry.get("supports") not in {"yes", "partial", "no"} or not entry.get("evidence") and entry.get("supports") == "yes":
                errors.append(f"{url}: supersession must state what the replacement supports")
                remaining.append(line)
                continue
            if entry.get("supports") != "yes" and not entry.get("note"):
                errors.append(f"{url}: partial or conflicting supersession must explain the gap")
                remaining.append(line)
                continue
            replacement_errors = evidence.source_errors({replacement}, ledger, self.run_dir)
            if replacement_errors:
                remaining.extend(replacement_errors)
        return remaining, errors

    def check_source_ledger(self) -> CheckResult:
        cited = self.cited_urls()
        ledger = _read_jsonl(self.run_dir / "FETCH_LEDGER.jsonl")
        missing, supersession_errors = self._superseded(evidence.source_errors(cited, ledger, self.run_dir), ledger)
        missing = sorted(set(missing))
        field_failures = list(supersession_errors)
        for path in (self.root / "docs/behavior/gapfill").glob("OHM-*.md"):
            if self._gapfill_evidence(path.stem) is None:
                field_failures.append(f"{path.name}: per-entry gapfill lacks machine-readable audit-evidence fields")
        # Named source references without URLs are unresolved evidence, not an
        # implicit exemption from the ledger requirement.
        from .sources import source_catalog
        catalog = source_catalog(self.root)
        _atomic_json(self.run_dir / "SOURCE_CATALOG.json", catalog)
        for row in catalog.values():
            field_failures.extend(row["unresolved"])
        for path in sorted((self.root / "src/ohmni/behavior/data/bindings").glob("*.json")):
            for order in _json(path).get("package_pin_orders", []):
                cite = order.get("citation", {})
                bound = self.source_bindings().get("citation_urls", {}).get(cite.get("document_id"))
                if cite.get("document_id") != "ohmni-component-behavior-spec" and not cite.get("url"):
                    if not bound:
                        field_failures.append(f"{path.stem}/{order.get('package_name')}: external citation has no fetched URL: {cite.get('document_id')}")
                    else:
                        field_failures.extend(evidence.source_errors({bound}, ledger, self.run_dir))
        for entry_id in _entries(self.root):
            gap = self._gapfill_evidence(entry_id)
            if gap:
                for field in gap.get("field_updates", []):
                    field_failures.extend(evidence.field_errors(field, ledger, self.run_dir))
        return CheckResult(
            "AUD-SOURCE-001",
            not missing and not field_failures,
            f"{len(cited) - len(missing)}/{len(cited)} cited URLs have successful hashed fetches",
            tuple(missing + field_failures),
        )

    def _gapfill_evidence(self, entry_id: str) -> dict[str, Any] | None:
        directory = self.root / "docs/behavior/gapfill"
        sidecar = directory / f"{entry_id}.audit.json"
        if sidecar.exists():
            value = _json(sidecar)
            return value if isinstance(value, dict) else None
        markdown = directory / f"{entry_id}.md"
        if markdown.exists():
            match = re.search(
                r"```audit-evidence\s*\n(.*?)\n```",
                markdown.read_text(encoding="utf-8"),
                re.DOTALL,
            )
            if match:
                value = json.loads(match.group(1))
                return value if isinstance(value, dict) else None
        return None

    def _upgrade_evidence_errors(self, evidence: dict[str, Any] | None) -> list[str]:
        from .evidence import upgrade_errors

        errors = upgrade_errors(evidence, _read_jsonl(self.run_dir / "FETCH_LEDGER.jsonl"), self.run_dir)
        if evidence and evidence.get("bench_result"):
            path = self._safe_run_path(evidence["bench_result"])
            if not path.is_file():
                errors.append("AUD-UPGRADE-001: referenced current-run bench missing")
            else:
                errors.extend(self._bench_errors(_json(path)))
        return errors

    def _safe_run_path(self, relative: str) -> Path:
        candidate = (self.run_dir / relative).resolve()
        if self.run_dir not in candidate.parents:
            raise AuditError(f"run artifact path escapes run directory: {relative}")
        return candidate

    def check_status_upgrades(self) -> CheckResult:
        state = self._state()
        records = _entries(self.root)
        order = {name: index for index, name in enumerate(self.rules["status_order"])}
        errors: list[str] = []
        upgrades = 0
        for entry_id, record in sorted(records.items()):
            before = state["entry_status"].get(entry_id, {}).get("before")
            after = record.get("status")
            if before not in order or after not in order:
                errors.append(f"{entry_id}: invalid before/after status {before!r}/{after!r}")
                continue
            if order[after] > order[before]:
                upgrades += 1
                for error in self._upgrade_evidence_errors(self._gapfill_evidence(entry_id)):
                    errors.append(f"{entry_id}: {error}")
        return CheckResult(
            "AUD-UPGRADE-001",
            not errors,
            f"{upgrades} status upgrades checked",
            tuple(errors),
        )

    def _vendor_errors(self, record: dict[str, Any], context: str) -> list[str]:
        if record.get("fidelity") != "vendor_model":
            return []
        model = record.get("vendor_model")
        if not isinstance(model, dict):
            return [f"{context}: vendor_model metadata missing"]
        errors: list[str] = []
        for key in ("file", "license_file"):
            path = model.get(key)
            if not isinstance(path, str) or self.root not in (self.root / path).resolve().parents or not (self.root / path).is_file():
                errors.append(f"{context}: missing {key} {path!r}")
        if model.get("license_compatible") is not True:
            errors.append(f"{context}: license_compatible is not true")
        if model.get("license") not in self.rules["compatible_vendor_model_licenses"]:
            errors.append(f"{context}: license is not allowlisted")
        return errors

    def check_vendor_models(self) -> CheckResult:
        errors: list[str] = []
        for path in sorted((self.root / "src/ohmni/behavior/data").rglob("*.json")):
            errors.extend(self._vendor_errors(_json(path), str(path.relative_to(self.root))))
        return CheckResult(
            "AUD-VENDOR-001",
            not errors,
            "all vendor_model labels have attached compatible models" if not errors else "invalid vendor_model labels",
            tuple(errors),
        )

    def check_spec_preservation(self) -> CheckResult:
        completed = _run(
            [sys.executable, "scripts/generate_behavior_records.py", "--check"], self.root
        )
        led = _json(self.root / "src/ohmni/behavior/data/bindings/GENERIC_LED_GREEN.json")
        led_orders = led.get("package_pin_orders", [])
        permutation_ok = bool(led_orders) and all(not evidence.led_errors(value) for value in led_orders)
        details: list[str] = []
        if completed.returncode:
            details.append((completed.stdout + completed.stderr).strip())
        if not permutation_ok:
            details.append("GENERIC_LED_GREEN catalog-to-package permutation is not 1->2, 2->1")
        return CheckResult(
            "AUD-SPEC-001",
            completed.returncode == 0 and permutation_ok,
            "generated projection and approved LED permutation are current",
            tuple(details),
        )

    def _bench_errors(self, result: dict[str, Any]) -> list[str]:
        from .benches import compound_contracts, numeric_contract, observed_value

        bench_id = str(result.get("bench_id", "<unknown>"))
        state = self._state()
        contract = self._bench_contracts().get(bench_id)
        if not contract:
            return [f"AUD-BENCH-001: {bench_id}: unknown locked bench identity"]
        errors = []
        if result.get("run_id") != state["run_id"]:
            errors.append(f"AUD-BENCH-001: {bench_id}: not a result from this run")
        comparisons = result.get("comparisons", [])
        expected = contract["expected"]
        if not isinstance(expected, list) or not expected or len(expected) != len(comparisons):
            errors.append(f"AUD-BENCH-001: {bench_id}: missing numeric analytical comparison")
        else:
            for actual, expected_measure in zip(comparisons, expected, strict=True):
                if not isinstance(expected_measure, dict):
                    errors.append(f"AUD-BENCH-001: {bench_id}: analytical expression needs an explicit parser")
                    continue
                if "components" in actual:
                    parts = compound_contracts(expected_measure)
                    if parts is None or len(parts) != len(actual["components"]):
                        errors.append(f"AUD-BENCH-001: {bench_id}: compound comparison does not match locked value")
                    else:
                        for part, observed in zip(parts, actual["components"], strict=True):
                            errors.extend(evidence.bench_errors(dict(result, **observed), part))
                else:
                    check = dict(result, **actual)
                    errors.extend(evidence.bench_errors(check, numeric_contract(expected_measure)))
                if actual.get("measure") != expected_measure.get("measure"):
                    errors.append(f"AUD-BENCH-001: {bench_id}: measurement identity mismatch")
        for key in ("output", "version"):
            relative = result.get(f"{key}_file")
            digest = result.get(f"{key}_sha256")
            if not relative:
                errors.append(f"AUD-BENCH-001: {bench_id}: {key} artifact missing")
                continue
            path = self._safe_run_path(relative)
            if not path.is_file() or _sha_bytes(path.read_bytes()) != digest:
                errors.append(f"AUD-BENCH-001: {bench_id}: {key} artifact hash mismatch")
            elif key == "version" and path.read_text(encoding="utf-8") != result.get("ngspice_version"):
                errors.append(f"AUD-BENCH-001: {bench_id}: version differs from captured output")
            elif key == "output":
                output = path.read_text(encoding="utf-8")
                for comparison in comparisons:
                    name = str(comparison.get("measure", ""))
                    observed = observed_value(self, bench_id, comparison, output)
                    recorded = ([part.get("measured") for part in comparison["components"]]
                                if "components" in comparison else comparison.get("measured"))
                    if observed is None or recorded != observed:
                        errors.append(f"AUD-BENCH-001: {bench_id}: measurement not found unambiguously in archived output: {name}")
        if result.get("netlist_sha256") != contract["netlist_sha256"]:
            errors.append(f"AUD-BENCH-001: {bench_id}: netlist differs from locked source")
        if _sha_bytes((self.root / contract["file"]).read_bytes()) != contract["netlist_sha256"]:
            errors.append(f"AUD-BENCH-001: {bench_id}: source bench modified")
        return errors

    def bench_contracts(self) -> dict[str, dict]:
        required = {}
        for path in sorted((self.root / "src/ohmni/behavior/data/classes").glob("*.json")):
            record = _json(path)
            for bench in record.get("benches", []):
                bench_id = bench.get("bench_id")
                if bench_id:
                    identity = f"{record['behavior_id']}/{bench_id}"
                    if identity in required:
                        raise AuditError(f"duplicate class/bench ID: {identity}")
                    required[identity] = {
                        "file": bench["file"], "expected": bench["expected"],
                        "netlist_sha256": _sha_bytes((self.root / bench["file"]).read_bytes()),
                    }
        return required

    def check_benches(self) -> CheckResult:
        required = set(self._bench_contracts())
        results: dict[str, dict[str, Any]] = {}
        errors: list[str] = []
        passing = 0
        for path in sorted((self.run_dir / "bench-results").glob("*.json")):
            result = _json(path)
            bench_id = str(result.get("bench_id", ""))
            if not bench_id or bench_id in results:
                errors.append(f"invalid or duplicate bench result {path.name}")
                continue
            results[bench_id] = result
            result_errors = self._bench_errors(result)
            errors.extend(result_errors)
            passing += int(not result_errors)
        missing = sorted(required - set(results))
        errors.extend(f"{bench_id}: no current-run result" for bench_id in missing)
        mapped = {row["file"] for row in self._bench_contracts().values()}
        unbound = sorted(path.relative_to(self.root).as_posix() for path in (self.root / "docs/behavior/bench").rglob("*.cir") if path.relative_to(self.root).as_posix() not in mapped)
        errors.extend(f"{path}: authored netlist has no canonical benchmark contract; not run" for path in unbound)
        runtime_models = self._state().get("model_implementation", {})
        if runtime_models:
            from .runtime_benches import runtime_receipt_errors

            for entry_id, implementation in runtime_models.items():
                if implementation in {"implemented", "audited"}:
                    errors.extend(runtime_receipt_errors(self, entry_id))
        return CheckResult(
            "AUD-BENCH-001",
            not errors,
            f"{passing}/{len(required)} canonical bench references passed; {len(unbound)} additional authored netlists lack a canonical contract",
            tuple(errors),
        )

    def _honesty_errors(self, claim: dict[str, Any], context: str) -> list[str]:
        return [f"{context}: {item}" for item in evidence.honesty_errors(claim)]

    def check_honesty(self) -> CheckResult:
        errors: list[str] = []
        for path in sorted((self.run_dir / "claims").glob("*.json")):
            errors.extend(self._honesty_errors(_json(path), path.name))
        canaries = self.run_dir / "CANARY_RESULTS.json"
        if not canaries.exists() or not _json(canaries).get("passed"):
            errors.append("current canary result proving non-run rejection is missing")
        proof = self.run_dir / "REGRESSION_RESULTS.json"
        if not proof.exists() or not _json(proof).get("passed"):
            errors.append("current product/UI honesty regression evidence missing")
        return CheckResult(
            "AUD-HONESTY-001",
            not errors,
            "all recorded UI/code claims preserve non-run and violation status",
            tuple(errors),
        )

    def check_protected_state(self) -> CheckResult:
        state = self._state()
        baseline = state["protected_baseline"]
        current = self._protected_snapshot()
        errors: list[str] = []
        for key in ("main_ref", "remote_refs_sha256", "production_status_sha256", "production_content_sha256", "production_head", "production_index_sha256"):
            if current.get(key) != baseline.get(key):
                errors.append(f"{key} changed: {baseline.get(key)} -> {current.get(key)}")
        if current.get("protected_files") != baseline.get("protected_files"):
            errors.append("protected file content changed")
        branch = _git(self.root, "branch", "--show-current").strip()
        if not branch.startswith(self.rules["allowed_work_branch_prefix"]):
            errors.append(f"work branch {branch!r} is outside the allowed prefix")
        return CheckResult(
            "AUD-PROTECT-001",
            not errors,
            "main, production checkout, remote refs and protected paths match baseline",
            tuple(errors),
        )

    def write_coverage(self) -> Path:
        state = self._state()
        records = _entries(self.root)
        bench_ids = {
            _json(path).get("bench_id")
            for path in (self.run_dir / "bench-results").glob("*.json")
            if path.is_file() and not self._bench_errors(_json(path))
        }
        statuses: dict[str, int] = {}
        simulable = 0
        rows: list[str] = []
        for entry_id, record in sorted(records.items()):
            status = record["status"]
            statuses[status] = statuses.get(status, 0) + 1
            class_ids = record["behavior_class_ids"]
            required = {key for key in state["bench_contracts"] if key.split("/")[0] in class_ids}
            bench_pass = bool(required) and required <= bench_ids
            # Simulable is derived from current evidence on every run, never from a stored
            # flag: an implemented model counts only when all of its runtime receipts pass now.
            implemented = state.get("model_implementation", {}).get(entry_id) in {"implemented", "audited"}
            if implemented:
                from .runtime_benches import runtime_receipt_errors

                implemented = not runtime_receipt_errors(self, entry_id)
            can_simulate = implemented and bench_pass and record["simulation_disposition"] == "simulable"
            simulable += int(can_simulate)
            before = state["entry_status"][entry_id]["before"]
            classes = ", ".join(record["behavior_class_ids"])
            bench = f"{len(required & bench_ids)}/{len(required)} PASS" if required else "NOT RUN"
            reason = "audited implementation" if can_simulate else (
                record["simulation_reason"] if record["simulation_disposition"] == "not_simulable"
                else "Product behavior model and current-run bench not yet audited."
            )
            reason = reason.replace("|", "\\|")
            inventory_path = self.run_dir / "GAP_INVENTORY.json"
            inventory = _json(inventory_path) if inventory_path.exists() else {}
            open_items = inventory.get("entries", {}).get(entry_id, {}).get("open_items", [])
            open_text = "; ".join(open_items).replace("|", "\\|").replace("\n", " ")
            if not open_text:
                open_text = "Current-run audit/bench pending" if not can_simulate else "none recorded"
            rows.append(
                f"| {entry_id} | {classes} | {record['layer']} | {record['fidelity']} | "
                f"{before} | {status} | {'yes' if can_simulate else 'no'} | {reason} | {bench} | "
                f"{open_text} |"
            )
        lines = [
            "# Component behavior coverage",
            "",
            "> Generated by `python -m tools.behavior_audit coverage`; do not edit rows by hand.",
            "",
            f"Entries: **{len(records)}**. Audited simulable: **{simulable}**. "
            + ". ".join(f"{key}: **{value}**" for key, value in sorted(statuses.items()))
            + ".",
            "",
            "| Entry | Behavior class | Layer | Fidelity | Status before | Status after | Simulable | Why | Current-run bench | Open items |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            *rows,
            "",
        ]
        path = self.root / "docs/behavior/COVERAGE.md"
        _atomic_text(path, "\n".join(lines))
        return path

    def check_coverage(self) -> CheckResult:
        records = _entries(self.root)
        expected_ids = {f"OHM-{index:03d}" for index in range(1, self.rules["expected_entry_count"] + 1)}
        coverage = self.root / "docs/behavior/COVERAGE.md"
        rows: list[str] = []
        if coverage.exists():
            rows = re.findall(r"^\| (OHM-\d{3}) \|", coverage.read_text(encoding="utf-8"), re.MULTILINE)
        errors: list[str] = []
        if set(records) != expected_ids:
            errors.append(f"record IDs differ: missing={sorted(expected_ids-set(records))}, extra={sorted(set(records)-expected_ids)}")
        if set(rows) != expected_ids or len(rows) != len(expected_ids):
            errors.append(f"coverage rows={len(rows)}, unique={len(set(rows))}, expected={len(expected_ids)}")
        return CheckResult(
            "AUD-COVERAGE-001",
            not errors,
            f"{len(records)} records and {len(rows)} coverage rows",
            tuple(errors),
        )

    def check_regression(self) -> CheckResult:
        details: list[str] = []
        passed = True
        receipts = []
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.root / "src")
        base_temp = self.run_dir / "pytest-temp"
        base_temp.mkdir(parents=True, exist_ok=True)
        for index, command in enumerate(self.rules["regression_commands"], 1):
            tokens = _command_tokens(command)
            if tokens[0] == "python":
                tokens[0] = sys.executable
            if "pytest" in tokens:
                tokens.append(f"--basetemp={base_temp / str(index)}")
            completed = subprocess.run(
                tokens, cwd=self.root, text=True, capture_output=True, check=False, env=env
            )
            output = (completed.stdout + completed.stderr).strip()
            details.append(f"{command}: exit {completed.returncode}: {output[-1000:]}")
            receipts.append({"command": command, "exit_code": completed.returncode, "output": output})
            passed = passed and completed.returncode == 0
        _atomic_json(self.run_dir / "REGRESSION_RESULTS.json", {"run_id": self._state()["run_id"], "timestamp": _now(), "passed": passed, "commands": receipts})
        return CheckResult(
            "AUD-REGRESSION-001",
            passed,
            f"{len(self.rules['regression_commands'])} locked regression commands ran",
            tuple(details),
        )

    def _verifier_errors(self, stage: str, report: dict[str, Any]) -> list[str]:
        population = report.get("population")
        sample = report.get("sample")
        results = report.get("results")
        errors: list[str] = []
        if report.get("stage") != stage or report.get("reviewer_context") != "fresh":
            errors.append("stage or fresh reviewer context missing")
        if not isinstance(report.get("seed"), int):
            errors.append("integer random seed missing")
        if not isinstance(population, list) or not population:
            errors.append("population missing")
            return errors
        expected_k = max(5, math.ceil(len(population) * 0.10))
        if not isinstance(sample, list) or len(set(sample)) != expected_k or len(sample) != expected_k or not set(sample) <= set(population):
            errors.append(f"sample must contain K={expected_k} unique population entries")
        elif isinstance(report.get("seed"), int):
            chosen = sorted(random.Random(report["seed"]).sample(sorted(set(population)), expected_k))
            if sorted(sample) != chosen:
                errors.append("sample does not match the recorded random seed")
        if not isinstance(results, list) or {row.get("entry_id") for row in results if isinstance(row, dict)} != set(sample or []):
            errors.append("one verifier result per sampled entry is required")
        else:
            for result in results:
                if not result.get("primary_sources"):
                    errors.append(f"{result.get('entry_id')}: primary source missing")
                if result.get("mismatches"):
                    errors.append(f"{result.get('entry_id')}: verifier mismatch")
        return errors

    def check_independent_verifiers(self) -> CheckResult:
        state = self._state()
        errors: list[str] = []
        checked = 0
        for stage in state.get("completed_research_stages", []):
            path = self.run_dir / "verifier" / f"{stage}.json"
            if not path.exists():
                errors.append(f"{stage}: verifier report missing")
                continue
            checked += 1
            report = _json(path)
            errors.extend(f"{stage}: {item}" for item in self._verifier_errors(stage, report))
            plan_path = path.with_name(f"{stage}-plan.json")
            if not plan_path.exists():
                errors.append(f"{stage}: verifier plan missing")
                continue
            plan = _json(plan_path)
            for key in ("seed", "population", "sample"):
                if report.get(key) != plan.get(key):
                    errors.append(f"{stage}: report {key} differs from current plan")
            for row in report.get("results", []):
                entry_id = row.get("entry_id", "")
                if not re.fullmatch(r"OHM-\d{3}", entry_id):
                    errors.append(f"{stage}: invalid reviewed entry ID")
                    continue
                reviewed = row.get("reviewed_content", {})
                for key, relative in (
                    ("gapfill_sha256", f"docs/behavior/gapfill/{entry_id}.md"),
                    ("generated_record_sha256", f"src/ohmni/behavior/data/entries/{entry_id}.json"),
                ):
                    source = self.root / relative
                    if not source.is_file() or reviewed.get(key) != _sha_bytes(source.read_bytes()):
                        errors.append(f"{stage}: {entry_id} reviewed {key} is missing or stale")
        return CheckResult(
            "AUD-VERIFY-001",
            not errors,
            f"{checked} completed research-stage verifier reports checked",
            tuple(errors),
        )

    def check_state(self) -> CheckResult:
        state = self._state()
        errors: list[str] = []
        required = {
            "run_id", "current_stage", "stage_status", "rule_hash", "heartbeat_time",
            "attempts", "entry_status", "protected_baseline", "blocked_entries",
        }
        missing = sorted(required - set(state))
        if missing:
            errors.append(f"missing fields {missing}")
        try:
            datetime.fromisoformat(str(state.get("heartbeat_time", "")))
        except ValueError:
            errors.append("heartbeat_time is invalid")
        if len(state.get("entry_status", {})) != self.rules["expected_entry_count"]:
            errors.append("entry_status does not contain exactly 180 entries")
        baseline_path = self.run_dir / "BASELINE.json"
        baseline = _json(baseline_path)
        recorded_hash = _json(self.run_dir / "BASELINE.sha256.json")["sha256"]
        if _sha_bytes(baseline_path.read_bytes()) != recorded_hash:
            errors.append("baseline archive hash mismatch")
        # Once committed, editing both local baseline and its local hash is still
        # detected against the immutable Git version used by this checkpoint.
        relative = baseline_path.relative_to(self.root).as_posix() if self.root in baseline_path.parents else None
        if relative:
            known = _run(["git", "ls-files", "--error-unmatch", relative], self.root)
            if known.returncode == 0 and _git(self.root, "diff", "HEAD", "--", relative).strip():
                errors.append("committed protected baseline artifact was modified")
        for key in ("bench_contracts", "protected_baseline", "rules_baseline", "canary_hashes", "run_id"):
            if state.get(key) != baseline.get(key):
                errors.append(f"state changed locked baseline field {key}")
        full, repin_errors = self._apply_repins(baseline["bench_contracts"])
        errors.extend(repin_errors)
        # Class records keep the spec's expectations; ledger corrections and
        # additions apply on top and are verified separately above.
        effective, _ = self._apply_repins(baseline["bench_contracts"], corrections=False, additions=False)
        if self.bench_contracts() != effective:
            errors.append("bench expectations, tolerances or source decks changed")
        repinned = {row["file"] for key, row in full.items()
                    if key not in baseline["bench_contracts"]
                    or row["netlist_sha256"] != baseline["bench_contracts"][key]["netlist_sha256"]}
        for key, row in full.items():
            if key not in baseline["bench_contracts"]:
                path = self.root / row["file"]
                if not path.is_file() or _sha_bytes(path.read_bytes()) != row["netlist_sha256"]:
                    errors.append(f"added bench deck missing or changed: {key}")
        changed = set(_git(self.root, "diff", "--name-only", state["baseline_commit"], "--", "docs/behavior/bench").split())
        if changed - repinned:
            errors.append("authored bench/include corpus changed from the baseline commit outside an approved re-pin: "
                          + ", ".join(sorted(changed - repinned)))
        return CheckResult("AUD-RESUME-001", not errors, "run state is complete and parseable", tuple(errors))

    def _validate_canary(self, fixture: dict[str, Any]) -> str | None:
        kind, payload = fixture["kind"], fixture["payload"]
        errors = []
        if kind == "gapfill_field":
            errors = evidence.field_errors(payload, [], self.run_dir)
        elif kind == "source_ledger":
            errors = evidence.source_errors(set(payload["urls"]), payload["ledger"], self.run_dir)
        elif kind == "status_upgrade":
            errors = self._upgrade_evidence_errors(payload)
        elif kind == "vendor_model":
            errors = self._vendor_errors(payload, "canary")
            errors = [f"AUD-VENDOR-001: {item}" for item in errors]
        elif kind == "bench":
            errors = evidence.bench_errors(payload, fixture["contract"])
        elif kind == "led_permutation":
            errors = evidence.led_errors(payload)
        elif kind == "honesty":
            errors = evidence.honesty_errors(payload)
        else:
            raise AuditError(f"unknown canary kind {kind!r}")
        expected = fixture["expected_rule"]
        return expected if any(error.startswith(expected + ":") for error in errors) else None

    def run_canaries(self) -> CheckResult:
        expected_names = set(self.rules["required_canaries"])
        fixtures = [_json(path) for path in sorted(self.fixtures_dir.glob("*.json"))]
        names = {fixture.get("canary_id") for fixture in fixtures}
        details: list[str] = []
        passed = names == expected_names
        state = self._state()
        current_hashes = {path.name: _sha_bytes(path.read_bytes()) for path in sorted(self.fixtures_dir.glob("*.json"))}
        if current_hashes != state.get("canary_hashes"):
            passed = False
            details.append("canary fixture bytes changed after initialization")
        if names != expected_names:
            details.append(f"fixture set differs: expected={sorted(expected_names)}, actual={sorted(names)}")
        results: list[dict[str, Any]] = []
        for fixture in fixtures:
            rejected_by = self._validate_canary(fixture)
            correct = rejected_by == fixture.get("expected_rule")
            passed = passed and correct
            results.append(
                {
                    "canary_id": fixture.get("canary_id"),
                    "expected_rule": fixture.get("expected_rule"),
                    "rejected_by": rejected_by,
                    "passed": correct,
                }
            )
            if not correct:
                details.append(
                    f"{fixture.get('canary_id')}: expected {fixture.get('expected_rule')}, got {rejected_by}"
                )
        _atomic_json(
            self.run_dir / "CANARY_RESULTS.json",
            {"schema_version": 1, "ran_at": _now(), "passed": passed, "results": results},
        )
        return CheckResult(
            "AUD-CANARY-001",
            passed,
            f"{sum(result['passed'] for result in results)}/{len(results)} canaries rejected as expected",
            tuple(details),
        )

    def run_checks(self, *, regression: bool = True) -> list[CheckResult]:
        methods = [
            ("AUD-RULE-001", self.check_rule_hash), ("AUD-CANARY-001", self.run_canaries),
            ("AUD-SOURCE-001", self.check_source_ledger), ("AUD-UPGRADE-001", self.check_status_upgrades),
            ("AUD-VENDOR-001", self.check_vendor_models), ("AUD-SPEC-001", self.check_spec_preservation),
            ("AUD-BENCH-001", self.check_benches), ("AUD-PROTECT-001", self.check_protected_state),
            ("AUD-COVERAGE-001", self.check_coverage), ("AUD-VERIFY-001", self.check_independent_verifiers),
            ("AUD-RESUME-001", self.check_state),
            ("AUD-REGRESSION-001", self.check_regression if regression else lambda: CheckResult("AUD-REGRESSION-001", False, "Regression not run")),
            ("AUD-HONESTY-001", self.check_honesty),
        ]
        checks = []
        for rule_id, method in methods:
            try:
                checks.append(method())
            except (AuditError, OSError, KeyError, TypeError, ValueError) as exc:
                checks.append(CheckResult(rule_id, False, "Check failed to evaluate", (str(exc),)))
        return checks

    def checkpoint(self, stage: str, touched: list[str], *, regression: bool = True) -> tuple[Path, list[CheckResult]]:
        state = self._state()
        state["current_stage"] = stage
        self._write_state(state)
        checks = self.run_checks(regression=regression)
        passed = all(check.passed for check in checks)
        checkpoint_dir = self.run_dir / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        existing = sorted(checkpoint_dir.glob("[0-9][0-9][0-9]-*.md"))
        number = len(existing) + 1
        path = checkpoint_dir / f"{number:03d}-{stage}.md"
        drift = (
            f"Audited {len(touched)} touched entries against the locked brief. "
            f"The checkpoint {'matches' if passed else 'does not yet satisfy'} every required assertion; "
            "all deviations are listed as failed checks below."
        )
        lines = [
            f"# Checkpoint {number:03d}: {stage}",
            "",
            f"- Time: `{_now()}`",
            f"- Commit: `{_git(self.root, 'rev-parse', 'HEAD').strip()}`",
            f"- Rule hash: `{self.rule_hash}`",
            f"- Overall: **{'PASS' if passed else 'FAIL'}**",
            f"- Entries touched: {', '.join(touched) if touched else 'none'}",
            "",
            "| Rule | Result | Summary |",
            "| --- | --- | --- |",
        ]
        for check in checks:
            lines.append(f"| {check.rule_id} | {'PASS' if check.passed else 'FAIL'} | {check.summary.replace('|', '/')} |")
        lines.extend(["", "## Details", ""])
        for check in checks:
            if check.details:
                lines.append(f"### {check.rule_id}")
                lines.extend(f"- {detail}" for detail in check.details)
                lines.append("")
        lines.extend(["## Drift note", "", drift, ""])
        _atomic_text(path, "\n".join(lines))
        _atomic_json(path.with_suffix(".json"), {
            "stage": stage, "number": number, "run_id": state["run_id"],
            "passed": passed, "rule_hash": self.rule_hash,
            "entries_touched": touched, "drift_note": drift,
            "checks": [check.to_dict() for check in checks],
            "canaries": _json(self.run_dir / "CANARY_RESULTS.json"),
        })
        state = self._state()
        for check in checks:
            if not check.passed:
                identity = f"{stage}/{check.rule_id}"
                attempt = _record_checkpoint_failure(
                    state, identity, check.summary, self.rules["maximum_repair_attempts"]
                )
                if check.rule_id == "AUD-PROTECT-001":
                    state["hard_stop"] = "protected_path_violation"
                if check.rule_id == "AUD-CANARY-001" and attempt >= 3:
                    state["hard_stop"] = "canary_repair_exhausted"
        state["last_checkpoint"] = {
            "number": number,
            "stage": stage,
            "status": "passed" if passed else "failed",
            "path": str(path.relative_to(self.root)).replace("\\", "/"),
            "rule_hash": self.rule_hash,
            "entries_touched": touched,
        }
        state["stage_status"] = "checkpoint_passed" if passed else "blocked_by_checkpoint"
        state["entry_status"] = {
            entry_id: {
                "before": state["entry_status"][entry_id]["before"],
                "current": record["status"],
            }
            for entry_id, record in sorted(_entries(self.root).items())
        }
        self._write_state(state)
        return path, checks

    def fetch(self, url: str) -> dict[str, Any]:
        ledger_rows = _read_jsonl(self.run_dir / "FETCH_LEDGER.jsonl")
        if not evidence.source_errors({url}, ledger_rows, self.run_dir):
            return next(row for row in reversed(ledger_rows) if row.get("url") == url and row.get("content_sha256"))
        started = _now()
        status: int | None = None
        content = b""
        error: str | None = None
        request_url = urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=%")
        try:
            request = urllib.request.Request(request_url, headers={"User-Agent": "OhmniBehaviorAudit/1.0"})
            with urllib.request.urlopen(request, timeout=45) as response:
                status = int(response.status)
                content = response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            error = str(exc)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            error = str(exc)
        digest = _sha_bytes(content) if content else None
        if content and digest:
            source_dir = self.run_dir / "fetched-sources"
            source_dir.mkdir(parents=True, exist_ok=True)
            path = source_dir / f"{digest}.bin"
            if not path.exists():
                path.write_bytes(content)
        row = {
            "url": url,
            "request_url": request_url,
            "timestamp": started,
            "http_status": status,
            "content_sha256": digest,
            "content_bytes": len(content),
            "tool_used": "tools.behavior_audit.fetch/urllib",
            "error": error,
        }
        ledger = self.run_dir / "FETCH_LEDGER.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with _LEDGER_LOCK, ledger.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return row

    def probe_ngspice(self) -> dict:
        import shutil

        executable = shutil.which("ngspice")
        try:
            completed = subprocess.run([executable or "ngspice", "-v"], capture_output=True, text=True, timeout=15, check=False)
            output = completed.stdout + completed.stderr
            code = completed.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            output, code = str(exc), None
        _atomic_text(self.run_dir / "ngspice-version.txt", output)
        result = {
            "command": ["ngspice", "-v"], "timestamp": _now(), "executable": executable,
            "exit_code": code, "version_output": output,
            "passed": code == 0 and evidence.version_42(output),
            "output_sha256": _sha_bytes(output.encode()),
        }
        _atomic_json(self.run_dir / "NGSPICE_PROBE.json", result)
        return result

    def verifier_plan(self, stage: str, population: list[str], seed: int | None = None) -> dict[str, Any]:
        if not population:
            raise AuditError("verifier population is empty")
        existing = self.run_dir / "verifier" / f"{stage}-plan.json"
        if seed is None and existing.exists():
            prior = _json(existing)
            if prior["population"] == sorted(set(population)):
                return prior
        actual_seed = seed if seed is not None else int.from_bytes(os.urandom(8), "big")
        rng = random.Random(actual_seed)
        k = max(5, math.ceil(len(population) * 0.10))
        if len(set(population)) < k:
            raise AuditError(f"verifier population has fewer than required K={k} unique entries")
        sample = sorted(rng.sample(sorted(set(population)), k))
        plan = {
            "schema_version": 1,
            "stage": stage,
            "seed": actual_seed,
            "population": sorted(set(population)),
            "sample": sample,
            "instructions": "Fresh reviewer sees only each entry gapfill, cited primary source and generated record; re-derive values, ratings and pin maps and record all mismatches.",
        }
        path = self.run_dir / "verifier" / f"{stage}-plan.json"
        _atomic_json(path, plan)
        return plan

    def final_report(self) -> Path:
        from .report import final_report

        return final_report(self)


__all__ = ["AuditError", "BehaviorAudit", "CheckResult"]
