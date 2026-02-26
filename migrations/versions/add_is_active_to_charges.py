"""add_is_active_to_charges - Add is_active column to charges table

Revision ID: add_is_active_to_charges
Revises: fix_appointmenttype_enum
Create Date: 2026-02-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_is_active_to_charges'
down_revision: Union[str, Sequence[str], None] = 'fix_appointmenttype_enum'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_active column to charges table for soft delete support."""
    # Add is_active column with default value True
    op.add_column(
        'charges',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
    )


def downgrade() -> None:
    """Remove is_active column from charges table."""
    op.drop_column('charges', 'is_active')
