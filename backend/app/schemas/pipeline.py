from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CreatePipelineRequest(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = None
    dataset_id: Optional[str] = None


class SaveNodeIn(BaseModel):
    id: Optional[str] = None
    node_type: str
    node_name: str = ""
    config_json: Dict[str, Any] = {}
    position_x: Optional[float] = None
    position_y: Optional[float] = None


class SaveEdgeIn(BaseModel):
    source_node_id: str
    target_node_id: str


class SavePipelineRequest(BaseModel):
    nodes: List[SaveNodeIn]
    edges: List[SaveEdgeIn]


class PipelineNodeOut(BaseModel):
    id: str
    pipeline_id: str
    node_type: str
    node_name: str
    config_json: Dict[str, Any]
    position_x: Optional[float]
    position_y: Optional[float]

    model_config = {"from_attributes": True}


class PipelineEdgeOut(BaseModel):
    id: str
    pipeline_id: str
    source_node_id: str
    target_node_id: str

    model_config = {"from_attributes": True}


class PipelineOut(BaseModel):
    id: str
    project_id: str
    dataset_id: Optional[str]
    name: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    nodes: List[PipelineNodeOut] = []
    edges: List[PipelineEdgeOut] = []

    model_config = {"from_attributes": True}
