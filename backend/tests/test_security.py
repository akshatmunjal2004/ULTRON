import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import create_app
from app.middleware.rate_limit import RateLimitMiddleware
from app.services.agent_service import get_agent_service


@pytest.fixture()
def secured_client(fake_agent, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "s3cret")
    app = create_app()
    app.dependency_overrides[get_agent_service] = lambda: fake_agent
    with TestClient(app) as client:
        yield client


def test_write_routes_require_the_key(secured_client):
    res = secured_client.put("/api/v1/memory", json={"key": "a", "value": "b"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "unauthorized"


def test_correct_key_is_accepted(secured_client):
    res = secured_client.put(
        "/api/v1/memory",
        json={"key": "a", "value": "b"},
        headers={"X-API-Key": "s3cret"},
    )
    assert res.status_code == 200


def test_reads_stay_open(secured_client):
    assert secured_client.get("/api/v1/memory").status_code == 200


def test_tool_execution_is_protected(secured_client):
    res = secured_client.post(
        "/api/v1/tools/execute", json={"tool": "code_runner", "args": {"code": "x"}}
    )
    assert res.status_code == 401


def test_rate_limiter_returns_429(fake_agent):
    app = create_app()
    app.user_middleware = [
        m for m in app.user_middleware if m.cls is not RateLimitMiddleware
    ]
    app.add_middleware(RateLimitMiddleware, limit=3, window=60)
    app.dependency_overrides[get_agent_service] = lambda: fake_agent
    with TestClient(app) as client:
        codes = [client.get("/api/v1/memory").status_code for _ in range(6)]
    assert 429 in codes
    assert codes[0] == 200


def test_production_config_rejects_wildcard_cors(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "production")
    monkeypatch.setattr(settings, "CORS_ORIGINS", "*")
    monkeypatch.setattr(settings, "API_KEY", "")
    problems = settings.check_runtime_requirements()
    assert any("CORS_ORIGINS" in p for p in problems)
    assert any("API_KEY" in p for p in problems)
