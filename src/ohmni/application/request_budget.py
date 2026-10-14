"""Bounded admission for every request that can reach a paid model provider.

Three independent limits, all global (no per-IP trust, no forwarded headers):

* a durable daily count, incremented atomically in SQLite before the provider
  is called and never refunded, so failed calls count and a restart does not
  reset it;
* a bounded number of in-flight billed requests, held by a lease that the
  caller releases only when its provider work has finished; and
* a small burst limit over a sliding window.

A request count is not a dollar guarantee: one admitted request can make
several provider attempts (retries, repair rounds). If the counter cannot be
read or written, or the configuration is invalid, every billed request is
refused. There is deliberately no reset or bypass route; operators reset a
day's count only with local tooling (``scripts/ai_budget.py``).
"""

from __future__ import annotations

import math
import os
import sqlite3
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

#: Defaults sized for a supervised hackathon demonstration: a presenter and a
#: handful of judges can exercise every AI path many times, while a runaway
#: client or a scripted loop stops at a small, known number of paid requests.
DEFAULT_DAILY_LIMIT = 200
DEFAULT_MAX_IN_FLIGHT = 2  # matches the existing two-active-jobs local capacity
DEFAULT_BURST_LIMIT = 6
DEFAULT_BURST_WINDOW_SECONDS = 60
CONCURRENCY_RETRY_AFTER_SECONDS = 15
BILLED_ROUTES = ("planner", "assistant", "brief", "generation")
ENVIRONMENT = {
    "daily_limit": ("OHMNI_AI_DAILY_LIMIT", DEFAULT_DAILY_LIMIT),
    "max_in_flight": ("OHMNI_AI_MAX_IN_FLIGHT", DEFAULT_MAX_IN_FLIGHT),
    "burst_limit": ("OHMNI_AI_BURST_LIMIT", DEFAULT_BURST_LIMIT),
    "burst_window_seconds": ("OHMNI_AI_BURST_WINDOW_SECONDS", DEFAULT_BURST_WINDOW_SECONDS),
}


class BudgetUnavailable(RuntimeError):
    """The budget cannot be trusted, so the billed call is refused."""


class BudgetExceeded(RuntimeError):
    def __init__(self, reason: str, retry_after_seconds: int):
        super().__init__(reason)
        self.reason = reason
        self.retry_after_seconds = max(1, int(retry_after_seconds))


@dataclass(frozen=True)
class BudgetConfig:
    daily_limit: int = DEFAULT_DAILY_LIMIT
    max_in_flight: int = DEFAULT_MAX_IN_FLIGHT
    burst_limit: int = DEFAULT_BURST_LIMIT
    burst_window_seconds: int = DEFAULT_BURST_WINDOW_SECONDS

    def __post_init__(self):
        for name in ("daily_limit", "max_in_flight", "burst_limit", "burst_window_seconds"):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= 1_000_000:
                raise ValueError(f"{name} must be a positive finite integer")

    @classmethod
    def from_environment(cls, environ=os.environ) -> BudgetConfig:
        values = {}
        for name, (variable, default) in ENVIRONMENT.items():
            raw = environ.get(variable)
            if raw is None or raw == "":
                values[name] = default
                continue
            if not raw.strip().isdigit():
                raise ValueError(f"{variable} must be a positive integer")
            values[name] = int(raw.strip())
        return cls(**values)


class Lease:
    """One admitted billed request's concurrency slot. Release is idempotent."""

    def __init__(self, release: Callable[[], None], route: str, day: str):
        self._release = release
        self._released = False
        self._lock = threading.Lock()
        self.route = route
        self.day = day

    @property
    def released(self) -> bool:
        return self._released

    def release(self) -> None:
        with self._lock:
            if self._released:
                return
            self._released = True
        self._release()

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.release()


def _utc_day(now: float) -> str:
    return datetime.fromtimestamp(now, UTC).strftime("%Y-%m-%d")


def seconds_until_utc_midnight(now: float) -> int:
    current = datetime.fromtimestamp(now, UTC)
    tomorrow = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(1, math.ceil((tomorrow - current).total_seconds()))


