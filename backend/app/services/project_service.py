from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.project import Project


def create_project(db: Session, user_id: str, name: str, description: Optional[str]) -> Project:
    project = Project(user_id=user_id, name=name, description=description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def list_projects(db: Session, user_id: str) -> List[Project]:
    return (
        db.query(Project)
        .filter(Project.user_id == user_id, Project.status == "active")
        .all()
    )


def get_project(db: Session, project_id: str, user_id: str) -> Optional[Project]:
    """Return project only if owned by user AND still active."""
    return (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == user_id,
            Project.status == "active",
        )
        .first()
    )


def get_project_by_id(db: Session, project_id: str) -> Optional[Project]:
    """Return project regardless of owner or status — used for 403 vs 404 distinction."""
    return db.get(Project, project_id)


def update_project(
    db: Session, project: Project, name: Optional[str], description: Optional[str]
) -> Project:
    if name is not None:
        project.name = name
    if description is not None:
        project.description = description
    db.commit()
    db.refresh(project)
    return project


def soft_delete_project(db: Session, project: Project) -> None:
    project.status = "deleted"
    db.commit()
