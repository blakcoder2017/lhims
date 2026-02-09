"""add restriction fields for direct requests

Revision ID: 6f4520413ad0
Revises: 4a83272e2da6
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f4520413ad0'
down_revision: Union[str, Sequence[str], None] = '4a83272e2da6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_controlled field to medications table
    op.add_column('medications', sa.Column('is_controlled', sa.Boolean(), nullable=True, server_default='false'))
    
    # Add is_specialized field to lab_tests table
    op.add_column('lab_tests', sa.Column('is_specialized', sa.Boolean(), nullable=True, server_default='false'))


def downgrade() -> None:
    # Remove is_controlled field from medications table
    op.drop_column('medications', 'is_controlled')
    
    # Remove is_specialized field from lab_tests table
    op.drop_column('lab_tests', 'is_specialized')
