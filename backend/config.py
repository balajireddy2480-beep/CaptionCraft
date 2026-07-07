"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Settings for the Video Captioning backend."""

    fireworks_api_key: str = ""
    fireworks_model: str = "accounts/fireworks/models/qwen3-omni-30b-a3b-instruct"
    max_video_size_mb: int = 25
    allowed_extensions: str = ".mp4,.mov,.avi,.webm,.mkv"

    @property
    def max_video_size_bytes(self) -> int:
        return self.max_video_size_mb * 1024 * 1024

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
