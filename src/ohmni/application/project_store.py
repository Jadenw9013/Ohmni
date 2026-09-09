"""Local durable project revisions and job envelopes.

This store is for one local workspace, not a multi-user authorization boundary.
Briefs are accepted by the application before reaching this module. Each edit
inserts a new revision; a revision's input and preview are never overwritten.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ID_PATTERN = re.compile(r"^[0-9a-f]{16}$")


class ProjectWorkspaceInUseError(RuntimeError):
    """Another local server still owns this workspace's durable jobs."""


class ProjectWorkspaceLock:
    """Hold an OS-released lock so restart recovery cannot stop a live server."""

    def __init__(self, output_root: Path):
        root = output_root.resolve()
        root.mkdir(parents=True, exist_ok=True)
        path = root / "project-state.lock"
        if path.is_symlink():
            raise ValueError("local workspace lock cannot be a symlink")
        handle = path.open("a+b")
        try:
            if path.stat().st_size == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            raise ProjectWorkspaceInUseError("local project workspace is already in use") from None
        self._handle = handle

    def close(self):
        # Closing the descriptor releases both Windows byte-range and POSIX
        # advisory locks; process death also releases them without stale leases.
        self._handle.close()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _json(value: object) -> str:
    return json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"))


class ProjectStore:
    """SQLite transactions keep revision allocation and job association atomic."""

    def __init__(self, output_root: Path):
        self.root = output_root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "project-state.sqlite3"
        if self.path.is_symlink():
            raise ValueError("local project database cannot be a symlink")
        with self._connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS revisions (
                    revision_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(project_id),
                    number INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    brief TEXT NOT NULL,
                    brief_fingerprint TEXT NOT NULL,
                    preview TEXT NOT NULL,
                    job_id TEXT,
                    UNIQUE(project_id, number),
                    UNIQUE(job_id)
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    record TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS revision_jobs (
                    job_id TEXT PRIMARY KEY REFERENCES jobs(job_id),
                    project_id TEXT NOT NULL REFERENCES projects(project_id),
                    revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
                    attempt INTEGER NOT NULL,
                    UNIQUE(revision_id, attempt)
                );
            """)

    @contextmanager
    def _connection(self):
        if self.path.is_symlink() or self.path.resolve().parent != self.root:
            raise ValueError("local project database path changed")
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _revision(row: sqlite3.Row) -> dict:
        return {
            "revision_id": row["revision_id"],
            "number": row["number"],
            "created_at": row["created_at"],
            "brief": json.loads(row["brief"]),
            "brief_fingerprint": row["brief_fingerprint"],
            "preview": json.loads(row["preview"]),
            "job_id": row["job_id"],
        }

    def _project(self, db, project_id: str) -> dict | None:
        row = db.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
        if row is None:
            return None
        revisions = db.execute(
            "SELECT * FROM revisions WHERE project_id=? ORDER BY number", (project_id,)
        ).fetchall()
        return {**dict(row), "revisions": [self._revision(item) for item in revisions]}

    def get(self, project_id: str) -> dict | None:
        if not PROJECT_ID_PATTERN.fullmatch(project_id):
            return None
        with self._connection() as db:
            return self._project(db, project_id)

    def list_projects(self) -> list[dict]:
        with self._connection() as db:
            rows = db.execute("""
                SELECT p.*, r.revision_id, r.number, r.brief
                FROM projects p JOIN revisions r ON r.project_id=p.project_id
                WHERE r.number=(SELECT MAX(number) FROM revisions WHERE project_id=p.project_id)
                ORDER BY p.updated_at DESC, p.project_id
            """).fetchall()
        return [
            {
                "project_id": row["project_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "name": json.loads(row["brief"])["project_name"],
                "revision_count": row["number"],
                "latest_revision_id": row["revision_id"],
            }
            for row in rows
        ]

    def save_revision(self, brief: dict, fingerprint: str, preview: dict,
                      project_id: str | None = None) -> dict | None:
        """Create a project or append a revision without mutating older inputs."""
        if project_id is not None and not PROJECT_ID_PATTERN.fullmatch(project_id):
            return None
        now = _now()
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if project_id is None:
                project_id = uuid.uuid4().hex[:16]
                db.execute("INSERT INTO projects VALUES (?, ?, ?)", (project_id, now, now))
                number = 1
            else:
                project = self._project(db, project_id)
                if project is None:
                    return None
                number = len(project["revisions"]) + 1
                db.execute("UPDATE projects SET updated_at=? WHERE project_id=?", (now, project_id))
            db.execute(
                "INSERT INTO revisions VALUES (?, ?, ?, ?, ?, ?, ?, NULL)",
                (uuid.uuid4().hex[:16], project_id, number, now,
                 _json(brief), fingerprint, _json(preview)),
            )
            return self._project(db, project_id)

    def revision(self, project_id: str, revision_id: str) -> dict | None:
        if not all(PROJECT_ID_PATTERN.fullmatch(value) for value in (project_id, revision_id)):
            return None
        with self._connection() as db:
            row = db.execute(
                "SELECT * FROM revisions WHERE project_id=? AND revision_id=?",
                (project_id, revision_id),
            ).fetchone()
        return None if row is None else self._revision(row)

    def claim_job(self, project_id: str, revision_id: str, record: dict,
                  previous_job_id: str | None = None) -> str | None:
        """Claim an initial attempt or atomically replace one failed attempt.

        The caller supplies the failed ID it observed. An overlapping retry
        returns the newer attempt instead of launching another worker.
        """
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT job_id FROM revisions WHERE project_id=? AND revision_id=?",
                (project_id, revision_id),
            ).fetchone()
            if row is None:
                return None
            if row["job_id"] is not None:
                if row["job_id"] != previous_job_id:
                    return row["job_id"]
                previous = db.execute("SELECT record FROM jobs WHERE job_id=?", (previous_job_id,)).fetchone()
                if previous is None or json.loads(previous["record"]).get("status") != "failed":
                    return row["job_id"]
            db.execute("INSERT INTO jobs VALUES (?, ?)", (record["job_id"], _json(record)))
            attempt = db.execute(
                "SELECT COALESCE(MAX(attempt), 0)+1 FROM revision_jobs WHERE revision_id=?", (revision_id,)
            ).fetchone()[0]
            db.execute("INSERT INTO revision_jobs VALUES (?, ?, ?, ?)",
                       (record["job_id"], project_id, revision_id, attempt))
            db.execute(
                "UPDATE revisions SET job_id=? WHERE project_id=? AND revision_id=?",
                (record["job_id"], project_id, revision_id),
            )
            return record["job_id"]

    def save_job(self, record: dict) -> None:
        with self._connection() as db:
            db.execute(
                "INSERT INTO jobs VALUES (?, ?) ON CONFLICT(job_id) DO UPDATE SET record=excluded.record",
                (record["job_id"], _json(record)),
            )

    def job_revision(self, job_id: str) -> dict | None:
        """Return the immutable input of an attempt, including superseded retries."""
        with self._connection() as db:
            row = db.execute("""
                SELECT a.project_id, a.revision_id, a.attempt, r.number,
                       r.created_at, r.brief, r.brief_fingerprint
                FROM revision_jobs a JOIN revisions r ON r.revision_id=a.revision_id
                WHERE a.job_id=?
            """, (job_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["brief"] = json.loads(result["brief"])
        return result

    def load_jobs(self) -> list[tuple[str, dict]]:
        with self._connection() as db:
            rows = db.execute("SELECT job_id, record FROM jobs ORDER BY rowid").fetchall()
        return [(row["job_id"], json.loads(row["record"])) for row in rows]
