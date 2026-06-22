from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "007"
down_revision = "006"


def upgrade():
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "pipeline_id",
            sa.String(36),
            sa.ForeignKey("pipelines.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column("current_node_id", sa.String(36), nullable=True),
        sa.Column("logs_json", JSONB, nullable=True),
        sa.Column("output_json", JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_table("pipeline_runs")
