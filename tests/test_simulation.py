"""SPICE export and operating-point simulation, with no ngspice installed.

Every test here runs offline. The parser is exercised against literal ngspice
batch output, and the two adapters are driven through a stubbed `run_tool`, so
the behaviour that matters -- that nothing without a real result is ever
reported as one -- is checked on a machine where ngspice is absent, which is
the machine most of these will run on.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from ohmni.adapters import (
    SimulationRun,
    ToolAvailability,
    ToolStatus,
    TransientData,
    TransientSeries,
)
from ohmni.adapters.process import ToolTimeoutError
from ohmni.domain.evidence import EvidenceKind
from ohmni.domain.units import Unit
from ohmni.eda import simulation
from ohmni.eda.simulation import (
    BEHAVIOURAL_APPROXIMATION,
    IDEAL_COMPONENTS,
    KiCadNetlistExporter,
    NgspiceAdapter,
    _not_run,
    describe_netlist,
    model_fidelity,
    operating_point_deck,
    operating_point_for,
    parse_operating_point,
    simulation_run_id,
)

GOLDEN_NETLIST = """.title KiCad schematic
C1 VBUS GND 1u
R1 CC1 GND 5.1k
U1 __U1
.end
"""

PRINT_OP_STDOUT = """
Circuit: .title KiCad schematic

Doing analysis at TEMP = 27.000000 and TNOM = 27.000000

No. of Data Rows : 1
        V(net1) = 3.300000e+00
        v(gnd) = 0.000000e+00
        I(V1) = -1.250000e-03
        v1#branch = -1.250000e-03
"""

OP_TABLE_STDOUT = """
\tNode                                  \tVoltage
\t----                                  \t-------
\t3v3                                   \t3.3
\tvbus                                  \t5.05

\tSource\tCurrent
\t------\t-------
\tv1#branch\t-1.2e-03

