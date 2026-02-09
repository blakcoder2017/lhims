"""make triage_vitals.temperature nullable

Revision ID: 9ed833a63cf2
Revises: 6c495c397f81
Create Date: 2025-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9ed833a63cf2'
down_revision: Union[str, Sequence[str], None] = "6c495c397f81"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "triage_vitals",
        "temperature",
        existing_type=sa.Float(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "triage_vitals",
        "temperature",
        existing_type=sa.Float(),
        nullable=False,
    )
