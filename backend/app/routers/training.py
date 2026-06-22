import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.dataset import DatasetVersion
from app.models.job import Job
from app.models.training import TrainingMetric, TrainingRun
from app.models.user import User
from app.schemas.training import (
    CompareRunsRequest,
    StartTrainingRequest,
    TrainingMetricOut,
    TrainingRunOut,
)
from app.services.project_service import get_project

logger = logging.getLogger(__name__)
router = APIRouter()


def ok(data):
    return JSONResponse({"success": True, "data": data})


def _assert_run_access(db: Session, run_id: str, user_id: str) -> TrainingRun:
    run = db.get(TrainingRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Training run not found")
    project = get_project(db, run.project_id, user_id)
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")
    return run


def _run_with_metrics(db: Session, run: TrainingRun) -> dict:
    metrics = (
        db.query(TrainingMetric)
        .filter(TrainingMetric.training_run_id == run.id)
        .all()
    )
    data = TrainingRunOut.model_validate(run).model_dump(mode="json")
    data["metrics"] = [TrainingMetricOut.model_validate(m).model_dump(mode="json") for m in metrics]
    return data


@router.post("/training/start", status_code=201)
def start_training(
    body: StartTrainingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import io
    import pandas as pd

    version = db.get(DatasetVersion, body.dataset_version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Dataset version not found")

    from app.models.dataset import Dataset
    dataset = db.get(Dataset, version.dataset_id)
    project = get_project(db, dataset.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")

    valid_model_types = {
        "logistic_regression", "random_forest", "xgboost",
        "linear_regression", "random_forest_regressor", "xgboost_regressor",
    }
    if body.model_type not in valid_model_types:
        raise HTTPException(status_code=422, detail=f"Invalid model_type '{body.model_type}'")

    if body.task_type not in ("classification", "regression"):
        raise HTTPException(status_code=422, detail="task_type must be 'classification' or 'regression'")

    # Validate target column exists and column count is within limit
    from app.services.storage_service import storage
    try:
        content = storage.download_file(version.storage_uri)
        fmt = dataset.file_format
        if fmt == "csv":
            df_headers = pd.read_csv(io.BytesIO(content), nrows=0)
        elif fmt == "xlsx":
            df_headers = pd.read_excel(io.BytesIO(content), nrows=0)
        elif fmt == "json":
            df_headers = pd.read_json(io.BytesIO(content)).iloc[:0]
        else:
            df_headers = pd.read_csv(io.BytesIO(content), nrows=0)

        col_count = len(df_headers.columns)
        if col_count > 500:
            raise HTTPException(
                status_code=422,
                detail=f"Dataset has {col_count} columns. Maximum supported is 500.",
            )

        available = sorted(df_headers.columns.tolist())
        if body.target_column not in df_headers.columns:
            raise HTTPException(
                status_code=422,
                detail=f"Column '{body.target_column}' not found. Available columns: {available}",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Could not pre-validate columns for version %s: %s", version.id, e)

    run = TrainingRun(
        project_id=dataset.project_id,
        dataset_version_id=body.dataset_version_id,
        model_type=body.model_type,
        task_type=body.task_type,
        hyperparameters_json=body.hyperparameters,
        train_status="queued",
        selected_target_column=body.target_column,
    )
    db.add(run)
    db.flush()

    job = Job(
        project_id=dataset.project_id,
        dataset_id=dataset.id,
        job_type="train_model",
        status="queued",
        input_json={"training_run_id": run.id},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    from app.workers.training_worker import train_model_task
    try:
        task = train_model_task.delay(job.id)
        job.celery_task_id = task.id
        db.commit()
    except Exception as e:
        job.status = "failed"
        job.error_message = f"Dispatch failed: {e}"
        run.train_status = "failed"
        db.commit()

    return ok({"training_run_id": run.id, "job_id": job.id})


@router.get("/projects/{project_id}/training/runs")
def list_training_runs(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")

    runs = (
        db.query(TrainingRun)
        .filter(TrainingRun.project_id == project_id)
        .order_by(TrainingRun.created_at.desc())
        .all()
    )
    return ok([TrainingRunOut.model_validate(r).model_dump(mode="json") for r in runs])


@router.get("/training/runs/{run_id}")
def get_training_run(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = _assert_run_access(db, run_id, current_user.id)
    return ok(_run_with_metrics(db, run))


@router.get("/training/runs/{run_id}/metrics")
def get_training_metrics(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = _assert_run_access(db, run_id, current_user.id)
    metrics = (
        db.query(TrainingMetric)
        .filter(TrainingMetric.training_run_id == run.id)
        .all()
    )
    return ok([TrainingMetricOut.model_validate(m).model_dump(mode="json") for m in metrics])


@router.get("/training/runs/{run_id}/feature-importance")
def get_feature_importance(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = _assert_run_access(db, run_id, current_user.id)
    return ok(run.feature_importance_json or [])


@router.get("/training/runs/{run_id}/summary")
def get_training_summary(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = _assert_run_access(db, run_id, current_user.id)
    if run.train_status != "succeeded":
        raise HTTPException(status_code=422, detail="Training run must be succeeded to get summary")

    metrics = {
        m.metric_name: m.metric_value
        for m in db.query(TrainingMetric)
        .filter(TrainingMetric.training_run_id == run.id)
        .all()
    }
    feature_importance = run.feature_importance_json or []

    from app.services.ai_service import summarize_training_results
    try:
        result = summarize_training_results(
            run.model_type, run.task_type, metrics, feature_importance
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI summary failed: {e}")

    return ok(result)


@router.post("/training/compare")
def compare_training_runs(
    body: CompareRunsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if len(body.run_ids) < 2:
        raise HTTPException(status_code=422, detail="Provide at least 2 run_ids to compare")
    if len(body.run_ids) > 5:
        raise HTTPException(status_code=422, detail="Compare at most 5 runs at a time")

    comparison = []
    for run_id in body.run_ids:
        run = _assert_run_access(db, run_id, current_user.id)
        metrics = {
            m.metric_name: m.metric_value
            for m in db.query(TrainingMetric)
            .filter(TrainingMetric.training_run_id == run_id)
            .all()
        }
        comparison.append({
            "run_id": run.id,
            "model_type": run.model_type,
            "task_type": run.task_type,
            "target_column": run.selected_target_column,
            "train_status": run.train_status,
            "metrics": metrics,
        })

    return ok(comparison)


@router.get("/training/runs/{run_id}/download")
def download_model_artifact(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = _assert_run_access(db, run_id, current_user.id)
    if run.train_status != "succeeded":
        raise HTTPException(
            status_code=422,
            detail="Training run must be succeeded to download artifact",
        )
    if not run.artifact_id:
        raise HTTPException(status_code=404, detail="No artifact found for this run")

    from app.models.training import Artifact
    artifact = db.get(Artifact, run.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact record not found")

    from app.services.storage_service import storage
    content = storage.download_file(artifact.storage_uri)
    file_name = artifact.file_name or "model.joblib"
    return StreamingResponse(
        iter([content]),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
