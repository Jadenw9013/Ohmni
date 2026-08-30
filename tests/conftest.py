"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from ohmni.catalog import JsonPartCatalog, default_catalog
from ohmni.domain import CircuitIR, RequirementsSpec
from ohmni.fixtures import esp32_env_logger

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_JSON_DIR = REPO_ROOT / "fixtures" / "esp32_env_logger"


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
        if "test_golden_routing" in item.name:
            item.add_marker(pytest.mark.slow_integration)
        else:
            item.add_marker(pytest.mark.integration)
