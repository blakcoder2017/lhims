"""add_addendum_to_encounters

Revision ID: add_addendum_to_encounters
Revises: 
Create Date: 2026-02-23 08:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_addendum_to_encounters'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add addendum column to encounters table."""
    op.add_column('encounters', sa.Column('addendum', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove addendum column from encounters table."""
    op.drop_column('encounters', 'addendum')
