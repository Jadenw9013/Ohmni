"""Rebuild the content-addressed source archive from the fetch ledger (CBH-R01).

The archive under out/component-behavior/run/fetched-sources/ holds manufacturer datasheets and
specifications. They are copyrighted documents, so a public repository must not redistribute them;
what the repository does publish is the ledger: every URL with the sha256 and byte count of the
document that was checked. This command re-downloads each successful ledger URL into the archive
and verifies the bytes against the recorded hash, so a clean checkout can reproduce the evidence
and the source audit without any copy of the documents travelling with the code.

Usage: python -m tools.behavior_audit rebuild-sources [--only URL] [--report PATH]

Outcomes per URL:
  rebuilt     the download matched the ledger hash and was stored
  present     the archive already held the exact bytes
  changed     the host now serves different bytes (the hash is recorded; the archive keeps nothing)
  unavailable the host refused or failed; the ledger still proves what was checked, not that it
              can be fetched today
  manual      a browser-saved document with named provenance; it cannot be rebuilt automatically
              and must be supplied by the person named in the ledger row
"""

from __future__ import annotations

import datetime
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from .audit import _atomic_json, _read_jsonl


def successful_rows(ledger: list[dict]) -> dict[str, dict]:
    """The latest successful ledger row per URL, which is what the source audit relies on."""
    rows: dict[str, dict] = {}
    for row in ledger:
        status = row.get("http_status")
        manual = row.get("manual_download")
        digest = row.get("content_sha256") or ""
        ok = (type(status) is int and 200 <= status < 300) or (isinstance(manual, dict) and status is None)
        if ok and len(digest) == 64:
            rows[row["url"]] = row
    return rows


def _download(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "OhmniBehaviorAudit/1.0 (source rebuild)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def rebuild(run_dir: Path, *, only: str | None = None, download=_download) -> dict:
    ledger = _read_jsonl(run_dir / "FETCH_LEDGER.jsonl")
    archive = run_dir / "fetched-sources"
    archive.mkdir(parents=True, exist_ok=True)
    report = {"rebuilt_at": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "results": {}, "counts": {}}
    for url, row in sorted(successful_rows(ledger).items()):
        if only and url != only:
            continue
        digest = row["content_sha256"]
        blob = archive / f"{digest}.bin"
        if blob.is_file() and hashlib.sha256(blob.read_bytes()).hexdigest() == digest:
            outcome = {"outcome": "present"}
        elif row.get("manual_download"):
            outcome = {"outcome": "manual", "provenance": row["manual_download"]}
        else:
            try:
                data = download(row.get("request_url") or url)
            except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
                outcome = {"outcome": "unavailable", "error": str(exc)[:200]}
            else:
                actual = hashlib.sha256(data).hexdigest()
                if actual == digest:
                    blob.write_bytes(data)
                    outcome = {"outcome": "rebuilt", "bytes": len(data)}
                else:
                    outcome = {"outcome": "changed", "served_sha256": actual, "served_bytes": len(data)}
        outcome.update(expected_sha256=digest, expected_bytes=row.get("content_bytes"),
                       host=urlsplit(url).netloc)
        report["results"][url] = outcome
        report["counts"][outcome["outcome"]] = report["counts"].get(outcome["outcome"], 0) + 1
    return report


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--only")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    run_dir = args.root / "out/component-behavior/run"
    report = rebuild(run_dir, only=args.only)
    target = args.report or run_dir / "SOURCE_REBUILD.json"
    _atomic_json(target, report)
    print(json.dumps(report["counts"], indent=2))
    print(target)
    missing = report["counts"].get("unavailable", 0) + report["counts"].get("changed", 0) + report["counts"].get("manual", 0)
    return 0 if missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
