"""Add department_id to procedure_catalog table

Revision ID: add_dept_id_proc_cat
Revises: 
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_dept_id_proc_cat'
down_revision = '803bec0a2275'  # Using the merge head
branch_labels = None
depends_on = None


def upgrade():
    # Add department_id column to procedure_catalog table
    op.add_column(
        'procedure_catalog',
        sa.Column('department_id', sa.Integer(), sa.ForeignKey('departments.id'), nullable=True)
    )
    
    # Create index for faster queries
    op.create_index('ix_procedure_catalog_department_id', 'procedure_catalog', ['department_id'])


def downgrade():
    op.drop_index('ix_procedure_catalog_department_id', 'procedure_catalog')
    op.drop_column('procedure_catalog', 'department_id')
