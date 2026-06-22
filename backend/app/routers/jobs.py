from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.job import Job
from app.models.project import Project
from app.models.user import User
from app.schemas.job import JobOut

router = APIRouter()


def ok(data):
    return JSONResponse({"success": True, "data": data})


@router.get("")
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_project_ids = select(Project.id).where(Project.user_id == current_user.id)
    jobs = (
        db.query(Job)
        .filter(Job.project_id.in_(user_project_ids))
        .order_by(Job.created_at.desc())
        .limit(50)
        .all()
    )
    return ok([JobOut.model_validate(j).model_dump(mode="json") for j in jobs])


@router.get("/{job_id}")
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    project = db.get(Project, job.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return ok(JobOut.model_validate(job).model_dump(mode="json"))
