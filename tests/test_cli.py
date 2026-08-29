"""CLI behaviour, including its exit codes.

`verify` is meant to be usable in CI on its own, so the exit code has to mean
what it says: non-zero exactly when the design cannot be exported as verified.
"""

from __future__ import annotations

import json

import pytest

from ohmni.cli import EXIT_BLOCKED, EXIT_OK, main
from ohmni.fixtures.esp32_env_logger import BROKEN_VARIANTS


class TestExitCodes:
    def test_golden_exits_zero(self, capsys):
        assert main(["verify", "golden"]) == EXIT_OK
        assert "export allowed" in capsys.readouterr().out

    @pytest.mark.parametrize("name", sorted(BROKEN_VARIANTS))
    def test_broken_variants_exit_nonzero(self, name, capsys):
        assert main(["verify", name]) == EXIT_BLOCKED
        assert "export BLOCKED" in capsys.readouterr().out

    def test_regression_sweep_passes(self, capsys):
        assert main(["verify-all"]) == EXIT_OK
        assert "behaved as intended" in capsys.readouterr().out


class TestOutputFormats:
    def test_json_output_is_parseable_and_carries_the_summary(self, capsys):
        main(["verify", "golden", "--json"])
        payload = json.loads(capsys.readouterr().out)
        # A consumer must not have to re-derive the gate or the coverage.
        assert payload["export_blocked"] is False
        assert payload["coverage"] == 1.0
        assert payload["counts_by_severity"]["critical"] == 0
        assert len(payload["results"]) == 24

    def test_report_names_what_it_did_not_verify(self, capsys):
        main(["verify", "golden"])
        out = capsys.readouterr().out
        assert "What a pass here does not establish" in out
        assert "UNSUPPORTED" in out  # eda and simulation subsystems

    def test_verbose_lists_every_rule(self, capsys):
        main(["verify", "golden", "--verbose"])
        out = capsys.readouterr().out
        assert "PB-PWR-001" in out
        assert "PB-USB-001" in out

    def test_rules_and_parts_listings(self, capsys):
        assert main(["rules"]) == EXIT_OK
        assert "deterministic rules" in capsys.readouterr().out
        assert main(["parts"]) == EXIT_OK
        assert "ESP32-WROOM-32E" in capsys.readouterr().out

    def test_doctor_never_claims_a_missing_tool_passed(self, capsys):
        assert main(["doctor"]) == EXIT_OK
        out = capsys.readouterr().out
        assert "UNSUPPORTED, never as a pass" in out


class TestFileInput:
    def test_verifies_a_circuit_from_disk(self, tmp_path, capsys, golden):
        path = tmp_path / "circuit.json"
        path.write_text(golden.model_dump_json(), encoding="utf-8")
        assert main(["verify", "--file", str(path)]) == EXIT_OK
        assert golden.content_hash[:16] in capsys.readouterr().out

    def test_unknown_fixture_is_a_usage_error(self, capsys):
        assert main(["verify", "not-a-fixture"]) == 2
        assert "unknown fixture" in capsys.readouterr().err


class TestEntryPointDoesNotRunOnImport:
    def test_importing_main_module_is_inert(self):
        """Regression: `__main__.py` used to run the CLI when imported.

        Anything that walks the package -- the module-import test, a doc tool,
        an IDE -- would execute the CLI against whatever argv was current.
        """
        import importlib

        module = importlib.import_module("ohmni.__main__")
        assert hasattr(module, "main")
