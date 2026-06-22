"""add training_runs, training_metrics, artifacts

Revision ID: 004
Revises: 003
Create Date: 2026-06-16 00:03:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'training_runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36),
                  sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dataset_version_id', sa.String(36),
                  sa.ForeignKey('dataset_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model_type', sa.String(100), nullable=False),
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('hyperparameters_json', postgresql.JSONB, nullable=True),
        sa.Column('train_status', sa.String(50), nullable=False, server_default='queued'),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('selected_target_column', sa.String(255), nullable=False),
        sa.Column('artifact_id', sa.String(36), nullable=True),
        sa.Column('feature_importance_json', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_training_runs_project_id', 'training_runs', ['project_id'])
    op.create_index('ix_training_runs_dataset_version_id', 'training_runs', ['dataset_version_id'])

    op.create_table(
        'training_metrics',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('training_run_id', sa.String(36),
                  sa.ForeignKey('training_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('metric_value', sa.Float, nullable=False),
        sa.Column('metric_group', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_training_metrics_training_run_id', 'training_metrics', ['training_run_id'])

    op.create_table(
        'artifacts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36),
                  sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dataset_id', sa.String(36),
                  sa.ForeignKey('datasets.id', ondelete='SET NULL'), nullable=True),
        sa.Column('training_run_id', sa.String(36),
                  sa.ForeignKey('training_runs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('artifact_type', sa.String(100), nullable=False),
        sa.Column('storage_uri', sa.String(1000), nullable=False),
        sa.Column('file_name', sa.String(500), nullable=False),
        sa.Column('mime_type', sa.String(200), nullable=False),
        sa.Column('size_bytes', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_artifacts_project_id', 'artifacts', ['project_id'])


def downgrade() -> None:
    op.drop_table('artifacts')
    op.drop_table('training_metrics')
    op.drop_table('training_runs')
