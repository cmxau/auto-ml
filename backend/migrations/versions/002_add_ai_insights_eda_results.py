"""add ai_insights and eda_results tables

Revision ID: 002
Revises: 001
Create Date: 2026-06-16 00:01:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_insights',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('dataset_id', sa.String(36),
                  sa.ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dataset_version_id', sa.String(36),
                  sa.ForeignKey('dataset_versions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('insight_type', sa.String(100), nullable=False),
        sa.Column('content', sa.Text, nullable=True),
        sa.Column('confidence_score', sa.Float, nullable=True),
        sa.Column('metadata_json', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_ai_insights_dataset_id', 'ai_insights', ['dataset_id'])
    op.create_index('ix_ai_insights_insight_type', 'ai_insights', ['insight_type'])

    op.create_table(
        'eda_results',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('dataset_version_id', sa.String(36),
                  sa.ForeignKey('dataset_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='queued'),
        sa.Column('charts_json', postgresql.JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_eda_results_dataset_version_id', 'eda_results', ['dataset_version_id'])


def downgrade() -> None:
    op.drop_table('eda_results')
    op.drop_table('ai_insights')