class RequestBudget:
    def __init__(self, path: Path | None, config: BudgetConfig | None = None, *,
                 clock: Callable[[], float] = time.time, monotonic: Callable[[], float] = time.monotonic,
                 config_error: str | None = None):
        self.path = Path(path) if path is not None else None
        self.config = config
        self.config_error = config_error if config is not None or config_error else "budget not configured"
        self.clock = clock
        self.monotonic = monotonic
        self._lock = threading.Lock()
        self._in_flight = 0
        self._recent: deque[float] = deque()

    @classmethod
    def from_environment(cls, default_path: Path, environ=os.environ) -> RequestBudget:
        """Build from environment; an invalid value refuses billed calls instead of guessing."""
        path = Path(environ.get("OHMNI_AI_BUDGET_PATH") or default_path)
        try:
            return cls(path, BudgetConfig.from_environment(environ))
        except ValueError as error:
            return cls(path, None, config_error=str(error))

    # -- durable daily counter -------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        if self.path is None:
            raise BudgetUnavailable("no budget storage")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Concurrent first connections can return SQLITE_BUSY while switching
        # to WAL without waiting for SQLite's busy timeout. Retry only this
        # idempotent setup, never an admission whose COMMIT might have succeeded.
        # Use real elapsed time: the admission clock may be frozen in tests.
        deadline = time.monotonic() + 5
        while True:
            connection = None
            try:
                connection = sqlite3.connect(
                    self.path, timeout=max(0, deadline - time.monotonic()), isolation_level=None)
                for sql in (
                    "PRAGMA journal_mode=WAL",
                    "PRAGMA synchronous=FULL",
                    ("CREATE TABLE IF NOT EXISTS ai_daily_requests ("
                     " day TEXT PRIMARY KEY, admitted INTEGER NOT NULL CHECK (admitted >= 0))"),
                ):
                    remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))
                    connection.execute(f"PRAGMA busy_timeout={remaining_ms}")
                    connection.execute(sql)
                # The counter transaction keeps its original five-second wait.
                connection.execute("PRAGMA busy_timeout=5000")
                return connection
            except BaseException as error:
                if connection is not None:
                    connection.close()
                remaining = deadline - time.monotonic()
                if (not isinstance(error, sqlite3.OperationalError)
                        or getattr(error, "sqlite_errorcode", 0) & 0xff != sqlite3.SQLITE_BUSY
                        or remaining <= 0):
                    raise
                time.sleep(min(0.01, remaining))

    def _increment(self, day: str, limit: int) -> bool:
        """Atomically admit one request for ``day``; False when the limit is reached."""
        try:
            connection = self._connect()
        except (OSError, sqlite3.Error) as error:
            raise BudgetUnavailable("budget storage unavailable") from error
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT admitted FROM ai_daily_requests WHERE day = ?", (day,)).fetchone()
            admitted = 0 if row is None else row[0]
            if type(admitted) is not int or admitted < 0:
                connection.execute("ROLLBACK")
                raise BudgetUnavailable("budget storage is corrupt")
            if admitted >= limit:
                connection.execute("ROLLBACK")
                return False
            connection.execute(
                "INSERT INTO ai_daily_requests (day, admitted) VALUES (?, 1) "
                "ON CONFLICT(day) DO UPDATE SET admitted = admitted + 1", (day,))
            connection.execute("COMMIT")
            return True
        except sqlite3.Error as error:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise BudgetUnavailable("budget storage unavailable") from error
        finally:
            connection.close()

    def admitted_today(self) -> int:
        try:
            connection = self._connect()
            try:
                row = connection.execute("SELECT admitted FROM ai_daily_requests WHERE day = ?",
                                         (_utc_day(self.clock()),)).fetchone()
            finally:
                connection.close()
        except (OSError, sqlite3.Error) as error:
            raise BudgetUnavailable("budget storage unavailable") from error
        return 0 if row is None else int(row[0])

    # -- admission ---------------------------------------------------------------
    def admit(self, route: str) -> Lease:
        """Admit one billed request or raise. The caller must release the lease
        after its provider work ends, on every path; the daily count is kept."""
        if route not in BILLED_ROUTES:
            raise ValueError(f"unknown billed route {route!r}")
        config = self.config
        if config is None:
            raise BudgetUnavailable(self.config_error or "budget not configured")
        now = self.monotonic()
        with self._lock:
            while self._recent and self._recent[0] <= now - config.burst_window_seconds:
                self._recent.popleft()
            if self._in_flight >= config.max_in_flight:
                raise BudgetExceeded("concurrency", CONCURRENCY_RETRY_AFTER_SECONDS)
            if len(self._recent) >= config.burst_limit:
                wait = self._recent[0] + config.burst_window_seconds - now
                raise BudgetExceeded("burst", math.ceil(wait))
            wall = self.clock()
            day = _utc_day(wall)
            # Durable admission happens inside the in-memory lock so concurrent
            # admissions in this process cannot over-commit the slot counts; the
            # SQLite transaction serialises against other processes too.
            if not self._increment(day, config.daily_limit):
                raise BudgetExceeded("daily", seconds_until_utc_midnight(wall))
            self._in_flight += 1
            self._recent.append(now)
        return Lease(self._release_slot, route, day)

    def _release_slot(self) -> None:
        with self._lock:
            self._in_flight = max(0, self._in_flight - 1)

    @property
    def in_flight(self) -> int:
        with self._lock:
            return self._in_flight

    def describe(self) -> dict[str, object]:
        """Operator view: limits and today's count (never exposed over HTTP)."""
        config = self.config
        return {
            "configured": config is not None,
            "config_error": None if config is not None else self.config_error,
            "path": str(self.path) if self.path else None,
            "daily_limit": config.daily_limit if config else None,
            "max_in_flight": config.max_in_flight if config else None,
            "burst_limit": config.burst_limit if config else None,
            "burst_window_seconds": config.burst_window_seconds if config else None,
            "utc_day": _utc_day(self.clock()),
        }


def reset_day(path: Path, day: str) -> int:
    """Local operator reset of one UTC day's count; returns the removed count."""
    datetime.strptime(day, "%Y-%m-%d")
    budget = RequestBudget(path, BudgetConfig())
    try:
        connection = budget._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT admitted FROM ai_daily_requests WHERE day = ?", (day,)).fetchone()
            connection.execute("DELETE FROM ai_daily_requests WHERE day = ?", (day,))
            connection.execute("COMMIT")
        finally:
            connection.close()
    except (OSError, sqlite3.Error) as error:
        raise BudgetUnavailable("budget storage unavailable") from error
    return 0 if row is None else int(row[0])
