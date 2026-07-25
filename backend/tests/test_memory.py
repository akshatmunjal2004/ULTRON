def test_memory_crud_round_trip(client):
    created = client.put(
        "/api/v1/memory", json={"key": "Deadline", "value": "Friday"}
    )
    assert created.status_code == 200
    assert created.json()["value"] == "Friday"

    # Keys are case-insensitive, so this updates rather than duplicating.
    client.put("/api/v1/memory", json={"key": "deadline", "value": "Monday"})

    listed = client.get("/api/v1/memory").json()
    assert listed["total"] == 1
    assert listed["items"][0]["value"] == "Monday"

    fetched = client.get("/api/v1/memory/DEADLINE")
    assert fetched.status_code == 200

    deleted = client.delete("/api/v1/memory/deadline")
    assert deleted.status_code == 200
    assert client.get("/api/v1/memory/deadline").status_code == 404


def test_missing_key_returns_structured_error(client):
    res = client.get("/api/v1/memory/nope")
    assert res.status_code == 404
    body = res.json()
    assert body["error"]["code"] == "not_found"
    assert "request_id" in body


def test_blank_value_is_rejected(client):
    res = client.put("/api/v1/memory", json={"key": "x", "value": "   "})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_failed"


def test_like_wildcards_do_not_match_everything(client):
    client.put("/api/v1/memory", json={"key": "alpha", "value": "one"})
    client.put("/api/v1/memory", json={"key": "beta", "value": "two"})
    res = client.get("/api/v1/memory", params={"q": "%"}).json()
    assert res["items"] == []
