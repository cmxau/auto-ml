from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.dataset import Dataset, DatasetVersion
from app.models.job import Job

ALLOWED_EXTENSIONS = {"csv", "xlsx", "json"}


def validate_extension(filename: str) -> Optional[str]:
    """Return extension if allowed, None otherwise."""
    if "." not in filename:
        return None
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext if ext in ALLOWED_EXTENSIONS else None


def create_dataset_with_version(
    db: Session,
    project_id: str,
    name: str,
    source_type: str,
    original_file_name: str,
    file_format: str,
    storage_uri: str,
) -> Tuple[Dataset, DatasetVersion]:
    ds = Dataset(
        project_id=project_id,
        name=name,
        source_type=source_type,
        original_file_name=original_file_name,
        file_format=file_format,
        storage_uri=storage_uri,
        status="uploaded",
    )
    db.add(ds)
    db.flush()  # get ds.id without full commit

    version = DatasetVersion(
        dataset_id=ds.id,
        version_number=0,
        storage_uri=storage_uri,
    )
    db.add(version)
    db.commit()
    db.refresh(ds)
    db.refresh(version)
    return ds, version


def create_profiling_job(
    db: Session, project_id: str, dataset_id: str, dataset_version_id: str
) -> Job:
    job = Job(
        project_id=project_id,
        dataset_id=dataset_id,
        job_type="profile_dataset",
        status="queued",
        input_json={"dataset_version_id": dataset_version_id},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def list_datasets(db: Session, project_id: str) -> List[Dataset]:
    return (
        db.query(Dataset)
        .filter(Dataset.project_id == project_id, Dataset.status != "deleted")
        .all()
    )


def get_dataset(db: Session, dataset_id: str) -> Optional[Dataset]:
    return db.get(Dataset, dataset_id)


def get_dataset_versions(db: Session, dataset_id: str) -> List[DatasetVersion]:
    return (
        db.query(DatasetVersion)
        .filter(DatasetVersion.dataset_id == dataset_id)
        .order_by(DatasetVersion.version_number)
        .all()
    )
