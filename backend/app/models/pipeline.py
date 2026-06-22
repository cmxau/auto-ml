from typing import Optional

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_uuid


class Pipeline(Base, TimestampMixin):
    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    dataset_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)


class PipelineNode(Base, TimestampMixin):
    __tablename__ = "pipeline_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    pipeline_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipelines.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    node_type: Mapped[str] = mapped_column(String(100), nullable=False)
    node_name: Mapped[str] = mapped_column(String(255), nullable=False)
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    position_x: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    position_y: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class PipelineEdge(Base, TimestampMixin):
    __tablename__ = "pipeline_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    pipeline_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipelines.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    source_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipeline_nodes.id", ondelete="CASCADE"), nullable=False
    )
    target_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipeline_nodes.id", ondelete="CASCADE"), nullable=False
    )
