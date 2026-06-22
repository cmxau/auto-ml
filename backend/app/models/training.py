from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_uuid


class TrainingRun(Base, TimestampMixin):
    __tablename__ = "training_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    dataset_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("dataset_versions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    model_type: Mapped[str] = mapped_column(String(100), nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    hyperparameters_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    train_status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    selected_target_column: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    feature_importance_json: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    output_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class TrainingMetric(Base, TimestampMixin):
    __tablename__ = "training_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    training_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("training_runs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    metric_group: Mapped[str] = mapped_column(String(50), nullable=False)


class Artifact(Base, TimestampMixin):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    dataset_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True
    )
    training_run_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("training_runs.id", ondelete="SET NULL"), nullable=True
    )
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(200), nullable=False)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
