"""Deterministic verification.

This is the load-bearing verification layer. It depends only on the domain
models and a part catalog: no language model, no network, no external tool. The
product's claim is that its checks are mechanical and reproducible, and that
claim is only true if nothing in this package can consult a model.

``tests/test_architecture.py`` enforces that mechanically.
"""

from .context import I2CBus, NetVoltage, ResolvedPin, TwoTerminalBridge, VerificationContext
from .engine import format_report, verify
from .registry import ResultBuilder, all_rules, get_rule, rule

__all__ = [
    "I2CBus",
    "NetVoltage",
    "ResolvedPin",
    "ResultBuilder",
    "TwoTerminalBridge",
    "VerificationContext",
    "all_rules",
    "format_report",
    "get_rule",
    "rule",
    "verify",
]
