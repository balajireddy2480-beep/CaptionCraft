"""Async SQLAlchemy database engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.core.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_async_session_factory = None


async def init_db() -> None:
    """Initialize the database engine and session factory."""
    global _engine, _async_session_factory
    if _engine is not None:
        return
    settings = get_settings()
    _engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )
    _async_session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    # Import models to register them on Base metadata and prevent circular imports
    from backend.models.task import Task  # noqa: F401
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose of the database engine."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session (FastAPI dependency)."""
    if _async_session_factory is None:
        await init_db()
    async with _async_session_factory() as session:  # type: ignore[union-attr]
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncSession:
    """Get a standalone DB session (for worker use outside FastAPI)."""
    if _async_session_factory is None:
        await init_db()
    return _async_session_factory()  # type: ignore[union-attr]