\tTEMP\t27.0
"""


def completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(["ngspice"], returncode, stdout, stderr)


class FakeSpice:
    """A SpiceTool stub whose availability is whatever a test needs it to be."""

    def __init__(self, status: ToolStatus = ToolStatus.OK, detail: str | None = None) -> None:
        self.status, self.detail, self.calls = status, detail, []

    def availability(self) -> ToolAvailability:
        return ToolAvailability(name="ngspice", status=self.status, detail=self.detail)

    def operating_point(self, netlist, run_id, *, work_dir=None):
        self.calls.append((netlist, run_id, work_dir))
        return simulation._not_run(run_id, ToolStatus.OK, IDEAL_COMPONENTS, "stub run")


def _write_netlist(tmp_path: Path, text: str):
    """Stand in for kicad-cli: write the netlist the exporter will read back."""
    run_id = simulation.simulation_run_id(artifact(tmp_path))
    (tmp_path / f"{run_id}.cir").write_text(text, encoding="utf-8")
    return completed(0)


def artifact(tmp_path: Path, *, current: bool = True) -> SimpleNamespace:
    path = tmp_path / "golden.kicad_sch"
    path.write_text("(kicad_sch)", encoding="utf-8")
    return SimpleNamespace(path=path, is_current=current,
                           fingerprint=SimpleNamespace(digest="a" * 64))


class TestParser:
    def test_marked_values_become_typed_voltages_and_currents(self):
        point = parse_operating_point(PRINT_OP_STDOUT)
        assert set(point.node_voltages) == {"net1", "gnd"}
        assert point.node_voltages["net1"].value == pytest.approx(3.3)
        assert point.node_voltages["net1"].unit is Unit.VOLT
        assert point.node_voltages["gnd"].value == 0.0
        assert point.branch_currents["v1"].value == pytest.approx(-1.25e-3)
        assert point.branch_currents["v1"].unit is Unit.AMPERE

    def test_the_plain_op_tables_are_read_only_under_their_own_headers(self):
        point = parse_operating_point(OP_TABLE_STDOUT)
        assert point.node_voltages["3v3"].value == pytest.approx(3.3)
        assert point.node_voltages["vbus"].value == pytest.approx(5.05)
        assert point.branch_currents["v1"].value == pytest.approx(-1.2e-3)
        # The temperature row sits under no header, so it is not a voltage.
        assert "temp" not in point.node_voltages and "temp" not in point.branch_currents

    @pytest.mark.parametrize(
        ("line", "name", "value"),
        [
            ("V(net1) = 3.300000e+00", "net1", 3.3),
            ("v(3v3)=3.3", "3v3", 3.3),
            ("V( vbus ) = 5.05", "vbus", 5.05),
            ("v(n1) -2.5", "n1", -2.5),
            ("V(n2) = .5", "n2", 0.5),
            ("V(n3) = +1E3", "n3", 1000.0),
        ],
    )
    def test_voltage_spellings_ngspice_actually_emits(self, line, name, value):
        assert parse_operating_point(line).node_voltages[name].value == pytest.approx(value)

    def test_nothing_that_is_not_marked_as_electrical_is_read(self):
        noise = """
        Doing analysis at TEMP = 27.000000 and TNOM = 27.000000
        No. of Data Rows : 1
        total elapsed time: 0.004 seconds
        binary raw file written
        warning: node 3v3 has 2 connections
        """
        point = parse_operating_point(noise)
        assert not point.node_voltages and not point.branch_currents

    def test_empty_output_is_an_empty_result_not_a_crash(self):
        for text in ("", "\n\n", None):
            point = parse_operating_point(text)
            assert not point.node_voltages and not point.branch_currents


class TestDeckPreparation:
    def test_the_operating_point_commands_are_added_before_end(self):
        deck = operating_point_deck(GOLDEN_NETLIST).splitlines()
        assert deck[0] == ".title KiCad schematic"
        assert deck[-1] == ".end"
        assert deck[-3:-1] == [".op", ".print op"]

    def test_existing_commands_are_never_duplicated(self):
        deck = operating_point_deck(".title t\n.op\n.print op\nR1 a b 1k\n.end\n")
        assert deck.lower().count(".op\n") == 1 and deck.lower().count(".print op") == 1

    def test_option_is_not_op_and_ends_is_not_end(self):
        """A prefix match here would drop the analysis or corrupt a subcircuit."""
        deck = operating_point_deck(".title t\n.options savecurrents\n.subckt x a b\n.ends\nR1 a b 1k\n.end\n")
        lines = [line.strip() for line in deck.splitlines()]
        assert ".op" in lines and ".print op" in lines
        assert lines.index(".op") > lines.index(".ends")
        assert lines[-1] == ".end"

    def test_a_deck_without_end_still_gets_one(self):
        deck = operating_point_deck("R1 a b 1k")
        assert deck.splitlines() == ["R1 a b 1k", ".op", ".print op", ".end"]


class TestFidelity:
    def test_a_deck_with_no_models_is_ideal_components(self):
        assert model_fidelity(GOLDEN_NETLIST) == IDEAL_COMPONENTS

    def test_a_deck_carrying_models_is_a_behavioural_approximation(self):
        assert model_fidelity(".model D1 D(is=1e-14)\n") == BEHAVIOURAL_APPROXIMATION
        assert model_fidelity(".SUBCKT reg in out\n.ends\n") == BEHAVIOURAL_APPROXIMATION

    def test_no_path_reports_a_vendor_model(self):
        """Ohmni attaches none, so no run here may claim one."""
        for netlist in (GOLDEN_NETLIST, ".model D1 D()\n", "", "V1 a 0 5\n"):
            assert model_fidelity(netlist) != "vendor_model"

    def test_the_netlist_description_states_what_decides_meaning(self):
        described = describe_netlist(GOLDEN_NETLIST)
        assert "device models: none" in described and "independent source: none" in described
        assert "independent source: present" in describe_netlist("V1 vbus 0 5\n")


class TestNgspiceAdapterWithoutNgspice:
    """Pinned to a host with no ngspice, whatever the host actually has."""

    @pytest.fixture(autouse=True)
    def _no_ngspice(self, monkeypatch):
        monkeypatch.setattr(simulation, "find_ngspice", lambda: None)

    def test_a_missing_executable_is_unavailable_not_a_failure(self):
        availability = NgspiceAdapter().availability()
        assert availability.status is ToolStatus.UNAVAILABLE
        assert "ngspice" in (availability.detail or "").lower()

    def test_an_unavailable_run_reports_no_operating_point_and_writes_nothing(self, tmp_path):
        run = NgspiceAdapter().operating_point(GOLDEN_NETLIST, "run-1", work_dir=tmp_path)
        assert run.status is ToolStatus.UNAVAILABLE
        assert run.operating_point is None and not run.evidence
        assert run.analysis == "op" and run.model_fidelity == IDEAL_COMPONENTS
        assert "not a pass" in (run.detail or "")
        assert not list(tmp_path.iterdir())

    def test_an_empty_netlist_is_refused_before_any_run(self):
        run = NgspiceAdapter(executable="ngspice").operating_point("   ", "run-1")
        assert run.status is ToolStatus.FAILED and run.operating_point is None


class TestNgspiceAdapterRuns:
    """Drives the real code path with `run_tool` replaced, so no tool is needed."""

    def _adapter(self, monkeypatch, result):
        calls = []

        def fake_run_tool(command, *, timeout):
            calls.append((command, timeout))
            if isinstance(result, BaseException):
                raise result
            return result

        monkeypatch.setattr(simulation, "run_tool", fake_run_tool)
        return NgspiceAdapter(executable="ngspice"), calls

    def test_a_successful_run_returns_the_parsed_operating_point(self, monkeypatch, tmp_path):
        adapter, calls = self._adapter(monkeypatch, completed(0, PRINT_OP_STDOUT))
        run = adapter.operating_point(GOLDEN_NETLIST, "run-1", work_dir=tmp_path)
        assert run.status is ToolStatus.OK
        assert run.operating_point.node_voltages["net1"].value == pytest.approx(3.3)
        assert run.model_fidelity == IDEAL_COMPONENTS
        assert run.evidence[0].kind is EvidenceKind.SIMULATION
        assert run.evidence[0].source_id == "run-1"
        # A fixed argument vector, never a shell string (SECURITY.md).
        command, _ = calls[0]
        assert command[:2] == ["ngspice", "-b"] and isinstance(command, list)
        # The deck that ran is kept where the caller asked for it.
        assert run.netlist_path is not None and Path(run.netlist_path).read_text().endswith(".end\n")

    def test_a_temporary_deck_is_cleaned_up_and_never_reported_as_a_path(self, monkeypatch):
        adapter, calls = self._adapter(monkeypatch, completed(0, PRINT_OP_STDOUT))
        run = adapter.operating_point(GOLDEN_NETLIST, "run-1")
        assert run.status is ToolStatus.OK and run.netlist_path is None
        assert not Path(calls[0][0][2]).exists()

    def test_a_nonzero_exit_is_a_failure_with_no_invented_result(self, monkeypatch):
        adapter, _ = self._adapter(
            monkeypatch, completed(1, "", "Error on line 4: unknown device type\n"))
        run = adapter.operating_point(GOLDEN_NETLIST, "run-1")
        assert run.status is ToolStatus.FAILED
        assert run.operating_point is None and not run.evidence
        assert "unknown device type" in (run.detail or "")

    def test_a_clean_exit_with_nothing_to_read_is_not_a_pass(self, monkeypatch):
        adapter, _ = self._adapter(monkeypatch, completed(0, "total elapsed time: 0.01 seconds\n"))
        run = adapter.operating_point(GOLDEN_NETLIST, "run-1")
        assert run.status is ToolStatus.FAILED and run.operating_point is None
        assert "without reporting an operating point" in (run.detail or "")

    def test_a_timeout_is_reported_as_a_timeout(self, monkeypatch):
        adapter, _ = self._adapter(monkeypatch, ToolTimeoutError(["ngspice"], 60))
        run = adapter.operating_point(GOLDEN_NETLIST, "run-1")
        assert run.status is ToolStatus.TIMED_OUT and run.operating_point is None

    def test_a_tool_that_cannot_start_fails_rather_than_raising(self, monkeypatch):
        adapter, _ = self._adapter(monkeypatch, OSError("no such file"))
        run = adapter.operating_point(GOLDEN_NETLIST, "run-1")
        assert run.status is ToolStatus.FAILED and run.operating_point is None


class TestNetlistExporter:
    def test_a_missing_kicad_cli_is_unavailable(self, tmp_path, monkeypatch):
        monkeypatch.setattr(simulation, "find_kicad_cli", lambda: None)
        exporter = KiCadNetlistExporter()
        assert exporter.availability().status is ToolStatus.UNAVAILABLE
        export = exporter.export(artifact(tmp_path))
        assert export.status is ToolStatus.UNAVAILABLE and not export.usable

    def test_a_schematic_that_changed_is_not_exported_from(self, tmp_path):
        export = KiCadNetlistExporter(executable="kicad-cli").export(
            artifact(tmp_path, current=False))
        assert export.status is ToolStatus.FAILED and "changed after compilation" in export.detail

    def test_a_successful_export_returns_the_netlist_text(self, monkeypatch, tmp_path):
        destination = tmp_path / "golden.cir"

        def fake_run_tool(command, *, timeout):
            destination.write_text(GOLDEN_NETLIST, encoding="utf-8")
            return completed(0)

        monkeypatch.setattr(simulation, "run_tool", fake_run_tool)
        export = KiCadNetlistExporter(executable="kicad-cli").export(artifact(tmp_path), destination)
        assert export.status is ToolStatus.OK and export.usable
        assert export.text == GOLDEN_NETLIST and export.path == str(destination)

    def test_a_reported_success_that_wrote_nothing_is_a_failure(self, monkeypatch, tmp_path):
        destination = tmp_path / "empty.cir"

        def fake_run_tool(command, *, timeout):
            destination.write_text("   \n", encoding="utf-8")
            return completed(0)

        monkeypatch.setattr(simulation, "run_tool", fake_run_tool)
        export = KiCadNetlistExporter(executable="kicad-cli").export(artifact(tmp_path), destination)
        assert export.status is ToolStatus.FAILED and not export.usable

    def test_a_failed_export_keeps_the_tool_complaint(self, monkeypatch, tmp_path):
        monkeypatch.setattr(simulation, "run_tool",
                            lambda command, *, timeout: completed(2, "", "Error: cannot open file\n"))
        export = KiCadNetlistExporter(executable="kicad-cli").export(artifact(tmp_path))
        assert export.status is ToolStatus.FAILED and "cannot open file" in export.detail


class TestOperatingPointFor:
    def test_without_ngspice_nothing_is_exported_at_all(self, tmp_path):
        exported = []

        class Refusing:
            def export(self, *args, **kwargs):
                exported.append(args)
                raise AssertionError("no netlist should be exported without ngspice")

        run = operating_point_for(artifact(tmp_path), exporter=Refusing(),
                                  spice=FakeSpice(ToolStatus.UNAVAILABLE, "ngspice was not found"),
                                  work_dir=tmp_path)
        assert run.status is ToolStatus.UNAVAILABLE and run.operating_point is None
        assert not exported

    def test_an_export_failure_stops_short_of_a_simulation(self, tmp_path, monkeypatch):
        monkeypatch.setattr(simulation, "run_tool",
                            lambda command, *, timeout: completed(3, "", "Error: no such file\n"))
        spice = FakeSpice()
        run = operating_point_for(artifact(tmp_path),
                                  exporter=KiCadNetlistExporter(executable="kicad-cli"),
                                  spice=spice, work_dir=tmp_path)
        assert run.status is ToolStatus.FAILED and run.operating_point is None
        assert not spice.calls

    def test_an_unexpected_failure_is_recorded_rather_than_raised(self, tmp_path):
        class Exploding:
            def export(self, *args, **kwargs):
                raise RuntimeError("something nobody predicted")

        run = operating_point_for(artifact(tmp_path), exporter=Exploding(), spice=FakeSpice())
        assert run.status is ToolStatus.FAILED and run.operating_point is None
        assert "RuntimeError" in (run.detail or "")

    def test_the_run_id_is_stable_for_one_artifact(self, tmp_path):
        first, second = artifact(tmp_path), artifact(tmp_path)
        assert simulation_run_id(first) == simulation_run_id(second)
        assert len(simulation_run_id(first)) == 16


class TestOrchestratorIntegration:
    def test_a_design_without_eda_carries_no_simulation_at_all(self):
        """None means nothing was attempted; it is not an UNAVAILABLE result."""
        from ohmni.catalog import default_catalog
        from ohmni.generation import DesignOrchestrator
        from ohmni.generation.fixtures import GOLDEN_REQUEST, flawed_logger_provider

        report = DesignOrchestrator(flawed_logger_provider(), default_catalog()).design(
            GOLDEN_REQUEST, run_eda=False)
        assert report.state.value == "complete"
        assert report.simulation is None

    def test_an_unavailable_simulation_is_recorded_without_failing_the_design(self, tmp_path, monkeypatch):
        from ohmni.catalog import default_catalog
        from ohmni.eda.kicad import KiCadCliAdapter, KiCadSchematicCompiler
        from ohmni.generation import DesignOrchestrator, orchestrator
        from ohmni.generation.fixtures import GOLDEN_REQUEST, flawed_logger_provider

        # Both external tools are absent for this run: the point is that the
        # design still completes, and says so rather than implying a pass.
        monkeypatch.setattr(KiCadCliAdapter, "__init__",
                            lambda self, *args, **kwargs: setattr(self, "executable", None)
                            or setattr(self, "timeout_seconds", 60))
        monkeypatch.setattr(orchestrator, "operating_point_for",
                            lambda artifact, **kwargs: simulation._not_run(
                                "run-1", ToolStatus.UNAVAILABLE, IDEAL_COMPONENTS, "ngspice missing"))
        report = DesignOrchestrator(flawed_logger_provider(), default_catalog()).design(
            GOLDEN_REQUEST, output=tmp_path / "golden.kicad_sch", run_eda=True)
        assert report.state.value == "complete"
        assert report.simulation is not None
        assert report.simulation.status is ToolStatus.UNAVAILABLE
        assert report.simulation.operating_point is None
        assert any("ngspice unavailable" in issue.message for issue in report.issues)
        assert any(event.kind.value == "tool_unavailable" for event in report.notebook.events)
        assert isinstance(KiCadSchematicCompiler(default_catalog()), KiCadSchematicCompiler)


DRIVEN_NETLIST = """.title driven
V1 vbus 0 5
R1 vbus 3v3 100
C1 3v3 0 1u
.end
"""

TRAN_STDOUT = """
Circuit: .title driven

