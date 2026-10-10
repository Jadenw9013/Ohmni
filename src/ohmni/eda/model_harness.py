"""Manifest-contained SPICE model compilation and predeclared assertion runs."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from ..adapters import PartCatalog
from ..domain.circuit import CircuitIR
from ..domain.spice_models import (
    MeasuredAssertion,
    SimulationAnalysis,
    SimulationEligibility,
    SimulationEligibilityState,
    SimulationPlan,
    SpiceDialect,
    SpiceModelBinding,
    SpiceModelManifest,
    content_hash,
)

_INCLUDE = re.compile(r"^\s*\.(?:include|inc)\s+['\"]?([^'\"\s]+)['\"]?\s*$", re.IGNORECASE)
_FORBIDDEN = re.compile(
    r"^\s*(?:\.(?:control|endc|shell|csparam|lib)\b|(?:shell|source|cd|write|wrdata|hardcopy)\b)",
    re.IGNORECASE,
)
_SUBCKT = re.compile(r"^\s*\.subckt\s+(\S+)\s+(.+?)\s*$", re.IGNORECASE)
_MEASURED = re.compile(
    r"^\s*OHMNI\s+(?P<id>[A-Za-z0-9_.:-]+)\s+(?P<value>[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*$"
)


class ModelBoundaryError(ValueError):
    """A model cannot cross the trusted simulation boundary."""


class BoundModelDeck(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    text: str
    deck_sha256: str
    manifest_sha256: str
    binding_sha256: str
    circuit_content_hash: str
    component_ref: str
    analysis: SimulationAnalysis
    plan_sha256: str


class HarnessStatus(StrEnum):
    PASSED = "passed"
    ASSERTION_FAILED = "assertion_failed"
    UNSUPPORTED_DIALECT = "unsupported_dialect"
    NONCONVERGENT = "nonconvergent"
    EMPTY_RESULTS = "empty_results"
    TOOL_FAILED = "tool_failed"
    NOT_ELIGIBLE = "not_eligible"


class AssertionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    assertion_id: str
    measured: float
    minimum: float
    maximum: float
    passed: bool


class HarnessResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    status: HarnessStatus
    plan_sha256: str
    deck_sha256: str | None = None
    results: tuple[AssertionResult, ...] = ()
    detail: str


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_model_files(
    manifest: SpiceModelManifest, read_blob: Callable[[str], bytes]
) -> str:
    """Hash-check and inline the entrypoint's complete manifest-listed include graph."""
    if manifest.dialect is not SpiceDialect.NGSPICE_42:
        raise ModelBoundaryError(f"unsupported SPICE dialect: {manifest.dialect.value}")
    listed = {item.path: item for item in manifest.files}
    decoded: dict[str, str] = {}
    for path, item in listed.items():
        raw = read_blob(item.sha256)
        if _digest(raw) != item.sha256:
            raise ModelBoundaryError(f"model blob hash mismatch: {path}")
        try:
            decoded[path] = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ModelBoundaryError(f"model file is not UTF-8 text: {path}") from exc

    visiting: set[str] = set()
    resolved: set[str] = set()

    def inline(path: str) -> list[str]:
        if path in visiting:
            raise ModelBoundaryError("cyclic model include graph")
        if path in resolved:
            return []
        if path not in listed:
            raise ModelBoundaryError(f"include is not manifest-listed: {path}")
        visiting.add(path)
        output = [f"* begin manifest:{path}:{listed[path].sha256}"]
        for line in decoded[path].splitlines():
            if _FORBIDDEN.match(line):
                raise ModelBoundaryError(f"restricted SPICE directive in {path}")
            match = _INCLUDE.match(line)
            if match:
                target = match.group(1).replace("\\", "/")
                if target not in listed:
                    raise ModelBoundaryError(f"include is not manifest-listed: {target}")
                output.extend(inline(target))
            else:
                output.append(line)
        output.append(f"* end manifest:{path}")
        visiting.remove(path)
        resolved.add(path)
        return output

    text = "\n".join(inline(manifest.entrypoint)) + "\n"
    unreachable = sorted(set(listed) - resolved)
    if unreachable:
        raise ModelBoundaryError("manifest contains unreachable model files: " + ", ".join(unreachable))
    return text


