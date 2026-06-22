from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.project_service import (
    create_project,
    get_project,
    get_project_by_id,
    list_projects,
    soft_delete_project,
    update_project,
)

router = APIRouter()


def ok(data, status_code: int = 200):
    return JSONResponse({"success": True, "data": data}, status_code=status_code)


def _get_owned_project_or_error(db: Session, project_id: str, user_id: str):
    """Return project if owned by user and active.
    - 403 if project exists, is active, but belongs to a different user
    - 404 if project doesn't exist or has been soft-deleted (even if owned by this user)
    """
    project = get_project(db, project_id, user_id)
    if project:
        return project
    # Check if an active project with this id exists but belongs to someone else → 403
    exists = get_project_by_id(db, project_id)
    if exists and exists.status == "active" and exists.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    raise HTTPException(status_code=404, detail="Project not found")


@router.post("", status_code=201)
def create(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = create_project(db, current_user.id, body.name, body.description)
    return ok(ProjectOut.model_validate(project).model_dump(mode="json"), status_code=201)


@router.get("")
def list_(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    projects = list_projects(db, current_user.id)
    return ok([ProjectOut.model_validate(p).model_dump(mode="json") for p in projects])


@router.get("/{project_id}")
def get(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_owned_project_or_error(db, project_id, current_user.id)
    return ok(ProjectOut.model_validate(project).model_dump(mode="json"))


@router.patch("/{project_id}")
def patch(
    project_id: str,
    body: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_owned_project_or_error(db, project_id, current_user.id)
    project = update_project(db, project, body.name, body.description)
    return ok(ProjectOut.model_validate(project).model_dump(mode="json"))


@router.delete("/{project_id}", status_code=204)
def delete(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_owned_project_or_error(db, project_id, current_user.id)
    soft_delete_project(db, project)
    return Response(status_code=204)
