

from celery import Celery

celery_app = Celery(
    "safety_ai",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# register tasks
import backend.tasks
import backend.services.report_service
