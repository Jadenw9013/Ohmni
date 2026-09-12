"""Dependency direction, enforced mechanically.

REPO_STRUCTURE.md states the rule and nothing checked it. An architecture
constraint that is only written down is a suggestion; these tests make it real.

The two claims being defended:

* The domain layer is pure data and pure functions. If it could import a vendor
  SDK or open a socket, "testable without external tools" would be aspiration.
* No verification rule can consult a language model. The product's entire claim
  is that its checks are deterministic and reproducible, and one `import
  anthropic` inside a rule would quietly make that false.
"""

from __future__ import annotations

import ast
import importlib
import pkgutil
from pathlib import Path

import pytest

import ohmni
from ohmni.verifier.registry import all_rules

SRC = Path(ohmni.__file__).parent

#: Modules the domain layer may never reach for.
FORBIDDEN_IN_DOMAIN = {
    "anthropic", "openai", "httpx", "requests", "urllib", "urllib3", "socket",
    "subprocess", "fitz", "pymupdf", "pdfplumber", "pypdfium2", "sqlite3",
    "fastapi", "flask", "boto3", "networkx",
}

#: Additional modules a deterministic rule may never reach for. File and clock
#: access are excluded too: a rule whose verdict depends on the wall clock or
#: on a file outside the catalog is not reproducible.
FORBIDDEN_IN_RULES = FORBIDDEN_IN_DOMAIN | {"random", "time", "datetime", "os", "pathlib"}


def _iter_modules(package_path: Path, prefix: str):
    for info in pkgutil.walk_packages([str(package_path)], prefix=f"{prefix}."):
        yield info.name


def _imported_top_level_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
    return found


def _python_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*.py") if "__pycache__" not in p.parts)


class TestDomainPurity:
    @pytest.mark.parametrize(
        "path", _python_files(SRC / "domain"), ids=lambda p: p.name
    )
    def test_domain_imports_no_infrastructure(self, path: Path):
        offenders = _imported_top_level_modules(path) & FORBIDDEN_IN_DOMAIN
        assert not offenders, (
            f"{path.relative_to(SRC)} imports infrastructure: {sorted(offenders)}. "
            "The domain layer must stay pure data and pure functions."
        )

    @pytest.mark.parametrize(
        "path", _python_files(SRC / "domain"), ids=lambda p: p.name
    )
    def test_domain_does_not_import_sibling_packages(self, path: Path):
        source = path.read_text(encoding="utf-8")
        for sibling in ("verifier", "catalog", "adapters", "fixtures", "orchestration"):
            assert f"from ..{sibling}" not in source, (
                f"{path.relative_to(SRC)} imports ohmni.{sibling}; "
                "dependencies point at the domain, never out of it."
            )


class TestVerifierDeterminism:
    @pytest.mark.parametrize(
        "path", _python_files(SRC / "verifier" / "rules"), ids=lambda p: p.name
    )
    def test_rules_import_nothing_nondeterministic(self, path: Path):
        offenders = _imported_top_level_modules(path) & FORBIDDEN_IN_RULES
        assert not offenders, (
            f"{path.relative_to(SRC)} imports {sorted(offenders)}. A verification rule "
            "must be a pure function of the circuit and the catalog."
        )

    def test_verifier_package_imports_no_llm_or_network(self):
        for path in _python_files(SRC / "verifier"):
            offenders = _imported_top_level_modules(path) & {
                "anthropic", "openai", "httpx", "requests", "socket", "subprocess"
            }
            assert not offenders, f"{path.relative_to(SRC)} imports {sorted(offenders)}"

    def test_verifier_knows_nothing_about_pdf_ingestion(self):
        for path in _python_files(SRC / "verifier"):
            source = path.read_text(encoding="utf-8")
            assert "datasheet" not in _imported_top_level_modules(path)
            assert "from ..datasheet" not in source
            assert "import ohmni.datasheet" not in source

    def test_verification_is_reproducible(self, golden, catalog, requirements):
        from ohmni.verifier import verify

        first = verify(golden, catalog, requirements)
        second = verify(golden, catalog, requirements)
        assert first.report_id == second.report_id
        assert first.finding_ids() == second.finding_ids()
        assert first.coverage == second.coverage
        assert [r.outcome for r in first.results] == [r.outcome for r in second.results]


class TestRuleRegistry:
    def test_every_rule_has_an_id_title_and_description(self):
        for registered in all_rules():
            assert registered.rule_id.startswith("PB-"), registered.rule_id
            assert registered.title
            assert registered.description

    def test_rule_ids_are_unique(self):
        ids = [r.rule_id for r in all_rules()]
        assert len(ids) == len(set(ids))

    def test_the_specified_rule_families_all_exist(self):
        """Every check named in VERIFICATION.md and the brief is implemented."""
        ids = {r.rule_id for r in all_rules()}
        required = {
            "PB-ID-001",    # MPN / part identity
            "PB-ID-003",    # package and footprint consistency
            "PB-CONN-002",  # ground connectivity
            "PB-CONN-003",  # required power pins
            "PB-PWR-001",   # operating range and absolute maximum
            "PB-PWR-003",   # voltage-domain compatibility
            "PB-PWR-004",   # required decoupling
            "PB-PIN-001",   # output contention
            "PB-PIN-002",   # floating critical control pins
            "PB-I2C-001",   # I2C pull-ups
            "PB-I2C-003",   # duplicate I2C addresses
            "PB-LED-001",   # LED current limiting
            "PB-REG-001",   # regulator voltage compatibility
            "PB-REG-002",   # regulator current capacity
            "PB-UART-001",  # UART orientation
            "PB-USB-001",   # USB-C sink termination
        }
        assert required <= ids, f"missing rules: {sorted(required - ids)}"


