"""add differential diagnosis data column to encounters

Revision ID: f0d61f438a43
Revises: c7b0f9fd8d23
Create Date: 2025-11-17 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0d61f438a43'
down_revision: Union[str, Sequence[str], None] = 'c7b0f9fd8d23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add JSON blob column for G-STG differential diagnoses."""
    op.add_column('encounters', sa.Column('differential_diagnosis_data', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove differential diagnosis data column."""
    op.drop_column('encounters', 'differential_diagnosis_data')


