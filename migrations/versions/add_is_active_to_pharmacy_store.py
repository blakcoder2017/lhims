"""add_is_active_to_pharmacy_store - Add is_active column to pharmacy_store table

Revision ID: add_is_active_to_pharmacy_store
Revises: add_is_active_to_charges
Create Date: 2026-02-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_is_active_to_pharmacy_store'
down_revision: Union[str, Sequence[str], None] = 'add_discount_rule_and_audit_void'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_active column to pharmacy_store table for soft delete support."""
    # Add is_active column with default value True
    op.add_column(
        'pharmacy_store',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
    )


def downgrade() -> None:
    """Remove is_active column from pharmacy_store table."""
    op.drop_column('pharmacy_store', 'is_active')
