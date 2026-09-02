from __future__ import annotations

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    app_name: str = "TrancheAI"
    database_url: str = getenv("DATABASE_URL", "postgresql+psycopg://trancheai:change-me@localhost:5433/trancheai")
    jwt_secret: str = getenv("JWT_SECRET", "change-this-on-server")
    cors_origins: tuple[str, ...] = tuple(origin.strip() for origin in getenv("CORS_ORIGINS", "http://localhost:3100").split(",") if origin.strip())
    ai_enabled: bool = getenv("AI_ENABLED", "false").lower() == "true"
    ai_base_url: str = getenv("AI_BASE_URL", "")
    ai_model: str = getenv("AI_MODEL", "")
    ai_api_key: str = getenv("AI_API_KEY", "")
    ai_timeout_seconds: int = int(getenv("AI_TIMEOUT_SECONDS", "60"))
    ai_max_tokens: int = int(getenv("AI_MAX_TOKENS", "2048"))
    ai_temperature: float = float(getenv("AI_TEMPERATURE", "0.1"))
    stt_enabled: bool = getenv("STT_ENABLED", "false").lower() == "true"
    stt_base_url: str = getenv("STT_BASE_URL", "")
    stt_model: str = getenv("STT_MODEL", "")
    stt_timeout_seconds: int = int(getenv("STT_TIMEOUT_SECONDS", "120"))


settings = Settings()
