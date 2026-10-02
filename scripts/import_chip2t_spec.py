"""Import the approved CHIP2T slice without fetching or interpreting remote sources.

Authoring-only dependency: PyYAML==6.0.3 (install into build/spec-tools or your dev env).
The runtime consumes committed JSON, never YAML or this Markdown document.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build" / "spec-tools"))
import yaml
from component_spec_metadata import library_metadata

IDS = [f"OHM-{n:03}" for n in [*range(1, 10), 14, *range(21, 28), 41, 42, 43]]


def extract(source: bytes) -> dict:
    text = source.decode("utf-8")
    entries = {}
    for match in re.finditer(r"^# \[(OHM-\d+)\].*?(?=^# \[|^## PROPOSED ADDITIONS|\Z)",
                             text, re.MULTILINE | re.DOTALL):
        if match[1] not in IDS:
            continue
        section = match[0]
        raw = re.search(r"```yaml\s*\n(.*?)\n```", section, re.DOTALL)[1]
        record = yaml.safe_load(raw)
        assert record["id"] == match[1]
        headings = dict(re.findall(r"^## ([^\n]+)\n(.*?)(?=^## |\Z)", section, re.MULTILINE | re.DOTALL))
        record["source"] = {
            "document": "PCB_COMPONENT_3D_LIBRARY_SPEC.md",
            "line": text[:match.start()].count("\n") + 1,
            "yaml_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "sections": {key: value.strip() for key, value in headings.items()
                         if key != "Structured Specification"},
            "evidence_level": "SPEC_REPORTED; cited documents not reverified by this importer",
        }
        entries[record["id"]] = record
    assert sorted(entries) == IDS
    profiles, components = {}, []
    for identifier in IDS:
        record = entries[identifier]
        profile = ("CURRENT_SENSE" if identifier == "OHM-014" else
                   "R" if int(identifier[4:]) < 10 else
                   "C" if int(identifier[4:]) < 28 else "L")
        key = f"{profile}.{record['package_member']}"
        profiles[key] = {"member": record["package_member"], "function": profile,
                         "dimensions_mm": record.pop("dimensions_mm")}
        notes = record["source"]["sections"]["Research Confidence"]
        uncertainties = [line.strip("- ") for line in notes.splitlines()
                         if any(word in line for word in ["Unresolved", "RESEARCH_REQUIRED", "partial"])]
        if identifier == "OHM-014":
            uncertainties += [
                "overall_height default 0.70 mm: resistance-range dependent, confidence L.",
                "terminal_length default 2.72 mm: second-pass narrative limits it to the lowest-ohm range (L); source YAML confidence M is preserved.",
                "MAT_ALLOY_MANGANIN is a G02 proposed token; appearance is an OHMNI default.",
                "3/4-terminal Kelvin layouts unresolved; only the default 2-terminal 2512 is supported.",
            ]
        if identifier == "OHM-043":
            uncertainties.append("terminal_length 0.50 mm is UNCERTAIN/L, borrowed from MLCC; not sourced for the inductor.")
        record["profile_id"] = key
        record["library_metadata"] = library_metadata(record, uncertainties,
            supported_variant="default_2_terminal",
            unsupported_variants=["wirewound", "Kelvin_3_terminal", "Kelvin_4_terminal"])
        components.append(record)
    return {
        "schema_version": 1,
        "source_spec_sha256": hashlib.sha256(source).hexdigest(),
        "family": {"id": "PKG-CHIP2T", "generator": "GEN-CHIP_2T", "profiles": profiles},
        "modeling_defaults": {
            "resistor_coat_mm": 0.03, "current_sense_coat_mm": 0.05,
            "edge_radius_mm": 0.02, "current_sense_chamfer_mm": 0.05,
            "cap_proudness_mm": 0,
            "basis": "OHMNI visual conventions; rounding uses the documented minimum; optional proudness omitted to preserve the envelope.",
        },
        "components": components,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = extract((ROOT / "PCB_COMPONENT_3D_LIBRARY_SPEC.md").read_bytes())
    target = ROOT / "apps/web/component-library/data/chip2t.json"
    encoded = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if target.read_text(encoding="utf-8") != encoded:
            raise SystemExit("CHIP2T data is stale relative to the supplied specification")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(encoded, encoding="utf-8", newline="\n")
    print(f"20 CHIP2T records {'checked' if args.check else 'imported'}; source {payload['source_spec_sha256']}")


if __name__ == "__main__":
    main()
