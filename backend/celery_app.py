from celery import Celery
import os

# Redis URL from environment variable (important for deployment)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "safety_ai",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# Automatically discover Celery tasks
celery_app.autodiscover_tasks([
    "backend.tasks",
    "backend.services"
])