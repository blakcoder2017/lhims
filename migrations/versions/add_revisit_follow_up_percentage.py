"""add_revisit_follow_up_percentage

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-02-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a8'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'hospital_settings',
        sa.Column('revisit_follow_up_percentage', sa.Numeric(5, 2), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('hospital_settings', 'revisit_follow_up_percentage')
