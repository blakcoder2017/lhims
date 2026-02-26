"""add nhis_expiry_date to patients

Revision ID: add_nhis_expiry
Revises: 446dc4c3cf37
Create Date: 2025-02-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_nhis_expiry'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('patients', sa.Column('nhis_expiry_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('patients', 'nhis_expiry_date')
