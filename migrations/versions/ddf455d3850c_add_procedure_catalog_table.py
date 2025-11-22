"""add_procedure_catalog_table

Revision ID: ddf455d3850c
Revises: c8d9e0f1a2b3
Create Date: 2025-01-XX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ddf455d3850c'
down_revision: Union[str, Sequence[str], None] = 'c8d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create procedure_catalog table
    op.create_table('procedure_catalog',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('procedure_name', sa.String(length=255), nullable=False),
    sa.Column('procedure_code', sa.String(length=50), nullable=True),
    sa.Column('procedure_category', sa.String(length=100), nullable=True),
    sa.Column('procedure_type', sa.String(length=100), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('indication', sa.Text(), nullable=True),
    sa.Column('preparation_instructions', sa.Text(), nullable=True),
    sa.Column('post_procedure_care', sa.Text(), nullable=True),
    sa.Column('estimated_duration_minutes', sa.Integer(), nullable=True),
    sa.Column('typical_duration_minutes', sa.Integer(), nullable=True),
    sa.Column('cash_price', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('cash_currency', sa.String(length=10), nullable=True),
    sa.Column('nhis_covered', sa.Boolean(), nullable=True),
    sa.Column('nhis_code', sa.String(length=50), nullable=True),
    sa.Column('nhis_price', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('private_insurance_covered', sa.Boolean(), nullable=True),
    sa.Column('private_insurance_price', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('requires_anesthesia', sa.Boolean(), nullable=True),
    sa.Column('typical_anesthesia_type', sa.String(length=100), nullable=True),
    sa.Column('requires_operating_room', sa.Boolean(), nullable=True),
    sa.Column('typical_location', sa.String(length=200), nullable=True),
    sa.Column('is_specialized', sa.Boolean(), nullable=True),
    sa.Column('requires_consultation', sa.Boolean(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('updated_by_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_procedure_catalog_id'), 'procedure_catalog', ['id'], unique=False)
    op.create_index(op.f('ix_procedure_catalog_procedure_name'), 'procedure_catalog', ['procedure_name'], unique=False)
    op.create_index(op.f('ix_procedure_catalog_procedure_code'), 'procedure_catalog', ['procedure_code'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_procedure_catalog_procedure_code'), table_name='procedure_catalog')
    op.drop_index(op.f('ix_procedure_catalog_procedure_name'), table_name='procedure_catalog')
    op.drop_index(op.f('ix_procedure_catalog_id'), table_name='procedure_catalog')
    op.drop_table('procedure_catalog')

