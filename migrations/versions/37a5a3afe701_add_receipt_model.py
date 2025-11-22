"""add_receipt_model

Revision ID: 37a5a3afe701
Revises: 866b026e17f1
Create Date: 2025-11-17 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37a5a3afe701'
down_revision: Union[str, None] = '866b026e17f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create receipts table
    op.create_table(
        'receipts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('generated_by_id', sa.Integer(), nullable=False),
        sa.Column('receipt_number', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='GHS'),
        sa.Column('generated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], name='fk_receipts_payment_id_payments'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name='fk_receipts_patient_id_patients'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], name='fk_receipts_invoice_id_invoices'),
        sa.ForeignKeyConstraint(['generated_by_id'], ['users.id'], name='fk_receipts_generated_by_id_users'),
    )
    
    # Create indexes
    op.create_index(op.f('ix_receipts_id'), 'receipts', ['id'], unique=False)
    op.create_index(op.f('ix_receipts_receipt_number'), 'receipts', ['receipt_number'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_receipts_receipt_number'), table_name='receipts')
    op.drop_index(op.f('ix_receipts_id'), table_name='receipts')
    
    # Drop receipts table
    op.drop_table('receipts')