Doing analysis at TEMP = 27.000000 and TNOM = 27.000000

Index   time            v(vbus)         v(3v3)
--------------------------------------------------------
0\t0.000000e+00\t5.000000e+00\t0.000000e+00
1\t1.000000e-05\t5.000000e+00\t4.750000e-01
2\t2.000000e-05\t5.000000e+00\t9.060000e-01

Index   time            v(vbus)         v(3v3)
--------------------------------------------------------
3\t3.000000e-05\t5.000000e+00\t1.296000e+00
"""


class TestTransientDeck:
    def test_the_nodes_to_print_come_from_the_element_lines(self):
        assert simulation.netlist_nodes(DRIVEN_NETLIST) == ["vbus", "3v3"]

    def test_ground_is_never_printed(self):
        """It is zero by definition; a graph of it teaches nothing."""
        assert "0" not in simulation.netlist_nodes("V1 a 0 5\nR1 a gnd 1k\n")

    def test_a_value_is_never_mistaken_for_a_node(self):
        """`v(4.7k)` would make ngspice reject the whole deck."""
        assert simulation.netlist_nodes("R1 sda 3v3 4.7k\n") == ["sda", "3v3"]

    def test_a_device_of_unknown_shape_is_skipped_rather_than_guessed(self):
        assert simulation.netlist_nodes("U1 __U1\nX1 a b amp\nR1 a b 1k\n") == ["a", "b"]

    def test_the_signal_list_is_bounded(self):
        netlist = "\n".join(f"R{index} n{index} n{index + 1} 1k" for index in range(40))
        assert len(simulation.netlist_nodes(netlist)) == simulation.MAX_TRANSIENT_SIGNALS

    def test_the_analysis_and_print_go_in_before_end(self):
        deck = simulation.transient_deck(DRIVEN_NETLIST, "10us", "1ms", ["vbus", "3v3"])
        lines = deck.splitlines()
        assert lines[0] == ".title driven" and lines[-1] == ".end"
        assert lines[-3] == ".tran 10us 1ms"
        assert lines[-2] == ".print tran v(vbus) v(3v3)"

    def test_existing_commands_are_not_duplicated(self):
        deck = simulation.transient_deck(
            ".title t\n.tran 1us 2ms\n.print tran v(a)\nR1 a 0 1k\n.end\n", "10us", "1ms", ["a"])
        assert deck.lower().count(".tran") == 1 and deck.lower().count(".print tran") == 1


class TestTransientParser:
    def test_columns_become_a_time_axis_and_one_series_each(self):
        data = simulation.parse_transient(TRAN_STDOUT, analysis=".tran 10us 1ms")
        assert data.analysis == ".tran 10us 1ms"
        assert data.time_s == [0.0, 1e-05, 2e-05, 3e-05]
        assert [series.name for series in data.series] == ["v(vbus)", "v(3v3)"]
        assert data.series[0].values == [5.0, 5.0, 5.0, 5.0]
        assert data.series[1].values == [0.0, 0.475, 0.906, 1.296]
        assert data.sample_count == 4

    def test_a_repeated_page_header_is_not_parsed_as_data(self):
        """ngspice pages the table; the fourth row arrives under a second header."""
        data = simulation.parse_transient(TRAN_STDOUT, analysis="t")
        assert len(data.time_s) == 4
        assert all(len(series.values) == 4 for series in data.series)

    def test_a_current_column_is_amperes_and_a_voltage_column_is_volts(self):
        stdout = "Index   time   v(a)   i(v1)\n----\n0\t0.0\t1.0\t-0.002\n"
        data = simulation.parse_transient(stdout, analysis="t")
        assert [series.unit for series in data.series] == [Unit.VOLT, Unit.AMPERE]

    def test_a_partial_row_is_dropped_rather_than_padded(self):
        stdout = "Index   time   v(a)   v(b)\n----\n0\t0.0\t1.0\t2.0\n1\t1e-05\t1.5\n"
        data = simulation.parse_transient(stdout, analysis="t")
        assert data.time_s == [0.0]

    def test_output_with_no_table_is_an_empty_result_not_a_crash(self):
        for text in ("", None, "total elapsed time: 0.01 seconds\n"):
            data = simulation.parse_transient(text, analysis="t")
            assert not data.time_s and not data.series

    def test_a_long_run_is_thinned_and_says_so(self):
        rows = "\n".join(f"{index}\t{index * 1e-06:.6e}\t{index * 0.01:.6e}"
                         for index in range(5000))
        data = simulation.parse_transient(
            f"Index   time   v(a)\n----\n{rows}\n", analysis="t")
        assert data.decimated_from == 5000
        assert data.sample_count <= simulation.MAX_TRANSIENT_SAMPLES + 1
        # The end of the curve survives the thinning: a settling waveform whose
        # last sample was dropped would look like it never arrived.
        assert data.time_s[0] == 0.0
        assert data.series[0].values[-1] == pytest.approx(4999 * 0.01)

    def test_a_short_run_is_not_marked_as_thinned(self):
        data = simulation.parse_transient(TRAN_STDOUT, analysis="t")
        assert data.decimated_from is None


class TestTransientAnalysis:
    def _adapter(self, monkeypatch, result):
        def fake_run_tool(command, *, timeout):
            if isinstance(result, BaseException):
                raise result
            return result

        monkeypatch.setattr(simulation, "run_tool", fake_run_tool)
        return NgspiceAdapter(executable="ngspice")

    def test_a_successful_run_returns_curves_and_evidence(self, monkeypatch, tmp_path):
        adapter = self._adapter(monkeypatch, completed(0, TRAN_STDOUT))
        run = adapter.transient_analysis(DRIVEN_NETLIST, "run-1", "10us", "1ms",
                                         work_dir=tmp_path)
        assert run.status is ToolStatus.OK
        assert run.analysis == ".tran 10us 1ms"
        assert run.transient_data.sample_count == 4
        assert run.operating_point is None
        assert run.evidence[0].kind is EvidenceKind.SIMULATION
        assert run.evidence[0].source_id == "run-1"
        assert Path(run.netlist_path).read_text().count(".tran 10us 1ms") == 1

    def test_without_ngspice_no_curve_is_reported(self, monkeypatch, tmp_path):
        monkeypatch.setattr(simulation, "find_ngspice", lambda: None)
        run = NgspiceAdapter().transient_analysis(DRIVEN_NETLIST, "run-1", work_dir=tmp_path)
        assert run.status is ToolStatus.UNAVAILABLE
        assert run.transient_data is None and run.analysis == ".tran 10us 1ms"
        assert not list(tmp_path.iterdir())

    def test_a_clean_exit_with_no_table_is_not_an_empty_graph(self, monkeypatch):
        """An empty plot of a real circuit is the most misleading result here."""
        adapter = self._adapter(monkeypatch, completed(0, "total elapsed time: 0.01\n"))
        run = adapter.transient_analysis(DRIVEN_NETLIST, "run-1")
        assert run.status is ToolStatus.FAILED and run.transient_data is None
        assert "without reporting a transient" in run.detail

    def test_a_nonzero_exit_is_a_failure(self, monkeypatch):
        adapter = self._adapter(monkeypatch, completed(1, "", "Error: no such node\n"))
        run = adapter.transient_analysis(DRIVEN_NETLIST, "run-1")
        assert run.status is ToolStatus.FAILED and "no such node" in run.detail

    def test_a_timeout_is_reported_as_a_timeout(self, monkeypatch):
        adapter = self._adapter(monkeypatch, ToolTimeoutError(["ngspice"], 60))
        run = adapter.transient_analysis(DRIVEN_NETLIST, "run-1")
        assert run.status is ToolStatus.TIMED_OUT and run.transient_data is None

    def test_a_netlist_with_nothing_to_print_is_refused_before_running(self, monkeypatch):
        called = []
        monkeypatch.setattr(simulation, "run_tool",
                            lambda command, *, timeout: called.append(command))
        run = NgspiceAdapter(executable="ngspice").transient_analysis("U1 __U1\n.end\n", "run-1")
        assert run.status is ToolStatus.FAILED and "nothing to plot" in run.detail
        assert not called


class TestTransientInThePipeline:
    def test_an_undriven_netlist_never_spends_a_transient(self, tmp_path, monkeypatch):
        """Every netlist KiCad exports from an Ohmni schematic is this one."""
        spice = FakeSpice()
        spice.transient_calls = []
        spice.transient_analysis = lambda *args, **kwargs: spice.transient_calls.append(args)
        monkeypatch.setattr(simulation, "run_tool",
                            lambda command, *, timeout: _write_netlist(tmp_path, GOLDEN_NETLIST))
        run = operating_point_for(
            artifact(tmp_path), exporter=KiCadNetlistExporter(executable="kicad-cli"),
            spice=spice, work_dir=tmp_path)
        assert run.status is ToolStatus.OK
        assert run.transient_data is None
        assert spice.transient_calls == []

    def test_a_driven_netlist_gets_its_curve_attached_to_the_operating_point(
            self, tmp_path, monkeypatch):
        spice = FakeSpice()
        curve = TransientData(analysis=".tran 10us 1ms", time_s=[0.0, 1e-05],
                              series=[TransientSeries(name="v(vbus)", unit=Unit.VOLT,
                                                      values=[0.0, 5.0])])
        spice.transient_analysis = lambda netlist, run_id, tstep, tstop, **kwargs: SimulationRun(
            status=ToolStatus.OK, run_id=run_id, analysis=f".tran {tstep} {tstop}",
            model_fidelity=IDEAL_COMPONENTS, transient_data=curve, detail="2 samples")
        monkeypatch.setattr(simulation, "run_tool",
                            lambda command, *, timeout: _write_netlist(tmp_path, DRIVEN_NETLIST))
        run = operating_point_for(
            artifact(tmp_path), exporter=KiCadNetlistExporter(executable="kicad-cli"),
            spice=spice, work_dir=tmp_path)
        assert run.analysis == "op" and run.status is ToolStatus.OK
        assert run.transient_data.sample_count == 2
        assert "transient" in run.detail

    def test_a_failed_transient_leaves_the_operating_point_standing(self, tmp_path, monkeypatch):
        spice = FakeSpice()
        spice.transient_analysis = lambda netlist, run_id, tstep, tstop, **kwargs: _not_run(
            run_id, ToolStatus.FAILED, IDEAL_COMPONENTS, "ngspice failed",
            analysis=f".tran {tstep} {tstop}")
        monkeypatch.setattr(simulation, "run_tool",
                            lambda command, *, timeout: _write_netlist(tmp_path, DRIVEN_NETLIST))
        run = operating_point_for(
            artifact(tmp_path), exporter=KiCadNetlistExporter(executable="kicad-cli"),
            spice=spice, work_dir=tmp_path)
        assert run.status is ToolStatus.OK and run.transient_data is None
        assert "transient failed" in run.detail

    def test_the_transient_can_be_turned_off(self, tmp_path, monkeypatch):
        spice = FakeSpice()
        spice.transient_analysis = lambda *args, **kwargs: pytest.fail("must not be called")
        monkeypatch.setattr(simulation, "run_tool",
                            lambda command, *, timeout: _write_netlist(tmp_path, DRIVEN_NETLIST))
        run = operating_point_for(
            artifact(tmp_path), exporter=KiCadNetlistExporter(executable="kicad-cli"),
            spice=spice, work_dir=tmp_path, transient=False)
        assert run.status is ToolStatus.OK and run.transient_data is None

    def test_the_offline_fake_answers_the_new_question_the_same_way(self):
        from ohmni.adapters.fakes import UnavailableSpice

        run = UnavailableSpice().transient_analysis("V1 a 0 5", "run-1", "10us", "1ms")
        assert run.status is ToolStatus.UNAVAILABLE and run.transient_data is None


class TestPowerOnStimulus:
    UNDRIVEN = ".title t\nC1 VBUS GND 1u\nR1 VBUS 3V3 100\nU1 __U1\n.end\n"

    def test_an_undriven_deck_gets_a_ramp_and_a_sentence_about_it(self):
        deck, note = simulation.with_power_on_stimulus(self.UNDRIVEN)
        assert simulation.has_independent_source(deck)
        lines = deck.splitlines()
        assert lines[-2].startswith(simulation.STIMULUS_REFERENCE)
        assert "PULSE(0 5.0 0 1u 1u 1 2)" in lines[-2]
        assert lines[-1] == ".end" and lines[0] == ".title t"
        # The assumption is stated, because a curve drawn from it means "if the
        # rail came up like this", never "the rail comes up like this".
        assert "assumed, not measured" in note

    def test_a_deck_that_is_already_driven_is_left_alone(self):
        """Two sources on one net is a short, not a better simulation."""
        driven = "V1 VBUS 0 5\nC1 VBUS GND 1u\n.end\n"
        deck, note = simulation.with_power_on_stimulus(driven)
        assert deck == driven and note is None

    def test_a_net_the_deck_does_not_have_is_not_driven(self):
        """Driving a node nothing connects to simulates a different circuit."""
        deck, note = simulation.with_power_on_stimulus("R1 a b 1k\n.end\n", "VBUS")
        assert note is None and not simulation.has_independent_source(deck)

    def test_the_ramp_can_name_another_net(self):
        deck, note = simulation.with_power_on_stimulus(self.UNDRIVEN, "3V3", volts=3.3)
        assert "3V3 0 PULSE(0 3.3" in deck and "3V3" in note

    def test_a_deck_without_end_still_gets_one(self):
        deck, _ = simulation.with_power_on_stimulus("C1 VBUS GND 1u\n")
        assert deck.splitlines()[-1] == ".end"

    def test_the_operating_point_is_never_computed_from_an_altered_deck(self, tmp_path, monkeypatch):
        """A DC solution of a deck Ohmni changed is a solution to another circuit."""
        seen = {}
        spice = FakeSpice()
        spice.operating_point = lambda netlist, run_id, **kwargs: seen.setdefault(
            "op", netlist) and None or _not_run(run_id, ToolStatus.OK, IDEAL_COMPONENTS, "ok")
        spice.transient_analysis = lambda netlist, run_id, tstep, tstop, **kwargs: seen.setdefault(
            "tran", netlist) and None or _not_run(
                run_id, ToolStatus.FAILED, IDEAL_COMPONENTS, "stub",
                analysis=f".tran {tstep} {tstop}")
        monkeypatch.setattr(simulation, "run_tool",
                            lambda command, *, timeout: _write_netlist(tmp_path, self.UNDRIVEN))
        operating_point_for(artifact(tmp_path),
                            exporter=KiCadNetlistExporter(executable="kicad-cli"),
                            spice=spice, work_dir=tmp_path, stimulus=True)
        assert simulation.STIMULUS_REFERENCE not in seen["op"]
        assert simulation.STIMULUS_REFERENCE in seen["tran"]

    def test_without_the_opt_in_nothing_is_added_and_no_transient_runs(self, tmp_path, monkeypatch):
        spice = FakeSpice()
        spice.transient_analysis = lambda *args, **kwargs: pytest.fail("must not be called")
        monkeypatch.setattr(simulation, "run_tool",
                            lambda command, *, timeout: _write_netlist(tmp_path, self.UNDRIVEN))
        run = operating_point_for(artifact(tmp_path),
                                  exporter=KiCadNetlistExporter(executable="kicad-cli"),
                                  spice=spice, work_dir=tmp_path)
        assert run.transient_data is None
