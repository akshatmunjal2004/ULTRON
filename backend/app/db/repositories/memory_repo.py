"""Data access for the `memory` table.

Endpoints and tools call these functions; neither writes SQL of its own. Every
statement is parameterised, and LIKE wildcards in user input are escaped so a
search for "50%" doesn't match everything.
"""

from __future__ import annotations

import sqlite3
from typing import Any

_LIKE_ESCAPE = "\\"


def _escape_like(term: str) -> str:
    out = term.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2)
    for ch in ("%", "_"):
        out = out.replace(ch, _LIKE_ESCAPE + ch)
    return out


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "key": row["key"],
        "value": row["value"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def upsert(conn: sqlite3.Connection, key: str, value: str) -> dict[str, Any]:
    key = key.strip()
    value = value.strip()
    conn.execute(
        """
        INSERT INTO memory (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE
            SET value = excluded.value, updated_at = datetime('now')
        """,
        (key, value),
    )
    row = conn.execute(
        "SELECT * FROM memory WHERE key = ? COLLATE NOCASE", (key,)
    ).fetchone()
    return _row_to_dict(row)


def get_by_key(conn: sqlite3.Connection, key: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM memory WHERE key = ? COLLATE NOCASE", (key.strip(),)
    ).fetchone()
    return _row_to_dict(row) if row else None


def search(conn: sqlite3.Connection, term: str, limit: int = 10) -> list[dict[str, Any]]:
    pattern = f"%{_escape_like(term.strip())}%"
    rows = conn.execute(
        """
        SELECT * FROM memory
        WHERE key LIKE ? ESCAPE ? OR value LIKE ? ESCAPE ?
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (pattern, _LIKE_ESCAPE, pattern, _LIKE_ESCAPE, limit),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def list_all(
    conn: sqlite3.Connection, limit: int = 50, offset: int = 0
) -> tuple[list[dict[str, Any]], int]:
    rows = conn.execute(
        "SELECT * FROM memory ORDER BY updated_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) AS c FROM memory").fetchone()["c"]
    return [_row_to_dict(r) for r in rows], total


def delete(conn: sqlite3.Connection, key: str) -> bool:
    cur = conn.execute("DELETE FROM memory WHERE key = ? COLLATE NOCASE", (key.strip(),))
    return cur.rowcount > 0


def clear(conn: sqlite3.Connection) -> int:
    cur = conn.execute("DELETE FROM memory")
    return cur.rowcount
