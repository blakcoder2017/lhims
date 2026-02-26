"""Add missing columns to pharmacy_dispense_item

Revision ID: add_missing_dispense_item_cols
Revises: 
Create Date: 2026-02-17
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_missing_dispense_item_cols'
down_revision = None  # Set to the last migration revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing columns to pharmacy_dispense_item
    op.add_column('pharmacy_dispense_item', 
        sa.Column('unit_cost_snapshot', sa.Numeric(20, 6), nullable=True))
    op.add_column('pharmacy_dispense_item', 
        sa.Column('total_cost', sa.Numeric(20, 6), nullable=True))
    op.add_column('pharmacy_dispense_item', 
        sa.Column('margin', sa.Numeric(20, 6), nullable=True))
    
    # Also add prescription_id to pharmacy_dispense if it doesn't exist
    op.add_column('pharmacy_dispense', 
        sa.Column('prescription_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('pharmacy_dispense_item', 'margin')
    op.drop_column('pharmacy_dispense_item', 'total_cost')
    op.drop_column('pharmacy_dispense_item', 'unit_cost_snapshot')
    op.drop_column('pharmacy_dispense', 'prescription_id')
