from fastapi.testclient import TestClient

from app.agents.llm import LLMConfigError
from app.api import chat
from app.main import app

client = TestClient(app)


def test_misconfigured_provider_returns_503_with_reason(monkeypatch):
    def unconfigured():
        raise LLMConfigError("LLM_API_KEY is not set (LLM_PROVIDER=gemini).")

    monkeypatch.setattr(chat, "get_provider", unconfigured)

    response = client.post("/api/chat/stream", json={"message": "hi"})

    assert response.status_code == 503
    assert "LLM_API_KEY" in response.json()["detail"]


def test_streams_tokens_from_the_agent(monkeypatch):
    monkeypatch.setattr(chat, "get_provider", lambda: object())
    monkeypatch.setattr(chat, "stream_agent_reply", lambda db, messages, provider: iter(["Hel", "lo"]))

    response = client.post(
        "/api/chat/stream",
        json={"message": "hi", "history": [{"role": "assistant", "content": "earlier"}]},
    )

    assert response.status_code == 200
    assert response.text == "Hello"


def test_mid_stream_failure_becomes_a_readable_message(monkeypatch):
    def failing(db, messages, provider):
        yield "partial "
        raise RuntimeError("429 rate limited")

    monkeypatch.setattr(chat, "get_provider", lambda: object())
    monkeypatch.setattr(chat, "stream_agent_reply", failing)

    response = client.post("/api/chat/stream", json={"message": "hi"})

    assert response.status_code == 200
    assert response.text.startswith("partial ")
    assert "model request failed" in response.text
