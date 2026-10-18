"""tools/stackchan is an optional desk-robot companion; Ohmni must not depend on it."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ohmni_runtime_never_imports_stackchan():
    offenders = [
        str(path.relative_to(ROOT))
        for path in (ROOT / "src" / "ohmni").rglob("*.py")
        if re.search(r"^\s*(from|import)\s+(tools\.)?stackchan\b", path.read_text(encoding="utf-8"), re.MULTILINE)
    ]
    assert offenders == []


def test_stackchan_packages_are_not_ohmni_dependencies():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    for package in ("pyserial", "mlx-whisper", "mlx_whisper", "esptool", "platformio"):
        assert package not in pyproject


def test_stackchan_companion_is_not_a_python_package_of_tools():
    # tools/ is an importable package; keep the companion self-contained instead.
    assert not (ROOT / "tools" / "stackchan" / "__init__.py").exists()
    assert (ROOT / "tools" / "stackchan" / "companion" / "requirements.txt").is_file()
