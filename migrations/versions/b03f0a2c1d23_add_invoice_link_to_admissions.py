"""add_invoice_link_to_admissions

Revision ID: b03f0a2c1d23
Revises: a46a659383dc
Create Date: 2025-11-14 06:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b03f0a2c1d23"
down_revision = "a46a659383dc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "admissions",
        sa.Column("invoice_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_admissions_invoice_id",
        "admissions",
        "invoices",
        ["invoice_id"],
        ["id"],
        ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("fk_admissions_invoice_id", "admissions", type_="foreignkey")
    op.drop_column("admissions", "invoice_id")

