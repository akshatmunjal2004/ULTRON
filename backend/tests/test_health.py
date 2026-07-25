def test_health_reports_online(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "online"
    assert body["environment"] == "test"


def test_ready_lists_enabled_tools(client):
    res = client.get("/api/v1/ready")
    assert res.status_code == 200
    body = res.json()
    assert body["database"] is True
    assert "memory_tool" in body["tools_enabled"]


def test_legacy_health_redirects(client):
    res = client.get("/health", follow_redirects=False)
    assert res.status_code == 308
    assert res.headers["location"].endswith("/api/v1/health")


def test_every_response_carries_a_request_id(client):
    res = client.get("/api/v1/health")
    assert res.headers.get("X-Request-ID")
