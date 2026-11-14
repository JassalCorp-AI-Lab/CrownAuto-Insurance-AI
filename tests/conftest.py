"""Shared test fixtures.

`fake_llm` replaces the real OpenAI models with a scripted fake, so the whole
graph (supervisor → agents → tools) can be tested offline and for free.
"""

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage


class FakeChatModel:
    """Returns pre-scripted AIMessages in order, one per invoke() call."""

    def __init__(self, replies: list[AIMessage]):
        self.replies = list(replies)
        self.calls = 0

    def bind_tools(self, _tools):
        return self

    def invoke(self, _messages):
        self.calls += 1
        if not self.replies:
            raise AssertionError("FakeChatModel ran out of scripted replies")
        return self.replies.pop(0)


def tool_call(name: str, args: dict, call_id: str = "call_1") -> AIMessage:
    """An AI message that asks to run one tool."""
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


@pytest.fixture(autouse=True)
def no_real_api_key(monkeypatch):
    """Tests must never call OpenAI, even if your .env has a real key.
    (Environment variables take priority over .env in pydantic-settings.)"""
    from app.core.config import get_settings
    from app.llm import factory

    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    factory.get_chat_model.cache_clear()
    factory.get_embeddings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def fake_llm(monkeypatch):
    """Usage: model = fake_llm([...replies...], vision=[...replies...])"""

    def install(replies, vision=None):
        chat_model = FakeChatModel(replies)
        vision_model = FakeChatModel(vision or [])
        pick = lambda role: vision_model if role == "vision" else chat_model  # noqa: E731
        for module in ("app.agents.supervisor", "app.agents.specialists", "app.tools.claims_tools"):
            monkeypatch.setattr(f"{module}.get_chat_model", pick)
        return chat_model

    return install


@pytest.fixture
def client():
    from app.main import create_app

    with TestClient(create_app()) as test_client:  # `with` runs the startup lifespan
        yield test_client
