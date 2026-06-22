from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class PreviewRequest(BaseModel):
    dataset_version_id: str
    action_type: str
    parameters: Dict[str, Any] = {}


class PreviewResult(BaseModel):
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    columns_added: List[str]
    columns_removed: List[str]
    sample_rows: List[Dict[str, Any]]


class ApplyRequest(BaseModel):
    dataset_version_id: str
    action_type: str
    parameters: Dict[str, Any] = {}
    title: str
    description: Optional[str] = None
    suggested_by: str = "user"


class CleaningActionOut(BaseModel):
    id: str
    dataset_version_id: str
    action_type: str
    title: str
    description: Optional[str]
    parameters_json: Dict[str, Any]
    status: str
    suggested_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CleaningExecutionOut(BaseModel):
    id: str
    cleaning_action_id: str
    input_version_id: str
    output_version_id: Optional[str]
    execution_status: str
    result_summary: Optional[str]
    error_message: Optional[str]
    executed_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class CleaningHistoryItem(BaseModel):
    action: CleaningActionOut
    execution: Optional[CleaningExecutionOut]
