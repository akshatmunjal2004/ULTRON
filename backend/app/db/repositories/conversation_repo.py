"""Data access for conversations, messages and the tool-call audit trail."""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

TITLE_MAX_CHARS = 60


def _new_id() -> str:
    return uuid.uuid4().hex


def create(conn: sqlite3.Connection, title: str = "") -> str:
    conversation_id = _new_id()
    conn.execute(
        "INSERT INTO conversations (id, title) VALUES (?, ?)",
        (conversation_id, (title or "New conversation")[:TITLE_MAX_CHARS]),
    )
    return conversation_id


def exists(conn: sqlite3.Connection, conversation_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
    ).fetchone()
    return row is not None


def ensure(conn: sqlite3.Connection, conversation_id: str | None, seed_title: str) -> str:
    """Return an existing conversation id, or create one titled from the first message."""
    if conversation_id and exists(conn, conversation_id):
        return conversation_id
    return create(conn, seed_title)


def touch(conn: sqlite3.Connection, conversation_id: str) -> None:
    conn.execute(
        "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?",
        (conversation_id,),
    )


def add_message(
    conn: sqlite3.Connection, conversation_id: str, role: str, content: str
) -> int:
    cur = conn.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conversation_id, role, content),
    )
    touch(conn, conversation_id)
    return int(cur.lastrowid)


def add_tool_calls(
    conn: sqlite3.Connection, message_id: int, calls: list[dict[str, Any]]
) -> None:
    if not calls:
        return
    conn.executemany(
        """
        INSERT INTO tool_calls (message_id, tool_name, arguments, result, ok, duration_ms)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                message_id,
                c.get("name", "unknown"),
                json.dumps(c.get("arguments", {}), ensure_ascii=False)[:4000],
                str(c.get("result", ""))[:4000],
                1 if c.get("ok", True) else 0,
                int(c.get("duration_ms", 0)),
            )
            for c in calls
        ],
    )


def recent_messages(
    conn: sqlite3.Connection, conversation_id: str, limit: int
) -> list[dict[str, str]]:
    """Last `limit` turns, oldest first, ready to hand to the LLM."""
    rows = conn.execute(
        """
        SELECT role, content FROM (
            SELECT id, role, content FROM messages
            WHERE conversation_id = ? AND role IN ('user', 'assistant')
            ORDER BY id DESC LIMIT ?
        ) ORDER BY id ASC
        """,
        (conversation_id, limit),
    ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def list_messages(conn: sqlite3.Connection, conversation_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, role, content, created_at FROM messages
        WHERE conversation_id = ? ORDER BY id ASC
        """,
        (conversation_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def list_conversations(
    conn: sqlite3.Connection, limit: int = 20, offset: int = 0
) -> tuple[list[dict[str, Any]], int]:
    rows = conn.execute(
        """
        SELECT c.id, c.title, c.created_at, c.updated_at,
               (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id)
                   AS message_count
        FROM conversations c
        ORDER BY c.updated_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) AS c FROM conversations").fetchone()["c"]
    return [dict(r) for r in rows], total


def delete(conn: sqlite3.Connection, conversation_id: str) -> bool:
    cur = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    return cur.rowcount > 0
