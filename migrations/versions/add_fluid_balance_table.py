"""add fluid_balance table

Revision ID: fluid_balance_01
Revises: add_phone_users
Create Date: 2025-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "fluid_balance_01"
down_revision: Union[str, None] = "triage_temp_null"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fluid_balance",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admission_id", sa.Integer(), nullable=False),
        sa.Column("recorded_by_id", sa.Integer(), nullable=False),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("volume_ml", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["admission_id"], ["admissions.id"]),
        sa.ForeignKeyConstraint(["recorded_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fluid_balance_id"), "fluid_balance", ["id"], unique=False)
    op.create_index("ix_fluid_balance_admission_id", "fluid_balance", ["admission_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_fluid_balance_admission_id", table_name="fluid_balance")
    op.drop_index(op.f("ix_fluid_balance_id"), table_name="fluid_balance")
    op.drop_table("fluid_balance")
