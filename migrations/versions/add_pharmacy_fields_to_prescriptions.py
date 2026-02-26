"""Add pharmacy_drug_id and snapshot fields to prescriptions table

Revision ID: add_prescription_snapshot_fields
Revises: add_pharmacy_ghana_ready
Create Date: 2026-02-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision = 'add_prescription_snapshot_fields'
down_revision: Union[str, Sequence[str], None] = 'add_pharmacy_ghana_ready'
branch_labels = None
depends_on = None


def upgrade():
    # Add pharmacy_drug_id column if it doesn't exist (may already exist from pharmacy_ghana migration)
    try:
        op.add_column('prescriptions', 
            sa.Column('pharmacy_drug_id', postgresql.UUID(as_uuid=True), 
                      sa.ForeignKey('pharmacy_drug.id'), 
                      nullable=True))
    except Exception:
        # Column may already exist
        pass
    
    # Add snapshot fields for when drug is deleted
    op.add_column('prescriptions',
        sa.Column('dosage_form_name', sa.String(100), nullable=True))
    op.add_column('prescriptions',
        sa.Column('strength_value', sa.Numeric(20, 6), nullable=True))
    op.add_column('prescriptions',
        sa.Column('strength_unit', sa.String(50), nullable=True))
    op.add_column('prescriptions',
        sa.Column('route', sa.String(50), nullable=True))
    op.add_column('prescriptions',
        sa.Column('concentration_value', sa.Numeric(20, 6), nullable=True))
    op.add_column('prescriptions',
        sa.Column('concentration_unit', sa.String(100), nullable=True))


def downgrade():
    op.drop_column('prescriptions', 'concentration_unit')
    op.drop_column('prescriptions', 'concentration_value')
    op.drop_column('prescriptions', 'route')
    op.drop_column('prescriptions', 'strength_unit')
    op.drop_column('prescriptions', 'strength_value')
    op.drop_column('prescriptions', 'dosage_form_name')
    # Don't drop pharmacy_drug_id as it's needed for pharmacy_ghana migration
