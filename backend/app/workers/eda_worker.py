import io
import logging

import pandas as pd

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name="app.workers.eda_worker.run_eda_task",
)
def run_eda_task(self, job_id: str):
    from app.database import SessionLocal
    from app.models.dataset import Dataset, DatasetVersion
    from app.models.eda_result import EdaResult
    from app.models.job import Job
    from app.models.project import Project  # noqa: F401
    from app.models.profile import DatasetProfile
    from app.services.eda_service import compute_eda_charts
    from app.services.storage_service import storage

    db = SessionLocal()
    job = None
    try:
        job = db.get(Job, job_id)
        if not job:
            logger.error("EDA job %s not found", job_id)
            return

        job.status = "running"
        db.commit()

        input_data = job.input_json or {}
        version_id = input_data.get("dataset_version_id")
        if not version_id:
            raise ValueError("Missing dataset_version_id in job input")

        version = db.get(DatasetVersion, version_id)
        dataset = db.get(Dataset, version.dataset_id)

        # Load profile for column type info
        profile_row = (
            db.query(DatasetProfile)
            .filter(DatasetProfile.dataset_version_id == version_id)
            .order_by(DatasetProfile.created_at.desc())
            .first()
        )
        if not profile_row or not profile_row.profile_json:
            raise ValueError("No profile found — profile must run before EDA")

        profile = profile_row.profile_json

        # Download and parse the file
        content = storage.download_file(version.storage_uri)
        from app.services.storage_service import resolve_format
        fmt = resolve_format(version.storage_uri, dataset.file_format)
        if fmt == "csv":
            df = pd.read_csv(io.BytesIO(content))
        elif fmt == "xlsx":
            df = pd.read_excel(io.BytesIO(content))
        elif fmt == "json":
            df = pd.read_json(io.BytesIO(content))
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        charts = compute_eda_charts(df, profile)

        # Upsert EDA result for this version
        existing = (
            db.query(EdaResult)
            .filter(EdaResult.dataset_version_id == version_id)
            .first()
        )
        if existing:
            existing.status = "succeeded"
            existing.charts_json = charts
            existing.error_message = None
        else:
            db.add(EdaResult(
                dataset_version_id=version_id,
                status="succeeded",
                charts_json=charts,
            ))

        job.status = "succeeded"
        job.progress_percent = 100.0
        db.commit()

    except Exception as exc:
        logger.exception("EDA failed for job %s: %s", job_id, exc)
        if job is not None:
            if self.request.retries >= self.max_retries:
                job.status = "failed"
                job.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()
