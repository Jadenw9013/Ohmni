"""One database per workspace: where it lives, what it records, what it migrates.

The migration test is the one that matters most. A workspace that predates this
schema holds real projects and real job envelopes, and opening it must add what
is missing without touching what is already there -- a store that lost a job on
upgrade would lose the artifacts it is the only index for.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from ohmni.application import database
from ohmni.application.project_store import ProjectStore

#: The schema exactly as it shipped before users and ownership existed.
LEGACY_SCHEMA = """
CREATE TABLE projects (
    project_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE revisions (
    revision_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id),
    number INTEGER NOT NULL, created_at TEXT NOT NULL, brief TEXT NOT NULL,
    brief_fingerprint TEXT NOT NULL, preview TEXT NOT NULL, job_id TEXT,
    UNIQUE(project_id, number), UNIQUE(job_id)
);
CREATE TABLE jobs (job_id TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE revision_jobs (
    job_id TEXT PRIMARY KEY REFERENCES jobs(job_id),
    project_id TEXT NOT NULL REFERENCES projects(project_id),
    revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
    attempt INTEGER NOT NULL, UNIQUE(revision_id, attempt)
);
"""

BRIEF = {"project_name": "Legacy sensor board"}
RECORD = {"job_id": "abcdef012345", "status": "complete", "progress": [],
          "report": {"kept": True}, "error": None, "error_code": None}


@pytest.fixture(autouse=True)
def _unconfigured(monkeypatch):
    """The environment must not decide where a test's database lives."""
    monkeypatch.delenv(database.DB_PATH_ENV_VAR, raising=False)


def _legacy_database(path):
    db = sqlite3.connect(path)
    try:
        db.executescript(LEGACY_SCHEMA)
        db.execute("INSERT INTO projects VALUES ('0123456789abcdef', 'then', 'then')")
        db.execute(
            "INSERT INTO revisions VALUES ('fedcba9876543210', '0123456789abcdef', 1, 'then', ?,"
            " 'fingerprint', '{}', NULL)", (json.dumps(BRIEF),),
        )
        db.execute("INSERT INTO jobs VALUES (?, ?)", (RECORD["job_id"], json.dumps(RECORD)))
        db.commit()
    finally:
        db.close()
    return path


class TestWhereTheDatabaseLives:
    def test_a_fresh_workspace_gets_the_current_name(self, tmp_path):
        assert database.resolve_database_path(tmp_path) == tmp_path / database.DB_NAME

    def test_an_existing_database_keeps_being_used_rather_than_orphaned(self, tmp_path):
        legacy = _legacy_database(tmp_path / database.LEGACY_DB_NAME)
        assert database.resolve_database_path(tmp_path) == legacy

    def test_the_environment_variable_wins_outright(self, tmp_path, monkeypatch):
        _legacy_database(tmp_path / database.LEGACY_DB_NAME)
        chosen = tmp_path / "elsewhere" / "ohmni.sqlite3"
        monkeypatch.setenv(database.DB_PATH_ENV_VAR, str(chosen))
        assert database.resolve_database_path(tmp_path) == chosen

    def test_a_configured_database_outside_the_workspace_opens(self, tmp_path, monkeypatch):
        """On Fly the volume holds the database one level above the artifacts."""
        chosen = tmp_path / "volume" / "ohmni.sqlite3"
        monkeypatch.setenv(database.DB_PATH_ENV_VAR, str(chosen))
        store = ProjectStore(tmp_path / "volume" / "demo-jobs")
        assert store.path == chosen and chosen.is_file()

    def test_a_symlinked_database_is_refused(self, tmp_path):
        real = _legacy_database(tmp_path / "real.sqlite3")
        link = tmp_path / "link.sqlite3"
        try:
            link.symlink_to(real)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks are not available to this user")
        with pytest.raises(ValueError, match="symlink"):
            ProjectStore(tmp_path, path=link)


class TestMigration:
    def test_opening_a_legacy_workspace_adds_what_is_missing_and_keeps_what_is_there(self, tmp_path):
        _legacy_database(tmp_path / database.LEGACY_DB_NAME)
        store = ProjectStore(tmp_path)
        assert store.path.name == database.LEGACY_DB_NAME

        # Everything the old workspace held is still exactly where it was.
        assert store.job(RECORD["job_id"]) == RECORD
        project = store.get("0123456789abcdef")
        assert project["revisions"][0]["brief"] == BRIEF
        assert project["created_at"] == "then"

        with store._connection() as db:
            columns = {row["name"] for row in db.execute("PRAGMA table_info(projects)")}
            job_columns = {row["name"] for row in db.execute("PRAGMA table_info(jobs)")}
        assert "owner_user_id" in columns
        assert {"owner_user_id", "project_id", "created_at", "updated_at"} <= job_columns
        # A row nobody attributed keeps no owner: inventing one would record a
        # fact that was never true.
        assert project["owner_user_id"] is None
        assert store.job_owner(RECORD["job_id"])["owner_user_id"] is None

    def test_opening_twice_is_not_a_second_migration(self, tmp_path):
        _legacy_database(tmp_path / database.LEGACY_DB_NAME)
        first = ProjectStore(tmp_path)
        second = ProjectStore(tmp_path)
        with second._connection() as db:
            assert len(database.users(db)) == 1
        assert first.job(RECORD["job_id"]) == second.job(RECORD["job_id"])


class TestOwnership:
    def test_the_local_owner_is_seeded_once_and_deterministically(self, tmp_path):
        store = ProjectStore(tmp_path)
        with store._connection() as db:
            people = database.users(db)
        assert [person["user_id"] for person in people] == [database.LOCAL_USER_ID]
        assert people[0]["label"] == database.LOCAL_USER_LABEL
        assert ProjectStore(tmp_path / "other").owner_user_id == database.LOCAL_USER_ID

    def test_a_saved_project_records_who_saved_it(self, tmp_path):
        store = ProjectStore(tmp_path)
        project = store.save_revision(BRIEF, "fingerprint", {"preview": True})
        assert project["owner_user_id"] == database.LOCAL_USER_ID

    def test_a_demo_job_belongs_to_the_workspace_demo_project(self, tmp_path):
        store = ProjectStore(tmp_path)
        store.claim_demo_job(RECORD)
        owner = store.job_owner(RECORD["job_id"])
        assert owner["owner_user_id"] == database.LOCAL_USER_ID
        assert owner["project_id"] == database.DEMO_PROJECT_ID
        assert owner["created_at"] and owner["updated_at"]

    def test_updating_a_job_does_not_rewrite_what_it_belongs_to(self, tmp_path):
        store = ProjectStore(tmp_path)
        store.claim_demo_job(RECORD)
        store.save_job({**RECORD, "status": "failed", "report": None,
                        "error": "Demo pipeline failed", "error_code": "pipeline_failed"})
        owner = store.job_owner(RECORD["job_id"])
        assert owner["project_id"] == database.DEMO_PROJECT_ID
        assert store.job(RECORD["job_id"])["status"] == "failed"

    def test_the_demo_project_stays_out_of_the_saved_project_shelf(self, tmp_path):
        """It exists to own demo jobs, not to look like something a person made."""
        store = ProjectStore(tmp_path)
        store.claim_demo_job(RECORD)
        assert store.list_projects() == []
        store.save_revision(BRIEF, "fingerprint", {"preview": True})
        assert [item["name"] for item in store.list_projects()] == ["Legacy sensor board"]

    def test_ownership_is_attribution_and_says_so(self):
        """No sign-in exists, so nothing here may read as an access check."""
        def prose(text):
            return " ".join(text.split())

        assert "attribution and not access control" in prose(ProjectStore.__doc__)
        assert "attribution, not authorization" in prose(database.__doc__)