def bind_model_to_design(
    circuit: CircuitIR,
    component_ref: str,
    catalog: PartCatalog,
    manifest: SpiceModelManifest,
    binding: SpiceModelBinding,
    eligibility: SimulationEligibility,
    plan: SimulationPlan,
    read_blob: Callable[[str], bytes],
) -> BoundModelDeck:
    """Create an actual design instance from exact circuit nets and the pin map."""
    if eligibility.state is not SimulationEligibilityState.ELIGIBLE:
        raise ModelBoundaryError("component is CAD-only and has no simulation eligibility")
    if eligibility.binding != binding or eligibility.manifest_sha256 != manifest.manifest_sha256:
        raise ModelBoundaryError("simulation eligibility does not bind these exact model inputs")
    if binding.manifest_sha256 != manifest.manifest_sha256:
        raise ModelBoundaryError("model binding and manifest fingerprints differ")
    if plan.analysis not in manifest.supported_analyses:
        raise ModelBoundaryError("requested analysis is not supported by the model manifest")
    component = circuit.component(component_ref)
    if component is None or component.part_id != binding.part_id:
        raise ModelBoundaryError("model binding does not match the circuit component")
    spec = catalog.require(component.part_id)
    if {pin.symbol_pin for pin in binding.pins} != {pin.number for pin in spec.pins}:
        raise ModelBoundaryError("model pin map must cover every catalog symbol pin exactly")
    net_by_pin = {
        pin.pin: net.name
        for net in circuit.nets for pin in net.connections if pin.component == component_ref
    }
    if set(net_by_pin) != {pin.number for pin in spec.pins}:
        raise ModelBoundaryError("every model-bound symbol pin must connect to a design net")

    model_text = resolve_model_files(manifest, read_blob)
    declarations = [match for line in model_text.splitlines() if (match := _SUBCKT.match(line))]
    named = [match for match in declarations if match.group(1).casefold() == manifest.model_name.casefold()]
    if len(named) != 1:
        raise ModelBoundaryError("manifest must define its named subcircuit exactly once")
    ports = named[0].group(2).split()
    ordered = sorted(binding.pins, key=lambda item: item.model_position)
    if len(ports) != len(ordered) or [item.model_port.casefold() for item in ordered] != [
        port.casefold() for port in ports
    ]:
        raise ModelBoundaryError("model pin map does not match the subcircuit port declaration")
    nodes = " ".join(net_by_pin[item.symbol_pin] for item in ordered)
    assertion_lines = [
        f"* assertion {item.assertion_id} {item.kind.value} {item.signal} "
        f"[{item.minimum},{item.maximum}] {item.unit}"
        for item in plan.assertions
    ]
    deck = "\n".join(
        [
            f"Ohmni bound model {component_ref}",
            model_text.rstrip(),
            f"X{component_ref} {nodes} {manifest.model_name}",
            *assertion_lines,
            ".end",
            "",
        ]
    )
    return BoundModelDeck(
        text=deck, deck_sha256=_digest(deck.encode()), manifest_sha256=manifest.manifest_sha256,
        binding_sha256=content_hash(binding.model_dump(mode="json")),
        circuit_content_hash=circuit.content_hash, component_ref=component_ref,
        analysis=plan.analysis, plan_sha256=plan.plan_sha256,
    )


def evaluate_harness(
    deck: BoundModelDeck,
    manifest: SpiceModelManifest,
    plan: SimulationPlan,
    run: Callable[[str], dict],
) -> HarnessResult:
    """Run only after plan/deck binding; compare independent observations afterwards."""
    if manifest.dialect is not SpiceDialect.NGSPICE_42:
        return HarnessResult(status=HarnessStatus.UNSUPPORTED_DIALECT,
                             plan_sha256=plan.plan_sha256, detail="unsupported model dialect")
    if deck.plan_sha256 != plan.plan_sha256 or deck.manifest_sha256 != manifest.manifest_sha256:
        raise ModelBoundaryError("run inputs changed after assertions were defined")
    raw = run(deck.text)
    status = raw.get("status")
    combined = f"{raw.get('stdout', '')}\n{raw.get('stderr', '')}"
    if status in {"timed_out", "failed"} and re.search(r"converg|timestep too small|singular", combined, re.IGNORECASE):
        return HarnessResult(status=HarnessStatus.NONCONVERGENT, plan_sha256=plan.plan_sha256,
                             deck_sha256=deck.deck_sha256, detail="ngspice did not converge")
    if status != "ran":
        return HarnessResult(status=HarnessStatus.TOOL_FAILED, plan_sha256=plan.plan_sha256,
                             deck_sha256=deck.deck_sha256, detail="ngspice did not complete")
    supplied = raw.get("measurements", {})
    if not isinstance(supplied, dict):
        supplied = {}
    measured = {str(key): float(value) for key, value in supplied.items()}
    measured.update(
        {
            match.group("id"): float(match.group("value"))
            for line in combined.splitlines()
            if (match := _MEASURED.match(line))
        }
    )
    expected = {item.assertion_id for item in plan.assertions}
    if set(measured) != expected:
        return HarnessResult(status=HarnessStatus.EMPTY_RESULTS, plan_sha256=plan.plan_sha256,
                             deck_sha256=deck.deck_sha256,
                             detail="ngspice returned incomplete or empty assertion observations")
    results = tuple(_assertion(item, measured[item.assertion_id]) for item in plan.assertions)
    passed = all(item.passed for item in results)
    return HarnessResult(status=HarnessStatus.PASSED if passed else HarnessStatus.ASSERTION_FAILED,
                         plan_sha256=plan.plan_sha256, deck_sha256=deck.deck_sha256,
                         results=results, detail="all predeclared assertions passed" if passed
                         else "one or more predeclared assertions failed")


def _assertion(assertion: MeasuredAssertion, measured: float) -> AssertionResult:
    return AssertionResult(assertion_id=assertion.assertion_id, measured=measured,
                           minimum=assertion.minimum, maximum=assertion.maximum,
                           passed=assertion.minimum <= measured <= assertion.maximum)


__all__ = [
    "AssertionResult", "BoundModelDeck", "HarnessResult", "HarnessStatus",
    "ModelBoundaryError", "bind_model_to_design", "evaluate_harness", "resolve_model_files",
]
