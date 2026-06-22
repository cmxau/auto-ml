import io
import logging

import pandas as pd

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10, name="app.workers.profiling_worker.profile_dataset_task")
def profile_dataset_task(self, job_id: str):
    from app.database import SessionLocal
    from app.models.dataset import Dataset, DatasetVersion
    from app.models.job import Job
    from app.models.profile import DatasetColumnProfile, DatasetProfile
    from app.models.project import Project  # noqa: F401 — registers FK target
    from app.services.profiling_service import profile_dataframe
    from app.services.storage_service import storage

    db = SessionLocal()
    job = None
    try:
        job = db.get(Job, job_id)
        if not job:
            logger.error("Job %s not found", job_id)
            return

        job.status = "running"
        db.commit()

        input_data = job.input_json or {}
        version_id = input_data.get("dataset_version_id")
        if not version_id:
            raise ValueError(f"Missing dataset_version_id in job {job_id} input_json")
        version = db.get(DatasetVersion, version_id)
        dataset = db.get(Dataset, version.dataset_id)

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

        result = profile_dataframe(df)

        dataset.row_count = result["row_count"]
        dataset.column_count = result["column_count"]
        dataset.status = "ready"
        version.row_count = result["row_count"]
        version.column_count = result["column_count"]

        profile = DatasetProfile(
            dataset_version_id=version_id,
            profile_json=result,
            missing_value_count=result["missing_value_count"],
            duplicate_row_count=result["duplicate_row_count"],
            numeric_column_count=result["numeric_column_count"],
            categorical_column_count=result["categorical_column_count"],
        )
        db.add(profile)
        db.flush()

        for col in result["columns"]:
            db.add(DatasetColumnProfile(
                dataset_profile_id=profile.id,
                column_name=col["column_name"],
                data_type=col["data_type"],
                missing_count=col["missing_count"],
                unique_count=col["unique_count"],
                mean_value=col["mean_value"],
                std_value=col["std_value"],
                min_value=col["min_value"],
                max_value=col["max_value"],
                top_values_json=col["top_values"],
                example_values_json=col["example_values"],
                high_cardinality_flag=col["high_cardinality_flag"],
            ))

        job.status = "succeeded"
        job.progress_percent = 100.0
        job.output_json = {"profile_id": profile.id}
        db.commit()

        # Auto-dispatch AI analysis job
        ai_job = Job(
            project_id=job.project_id,
            dataset_id=dataset.id,
            job_type="analyze_dataset",
            status="queued",
            input_json={"dataset_id": dataset.id, "dataset_version_id": version_id},
        )
        db.add(ai_job)
        db.commit()
        db.refresh(ai_job)
        try:
            from app.workers.ai_worker import analyze_dataset_task
            task = analyze_dataset_task.delay(ai_job.id)
            ai_job.celery_task_id = task.id
            db.commit()
        except Exception as dispatch_err:
            logger.warning("Could not dispatch AI job: %s", dispatch_err)
            ai_job.status = "failed"
            ai_job.error_message = str(dispatch_err)
            db.commit()

        # Auto-dispatch EDA job
        eda_job = Job(
            project_id=job.project_id,
            dataset_id=dataset.id,
            job_type="run_eda",
            status="queued",
            input_json={"dataset_version_id": version_id},
        )
        db.add(eda_job)
        db.commit()
        db.refresh(eda_job)
        try:
            from app.workers.eda_worker import run_eda_task
            eda_task = run_eda_task.delay(eda_job.id)
            eda_job.celery_task_id = eda_task.id
            db.commit()
        except Exception as dispatch_err:
            logger.warning("Could not dispatch EDA job: %s", dispatch_err)
            eda_job.status = "failed"
            eda_job.error_message = str(dispatch_err)
            db.commit()

    except Exception as exc:
        logger.exception("Profiling failed for job %s: %s", job_id, exc)
        if job is not None:
            if self.request.retries >= self.max_retries:
                # Only mark failed after all retries exhausted
                job.status = "failed"
                job.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()