class TestPackageImports:
    def test_every_module_imports_cleanly(self):
        for name in _iter_modules(SRC, "ohmni"):
            importlib.import_module(name)


class TestDatasheetBoundaries:
    def test_datasheet_pipeline_does_not_depend_on_electrical_verifier(self):
        for path in _python_files(SRC / "datasheet"):
            source = path.read_text(encoding="utf-8")
            assert "from ..verifier" not in source
            assert "import ohmni.verifier" not in source

    def test_only_pdf_adapter_imports_parser_library(self):
        for path in _python_files(SRC / "datasheet"):
            imports = _imported_top_level_modules(path)
            if path.name != "pdf.py":
                assert not ({"fitz", "pymupdf"} & imports), path.name

    def test_datasheet_pipeline_has_no_network_or_model_sdk(self):
        forbidden = {"anthropic", "openai", "httpx", "requests", "urllib", "socket"}
        for path in _python_files(SRC / "datasheet"):
            assert not (_imported_top_level_modules(path) & forbidden), path.name


class TestEdaBoundaries:
    def test_domain_and_verifier_do_not_import_eda(self):
        for directory in (SRC / "domain", SRC / "verifier"):
            for path in _python_files(directory):
                source = path.read_text(encoding="utf-8")
                assert "from ..eda" not in source
                assert "import ohmni.eda" not in source

    def test_process_spawning_stays_inside_the_bounded_runner(self):
        """Two modules start native tools; neither one invents how.

        `erc.py` owns the raw `subprocess` import, for the exception types it
        must catch. Everything else that starts a child -- `simulation.py` runs
        kicad-cli and ngspice -- goes through `adapters.process.run_tool`, which
        is what supplies the fixed argument vector, the absent shell and the
        bounded wait. The guard is that nobody writes their own process call,
        not that exactly one file may ever have one.
        """
        spawning = {"erc.py", "simulation.py"}
        for path in _python_files(SRC / "eda"):
            source = path.read_text(encoding="utf-8")
            if path.name != "erc.py":
                assert "subprocess" not in _imported_top_level_modules(path), path
            if "run_tool(" in source:
                assert path.name in spawning, f"{path.name} starts native tools unexpectedly"
            assert "shell=True" not in source, path

    def test_eda_compiler_has_no_model_or_network_dependency(self):
        forbidden = {"anthropic", "openai", "httpx", "requests", "socket"}
        for path in _python_files(SRC / "eda"):
            assert not (_imported_top_level_modules(path) & forbidden), path


class TestGenerationBoundaries:
    def test_generation_has_no_vendor_sdk_or_network_dependency(self):
        forbidden = {"anthropic", "openai", "httpx", "requests", "urllib", "socket"}
        for path in _python_files(SRC / "generation"):
            assert not (_imported_top_level_modules(path) & forbidden), path

    def test_generation_never_edits_eda_artifacts(self):
        for path in _python_files(SRC / "generation"):
            source = path.read_text(encoding="utf-8")
            assert ".write_text(" not in source
            assert ".write_bytes(" not in source


class TestSynthesisBoundaries:
    def test_synthesis_has_no_model_network_random_or_fixture_dependency(self):
        forbidden = {"anthropic", "openai", "httpx", "requests", "urllib", "socket", "random"}
        for path in _python_files(SRC / "synthesis"):
            imports = _imported_top_level_modules(path)
            source = path.read_text(encoding="utf-8")
            assert not (imports & forbidden), path
            assert "ohmni.fixtures" not in source
            assert "..fixtures" not in source
            assert "generation.fixtures" not in source


class TestPhysicalBoundaries:
    def test_physical_domain_is_pure_and_knows_no_kicad(self):
        forbidden={"subprocess","socket","requests","httpx","openai","anthropic"}
        for path in _python_files(SRC / "physical"):
            assert not (_imported_top_level_modules(path) & forbidden), path
            assert "from ..eda" not in path.read_text(encoding="utf-8")

    def test_pcb_compiler_and_geometry_have_no_llm_dependency(self):
        for path in [SRC / "eda" / "kicad" / "pcb_compiler.py", SRC / "eda" / "kicad" / "placement.py"]:
            source=path.read_text(encoding="utf-8")
            assert "LlmProvider" not in source
            assert "openai" not in source and "anthropic" not in source


class TestRoutingBoundaries:
    def test_routing_has_no_llm_network_random_or_generation_dependency(self):
        forbidden={"openai","anthropic","requests","httpx","socket","random"}
        for path in _python_files(SRC / "routing"):
            source=path.read_text(encoding="utf-8")
            assert not (_imported_top_level_modules(path)&forbidden),path
            assert "ohmni.generation" not in source


class TestManufacturingBoundaries:
    def test_deterministic_manufacturing_and_bom_have_no_llm_or_network_dependency(self):
        forbidden = {"openai", "anthropic", "requests", "httpx", "urllib", "socket", "random"}
        for directory in (SRC / "manufacturing", SRC / "bom"):
            for path in _python_files(directory):
                imports = _imported_top_level_modules(path)
                assert not (imports & forbidden), path
                source = path.read_text(encoding="utf-8")
                assert "ohmni.generation" not in source

    def test_only_fabrication_adapter_can_spawn_processes(self):
        for directory in (SRC / "manufacturing", SRC / "bom"):
            for path in _python_files(directory):
                if path.name != "exporter.py":
                    assert "subprocess" not in _imported_top_level_modules(path), path
