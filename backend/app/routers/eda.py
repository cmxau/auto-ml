from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.dataset import Dataset, DatasetVersion
from app.models.eda_result import EdaResult
from app.models.job import Job
from app.models.user import User
from app.schemas.eda import EdaResultOut
from app.services.project_service import get_project

router = APIRouter()


def ok(data):
    return JSONResponse({"success": True, "data": data})


def _assert_dataset_access(db: Session, dataset_id: str, user_id: str) -> Dataset:
    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    project = get_project(db, ds.project_id, user_id)
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")
    return ds


@router.post("/generate")
def generate_eda(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset_id = body.get("dataset_id")
    dataset_version_id = body.get("dataset_version_id")
    if not dataset_id:
        raise HTTPException(status_code=422, detail="dataset_id required")

    ds = _assert_dataset_access(db, dataset_id, current_user.id)
    if ds.status != "ready":
        raise HTTPException(status_code=422, detail="Dataset must be profiled first")

    if not dataset_version_id:
        latest = (
            db.query(DatasetVersion)
            .filter(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version_number.desc())
            .first()
        )
        if not latest:
            raise HTTPException(status_code=422, detail="No dataset version found")
        dataset_version_id = latest.id

    job = Job(
        project_id=ds.project_id,
        dataset_id=dataset_id,
        job_type="run_eda",
        status="queued",
        input_json={"dataset_version_id": dataset_version_id},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    from app.workers.eda_worker import run_eda_task
    try:
        task = run_eda_task.delay(job.id)
        job.celery_task_id = task.id
        db.commit()
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()

    return ok({"job_id": job.id})


@router.get("/{dataset_version_id}")
def get_eda(
    dataset_version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    version = db.get(DatasetVersion, dataset_version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Dataset version not found")
    _assert_dataset_access(db, version.dataset_id, current_user.id)

    result = (
        db.query(EdaResult)
        .filter(EdaResult.dataset_version_id == dataset_version_id)
        .order_by(EdaResult.created_at.desc())
        .first()
    )
    if not result:
        return ok(None)
    return ok(EdaResultOut.model_validate(result).model_dump(mode="json"))
