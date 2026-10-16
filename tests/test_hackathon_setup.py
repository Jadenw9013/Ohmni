"""Setup must fail closed and check mode must not install dependencies."""
import importlib.util
from pathlib import Path

import pytest


def load_script(name):
    path = Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def setup(monkeypatch, tmp_path):
    module = load_script("setup_hackathon")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module.sys, "version_info", (3, 13, 0))
    monkeypatch.setattr(module.sys, "platform", "linux")
    python = tmp_path / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.touch()
    return module


def test_check_mode_never_installs_and_requires_selected_capabilities(setup, monkeypatch):
    commands = []
    monkeypatch.setattr(setup, "run", lambda command: commands.append(command) or 0)
    assert setup.main(["--check", "--board"]) == 0
    assert not any("install" in command for command in commands)
    assert commands[-1][-3:] == ["--fetch", "--browser", "--board"]


def test_incompatible_existing_venv_stops_before_install(setup, monkeypatch):
    commands = []
    monkeypatch.setattr(setup, "run", lambda command: commands.append(command) or 2)
    assert setup.main([]) == 2
    assert len(commands) == 1
    assert "pip" not in commands[0]


@pytest.mark.parametrize("failure", ["pip", "playwright"])
def test_install_failure_cannot_report_success(setup, monkeypatch, failure):
    commands = []

    def run(command):
        commands.append(command)
        return 1 if failure in command and "install" in command else 0

    monkeypatch.setattr(setup, "run", run)
    assert setup.main([]) == 2
    assert not any("scripts/hackathon_preflight.py" in command for command in commands)


def test_backend_setup_does_not_download_or_require_chromium(setup, monkeypatch):
    commands = []
    monkeypatch.setattr(setup, "run", lambda command: commands.append(command) or 0)
    assert setup.main(["--skip-browser"]) == 0
    assert any(".[dev,mcp,browser,fetch]" in command for command in commands)
    assert not any("playwright" in command for command in commands)
    assert "--browser" not in commands[-1]


def test_missing_venv_in_check_mode_is_not_created(setup):
    (setup.ROOT / ".venv/bin/python").unlink()
    assert setup.main(["--check"]) == 2
    assert not (setup.ROOT / ".venv/bin/python").exists()


def test_windows_venv_path_with_spaces_is_one_argument(setup, monkeypatch, tmp_path):
    root = tmp_path / "teammate checkout"
    python = root / ".venv/Scripts/python.exe"
    python.parent.mkdir(parents=True)
    python.touch()
    monkeypatch.setattr(setup, "ROOT", root)
    monkeypatch.setattr(setup.sys, "platform", "win32")
    commands = []
    monkeypatch.setattr(setup, "run", lambda command: commands.append(command) or 0)
    assert setup.main(["--check", "--skip-browser"]) == 0
    assert all(command[0] == str(python) for command in commands)


def test_wrong_fetch_pin_blocks_readiness(monkeypatch):
    preflight = load_script("hackathon_preflight")
    monkeypatch.setattr(preflight.sys, "version_info", (3, 13, 0))
    versions = {"mcp": "2.2.0", "uagents": "0.26.0", "uagents-core": "0.4.12"}
    monkeypatch.setattr(preflight.metadata, "version", lambda name: versions.get(name, "1.0"))
    checks = preflight.inspect(False, require_fetch=True)
    assert any(c["name"] == "uagents" and c["status"] == "BLOCKED" for c in checks)


def test_installed_fetch_sdk_accepts_complete_acp_handlers_without_agent_startup():
    uagents = pytest.importorskip("uagents", reason="install the fetch extra for SDK smoke test")
    from uagents_core.contrib.protocols.chat import (
        ChatAcknowledgement,
        ChatMessage,
        chat_protocol_spec,
    )

    protocol = uagents.Protocol(spec=chat_protocol_spec)

    @protocol.on_message(ChatMessage)
    async def receive_message(ctx, sender, message):
        pass

    @protocol.on_message(ChatAcknowledgement)
    async def receive_acknowledgement(ctx, sender, message):
        pass

    assert protocol.verify()
