"""Strict project-file CLI orchestration, independent of installed EDA tools."""

import json
from types import SimpleNamespace

import pytest

from ohmni.application.demo import RoutingIncompleteError
from ohmni.cli import EXIT_BLOCKED, EXIT_OK, EXIT_USAGE, main
from ohmni.synthesis import ArchetypeId, SpiPeripheralSlot, SynthesisBrief

FAMILIES = (
    SynthesisBrief(project_name="Sensor project"),
    SynthesisBrief(project_name="Button project", archetype=ArchetypeId.A2_USB_GPIO_CONTROLLER,
                   sensors=(), button_count=2, status_led_count=3),
    SynthesisBrief(project_name="Memory project", archetype=ArchetypeId.A3_USB_SPI_PERIPHERAL,
                   sensors=(), spi_devices=(SpiPeripheralSlot(part_id="25LC256-I/SN"),)),
)


def _brief_file(tmp_path, brief):
    path = tmp_path / "confirmed project.json"
    path.write_text(brief.model_dump_json(), encoding="utf-8-sig")
    return path


@pytest.mark.parametrize("brief", FAMILIES, ids=lambda brief: brief.archetype.value)
def test_preview_all_families_is_explicitly_unverified_and_never_starts_eda(tmp_path, monkeypatch, capsys, brief):
    from ohmni import cli

    path = _brief_file(tmp_path, brief)

    def unexpected_pipeline(*args, **kwargs):
        raise AssertionError("Preview must not start a build")

    monkeypatch.setattr(cli, "ProjectPipeline", unexpected_pipeline)
    assert main(["generate", "--brief", str(path), "--preview", "--json"]) == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["verification_status"] == "NOT_RUN"
    assert payload["archetype"] == brief.archetype.value
    assert payload["brief_fingerprint"] == brief.fingerprint
    assert payload["confirmed_brief"] == brief.model_dump(mode="json")
    assert payload["preview"]["asked_for"]
    assert "release have not run" in payload["limitation"]
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("brief", FAMILIES, ids=lambda brief: brief.archetype.value)
def test_build_all_families_passes_exact_brief_to_project_pipeline_and_saves_report(tmp_path, monkeypatch, capsys, brief):
    from ohmni import cli

    path = _brief_file(tmp_path, brief)
    output = tmp_path / "new board build"
    payload = {"mode": "bounded_synthesis", "project": {"name": brief.project_name},
               "release": {"status": "READY_FOR_MANUFACTURING_REVIEW", "current": True},
               "limitations": ["Not bench verified.", "Manufacturing profile and prices are synthetic."]}
    calls = []

    class Pipeline:
        def __init__(self, progress):
            self.progress = progress

        def run(self, destination, received):
            calls.append((destination, received))
            assert json.loads((destination / "confirmed-brief.json").read_text()) == brief.model_dump(mode="json")
            self.progress(SimpleNamespace(percent=40, label="Routing project copper", status="RUNNING"))
            # Files owned by the existing pipeline are retained, not rewritten
            # by the CLI presentation layer.
            (destination / "placement.json").write_text("pipeline placement")
            return SimpleNamespace(release=payload["release"], limitations=payload["limitations"],
                                   model_dump_json=lambda indent: json.dumps(payload, indent=indent))

    def unexpected_fixture(*args, **kwargs):
        raise AssertionError("Personal generation must not use a scripted provider")

    monkeypatch.setattr(cli, "ProjectPipeline", Pipeline)
    monkeypatch.setattr(cli, "flawed_logger_provider", unexpected_fixture)
    assert main(["generate", "--brief", str(path), "--output", str(output), "--json"]) == EXIT_OK
    captured = capsys.readouterr()
    assert json.loads(captured.out) == json.loads((output / "report.json").read_text()) == payload
    assert calls == [(output.resolve(), brief)]
    assert "RUNNING" in captured.err and "Routing" in captured.err
    assert json.loads((output / "preview.json").read_text())["verification_status"] == "NOT_RUN"
    assert (output / "placement.json").read_text() == "pipeline placement"
    assert not (output / "failure.json").exists()


@pytest.mark.parametrize("payload", ['not json', '[]', '{"status_led_count":"1"}',
                                    '{"include_programming_header":"false"}', '{"unexpected":true}',
                                    '{"budget_usd":NaN}'])
