"""Pydantic schemas for task creation and response."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, model_validator


class StyleEnum(str, Enum):
    formal = "formal"
    sarcastic = "sarcastic"
    humorous_tech = "humorous_tech"
    humorous_non_tech = "humorous_non_tech"


class TaskCreate(BaseModel):
    video_url: HttpUrl = Field(
        ...,
        description="Public URL of the video to caption",
        examples=["https://example.com/videos/demo.mp4"],
    )
    styles: list[StyleEnum] = Field(
        default_factory=lambda: list(StyleEnum),
        description="Caption styles to generate",
    )

    @model_validator(mode="after")
    def ensure_at_least_one_style(self) -> "TaskCreate":
        if not self.styles:
            self.styles = list(StyleEnum)
        return self


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskResponse(BaseModel):
    task_id: uuid.UUID = Field(..., description="Unique task identifier")
    status: TaskStatus = Field(..., description="Current task status")
    result: dict[str, Any] | None = Field(
        None,
        description="Generated captions and metadata (only when status=COMPLETED)",
    )
    error_message: str | None = Field(
        None,
        description="Error details (only when status=FAILED)",
    )
    created_at: datetime | None = Field(None, description="Task creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    model_config = {"from_attributes": True}
