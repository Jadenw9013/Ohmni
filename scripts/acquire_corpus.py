#!/usr/bin/env python3
"""Acquire the pinned component-synthesis source corpus into build/corpus/.

The PDFs are copyrighted manufacturer documents. They are not committed; this
script fetches the exact pinned bytes from the recorded manufacturer HTTPS
origin and refuses anything whose SHA-256 differs. A digest proves identity of
bytes, not manufacturer authenticity -- see COMPONENT_SYNTHESIS_PLAN.md section
5 -- so the recorded origin and redirect chain are written beside the file.

Usage::

    python scripts/acquire_corpus.py            # fetch anything missing
    python scripts/acquire_corpus.py --check    # report only, fetch nothing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "corpus" / "manifest.json"
#: Redirects may not leave the reviewed manufacturer source list.
ALLOWED_HOSTS = ("ww1.microchip.com", "www.microchip.com")
TIMEOUT_SECONDS = 120
MAX_BYTES = 64 * 1024 * 1024


class _BoundedRedirects(urllib.request.HTTPRedirectHandler):
    """Record every redirect and keep them on HTTPS inside the allowed hosts."""

    def __init__(self) -> None:
        self.chain: list[str] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.startswith("https://"):
            raise urllib.error.URLError(f"refusing non-HTTPS redirect to {newurl!r}")
        host = newurl.split("/", 3)[2].split("@")[-1]
        if host not in ALLOWED_HOSTS:
            raise urllib.error.URLError(f"refusing redirect off the reviewed source list: {host}")
        self.chain.append(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def workspace() -> Path:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return ROOT / manifest["workspace"]


def document_path(document_id: str) -> Path:
    return workspace() / f"{document_id}.pdf"


def fetch(entry: dict) -> tuple[bool, str]:
    target = document_path(entry["id"])
    if target.is_file():
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest == entry["sha256"]:
            return True, f"{entry['id']}: present and pinned"
        return False, f"{entry['id']}: present but digest {digest} != pinned {entry['sha256']}"
    url = entry["acquisition_url"]
    if not url.startswith("https://") or url.split("/", 3)[2] not in ALLOWED_HOSTS:
        return False, f"{entry['id']}: acquisition URL is not on the reviewed source list"
    handler = _BoundedRedirects()
    opener = urllib.request.build_opener(handler)
    try:
        with opener.open(url, timeout=TIMEOUT_SECONDS) as response:
            data = response.read(MAX_BYTES + 1)
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return False, f"{entry['id']}: acquisition failed ({type(exc).__name__}: {exc})"
    if len(data) > MAX_BYTES:
        return False, f"{entry['id']}: response exceeded the {MAX_BYTES} byte limit"
    digest = hashlib.sha256(data).hexdigest()
    if digest != entry["sha256"]:
        return False, (
            f"{entry['id']}: downloaded bytes hash {digest}, not the pinned {entry['sha256']}. "
            "The document was not written; the manufacturer may have republished it."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    origin = {
        "document_id": entry["id"],
        "acquisition_url": url,
        "redirect_chain": handler.chain,
        "sha256": digest,
        "bytes": len(data),
        "origin_kind": entry["origin_kind"],
        "note": "Observed manufacturer distribution source; not a guarantee of silicon identity.",
    }
    target.with_suffix(".origin.json").write_text(
        json.dumps(origin, indent=2) + "\n", encoding="utf-8"
    )
    return True, f"{entry['id']}: acquired {len(data)} bytes matching the pinned digest"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report presence without fetching")
    args = parser.parse_args(argv)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures = 0
    for entry in manifest["documents"]:
        if args.check:
            target = document_path(entry["id"])
            if not target.is_file():
                print(f"{entry['id']}: ABSENT ({target.relative_to(ROOT)})")
                failures += 1
                continue
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            ok = digest == entry["sha256"]
            print(f"{entry['id']}: {'OK' if ok else 'DIGEST MISMATCH'}")
            failures += 0 if ok else 1
            continue
        ok, message = fetch(entry)
        print(message)
        failures += 0 if ok else 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
