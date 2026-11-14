"""Health check — used by the UI's status indicator."""

from fastapi import APIRouter

from app.api.schemas import HealthResponse
from app.core.config import get_settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health():
    settings = get_settings()
    return HealthResponse(
        status="ok",
        api_key_configured=bool(settings.openai_api_key),
        chat_model=settings.chat_model,
        embedding_model=settings.embedding_model,
    )
