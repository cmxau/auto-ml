from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AIInsightOut(BaseModel):
    id: str
    dataset_id: str
    dataset_version_id: Optional[str]
    insight_type: str
    content: Optional[str]
    confidence_score: Optional[float]
    metadata_json: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalyzeRequest(BaseModel):
    dataset_id: str
    dataset_version_id: Optional[str] = None
