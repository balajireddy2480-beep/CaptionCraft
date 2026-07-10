"""FastAPI application entry point — Video Captioning Agent API v1."""

import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

# pyrefly: ignore [missing-import]
import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
# pyrefly: ignore [missing-import]
from slowapi import Limiter, _rate_limit_exceeded_handler
# pyrefly: ignore [missing-import]
from slowapi.errors import RateLimitExceeded
# pyrefly: ignore [missing-import]
from slowapi.middleware import SlowAPIMiddleware
# pyrefly: ignore [missing-import]
from slowapi.util import get_remote_address

from backend.core.config import get_settings
from backend.core.logging import configure_logging, get_logger
from backend.core.deps import get_rate_limit_key
from backend.models.database import close_db, init_db
from backend.routers.v1_tasks import router as tasks_router
from backend.schemas.health import HealthResponse

# Configure structured logging
configure_logging()
logger = get_logger(__name__)


# =============================================================================
# Rate Limiter (slowapi + Redis)
# =============================================================================

class RedisLimiter(Limiter):
    """Limiter that uses the X-API-Key header for rate limit keying."""

    async def get_identifier(self, request: Request) -> str:
        return await get_rate_limit_key(request)


_settings = get_settings()
rate_limiter = RedisLimiter(key_func=get_remote_address, storage_uri=_settings.redis_url)


# =============================================================================
# App Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle: startup and shutdown."""
    settings = get_settings()
    logger.info("Video Captioning API starting up", model=settings.fireworks_model)

    # Validate required config
    _validate_env(settings)

    # Initialize database
    await init_db()
    logger.info("Database connection pool initialized.")

    yield

    # Shutdown
    await close_db()
    logger.info("Database connection pool closed.")
    logger.info("Video Captioning API shutting down.")


def _validate_env(settings) -> None:
    """Crash on startup if critical env vars are missing or invalid."""
    errors = []
    if not settings.fireworks_api_key or settings.fireworks_api_key == "your_fireworks_api_key_here":
        errors.append("FIREWORKS_API_KEY is missing or still set to default.")
    if not settings.allowed_api_keys or settings.allowed_api_keys == "":
        errors.append("ALLOWED_API_KEYS is empty. Configure at least one API key.")
    if errors:
        for err in errors:
            logger.error("Env validation failed: %s", err)
            print(f"FATAL: {err}", file=sys.stderr)
        sys.exit(1)


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Video Captioning Agent API",
    description="AI-powered video captioning in 4 stylistic voices. "
    "Submit a video URL via POST /v1/tasks and poll for results.",
    version="2.0.0",
    lifespan=lifespan,
)

# Rate limiter exception handler
app.state.limiter = rate_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware (must be after CORS)
app.add_middleware(SlowAPIMiddleware)


# =============================================================================
# Routes
# =============================================================================

app.include_router(tasks_router)

_health_limit = "10/minute"


@app.get("/health", response_model=HealthResponse, tags=["Health"])
@rate_limiter.limit(_health_limit)
async def health_check(request: Request) -> HealthResponse:
    """Check API, database, and Redis connectivity."""
    db_status = "unknown"
    redis_status = "unknown"

    settings = get_settings()

    # Check DB
    try:
        # pyrefly: ignore [missing-import]
        from sqlalchemy import text
        from backend.models.database import get_db_session

        session = await get_db_session()
        await session.execute(text("SELECT 1"))
        await session.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    # Check Redis
    try:
        redis = aioredis.from_url(
            settings.redis_url,
            socket_connect_timeout=3,
        )
        await redis.ping()
        await redis.aclose()
        redis_status = "connected"
    except Exception as e:
        redis_status = f"error: {e}"

    overall = "healthy" if db_status == "connected" and redis_status == "connected" else "degraded"

    return HealthResponse(
        status=overall,
        database=db_status,
        redis=redis_status,
    )


# =============================================================================
# Static Frontend (Production)
# =============================================================================

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    logger.info(
        "Serving frontend from %s. "
        "Note: Old /api/caption endpoint removed. "
        "Frontend must use /v1/tasks with JSON body.",
        frontend_dist,
    )


# =============================================================================
# Shutdown hook for Celery worker (prevents asyncio loop issues)
# =============================================================================
@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Application shutdown event received.")
