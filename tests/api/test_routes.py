"""HTTP-level tests using FastAPI's TestClient (no real server, no LLM)."""

import json

from langchain_core.messages import AIMessage


def test_index_and_static_are_served(client):
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert "api_key_configured" in body


def test_empty_message_rejected(client):
    r = client.post("/api/chat", data={"message": "  ", "session_id": "s"})
    assert r.status_code == 400


def test_non_image_upload_rejected(client):
    r = client.post(
        "/api/chat",
        data={"message": "hi", "session_id": "s"},
        files={"image": ("notes.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 415


def test_chat_json(client, fake_llm):
    fake_llm([AIMessage(content='{"intent": "policy_qa"}'), AIMessage(content="Yes, with Comprehensive.")])
    r = client.post("/api/chat", data={"message": "Is flood covered?", "session_id": "api-1"})
    assert r.status_code == 200
    assert r.json()["reply"] == "Yes, with Comprehensive."
    assert r.json()["agent"] == "policy_qa"


def test_chat_stream_sse(client, fake_llm):
    fake_llm([AIMessage(content='{"intent": "policy_qa"}'), AIMessage(content="Hello!")])
    r = client.post("/api/chat/stream", data={"message": "hi", "session_id": "api-2"})
    events = [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith("data: ")]
    assert [e["type"] for e in events] == ["route", "final"]


def test_delete_session(client):
    assert client.delete("/api/session/whatever").json() == {"ok": True}
