from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class EdaResultOut(BaseModel):
    id: str
    dataset_version_id: str
    status: str
    charts_json: Optional[List[Dict[str, Any]]]
    error_message: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
