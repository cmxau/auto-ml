import logging
from collections import deque
from datetime import datetime, timezone

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=1,
    name="app.workers.pipeline_worker.run_pipeline_task",
)
def run_pipeline_task(self, job_id: str):
    from app.database import SessionLocal
    from app.models.dataset import Dataset, DatasetVersion  # noqa: F401 — registers FK targets
    from app.models.job import Job
    from app.models.pipeline import Pipeline, PipelineEdge, PipelineNode
    from app.models.pipeline_run import PipelineRun
    from app.models.project import Project  # noqa: F401

    db = SessionLocal()
    job = None
    run = None
    try:
        job = db.get(Job, job_id)
        if not job:
            logger.error("Pipeline job %s not found", job_id)
            return

        job.status = "running"
        db.commit()

        input_data = job.input_json or {}
        pipeline_run_id = input_data["pipeline_run_id"]

        run = db.get(PipelineRun, pipeline_run_id)
        if not run:
            raise ValueError(f"PipelineRun {pipeline_run_id} not found")

        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        run.logs_json = []
        db.commit()

        pipeline = db.get(Pipeline, run.pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline {run.pipeline_id} not found")

        nodes = (
            db.query(PipelineNode)
            .filter(PipelineNode.pipeline_id == pipeline.id)
            .all()
        )
        edges = (
            db.query(PipelineEdge)
            .filter(PipelineEdge.pipeline_id == pipeline.id)
            .all()
        )

        # Build adjacency for topological sort
        adj = {n.id: [] for n in nodes}
        in_degree = {n.id: 0 for n in nodes}
        for e in edges:
            adj[e.source_node_id].append(e.target_node_id)
            in_degree[e.target_node_id] = in_degree.get(e.target_node_id, 0) + 1

        # Topological sort (Kahn's algorithm)
        queue = deque([n.id for n in nodes if in_degree[n.id] == 0])
        order = []
        while queue:
            nid = queue.popleft()
            order.append(nid)
            for succ in adj[nid]:
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        if len(order) != len(nodes):
            raise ValueError("Pipeline has a cycle — cannot execute")

        node_map = {n.id: n for n in nodes}
        logs = []
        outputs = {}

        for nid in order:
            node = node_map[nid]
            run.current_node_id = nid
            db.commit()

            config = node.config_json or {}
            logs.append({"node_id": nid, "type": node.node_type, "status": "running"})

            if node.node_type == "input":
                dataset_version_id = config.get("dataset_version_id")
                if not dataset_version_id:
                    raise ValueError(
                        f"Input node {nid} missing dataset_version_id in config"
                    )
                outputs[nid] = {"dataset_version_id": dataset_version_id}
                logs[-1]["status"] = "succeeded"

            elif node.node_type in ("clean", "transform", "feature_engineering"):
                # MVP: pass-through with log warning
                parent_outputs = [
                    outputs[e.source_node_id]
                    for e in edges
                    if e.target_node_id == nid and e.source_node_id in outputs
                ]
                parent_version_id = (
                    parent_outputs[0].get("dataset_version_id")
                    if parent_outputs
                    else None
                )
                outputs[nid] = {"dataset_version_id": parent_version_id}
                logs[-1]["status"] = "skipped"
                logs[-1]["note"] = (
                    f"{node.node_type} nodes are pass-through in pipeline MVP"
                )

            elif node.node_type == "split":
                parent_outputs = [
                    outputs[e.source_node_id]
                    for e in edges
                    if e.target_node_id == nid and e.source_node_id in outputs
                ]
                parent_version_id = next(
                    (po.get("dataset_version_id") for po in parent_outputs if po.get("dataset_version_id")),
                    config.get("dataset_version_id"),
                )
                outputs[nid] = {
                    "dataset_version_id": parent_version_id,
                    "test_size": config.get("test_size", 0.2),
                }
                logs[-1]["status"] = "succeeded"

            elif node.node_type == "train":
                parent_outputs = [
                    outputs[e.source_node_id]
                    for e in edges
                    if e.target_node_id == nid and e.source_node_id in outputs
                ]
                dataset_version_id = None
                for po in parent_outputs:
                    if po.get("dataset_version_id"):
                        dataset_version_id = po["dataset_version_id"]
                        break
                # Fall back to dataset_version_id set directly on this node's config
                if not dataset_version_id:
                    dataset_version_id = config.get("dataset_version_id")
                if not dataset_version_id:
                    raise ValueError(
                        f"Train node {nid} has no dataset_version_id — "
                        "connect it to an Input node or set dataset_version_id in its config"
                    )

                model_type = config.get("model_type", "random_forest")
                target_column = config.get("target_column")
                task_type = config.get("task_type", "classification")
                if not target_column:
                    raise ValueError(
                        f"Train node {nid} missing target_column in config"
                    )

                # Dispatch training job — replicate training router pattern exactly
                from app.models.training import TrainingRun

                training_run = TrainingRun(
                    project_id=pipeline.project_id,
                    dataset_version_id=dataset_version_id,
                    model_type=model_type,
                    task_type=task_type,
                    selected_target_column=target_column,
                    hyperparameters_json=config.get("hyperparameters", {}),
                    train_status="queued",
                )
                db.add(training_run)
                db.flush()

                training_job = Job(
                    project_id=pipeline.project_id,
                    job_type="train_model",
                    status="queued",
                    input_json={"training_run_id": training_run.id},
                )
                db.add(training_job)
                db.commit()
                db.refresh(training_job)

                from app.workers.training_worker import train_model_task

                task = train_model_task.delay(training_job.id)
                training_job.celery_task_id = task.id
                db.commit()

                outputs[nid] = {
                    "training_run_id": training_run.id,
                    "job_id": training_job.id,
                }
                logs[-1]["status"] = "dispatched"
                logs[-1]["training_run_id"] = training_run.id
                logs[-1]["job_id"] = training_job.id

            else:
                logs[-1]["status"] = "skipped"
                logs[-1]["note"] = (
                    f"Node type '{node.node_type}' not yet implemented"
                )

            run.logs_json = logs
            db.commit()

        run.status = "succeeded"
        run.output_json = outputs
        run.completed_at = datetime.now(timezone.utc)
        run.current_node_id = None
        run.logs_json = logs
        db.commit()

        job.status = "succeeded"
        db.commit()

        logger.info("Pipeline run %s succeeded (job %s)", pipeline_run_id, job_id)

    except Exception as exc:
        logger.exception("Pipeline job %s failed: %s", job_id, exc)
        if run is not None:
            run.status = "failed"
            run.error_message = str(exc)
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
        if job is not None:
            job.status = "failed"
            job.error_message = str(exc)
            db.commit()
    finally:
        db.close()
