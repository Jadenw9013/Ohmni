"""Typed component-behavior records and their deterministic registry."""

from .loader import BehaviorRegistry, BehaviorRegistryError, default_behavior_registry
from .models import (
    BehaviorClassRecord,
    BehaviorEntryRecord,
    BehaviorFidelity,
    BehaviorLayer,
    BehaviorManifest,
    BehaviorStatus,
    CatalogPartBinding,
    PackagePinOrder,
    SimulationDisposition,
)

__all__ = [
    "BehaviorClassRecord",
    "BehaviorEntryRecord",
    "BehaviorFidelity",
    "BehaviorLayer",
    "BehaviorManifest",
    "BehaviorRegistry",
    "BehaviorRegistryError",
    "BehaviorStatus",
    "CatalogPartBinding",
    "PackagePinOrder",
    "SimulationDisposition",
    "default_behavior_registry",
]
