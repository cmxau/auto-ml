"""add error_message to training_runs

Revision ID: 005
Revises: 004
Create Date: 2026-06-17 00:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'training_runs',
        sa.Column('error_message', sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column('training_runs', 'error_message')
