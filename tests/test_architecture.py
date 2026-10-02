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
    "fastapi", "flask", "boto3", "networkx", "mcp", "mcp_types",
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


class TestMcpBoundary:
    def test_core_cannot_depend_on_mcp_transport(self):
        for directory in ("domain", "verifier", "catalog", "datasheet", "physical",
                          "routing", "manufacturing", "bom", "eda"):
            for path in _python_files(SRC / directory):
                assert not (_imported_top_level_modules(path) & {"mcp", "mcp_types"}), path
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        names = [alias.name for alias in node.names]
                    elif isinstance(node, ast.ImportFrom):
                        names = [node.module or "", *(alias.name for alias in node.names)]
                    else:
                        continue
                    assert all("mcp_server" not in name.split(".") for name in names), path

    def test_semantic_adapter_has_no_generation_or_eda_execution_path(self):
        for path in _python_files(SRC / "mcp_server"):
            assert not (_imported_top_level_modules(path) & {
                "anthropic", "openai", "subprocess", "requests", "httpx", "socket",
            }), path
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.ImportFrom):
                    assert not ({"eda", "generation", "routing", "manufacturing", "application"}
                                & set((node.module or "").split("."))), path


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
        spawning = {"erc.py", "simulation.py", "component_harness.py"}
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


class TestComponentSynthesisBoundaries:
    """COMPONENT_SYNTHESIS_PLAN.md's trust boundary, enforced mechanically.

    The plan's central claim is an ordering: a model proposes, a deterministic
    checker relocates the claim in the document, and only then is CAD generated
    and independently measured. Each test below defends one link of that chain
    against the refactor that would quietly collapse it.
    """

    #: The deterministic source checker is a pure function of immutable
    #: observations. A filesystem or clock dependency would make its receipts
    #: irreproducible; a provider import would make them circular.
    FORBIDDEN_IN_CONSTRAINT_VERIFIER = FORBIDDEN_IN_DOMAIN | {
        "random", "time", "datetime", "os", "pathlib", "tempfile", "shutil",
    }

    def test_the_source_checker_is_pure(self):
        path = SRC / "datasheet" / "constraint_verifier.py"
        offenders = _imported_top_level_modules(path) & self.FORBIDDEN_IN_CONSTRAINT_VERIFIER
        assert not offenders, (
            f"constraint_verifier.py imports {sorted(offenders)}. Source verification must be "
            "a pure function of the recorded observations."
        )

    def test_the_source_checker_never_reads_a_generated_artifact(self):
        """It reads the document. It must not be able to read what was emitted.

        ``land_pattern`` appears here as the name of a *printed table*, which is
        the point; what must not appear is any route to the generator or to a
        file it wrote.
        """
        source = (SRC / "datasheet" / "constraint_verifier.py").read_text(encoding="utf-8")
        for forbidden in ("from ..eda", "from ..physical", "import ohmni.eda",
                          "import ohmni.physical", "kicad", "measure_footprint",
                          "LandPatternDefinition", "read_text", "open("):
            assert forbidden not in source, (
                f"the source checker must not reach for {forbidden!r}; otherwise "
                "'the footprint matches the datasheet' degrades into 'the footprint "
                "matches the footprint'"
            )

    def test_the_asset_measurer_does_not_import_the_asset_generator(self):
        source = (SRC / "eda" / "kicad" / "component_asset_parser.py").read_text(
            encoding="utf-8"
        )
        assert "component_assets" not in source
        assert "land_patterns" not in source

    def test_the_asset_checker_measures_bytes_not_the_generator(self):
        """It may read the definitions for lineage, never for geometry.

        Sharing a tokenizer is fine. Taking the generator's in-memory pad
        objects as the oracle is not, so every geometric comparison must come
        from the parsed measurements.
        """
        source = (SRC / "physical" / "component_asset_verifier.py").read_text(encoding="utf-8")
        assert "from .asset_measurements import" in source
        for geometric in ("land_pattern.pads", "symbol_definition.pins"):
            assert geometric not in source, (
                f"{geometric} is the generator's own geometry; measure the emitted bytes"
            )

    def test_component_synthesis_domain_contracts_stay_pure(self):
        path = SRC / "domain" / "component_synthesis.py"
        assert not (_imported_top_level_modules(path) & FORBIDDEN_IN_DOMAIN)

    def test_every_provider_facing_schema_refuses_verdict_fields(self):
        from ohmni.domain.component_synthesis import (
            PROPOSAL_SCHEMAS,
            assert_proposal_schema_is_untrusted,
        )

        for schema in PROPOSAL_SCHEMAS:
            assert_proposal_schema_is_untrusted(schema)

    def test_the_multimodal_adapter_has_no_vendor_sdk(self):
        path = SRC / "datasheet" / "multimodal.py"
        offenders = _imported_top_level_modules(path) & {
            "anthropic", "openai", "httpx", "requests", "urllib", "socket",
        }
        assert not offenders, f"multimodal.py imports {sorted(offenders)}"

    def test_the_vision_sdk_lives_only_in_adapters_and_is_imported_lazily(self):
        path = SRC / "adapters" / "anthropic_vision.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        module_level = {
            alias.name.split(".")[0]
            for node in tree.body if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            node.module.split(".")[0]
            for node in tree.body if isinstance(node, ast.ImportFrom) and node.module
        }
        assert "anthropic" not in module_level, (
            "the vendor SDK must be imported inside __init__ so every other "
            "subsystem runs without it installed"
        )
        for other in _python_files(SRC / "datasheet"):
            assert "anthropic" not in _imported_top_level_modules(other), other

    def test_land_pattern_generation_has_no_model_network_or_clock_path(self):
        for name in ("land_patterns.py", "component_asset_verifier.py", "asset_measurements.py"):
            path = SRC / "physical" / name
            offenders = _imported_top_level_modules(path) & {
                "anthropic", "openai", "httpx", "requests", "socket", "subprocess",
                "random", "time", "datetime",
            }
            assert not offenders, f"{name} imports {sorted(offenders)}"

    def test_only_the_bounded_runner_starts_the_component_harness_tools(self):
        source = (SRC / "eda" / "kicad" / "component_harness.py").read_text(encoding="utf-8")
        assert "run_tool(" in source
        assert "shell=True" not in source
        assert "Popen" not in source


