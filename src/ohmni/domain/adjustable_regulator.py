"""Deterministic adjustable-linear-regulator design checks."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RegulatorFindingCode(StrEnum):
    PIN_MAP = "pin_map"
    TAB_NET = "tab_net"
    DIVIDER_TOPOLOGY = "divider_topology"
    OUTPUT_RANGE = "output_range"
    HEADROOM = "headroom"
    LOAD_CURRENT = "load_current"


class AdjustableRegulatorLimits(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    reference_voltage_v: float = Field(gt=0)
    adjust_current_a: float = Field(ge=0)
    output_min_v: float
    output_max_v: float
    differential_min_v: float
    differential_max_v: float
    load_min_a: float
    load_max_a: float

    @model_validator(mode="after")
    def _ordered(self):
        for low, high, name in (
            (self.output_min_v, self.output_max_v, "output"),
            (self.differential_min_v, self.differential_max_v, "differential"),
            (self.load_min_a, self.load_max_a, "load"),
        ):
            if low > high:
                raise ValueError(f"{name} minimum exceeds maximum")
        return self


class FeedbackNetwork(BaseModel):
    """R1 is OUTPUT-to-ADJUST and R2 is ADJUST-to-ground."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    r1_ohm: float = Field(gt=0)
    r2_ohm: float = Field(ge=0)
    r1_from: str
    r1_to: str
    r2_from: str
    r2_to: str


class AdjustableRegulatorDesign(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    pin_nets: dict[str, str]
    ground_net: str
    input_voltage_v: float
    load_current_a: float
    divider: FeedbackNetwork


class RegulatorFinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: RegulatorFindingCode
    detail: str


class RegulatorDesignResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    output_voltage_v: float
    findings: tuple[RegulatorFinding, ...]

    @property
    def passed(self) -> bool:
        return not self.findings


def output_voltage(network: FeedbackNetwork, limits: AdjustableRegulatorLimits) -> float:
    """Apply the sourced LM317 equation without dropping the adjust-current term."""
    return (
        limits.reference_voltage_v * (1 + network.r2_ohm / network.r1_ohm)
        + limits.adjust_current_a * network.r2_ohm
    )


def verify_adjustable_regulator(
    design: AdjustableRegulatorDesign,
    limits: AdjustableRegulatorLimits,
) -> RegulatorDesignResult:
    findings: list[RegulatorFinding] = []
    required = {"1", "2", "3", "4"}
    if set(design.pin_nets) != required:
        findings.append(RegulatorFinding(
            code=RegulatorFindingCode.PIN_MAP,
            detail="LM317 SOT-223 requires pins 1 ADJUST, 2 OUTPUT, 3 INPUT and 4 OUTPUT tab",
        ))
    pin = design.pin_nets
    if pin.get("2") != pin.get("4"):
        findings.append(RegulatorFinding(
            code=RegulatorFindingCode.TAB_NET,
            detail="SOT-223 tab pin 4 must share the OUTPUT net with pin 2",
        ))
    divider = design.divider
    if not (
        divider.r1_from == pin.get("2")
        and divider.r1_to == pin.get("1")
        and divider.r2_from == pin.get("1")
        and divider.r2_to == design.ground_net
    ):
        findings.append(RegulatorFinding(
            code=RegulatorFindingCode.DIVIDER_TOPOLOGY,
            detail="R1 must connect OUTPUT-to-ADJUST and R2 ADJUST-to-ground",
        ))
    voltage = output_voltage(divider, limits)
    if not limits.output_min_v <= voltage <= limits.output_max_v:
        findings.append(RegulatorFinding(
            code=RegulatorFindingCode.OUTPUT_RANGE,
            detail=f"derived output {voltage:.6g} V is outside the sourced operating range",
        ))
    differential = design.input_voltage_v - voltage
    if not limits.differential_min_v <= differential <= limits.differential_max_v:
        findings.append(RegulatorFinding(
            code=RegulatorFindingCode.HEADROOM,
            detail=f"input-output differential {differential:.6g} V is outside the sourced range",
        ))
    if not limits.load_min_a <= design.load_current_a <= limits.load_max_a:
        findings.append(RegulatorFinding(
            code=RegulatorFindingCode.LOAD_CURRENT,
            detail=f"load current {design.load_current_a:.6g} A is outside the sourced range",
        ))
    return RegulatorDesignResult(output_voltage_v=voltage, findings=tuple(findings))


__all__ = [
    "AdjustableRegulatorDesign",
    "AdjustableRegulatorLimits",
    "FeedbackNetwork",
    "RegulatorDesignResult",
    "RegulatorFinding",
    "RegulatorFindingCode",
    "output_voltage",
    "verify_adjustable_regulator",
]
