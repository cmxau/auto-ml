"""add output_json to training_runs

Revision ID: 006
Revises: 005
Create Date: 2026-06-17 00:06:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'training_runs',
        sa.Column('output_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('training_runs', 'output_json')
