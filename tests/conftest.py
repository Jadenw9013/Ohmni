"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from ohmni.catalog import JsonPartCatalog, default_catalog
from ohmni.domain import CircuitIR, RequirementsSpec
from ohmni.fixtures import esp32_env_logger

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_JSON_DIR = REPO_ROOT / "fixtures" / "esp32_env_logger"


@pytest.fixture(autouse=True)
def _no_developer_ai_credentials(monkeypatch):
    """Keep a developer's real .env or shell key out of offline tests.

    Importing scripts/demo_server.py loads the root .env into os.environ, so a
    teammate with a configured key would otherwise run tests against a live
    provider. Tests that need a key set their own with monkeypatch.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OHMNI_ANTHROPIC_MODEL", raising=False)


@pytest.fixture(scope="session")
def catalog() -> JsonPartCatalog:
    return default_catalog()


@pytest.fixture
def requirements() -> RequirementsSpec:
    return esp32_env_logger.requirements()


@pytest.fixture
def golden() -> CircuitIR:
    return esp32_env_logger.golden()


def pytest_collection_modifyitems(items):
    """Keep external-tool tiers explicit without duplicating every marker."""
    for item in items:
        if item.get_closest_marker("kicad") is None:
            continue
        if item.get_closest_marker("slow_integration") is not None:
            continue
        if "test_golden_routing" in item.name:
            item.add_marker(pytest.mark.slow_integration)
        else:
            item.add_marker(pytest.mark.integration)
