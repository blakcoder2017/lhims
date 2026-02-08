"""make triage_vitals.temperature nullable

Revision ID: triage_temp_null
Revises: add_phone_users
Create Date: 2025-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "triage_temp_null"
down_revision: Union[str, None] = "add_phone_users"
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
