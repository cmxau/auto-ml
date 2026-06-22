from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_uuid


class DatasetProfile(Base, TimestampMixin):
    __tablename__ = "dataset_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    dataset_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    summary_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    missing_value_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duplicate_row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    numeric_column_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    categorical_column_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class DatasetColumnProfile(Base, TimestampMixin):
    __tablename__ = "dataset_column_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    dataset_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("dataset_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str] = mapped_column(String(50), nullable=False)
    missing_count: Mapped[int] = mapped_column(Integer, default=0)
    unique_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mean_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    std_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    top_values_json: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    example_values_json: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    high_cardinality_flag: Mapped[bool] = mapped_column(default=False)
