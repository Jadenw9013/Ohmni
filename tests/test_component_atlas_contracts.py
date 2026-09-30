"""Adversarial boundary tests; no model, browser, PDF or native tool needed."""

import json

import pytest
from pydantic import ValidationError

from ohmni.domain.component_atlas import (
    ComponentReferenceRecord,
    DraftCommandRequest,
    DraftContext,
    Eligibility,
    PlacementTarget,
    VisualAssetRecord,
    check_request_binding,
    current_library_eligibility,
    invalidated_stages,
)


def ref(name="source", char="a"):
    return {"id": name, "sha256": char * 64}


def asset():
    return {
        "asset": ref("ohmni-procedural/sensor@v1"), "family": "sensor",
        "representation_grade": "ILLUSTRATIVE_FAMILY",
        "origin_policy": "ILLUSTRATION_ORIGIN", "contact_basis": "ILLUSTRATION_PARAMETERS",
        "dimensions": {"width_nm": 2_500_000, "depth_nm": 2_500_000,
                       "height_nm": 900_000, "basis": "ARTISTIC_SAMPLE"},
        "provenance": {"source": "apps/web/visual-assets.js", "license": "UNSPECIFIED",
                       "attribution": "Original procedural project source"},
        "limitations": ["Appearance only; dimensions do not establish package conformance."],
    }


def component():
    return {
        "catalog_part": ref("BME280"), "display_name": "Environmental sensor",
        "category": "sensor", "package_variant": "LGA-8", "footprint": ref("LGA-8"),
        "pin_map": ref("BME280-pins"), "visual": asset(), "lifecycle_status": "SEED",
        "evidence_summary": ["Catalog-reported; source verification pending."],
    }


def request(kind="move_existing", **command):
    if kind == "move_existing" and not command:
        command = {"component_ref": "U1", "target": {"x_nm": 1_000_000, "y_nm": 2_000_000}}
    return {
        "identity": {"draft_id": "draft-1", "project_id": "project-1",
                     "base_revision_id": "revision-1", "base_artifact_sha256": "a" * 64,
                     "catalog_snapshot_sha256": "b" * 64},
        "sequence": 2, "idempotency_key": "command-2", "command": {"kind": kind, **command},
    }


def context():
    return DraftContext(identity=request()["identity"], owner_workspace_id="local",
                        next_sequence=2, status="OPEN", existing_components=("U1", "R1"))


@pytest.mark.parametrize("status,expected", [
    ("SEED", Eligibility.LEARN_ONLY), ("ACTIVE", Eligibility.LEARN_ONLY),
    ("QUARANTINED", Eligibility.QUARANTINED), ("REVOKED", Eligibility.REVOKED),
    ("UNSUPPORTED", Eligibility.UNSUPPORTED),
])
def test_no_lifecycle_label_or_visual_grants_insertion(status, expected):
    value = component()
    value.update(lifecycle_status=status, supported_roles=["sensor"], supported_project_families=["A1"])
    assert current_library_eligibility(ComponentReferenceRecord(**value)).eligibility == expected
    value["visual"] = None
    assert current_library_eligibility(ComponentReferenceRecord(**value)).eligibility == expected


@pytest.mark.parametrize("field", ["design_eligibility", "verified", "admitted", "receipt", "status"])
def test_component_descriptions_cannot_carry_authority(field):
    with pytest.raises(ValidationError):
        ComponentReferenceRecord(**component(), **{field: "PASS"})


@pytest.mark.parametrize("grade", ["SOURCE_VERIFIED", "VERIFIED_GENERATED", "MANUFACTURER_MODEL"])
def test_unimplemented_visual_accuracy_is_not_claimable(grade):
    with pytest.raises(ValidationError):
        VisualAssetRecord(**(asset() | {"representation_grade": grade}))


def test_artifact_binding_requires_exact_footprint_and_source_pads():
    value = asset() | {"representation_grade": "ARTIFACT_BOUND"}
    with pytest.raises(ValidationError, match="footprint revision"):
        VisualAssetRecord(**value)
    value.update(footprint=ref("LGA-8"))
    with pytest.raises(ValidationError, match="source pads"):
        VisualAssetRecord(**value)
    value.update(contact_basis="SOURCE_PADS", origin_policy="FOOTPRINT_ORIGIN")
    good = ComponentReferenceRecord(**(component() | {"visual": value}))
    assert current_library_eligibility(good).eligibility == Eligibility.LEARN_ONLY
    value["footprint"] = ref("LGA-8", "b")
    with pytest.raises(ValidationError, match="revisions differ"):
        ComponentReferenceRecord(**(component() | {"visual": value}))


