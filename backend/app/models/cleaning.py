from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_uuid


class CleaningAction(Base, TimestampMixin):
    __tablename__ = "cleaning_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    dataset_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("dataset_versions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parameters_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(50), default="proposed", nullable=False)
    suggested_by: Mapped[str] = mapped_column(String(50), default="user", nullable=False)


class CleaningExecution(Base):
    __tablename__ = "cleaning_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    cleaning_action_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cleaning_actions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    input_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    output_version_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("dataset_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    execution_status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    preview_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
