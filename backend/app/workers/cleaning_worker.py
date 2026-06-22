import io
import logging
from datetime import datetime, timezone

import pandas as pd

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name="app.workers.cleaning_worker.apply_cleaning_task",
)
def apply_cleaning_task(self, job_id: str):
    from app.database import SessionLocal
    from app.models.cleaning import CleaningAction, CleaningExecution
    from app.models.dataset import Dataset, DatasetVersion
    from app.models.job import Job
    from app.models.project import Project  # noqa: F401
    from app.services.cleaning_service import apply_action
    from app.services.storage_service import storage

    db = SessionLocal()
    job = None
    try:
        job = db.get(Job, job_id)
        if not job:
            logger.error("Cleaning job %s not found", job_id)
            return

        job.status = "running"
        db.commit()

        input_data = job.input_json or {}
        cleaning_action_id = input_data["cleaning_action_id"]
        version_id = input_data["dataset_version_id"]
        action_type = input_data["action_type"]
        parameters = input_data.get("parameters", {})

        action_row = db.get(CleaningAction, cleaning_action_id)
        input_version = db.get(DatasetVersion, version_id)
        dataset = db.get(Dataset, input_version.dataset_id)

        # Load the file
        content = storage.download_file(input_version.storage_uri)
        fmt = dataset.file_format
        if fmt == "csv":
            df = pd.read_csv(io.BytesIO(content))
        elif fmt == "xlsx":
            df = pd.read_excel(io.BytesIO(content))
        elif fmt == "json":
            df = pd.read_json(io.BytesIO(content))
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        rows_before = len(df)
        cols_before = list(df.columns)

        # Apply transform
        result_df = apply_action(df, action_type, parameters)

        rows_after = len(result_df)
        cols_after = list(result_df.columns)

        # Save new version to MinIO (always CSV regardless of original format)
        new_version_number = input_version.version_number + 1
        base_name = dataset.original_file_name.rsplit(".", 1)[0]
        new_key = f"datasets/{dataset.id}/v{new_version_number}/{base_name}.csv"
        buf = io.BytesIO()
        result_df.to_csv(buf, index=False)
        buf.seek(0)
        storage.upload_file(buf, new_key, "text/csv")

        # Create new DatasetVersion
        new_version = DatasetVersion(
            dataset_id=dataset.id,
            version_number=new_version_number,
            parent_version_id=version_id,
            storage_uri=new_key,
            row_count=rows_after,
            column_count=len(cols_after),
        )
        db.add(new_version)
        db.flush()

        # Create CleaningExecution record
        now = datetime.now(timezone.utc)
        execution = CleaningExecution(
            cleaning_action_id=cleaning_action_id,
            input_version_id=version_id,
            output_version_id=new_version.id,
            execution_status="succeeded",
            result_summary=(
                f"Rows: {rows_before} → {rows_after}. "
                f"Columns: {len(cols_before)} → {len(cols_after)}."
            ),
            executed_at=now,
            completed_at=now,
        )
        db.add(execution)

        # Mark action as applied
        action_row.status = "applied"

        job.status = "succeeded"
        job.progress_percent = 100.0
        job.output_json = {"output_version_id": new_version.id}
        db.commit()
        logger.info("Cleaning job %s succeeded, new version %s", job_id, new_version.id)

        # Dispatch profiling, EDA, and AI analysis for the new version
        try:
            from app.models.job import Job as JobModel
            from app.workers.profiling_worker import profile_dataset_task
            from app.workers.eda_worker import run_eda_task
            from app.workers.ai_worker import analyze_dataset_task

            profile_job = JobModel(
                project_id=dataset.project_id,
                dataset_id=dataset.id,
                job_type="profile_dataset",
                status="queued",
                input_json={"dataset_version_id": new_version.id},
            )
            db.add(profile_job)

            eda_job = JobModel(
                project_id=dataset.project_id,
                dataset_id=dataset.id,
                job_type="run_eda",
                status="queued",
                input_json={"dataset_version_id": new_version.id},
            )
            db.add(eda_job)

            ai_job = JobModel(
                project_id=dataset.project_id,
                dataset_id=dataset.id,
                job_type="analyze_dataset",
                status="queued",
                input_json={"dataset_version_id": new_version.id},
            )
            db.add(ai_job)
            db.commit()
            db.refresh(profile_job)
            db.refresh(eda_job)
            db.refresh(ai_job)

            try:
                task = profile_dataset_task.delay(profile_job.id)
                profile_job.celery_task_id = task.id
            except Exception as e:
                profile_job.status = "failed"
                profile_job.error_message = f"Failed to dispatch profiling task: {e}"
                logger.warning("Failed to dispatch profiling task for version %s: %s", new_version.id, e)

            try:
                task = run_eda_task.delay(eda_job.id)
                eda_job.celery_task_id = task.id
            except Exception as e:
                eda_job.status = "failed"
                eda_job.error_message = f"Failed to dispatch EDA task: {e}"
                logger.warning("Failed to dispatch EDA task for version %s: %s", new_version.id, e)

            try:
                task = analyze_dataset_task.delay(ai_job.id)
                ai_job.celery_task_id = task.id
            except Exception as e:
                ai_job.status = "failed"
                ai_job.error_message = f"Failed to dispatch AI analysis task: {e}"
                logger.warning("Failed to dispatch AI analysis task for version %s: %s", new_version.id, e)

            db.commit()
            logger.info(
                "Dispatched profiling/EDA/AI jobs for new version %s (profile=%s, eda=%s, ai=%s)",
                new_version.id, profile_job.id, eda_job.id, ai_job.id,
            )
        except Exception as dispatch_exc:
            logger.exception(
                "Failed to dispatch downstream jobs for version %s: %s", new_version.id, dispatch_exc
            )

    except Exception as exc:
        logger.exception("Cleaning job %s failed: %s", job_id, exc)
        if job is not None:
            if self.request.retries >= self.max_retries:
                job.status = "failed"
                job.error_message = str(exc)
                try:
                    input_data = job.input_json or {}
                    action_row = db.get(CleaningAction, input_data.get("cleaning_action_id"))
                    if action_row:
                        action_row.status = "failed"
                except Exception:
                    pass
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()
