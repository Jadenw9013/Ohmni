"""Catalog learning metadata cannot become an admission or project write path."""

import json

import pytest
from test_visual_assets_server import _copy_web_root, _request, _server

from ohmni.application.component_library import (
    LibraryQuery,
    LibraryQueryError,
    LibrarySnapshotConflict,
    build_component_library,
)
from ohmni.catalog.loader import JsonPartCatalog
from ohmni.domain.component_atlas import current_library_eligibility
from scripts import demo_server


def sources(root=None):
    root = root or demo_server.WEB_ROOT
    return {name: (root / name).read_bytes() for name in (
        "component-visuals.json", "visual-assets.js", "vendor/three.module.js", "vendor/three.core.min.js")}


@pytest.fixture
def library():
    return build_component_library(JsonPartCatalog().all_parts(), sources())


def test_all_seed_parts_and_packages_are_truthfully_present(library):
    page = library.page(LibraryQuery())
    catalog = JsonPartCatalog()
    assert page["total"] == 12
    assert [item["part_id"] for item in page["items"]] == [p.part_id for p in catalog.all_parts()]
    assert sum(len(item["variants"]) for item in page["items"]) == 19
    for item in page["items"]:
        part = catalog.require(item["part_id"])
        assert item["description"] == part.description
        assert [v["record"]["package_variant"] for v in item["variants"]] == sorted(p.name for p in part.packages)
        for variant in item["variants"]:
            record = variant["record"]
            assert record["footprint"] is None and record["pin_map"] is None
            assert record["lifecycle_status"] == "SEED"
            assert variant["eligibility"]["eligibility"] == "LEARN_ONLY"
            assert variant["catalog_footprint_name"]
            assert any("not reverified" in text for text in record["evidence_summary"])


def test_missing_visual_never_guesses_a_similar_package(library):
    missing = [item.part_id for item in library.items if item.variants[0].visual_status == "MISSING_MODEL"]
    assert missing == ["MCP1700T-3302E-TT", "TMP102AIDRLR"]
    for item in library.items:
        for variant in item.variants:
            if variant.visual_status == "MISSING_MODEL":
                assert variant.record.visual is None
                assert "No model" in variant.visual_note
            else:
                assert variant.record.visual.representation_grade == "ILLUSTRATIVE_FAMILY"
                assert variant.record.visual.provenance.redistribution == "UNRESOLVED"


def test_snapshot_is_deterministic_detached_and_content_sensitive():
    parts = JsonPartCatalog().all_parts()
    visual_sources = sources()
    before = build_component_library(parts, visual_sources)
    assert before == build_component_library(list(reversed(parts)), dict(reversed(list(visual_sources.items()))))
    expected = before.model_dump_json()
    parts[0].description += " Changed description."
    assert before.model_dump_json() == expected
    assert build_component_library(parts, visual_sources).snapshot_sha256 != before.snapshot_sha256
    visual_sources["visual-assets.js"] += b"\n// changed renderer"
    after = build_component_library(JsonPartCatalog().all_parts(), visual_sources)
    assert after.snapshot_sha256 != before.snapshot_sha256
    assert before.model_dump_json() == expected
    assert before.items[0].variants[0].record.catalog_part == after.items[0].variants[0].record.catalog_part
    assert before.items[0].variants[0].record.visual.asset != after.items[0].variants[0].record.visual.asset


def test_vendor_and_mapping_changes_also_invalidate_the_snapshot(library):
    for name in sources():
        changed = sources()
        changed[name] += b" "  # Valid trailing JSON whitespace, still different exact source bytes.
        other = build_component_library(JsonPartCatalog().all_parts(), changed)
        assert other.snapshot_sha256 != library.snapshot_sha256, name


def test_pagination_has_no_gaps_and_requires_exact_snapshot(library):
    first = library.page(LibraryQuery(limit=5))
    second = library.page(LibraryQuery(limit=5, offset=first["next_offset"], snapshot=first["snapshot_sha256"]))
    third = library.page(LibraryQuery(limit=5, offset=second["next_offset"], snapshot=first["snapshot_sha256"]))
    assert third["next_offset"] is None
    assert [p["part_id"] for page in (first, second, third) for p in page["items"]] == [p.part_id for p in library.items]
    with pytest.raises(LibraryQueryError):
        library.page(LibraryQuery(offset=5))
    with pytest.raises(LibrarySnapshotConflict):
        library.page(LibraryQuery(snapshot="0" * 64))
    assert library.page(LibraryQuery(offset=99, snapshot=library.snapshot_sha256))["items"] == []


