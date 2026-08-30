"""The properties that make the verifier trustworthy rather than decorative.

These are the tests that would catch the failure this whole product exists to
prevent: a report that looks clean because nothing was actually checked.
"""

from __future__ import annotations

import pytest

from ohmni.adapters import ToolStatus
from ohmni.adapters.fakes import (
    InMemoryPartCatalog,
    RecordingLlmProvider,
    UnavailableKicad,
    UnavailableSpice,
)
from ohmni.domain import (
    BLOCKING_SEVERITIES,
    CircuitComponent,
    CircuitIR,
    ComponentCategory,
    ComponentSpec,
    Net,
    NetKind,
    PackageOption,
    PinElectricalType,
    PinRef,
    PinRole,
    PinSpec,
    Quantity,
    RuleCategory,
    RuleOutcome,
    Severity,
    SubsystemStatus,
    SupplyRail,
    ValueRange,
    VerificationReport,
)
from ohmni.verifier import verify
from ohmni.verifier.registry import RegisteredRule, ResultBuilder

V = Quantity.volts


def _widget(*, current_max: Quantity | None) -> ComponentSpec:
    """A minimal two-pin powered part, with or without a current figure."""
    return ComponentSpec(
        part_id="TEST_WIDGET",
        mpn="TEST-WIDGET-1",
        category=ComponentCategory.SENSOR,
        description="Test part.",
        packages=[PackageOption(name="TEST-2", pin_count=2)],
        pins=[
            PinSpec(
                number="1",
                name="VDD",
                roles=[PinRole.POWER],
                electrical_type=PinElectricalType.POWER_IN,
                supply_rail="VDD",
            ),
            PinSpec(
                number="2",
                name="GND",
                roles=[PinRole.GROUND],
                electrical_type=PinElectricalType.POWER_IN,
            ),
        ],
        supply_rails=[
            SupplyRail(
                name="VDD",
                operating=ValueRange(minimum=V(3.0), typical=V(3.3), maximum=V(3.6)),
                absolute_max=V(4.0),
                current_max=current_max,
            )
        ],
    )


class TestOutcomeSemantics:
    """PASS, FAIL, INSUFFICIENT_DATA and NOT_APPLICABLE are four things."""

    def test_missing_data_is_not_a_pass(self):
        builder = ResultBuilder("PB-TEST", "t", RuleCategory.ELECTRICAL)
        builder.missing("no absolute maximum recorded")
        assert builder.build().outcome is RuleOutcome.INSUFFICIENT_DATA

    def test_nothing_to_check_is_not_a_pass_either(self):
        builder = ResultBuilder("PB-TEST", "t", RuleCategory.ELECTRICAL)
        builder.not_applicable("no LEDs")
        assert builder.build().outcome is RuleOutcome.NOT_APPLICABLE

    def test_checked_and_clean_is_a_pass(self):
        builder = ResultBuilder("PB-TEST", "t", RuleCategory.ELECTRICAL)
        builder.examined("R1")
        assert builder.build().outcome is RuleOutcome.PASS

    def test_info_alone_does_not_fail_a_rule(self):
        builder = ResultBuilder("PB-TEST", "t", RuleCategory.ELECTRICAL)
        builder.finding(severity=Severity.INFO, title="fyi", description="d")
        assert builder.build().outcome is RuleOutcome.PASS

    def test_a_warning_fails_the_rule(self):
        builder = ResultBuilder("PB-TEST", "t", RuleCategory.ELECTRICAL)
        builder.finding(severity=Severity.WARNING, title="hmm", description="d")
        assert builder.build().outcome is RuleOutcome.FAIL

    def test_a_real_finding_wins_over_incomplete_data(self):
        # A rule that found a genuine defect AND lacked data elsewhere has still
        # found a defect. It must not be downgraded to "could not check".
        builder = ResultBuilder("PB-TEST", "t", RuleCategory.ELECTRICAL)
        builder.finding(severity=Severity.CRITICAL, title="bad", description="d")
        builder.missing("something else was unknown")
        result = builder.build()
        assert result.outcome is RuleOutcome.FAIL
        assert result.missing_data == ["something else was unknown"]

    def test_a_crashing_rule_reports_error_not_pass(self):
        def explode(ctx, out):  # noqa: ANN001, ARG001
            raise ZeroDivisionError("boom")

        registered = RegisteredRule(
            rule_id="PB-BOOM",
            title="explodes",
            category=RuleCategory.ELECTRICAL,
            description="",
            function=explode,
        )
        result = registered.run(ctx=None)  # type: ignore[arg-type]
        assert result.outcome is RuleOutcome.ERROR
        assert "ZeroDivisionError" in (result.error_text or "")
        assert result.missing_data, "a crashed rule must record that it did not decide"


