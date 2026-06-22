import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.job import Job
from app.models.user import User
from app.schemas.pipeline import (
    CreatePipelineRequest,
    PipelineEdgeOut,
    PipelineNodeOut,
    PipelineOut,
    SavePipelineRequest,
)
from app.services.pipeline_service import (
    create_pipeline,
    delete_pipeline,
    get_pipeline,
    get_pipeline_edges,
    get_pipeline_nodes,
    list_pipelines,
    save_pipeline,
    validate_pipeline_in_db,
)
from app.models.pipeline_run import PipelineRun
from app.services.project_service import get_project

logger = logging.getLogger(__name__)
router = APIRouter()


def ok(data):
    return JSONResponse({"success": True, "data": data})


def _assert_pipeline_access(db: Session, pipeline_id: str, user_id: str):
    pipeline = get_pipeline(db, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    project = get_project(db, pipeline.project_id, user_id)
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")
    return pipeline


def _pipeline_with_graph(db: Session, pipeline) -> dict:
    nodes = get_pipeline_nodes(db, pipeline.id)
    edges = get_pipeline_edges(db, pipeline.id)
    data = PipelineOut.model_validate(pipeline).model_dump(mode="json")
    data["nodes"] = [PipelineNodeOut.model_validate(n).model_dump(mode="json") for n in nodes]
    data["edges"] = [PipelineEdgeOut.model_validate(e).model_dump(mode="json") for e in edges]
    return data


@router.post("/pipelines", status_code=201)
def create_pipeline_endpoint(
    body: CreatePipelineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project(db, body.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=403, detail="Project not found or access denied")

    pipeline = create_pipeline(
        db,
        project_id=body.project_id,
        name=body.name,
        description=body.description,
        dataset_id=body.dataset_id,
    )
    return ok(_pipeline_with_graph(db, pipeline))


@router.get("/projects/{project_id}/pipelines")
def list_pipelines_endpoint(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=403, detail="Project not found or access denied")

    pipelines = list_pipelines(db, project_id)
    result = []
    for p in pipelines:
        nodes = get_pipeline_nodes(db, p.id)
        edges = get_pipeline_edges(db, p.id)
        data = PipelineOut.model_validate(p).model_dump(mode="json")
        data["nodes"] = [PipelineNodeOut.model_validate(n).model_dump(mode="json") for n in nodes]
        data["edges"] = [PipelineEdgeOut.model_validate(e).model_dump(mode="json") for e in edges]
        result.append(data)
    return ok(result)


@router.get("/pipelines/{pipeline_id}")
def get_pipeline_endpoint(
    pipeline_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pipeline = _assert_pipeline_access(db, pipeline_id, current_user.id)
    return ok(_pipeline_with_graph(db, pipeline))


@router.patch("/pipelines/{pipeline_id}")
def save_pipeline_endpoint(
    pipeline_id: str,
    body: SavePipelineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_pipeline_access(db, pipeline_id, current_user.id)

    nodes = [n.model_dump(mode="json") for n in body.nodes]
    edges = [e.model_dump(mode="json") for e in body.edges]
    pipeline = save_pipeline(db, pipeline_id, nodes, edges)
    return ok(_pipeline_with_graph(db, pipeline))


@router.post("/pipelines/{pipeline_id}/validate")
def validate_pipeline_endpoint(
    pipeline_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_pipeline_access(db, pipeline_id, current_user.id)
    result = validate_pipeline_in_db(db, pipeline_id)
    return ok(result)


@router.post("/pipelines/{pipeline_id}/execute")
def execute_pipeline_endpoint(
    pipeline_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pipeline = _assert_pipeline_access(db, pipeline_id, current_user.id)

    result = validate_pipeline_in_db(db, pipeline_id)
    if not result["valid"]:
        raise HTTPException(
            status_code=422,
            detail=f"Pipeline is not valid: {'; '.join(result['errors'])}",
        )

    job = Job(
        project_id=pipeline.project_id,
        job_type="run_pipeline",
        status="queued",
        input_json={"pipeline_id": pipeline_id},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return ok({"job_id": job.id})


@router.post("/pipelines/{pipeline_id}/run", status_code=201)
def start_pipeline_run(
    pipeline_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pipeline = _assert_pipeline_access(db, pipeline_id, current_user.id)

    run = PipelineRun(pipeline_id=pipeline_id)
    db.add(run)
    db.flush()

    job = Job(
        project_id=pipeline.project_id,
        job_type="run_pipeline",
        status="queued",
        input_json={"pipeline_id": pipeline_id, "pipeline_run_id": run.id},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    from app.workers.pipeline_worker import run_pipeline_task

    try:
        task = run_pipeline_task.delay(job.id)
        job.celery_task_id = task.id
        run.logs_json = [{"note": f"Dispatched as celery task {task.id}"}]
        db.commit()
    except Exception as e:
        job.status = "failed"
        job.error_message = f"Dispatch failed: {e}"
        run.status = "failed"
        run.error_message = f"Dispatch failed: {e}"
        db.commit()

    return ok({"pipeline_run_id": run.id, "job_id": job.id})


@router.get("/pipelines/{pipeline_id}/runs")
def list_pipeline_runs(
    pipeline_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_pipeline_access(db, pipeline_id, current_user.id)
    runs = (
        db.query(PipelineRun)
        .filter(PipelineRun.pipeline_id == pipeline_id)
        .order_by(PipelineRun.created_at.desc())
        .all()
    )
    return ok(
        [
            {
                "id": r.id,
                "status": r.status,
                "current_node_id": r.current_node_id,
                "error_message": r.error_message,
                "created_at": r.created_at.isoformat(),
                "completed_at": r.completed_at.isoformat()
                if r.completed_at
                else None,
            }
            for r in runs
        ]
    )


@router.get("/pipelines/{pipeline_id}/runs/{run_id}")
def get_pipeline_run(
    pipeline_id: str,
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_pipeline_access(db, pipeline_id, current_user.id)
    run = db.get(PipelineRun, run_id)
    if not run or run.pipeline_id != pipeline_id:
        raise HTTPException(status_code=404, detail="Run not found")
    return ok(
        {
            "id": run.id,
            "status": run.status,
            "current_node_id": run.current_node_id,
            "logs_json": run.logs_json,
            "output_json": run.output_json,
            "error_message": run.error_message,
            "created_at": run.created_at.isoformat(),
            "completed_at": run.completed_at.isoformat()
            if run.completed_at
            else None,
        }
    )


@router.delete("/pipelines/{pipeline_id}", status_code=204)
def delete_pipeline_endpoint(
    pipeline_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_pipeline_access(db, pipeline_id, current_user.id)
    delete_pipeline(db, pipeline_id)
