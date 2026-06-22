import io
import os
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, Response, StreamingResponse as _StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.database import get_db
from app.models.dataset import DatasetVersion
from app.models.profile import DatasetColumnProfile, DatasetProfile
from app.models.user import User
from app.schemas.dataset import DatasetOut, DatasetVersionOut
from app.services.dataset_service import (
    create_dataset_with_version,
    create_profiling_job,
    get_dataset,
    get_dataset_versions,
    list_datasets,
    validate_extension,
)
from app.services.project_service import get_project
from app.services.storage_service import storage

router = APIRouter()


def ok(data, status_code: int = 200):
    return JSONResponse({"success": True, "data": data}, status_code=status_code)


def _assert_project_access(db: Session, project_id: str, user_id: str):
    project = get_project(db, project_id, user_id)
    if not project:
        raise HTTPException(status_code=403, detail="Project not found or access denied")
    return project


def _safe_filename(filename: str) -> str:
    """Strip path components and unsafe characters from filenames."""
    return os.path.basename(filename).replace(" ", "_")


@router.post("/datasets/upload", status_code=201)
async def upload_dataset(
    project_id: str = Form(...),
    file: UploadFile = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import pandas as pd

    _assert_project_access(db, project_id, current_user.id)

    ext = validate_extension(file.filename or "")
    if not ext:
        raise HTTPException(status_code=422, detail="Unsupported file type. Use CSV, XLSX, or JSON.")

    # Read file in chunks, rejecting early if too large
    MAX_CHUNK = 256 * 1024  # 256 KB chunks
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    chunks = []
    total_size = 0
    while True:
        chunk = await file.read(MAX_CHUNK)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_bytes:
            raise HTTPException(status_code=422, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit")
        chunks.append(chunk)
    content = b"".join(chunks)

    # Column count guard — parse headers only, no full read
    try:
        if ext == "csv":
            df_peek = pd.read_csv(io.BytesIO(content), nrows=0)
        elif ext == "xlsx":
            df_peek = pd.read_excel(io.BytesIO(content), nrows=0)
        elif ext == "json":
            df_peek = pd.read_json(io.BytesIO(content)).iloc[:0]
        else:
            df_peek = pd.read_csv(io.BytesIO(content), nrows=0)
        col_count = len(df_peek.columns)
        if col_count > 500:
            raise HTTPException(
                status_code=422,
                detail=f"File has {col_count} columns. Maximum supported is 500.",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # If peek fails, let profiling worker catch the real error

    key = f"datasets/{project_id}/{uuid.uuid4()}/{_safe_filename(file.filename or 'dataset')}"
    filename = file.filename or "dataset"
    name = filename.rsplit(".", 1)[0]

    # Create DB records first (so we have IDs), storage_uri set to key
    dataset, version = create_dataset_with_version(
        db,
        project_id=project_id,
        name=name,
        source_type="local_upload",
        original_file_name=filename,
        file_format=ext,
        storage_uri=key,
    )

    # Upload to storage after DB records exist
    try:
        storage.upload_file(io.BytesIO(content), key, file.content_type or "application/octet-stream")
    except Exception as e:
        dataset.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail="Storage upload failed")

    job = create_profiling_job(db, project_id, dataset.id, version.id)

    # Dispatch Celery task with failure handling
    from app.workers.profiling_worker import profile_dataset_task
    try:
        task = profile_dataset_task.delay(job.id)
        job.celery_task_id = task.id
    except Exception as e:
        job.status = "failed"
        job.error_message = f"Failed to dispatch profiling task: {e}"
    db.commit()

    return ok({"dataset_id": dataset.id, "job_id": job.id}, status_code=201)


@router.get("/projects/{project_id}/datasets")
def list_datasets_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_project_access(db, project_id, current_user.id)
    datasets = list_datasets(db, project_id)
    return ok([DatasetOut.model_validate(d).model_dump(mode="json") for d in datasets])


@router.delete("/datasets/{dataset_id}", status_code=204)
def delete_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ds = get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _assert_project_access(db, ds.project_id, current_user.id)
    ds.status = "deleted"
    db.commit()
    return Response(status_code=204)


@router.post("/datasets/{dataset_id}/replace", status_code=200)
async def replace_dataset_file(
    dataset_id: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ds = get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _assert_project_access(db, ds.project_id, current_user.id)

    ext = validate_extension(file.filename or "")
    if not ext:
        raise HTTPException(status_code=422, detail="Unsupported file type.")

    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=422, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit")

    # Count existing versions to get next version_number
    existing = get_dataset_versions(db, dataset_id)
    next_version_num = len(existing)  # 0-indexed so len = next number
    key = f"datasets/{dataset_id}/v{next_version_num}/{_safe_filename(file.filename or 'dataset')}"

    try:
        storage.upload_file(io.BytesIO(content), key, file.content_type or "application/octet-stream")
    except Exception:
        raise HTTPException(status_code=500, detail="Storage upload failed")

    new_version = DatasetVersion(
        dataset_id=dataset_id,
        version_number=next_version_num,
        storage_uri=key,
    )
    db.add(new_version)
    ds.file_format = ext
    ds.original_file_name = file.filename or ds.original_file_name
    ds.status = "queued"
    db.flush()

    job = create_profiling_job(db, ds.project_id, dataset_id, new_version.id)
    db.commit()

    from app.workers.profiling_worker import profile_dataset_task
    try:
        task = profile_dataset_task.delay(job.id)
        job.celery_task_id = task.id
        db.commit()
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()

    return ok({"dataset_id": dataset_id, "version_id": new_version.id, "job_id": job.id})


@router.get("/datasets/{dataset_id}")
def get_dataset_endpoint(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ds = get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _assert_project_access(db, ds.project_id, current_user.id)
    return ok(DatasetOut.model_validate(ds).model_dump(mode="json"))


@router.get("/datasets/{dataset_id}/versions")
def get_versions(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ds = get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _assert_project_access(db, ds.project_id, current_user.id)
    versions = get_dataset_versions(db, dataset_id)
    return ok([DatasetVersionOut.model_validate(v).model_dump(mode="json") for v in versions])


@router.delete("/datasets/{dataset_id}/versions/{version_id}", status_code=204)
def delete_dataset_version(
    dataset_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ds = get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _assert_project_access(db, ds.project_id, current_user.id)
    version = db.get(DatasetVersion, version_id)
    if not version or version.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Version not found")
    if version.version_number == 0:
        raise HTTPException(status_code=422, detail="Cannot delete the original version (v0)")
    db.delete(version)
    db.commit()
    return Response(status_code=204)


@router.get("/datasets/{dataset_id}/versions/{version_id}/preview")
def preview_dataset_version(
    dataset_id: str,
    version_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ds = get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _assert_project_access(db, ds.project_id, current_user.id)

    version = db.get(DatasetVersion, version_id)
    if not version or version.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Version not found")

    from app.services.storage_service import resolve_format
    content = storage.download_file(version.storage_uri)
    df = _read_dataframe(content, resolve_format(version.storage_uri, ds.file_format))
    offset = (page - 1) * page_size
    chunk = df.iloc[offset: offset + page_size]
    return ok({
        "columns": list(df.columns),
        "rows": chunk.fillna("").astype(str).values.tolist(),
        "total_rows": len(df),
        "page": page,
        "page_size": page_size,
    })


@router.get("/datasets/{dataset_id}/versions/{version_id}/export")
def export_dataset_version(
    dataset_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ds = get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _assert_project_access(db, ds.project_id, current_user.id)
    version = db.get(DatasetVersion, version_id)
    if not version or version.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Version not found")

    from app.services.storage_service import resolve_format
    content = storage.download_file(version.storage_uri)
    fmt = resolve_format(version.storage_uri, ds.file_format)

    if fmt != "csv":
        import pandas as pd
        if fmt == "xlsx":
            df = pd.read_excel(io.BytesIO(content))
        else:
            df = pd.read_json(io.BytesIO(content))
        buf = io.BytesIO()
        df.to_csv(buf, index=False)
        content = buf.getvalue()

    base = ds.original_file_name.rsplit(".", 1)[0]
    filename = f"{base}_v{version.version_number}.csv"
    return _StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/datasets/{dataset_id}/preview")
def preview_dataset(
    dataset_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ds = get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _assert_project_access(db, ds.project_id, current_user.id)

    if ds.status != "ready":
        return ok({"columns": [], "rows": [], "total_rows": 0, "status": ds.status})

    content = storage.download_file(ds.storage_uri)
    df = _read_dataframe(content, ds.file_format)
    offset = (page - 1) * page_size
    chunk = df.iloc[offset: offset + page_size]
    return ok({
        "columns": list(df.columns),
        "rows": chunk.fillna("").astype(str).values.tolist(),
        "total_rows": len(df),
        "page": page,
        "page_size": page_size,
    })


@router.get("/datasets/{dataset_id}/profile")
def get_profile(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ds = get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _assert_project_access(db, ds.project_id, current_user.id)

    version = (
        db.query(DatasetVersion)
        .filter(DatasetVersion.dataset_id == dataset_id)
        .order_by(DatasetVersion.version_number.desc())
        .first()
    )
    if not version:
        return ok(None)

    profile = (
        db.query(DatasetProfile)
        .filter(DatasetProfile.dataset_version_id == version.id)
        .order_by(DatasetProfile.created_at.desc())
        .first()
    )
    if not profile:
        return ok(None)

    col_profiles = (
        db.query(DatasetColumnProfile)
        .filter(DatasetColumnProfile.dataset_profile_id == profile.id)
        .all()
    )

    return ok({
        "row_count": ds.row_count,
        "column_count": ds.column_count,
        "missing_value_count": profile.missing_value_count,
        "duplicate_row_count": profile.duplicate_row_count,
        "numeric_column_count": profile.numeric_column_count,
        "categorical_column_count": profile.categorical_column_count,
        "column_profiles": [
            {
                "column_name": c.column_name,
                "data_type": c.data_type,
                "missing_count": c.missing_count,
                "unique_count": c.unique_count,
                "mean_value": c.mean_value,
                "std_value": c.std_value,
                "min_value": c.min_value,
                "max_value": c.max_value,
                "top_values": c.top_values_json or [],
                "example_values": c.example_values_json or [],
                "high_cardinality_flag": c.high_cardinality_flag,
            }
            for c in col_profiles
        ],
    })


@router.get("/datasets/{dataset_id}/versions/{version_id}/profile")
def get_version_profile(
    dataset_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ds = get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _assert_project_access(db, ds.project_id, current_user.id)

    version = db.get(DatasetVersion, version_id)
    if not version or version.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Version not found")

    profile = (
        db.query(DatasetProfile)
        .filter(DatasetProfile.dataset_version_id == version_id)
        .order_by(DatasetProfile.created_at.desc())
        .first()
    )
    if not profile:
        return ok(None)

    col_profiles = (
        db.query(DatasetColumnProfile)
        .filter(DatasetColumnProfile.dataset_profile_id == profile.id)
        .all()
    )

    return ok({
        "version_number": version.version_number,
        "row_count": version.row_count,
        "column_count": version.column_count,
        "missing_value_count": profile.missing_value_count,
        "duplicate_row_count": profile.duplicate_row_count,
        "numeric_column_count": profile.numeric_column_count,
        "categorical_column_count": profile.categorical_column_count,
        "column_profiles": [
            {
                "column_name": c.column_name,
                "data_type": c.data_type,
                "missing_count": c.missing_count,
                "unique_count": c.unique_count,
                "mean_value": c.mean_value,
                "std_value": c.std_value,
                "min_value": c.min_value,
                "max_value": c.max_value,
            }
            for c in col_profiles
        ],
    })


def _read_dataframe(content: bytes, fmt: str):
    import pandas as pd
    try:
        if fmt == "csv":
            return pd.read_csv(io.BytesIO(content))
        elif fmt == "xlsx":
            return pd.read_excel(io.BytesIO(content))
        elif fmt == "json":
            return pd.read_json(io.BytesIO(content))
        raise ValueError(f"Unknown format: {fmt}")
    except (ValueError, Exception) as e:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {e}")
