"""Caption generation API endpoint."""

import time
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from backend.config import get_settings
from backend.models.schemas import CaptionResponse
from backend.utils.validators import validate_video_file, validate_file_size, validate_styles
from backend.services.fireworks_service import generate_captions

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/caption", response_model=CaptionResponse)
async def create_caption(
    video: UploadFile = File(..., description="Video file to caption"),
    styles: str = Form(
        default="formal,sarcastic,humorous_tech,humorous_non_tech",
        description="Comma-separated list of caption styles",
    ),
):
    """
    Generate styled captions for an uploaded video.

    Accepts a video file and optional style selection.
    Returns captions in each requested style along with a factual video summary.
    """
    settings = get_settings()

    # Validate API key is configured
    if not settings.fireworks_api_key or settings.fireworks_api_key == "your_fireworks_api_key_here":
        raise HTTPException(
            status_code=500,
            detail="Fireworks API key not configured. Please set FIREWORKS_API_KEY in your .env file.",
        )

    # Validate file type
    validate_video_file(
        video,
        settings.allowed_extensions_list,
        settings.max_video_size_bytes,
    )

    # Validate styles
    style_list = validate_styles(styles)

    # Read file bytes
    video_bytes = await video.read()

    # Validate file size
    validate_file_size(video_bytes, settings.max_video_size_bytes)

    logger.info(
        "Processing video: %s (%.1f MB), styles: %s",
        video.filename,
        len(video_bytes) / (1024 * 1024),
        style_list,
    )

    # Generate captions
    start_time = time.time()

    try:
        results = generate_captions(video_bytes, video.filename or "video.mp4", style_list)
    except Exception as e:
        logger.error("Caption generation failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail=f"AI service error: {str(e)}",
        )

    elapsed = time.time() - start_time
    logger.info("Captions generated in %.1f seconds.", elapsed)

    return CaptionResponse(
        formal=results.get("formal"),
        sarcastic=results.get("sarcastic"),
        humorous_tech=results.get("humorous_tech"),
        humorous_non_tech=results.get("humorous_non_tech"),
        video_summary=results.get("video_summary", ""),
        model_used=settings.fireworks_model,
        processing_time_seconds=round(elapsed, 2),
    )
