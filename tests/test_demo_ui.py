"""Frontend structure and dependency-free component behavior."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from ohmni.application import DEMO_REQUEST


def test_ui_contains_every_major_truth_surface():
    web_root=Path(__file__).parents[1]/"apps"/"web"
    html=(web_root/"index.html").read_text(encoding="utf-8")
    app=(web_root/"app.js").read_text(encoding="utf-8")
    for section in ("overview","repair","evidence","notebook","artifacts","bom","release"):
        assert f'id="{section}"' in html
    text=html.lower()
    assert "deterministic demo" in text and "no live ai" in text
    assert '<textarea id="request" rows="5" readonly' in text and "fixed offline fixture" in text
    displayed=re.search(r'<textarea[^>]*id="request"[^>]*>(.*?)</textarea>',html,re.DOTALL)
    assert displayed and displayed.group(1).strip()==DEMO_REQUEST
    assert "production ready" not in text and "guaranteed manufacturable" not in text
    assert 'API_VERSION=2' in app and 'fetcher("/api/health",{cache:"no-store"})' in app
    assert '"X-Ohmni-Server-Instance"' in app and '"X-Ohmni-UI-Version"' in app
    assert "Demo could not be started" not in app


@pytest.mark.skipif(shutil.which("node") is None,reason="Node.js unavailable")
def test_frontend_view_model_behavior():
    result=subprocess.run(["node","--test","apps/web/tests/view-model.test.mjs"],cwd=Path(__file__).parents[1],capture_output=True,text=True,check=False,shell=False)
    assert result.returncode==0,result.stdout+result.stderr
    assert "# pass 9" in result.stdout
