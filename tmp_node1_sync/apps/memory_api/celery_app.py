from celery import Celery

from apps.memory_api.config import settings

celery_app = Celery(
    "rae_memory_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["apps.memory_api.tasks.background_tasks"],  # Points to the tasks module
)

celery_app.conf.update(
    task_track_started=True,
)
