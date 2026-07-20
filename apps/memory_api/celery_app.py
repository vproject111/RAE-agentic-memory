import os

from celery import Celery

# Set default settings module
os.environ.setdefault("CELERY_CONFIG_MODULE", "apps.memory_api.config")

from apps.memory_api.config import settings

celery_app = Celery(
    "rae_memory_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Optional configuration
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Auto-discover tasks from all registered apps
celery_app.autodiscover_tasks(["apps.memory_api.tasks"])
