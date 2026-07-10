"""SQLAlchemy Task model for caption generation jobs."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID

from backend.models.database import Base


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    status = Column(
        Enum(TaskStatus, name="task_status", create_type=True),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True,
    )
    video_url = Column(String(2048), nullable=False)
    styles = Column(JSON, nullable=False, default=list)
    result_json = Column(JSON, nullable=True, default=None)
    error_message = Column(Text, nullable=True, default=None)
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, status={self.status})>"
