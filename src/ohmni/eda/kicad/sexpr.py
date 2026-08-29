"""Tiny S-expression helpers; not a general KiCad parser."""

from __future__ import annotations

import re


def quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{escaped}"'


def identifier(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_+.-]", "_", value)


def number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")
