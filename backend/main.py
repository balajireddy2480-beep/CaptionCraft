"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.config import get_settings
from backend.models.schemas import HealthResponse
from backend.routers.caption import router as caption_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    settings = get_settings()
    logger.info("🚀 Video Captioning API starting up")
    logger.info("   Model: %s", settings.fireworks_model)
    logger.info("   Max video size: %d MB", settings.max_video_size_mb)
    api_configured = (
        settings.fireworks_api_key
        and settings.fireworks_api_key != "your_fireworks_api_key_here"
    )
    logger.info("   API key configured: %s", "✅ Yes" if api_configured else "❌ No")
    yield
    logger.info("👋 Video Captioning API shutting down")


app = FastAPI(
    title="Video Captioning Agent",
    description="AI-powered video captioning in 4 stylistic voices",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Vite dev server and common local origins
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

# API routes
app.include_router(caption_router, prefix="/api", tags=["Captions"])


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check if the API is running and configured."""
    settings = get_settings()
    return HealthResponse(status="healthy", model=settings.fireworks_model)


# Serve frontend static files in production
# (In dev, Vite dev server handles this via proxy)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    logger.info("📁 Serving frontend from %s", frontend_dist)
