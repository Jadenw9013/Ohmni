"""Pure electrical-profile construction and synthesized-component admission gates.

Geometric source verification and CAD verification are necessary but do not
establish electrical behaviour. This module accepts only hash-bound checked
electrical facts, evaluates a named required-fact matrix and named applicable
rules, then constructs a :class:`ComponentSpec` only for a bounded profile.
No generic report flag can substitute for those explicit outcomes.
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from .component import (
    ComponentCategory,
    ComponentSpec,
    I2CAddressOption,
    Interface,
    Lifecycle,
    PackageOption,
    PinElectricalType,
    PinRole,
    PinSpec,
    SupplyRail,
)
from .component_synthesis import (
    CHECKER_CONTRACT_VERSION,
    Capability,
    CapabilityMatrix,
    CapabilityResult,
    CapabilityState,
    ReceiptOutcome,
    Sha256,
    ShortText,
    VerificationReceipt,
    VerifiedConstraintSet,
    claim_hash,
)
from .evidence import DocumentRef
from .units import Unit, ValueRange, parse_quantity

FactId = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_.-]{0,119}$")]
RuleId = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_.-]{0,119}$")]
FactValue = str | int | bool | tuple[str, ...]


class ElectricalProfile(StrEnum):
    PASSIVE_TWO_TERMINAL = "passive_two_terminal"
    I2C_PERIPHERAL = "i2c_peripheral"
    ADJUSTABLE_LINEAR_REGULATOR = "adjustable_linear_regulator"
    UNSUPPORTED = "unsupported"


class ApplicableRuleOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class CheckedElectricalFact(BaseModel):
    """One source-checked semantic value and the receipt that binds it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fact_id: FactId
    value: FactValue
    receipt_id: ShortText

    def claim(self) -> dict:
        return {"claim": "electrical_fact", "fact_id": self.fact_id, "value": self.value}


class CheckedElectricalClaims(BaseModel):
    """Electrical facts whose values all re-hash to current supported receipts."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_digest: Sha256
    observation_digest: Sha256
    profile: ElectricalProfile
    facts: tuple[CheckedElectricalFact, ...] = Field(min_length=1, max_length=512)
    receipts: tuple[VerificationReceipt, ...] = Field(min_length=1, max_length=512)

    @model_validator(mode="after")
    def _bind_every_fact(self) -> CheckedElectricalClaims:
        by_fact = {fact.fact_id: fact for fact in self.facts}
        if len(by_fact) != len(self.facts):
            raise ValueError("duplicate electrical fact ID")
        by_receipt = {receipt.receipt_id: receipt for receipt in self.receipts}
        if len(by_receipt) != len(self.receipts):
            raise ValueError("duplicate electrical receipt ID")
        for fact in self.facts:
            receipt = by_receipt.get(fact.receipt_id)
            if receipt is None:
                raise ValueError(f"electrical fact {fact.fact_id!r} has no receipt")
            if receipt.outcome is not ReceiptOutcome.SUPPORTED:
                raise ValueError(f"electrical fact {fact.fact_id!r} is not supported")
            if receipt.checker != "CS-ELECTRICAL":
                raise ValueError(f"electrical fact {fact.fact_id!r} used a non-electrical checker")
            if receipt.checker_version != CHECKER_CONTRACT_VERSION:
                raise ValueError(f"electrical fact {fact.fact_id!r} has a stale checker receipt")
            if receipt.document_digest != self.document_digest:
                raise ValueError(f"electrical fact {fact.fact_id!r} checked another document")
            if receipt.observation_digest != self.observation_digest:
                raise ValueError(f"electrical fact {fact.fact_id!r} checked other observations")
            if receipt.claim_hash != claim_hash(fact.claim()):
                raise ValueError(f"electrical fact {fact.fact_id!r} changed after checking")
        return self

    def value(self, fact_id: str) -> FactValue | None:
        return next((fact.value for fact in self.facts if fact.fact_id == fact_id), None)

    @property
    def fact_ids(self) -> frozenset[str]:
        return frozenset(fact.fact_id for fact in self.facts)


class ApplicableRuleResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: RuleId
    outcome: ApplicableRuleOutcome
    report_digest: Sha256
    detail: ShortText


class AdmissionRequest(BaseModel):
    """Exact inputs evaluated at the catalog transaction boundary."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    revision_id: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{32}$")]
    publication_digest: Sha256
    constraints: VerifiedConstraintSet
    electrical: CheckedElectricalClaims
    applicable_rules: tuple[ApplicableRuleResult, ...] = Field(min_length=1, max_length=64)
    requested_capabilities: tuple[Capability, ...] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def _one_rule_and_capability_each(self) -> AdmissionRequest:
        rules = [item.rule_id for item in self.applicable_rules]
        if len(rules) != len(set(rules)):
            raise ValueError("duplicate applicable-rule result")
        if len(self.requested_capabilities) != len(set(self.requested_capabilities)):
            raise ValueError("duplicate requested capability")
        return self


class RequiredFactResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    fact_id: FactId
    present: bool


class AdmissionDecision(BaseModel):
    """Complete gate output. Only an admitted decision may activate a revision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    revision_id: str
    publication_digest: Sha256
    admitted: bool
    component_spec: ComponentSpec | None
    required_facts: tuple[RequiredFactResult, ...]
    applicable_rules: tuple[ApplicableRuleResult, ...]
    capabilities: CapabilityMatrix
    reasons: tuple[ShortText, ...] = Field(default=(), max_length=64)

    @model_validator(mode="after")
    def _admission_has_a_spec(self) -> AdmissionDecision:
        if self.admitted != (self.component_spec is not None):
            raise ValueError("admitted decision and component spec must appear together")
        return self

    @property
    def decision_digest(self) -> str:
        payload = self.model_dump(mode="json")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode()).hexdigest()


_COMMON_FACTS = frozenset({
    "component.manufacturer",
    "component.mpn",
    "component.category",
    "component.description",
    "package.name",
})
_COMMON_RULES = frozenset({"source.constraints", "assets.geometry", "assets.native"})
_SUPPORTED_CAPABILITIES = {
    ElectricalProfile.PASSIVE_TWO_TERMINAL: frozenset({
        Capability.IDENTITY,
        Capability.SYMBOL,
        Capability.FOOTPRINT,
        Capability.ELECTRICAL_PROFILE,
        Capability.ROUTING,
    }),
    ElectricalProfile.I2C_PERIPHERAL: frozenset({
        Capability.IDENTITY,
        Capability.SYMBOL,
        Capability.FOOTPRINT,
        Capability.ELECTRICAL_PROFILE,
        Capability.ROUTING,
    }),
    ElectricalProfile.ADJUSTABLE_LINEAR_REGULATOR: frozenset({
        Capability.IDENTITY,
        Capability.SYMBOL,
        Capability.FOOTPRINT,
        Capability.ELECTRICAL_PROFILE,
        Capability.ROUTING,
    }),
    ElectricalProfile.UNSUPPORTED: frozenset({Capability.IDENTITY}),
}


def electrical_fact_claim(fact_id: str, value: FactValue) -> dict:
    """Canonical payload for a deterministic electrical-fact checker."""
    return {"claim": "electrical_fact", "fact_id": fact_id, "value": value}


def evaluate_admission(request: AdmissionRequest) -> AdmissionDecision:
    """Evaluate every required fact/rule and build a spec only on full support."""
    reasons: list[str] = []
    constraints_broken = request.constraints.revalidate()
    if constraints_broken:
        reasons.append("source constraint receipt bindings do not revalidate")
    if request.constraints.document_digest != request.electrical.document_digest:
        reasons.append("mechanical and electrical claims use different documents")
    if request.constraints.observation_digest != request.electrical.observation_digest:
        reasons.append("mechanical and electrical claims use different observations")

    required = set(_COMMON_FACTS)
    for terminal in request.constraints.terminals:
        required.update({
            f"pin.{terminal.pin_number}.name",
            f"pin.{terminal.pin_number}.roles",
            f"pin.{terminal.pin_number}.electrical_type",
        })
    profile = request.electrical.profile
    required_rules = set(_COMMON_RULES)
    if profile is ElectricalProfile.PASSIVE_TWO_TERMINAL:
        required_rules.add("electrical.passive")
    elif profile is ElectricalProfile.I2C_PERIPHERAL:
        required.update({"interface.i2c", "rail.names", "i2c.addresses"})
        required_rules.add("electrical.i2c")
        rail_names = request.electrical.value("rail.names")
        if isinstance(rail_names, tuple):
            for name in rail_names:
                key = name.casefold()
                required.update({f"rail.{key}.minimum", f"rail.{key}.maximum"})
        for terminal in request.constraints.terminals:
            roles = request.electrical.value(f"pin.{terminal.pin_number}.roles")
            if isinstance(roles, tuple) and any(
                role in roles for role in (PinRole.POWER.value, PinRole.I2C_SDA.value,
                                           PinRole.I2C_SCL.value)
            ):
                required.add(f"pin.{terminal.pin_number}.supply_rail")
    elif profile is ElectricalProfile.ADJUSTABLE_LINEAR_REGULATOR:
        required.update({
            "regulator.reference_voltage",
            "regulator.adjust_current_typical",
            "regulator.output_minimum",
            "regulator.output_maximum",
            "regulator.differential_minimum",
            "regulator.differential_maximum",
            "regulator.load_minimum",
            "regulator.load_maximum",
            "package.tab_pin",
            "package.tab_role",
        })
        required_rules.update({"electrical.adjustable_regulator", "package.tab_output"})
    else:
        reasons.append("electrical behaviour profile is unsupported")

    fact_results = tuple(
        RequiredFactResult(fact_id=fact_id, present=fact_id in request.electrical.fact_ids)
        for fact_id in sorted(required)
    )
    missing = [item.fact_id for item in fact_results if not item.present]
    if missing:
        reasons.append("missing required facts: " + ", ".join(missing))

    rule_map = {item.rule_id: item for item in request.applicable_rules}
    for rule_id in sorted(required_rules):
        result = rule_map.get(rule_id)
        if result is None:
            reasons.append(f"applicable rule {rule_id} was not evaluated")
        elif result.outcome is not ApplicableRuleOutcome.PASS:
            reasons.append(f"applicable rule {rule_id} is {result.outcome.value}")
    for result in request.applicable_rules:
        if result.rule_id not in required_rules and result.outcome in {
            ApplicableRuleOutcome.FAIL,
            ApplicableRuleOutcome.UNKNOWN,
        }:
            reasons.append(f"applicable rule {result.rule_id} is {result.outcome.value}")

    spec: ComponentSpec | None = None
    if not reasons:
        try:
            spec = _build_component(request)
        except (KeyError, TypeError, ValueError) as exc:
            reasons.append(f"checked electrical facts cannot construct ComponentSpec: {exc}")

    supported = _SUPPORTED_CAPABILITIES[profile] if spec is not None else frozenset()
    results = tuple(
        CapabilityResult(
            capability=capability,
            state=(CapabilityState.SUPPORTED if capability in supported else
                   CapabilityState.UNSUPPORTED if profile is ElectricalProfile.UNSUPPORTED else
                   CapabilityState.BLOCKED),
            reasons=(() if capability in supported else tuple(reasons[:4]) or
                     ("capability is outside the selected electrical profile",)),
        )
        for capability in Capability
    )
    matrix = CapabilityMatrix(results=results)
    unavailable = [
        capability.value for capability in request.requested_capabilities
        if not matrix.supports(capability)
    ]
    if unavailable:
        reasons.append("requested capabilities are not supported: " + ", ".join(unavailable))
        spec = None

    return AdmissionDecision(
        revision_id=request.revision_id,
        publication_digest=request.publication_digest,
        admitted=not reasons,
        component_spec=spec if not reasons else None,
        required_facts=fact_results,
        applicable_rules=request.applicable_rules,
        capabilities=matrix,
        reasons=tuple(dict.fromkeys(reasons)),
    )


def _build_component(request: AdmissionRequest) -> ComponentSpec:
    claims = request.electrical
    identity = request.constraints.identity
    manufacturer = _string(claims, "component.manufacturer")
    mpn = _string(claims, "component.mpn")
    if manufacturer != identity.manufacturer or mpn != identity.orderable_part_number:
        raise ValueError("electrical identity differs from source-verified package identity")
    category = ComponentCategory(_string(claims, "component.category"))
    package_name = _string(claims, "package.name")
    if package_name not in {identity.package_code, identity.package_description}:
        raise ValueError("package fact differs from source-verified package")

    pins: list[PinSpec] = []
    for terminal in request.constraints.terminals:
        number = terminal.pin_number
        roles = [PinRole(value) for value in _strings(claims, f"pin.{number}.roles")]
        pins.append(PinSpec(
            number=number,
            name=_string(claims, f"pin.{number}.name"),
            roles=roles,
            electrical_type=PinElectricalType(
                _string(claims, f"pin.{number}.electrical_type")
            ),
            supply_rail=_optional_string(claims, f"pin.{number}.supply_rail"),
        ))

    rails: list[SupplyRail] = []
    rail_names = claims.value("rail.names")
    if rail_names is not None:
        if not isinstance(rail_names, tuple):
            raise TypeError("rail.names must be a tuple")
        for name in rail_names:
            key = name.casefold()
            minimum = parse_quantity(_string(claims, f"rail.{key}.minimum"), Unit.VOLT)
            maximum = parse_quantity(_string(claims, f"rail.{key}.maximum"), Unit.VOLT)
            rails.append(SupplyRail(
                name=name,
                operating=ValueRange(minimum=minimum, maximum=maximum),
            ))

    interfaces: list[Interface] = []
    if claims.value("interface.i2c") is True:
        interfaces.append(Interface.I2C)
    addresses: list[I2CAddressOption] = []
    address_values = claims.value("i2c.addresses")
    if address_values is not None:
        if not isinstance(address_values, tuple):
            raise TypeError("i2c.addresses must be a tuple")
        addresses = [I2CAddressOption(address=int(value, 0)) for value in address_values]

    if claims.profile is ElectricalProfile.PASSIVE_TWO_TERMINAL:
        if category not in {
            ComponentCategory.RESISTOR,
            ComponentCategory.CAPACITOR,
            ComponentCategory.INDUCTOR,
        }:
            raise ValueError("passive profile requires resistor, capacitor or inductor category")
        if len(pins) != 2 or any(
            pin.electrical_type is not PinElectricalType.PASSIVE or
            PinRole.TERMINAL not in pin.roles for pin in pins
        ):
            raise ValueError("passive profile requires exactly two passive terminal pins")
    if claims.profile is ElectricalProfile.I2C_PERIPHERAL:
        roles = {role for pin in pins for role in pin.roles}
        required_roles = {PinRole.POWER, PinRole.GROUND, PinRole.I2C_SDA, PinRole.I2C_SCL}
        if not required_roles.issubset(roles) or not rails or not addresses:
            raise ValueError("I2C profile requires power, ground, SDA, SCL, rails and address")
    if claims.profile is ElectricalProfile.ADJUSTABLE_LINEAR_REGULATOR:
        if category is not ComponentCategory.REGULATOR_LINEAR:
            raise ValueError("adjustable-regulator profile requires a linear regulator")
        by_number = {pin.number: pin for pin in pins}
        if set(by_number) != {"1", "2", "3", "4"}:
            raise ValueError("LM317 SOT-223 profile requires pins 1, 2, 3 and tab 4")
        if PinRole.ADJUST not in by_number["1"].roles:
            raise ValueError("pin 1 must carry the adjust role")
        if any(PinRole.POWER not in by_number[number].roles for number in ("2", "3", "4")):
            raise ValueError("input, output and tab require power roles")
        if _string(claims, "package.tab_pin") != "4" or _string(
            claims, "package.tab_role"
        ) != "output":
            raise ValueError("SOT-223 tab must be pin 4 OUTPUT")

    return ComponentSpec(
        part_id=f"SYNTH-{request.revision_id}",
        mpn=mpn,
        manufacturer=manufacturer,
        category=category,
        description=_string(claims, "component.description"),
        lifecycle=Lifecycle.UNKNOWN,
        packages=[PackageOption(
            name=package_name,
            pin_count=identity.pin_count,
            hand_solderable=False,
        )],
        pins=pins,
        supply_rails=rails,
        interfaces=interfaces,
        i2c_addresses=addresses,
        datasheet=DocumentRef(
            document_id=request.constraints.document_digest,
            manufacturer=manufacturer,
            part_number=mpn,
            revision=identity.document_revision,
            sha256=request.constraints.document_digest,
        ),
    )


def _string(claims: CheckedElectricalClaims, fact_id: str) -> str:
    value = claims.value(fact_id)
    if not isinstance(value, str) or not value:
        raise TypeError(f"{fact_id} must be a non-empty string")
    return value


def _optional_string(claims: CheckedElectricalClaims, fact_id: str) -> str | None:
    value = claims.value(fact_id)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise TypeError(f"{fact_id} must be a non-empty string")
    return value


def _strings(claims: CheckedElectricalClaims, fact_id: str) -> tuple[str, ...]:
    value = claims.value(fact_id)
    if not isinstance(value, tuple) or not value or not all(isinstance(item, str) for item in value):
        raise TypeError(f"{fact_id} must be a non-empty tuple of strings")
    return value


__all__ = [
    "AdmissionDecision",
    "AdmissionRequest",
    "ApplicableRuleOutcome",
    "ApplicableRuleResult",
    "CheckedElectricalClaims",
    "CheckedElectricalFact",
    "ElectricalProfile",
    "RequiredFactResult",
    "electrical_fact_claim",
    "evaluate_admission",
]
