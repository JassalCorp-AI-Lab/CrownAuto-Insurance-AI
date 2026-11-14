"""Application settings, read from environment variables or the .env file.

Usage:
    from app.core.config import get_settings
    settings = get_settings()
"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    # ─── OpenAI ───────────────────────────────────────────────────────
    openai_api_key: str | None = None
    chat_model: str = "gpt-6-luna"
    vision_model: str = "gpt-6-luna"
    embedding_model: str = "text-embedding-3-small"

    # Reasoning effort per role. None = don't send the parameter
    # (needed for non-reasoning models such as gpt-4o-mini).
    # gpt-6-luna on Chat Completions only allows tool calling with "none".
    router_reasoning_effort: str | None = "low"
    vision_reasoning_effort: str | None = "low"
    agent_reasoning_effort: str | None = "none"

    # ─── App ──────────────────────────────────────────────────────────
    chroma_dir: Path = ROOT_DIR / "data" / "chroma"
    graph_recursion_limit: int = 25
    max_image_mb: float = 8

    @field_validator("openai_api_key", "router_reasoning_effort",
                     "vision_reasoning_effort", "agent_reasoning_effort", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        """Treat `KEY=` (empty) in .env as 'not set'."""
        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    """Settings are loaded once and reused (cached)."""
    return Settings()
