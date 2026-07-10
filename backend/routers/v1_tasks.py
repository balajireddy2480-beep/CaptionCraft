"""REST API endpoints for video caption task management."""

import os
import shutil
import uuid
from pathlib import Path
import time
import traceback
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Query, Request, Response, UploadFile
from sqlalchemy import delete, select

from backend.core.config import get_settings
from backend.core.deps import APIKeyDep, SessionDep
from backend.core.security import check_ssrf
from backend.core.logging import get_logger
from backend.models.task import Task, TaskStatus
from backend.schemas.task import TaskCreate, TaskResponse
from backend.worker.tasks import process_video_task

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/tasks", tags=["Tasks"])
ALLOWED_STYLES = {"formal", "sarcastic", "humorous_tech", "humorous_non_tech"}


@router.post("", status_code=202, response_model=TaskResponse)
async def create_task(
    body: TaskCreate,
    request: Request,
    session: SessionDep,
    api_key: APIKeyDep,
) -> TaskResponse:
    """Submit a video URL for caption generation.

    Validates the URL (SSRF protection), creates a task in PENDING status,
    dispatches to Celery worker, and returns immediately with 202 Accepted.
    """
    start_time = time.perf_counter()
    video_url_str = str(body.video_url)
    check_ssrf(video_url_str)

    # Filter to requested styles (already validated by Pydantic)
    requested_styles = [s.value for s in body.styles]

    # Create DB task
    task_id = uuid.uuid4()
    task = Task(
        id=task_id,
        video_url=video_url_str,
        styles=requested_styles,
        status=TaskStatus.PENDING,
    )

    logger.info("TASK_CREATED", task_id=str(task_id), video_url=video_url_str, styles=requested_styles)
    session.add(task)
    await session.commit()

    # Dispatch task to Celery worker
    try:
        process_video_task.delay(str(task.id))
        logger.info(
            "TASK_DISPATCHED",
            task_id=str(task.id),
            video_url=video_url_str,
            styles=requested_styles,
            elapsed_ms=round((time.perf_counter() - start_time) * 1000, 2)
        )
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = f"TASK_DISPATCH_FAILED: {type(e).__name__}: {str(e)}"
        await session.commit()
        logger.error(
            "TASK_FAILED",
            task_id=str(task.id),
            stage="TASK_DISPATCH",
            error=str(e),
            stack_trace=traceback.format_exc(),
        )

    return TaskResponse(
        task_id=task.id,
        status=task.status.value if hasattr(task.status, "value") else str(task.status),
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm", ".mkv"}


@router.post("/upload", status_code=202, response_model=TaskResponse)
async def upload_and_create_task(
    video: UploadFile,
    session: SessionDep,
    styles: str = Form("formal,sarcastic,humorous_tech,humorous_non_tech"),
    api_key: APIKeyDep = ...,
) -> TaskResponse:
    """Upload a video file and create a caption generation task.

    Accepts multipart form data with a video file and optional styles.
    Saves the file locally, creates a task in the database, and dispatches
    to the Celery worker for processing.
    """
    start_time = time.perf_counter()
    task_id = uuid.uuid4()
    
    logger.info("UPLOAD_STARTED", task_id=str(task_id), filename=video.filename)

    settings = get_settings()
    max_upload_bytes = settings.max_video_size_bytes

    # Validate file extension
    if not video.filename:
        logger.error("Upload failed: No filename provided", task_id=str(task_id))
        raise HTTPException(status_code=400, detail="No filename provided.")

    ext = Path(video.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.error("Upload failed: Unsupported extension", task_id=str(task_id), extension=ext)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file content and validate size
    content = await video.read()
    content_len = len(content)
    if content_len > max_upload_bytes:
        logger.error("Upload failed: File too large", task_id=str(task_id), size_bytes=content_len)
        raise HTTPException(
            status_code=400,
            detail=(
                f"File too large ({content_len / (1024 * 1024):.1f} MB). "
                f"Max: {settings.max_video_size_mb} MB."
            ),
        )

    # Parse styles
    requested_styles = [s.strip() for s in styles.split(",") if s.strip()]
    if not requested_styles:
        requested_styles = ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]
    invalid_styles = sorted(set(requested_styles) - ALLOWED_STYLES)
    if invalid_styles:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported caption style(s): {', '.join(invalid_styles)}",
        )

    # Generate task ID and save file using the configured temp directory
    temp_dir = Path(settings.temp_dir) / str(task_id)
    temp_dir.mkdir(parents=True, exist_ok=True)
    video_path = temp_dir / f"video{ext}"

    with open(video_path, "wb") as f:
        f.write(content)

    logger.info("UPLOAD_COMPLETED", task_id=str(task_id), video_path=str(video_path), size_bytes=content_len)

    # Create task in database
    task = Task(
        id=task_id,
        video_url=str(video_path),
        styles=requested_styles,
        status=TaskStatus.PENDING,
    )

    logger.info("TASK_CREATED", task_id=str(task_id), video_path=str(video_path), styles=requested_styles)
    session.add(task)
    await session.commit()

    # Dispatch to Celery worker
    try:
        process_video_task.delay(str(task.id))
        logger.info(
            "TASK_DISPATCHED",
            task_id=str(task.id),
            video_path=str(video_path),
            styles=requested_styles,
            elapsed_ms=round((time.perf_counter() - start_time) * 1000, 2)
        )
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = f"TASK_DISPATCH_FAILED: {type(e).__name__}: {str(e)}"
        await session.commit()
        logger.error(
            "TASK_FAILED",
            task_id=str(task.id),
            stage="TASK_DISPATCH",
            error=str(e),
            stack_trace=traceback.format_exc(),
        )

    return TaskResponse(
        task_id=task.id,
        status=task.status.value if hasattr(task.status, "value") else str(task.status),
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    session: SessionDep,
    api_key: APIKeyDep,
) -> TaskResponse:
    """Get the status and result of a caption generation task."""
    start_time = time.perf_counter()
    logger.info("POLL_REQUEST", task_id=str(task_id))
    
    result = await session.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if task is None:
        logger.warning("POLL_RESPONSE", task_id=str(task_id), status="NOT_FOUND")
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found.",
        )

    res = _task_to_response(task)
    logger.info(
        "POLL_RESPONSE",
        task_id=str(task_id),
        status=res.status,
        elapsed_ms=round((time.perf_counter() - start_time) * 1000, 2)
    )
    return res


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    session: SessionDep,
    api_key: APIKeyDep,
    skip: int = Query(0, ge=0, description="Number of tasks to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max tasks to return"),
    status: TaskStatus | None = Query(None, description="Filter by status"),
) -> list[TaskResponse]:
    """List tasks with pagination and optional status filter."""
    query = select(Task).order_by(Task.created_at.desc())
    if status is not None:
        query = query.where(Task.status == status)
    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    tasks = result.scalars().all()

    return [_task_to_response(t) for t in tasks]


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: uuid.UUID,
    session: SessionDep,
    api_key: APIKeyDep,
) -> Response:
    """Delete a task by ID."""
    result = await session.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
    await session.execute(delete(Task).where(Task.id == task_id))
    await session.commit()

    return Response(status_code=204)