class TestCoverageMath:
    def _report(self, outcomes: list[RuleOutcome]) -> VerificationReport:
        from ohmni.domain import RuleResult

        return VerificationReport(
            report_id="r",
            circuit_ir_id="c",
            circuit_content_hash="h",
            results=[
                RuleResult(
                    rule_id=f"PB-{i}",
                    title="t",
                    category=RuleCategory.ELECTRICAL,
                    outcome=outcome,
                )
                for i, outcome in enumerate(outcomes)
            ],
        )

    def test_full_coverage_when_every_rule_decided(self):
        report = self._report([RuleOutcome.PASS, RuleOutcome.FAIL])
        assert report.coverage == 1.0

    def test_insufficient_data_lowers_coverage(self):
        report = self._report([RuleOutcome.PASS, RuleOutcome.INSUFFICIENT_DATA])
        assert report.coverage == 0.5

    def test_a_crashed_rule_lowers_coverage(self):
        report = self._report([RuleOutcome.PASS, RuleOutcome.ERROR])
        assert report.coverage == 0.5

    def test_not_applicable_does_not_lower_coverage(self):
        # A board with no LEDs should not be penalised for the LED rule.
        report = self._report([RuleOutcome.PASS, RuleOutcome.NOT_APPLICABLE])
        assert report.coverage == 1.0

    def test_undecided_rules_are_listed(self):
        report = self._report([RuleOutcome.INSUFFICIENT_DATA, RuleOutcome.ERROR, RuleOutcome.PASS])
        assert len(report.undecided_rules) == 2


class TestExportGate:
    def _report_with(self, severity: Severity) -> VerificationReport:
        from ohmni.domain import RuleResult, VerificationFinding

        return VerificationReport(
            report_id="r",
            circuit_ir_id="c",
            circuit_content_hash="h",
            results=[
                RuleResult(
                    rule_id="PB-X",
                    title="t",
                    category=RuleCategory.ELECTRICAL,
                    outcome=RuleOutcome.FAIL,
                    findings=[
                        VerificationFinding(
                            rule_id="PB-X", severity=severity, title="t", description="d"
                        )
                    ],
                )
            ],
        )

    @pytest.mark.parametrize("severity", [Severity.ERROR, Severity.CRITICAL])
    def test_blocking_severities_block_export(self, severity):
        assert self._report_with(severity).export_blocked

    @pytest.mark.parametrize("severity", [Severity.INFO, Severity.WARNING])
    def test_advisory_severities_do_not_block(self, severity):
        assert not self._report_with(severity).export_blocked

    def test_blocking_policy_is_explicit(self):
        assert BLOCKING_SEVERITIES == frozenset({Severity.ERROR, Severity.CRITICAL})


class TestVoltageIsDerivedNotDeclared:
    """The property that makes the voltage rules trustworthy.

    Nothing anywhere lets a caller assert what voltage a net sits at. It comes
    from what drives the net, so a mislabelled net cannot hide a real fault and
    a well-named net cannot manufacture a clean result.
    """

    def test_net_name_does_not_determine_voltage(self, golden, catalog):
        from ohmni.verifier.context import VerificationContext

        ctx = VerificationContext(golden, catalog)
        assert ctx.net_voltage("3V3").nominal == V(3.3)

        # Rename the rail to something meaningless. The derived voltage is
        # unchanged, because it comes from the regulator's datasheet output.
        renamed = golden.model_copy(deep=True)
        for net in renamed.nets:
            if net.name == "3V3":
                net.name = "POTATO"
        ctx2 = VerificationContext(renamed, catalog)
        assert ctx2.net_voltage("POTATO").nominal == V(3.3)
        assert ctx2.net_voltage("POTATO").driver_descriptions == [
            "U2 (AP2112K-3.3TRG1) output"
        ]

    def test_a_reassuring_net_name_cannot_hide_a_5v_rail(self, catalog):
        """Call the 5 V rail "3V3" and the sensor is still on 5 V."""
        from ohmni.fixtures.esp32_env_logger import broken_sensor_on_5v

        circuit = broken_sensor_on_5v()
        for net in circuit.nets:
            if net.name == "VBUS":
                net.name = "3V3_SAFE"
            elif net.name == "3V3":
                net.name = "OLD_3V3"

        report = verify(circuit, catalog)
        critical = [
            f
            for f in report.findings
            if f.rule_id == "PB-PWR-001" and f.severity is Severity.CRITICAL
        ]
        assert critical, "renaming a net must not clear an absolute-maximum violation"
        assert "3V3_SAFE" in critical[0].affected_nets

    def test_pinspec_has_no_declarable_voltage_domain(self):
        # The specification's PinSpec.voltage_domain: str was removed on
        # purpose. If it comes back, this test should fail loudly.
        assert "voltage_domain" not in PinSpec.model_fields

    def test_circuit_component_cannot_declare_a_voltage(self):
        assert "voltage" not in CircuitComponent.model_fields
        assert "voltage_domain" not in CircuitComponent.model_fields

    def test_moving_a_pin_changes_the_verdict(self, golden, catalog, requirements):
        clean = verify(golden, catalog, requirements)
        assert not clean.export_blocked

        moved = golden.model_copy(deep=True)
        three_v3 = next(n for n in moved.nets if n.name == "3V3")
        vbus = next(n for n in moved.nets if n.name == "VBUS")
        three_v3.connections = [
            p for p in three_v3.connections if not (p.component == "U3" and p.pin == "8")
        ]
        vbus.connections.append(PinRef(component="U3", pin="8"))

        report = verify(moved, catalog, requirements)
        assert report.export_blocked
        assert any(f.severity is Severity.CRITICAL for f in report.findings)


