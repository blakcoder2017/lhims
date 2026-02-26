"""Add charge_types_config to hospital_settings

Revision ID: add_charge_types_config
Revises: 
Create Date: 2026-02-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_charge_types_config'
down_revision = None  # Set to latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Add charge_types_config JSON column to hospital_settings table
    op.add_column(
        'hospital_settings',
        sa.Column(
            'charge_types_config',
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment='Configurable charge types list'
        )
    )


def downgrade():
    op.drop_column('hospital_settings', 'charge_types_config')
