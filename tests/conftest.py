"""Pytest fixtures for Video Captioning API tests."""

import os
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set test env vars BEFORE importing app
os.environ["FIREWORKS_API_KEY"] = "test-fw-key"
os.environ["ALLOWED_API_KEYS"] = "test-api-key-123"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["RATE_LIMIT_PER_HOUR"] = "0"

from backend.core.config import get_settings  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models.database import Base, get_db  # noqa: E402
from backend.models.task import Task, TaskStatus  # noqa: E402

# Use aiosqlite for test DB (no Postgres dependency)
TEST_DB_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh test DB session per test."""
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        # Override the get_db dependency to use test DB
        async def _get_test_db():
            yield session

        app.dependency_overrides[get_db] = _get_test_db
        yield session
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(test_session) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with test DB session injected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-API-Key": "test-api-key-123"},
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def sample_task(test_session: AsyncSession) -> Task:
    """Create a sample completed task in the test DB."""
    task = Task(
        id=uuid.uuid4(),
        video_url="https://example.com/video.mp4",
        styles=["formal", "sarcastic"],
        status=TaskStatus.COMPLETED,
        result_json={
            "formal": "A person demonstrating a software application.",
            "sarcastic": "Wow, groundbreaking stuff.",
            "processing_time_seconds": 2.4,
            "model_used": "accounts/fireworks/models/qwen3p7-plus",
        },
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    test_session.add(task)
    await test_session.commit()
    await test_session.refresh(task)
    return task


@pytest.fixture
def mock_fireworks_success():
    """Mock the Fireworks AI client to return a successful response."""
    with patch(
        "backend.services.fireworks_client.generate_captions",
        return_value={
            "formal": "A person typing on a laptop in a coffee shop.",
            "sarcastic": "Wow, a human doing human things. Amazing.",
            "humorous_tech": "This code compiles on the first try. Clearly fake.",
            "humorous_non_tech": "Me pretending to work while actually planning lunch.",
        },
    ) as mock:
        yield mock


@pytest.fixture
def mock_fireworks_failure():
    """Mock the Fireworks AI client to raise an exception."""
    with patch(
        "backend.services.fireworks_client.generate_captions",
        side_effect=Exception("API quota exceeded"),
    ) as mock:
        yield mock
