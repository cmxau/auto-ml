from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class StartTrainingRequest(BaseModel):
    dataset_version_id: str
    model_type: str
    target_column: str
    task_type: str = "classification"
    hyperparameters: Optional[Dict[str, Any]] = None


class TrainingMetricOut(BaseModel):
    id: str
    training_run_id: str
    metric_name: str
    metric_value: float
    metric_group: str

    model_config = {"from_attributes": True}


class TrainingRunOut(BaseModel):
    id: str
    project_id: str
    dataset_version_id: str
    model_type: str
    task_type: str
    hyperparameters_json: Optional[Dict[str, Any]]
    train_status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    selected_target_column: str
    artifact_id: Optional[str]
    feature_importance_json: Optional[List[Dict[str, Any]]]
    output_json: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    metrics: List[TrainingMetricOut] = []

    model_config = {"from_attributes": True}


class CompareRunsRequest(BaseModel):
    run_ids: List[str]
