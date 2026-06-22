from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class JobOut(BaseModel):
    id: str
    project_id: str
    dataset_id: Optional[str]
    job_type: str
    status: str
    progress_percent: Optional[float]
    error_message: Optional[str]
    output_json: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}
