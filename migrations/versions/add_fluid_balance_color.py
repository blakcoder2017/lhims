"""Add color column to fluid_balance table

Revision ID: add_fluid_balance_color
Revises: 
Create Date: 2026-02-20
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_fluid_balance_color'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('fluid_balance', sa.Column('color', sa.String(length=50), nullable=True))

def downgrade():
    op.drop_column('fluid_balance', 'color')
