"""The one SQLite database behind a local Ohmni workspace.

Connections, schema and identity live here so there is exactly one database
file, one place that decides where it lives, and one place that migrates it.
:mod:`ohmni.application.project_store` builds its projects, revisions and jobs
on top; nothing else opens a connection of its own.

Two honesties about what "ownership" means here.

* **It is attribution, not authorization.** Ohmni has no authentication. A row
  recording who created a project says who created it on this workspace; it
  does not stop anyone from reading or replacing it, and the API performs no
  ownership check. Modelling the owner is the prerequisite for real auth, not a
  substitute for it -- calling it access control would be the kind of claim this
  codebase refuses to make about anything else.
* **A workspace has one owner today.** Until sign-in exists there is a single
  seeded local user, so every project and job in a workspace attributes to it.
  The column is there so that stops being true without a schema migration.

The database path is configurable because the deployment target decides it: on
Fly the volume is mounted at ``/data`` and ``OHMNI_DB_PATH`` points into it, and
locally it sits beside the job artifacts it describes.
"""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

#: Set this to put the database somewhere specific. On Fly.io it points at the
#: mounted volume (see fly.toml); a value here always wins.
DB_PATH_ENV_VAR = "OHMNI_DB_PATH"
#: A fresh workspace gets this name.
DB_NAME = "ohmni.sqlite3"
#: What workspaces created before the database had a name of its own used. An
#: existing one keeps being used rather than being orphaned by a rename.
LEGACY_DB_NAME = "project-state.sqlite3"

IDENTIFIER_PATTERN = re.compile(r"^[0-9a-f]{16}$")


def _identifier(seed: str) -> str:
    """A stable 16-hex id, so a well-known row has the same id in every workspace."""
    return hashlib.sha256(seed.encode()).hexdigest()[:16]


#: The single local owner. Deterministic so a workspace opened twice attributes
#: to the same person rather than accumulating anonymous users.
LOCAL_USER_ID = _identifier("ohmni:local-workspace-owner")
LOCAL_USER_LABEL = "Local workspace"

#: Runs of the reference fixture belong to this project. It deliberately has no
#: revisions: `list_projects` joins revisions, so the saved-project shelf keeps
#: showing only projects a person actually authored.
DEMO_PROJECT_ID = _identifier("ohmni:reference-demo")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    created_at TEXT NOT NULL
);
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
"""

#: Columns added after the first schema shipped. SQLite can only add nullable
#: columns to an existing table, which is the whole reason ownership is nullable
#: rather than NOT NULL: a workspace that predates this has rows with no owner,
#: and inventing one for them would be a fact nobody recorded.
ADDED_COLUMNS = (
    ("projects", "owner_user_id", "TEXT REFERENCES users(user_id)"),
    ("jobs", "owner_user_id", "TEXT REFERENCES users(user_id)"),
    ("jobs", "project_id", "TEXT REFERENCES projects(project_id)"),
    ("jobs", "created_at", "TEXT"),
    ("jobs", "updated_at", "TEXT"),
)


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def resolve_database_path(output_root: Path) -> Path:
    """Decide which file this workspace's database is.

    ``OHMNI_DB_PATH`` wins outright: a deployment that names a path means it.
    Otherwise an existing database in the workspace keeps being used, because
    renaming a live file orphans every project and job already inside it. Only
    a workspace with neither gets the current name.
    """
    configured = os.environ.get(DB_PATH_ENV_VAR, "").strip()
    if configured:
        return Path(configured).expanduser()
    legacy = output_root / LEGACY_DB_NAME
    return legacy if legacy.is_file() else output_root / DB_NAME


@contextmanager
def connect(path: Path, *, parent: Path | None = None):
    """One transaction against the workspace database.

    The symlink and parent checks are the same guard the artifact paths use: a
    database that moved out from under the workspace is not this workspace's
    database, and following a symlink to find out would be the bug.
    """
    if path.is_symlink() or (parent is not None and path.resolve().parent != parent):
        raise ValueError("local project database path changed")
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize(db: sqlite3.Connection) -> None:
    """Create what is missing, add what was added later, seed the local owner."""
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(SCHEMA)
    for table, column, declaration in ADDED_COLUMNS:
        if not _has_column(db, table, column):
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
    ensure_user(db, LOCAL_USER_ID, LOCAL_USER_LABEL)


def _has_column(db: sqlite3.Connection, table: str, column: str) -> bool:
    return any(row["name"] == column for row in db.execute(f"PRAGMA table_info({table})"))


def ensure_user(db: sqlite3.Connection, user_id: str, label: str) -> str:
    """Record a user once. An existing label is left alone, not rewritten."""
    if not IDENTIFIER_PATTERN.fullmatch(user_id):
        raise ValueError("user id must be 16 hexadecimal characters")
    db.execute(
        "INSERT INTO users (user_id, label, created_at) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO NOTHING",
        (user_id, label, now()),
    )
    return user_id


def ensure_project(db: sqlite3.Connection, project_id: str, owner_user_id: str) -> str:
    """Record a well-known project once, without touching an existing one."""
    timestamp = now()
    db.execute(
        "INSERT INTO projects (project_id, created_at, updated_at, owner_user_id) "
        "VALUES (?, ?, ?, ?) ON CONFLICT(project_id) DO NOTHING",
        (project_id, timestamp, timestamp, owner_user_id),
    )
    return project_id


def users(db: sqlite3.Connection) -> list[dict]:
    return [dict(row) for row in db.execute("SELECT * FROM users ORDER BY created_at, user_id")]


__all__ = [
    "ADDED_COLUMNS",
    "DB_NAME",
    "DB_PATH_ENV_VAR",
    "DEMO_PROJECT_ID",
    "IDENTIFIER_PATTERN",
    "LEGACY_DB_NAME",
    "LOCAL_USER_ID",
    "LOCAL_USER_LABEL",
    "SCHEMA",
    "connect",
    "ensure_project",
    "ensure_user",
    "initialize",
    "now",
    "resolve_database_path",
    "users",
]
