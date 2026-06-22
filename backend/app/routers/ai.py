from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.ai_insight import AIInsight
from app.models.dataset import Dataset, DatasetVersion
from app.models.job import Job
from app.models.user import User
from app.schemas.ai import AIInsightOut, AnalyzeRequest
from app.services.project_service import get_project

router = APIRouter()


def ok(data):
    return JSONResponse({"success": True, "data": data})


def _require_openai():
    from app.config import settings
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="AI features unavailable: OPENAI_API_KEY not configured."
        )


def _assert_dataset_access(db: Session, dataset_id: str, user_id: str) -> Dataset:
    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    project = get_project(db, ds.project_id, user_id)
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")
    return ds


@router.post("/analyze")
def trigger_analysis(
    body: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_openai()
    ds = _assert_dataset_access(db, body.dataset_id, current_user.id)
    if ds.status != "ready":
        raise HTTPException(status_code=422, detail="Dataset must be profiled before AI analysis")

    if body.dataset_version_id:
        version_id = body.dataset_version_id
    else:
        latest = (
            db.query(DatasetVersion)
            .filter(DatasetVersion.dataset_id == body.dataset_id)
            .order_by(DatasetVersion.version_number.desc())
            .first()
        )
        if not latest:
            raise HTTPException(status_code=422, detail="No dataset version found")
        version_id = latest.id

    job = Job(
        project_id=ds.project_id,
        dataset_id=body.dataset_id,
        job_type="analyze_dataset",
        status="queued",
        input_json={"dataset_id": body.dataset_id, "dataset_version_id": version_id},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    from app.workers.ai_worker import analyze_dataset_task
    try:
        task = analyze_dataset_task.delay(job.id)
        job.celery_task_id = task.id
        db.commit()
    except Exception as e:
        job.status = "failed"
        job.error_message = f"Failed to dispatch: {e}"
        db.commit()

    return ok({"job_id": job.id})


@router.get("/insights/{dataset_id}")
def get_insights(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_dataset_access(db, dataset_id, current_user.id)
    insights = (
        db.query(AIInsight)
        .filter(AIInsight.dataset_id == dataset_id)
        .order_by(AIInsight.created_at.desc())
        .all()
    )
    return ok([AIInsightOut.model_validate(i).model_dump(mode="json") for i in insights])


class TranslateCommandRequest(BaseModel):
    dataset_id: str
    command: str


class TranslateTrainingRequest(BaseModel):
    dataset_id: str
    command: str


@router.post("/translate-training-command")
def translate_training_command(
    body: TranslateTrainingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_openai()
    from app.services.ai_service import _openai_chat

    _assert_dataset_access(db, body.dataset_id, current_user.id)

    system_prompt = (
        "You are an ML assistant. Parse natural language training requests and return structured JSON."
    )
    user_prompt = (
        "Parse this natural language training request and return JSON with:\n"
        "- task_type: \"classification\" or \"regression\"\n"
        "- model_type: one of [\"random_forest\", \"logistic_regression\", \"gradient_boosting\", "
        "\"xgboost\", \"svm\", \"random_forest_regressor\", \"linear_regression\", "
        "\"gradient_boosting_regressor\", \"xgboost_regressor\"]\n"
        "- target_column: string (column name to predict)\n"
        "- confidence: 0-1\n\n"
        f"Command: {body.command}\n\n"
        "Return only valid JSON, no markdown."
    )

    try:
        response = _openai_chat(system_prompt, user_prompt)
        import json
        result = json.loads(response.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI translation failed: {e}")

    return ok(result)


@router.post("/translate-cleaning-command")
def translate_cleaning_command_endpoint(
    body: TranslateCommandRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_openai()
    from app.models.profile import DatasetProfile
    from app.models.dataset import DatasetVersion
    from app.services.ai_service import translate_cleaning_command

    _assert_dataset_access(db, body.dataset_id, current_user.id)

    latest_version = (
        db.query(DatasetVersion)
        .filter(DatasetVersion.dataset_id == body.dataset_id)
        .order_by(DatasetVersion.version_number.desc())
        .first()
    )
    if not latest_version:
        raise HTTPException(status_code=422, detail="No dataset version found")

    profile_row = (
        db.query(DatasetProfile)
        .filter(DatasetProfile.dataset_version_id == latest_version.id)
        .order_by(DatasetProfile.created_at.desc())
        .first()
    )
    if not profile_row or not profile_row.profile_json:
        raise HTTPException(status_code=422, detail="Dataset must be profiled first")

    schema = profile_row.profile_json.get("columns", [])

    try:
        result = translate_cleaning_command(body.command, schema)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI translation failed: {e}")

    return ok(result)


class RecommendPipelineRequest(BaseModel):
    dataset_id: str
    project_id: str


@router.post("/recommend-pipeline", status_code=201)
def recommend_pipeline(
    body: RecommendPipelineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_openai()
    _assert_dataset_access(db, body.dataset_id, current_user.id)

    project = get_project(db, body.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=403, detail="Project not found or access denied")

    ds = db.get(Dataset, body.dataset_id)

    from app.models.profile import DatasetColumnProfile, DatasetProfile

    latest_version = (
        db.query(DatasetVersion)
        .filter(DatasetVersion.dataset_id == body.dataset_id)
        .order_by(DatasetVersion.version_number.desc())
        .first()
    )
    if not latest_version:
        raise HTTPException(status_code=422, detail="No dataset version found")

    profile_row = (
        db.query(DatasetProfile)
        .filter(DatasetProfile.dataset_version_id == latest_version.id)
        .order_by(DatasetProfile.created_at.desc())
        .first()
    )
    col_profiles = (
        db.query(DatasetColumnProfile)
        .filter(DatasetColumnProfile.dataset_profile_id == profile_row.id)
        .all()
    ) if profile_row else []

    col_summary = [
        {"name": c.column_name, "type": c.data_type, "missing": c.missing_count or 0}
        for c in col_profiles
    ]

    # Check for existing AI insights
    insight = (
        db.query(AIInsight)
        .filter(AIInsight.dataset_id == body.dataset_id)
        .order_by(AIInsight.created_at.desc())
        .first()
    )
    insight_text = ""
    if insight and insight.metadata_json:
        task = insight.metadata_json.get("task_type", "")
        target = insight.metadata_json.get("target_column", "")
        if task or target:
            insight_text = f"\nAI analysis suggests: task_type={task}, target_column={target}"

    system_prompt = (
        "You are an ML pipeline designer. Given a dataset profile, return a JSON pipeline "
        "recommendation with nodes and edges. Return ONLY valid JSON, no markdown.\n"
        "Node types available: input, clean, split, train\n"
        "Each node has: node_type, node_name, config_json, position_x, position_y\n"
        "Each edge has: source_idx (index into nodes array), target_idx (index into nodes array)\n"
        "config_json for input node: {\"dataset_version_id\": \"<version_id>\"}\n"
        "config_json for clean node: {} (empty)\n"
        "config_json for split node: {\"test_size\": \"0.2\"}\n"
        "config_json for train node: {\"model_type\": \"<model>\", \"task_type\": \"<classification|regression>\", \"target_column\": \"<col>\"}\n"
        "VALID model_type values for classification (use exactly as written, snake_case):\n"
        "  random_forest, logistic_regression, gradient_boosting, xgboost, svm\n"
        "VALID model_type values for regression (use exactly as written, snake_case):\n"
        "  random_forest_regressor, linear_regression, gradient_boosting_regressor, xgboost_regressor\n"
        "Position nodes left to right, each 250px apart, y=200.\n"
        "Return: {\"pipeline_name\": \"...\", \"nodes\": [...], \"edges\": [...]}"
    )

    cols_with_nulls = [c["name"] for c in col_summary if c["missing"] > 0]
    user_prompt = (
        f"Dataset: {ds.name}\n"
        f"Rows: {latest_version.row_count}, Columns: {latest_version.column_count}\n"
        f"Columns: {[c['name'] + ' (' + c['type'] + ')' for c in col_summary]}\n"
        f"Columns with missing values: {cols_with_nulls}\n"
        f"Dataset version ID to use: {latest_version.id}\n"
        f"{insight_text}\n"
        "Design an optimal ML pipeline. Include a clean node only if there are missing values. "
        "Pick the best model for the apparent task type. Set target_column to the most likely target."
    )

    from app.services.ai_service import _openai_chat
    try:
        response = _openai_chat(system_prompt, user_prompt)
        import json
        rec = json.loads(response.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI recommendation failed: {e}")

    # Create pipeline + nodes + edges
    from app.models.pipeline import Pipeline, PipelineEdge, PipelineNode
    from app.models.base import new_uuid

    pipeline = Pipeline(
        project_id=body.project_id,
        name=rec.get("pipeline_name", f"AI Pipeline — {ds.name}"),
        description="AI-recommended pipeline",
        dataset_id=body.dataset_id,
    )
    db.add(pipeline)
    db.flush()

    nodes_data = rec.get("nodes", [])
    node_ids = []
    for node in nodes_data:
        nid = new_uuid()
        node_ids.append(nid)
        db.add(PipelineNode(
            id=nid,
            pipeline_id=pipeline.id,
            node_type=node.get("node_type", "input"),
            node_name=node.get("node_name", node.get("node_type", "node")),
            config_json=node.get("config_json", {}),
            position_x=node.get("position_x", 100),
            position_y=node.get("position_y", 200),
        ))
    db.flush()

    for edge in rec.get("edges", []):
        src_idx = int(edge.get("source_idx", 0))
        tgt_idx = int(edge.get("target_idx", 1))
        if src_idx < len(node_ids) and tgt_idx < len(node_ids):
            db.add(PipelineEdge(
                pipeline_id=pipeline.id,
                source_node_id=node_ids[src_idx],
                target_node_id=node_ids[tgt_idx],
            ))

    db.commit()
    return ok({"pipeline_id": pipeline.id, "pipeline_name": pipeline.name})
