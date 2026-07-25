"""SQLite connection management.

sqlite3 connections are not shareable across threads, and FastAPI runs sync
endpoints in a worker thread pool, so a connection is opened per unit of work
and closed at the end of it. WAL plus a busy timeout is what keeps concurrent
readers from tripping over the writer.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_PRAGMAS = (
    "PRAGMA journal_mode = WAL",
    "PRAGMA foreign_keys = ON",
    "PRAGMA synchronous = NORMAL",
    "PRAGMA busy_timeout = 5000",
)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(settings.DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    for pragma in _PRAGMAS:
        conn.execute(pragma)
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Transactional scope. Commits on success, rolls back on failure."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency wrapping get_conn()."""
    with get_conn() as conn:
        yield conn


def healthcheck() -> bool:
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Database healthcheck failed: %s", exc)
        return False
