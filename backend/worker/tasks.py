"""Core Celery task: download, extract, transcribe, and generate captions."""

import asyncio
import os
import shutil
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

from celery.signals import worker_process_init, worker_shutting_down
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.logging import get_logger
from backend.models.database import close_db, get_db_session, init_db
from backend.models.task import Task, TaskStatus
from backend.services.fireworks_client import generate_captions
from backend.services.video_processor import download_video, extract_keyframes, transcribe_audio
from backend.worker.celery_app import celery_app

logger = get_logger(__name__)
_worker_loop: asyncio.AbstractEventLoop | None = None


def _get_worker_loop() -> asyncio.AbstractEventLoop:
    """Return the long-lived event loop used by this Celery worker process."""
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
    return _worker_loop


def _run_on_worker_loop(task_id: uuid.UUID) -> None:
    """Run async task code without closing the loop between Celery jobs."""
    loop = _get_worker_loop()
    loop.run_until_complete(_run_async_workflow(task_id))


@worker_shutting_down.connect
def on_worker_shutting_down(sender=None, **kwargs):
    """Log when the Celery worker receives a shutdown signal."""
    global _worker_loop
    logger.warning("WORKER_SHUTTING_DOWN")
    if _worker_loop is not None and not _worker_loop.is_closed():
        try:
            _worker_loop.run_until_complete(close_db())
        finally:
            _worker_loop.close()
            _worker_loop = None


@worker_process_init.connect
def prewarm_whisper_model(**kwargs):
    """Load Whisper model on worker startup to avoid cold-start latency."""
    try:
        from backend.services.video_processor import _get_whisper_model
        settings = get_settings()
        logger.info("WHISPER_PREWARM_STARTED", model=settings.whisper_model)
        _get_whisper_model(settings.whisper_model)
        logger.info("WHISPER_PREWARM_COMPLETED", model=settings.whisper_model)
    except ImportError:
        logger.warning(
            "WHISPER_PREWARM_SKIPPED",
            reason="faster_whisper is not installed",
        )
    except Exception as e:
        logger.warning("WHISPER_PREWARM_FAILED", error=str(e))


async def _run_async_workflow(task_id: uuid.UUID) -> None:
    """Core async workflow for processing a single video task.

    Steps:
    1. Fetch task from DB, update status to PROCESSING.
    2. Download video to temp directory.
    3. Extract 16 keyframes as JPEG.
    4. Extract audio and transcribe with faster-whisper.
    5. Call Fireworks AI with frames + transcript.
    6. Save result to DB, update status to COMPLETED.
    7. Cleanup temp files.
    """
    settings = get_settings()
    temp_root = Path(settings.temp_dir)
    temp_root.mkdir(parents=True, exist_ok=True)
    work_dir = temp_root / str(task_id)
    work_dir.mkdir(parents=True, exist_ok=True)

    session: AsyncSession | None = None
    video_path: Path | None = None
    frames_dir: Path | None = None

    try:
        # Initialize DB if needed
        await init_db()
        session = await get_db_session()

        # Fetch and lock the task
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task is None:
            logger.error("TASK_FAILED", task_id=str(task_id), stage="TASK_LOOKUP", error="Task not found")
            return

        # Update status to PROCESSING
        task.status = TaskStatus.PROCESSING
        await session.commit()
        logger.info("ANALYSIS_STARTED", task_id=str(task_id))
        start_time = datetime.now(timezone.utc)

        # Step 2: Get video (download or use local file)
        video_path = work_dir / "video.mp4"
        if os.path.isfile(task.video_url):
            src = Path(task.video_url)
            if src.resolve() != video_path.resolve():
                logger.info("VIDEO_LOCAL_COPY", task_id=str(task_id), video_url=task.video_url)
                shutil.copy2(task.video_url, str(video_path))
            else:
                logger.info("VIDEO_LOCAL_READY", task_id=str(task_id), video_url=task.video_url)
                video_path = src
        else:
            logger.info("VIDEO_DOWNLOAD_STARTED", task_id=str(task_id), video_url=task.video_url)
            await download_video(str(task.video_url), video_path, settings.max_video_size_bytes)
        logger.info("VIDEO_READY", task_id=str(task_id), video_path=str(video_path))

        # Step 3: Extract 16 keyframes
        frames_dir = work_dir / "frames"
        frames_b64 = extract_keyframes(str(video_path), str(frames_dir), 16)
        logger.info("KEYFRAMES_EXTRACTED", task_id=str(task_id), frame_count=len(frames_b64))

        # Step 4: Transcribe audio
        transcript = transcribe_audio(str(video_path), str(work_dir), settings.whisper_model)
        logger.info(
            "AUDIO_TRANSCRIBED",
            task_id=str(task_id),
            transcript_chars=len(transcript) if transcript else 0,
        )

        # Step 5: Call Fireworks AI
        logger.info("FIREWORKS_REQUEST_START", task_id=str(task_id))
        captions = await generate_captions(
            frames_b64=frames_b64,
            transcript=transcript,
            requested_styles=list(task.styles or []),
        )
        logger.info("VALIDATION", task_id=str(task_id), status="PASSED", caption_keys=list(captions.keys()))

        # Enrich result with metadata for frontend
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        captions["processing_time_seconds"] = round(elapsed, 2)
        captions["model_used"] = settings.fireworks_model
        captions["video_summary"] = captions.get("formal") or next(iter(captions.values()), "")

        # Step 6: Save result
        task.status = TaskStatus.COMPLETED
        task.result_json = captions
        await session.commit()
        logger.info("DATABASE_SAVE", task_id=str(task_id), status="COMPLETED")
        logger.info("TASK_COMPLETED", task_id=str(task_id), elapsed_seconds=round(elapsed, 2))

    except Exception as e:
        logger.error(
            "TASK_FAILED",
            task_id=str(task_id),
            error=f"{type(e).__name__}: {str(e)}",
            stack_trace=traceback.format_exc(),
        )
        if session is not None and session.is_active:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            if task:
                task.status = TaskStatus.FAILED
                task.error_message = f"{type(e).__name__}: {str(e)}"
                await session.commit()
                logger.info("DATABASE_SAVE", task_id=str(task_id), status="FAILED")

    finally:
        # Step 7: Cleanup
        if session is not None:
            await session.close()
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)
            logger.info("TEMP_CLEANUP", task_id=str(task_id), work_dir=str(work_dir))


# =============================================================================
# Celery Task Definition
# =============================================================================


@celery_app.task(
    name="process_video_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    track_started=True,
)
def process_video_task(
    self,
    task_id_str: str,
) -> dict[str, str]:
    """Celery task: process a video URL for caption generation.

    This is the synchronous Celery entry point. It wraps the async workflow
    on the worker process' long-lived event loop.

    Args:
        task_id_str: The UUID string of the task to process.

    Returns:
        Dict with status and result info.
    """
    task_id = uuid.UUID(task_id_str)
    logger.info("WORKER_TASK_RECEIVED", task_id=str(task_id))

    try:
        _run_on_worker_loop(task_id)
        return {"status": "completed", "task_id": task_id_str}
    except Exception as exc:
        logger.exception("TASK_FAILED", task_id=str(task_id), error=str(exc))
        try:
            self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except Exception as retry_exc:
            logger.error("TASK_RETRIES_EXHAUSTED", task_id=str(task_id), error=str(retry_exc))
            return {
                "status": "failed",
                "task_id": task_id_str,
                "error": str(exc),
            }