class TestObservationIsolationBoundary:
    """CS-AUDIT-006: the datasheet parse runs in a bounded child.

    This is a deliberate widening of the process boundary, so it is pinned the
    same way the EDA one is: exactly one module in `datasheet/` may start a
    child, it must do so through the shared bounded runner, and the child must
    bound itself before the parser library can exist in it.
    """

    def test_only_the_isolation_module_starts_a_child(self):
        allowed = {"isolated_observations.py"}
        for path in _python_files(SRC / "datasheet"):
            source = path.read_text(encoding="utf-8")
            assert "subprocess" not in _imported_top_level_modules(path), path
            assert "shell=True" not in source, path
            assert "Popen" not in source, path
            if "run_tool(" in source:
                assert path.name in allowed, f"{path.name} starts a child unexpectedly"

    def test_the_isolation_module_uses_the_shared_bounded_runner(self):
        source = (SRC / "datasheet" / "isolated_observations.py").read_text(encoding="utf-8")
        assert "from ..adapters.process import" in source
        assert "run_tool(" in source

    def test_the_worker_bounds_itself_before_importing_the_parser(self):
        """Ordering is the guarantee, so the ordering is what is asserted.

        A cap applied after PyMuPDF is imported and the file is read leaves a
        window in which an unbounded allocation is possible, which is the defect
        this worker exists to close.
        """
        source = (SRC / "datasheet" / "observation_worker.py").read_text(encoding="utf-8")
        cap = source.index("apply_address_space_limit(")
        parser_import = source.index("from .pdf import")
        assert cap < parser_import, (
            "the address-space cap must be applied before the parser library is "
            "imported; otherwise the worker can allocate before it is bounded"
        )
        assert source.index("import BoundedObservationExtractor") > cap

    def test_each_platform_helper_fails_closed(self):
        """No platform branch may report success when no cap was applied.

        Grepping the source for a hazard string cannot fail in any realistic
        regression, so this exercises the behaviour instead: each helper is made
        to fail, and the wrapper must propagate rather than return a mechanism
        name. The outer wrapper is covered separately in the isolation tests;
        what is pinned here is that neither branch can be rewritten to swallow.
        """
        import os
        from unittest.mock import patch

        from ohmni.adapters import resource_limits

        # Only the branch this platform takes is exercised. The other is covered
        # by the CI matrix, which runs the suite on ubuntu-latest as well; this
        # test does not pretend to check it here.
        helper = "_apply_windows_limit" if os.name == "nt" else "_apply_posix_limit"
        with patch.object(
            resource_limits, helper,
            side_effect=resource_limits.ResourceLimitUnavailable("mechanism failed"),
        ), pytest.raises(resource_limits.ResourceLimitUnavailable):
            resource_limits._apply_platform_limit(256 * 1024 * 1024)
