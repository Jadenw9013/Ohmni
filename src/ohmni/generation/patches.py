"""Deterministic application of narrow, typed circuit operations."""

from ..adapters import PartCatalog
from ..domain import CircuitIR, PinRef
from .models import CircuitPatch


class PatchValidationError(ValueError):
    pass


def validate_circuit_references(circuit: CircuitIR, catalog: PartCatalog) -> None:
    for instance in circuit.components:
        spec = catalog.get(instance.part_id)
        if spec is None:
            raise PatchValidationError(f"COMPONENT_NOT_AVAILABLE: {instance.part_id}")
        for net in circuit.nets:
            for pin in net.connections:
                if pin.component == instance.ref and spec.pin(pin.pin) is None:
                    raise PatchValidationError(f"unknown pin {pin.component}.{pin.pin}")


def apply_patch(circuit: CircuitIR, patch: CircuitPatch, catalog: PartCatalog) -> CircuitIR:
    if patch.original_circuit_hash != circuit.content_hash:
        raise PatchValidationError("patch targets a different circuit fingerprint")
    result = circuit.model_copy(deep=True)
    for op in patch.operations:
        instance = result.component(op.component_ref)
        if instance is None:
            raise PatchValidationError(f"unknown component {op.component_ref}")
        spec = catalog.get(instance.part_id)
        if spec is None or spec.pin(op.pin) is None:
            raise PatchValidationError(f"unknown pin {op.component_ref}.{op.pin}")
        source, target = result.net(op.from_net), result.net(op.to_net)
        if source is None or target is None:
            raise PatchValidationError("patch references an unknown net")
        match = PinRef(component=op.component_ref, pin=op.pin)
        if match not in source.connections:
            raise PatchValidationError(f"{match} is not on {op.from_net}")
        source.connections.remove(match)
        target.connections.append(match)
    validate_circuit_references(result, catalog)
    return CircuitIR.model_validate(result.model_dump())
