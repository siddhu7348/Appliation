from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "forecastiq",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.nightly"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=60 * 60 * 6,
    worker_max_tasks_per_child=8,
)

celery_app.conf.beat_schedule = {
    # Nightly batch: ingest -> features -> inference -> persist -> cache -> alerts.
    # Starts at 23:00 UTC and is sized to complete well before the 08:00 store open.
    "nightly-forecast-batch": {
        "task": "app.tasks.nightly.run_nightly_batch",
        "schedule": crontab(hour=23, minute=0),
    },
    # Weekly drift evaluation on the rolling MAPE window.
    "weekly-drift-check": {
        "task": "app.tasks.nightly.check_model_drift",
        "schedule": crontab(hour=6, minute=30, day_of_week=1),
    },
}
