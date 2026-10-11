"""Bounded compatibility runner for an exact vendor PSpice model blob."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from ..adapters.process import ToolTimeoutError, run_tool
from .simulation import parse_operating_point

_UNSAFE = re.compile(
    r"^\s*(?:\.(?:include|inc|lib|control|endc|shell)\b|"
    r"(?:shell|source|cd|write|wrdata|hardcopy)\b)",
    re.IGNORECASE | re.MULTILINE,
)


class VendorCompatibilityResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    status: str
    model_sha256: str
    ngspice_version: str
    output_voltage_v: float | None = None
    adjust_voltage_v: float | None = None
    detail: str


def run_lm317_vendor_model(
    executable: str,
    model_bytes: bytes,
    expected_sha256: str,
    work_dir: Path,
) -> VendorCompatibilityResult:
    """Measure TI's exact PSpice model under ngspice-42 `psa` mode."""
    digest = hashlib.sha256(model_bytes).hexdigest()
    if digest != expected_sha256:
        raise ValueError("vendor model bytes do not match the approved SHA-256")
    try:
        model = model_bytes.decode("cp1252")
    except UnicodeDecodeError as exc:
        raise ValueError("vendor model encoding is not the recorded CP1252 text") from exc
    if _UNSAFE.search(model):
        raise ValueError("vendor model contains a file, shell or control directive")
    version = run_tool([executable, "-v"], timeout=10)
    version_text = version.stdout + version.stderr
    if version.returncode != 0 or not re.search(r"\bngspice-42\b", version_text, re.IGNORECASE):
        return VendorCompatibilityResult(
            status="unsupported_tool",
            model_sha256=digest,
            ngspice_version=version_text[:200],
            detail="the compatibility result requires ngspice-42",
        )
    deck = f"""LM317 vendor compatibility
V1 in 0 12
XREG in adj out out LM317_TRANS
RUP out adj 240
RDOWN adj 0 720
RLOAD out 0 1000
{model}
.op
.print op v(out) v(adj) i(V1)
.end
"""
    work_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lm317-psa-", dir=work_dir) as temporary:
        root = Path(temporary)
        scripts = root / "scripts"
        scripts.mkdir()
        (scripts / "spinit").write_text(
            "* isolated CS-T10 vendor compatibility\nset ngbehavior=psa\n",
            encoding="ascii",
            newline="\n",
        )
        path = root / "lm317.cir"
        path.write_text(deck, encoding="utf-8", newline="\n")
        environment = dict(os.environ)
        environment["SPICE_SCRIPTS"] = str(scripts.resolve())
        try:
            completed = run_tool(
                [executable, "-b", str(path.resolve())],
                timeout=30,
                environment=environment,
            )
        except ToolTimeoutError:
            return VendorCompatibilityResult(
                status="timed_out",
                model_sha256=digest,
                ngspice_version="ngspice-42",
                detail="vendor compatibility run timed out",
            )
    combined = completed.stdout + "\n" + completed.stderr
    if completed.returncode != 0 or re.search(r"^\s*(?:error|fatal):", combined, re.IGNORECASE | re.MULTILINE):
        return VendorCompatibilityResult(
            status="incompatible",
            model_sha256=digest,
            ngspice_version="ngspice-42",
            detail=combined[-500:],
        )
    point = parse_operating_point(completed.stdout)
    output = point.node_voltages.get("out")
    adjust = point.node_voltages.get("adj")
    if output is None or adjust is None:
        return VendorCompatibilityResult(
            status="empty_results",
            model_sha256=digest,
            ngspice_version="ngspice-42",
            detail="ngspice completed without the required operating-point observations",
        )
    return VendorCompatibilityResult(
        status="compatible",
        model_sha256=digest,
        ngspice_version="ngspice-42",
        output_voltage_v=output.value,
        adjust_voltage_v=adjust.value,
        detail="TI PSpice model ran in isolated ngspice psa compatibility mode",
    )


__all__ = ["VendorCompatibilityResult", "run_lm317_vendor_model"]