@pytest.mark.parametrize("change", [
    {"contact_basis": "SOURCE_PADS"}, {"origin_policy": "FOOTPRINT_ORIGIN"},
    {"footprint": ref("LGA-8")}, {"format": "GLB"}, {"units": "inch"},
    {"up_axis": "y"}, {"limitations": []},
    {"contact_plane_nm": False}, {"contact_plane_nm": 0.0},
])
def test_illustration_cannot_gain_unsupported_properties(change):
    with pytest.raises(ValidationError):
        VisualAssetRecord(**(asset() | change))


def test_license_review_and_provenance_are_required_not_inferred():
    value = asset()
    value["provenance"]["redistribution"] = "REVIEWED"
    with pytest.raises(ValidationError, match="license review"):
        VisualAssetRecord(**value)
    value["provenance"]["license_review"] = ref("review-1")
    assert VisualAssetRecord(**value).provenance.license_review.id == "review-1"
    del value["provenance"]["source"]
    with pytest.raises(ValidationError):
        VisualAssetRecord(**value)


def test_nested_records_are_immutable_and_input_lists_are_detached():
    value = asset()
    model = VisualAssetRecord(**value)
    before = model.content_sha256
    value["limitations"].append("new value")
    value["dimensions"]["width_nm"] = 30
    assert model.content_sha256 == before
    with pytest.raises(ValidationError):
        model.dimensions.width_nm = 30
    assert isinstance(model.limitations, tuple)


def test_copy_revalidates_invariants_and_changed_dimensions_change_identity():
    model = VisualAssetRecord(**asset())
    with pytest.raises(ValidationError):
        model.model_copy(update={"representation_grade": "ARTIFACT_BOUND"})
    changed = model.model_copy(update={"dimensions": model.dimensions.model_copy(update={"width_nm": 30})})
    assert changed.content_sha256 != model.content_sha256
    assert VisualAssetRecord.model_validate_json(model.model_dump_json()).content_sha256 == model.content_sha256


@pytest.mark.parametrize("value", [True, 1.0, 0.25, "1000", float("nan"), float("inf"), 500_000_001])
def test_coordinates_reject_coercion_nonfinite_and_out_of_bounds(value):
    with pytest.raises(ValidationError):
        PlacementTarget(x_nm=value, y_nm=0)


@pytest.mark.parametrize("value", [True, 90.0, "90000", -1, 360_000])
def test_rotation_has_one_canonical_integer_form(value):
    with pytest.raises(ValidationError):
        PlacementTarget(x_nm=0, y_nm=0, rotation_mdeg=value)


@pytest.mark.parametrize("where", ["root", "command", "target"])
@pytest.mark.parametrize("field", ["verified", "evidence", "nets", "design_eligibility", "status"])
def test_client_cannot_smuggle_authority_at_any_edit_level(where, field):
    value = request()
    target = value if where == "root" else value["command"] if where == "command" else value["command"]["target"]
    target[field] = "PASS"
    with pytest.raises(ValidationError):
        DraftCommandRequest.model_validate_json(json.dumps(value))


@pytest.mark.parametrize("field", ["draft_id", "project_id", "base_revision_id",
                                   "base_artifact_sha256", "catalog_snapshot_sha256"])
def test_every_identity_binding_rejects_stale_or_foreign_request(field):
    value = request()
    value["identity"][field] = "c" * 64 if field.endswith("sha256") else "other"
    with pytest.raises(ValueError, match="stale or mismatched"):
        check_request_binding(DraftCommandRequest(**value), context(), workspace_id="local")


@pytest.mark.parametrize("status", ["VALIDATING", "COMMITTED", "DISCARDED", "STALE"])
def test_closed_or_busy_drafts_reject_commands(status):
    with pytest.raises(ValueError, match="current state"):
        check_request_binding(DraftCommandRequest(**request()), context().model_copy(update={"status": status}),
                              workspace_id="local")


