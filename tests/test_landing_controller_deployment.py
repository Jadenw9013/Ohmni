"""The landing page embeds its same-origin controller viewer in production."""
import json
import shutil
from pathlib import Path

import pytest


@pytest.mark.parametrize("config", ["vercel.json", "apps/web/vercel.json"])
def test_public_host_allows_same_origin_viewer_but_not_cross_origin_frames(config):
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / config).read_text(encoding="utf-8"))
    headers = {item["key"].lower(): item["value"]
               for rule in data["headers"] if rule["source"] == "/(.*)"
               for item in rule["headers"]}
    assert headers["x-frame-options"] == "SAMEORIGIN"
    assert headers["x-content-type-options"] == "nosniff"


def test_container_behavior_inputs_resolve_without_the_development_checkout(tmp_path):
    from ohmni.application.component_behavior import ComponentBehaviorService
    from ohmni.behavior.loader import BehaviorRegistryError

    root = Path(__file__).resolve().parents[1]
    dockerfile = (root / "Dockerfile").read_text()
    for relative in ["src", "docs/behavior", "out/component-behavior/run/bench-results"]:
        assert f"COPY {relative}/" in dockerfile
        shutil.copytree(root / relative, tmp_path / relative)
    for relative in ["COMPONENT_BEHAVIOR_SPEC.md", "scripts/generate_behavior_examples.py"]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, target)
    service = ComponentBehaviorService(tmp_path, tmp_path / "new-runs")
    assert len(service.summary()) == service.registry.manifest.entry_count
    assert service.describe("OHM-001")["available"]
    # Packaging must retain validation: missing evidence cannot become a pass.
    (tmp_path / "COMPONENT_BEHAVIOR_SPEC.md").unlink()
    with pytest.raises(BehaviorRegistryError, match="missing source"):
        ComponentBehaviorService(tmp_path, tmp_path / "new-runs")
