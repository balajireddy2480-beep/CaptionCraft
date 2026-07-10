"""Application configuration loaded from environment variables."""

import sys
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Required: API Keys & Secrets ---
    fireworks_api_key: str = ""
    allowed_api_keys: str = "dev-key-123"
    secret_key: str = "change-me-to-a-random-64-char-string"

    # --- Required: Infrastructure ---
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/video_captioning"
    redis_url: str = "redis://localhost:6379/0"

    # --- Optional: Video Processing ---
    whisper_model: str = "base"
    max_video_size_mb: int = 200
    temp_dir: str = "/tmp/video_captions"

    # --- Optional: Rate Limiting ---
    rate_limit_per_hour: int = 100

    # --- Optional: Fireworks AI ---
    fireworks_model: str = "accounts/fireworks/models/qwen3p7-plus"
    fireworks_max_tokens: int = 600

    @field_validator("fireworks_api_key")
    @classmethod
    def validate_fireworks_api_key(cls, v: str) -> str:
        if not v or v == "your_fireworks_api_key_here":
            print(
                "FATAL: Missing required env var: FIREWORKS_API_KEY. "
                "Set it in your .env file.",
                file=sys.stderr,
            )
            sys.exit(1)
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            print(
                "FATAL: Missing required env var: DATABASE_URL. "
                "Set it in your .env file.",
                file=sys.stderr,
            )
            sys.exit(1)
        return v

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        if not v:
            print(
                "FATAL: Missing required env var: REDIS_URL. "
                "Set it in your .env file.",
                file=sys.stderr,
            )
            sys.exit(1)
        return v

    @property
    def max_video_size_bytes(self) -> int:
        return self.max_video_size_mb * 1024 * 1024

    @property
    def allowed_api_keys_list(self) -> List[str]:
        return [k.strip() for k in self.allowed_api_keys.split(",") if k.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
