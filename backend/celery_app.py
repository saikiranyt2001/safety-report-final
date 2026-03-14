import os

from celery import Celery

from backend.core.config import settings


REDIS_URL = os.getenv("REDIS_URL", settings.REDIS_URL)

celery = Celery(
    "ai_safety",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "backend.tasks.pipeline_tasks.*": {"queue": "ai_tasks"},
    },
)

celery.autodiscover_tasks([
    "backend.tasks",
    "backend.services",
])

# Backward-compatible alias for existing imports.
celery_app = celery