def test_invalid_json_or_coerced_fields_fail_before_build(tmp_path, monkeypatch, capsys, payload):
    from ohmni import cli

    path = tmp_path / "invalid.json"
    path.write_text(payload)
    monkeypatch.setattr(cli, "preview_project", lambda brief: pytest.fail("Invalid input reached preview"))
    output = tmp_path / "build"
    assert main(["generate", "--brief", str(path), "--output", str(output), "--json"]) == EXIT_USAGE
    assert json.loads(capsys.readouterr().out)["error"] == "invalid_brief"
    assert not output.exists()


def test_compiler_refusal_is_structured_and_precedes_directory_creation(tmp_path, monkeypatch, capsys):
    from ohmni import cli

    path = _brief_file(tmp_path, SynthesisBrief(input_power="battery"))
    output = tmp_path / "refused"
    monkeypatch.setattr(cli, "ProjectPipeline", lambda **kwargs: pytest.fail("Refused input reached EDA"))
    assert main(["generate", "--brief", str(path), "--output", str(output), "--json"]) == EXIT_BLOCKED
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "project_refused"
    assert payload["refusal"]["code"] == "input_power_unsupported"
    assert "input_power" in payload["refusal"]["field_paths"]
    assert not output.exists()


def test_existing_output_cannot_leave_previous_success_visible_on_a_failed_rerun(tmp_path, monkeypatch, capsys):
    from ohmni import cli

    path = _brief_file(tmp_path, FAMILIES[0])
    output = tmp_path / "previous build"
    output.mkdir()
    report = output / "report.json"
    report.write_text("previous report")
    monkeypatch.setattr(cli, "ProjectPipeline", lambda **kwargs: pytest.fail("Nonempty output was overwritten"))
    assert main(["generate", "--brief", str(path), "--output", str(output), "--json"]) == EXIT_USAGE
    assert json.loads(capsys.readouterr().out)["error"] == "output_not_empty"
    assert report.read_text() == "previous report"


@pytest.mark.parametrize("error,code", [(RoutingIncompleteError("The finite routing budget expired"), "routing_incomplete"),
                                       (RuntimeError("KiCad is unavailable"), "project_failed")])
def test_failed_build_retains_input_and_diagnostics_without_a_success_report(tmp_path, monkeypatch, capsys, error, code):
    from ohmni import cli

    path = _brief_file(tmp_path, FAMILIES[0])
    output = tmp_path / "failed build"

    class FailingPipeline:
        def __init__(self, progress):
            pass

        def run(self, destination, brief):
            raise error

    monkeypatch.setattr(cli, "ProjectPipeline", FailingPipeline)
    assert main(["generate", "--brief", str(path), "--output", str(output), "--json"]) == EXIT_BLOCKED
    assert json.loads(capsys.readouterr().out)["error"] == code
    assert json.loads((output / "failure.json").read_text())["error"] == code
    assert (output / "confirmed-brief.json").is_file()
    assert not (output / "report.json").exists()


def test_missing_input_and_ambiguous_output_flags_have_usage_exit_codes(tmp_path, capsys):
    missing = tmp_path / "missing.json"
    assert main(["generate", "--brief", str(missing), "--preview", "--json"]) == EXIT_USAGE
    assert json.loads(capsys.readouterr().out)["error"] == "brief_unreadable"
    assert main(["generate", "--brief", str(missing), "--json"]) == EXIT_USAGE
    assert json.loads(capsys.readouterr().out)["error"] == "invalid_arguments"
    assert main(["generate", "--brief", str(missing), "--preview", "--output", str(tmp_path), "--json"]) == EXIT_USAGE
    assert json.loads(capsys.readouterr().out)["error"] == "invalid_arguments"


@pytest.mark.parametrize("release", [{"status": "STALE", "current": False},
                                    {"status": "UNKNOWN", "current": True}])
def test_incomplete_release_status_never_becomes_success(tmp_path, monkeypatch, capsys, release):
    from ohmni import cli

    brief = FAMILIES[2]
    path = _brief_file(tmp_path, brief)
    payload = {"release": release, "limitations": ["Not bench verified."]}

    class Pipeline:
        def __init__(self, progress):
            pass

        def run(self, destination, received):
            return SimpleNamespace(release=release, limitations=payload["limitations"],
                                   model_dump_json=lambda indent: json.dumps(payload, indent=indent))

    monkeypatch.setattr(cli, "ProjectPipeline", Pipeline)
    assert main(["generate", "--brief", str(path), "--output", str(tmp_path / "build")]) == EXIT_BLOCKED
    output = capsys.readouterr().out
    assert f"Release: {release['status']}" in output
    assert "Memory project" in output and "Not bench verified." in output
    assert "BME280" not in output and "READY_FOR_MANUFACTURING_REVIEW" not in output
