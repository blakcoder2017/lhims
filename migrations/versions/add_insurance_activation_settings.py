"""add_insurance_activation_settings

Revision ID: b2c3d4e5f6a9
Revises: lab_inventory_v1
Create Date: 2026-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a9'
down_revision: Union[str, Sequence[str], None] = 'lab_inventory_v1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add NHIS activation flag
    op.add_column(
        'hospital_settings',
        sa.Column('nhis_enabled', sa.Boolean(), nullable=True, server_default='true')
    )
    # Add Private Insurance activation flag
    op.add_column(
        'hospital_settings',
        sa.Column('private_insurance_enabled', sa.Boolean(), nullable=True, server_default='true')
    )


def downgrade() -> None:
    op.drop_column('hospital_settings', 'private_insurance_enabled')
    op.drop_column('hospital_settings', 'nhis_enabled')
