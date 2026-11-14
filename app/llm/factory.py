"""Creates OpenAI clients. Every agent asks for a model by *role*:

    get_chat_model("router")   # supervisor — classifies intent
    get_chat_model("agent")    # quote / claims / policy agents — call tools
    get_chat_model("vision")   # damage-photo analysis

Each role has its own model name and reasoning effort in settings, so you can
tune one role without touching agent code. Clients are cached and reused.
"""

from functools import lru_cache
from typing import Literal

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import get_settings

Role = Literal["router", "agent", "vision"]


class MissingAPIKeyError(RuntimeError):
    """Raised when a model is needed but OPENAI_API_KEY is not configured."""


def _api_key() -> str:
    key = get_settings().openai_api_key
    if not key:
        raise MissingAPIKeyError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return key


@lru_cache
def get_chat_model(role: Role) -> ChatOpenAI:
    settings = get_settings()
    model, effort = {
        "router": (settings.chat_model, settings.router_reasoning_effort),
        "agent": (settings.chat_model, settings.agent_reasoning_effort),
        "vision": (settings.vision_model, settings.vision_reasoning_effort),
    }[role]

    kwargs = {"model": model, "api_key": _api_key()}
    if effort:
        kwargs["reasoning_effort"] = effort
    return ChatOpenAI(**kwargs)


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=get_settings().embedding_model, api_key=_api_key())
