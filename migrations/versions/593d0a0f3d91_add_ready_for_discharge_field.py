"""add_ready_for_discharge_field

Revision ID: 593d0a0f3d91
Revises: b03f0a2c1d23
Create Date: 2025-11-14 07:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "593d0a0f3d91"
down_revision: Union[str, Sequence[str], None] = "b03f0a2c1d23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "admissions",
        sa.Column("ready_for_discharge_at", sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("admissions", "ready_for_discharge_at")

