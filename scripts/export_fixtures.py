"""Emit every fixture circuit to JSON under fixtures/.

The Python builders are the authoring surface; the JSON files are the artifact
of record. Tests load the JSON, so a change to a builder that alters a fixture
shows up as a reviewable diff rather than silently changing what the regression
suite is testing.

Run:  python scripts/export_fixtures.py
"""

from __future__ import annotations

import json
from pathlib import Path

from ohmni.fixtures.esp32_env_logger import BUILDERS, requirements

OUT_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "esp32_env_logger"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    spec = requirements()
    (OUT_DIR / "requirements.json").write_text(
        json.dumps(spec.model_dump(mode="json", exclude_none=True), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote requirements.json ({spec.project_name})")

    for name, build in BUILDERS.items():
        circuit = build()
        payload = circuit.model_dump(mode="json", exclude_none=True)
        # The hash is derived, not stored, but writing it into the file gives a
        # reviewer something to eyeball when a fixture changes.
        payload["_content_hash"] = circuit.content_hash
        (OUT_DIR / f"{name}.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        print(
            f"wrote {name}.json  "
            f"({len(circuit.components)} components, {len(circuit.nets)} nets, "
            f"hash {circuit.content_hash[:12]})"
        )


if __name__ == "__main__":
    main()
