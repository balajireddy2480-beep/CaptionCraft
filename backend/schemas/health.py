"""Pydantic schemas for health check endpoint."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field("healthy", description="Overall service status")
    database: str = Field("unknown", description="Database connectivity status")
    redis: str = Field("unknown", description="Redis connectivity status")
