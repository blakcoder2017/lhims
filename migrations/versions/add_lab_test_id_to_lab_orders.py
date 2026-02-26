"""Add lab_test_id to lab_orders table

Revision ID: add_lab_test_id_to_lab_orders
Revises: 
Create Date: 2026-02-14
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_lab_test_id_to_lab_orders'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add lab_test_id column to lab_orders table
    op.add_column('lab_orders', 
        sa.Column('lab_test_id', sa.Integer(), 
                  sa.ForeignKey('lab_tests.id', ondelete='SET NULL'),
                  nullable=True))


def downgrade():
    op.drop_column('lab_orders', 'lab_test_id')
