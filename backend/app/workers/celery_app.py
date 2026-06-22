from celery import Celery

from app.config import settings

celery_app = Celery(
    "automl",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.profiling_worker",
        "app.workers.ai_worker",
        "app.workers.eda_worker",
        "app.workers.cleaning_worker",
        "app.workers.training_worker",
        "app.workers.pipeline_worker",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.workers.profiling_worker.*": {"queue": "profiling"},
        "app.workers.ai_worker.*": {"queue": "profiling"},
        "app.workers.eda_worker.*": {"queue": "profiling"},
        "app.workers.cleaning_worker.*": {"queue": "profiling"},
        "app.workers.training_worker.*": {"queue": "profiling"},
        "app.workers.pipeline_worker.*": {"queue": "profiling"},
    },
)
