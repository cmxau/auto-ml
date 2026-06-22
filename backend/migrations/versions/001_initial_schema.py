"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-16 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_projects_user_id', 'projects', ['user_id'])

    op.create_table(
        'datasets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('original_file_name', sa.String(500), nullable=False),
        sa.Column('file_format', sa.String(20), nullable=False),
        sa.Column('storage_uri', sa.String(1000), nullable=True),
        sa.Column('row_count', sa.Integer, nullable=True),
        sa.Column('column_count', sa.Integer, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='uploaded'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_datasets_project_id', 'datasets', ['project_id'])

    op.create_table(
        'dataset_versions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('dataset_id', sa.String(36), sa.ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer, nullable=False, server_default='0'),
        sa.Column('parent_version_id', sa.String(36), sa.ForeignKey('dataset_versions.id'), nullable=True),
        sa.Column('storage_uri', sa.String(1000), nullable=True),
        sa.Column('row_count', sa.Integer, nullable=True),
        sa.Column('column_count', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_dataset_versions_dataset_id', 'dataset_versions', ['dataset_id'])

    op.create_table(
        'dataset_profiles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('dataset_version_id', sa.String(36), sa.ForeignKey('dataset_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('profile_json', postgresql.JSONB, nullable=True),
        sa.Column('summary_text', sa.Text, nullable=True),
        sa.Column('missing_value_count', sa.Integer, nullable=True),
        sa.Column('duplicate_row_count', sa.Integer, nullable=True),
        sa.Column('numeric_column_count', sa.Integer, nullable=True),
        sa.Column('categorical_column_count', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_dataset_profiles_dataset_version_id', 'dataset_profiles', ['dataset_version_id'])

    op.create_table(
        'dataset_column_profiles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('dataset_profile_id', sa.String(36), sa.ForeignKey('dataset_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('column_name', sa.String(255), nullable=False),
        sa.Column('data_type', sa.String(50), nullable=False),
        sa.Column('missing_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('unique_count', sa.Integer, nullable=True),
        sa.Column('mean_value', sa.Float, nullable=True),
        sa.Column('std_value', sa.Float, nullable=True),
        sa.Column('min_value', sa.Float, nullable=True),
        sa.Column('max_value', sa.Float, nullable=True),
        sa.Column('top_values_json', postgresql.JSONB, nullable=True),
        sa.Column('example_values_json', postgresql.JSONB, nullable=True),
        sa.Column('high_cardinality_flag', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_dataset_column_profiles_dataset_profile_id', 'dataset_column_profiles', ['dataset_profile_id'])

    op.create_table(
        'jobs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dataset_id', sa.String(36), sa.ForeignKey('datasets.id', ondelete='SET NULL'), nullable=True),
        sa.Column('job_type', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='queued'),
        sa.Column('progress_percent', sa.Float, nullable=True),
        sa.Column('celery_task_id', sa.String(255), nullable=True),
        sa.Column('input_json', postgresql.JSONB, nullable=True),
        sa.Column('output_json', postgresql.JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('retry_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_jobs_project_id', 'jobs', ['project_id'])
    op.create_index('ix_jobs_status', 'jobs', ['status'])


def downgrade() -> None:
    op.drop_table('jobs')
    op.drop_table('dataset_column_profiles')
    op.drop_table('dataset_profiles')
    op.drop_table('dataset_versions')
    op.drop_table('datasets')
    op.drop_table('projects')
    op.drop_table('users')