class TestAbsoluteMaximumVsOperatingRange:
    """The distinction VERIFICATION.md calls critical."""

    def _circuit(self, rail_voltage: ValueRange) -> tuple[CircuitIR, InMemoryPartCatalog]:
        catalog = InMemoryPartCatalog([_widget(current_max=Quantity.amps(1e-3))])
        circuit = CircuitIR(
            ir_id="t",
            name="t",
            components=[CircuitComponent(ref="U1", part_id="TEST_WIDGET", package="TEST-2")],
            nets=[
                Net(
                    name="RAIL",
                    kind=NetKind.POWER,
                    connections=[PinRef(component="U1", pin="1")],
                    external_source={  # type: ignore[arg-type]
                        "kind": "bench_supply",
                        "voltage": rail_voltage,
                    },
                ),
                Net(
                    name="GND",
                    kind=NetKind.GROUND,
                    connections=[PinRef(component="U1", pin="2")],
                ),
            ],
        )
        return circuit, catalog

    def test_inside_the_operating_range_passes(self):
        circuit, catalog = self._circuit(ValueRange.exact(V(3.3)))
        result = verify(circuit, catalog).rule("PB-PWR-001")
        assert result is not None
        assert result.outcome is RuleOutcome.PASS

    def test_outside_operating_but_inside_absolute_max_is_an_error_not_critical(self):
        # 3.8 V: not specified to work, but not going to destroy the part.
        circuit, catalog = self._circuit(ValueRange.exact(V(3.8)))
        findings = verify(circuit, catalog).rule("PB-PWR-001").findings
        assert [f.severity for f in findings] == [Severity.ERROR]
        assert "recommended operating range" in findings[0].title

    def test_above_absolute_max_is_critical(self):
        circuit, catalog = self._circuit(ValueRange.exact(V(5.0)))
        findings = verify(circuit, catalog).rule("PB-PWR-001").findings
        assert [f.severity for f in findings] == [Severity.CRITICAL]
        assert "absolute maximum" in findings[0].title

    def test_tolerance_excursion_is_a_warning(self):
        # Nominal is fine; the top of the supply tolerance is not.
        circuit, catalog = self._circuit(
            ValueRange(minimum=V(3.2), typical=V(3.4), maximum=V(3.7))
        )
        findings = verify(circuit, catalog).rule("PB-PWR-001").findings
        assert [f.severity for f in findings] == [Severity.WARNING]

    def test_unknown_absolute_max_inside_operating_range_is_still_a_pass(self):
        """Recommended operating conditions sit inside the absolute maximum.

        So a voltage inside the operating range cannot violate an absolute
        maximum, and a missing abs-max figure is not missing data for that case.
        Reporting INSUFFICIENT_DATA here would be false modesty.
        """
        spec = _widget(current_max=Quantity.amps(1e-3))
        spec.supply_rails[0].absolute_max = None
        catalog = InMemoryPartCatalog([spec])
        circuit, _ = self._circuit(ValueRange.exact(V(3.3)))
        result = verify(circuit, catalog).rule("PB-PWR-001")
        assert result.outcome is RuleOutcome.PASS
        assert result.missing_data == []

    def test_unknown_absolute_max_outside_operating_range_admits_it(self):
        """Out of spec with no abs-max figure: report the error AND the gap."""
        spec = _widget(current_max=Quantity.amps(1e-3))
        spec.supply_rails[0].absolute_max = None
        catalog = InMemoryPartCatalog([spec])
        circuit, _ = self._circuit(ValueRange.exact(V(5.0)))
        result = verify(circuit, catalog).rule("PB-PWR-001")
        assert result.outcome is RuleOutcome.FAIL
        assert [f.severity for f in result.findings] == [Severity.ERROR]
        assert any("absolute maximum" in m for m in result.missing_data)
        assert "could not be determined" in result.findings[0].description


