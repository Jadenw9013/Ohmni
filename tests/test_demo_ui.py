"""Frontend structure and dependency-free component behavior."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_ui_contains_every_major_truth_surface():
    html=(Path(__file__).parents[1]/"apps"/"web"/"index.html").read_text(encoding="utf-8")
    for section in ("overview","repair","evidence","notebook","artifacts","bom","release"):
        assert f'id="{section}"' in html
    text=html.lower()
    assert "deterministic demo" in text and "no live ai" in text
    assert "production ready" not in text and "guaranteed manufacturable" not in text


@pytest.mark.skipif(shutil.which("node") is None,reason="Node.js unavailable")
def test_frontend_view_model_behavior():
    result=subprocess.run(["node","--test","apps/web/tests/view-model.test.mjs"],cwd=Path(__file__).parents[1],capture_output=True,text=True,check=False,shell=False)
    assert result.returncode==0,result.stdout+result.stderr
    assert "# pass 4" in result.stdout

