"""Durable, fail-closed persistence for synthesized component revisions.

Blob bytes and catalog publication deliberately use separate commits. A caller
must first place every artifact/report in the content-addressed blob store, then
publish a quarantined revision in one short SQLite transaction. A crash between
those steps can leave an unreferenced blob, but cannot expose a partial revision.

CS-T06 does not decide electrical eligibility. Consequently this module has no
active-revision table and :meth:`ComponentStore.activate` always refuses. CS-T07
owns the admission gates that can introduce that state.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import tempfile
from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..domain.component import ComponentSpec
from ..domain.component_admission import AdmissionRequest, evaluate_admission

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
LATEST_SCHEMA_VERSION = 3


class ComponentStoreError(RuntimeError):
    """Base class for explicit persistence outcomes."""


class BlobNotCommittedError(ComponentStoreError):
    """Publication referenced bytes that were not durably committed first."""


class IdempotencyConflictError(ComponentStoreError):
    """An import key was reused for different publication content."""


class ActivationDisabledError(ComponentStoreError):
    """Real catalog activation is unavailable until CS-T07 gates it."""


@dataclass(frozen=True)
class BlobReference:
    role: str
    digest: str


@dataclass(frozen=True)
class ReportReference:
    kind: str
    digest: str
    parent_digest: str | None = None


@dataclass(frozen=True)
class QuarantinedRevision:
    revision_id: str
    component_key: str
    record_digest: str
    publication_digest: str
    state: str
    assets: tuple[BlobReference, ...]
    reports: tuple[ReportReference, ...]


@dataclass(frozen=True)
class ActiveRevision:
    revision_id: str
    component_key: str
    record_digest: str
    publication_digest: str
    state: str
    assets: tuple[BlobReference, ...]
    reports: tuple[ReportReference, ...]


@dataclass(frozen=True)
class Migration:
    version: int
    statements: tuple[str, ...]


def _immutable_triggers(*tables: str) -> tuple[str, ...]:
    statements: list[str] = []
    for table in tables:
        for operation in ("UPDATE", "DELETE"):
            statements.append(
                f"CREATE TRIGGER immutable_{table}_{operation.lower()} "
                f"BEFORE {operation} ON {table} BEGIN "
                "SELECT RAISE(ABORT, 'immutable component admission record'); END"
            )
    return tuple(statements)


_MIGRATIONS = (
    Migration(
        version=1,
        statements=(
            """CREATE TABLE component_schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )""",
            """CREATE TABLE component_blobs (
                digest TEXT PRIMARY KEY,
                byte_count INTEGER NOT NULL CHECK(byte_count >= 0),
                committed_at TEXT NOT NULL
            )""",
            """CREATE TABLE component_revisions (
                revision_id TEXT PRIMARY KEY,
                component_key TEXT NOT NULL,
                record_digest TEXT NOT NULL,
                publication_digest TEXT NOT NULL,
                record_json TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state = 'QUARANTINED'),
                created_at TEXT NOT NULL,
                UNIQUE(component_key, publication_digest)
            )""",
            """CREATE TABLE component_imports (
                idempotency_key TEXT PRIMARY KEY,
                request_digest TEXT NOT NULL,
                revision_id TEXT NOT NULL REFERENCES component_revisions(revision_id),
                published_at TEXT NOT NULL
            )""",
            """CREATE TABLE component_revision_assets (
                revision_id TEXT NOT NULL REFERENCES component_revisions(revision_id),
                role TEXT NOT NULL,
                blob_digest TEXT NOT NULL REFERENCES component_blobs(digest),
                PRIMARY KEY(revision_id, role)
            )""",
            """CREATE TABLE component_reports (
                revision_id TEXT NOT NULL REFERENCES component_revisions(revision_id),
                kind TEXT NOT NULL,
                blob_digest TEXT NOT NULL REFERENCES component_blobs(digest),
                parent_digest TEXT REFERENCES component_blobs(digest),
                PRIMARY KEY(revision_id, kind)
            )""",
        ),
    ),
    Migration(
        version=2,
        statements=(
            """CREATE TABLE catalog_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                manifest_digest TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE catalog_snapshot_entries (
                snapshot_id TEXT NOT NULL REFERENCES catalog_snapshots(snapshot_id),
                component_key TEXT NOT NULL,
                revision_id TEXT NOT NULL REFERENCES component_revisions(revision_id),
                PRIMARY KEY(snapshot_id, component_key)
            )""",
            """CREATE TABLE component_revocations (
                revision_id TEXT PRIMARY KEY REFERENCES component_revisions(revision_id),
                reason TEXT NOT NULL,
                revoked_at TEXT NOT NULL
            )""",
            *_immutable_triggers(
                "component_blobs",
                "component_revisions",
                "component_imports",
                "component_revision_assets",
                "component_reports",
                "catalog_snapshots",
                "catalog_snapshot_entries",
                "component_revocations",
            ),
        ),
    ),
    Migration(
        version=3,
        statements=(
            """CREATE TABLE component_activations (
                revision_id TEXT PRIMARY KEY REFERENCES component_revisions(revision_id),
                decision_digest TEXT NOT NULL UNIQUE,
                decision_json TEXT NOT NULL,
                activated_at TEXT NOT NULL
            )""",
            *_immutable_triggers("component_activations"),
        ),
    ),
)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _canonical_json(value: object) -> str:
    return json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"))


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _text_digest(value: str) -> str:
    return _digest(value.encode("utf-8"))


def _validate_label(value: str, name: str) -> str:
    value = value.strip()
    if not value or len(value) > 200 or any(ord(character) < 32 for character in value):
        raise ValueError(f"{name} must be 1-200 printable characters")
    return value


def _apply_migrations(
    db: sqlite3.Connection, migrations: Sequence[Migration] = _MIGRATIONS
) -> None:
    """Apply each migration atomically and advance ``user_version`` last."""
    current = int(db.execute("PRAGMA user_version").fetchone()[0])
    versions = tuple(migration.version for migration in migrations)
    if versions != tuple(range(1, len(migrations) + 1)):
        raise ValueError("migrations must be contiguous and start at version 1")
    if current > len(migrations):
        raise ComponentStoreError(
            f"database schema {current} is newer than supported schema {len(migrations)}"
        )
    for migration in migrations[current:]:
        db.execute("BEGIN IMMEDIATE")
        try:
            for statement in migration.statements:
                db.execute(statement)
            db.execute(
                "INSERT INTO component_schema_migrations(version, applied_at) VALUES (?, ?)",
                (migration.version, _now()),
            )
            db.execute(f"PRAGMA user_version={migration.version}")
        except Exception:
            db.rollback()
            raise
        else:
            db.commit()


class ComponentStore:
    """SQLite catalog metadata plus workspace-local content-addressed blobs."""

    def __init__(self, database_path: Path, blob_root: Path):
        self.database_path = database_path.resolve()
        self.blob_root = blob_root.resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.blob_root.mkdir(parents=True, exist_ok=True)
        if self.database_path.is_symlink() or self.blob_root.is_symlink():
            raise ValueError("component store paths cannot be symbolic links")
        with self._connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            _apply_migrations(db)

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(self.database_path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
        finally:
            db.close()

    def _blob_path(self, digest: str) -> Path:
        if not SHA256_PATTERN.fullmatch(digest):
            raise ValueError("blob digest must be lowercase SHA-256")
        return self.blob_root / digest[:2] / digest[2:]

    def commit_blob(self, content: bytes) -> str:
        """Durably place immutable bytes, then register that completed commit."""
        digest = _digest(content)
        destination = self._blob_path(digest)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.is_symlink() or destination.read_bytes() != content:
                raise ComponentStoreError(f"content-addressed blob collision for {digest}")
        else:
            descriptor, temporary_name = tempfile.mkstemp(dir=destination.parent, prefix=".blob-")
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
        with self._connection() as db, db:
            db.execute(
                "INSERT INTO component_blobs(digest, byte_count, committed_at) VALUES (?, ?, ?) "
                "ON CONFLICT(digest) DO NOTHING",
                (digest, len(content), _now()),
            )
        return digest

    def _assert_committed(self, db: sqlite3.Connection, digests: Iterable[str]) -> None:
        for digest in sorted(set(digests)):
            row = db.execute(
                "SELECT byte_count FROM component_blobs WHERE digest=?", (digest,)
            ).fetchone()
            path = self._blob_path(digest)
            if row is None or not path.is_file() or path.is_symlink():
                raise BlobNotCommittedError(f"blob {digest} was not committed before publication")
            content = path.read_bytes()
            if len(content) != row["byte_count"] or _digest(content) != digest:
                raise BlobNotCommittedError(f"blob {digest} failed publication hash recheck")

    def publish_quarantined(
        self,
        *,
        idempotency_key: str,
        component_key: str,
        record: dict,
        assets: Sequence[BlobReference],
        reports: Sequence[ReportReference],
    ) -> QuarantinedRevision:
        """Publish one complete quarantined revision or return its prior result."""
        idempotency_key = _validate_label(idempotency_key, "idempotency key")
        component_key = _validate_label(component_key, "component key")
        if not assets:
            raise ValueError("a component revision requires at least one asset")
        asset_roles = tuple(_validate_label(item.role, "asset role") for item in assets)
        report_kinds = tuple(_validate_label(item.kind, "report kind") for item in reports)
        if len(set(asset_roles)) != len(asset_roles) or len(set(report_kinds)) != len(report_kinds):
            raise ValueError("asset roles and report kinds must be unique per revision")
        record_json = _canonical_json(record)
        record_digest = _text_digest(record_json)
        request_json = _canonical_json(
            {
                "component_key": component_key,
                "record_digest": record_digest,
                "assets": sorted((item.role, item.digest) for item in assets),
                "reports": sorted(
                    (item.kind, item.digest, item.parent_digest) for item in reports
                ),
            }
        )
        request_digest = _text_digest(request_json)
        revision_id = _text_digest(f"{component_key}\0{request_digest}")[:32]
        digests = [item.digest for item in assets]
        digests.extend(item.digest for item in reports)
        digests.extend(item.parent_digest for item in reports if item.parent_digest is not None)

        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                prior = db.execute(
                    "SELECT request_digest, revision_id FROM component_imports "
                    "WHERE idempotency_key=?",
                    (idempotency_key,),
                ).fetchone()
                if prior is not None:
                    if prior["request_digest"] != request_digest:
                        raise IdempotencyConflictError(
                            f"idempotency key {idempotency_key!r} was reused with different content"
                        )
                    db.rollback()
                    return self.revision(prior["revision_id"])
                self._assert_committed(db, digests)
                timestamp = _now()
                db.execute(
                    "INSERT INTO component_revisions VALUES (?, ?, ?, ?, ?, 'QUARANTINED', ?) "
                    "ON CONFLICT(component_key, publication_digest) DO NOTHING",
                    (
                        revision_id,
                        component_key,
                        record_digest,
                        request_digest,
                        record_json,
                        timestamp,
                    ),
                )
                for item in assets:
                    db.execute(
                        "INSERT INTO component_revision_assets VALUES (?, ?, ?) "
                        "ON CONFLICT(revision_id, role) DO NOTHING",
                        (revision_id, item.role, item.digest),
                    )
                for item in reports:
                    db.execute(
                        "INSERT INTO component_reports VALUES (?, ?, ?, ?) "
                        "ON CONFLICT(revision_id, kind) DO NOTHING",
                        (revision_id, item.kind, item.digest, item.parent_digest),
                    )
                db.execute(
                    "INSERT INTO component_imports VALUES (?, ?, ?, ?)",
                    (idempotency_key, request_digest, revision_id, timestamp),
                )
            except Exception:
                db.rollback()
                raise
            else:
                db.commit()
        return self.revision(revision_id)

    def revision(self, revision_id: str) -> QuarantinedRevision:
        with self._connection() as db:
            row = db.execute(
                "SELECT * FROM component_revisions WHERE revision_id=?", (revision_id,)
            ).fetchone()
            if row is None:
                raise KeyError(revision_id)
            assets = tuple(
                BlobReference(item["role"], item["blob_digest"])
                for item in db.execute(
                    "SELECT role, blob_digest FROM component_revision_assets "
                    "WHERE revision_id=? ORDER BY role",
                    (revision_id,),
                )
            )
            reports = tuple(
                ReportReference(item["kind"], item["blob_digest"], item["parent_digest"])
                for item in db.execute(
                    "SELECT kind, blob_digest, parent_digest FROM component_reports "
                    "WHERE revision_id=? ORDER BY kind",
                    (revision_id,),
                )
            )
        return QuarantinedRevision(
            revision_id=row["revision_id"],
            component_key=row["component_key"],
            record_digest=row["record_digest"],
            publication_digest=row["publication_digest"],
            state=row["state"],
            assets=assets,
            reports=reports,
        )

    def quarantined(self) -> tuple[QuarantinedRevision, ...]:
        """Diagnostic inventory. This is intentionally separate from discovery."""
        with self._connection() as db:
            identifiers = tuple(
                row[0]
                for row in db.execute(
                    "SELECT revision_id FROM component_revisions ORDER BY component_key, revision_id"
                )
            )
        return tuple(self.revision(identifier) for identifier in identifiers)

    def discover_active(self) -> tuple[ActiveRevision, ...]:
        """Return only admitted, non-revoked revisions for design discovery."""
        with self._connection() as db:
            identifiers = tuple(
                row[0]
                for row in db.execute(
                    """SELECT a.revision_id FROM component_activations a
                    JOIN component_revisions r ON r.revision_id=a.revision_id
                    LEFT JOIN component_revocations x ON x.revision_id=a.revision_id
                    WHERE x.revision_id IS NULL
                    ORDER BY r.component_key, r.revision_id"""
                )
            )
        active: list[ActiveRevision] = []
        for identifier in identifiers:
            revision = self.revision(identifier)
            active.append(ActiveRevision(
                revision_id=revision.revision_id,
                component_key=revision.component_key,
                record_digest=revision.record_digest,
                publication_digest=revision.publication_digest,
                state="ACTIVE",
                assets=revision.assets,
                reports=revision.reports,
            ))
        return tuple(active)

    def active_specs(self) -> tuple[tuple[ActiveRevision, ComponentSpec], ...]:
        """Read the exact admitted specs behind the current active inventory.

        The activation decision is immutable and hash checked when it is written.
        Design discovery therefore consumes that decision rather than rebuilding a
        component from mutable source or report files.
        """
        active = {item.revision_id: item for item in self.discover_active()}
        with self._connection() as db:
            rows = db.execute(
                "SELECT revision_id, decision_json FROM component_activations ORDER BY revision_id"
            ).fetchall()
        result = []
        for row in rows:
            revision = active.get(row["revision_id"])
            if revision is None:
                continue
            decision = json.loads(row["decision_json"])
            spec = decision.get("component_spec")
            if spec is None:
                raise ComponentStoreError("active admission decision has no component spec")
            result.append((revision, ComponentSpec.model_validate(spec)))
        return tuple(result)

    def activate(self, request: AdmissionRequest) -> ActiveRevision:
        """Rerun CS-T07 gates and activate their exact passing publication."""
        if not isinstance(request, AdmissionRequest):
            raise ActivationDisabledError(
                "direct activation is disabled; a complete CS-T07 AdmissionRequest is required"
            )
        request = AdmissionRequest.model_validate(request.model_dump(mode="json"))
        decision = evaluate_admission(request)
        if not decision.admitted or decision.component_spec is None:
            raise ActivationDisabledError("the CS-T07 admission decision did not pass")
        decision_json = _canonical_json(decision.model_dump(mode="json"))
        if _text_digest(decision_json) != decision.decision_digest:
            raise ComponentStoreError("admission decision digest does not match its content")
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute(
                    "SELECT publication_digest FROM component_revisions WHERE revision_id=?",
                    (decision.revision_id,),
                ).fetchone()
                if row is None:
                    raise KeyError(decision.revision_id)
                if row["publication_digest"] != decision.publication_digest:
                    raise ComponentStoreError(
                        "admission decision was evaluated for different publication content"
                    )
                if db.execute(
                    "SELECT 1 FROM component_revocations WHERE revision_id=?",
                    (decision.revision_id,),
                ).fetchone() is not None:
                    raise ComponentStoreError("a revoked revision cannot be activated")
                prior = db.execute(
                    "SELECT decision_digest FROM component_activations WHERE revision_id=?",
                    (decision.revision_id,),
                ).fetchone()
                if prior is not None:
                    if prior["decision_digest"] != decision.decision_digest:
                        raise IdempotencyConflictError(
                            "revision was already activated by a different decision"
                        )
                    db.rollback()
                    return self._active_revision(decision.revision_id)
                db.execute(
                    "INSERT INTO component_activations VALUES (?, ?, ?, ?)",
                    (decision.revision_id, decision.decision_digest, decision_json, _now()),
                )
            except Exception:
                db.rollback()
                raise
            else:
                db.commit()
        return self._active_revision(decision.revision_id)

    def _active_revision(self, revision_id: str) -> ActiveRevision:
        revision = self.revision(revision_id)
        return ActiveRevision(
            revision_id=revision.revision_id,
            component_key=revision.component_key,
            record_digest=revision.record_digest,
            publication_digest=revision.publication_digest,
            state="ACTIVE",
            assets=revision.assets,
            reports=revision.reports,
        )

    def create_snapshot(self, revision_ids: Sequence[str]) -> str:
        """Pin exact non-revoked revisions; snapshots do not imply activation."""
        if not revision_ids or len(set(revision_ids)) != len(revision_ids):
            raise ValueError("snapshot revisions must be a non-empty unique sequence")
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                entries: list[tuple[str, str]] = []
                for revision_id in revision_ids:
                    row = db.execute(
                        "SELECT component_key FROM component_revisions WHERE revision_id=?",
                        (revision_id,),
                    ).fetchone()
                    revoked = db.execute(
                        "SELECT 1 FROM component_revocations WHERE revision_id=?", (revision_id,)
                    ).fetchone()
                    if row is None:
                        raise KeyError(revision_id)
                    if revoked is not None:
                        raise ComponentStoreError(f"revoked revision {revision_id} cannot enter snapshot")
                    entries.append((row["component_key"], revision_id))
                if len({key for key, _ in entries}) != len(entries):
                    raise ValueError("snapshot cannot contain two revisions of one component")
                manifest = _canonical_json(sorted(entries))
                manifest_digest = _text_digest(manifest)
                snapshot_id = manifest_digest[:32]
                db.execute(
                    "INSERT INTO catalog_snapshots VALUES (?, ?, ?) "
                    "ON CONFLICT(snapshot_id) DO NOTHING",
                    (snapshot_id, manifest_digest, _now()),
                )
                for component_key, revision_id in entries:
                    db.execute(
                        "INSERT INTO catalog_snapshot_entries VALUES (?, ?, ?) "
                        "ON CONFLICT(snapshot_id, component_key) DO NOTHING",
                        (snapshot_id, component_key, revision_id),
                    )
            except Exception:
                db.rollback()
                raise
            else:
                db.commit()
        return snapshot_id

    def snapshot(self, snapshot_id: str) -> tuple[tuple[str, str], ...]:
        with self._connection() as db:
            exists = db.execute(
                "SELECT 1 FROM catalog_snapshots WHERE snapshot_id=?", (snapshot_id,)
            ).fetchone()
            if exists is None:
                raise KeyError(snapshot_id)
            return tuple(
                (row["component_key"], row["revision_id"])
                for row in db.execute(
                    "SELECT component_key, revision_id FROM catalog_snapshot_entries "
                    "WHERE snapshot_id=? ORDER BY component_key",
                    (snapshot_id,),
                )
            )

    def revoke(self, revision_id: str, reason: str) -> None:
        """Append a revocation; historical revision and snapshot bytes stay intact."""
        reason = _validate_label(reason, "revocation reason")
        with self._connection() as db, db:
            exists = db.execute(
                "SELECT 1 FROM component_revisions WHERE revision_id=?", (revision_id,)
            ).fetchone()
            if exists is None:
                raise KeyError(revision_id)
            prior = db.execute(
                "SELECT reason FROM component_revocations WHERE revision_id=?", (revision_id,)
            ).fetchone()
            if prior is not None:
                if prior["reason"] != reason:
                    raise IdempotencyConflictError("revision was already revoked for another reason")
                return
            db.execute(
                "INSERT INTO component_revocations VALUES (?, ?, ?)",
                (revision_id, reason, _now()),
            )

    def is_revoked(self, revision_id: str) -> bool:
        with self._connection() as db:
            return db.execute(
                "SELECT 1 FROM component_revocations WHERE revision_id=?", (revision_id,)
            ).fetchone() is not None

    def orphaned_blobs(self) -> tuple[str, ...]:
        """List explicit crash residue that no published revision references."""
        with self._connection() as db:
            return tuple(
                row[0]
                for row in db.execute(
                    """SELECT digest FROM component_blobs
                    WHERE digest NOT IN (SELECT blob_digest FROM component_revision_assets)
                      AND digest NOT IN (SELECT blob_digest FROM component_reports)
                      AND digest NOT IN (
                          SELECT parent_digest FROM component_reports WHERE parent_digest IS NOT NULL
                      )
                    ORDER BY digest"""
                )
            )


__all__ = [
    "LATEST_SCHEMA_VERSION",
    "ActivationDisabledError",
    "ActiveRevision",
    "BlobNotCommittedError",
    "BlobReference",
    "ComponentStore",
    "ComponentStoreError",
    "IdempotencyConflictError",
    "Migration",
    "QuarantinedRevision",
    "ReportReference",
]
