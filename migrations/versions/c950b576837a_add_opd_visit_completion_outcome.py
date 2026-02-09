"""add completion_outcome to opd_visits

Revision ID: c950b576837a
Revises: a46a659383dc
Create Date: 2025-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c950b576837a'
down_revision: Union[str, Sequence[str], None] = 'a46a659383dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('opd_visits', sa.Column('completion_outcome', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('opd_visits', 'completion_outcome')
