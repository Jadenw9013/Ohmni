"""Deterministic verification rules.

Importing this package registers every rule. Rules are deliberately grouped by
the verification layer they belong to in VERIFICATION.md, not by the part they
happen to inspect, so that a reader can see at a glance which layers have
coverage and which do not.
"""

from . import connectivity, identity, interfaces, led, pins, power, regulator, spi

__all__ = ["connectivity", "identity", "interfaces", "led", "pins", "power", "regulator", "spi"]
