"""add completion_outcome to opd_visits

Revision ID: opd_completion_outcome
Revises: antenatal_birth_01
Create Date: 2025-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'opd_completion_outcome'
down_revision: Union[str, None] = 'antenatal_birth_01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('opd_visits', sa.Column('completion_outcome', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('opd_visits', 'completion_outcome')
