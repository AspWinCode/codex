from __future__ import annotations

from celery import Celery

from app.config import settings

celery = Celery("judger", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "judger.tasks.run_python_io": {"queue": "queue_python_io"},
        "judger.tasks.run_pytest": {"queue": "queue_python_oop"},
        "judger.tasks.run_python_numpy": {"queue": "queue_python_numpy"},
        "judger.tasks.run_sql": {"queue": "queue_sql"},
    },
)
