"""add walk-in support to prescriptions

Revision ID: c7b0f9fd8d23
Revises: 0233094202a9
Create Date: 2025-11-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7b0f9fd8d23'
down_revision: Union[str, Sequence[str], None] = '0233094202a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add walk-in tracking fields to prescriptions."""
    op.add_column('prescriptions', sa.Column('is_walk_in', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('prescriptions', sa.Column('checked_in_at', sa.DateTime(), nullable=True))
    op.add_column('prescriptions', sa.Column('checked_in_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_prescriptions_checked_in_by',
        'prescriptions',
        'users',
        ['checked_in_by_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.alter_column('prescriptions', 'is_walk_in', server_default=None)


def downgrade() -> None:
    """Remove walk-in tracking fields from prescriptions."""
    op.drop_constraint('fk_prescriptions_checked_in_by', 'prescriptions', type_='foreignkey')
    op.drop_column('prescriptions', 'checked_in_by_id')
    op.drop_column('prescriptions', 'checked_in_at')
    op.drop_column('prescriptions', 'is_walk_in')

