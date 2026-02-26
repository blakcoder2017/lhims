"""add_department_consultation_price

Revision ID: a1b2c3d4e5f7
Revises: 00baf8b1931e
Create Date: 2026-02-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, Sequence[str], None] = '00baf8b1931e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'departments',
        sa.Column('consultation_price', sa.Numeric(10, 2), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('departments', 'consultation_price')