def test_workspace_sequence_and_missing_component_are_checked():
    value = DraftCommandRequest(**request())
    with pytest.raises(ValueError, match="another workspace"):
        check_request_binding(value, context(), workspace_id="other")
    with pytest.raises(ValueError, match="out of order"):
        check_request_binding(value.model_copy(update={"sequence": 3}), context(), workspace_id="local")
    other = DraftCommandRequest(**request(component_ref="U999", target={"x_nm": 0, "y_nm": 0}))
    with pytest.raises(ValueError, match="absent"):
        check_request_binding(other, context(), workspace_id="local")
    assert check_request_binding(value, context(), workspace_id="local") is None


def test_move_invalidates_physical_outputs_but_preserves_electrical_intent():
    stages = set(invalidated_stages(DraftCommandRequest(**request()).command))
    assert {"placement", "physical", "routing", "pcb", "drc", "manufacturing",
            "projection", "build_package", "bom", "economics"} <= stages
    assert not stages.intersection({"circuit", "semantic", "schematic", "erc"})


@pytest.mark.parametrize("kind,fields", [
    ("add_supported", {"role_id": "sensor", "catalog_part": ref("BME280"),
                       "requested_location": {"x_nm": 0, "y_nm": 0}}),
    ("remove_draft_addition", {"draft_component_id": "candidate-1"}),
    ("undo", {"target_sequence": 1}), ("redo", {"target_sequence": 1}),
])
def test_electrical_additions_and_history_invalidate_all_outputs(kind, fields):
    command = DraftCommandRequest(**request(kind, **fields)).command
    assert {"circuit", "requirements", "semantic", "erc", "bom", "build_package"} <= set(invalidated_stages(command))


@pytest.mark.parametrize("kind,fields", [
    ("add_mounting_feature", {"feature": ref("hole"), "target": {"x_nm": 0, "y_nm": 0}}),
    ("set_board_keepout", {"keepout_id": "k1", "points": [
        {"x_nm": 0, "y_nm": 0}, {"x_nm": 100, "y_nm": 0}, {"x_nm": 0, "y_nm": 100}]}),
])
def test_feature_request_schema_is_not_a_manufacturing_verdict(kind, fields):
    command = DraftCommandRequest(**request(kind, **fields)).command
    assert {"drc", "manufacturing", "build_package"} <= set(invalidated_stages(command))
    assert "PASS" not in command.model_dump_json()


def test_discard_has_no_base_artifact_invalidation_or_verification_result():
    command = DraftCommandRequest(**request("discard_draft")).command
    assert invalidated_stages(command) == ()
    assert command.model_dump() == {"kind": "discard_draft"}


@pytest.mark.parametrize("kind", ["undo", "redo"])
def test_history_cannot_reference_future_command(kind):
    value = DraftCommandRequest(**request(kind, target_sequence=2))
    with pytest.raises(ValueError, match="earlier command"):
        check_request_binding(value, context(), workspace_id="local")


def test_schema_and_hash_are_content_identity_not_receipts():
    schema = DraftCommandRequest.model_json_schema()
    forbidden = {"verified", "evidence", "status", "nets", "visual", "design_eligibility", "receipt"}
    for definition in [schema, *schema["$defs"].values()]:
        if definition.get("type") == "object":
            assert definition["additionalProperties"] is False
            assert not forbidden.intersection(definition["properties"])


def test_invalidated_stages_rejects_unknown_objects():
    with pytest.raises(TypeError):
        invalidated_stages({"kind": "move_existing"})


def test_unsafe_constructed_instances_are_revalidated_at_boundaries():
    # Pydantic model_construct deliberately bypasses validation. A receiving
    # boundary must not accept one merely because it has the right Python type.
    broken = DraftCommandRequest.model_construct(**(request() | {"sequence": True}))
    with pytest.raises(ValidationError):
        check_request_binding(broken, context(), workspace_id="local")
    record = ComponentReferenceRecord.model_construct(**(component() | {"lifecycle_status": "VERIFIED"}))
    with pytest.raises(ValidationError):
        current_library_eligibility(record)


def test_unknown_commands_and_duplicate_base_refs_are_rejected():
    with pytest.raises(ValidationError):
        DraftCommandRequest(**request("draw_copper", net="3V3"))
    with pytest.raises(ValidationError, match="unique"):
        context().model_copy(update={"existing_components": ("U1", "U1")})
