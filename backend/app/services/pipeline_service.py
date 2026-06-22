from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.base import new_uuid
from app.models.pipeline import Pipeline, PipelineEdge, PipelineNode


def _has_cycle(node_ids: List[str], edges: List[Dict[str, str]]) -> bool:
    """Detect cycles in a directed graph using DFS."""
    adjacency: Dict[str, List[str]] = {nid: [] for nid in node_ids}
    for e in edges:
        src = e["source_node_id"]
        if src in adjacency:
            adjacency[src].append(e["target_node_id"])

    visited: set = set()
    rec_stack: set = set()

    def dfs(node_id: str) -> bool:
        visited.add(node_id)
        rec_stack.add(node_id)
        for neighbor in adjacency.get(node_id, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True
        rec_stack.discard(node_id)
        return False

    for nid in node_ids:
        if nid not in visited:
            if dfs(nid):
                return True
    return False


def validate_graph(
    nodes: List[Dict[str, str]], edges: List[Dict[str, str]]
) -> Dict[str, Any]:
    """Validate a pipeline graph. Pure function, no DB.

    nodes: list of {id, node_type}
    edges: list of {source_node_id, target_node_id}
    Returns: {valid: bool, errors: list[str]}
    """
    errors: List[str] = []

    if not nodes:
        errors.append("Pipeline must have at least one node.")
        return {"valid": False, "errors": errors}

    node_ids = [n["id"] for n in nodes]
    node_id_set = set(node_ids)

    for e in edges:
        if e["source_node_id"] not in node_id_set:
            errors.append(
                f"Edge references unknown source node '{e['source_node_id']}'."
            )
        if e["target_node_id"] not in node_id_set:
            errors.append(
                f"Edge references unknown target node '{e['target_node_id']}'."
            )

    if errors:
        return {"valid": False, "errors": errors}

    if _has_cycle(node_ids, edges):
        errors.append(
            "Pipeline graph contains a cycle. Pipelines must be directed acyclic graphs (DAGs)."
        )

    return {"valid": len(errors) == 0, "errors": errors}


def create_pipeline(
    db: Session,
    project_id: str,
    name: str,
    description: Optional[str] = None,
    dataset_id: Optional[str] = None,
) -> Pipeline:
    pipeline = Pipeline(
        project_id=project_id,
        name=name,
        description=description,
        dataset_id=dataset_id,
    )
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)
    return pipeline


def get_pipeline(db: Session, pipeline_id: str) -> Optional[Pipeline]:
    return db.get(Pipeline, pipeline_id)


def list_pipelines(db: Session, project_id: str) -> List[Pipeline]:
    return (
        db.query(Pipeline)
        .filter(Pipeline.project_id == project_id)
        .order_by(Pipeline.created_at.desc())
        .all()
    )


def get_pipeline_nodes(db: Session, pipeline_id: str) -> List[PipelineNode]:
    return (
        db.query(PipelineNode)
        .filter(PipelineNode.pipeline_id == pipeline_id)
        .all()
    )


def get_pipeline_edges(db: Session, pipeline_id: str) -> List[PipelineEdge]:
    return (
        db.query(PipelineEdge)
        .filter(PipelineEdge.pipeline_id == pipeline_id)
        .all()
    )


def save_pipeline(
    db: Session,
    pipeline_id: str,
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
) -> Pipeline:
    """Replace all nodes and edges for a pipeline atomically."""
    # Delete edges first (FK: edges reference nodes)
    db.query(PipelineEdge).filter(PipelineEdge.pipeline_id == pipeline_id).delete()
    db.query(PipelineNode).filter(PipelineNode.pipeline_id == pipeline_id).delete()
    db.flush()

    for n in nodes:
        node_id = n.get("id") or new_uuid()
        db.add(PipelineNode(
            id=node_id,
            pipeline_id=pipeline_id,
            node_type=n["node_type"],
            node_name=n.get("node_name") or n["node_type"],
            config_json=n.get("config_json") or {},
            position_x=n.get("position_x"),
            position_y=n.get("position_y"),
        ))

    db.flush()

    for e in edges:
        db.add(PipelineEdge(
            pipeline_id=pipeline_id,
            source_node_id=e["source_node_id"],
            target_node_id=e["target_node_id"],
        ))

    pipeline = db.get(Pipeline, pipeline_id)
    pipeline.status = "draft"
    db.commit()
    db.refresh(pipeline)
    return pipeline


def validate_pipeline_in_db(db: Session, pipeline_id: str) -> Dict[str, Any]:
    """Validate the saved pipeline and update its status field."""
    nodes = get_pipeline_nodes(db, pipeline_id)
    edges = get_pipeline_edges(db, pipeline_id)

    node_dicts = [{"id": n.id, "node_type": n.node_type} for n in nodes]
    edge_dicts = [
        {"source_node_id": e.source_node_id, "target_node_id": e.target_node_id}
        for e in edges
    ]

    result = validate_graph(node_dicts, edge_dicts)

    pipeline = db.get(Pipeline, pipeline_id)
    if pipeline:
        pipeline.status = "valid" if result["valid"] else "invalid"
        db.commit()

    return result


def delete_pipeline(db: Session, pipeline_id: str) -> None:
    db.query(PipelineEdge).filter(PipelineEdge.pipeline_id == pipeline_id).delete()
    db.query(PipelineNode).filter(PipelineNode.pipeline_id == pipeline_id).delete()
    pipeline = db.get(Pipeline, pipeline_id)
    if pipeline:
        db.delete(pipeline)
    db.commit()