@router.post("/{task_id}/retry", status_code=202, response_model=TaskResponse)
async def retry_task(
    task_id: uuid.UUID,
    session: SessionDep,
    api_key: APIKeyDep,
) -> TaskResponse:
    """Re-queue a failed task for processing."""
    result = await session.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
    status_val = task.status.value if hasattr(task.status, "value") else str(task.status)
    if status_val != "FAILED":
        raise HTTPException(
            status_code=400,
            detail=f"Only failed tasks can be retried. Current status: {status_val}",
        )
    task.status = TaskStatus.PENDING
    task.error_message = None
    task.retry_count += 1
    await session.commit()

    try:
        process_video_task.delay(str(task.id))
        logger.info("TASK_DISPATCHED", task_id=str(task.id), attempt=task.retry_count)
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = f"TASK_DISPATCH_FAILED: {type(e).__name__}: {str(e)}"
        await session.commit()
        logger.error(
            "TASK_FAILED",
            task_id=str(task.id),
            stage="TASK_DISPATCH",
            error=str(e),
            stack_trace=traceback.format_exc(),
        )

    return _task_to_response(task)


def _task_to_response(task: Task) -> TaskResponse:
    """Convert a Task ORM model to a TaskResponse schema."""
    status_val = task.status.value if hasattr(task.status, "value") else str(task.status)

    result: dict[str, Any] | None = None
    if status_val == "COMPLETED" and task.result_json:
        result = task.result_json

    error_msg: str | None = None
    if status_val == "FAILED":
        error_msg = task.error_message

    return TaskResponse(
        task_id=task.id,
        status=status_val,
        result=result,
        error_message=error_msg,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
