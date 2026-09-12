"""The Freerouting adapter, with no Freerouting installed.

Every test runs offline through a stubbed `run_tool`, so the behaviour that
matters on a machine without the tool -- that it says so plainly and never
raises into the pipeline -- is checked on exactly such a machine.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ohmni.adapters import Router, ToolStatus
from ohmni.adapters.process import ToolTimeoutError
from ohmni.adapters.tools import FREEROUTING_ENV_VAR, FreeroutingCli, find_freerouting, probe_all
from ohmni.routing import freerouting
from ohmni.routing.freerouting import FreeroutingAdapter


@pytest.fixture(autouse=True)
def _unconfigured(monkeypatch):
    monkeypatch.delenv(FREEROUTING_ENV_VAR, raising=False)


def completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(["freerouting"], returncode, stdout, stderr)


def design(tmp_path: Path, name: str = "golden.dsn") -> Path:
    path = tmp_path / name
    path.write_text("(pcb golden)", encoding="utf-8")
    return path


class TestDiscovery:
    def test_a_missing_tool_is_unavailable_not_a_failure(self, monkeypatch):
        monkeypatch.setattr("ohmni.adapters.tools.shutil.which", lambda name: None)
        assert find_freerouting() is None
        availability = FreeroutingCli(None).availability()
        assert availability.status is ToolStatus.UNAVAILABLE
        assert "not required" in availability.detail

    def test_a_configured_path_is_used_when_it_exists(self, tmp_path, monkeypatch):
        binary = tmp_path / "freerouting.exe"
        binary.write_text("", encoding="utf-8")
        monkeypatch.setenv(FREEROUTING_ENV_VAR, str(binary))
        assert find_freerouting() == str(binary)

    def test_a_configured_path_that_is_not_there_finds_nothing(self, tmp_path, monkeypatch):
        monkeypatch.setenv(FREEROUTING_ENV_VAR, str(tmp_path / "absent.jar"))
        assert find_freerouting() is None

    def test_a_jar_without_java_cannot_run(self, monkeypatch):
        monkeypatch.setattr("ohmni.adapters.tools.shutil.which", lambda name: None)
        availability = FreeroutingCli("/opt/freerouting/freerouting.jar").availability()
        assert availability.status is ToolStatus.UNAVAILABLE and "java" in availability.detail

    def test_a_found_tool_does_not_claim_to_have_been_run(self):
        """Probing must not report OK on evidence it never gathered."""
        availability = FreeroutingCli("/usr/bin/freerouting").availability()
        assert availability.status is ToolStatus.OK
        assert "not executed at probe time" in availability.detail

    def test_the_doctor_reports_it_beside_the_other_tools(self):
        assert "freerouting" in {availability.name for availability in probe_all()}


class TestRouting:
    def test_it_satisfies_the_router_protocol(self):
        assert isinstance(FreeroutingAdapter("/usr/bin/freerouting"), Router)

    def test_without_the_tool_nothing_is_routed_and_nothing_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ohmni.adapters.tools.shutil.which", lambda name: None)
        result = FreeroutingAdapter().route(design(tmp_path), tmp_path)
        assert result.status is ToolStatus.UNAVAILABLE

    def test_a_board_file_is_refused_as_the_missing_export_it_is(self, tmp_path):
        """The .kicad_pcb is not a design file, and saying so beats a parse error."""
        board = tmp_path / "golden.kicad_pcb"
        board.write_text("(kicad_pcb)", encoding="utf-8")
        result = FreeroutingAdapter("/usr/bin/freerouting").route(board, tmp_path)
        assert result.status is ToolStatus.UNAVAILABLE
        assert "Specctra" in result.detail and "kicad-cli" in result.detail

    def test_a_missing_design_is_a_failure_rather_than_a_run(self, tmp_path):
        result = FreeroutingAdapter("/usr/bin/freerouting").route(tmp_path / "absent.dsn", tmp_path)
        assert result.status is ToolStatus.FAILED and "does not exist" in result.detail

    def test_a_successful_run_reports_the_session_it_wrote(self, tmp_path, monkeypatch):
        out = tmp_path / "out"
        calls = []

        def fake_run_tool(command, *, timeout):
            calls.append((command, timeout))
            (out / "golden.ses").write_text("(session golden)", encoding="utf-8")
            return completed(0)

        monkeypatch.setattr(freerouting, "run_tool", fake_run_tool)
        result = FreeroutingAdapter("/usr/bin/freerouting").route(design(tmp_path), out)
        assert result.status is ToolStatus.OK and "golden.ses" in result.detail
        # The session is explicitly not presented as verified copper.
        assert "not copper yet" in result.detail
        command, _ = calls[0]
        assert command[0] == "/usr/bin/freerouting"
        assert command[1:2] == ["-de"] and command[3:4] == ["-do"]
        assert isinstance(command, list)

    def test_a_jar_is_run_through_java(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ohmni.adapters.tools.shutil.which", lambda name: "/usr/bin/java")
        calls = []

        def fake_run_tool(command, *, timeout):
            calls.append(command)
            (tmp_path / "golden.ses").write_text("(session)", encoding="utf-8")
            return completed(0)

        monkeypatch.setattr(freerouting, "run_tool", fake_run_tool)
        result = FreeroutingAdapter("/opt/freerouting.jar").route(design(tmp_path), tmp_path)
        assert result.status is ToolStatus.OK
        assert calls[0][:3] == ["java", "-jar", "/opt/freerouting.jar"]

    def test_a_nonzero_exit_is_a_failure_with_the_tool_complaint(self, tmp_path, monkeypatch):
        monkeypatch.setattr(freerouting, "run_tool",
                            lambda command, *, timeout: completed(1, "", "no layers defined"))
        result = FreeroutingAdapter("/usr/bin/freerouting").route(design(tmp_path), tmp_path)
        assert result.status is ToolStatus.FAILED and "no layers defined" in result.detail

    def test_a_clean_exit_that_wrote_nothing_is_not_a_routed_board(self, tmp_path, monkeypatch):
        monkeypatch.setattr(freerouting, "run_tool", lambda command, *, timeout: completed(0))
        result = FreeroutingAdapter("/usr/bin/freerouting").route(design(tmp_path), tmp_path)
        assert result.status is ToolStatus.FAILED and "wrote no routing session" in result.detail

    def test_a_timeout_is_reported_as_a_timeout(self, tmp_path, monkeypatch):
        def timing_out(command, *, timeout):
            raise ToolTimeoutError(command, timeout)

        monkeypatch.setattr(freerouting, "run_tool", timing_out)
        result = FreeroutingAdapter("/usr/bin/freerouting", timeout_seconds=30).route(
            design(tmp_path), tmp_path)
        assert result.status is ToolStatus.TIMED_OUT and "30" in result.detail

    def test_a_tool_that_cannot_start_fails_rather_than_raising(self, tmp_path, monkeypatch):
        def missing(command, *, timeout):
            raise OSError("no such file")

        monkeypatch.setattr(freerouting, "run_tool", missing)
        result = FreeroutingAdapter("/usr/bin/freerouting").route(design(tmp_path), tmp_path)
        assert result.status is ToolStatus.FAILED


class TestItDoesNotTouchTheVerifiedPath:
    def test_the_pipeline_still_routes_with_the_deterministic_router(self):
        """Copper that ships is computed by Ohmni and checked by Ohmni."""
        from ohmni.application import demo

        source = Path(demo.__file__).read_text(encoding="utf-8")
        assert "DeterministicRouter().route(" in source
        assert "freerouting" not in source.lower()

    def test_released_copper_is_still_bound_to_a_verified_routing_plan(self):
        from ohmni.application import demo

        source = Path(demo.__file__).read_text(encoding="utf-8")
        assert "verify_routing(" in source and "_require_pcb_projection_lineage(" in source