def test_search_and_category_filtering_do_not_confer_eligibility(library):
    assert [p["part_id"] for p in library.page(LibraryQuery(q="  bMe280  "))["items"]] == ["BME280"]
    assert library.page(LibraryQuery(category="resistor"))["total"] == 1
    assert library.page(LibraryQuery(category="not_a_category"))["total"] == 0
    assert library.page(LibraryQuery(q="SOT-23-5"))["items"][0]["part_id"] == "AP2112K-3.3TRG1"
    for item in library.page(LibraryQuery(status="all"))["items"]:
        assert all(v["eligibility"]["eligibility"] == "LEARN_ONLY" for v in item["variants"])


@pytest.mark.parametrize("status", ["QUARANTINED", "REVOKED", "UNSUPPORTED"])
def test_restricted_records_need_an_explicit_filter_and_stay_restricted(library, status):
    item = library.items[0]
    variant = item.variants[0]
    record = variant.record.model_copy(update={"lifecycle_status": status})
    item = item.model_copy(update={"variants": (variant.model_copy(update={
        "record": record, "eligibility": current_library_eligibility(record)}),)})
    restricted = library.model_copy(update={"items": (item,)})
    assert restricted.page(LibraryQuery())["items"] == []
    for query in (LibraryQuery(status="restricted"), LibraryQuery(status="all")):
        result = restricted.page(query)["items"][0]["variants"][0]
        assert result["eligibility"]["eligibility"] == status


@pytest.mark.parametrize("query", ["limit=0", "limit=51", "offset=-1", "limit=1.5", "limit=True",
                                  "limit=1&limit=2", "q=x&q=y", "verified=PASS", "status=ACTIVE",
                                  "snapshot=no", "q=" + "x"*121, "q=x&" + "x="*1100,
                                  "offset=100001", "offset=+1", "bare", "q=%FF"])
def test_untrusted_queries_are_bounded_and_reject_extra_authority(query):
    with pytest.raises(LibraryQueryError):
        LibraryQuery.from_url(query)


def test_invalid_or_incomplete_manifest_cannot_claim_available_visuals():
    incomplete = sources()
    del incomplete["visual-assets.js"]
    with pytest.raises(ValueError):
        build_component_library(JsonPartCatalog().all_parts(), incomplete)
    for mutation in ("duplicate", "unknown", "evidence"):
        changed = sources()
        manifest = json.loads(changed["component-visuals.json"])
        if mutation == "duplicate":
            manifest["bindings"].append(manifest["bindings"][0])
        elif mutation == "unknown":
            manifest["bindings"][0]["family"] = "invented"
        else:
            manifest["samples"][0]["dimensions"]["basis"] = "SOURCE_VERIFIED"
        changed["component-visuals.json"] = json.dumps(manifest).encode()
        with pytest.raises(ValueError):
            build_component_library(JsonPartCatalog().all_parts(), changed)


def test_live_read_endpoint_does_not_create_projects_jobs_or_exports(tmp_path):
    with _server(tmp_path / "jobs") as (server, base):
        before = server.projects.list_projects()
        status, headers, raw = _request(base, "/api/components?limit=2")
        page = json.loads(raw)
        assert status == 200 and page["total"] == 12
        assert page["ui_version"] == headers["x-ohmni-ui-version"] == server.ui_version
        assert page["server_instance_id"] == server.server_instance_id
        assert _request(base, "/api/components?offset=2")[0] == 400
        assert _request(base, "/api/components?snapshot=" + "0"*64)[0] == 409
        assert _request(base, "/api/components?evidence=PASS")[0] == 400
        next_page = json.loads(_request(base, f'/api/components?offset=2&limit=2&snapshot={page["snapshot_sha256"]}')[2])
        assert not {p["part_id"] for p in page["items"]} & {p["part_id"] for p in next_page["items"]}
        assert _request(base, "/api/components", {"command": "add_supported"})[0] != 200
        assert server.projects.list_projects() == before == []


def test_running_server_retains_its_snapshot_and_restart_rejects_old_identity(tmp_path):
    web_root = _copy_web_root(tmp_path / "web")
    with _server(tmp_path / "first", web_root) as (_server_instance, base):
        before = json.loads(_request(base, "/api/components")[2])
        path = web_root / "visual-assets.js"
        path.write_bytes(path.read_bytes() + b"\n// renderer changed")
        assert json.loads(_request(base, "/api/components")[2]) == before
    with _server(tmp_path / "second", web_root) as (_server_instance, base):
        after = json.loads(_request(base, "/api/components")[2])
        assert after["snapshot_sha256"] != before["snapshot_sha256"]
        assert _request(base, "/api/components?snapshot=" + before["snapshot_sha256"])[0] == 409
