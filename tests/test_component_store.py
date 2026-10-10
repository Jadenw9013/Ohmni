from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from ohmni.catalog.component_store import (
    LATEST_SCHEMA_VERSION,
    ActivationDisabledError,
    BlobNotCommittedError,
    BlobReference,
    ComponentStore,
    ComponentStoreError,
    IdempotencyConflictError,
    Migration,
    ReportReference,
    _apply_migrations,
)


def _store(tmp_path: Path) -> ComponentStore:
    return ComponentStore(tmp_path / "catalog.sqlite3", tmp_path / "blobs")


def _publish(store: ComponentStore, key: str = "import-1"):
    footprint = store.commit_blob(b"(footprint immutable)")
    source = store.commit_blob(b"source receipt")
    report = store.commit_blob(b"verification report")
    return store.publish_quarantined(
        idempotency_key=key,
        component_key="ACME:PART-1:SOIC-8",
        record={"manufacturer": "ACME", "mpn": "PART-1", "package": "SOIC-8"},
        assets=(BlobReference("footprint", footprint),),
        reports=(ReportReference("source", source), ReportReference("asset", report, source)),
    )


def test_schema_is_versioned_and_restart_safe(tmp_path: Path):
    first = _store(tmp_path)
    revision = _publish(first)

    reopened = _store(tmp_path)

    assert reopened.revision(revision.revision_id) == revision
    with sqlite3.connect(reopened.database_path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION
        assert db.execute(
            "SELECT version FROM component_schema_migrations ORDER BY version"
        ).fetchall() == [(version,) for version in range(1, LATEST_SCHEMA_VERSION + 1)]


def test_failed_migration_rolls_back_schema_and_version(tmp_path: Path):
    database_path = tmp_path / "rollback.sqlite3"
    migrations = (
        Migration(
            1,
            (
                "CREATE TABLE component_schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)",
                "CREATE TABLE stable(value TEXT)",
            ),
        ),
        Migration(2, ("CREATE TABLE must_disappear(value TEXT)", "INVALID SQL")),
    )
    with sqlite3.connect(database_path) as db, pytest.raises(sqlite3.OperationalError):
        _apply_migrations(db, migrations)
    with sqlite3.connect(database_path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
        tables = {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
    assert "stable" in tables
    assert "must_disappear" not in tables


def test_blob_must_be_committed_and_is_rechecked_at_publication(tmp_path: Path):
    store = _store(tmp_path)
    fake = "0" * 64
    with pytest.raises(BlobNotCommittedError):
        store.publish_quarantined(
            idempotency_key="missing",
            component_key="ACME:MISSING:SOIC-8",
            record={"mpn": "MISSING"},
            assets=(BlobReference("footprint", fake),),
            reports=(),
        )
    digest = store.commit_blob(b"original")
    store._blob_path(digest).write_bytes(b"tampered")
    with pytest.raises(BlobNotCommittedError, match="hash recheck"):
        store.publish_quarantined(
            idempotency_key="tampered",
            component_key="ACME:TAMPERED:SOIC-8",
            record={"mpn": "TAMPERED"},
            assets=(BlobReference("footprint", digest),),
            reports=(),
        )
    assert store.quarantined() == ()


def test_duplicate_concurrent_import_is_one_idempotent_publication(tmp_path: Path):
    store = _store(tmp_path)
    footprint = store.commit_blob(b"same footprint")

    def publish():
        return store.publish_quarantined(
            idempotency_key="same-request",
            component_key="ACME:RACE:SOIC-8",
            record={"mpn": "RACE"},
            assets=(BlobReference("footprint", footprint),),
            reports=(),
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = tuple(pool.map(lambda _: publish(), range(16)))

    assert len({result.revision_id for result in results}) == 1
    assert len(store.quarantined()) == 1


def test_reused_idempotency_key_with_different_content_is_explicit(tmp_path: Path):
    store = _store(tmp_path)
    _publish(store, "same-key")
    digest = store.commit_blob(b"other")
    with pytest.raises(IdempotencyConflictError):
        store.publish_quarantined(
            idempotency_key="same-key",
            component_key="ACME:OTHER:SOIC-8",
            record={"mpn": "OTHER"},
            assets=(BlobReference("footprint", digest),),
            reports=(),
        )


def test_same_record_with_different_assets_creates_distinct_immutable_revisions(tmp_path: Path):
    store = _store(tmp_path)
    first = _publish(store, "first-assets")
    other = store.commit_blob(b"different footprint")
    second = store.publish_quarantined(
        idempotency_key="second-assets",
        component_key=first.component_key,
        record={"manufacturer": "ACME", "mpn": "PART-1", "package": "SOIC-8"},
        assets=(BlobReference("footprint", other),),
        reports=(),
    )
    assert first.record_digest == second.record_digest
    assert first.revision_id != second.revision_id
    assert first.assets != second.assets


def test_interrupted_blob_first_sequence_is_explicit_orphan_and_retriable(tmp_path: Path):
    store = _store(tmp_path)
    orphan = store.commit_blob(b"crash after this commit")
    assert store.orphaned_blobs() == (orphan,)

    reopened = _store(tmp_path)
    revision = reopened.publish_quarantined(
        idempotency_key="resume-after-crash",
        component_key="ACME:RESUMED:SOIC-8",
        record={"mpn": "RESUMED"},
        assets=(BlobReference("footprint", orphan),),
        reports=(),
    )
    assert revision.state == "QUARANTINED"
    assert reopened.orphaned_blobs() == ()


def test_quarantine_never_enters_active_discovery_and_activation_refuses(tmp_path: Path):
    store = _store(tmp_path)
    revision = _publish(store)
    assert store.quarantined() == (revision,)
    assert store.discover_active() == ()
    with pytest.raises(ActivationDisabledError, match="CS-T07"):
        store.activate(revision.revision_id)


def test_snapshots_pin_exact_revisions_and_revocation_preserves_history(tmp_path: Path):
    store = _store(tmp_path)
    revision = _publish(store)
    snapshot_id = store.create_snapshot((revision.revision_id,))

    store.revoke(revision.revision_id, "superseded source document")

    assert store.is_revoked(revision.revision_id)
    assert store.snapshot(snapshot_id) == ((revision.component_key, revision.revision_id),)
    assert store.revision(revision.revision_id) == revision
    with pytest.raises(ComponentStoreError, match="revoked revision"):
        store.create_snapshot((revision.revision_id,))
    store.revoke(revision.revision_id, "superseded source document")
    with pytest.raises(IdempotencyConflictError):
        store.revoke(revision.revision_id, "different reason")


def test_revision_report_and_snapshot_rows_are_immutable(tmp_path: Path):
    store = _store(tmp_path)
    revision = _publish(store)
    snapshot_id = store.create_snapshot((revision.revision_id,))
    with sqlite3.connect(store.database_path) as db:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            db.execute(
                "UPDATE component_revisions SET component_key='changed' WHERE revision_id=?",
                (revision.revision_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            db.execute("DELETE FROM catalog_snapshots WHERE snapshot_id=?", (snapshot_id,))
