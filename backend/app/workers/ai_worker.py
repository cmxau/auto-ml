import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name="app.workers.ai_worker.analyze_dataset_task",
)
def analyze_dataset_task(self, job_id: str):
    from app.database import SessionLocal
    from app.models.ai_insight import AIInsight
    from app.models.dataset import DatasetVersion
    from app.models.job import Job
    from app.models.project import Project  # noqa: F401
    from app.models.profile import DatasetProfile
    from app.services.ai_service import (
        analyze_dataset,
        recommend_models,
        suggest_cleaning_actions,
    )

    db = SessionLocal()
    job = None
    try:
        job = db.get(Job, job_id)
        if not job:
            logger.error("AI job %s not found", job_id)
            return

        job.status = "running"
        db.commit()

        input_data = job.input_json or {}
        dataset_version_id = input_data.get("dataset_version_id")
        dataset_id = input_data.get("dataset_id")
        if not dataset_version_id or not dataset_id:
            raise ValueError("Missing dataset_version_id or dataset_id in job input")

        profile_row = (
            db.query(DatasetProfile)
            .filter(DatasetProfile.dataset_version_id == dataset_version_id)
            .order_by(DatasetProfile.created_at.desc())
            .first()
        )
        if not profile_row or not profile_row.profile_json:
            raise ValueError("No profile found for dataset_version_id")

        profile = profile_row.profile_json

        # Delete stale insights for this dataset+version
        db.query(AIInsight).filter(
            AIInsight.dataset_id == dataset_id,
            AIInsight.dataset_version_id == dataset_version_id,
        ).delete()
        db.flush()

        # Run Dataset Analyst Agent
        analysis = analyze_dataset(profile)
        task_type = analysis.get("task_type", "unknown")
        target_candidates = analysis.get("target_candidates", [])
        first_target = target_candidates[0]["column"] if target_candidates else ""

        db.add(AIInsight(
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
            insight_type="task_detection",
            content=analysis.get("dataset_summary", ""),
            confidence_score=analysis.get("task_type_confidence"),
            metadata_json={
                "task_type": task_type,
                "task_type_reasoning": analysis.get("task_type_reasoning"),
                "target_candidates": target_candidates,
                "data_quality_issues": analysis.get("data_quality_issues", []),
            },
        ))

        # Run Cleaning Advisor Agent
        cleaning_actions = suggest_cleaning_actions(profile, task_type)
        db.add(AIInsight(
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
            insight_type="cleaning_suggestion",
            content=f"{len(cleaning_actions)} cleaning actions suggested.",
            confidence_score=None,
            metadata_json={"actions": cleaning_actions},
        ))

        # Run Model Recommendation Agent (only if task type is known and target exists)
        if task_type != "unknown" and first_target:
            model_recs = recommend_models(profile, task_type, first_target)
            db.add(AIInsight(
                dataset_id=dataset_id,
                dataset_version_id=dataset_version_id,
                insight_type="model_recommendation",
                content=f"Baseline: {model_recs.get('baseline_model', 'N/A')}",
                confidence_score=None,
                metadata_json=model_recs,
            ))

        job.status = "succeeded"
        job.progress_percent = 100.0
        db.commit()

    except Exception as exc:
        logger.exception("AI analysis failed for job %s: %s", job_id, exc)
        if job is not None:
            if self.request.retries >= self.max_retries:
                job.status = "failed"
                job.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()
