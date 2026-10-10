"""Record browser-saved source documents in the fetch ledger with named-person provenance.

Usage: python -m tools.behavior_audit.ingest_manual <folder> "<your name>" [map.json]

Each file in <folder> whose name appears in the map is hashed, copied into
fetched-sources/<sha256>.bin and appended to FETCH_LEDGER.jsonl. The row records
who saved it and never claims an HTTP status that was not observed; the audit
accepts such rows only with that provenance (see evidence.source_errors).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "out/component-behavior/run"
DEFAULT_MAP = ROOT / "docs/behavior/source_downloads/manual_map.json"


def ingest(folder: Path, who: str, mapping: dict[str, str]) -> list[str]:
    if not who.strip():
        raise SystemExit("name of the person who saved the files is required")
    report = []
    archive = RUN / "fetched-sources"
    archive.mkdir(parents=True, exist_ok=True)
    for name, url in mapping.items():
        path = folder / name
        if not path.is_file():
            report.append(f"missing {name}")
            continue
        data = path.read_bytes()
        if name.lower().endswith(".pdf") and b"%PDF-" not in data[:1024]:
            report.append(f"not a PDF, skipped {name}")
            continue
        if not data:
            report.append(f"empty, skipped {name}")
            continue
        digest = hashlib.sha256(data).hexdigest()
        shutil.copyfile(path, archive / f"{digest}.bin")
        row = {
            "url": url, "request_url": url,
            "timestamp": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "http_status": None, "content_sha256": digest, "content_bytes": len(data),
            "tool_used": "tools.behavior_audit.ingest_manual (browser download)",
            "manual_download": {"downloaded_by": who, "downloaded_on": datetime.date.today().isoformat(), "file_name": name},
            "error": None,
        }
        with open(RUN / "FETCH_LEDGER.jsonl", "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        report.append(f"recorded {name} {digest[:12]}")
    return report


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        return 2
    mapping = json.loads(Path(args[2] if len(args) > 2 else DEFAULT_MAP).read_text(encoding="utf-8"))
    for line in ingest(Path(args[0]), args[1], mapping):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
