"""Add prescription_id and invoice_id to pharmacy_dispense

Revision ID: add_prescription_invoice_to_dispense
Revises: add_pharmacy_ghana_ready
Create Date: 2026-02-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_prescription_invoice_to_dispense'
down_revision = 'add_pharmacy_ghana_ready'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add prescription_id column
    op.add_column(
        'pharmacy_dispense',
        sa.Column('prescription_id', sa.Integer(), sa.ForeignKey('prescriptions.id'), nullable=True)
    )
    # Add invoice_id column
    op.add_column(
        'pharmacy_dispense',
        sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('invoices.id'), nullable=True)
    )
    # Create indexes for the new columns
    op.create_index('ix_pharmacy_dispense_prescription_id', 'pharmacy_dispense', ['prescription_id'])
    op.create_index('ix_pharmacy_dispense_invoice_id', 'pharmacy_dispense', ['invoice_id'])


def downgrade() -> None:
    op.drop_index('ix_pharmacy_dispense_invoice_id', 'pharmacy_dispense')
    op.drop_index('ix_pharmacy_dispense_prescription_id', 'pharmacy_dispense')
    op.drop_column('pharmacy_dispense', 'invoice_id')
    op.drop_column('pharmacy_dispense', 'prescription_id')
