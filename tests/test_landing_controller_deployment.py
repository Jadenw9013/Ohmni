"""The landing page embeds its same-origin controller viewer in production."""
import json
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
