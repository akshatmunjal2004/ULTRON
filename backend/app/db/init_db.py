"""Schema bootstrap. Safe to run on every startup."""

from __future__ import annotations

from pathlib import Path

from app.core.logging import get_logger
from app.db.session import get_conn

logger = get_logger(__name__)

SCHEMA_FILE = Path(__file__).with_name("schema.sql")


def init_db() -> None:
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    with get_conn() as conn:
        conn.executescript(sql)
    logger.info("Database ready at %s", SCHEMA_FILE.parent)
