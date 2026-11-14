"""Request/response models. FastAPI uses these to validate data and to
generate the interactive docs at /docs."""

from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class ChatInput:
    """A validated chat request (built from the multipart form by forms.py)."""
    message: str
    session_id: str
    image_data_url: str | None = None


class ChatResponse(BaseModel):
    reply: str
    intent: str | None
    agent: str | None
    label: str | None
    tools_used: list[str]


class HealthResponse(BaseModel):
    status: str
    api_key_configured: bool
    chat_model: str
    embedding_model: str


class OkResponse(BaseModel):
    ok: bool = True