class TestRegulatorSizingHonesty:
    def test_a_known_overload_is_definitive_even_with_unknown_loads(self, catalog):
        """A lower bound above the rating is conclusive: unknowns only add."""
        from ohmni.fixtures.esp32_env_logger import broken_undersized_regulator

        result = verify(broken_undersized_regulator(), catalog).rule("PB-REG-002")
        assert result.outcome is RuleOutcome.FAIL
        assert result.findings[0].severity is Severity.ERROR

    def test_unknown_loads_under_the_rating_are_not_a_pass(self, golden, catalog):
        """Silently summing only the known parts would understate the load."""
        from ohmni.catalog import JsonPartCatalog

        stripped = JsonPartCatalog()
        sensor = stripped.require("BME280")
        for rail in sensor.supply_rails:
            rail.current_max = None

        result = verify(golden, stripped).rule("PB-REG-002")
        assert result.outcome is RuleOutcome.INSUFFICIENT_DATA
        assert any("BME280" in m or "U3" in m for m in result.missing_data)


class TestSubsystemRollup:
    def test_a_failure_makes_a_subsystem_not_verified(self, catalog, requirements):
        from ohmni.fixtures.esp32_env_logger import broken_sensor_on_5v

        report = verify(broken_sensor_on_5v(), catalog, requirements)
        assert report.subsystem_status["electrical"] is SubsystemStatus.NOT_VERIFIED

    def test_absent_subsystems_are_unsupported_not_verified(self, golden, catalog, requirements):
        # Nothing ran ERC or SPICE, so those must not read as clean.
        report = verify(golden, catalog, requirements)
        assert report.subsystem_status["eda"] is SubsystemStatus.UNSUPPORTED
        assert report.subsystem_status["simulation"] is SubsystemStatus.UNSUPPORTED

    def test_a_warning_downgrades_to_partially_verified(self, golden, catalog, requirements):
        report = verify(golden, catalog, requirements)
        # The BME280's LGA package trips the hand-solderability warning.
        assert report.subsystem_status["identity"] is SubsystemStatus.PARTIALLY_VERIFIED


class TestUnavailableToolsDoNotFabricatePasses:
    def test_kicad_unavailable_is_not_a_clean_erc(self):
        kicad = UnavailableKicad()
        assert not kicad.availability().usable
        run = kicad.run_erc(__import__("pathlib").Path("nope.kicad_sch"))
        assert run.status is ToolStatus.UNAVAILABLE
        assert run.findings == []
        assert run.detail and "not a pass" in run.detail

    def test_spice_unavailable_produces_no_simulated_evidence(self):
        spice = UnavailableSpice()
        run = spice.operating_point("* netlist", "run-1")
        assert run.status is ToolStatus.UNAVAILABLE
        assert run.evidence == []
        assert run.operating_point is None


class TestLlmOutputIsSchemaValidated:
    def test_a_response_that_violates_the_schema_is_rejected(self):
        from pydantic import ValidationError

        provider = RecordingLlmProvider()
        provider.queue({"ir_id": "x", "name": "y", "components": "not a list"})
        with pytest.raises(ValidationError):
            provider.complete_structured(
                instructions="propose a circuit",
                data="<untrusted datasheet text>",
                schema=CircuitIR,
            )

    def test_a_valid_response_comes_back_as_a_typed_model(self):
        provider = RecordingLlmProvider()
        provider.queue({"ir_id": "x", "name": "y", "components": [], "nets": []})
        result = provider.complete_structured(
            instructions="propose a circuit", data="<data>", schema=CircuitIR
        )
        assert isinstance(result, CircuitIR)
        assert provider.calls[0]["schema"] == "CircuitIR"

    def test_there_is_no_free_text_path(self):
        from ohmni.adapters import LlmProvider

        methods = {m for m in dir(LlmProvider) if not m.startswith("_")}
        assert methods == {"complete_structured", "generate_structured"}
