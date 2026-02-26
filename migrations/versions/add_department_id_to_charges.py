"""Add department_id to charges table

Revision ID: add_department_id_to_charges
Revises: 
Create Date: 2026-02-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_department_id_to_charges'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add department_id column to charges table
    op.add_column('charges', sa.Column('department_id', sa.Integer(), sa.ForeignKey('departments.id'), nullable=True))
    
    # Create index for faster department-based queries
    op.create_index('ix_charges_department_id', 'charges', ['department_id'])


def downgrade():
    op.drop_index('ix_charges_department_id', table_name='charges')
    op.drop_column('charges', 'department_id')
