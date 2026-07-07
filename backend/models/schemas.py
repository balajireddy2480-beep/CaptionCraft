"""Pydantic models for API request and response schemas."""

from pydantic import BaseModel


class CaptionResponse(BaseModel):
    """Response model for the caption generation endpoint."""

    formal: str | None = None
    sarcastic: str | None = None
    humorous_tech: str | None = None
    humorous_non_tech: str | None = None
    video_summary: str = ""
    model_used: str = ""
    processing_time_seconds: float = 0.0


class HealthResponse(BaseModel):
    """Response model for the health check endpoint."""

    status: str = "healthy"
    model: str = ""
