"""Add critical_low and critical_high to lab_reference_ranges

Revision ID: add_critical_range
Revises: 
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_critical_range'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('lab_reference_ranges', 
        sa.Column('critical_low', sa.Numeric(20, 6), nullable=True))
    op.add_column('lab_reference_ranges', 
        sa.Column('critical_high', sa.Numeric(20, 6), nullable=True))


def downgrade() -> None:
    op.drop_column('lab_reference_ranges', 'critical_high')
    op.drop_column('lab_reference_ranges', 'critical_low')
