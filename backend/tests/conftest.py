"""Test fixtures.

Every test gets a throwaway database and workspace, and the Groq client is never
reached: agent tests override the AgentService dependency with a fake.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

TMP = Path(tempfile.mkdtemp(prefix="ultron-tests-"))
os.environ.update(
    {
        "ENV": "test",
        "GROQ_API_KEY": "test-key-not-used",
        "DB_PATH": str(TMP / "test.db"),
        "WORKSPACE_DIR": str(TMP / "workspace"),
        "API_KEY": "",
        "RATE_LIMIT_REQUESTS": "10000",
        "ENABLE_CODE_EXECUTION": "true",
        "LOG_LEVEL": "WARNING",
    }
)

from fastapi.testclient import TestClient  # noqa: E402

from app.api.deps import Agent  # noqa: E402,F401
from app.core.config import settings  # noqa: E402
from app.db.init_db import init_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.agent_service import (  # noqa: E402
    AgentResult,
    ToolCallRecord,
    get_agent_service,
)


class FakeAgent:
    """Stands in for the real agent so tests never call Groq."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list | None]] = []

    def run(self, message: str, history=None) -> AgentResult:
        self.calls.append((message, history))
        return AgentResult(
            reply=f"echo: {message}",
            tool_calls=[
                ToolCallRecord(
                    name="system_info",
                    arguments={},
                    result="ok",
                    ok=True,
                    duration_ms=1,
                )
            ],
            model="test-model",
        )

    def stream(self, message: str, history=None):
        yield {"event": "status", "data": {"state": "answering"}}
        yield {"event": "token", "data": {"text": "hi"}}
        yield {"event": "done", "data": {"reply": "hi", "tools_used": [], "model": "test"}}


@pytest.fixture(scope="session", autouse=True)
def _prepare() -> None:
    settings.prepare_directories()
    init_db()


@pytest.fixture()
def fake_agent() -> FakeAgent:
    return FakeAgent()


@pytest.fixture()
def client(fake_agent: FakeAgent) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_agent_service] = lambda: fake_agent
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _clean_tables() -> Iterator[None]:
    from app.db.session import get_conn

    yield
    with get_conn() as conn:
        conn.execute("DELETE FROM tool_calls")
        conn.execute("DELETE FROM messages")
        conn.execute("DELETE FROM conversations")
        conn.execute("DELETE FROM memory")
