import io
import logging

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.cleaning import CleaningAction, CleaningExecution
from app.models.dataset import Dataset, DatasetVersion
from app.models.job import Job
from app.models.user import User
from app.schemas.cleaning import (
    ApplyRequest,
    CleaningActionOut,
    CleaningExecutionOut,
    CleaningHistoryItem,
    PreviewRequest,
)
from app.services.cleaning_service import preview_action
from app.services.project_service import get_project
from app.services.storage_service import storage

logger = logging.getLogger(__name__)
router = APIRouter()


def ok(data):
    return JSONResponse({"success": True, "data": data})


def _assert_version_access(db: Session, version_id: str, user_id: str) -> DatasetVersion:
    version = db.get(DatasetVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Dataset version not found")
    ds = db.get(Dataset, version.dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    project = get_project(db, ds.project_id, user_id)
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")
    return version


def _load_df(version: DatasetVersion, dataset: Dataset) -> pd.DataFrame:
    from app.services.storage_service import resolve_format
    content = storage.download_file(version.storage_uri)
    fmt = resolve_format(version.storage_uri, dataset.file_format)
    if fmt == "csv":
        return pd.read_csv(io.BytesIO(content))
    elif fmt == "xlsx":
        return pd.read_excel(io.BytesIO(content))
    elif fmt == "json":
        return pd.read_json(io.BytesIO(content))
    raise HTTPException(status_code=422, detail=f"Unsupported file format: {fmt}")


@router.post("/preview")
def preview_transformation(
    body: PreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    version = _assert_version_access(db, body.dataset_version_id, current_user.id)
    dataset = db.get(Dataset, version.dataset_id)

    try:
        df = _load_df(version, dataset)
        result = preview_action(df, body.action_type, body.parameters)
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid parameters: {e}")

    return ok(result)


@router.post("/apply")
def apply_transformation(
    body: ApplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    version = _assert_version_access(db, body.dataset_version_id, current_user.id)
    dataset = db.get(Dataset, version.dataset_id)

    action = CleaningAction(
        dataset_version_id=body.dataset_version_id,
        action_type=body.action_type,
        title=body.title,
        description=body.description,
        parameters_json=body.parameters,
        status="proposed",
        suggested_by=body.suggested_by,
    )
    db.add(action)
    db.flush()

    job = Job(
        project_id=dataset.project_id,
        dataset_id=dataset.id,
        job_type="apply_cleaning",
        status="queued",
        input_json={
            "cleaning_action_id": action.id,
            "dataset_version_id": body.dataset_version_id,
            "action_type": body.action_type,
            "parameters": body.parameters,
        },
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    from app.workers.cleaning_worker import apply_cleaning_task
    try:
        task = apply_cleaning_task.delay(job.id)
        job.celery_task_id = task.id
        db.commit()
    except Exception as e:
        job.status = "failed"
        job.error_message = f"Dispatch failed: {e}"
        db.commit()

    return ok({"job_id": job.id, "cleaning_action_id": action.id})


@router.get("/history/{dataset_id}")
def get_cleaning_history(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    project = get_project(db, ds.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")

    version_ids = [
        r[0] for r in db.query(DatasetVersion.id)
        .filter(DatasetVersion.dataset_id == dataset_id).all()
    ]

    actions = (
        db.query(CleaningAction)
        .filter(CleaningAction.dataset_version_id.in_(version_ids))
        .order_by(CleaningAction.created_at.desc())
        .all()
    )

    items = []
    for action in actions:
        execution = (
            db.query(CleaningExecution)
            .filter(CleaningExecution.cleaning_action_id == action.id)
            .first()
        )
        items.append(CleaningHistoryItem(
            action=CleaningActionOut.model_validate(action),
            execution=CleaningExecutionOut.model_validate(execution) if execution else None,
        ).model_dump(mode="json"))

    return ok(items)
