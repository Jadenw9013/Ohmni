"""Rule registration and the builder rules use to report what they found.

Two design points:

* A rule never constructs its own :class:`RuleOutcome`. The builder derives it
  from what the rule actually did, so "I found nothing" and "I had no data" can
  never be confused by a rule author in a hurry.
* A rule that raises is caught and reported as ``RuleOutcome.ERROR``. One
  broken rule must not take down a verification run, and it must not silently
  vanish either.
"""

from __future__ import annotations

import traceback
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from ..domain.evidence import Evidence
from ..domain.verification import (
    RuleCategory,
    RuleOutcome,
    RuleResult,
    Severity,
    VerificationFinding,
)
from .context import VerificationContext


class ResultBuilder:
    """Collects what a rule observed; decides the outcome from that."""

    def __init__(self, rule_id: str, title: str, category: RuleCategory) -> None:
        self.rule_id = rule_id
        self.title = title
        self.category = category
        self._findings: list[VerificationFinding] = []
        self._examined: list[str] = []
        self._missing: list[str] = []
        self._limitations: list[str] = []
        self._notes: list[str] = []
        self._not_applicable_reason: str | None = None

    def examined(self, *items: str) -> None:
        """Record what was actually inspected. This is the rule's audit trail."""
        self._examined.extend(items)

    def note(self, text: str) -> None:
        self._notes.append(text)

    def limitation(self, text: str) -> None:
        """Record what a PASS from this rule does NOT establish."""
        self._limitations.append(text)

    def missing(self, text: str) -> None:
        """Record a fact the rule needed and did not have."""
        self._missing.append(text)

    def not_applicable(self, reason: str) -> None:
        self._not_applicable_reason = reason

    def finding(
        self,
        *,
        severity: Severity,
        title: str,
        description: str,
        components: Iterable[str] = (),
        nets: Iterable[str] = (),
        evidence: Iterable[Evidence] = (),
        auto_fixable: bool = False,
        suggested_fix: str | None = None,
        lesson_topic: str | None = None,
    ) -> VerificationFinding:
        found = VerificationFinding(
            rule_id=self.rule_id,
            severity=severity,
            title=title,
            description=description,
            affected_components=list(components),
            affected_nets=list(nets),
            evidence=list(evidence),
            auto_fixable=auto_fixable,
            suggested_fix=suggested_fix,
            lesson_topic=lesson_topic,
        )
        self._findings.append(found)
        return found

    @property
    def examined_items(self) -> list[str]:
        """What the rule has recorded inspecting so far."""
        return list(self._examined)

    @property
    def missing_items(self) -> list[str]:
        """Facts the rule has recorded needing and not having."""
        return list(self._missing)

    def build(self) -> RuleResult:
        significant = [f for f in self._findings if f.severity is not Severity.INFO]

        if significant:
            outcome = RuleOutcome.FAIL
        elif self._not_applicable_reason is not None and not self._findings:
            outcome = RuleOutcome.NOT_APPLICABLE
        elif self._missing:
            outcome = RuleOutcome.INSUFFICIENT_DATA
        else:
            outcome = RuleOutcome.PASS

        notes = list(self._notes)
        if self._not_applicable_reason is not None:
            notes.insert(0, self._not_applicable_reason)

        return RuleResult(
            rule_id=self.rule_id,
            title=self.title,
            category=self.category,
            outcome=outcome,
            findings=self._findings,
            examined=self._examined,
            missing_data=self._missing,
            limitations=self._limitations,
            notes=notes,
        )


RuleFunction = Callable[[VerificationContext, ResultBuilder], None]


@dataclass(frozen=True)
class RegisteredRule:
    rule_id: str
    title: str
    category: RuleCategory
    description: str
    function: RuleFunction = field(repr=False)

    def run(self, ctx: VerificationContext) -> RuleResult:
        builder = ResultBuilder(self.rule_id, self.title, self.category)
        try:
            self.function(ctx, builder)
        except Exception as exc:  # noqa: BLE001 -- one bad rule must not stop the run
            return RuleResult(
                rule_id=self.rule_id,
                title=self.title,
                category=self.category,
                outcome=RuleOutcome.ERROR,
                error_text=f"{type(exc).__name__}: {exc}",
                notes=["Rule raised an exception; its verdict is unavailable, not a pass."],
                examined=builder.examined_items,
                missing_data=[f"rule {self.rule_id} did not complete"],
                findings=[],
                limitations=[traceback.format_exc(limit=3)],
            )
        return builder.build()


_REGISTRY: dict[str, RegisteredRule] = {}


def rule(
    rule_id: str, title: str, category: RuleCategory, description: str = ""
) -> Callable[[RuleFunction], RuleFunction]:
    """Register a deterministic verification rule.

    Rules are pure functions of a :class:`VerificationContext`. No rule may call
    a language model, touch the network, or read a file. That is not a style
    preference: the product's claim is that verification is mechanical and
    reproducible, and a rule that consults a model would make it neither.
    """

    def decorate(function: RuleFunction) -> RuleFunction:
        if rule_id in _REGISTRY:
            raise ValueError(f"duplicate rule id {rule_id!r}")
        _REGISTRY[rule_id] = RegisteredRule(
            rule_id=rule_id,
            title=title,
            category=category,
            description=description or (function.__doc__ or "").strip().split("\n")[0],
            function=function,
        )
        return function

    return decorate


def all_rules() -> list[RegisteredRule]:
    """Every registered rule, in stable rule-id order."""
    return [_REGISTRY[k] for k in sorted(_REGISTRY)]


def get_rule(rule_id: str) -> RegisteredRule:
    return _REGISTRY[rule_id]


def clear_registry_for_testing() -> None:
    _REGISTRY.clear()
