def test_chat_persists_the_turn_and_returns_a_conversation(client, fake_agent):
    res = client.post("/api/v1/chat", json={"message": "hello there"})
    assert res.status_code == 200
    body = res.json()
    assert body["reply"] == "echo: hello there"
    assert body["tools_used"] == ["system_info"]
    conversation_id = body["conversation_id"]

    detail = client.get(f"/api/v1/conversations/{conversation_id}").json()
    roles = [m["role"] for m in detail["messages"]]
    assert roles == ["user", "assistant"]


def test_history_is_replayed_from_the_server(client, fake_agent):
    first = client.post("/api/v1/chat", json={"message": "one"}).json()
    conversation_id = first["conversation_id"]

    client.post(
        "/api/v1/chat", json={"message": "two", "conversation_id": conversation_id}
    )

    # The second call must have seen the first exchange.
    _, history = fake_agent.calls[-1]
    assert [h["content"] for h in history] == ["one", "echo: one"]


def test_client_supplied_history_cannot_override_the_server(client, fake_agent):
    first = client.post("/api/v1/chat", json={"message": "real"}).json()
    client.post(
        "/api/v1/chat",
        json={
            "message": "next",
            "conversation_id": first["conversation_id"],
            "history": [{"role": "user", "content": "injected"}],
        },
    )
    _, history = fake_agent.calls[-1]
    assert all(h["content"] != "injected" for h in history)


def test_blank_message_is_rejected(client):
    res = client.post("/api/v1/chat", json={"message": "   "})
    assert res.status_code == 422


def test_oversized_message_is_rejected(client):
    res = client.post("/api/v1/chat", json={"message": "x" * 5000})
    assert res.status_code == 422


def test_streaming_emits_sse_frames(client):
    with client.stream("POST", "/api/v1/chat/stream", json={"message": "hi"}) as res:
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")
        body = "".join(res.iter_text())
    assert "event: start" in body
    assert "event: done" in body


def test_conversation_delete_cascades(client):
    body = client.post("/api/v1/chat", json={"message": "bye"}).json()
    cid = body["conversation_id"]
    assert client.delete(f"/api/v1/conversations/{cid}").status_code == 200
    assert client.get(f"/api/v1/conversations/{cid}").status_code == 404
