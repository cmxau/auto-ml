from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DatasetOut(BaseModel):
    id: str
    name: str
    source_type: str
    original_file_name: str
    file_format: str
    row_count: Optional[int]
    column_count: Optional[int]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetVersionOut(BaseModel):
    id: str
    dataset_id: str
    version_number: int
    row_count: Optional[int]
    column_count: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}
