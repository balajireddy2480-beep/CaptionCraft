"""Celery application configuration for video caption background tasks."""

from celery import Celery

from backend.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "video_caption_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["backend.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_acks_on_failure_or_timeout=False,
    result_expires=86400,  # Results expire after 1 day
)

# No rate limit — allow concurrent processing
celery_app.conf.task_annotations = {
    "backend.worker.tasks.process_video_task": {
        "rate_limit": "10/m",
    }
}
