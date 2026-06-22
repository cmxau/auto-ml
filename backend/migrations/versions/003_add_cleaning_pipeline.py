"""add cleaning_actions, cleaning_executions, pipelines, pipeline_nodes, pipeline_edges

Revision ID: 003
Revises: 002
Create Date: 2026-06-16 00:02:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'cleaning_actions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('dataset_version_id', sa.String(36),
                  sa.ForeignKey('dataset_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('parameters_json', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('status', sa.String(50), nullable=False, server_default='proposed'),
        sa.Column('suggested_by', sa.String(50), nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_cleaning_actions_dataset_version_id', 'cleaning_actions', ['dataset_version_id'])

    op.create_table(
        'cleaning_executions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('cleaning_action_id', sa.String(36),
                  sa.ForeignKey('cleaning_actions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('input_version_id', sa.String(36),
                  sa.ForeignKey('dataset_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('output_version_id', sa.String(36),
                  sa.ForeignKey('dataset_versions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('execution_status', sa.String(50), nullable=False, server_default='running'),
        sa.Column('preview_json', postgresql.JSONB, nullable=True),
        sa.Column('result_summary', sa.Text, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_cleaning_executions_cleaning_action_id', 'cleaning_executions', ['cleaning_action_id'])

    op.create_table(
        'pipelines',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36),
                  sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dataset_id', sa.String(36),
                  sa.ForeignKey('datasets.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_pipelines_project_id', 'pipelines', ['project_id'])

    op.create_table(
        'pipeline_nodes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('pipeline_id', sa.String(36),
                  sa.ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=False),
        sa.Column('node_type', sa.String(100), nullable=False),
        sa.Column('node_name', sa.String(255), nullable=False),
        sa.Column('config_json', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('position_x', sa.Float, nullable=True),
        sa.Column('position_y', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_pipeline_nodes_pipeline_id', 'pipeline_nodes', ['pipeline_id'])

    op.create_table(
        'pipeline_edges',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('pipeline_id', sa.String(36),
                  sa.ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_node_id', sa.String(36),
                  sa.ForeignKey('pipeline_nodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_node_id', sa.String(36),
                  sa.ForeignKey('pipeline_nodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_pipeline_edges_pipeline_id', 'pipeline_edges', ['pipeline_id'])


def downgrade() -> None:
    op.drop_table('pipeline_edges')
    op.drop_table('pipeline_nodes')
    op.drop_table('pipelines')
    op.drop_table('cleaning_executions')
    op.drop_table('cleaning_actions')
