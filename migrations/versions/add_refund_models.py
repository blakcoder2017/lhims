"""add_refund_models

Revision ID: add_refund_models
Revises: 
Create Date: 2026-02-24 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_refund_models'
down_revision: Union[str, None] = '2091a86885bd'  # Use the latest migration revision ID
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create refundstatus enum
    refund_status_enum = postgresql.ENUM(
        'pending', 'approved', 'rejected', 'processed',
        name='refundstatus',
        create_type=False
    )
    refund_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create refund_policies table
    op.create_table(
        'refund_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('max_refund_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('refund_window_days', sa.Integer(), nullable=True),
        sa.Column('auto_approve_threshold', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('approval_level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name='fk_refund_policies_created_by_id_users'),
    )
    op.create_index(op.f('ix_refund_policies_id'), 'refund_policies', ['id'], unique=False)
    
    # Create refunds table
    op.create_table(
        'refunds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('payment_id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('requested_by_id', sa.Integer(), nullable=False),
        sa.Column('approved_by_id', sa.Integer(), nullable=True),
        sa.Column('processed_by_id', sa.Integer(), nullable=True),
        sa.Column('policy_id', sa.Integer(), nullable=True),
        sa.Column('refund_number', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', refund_status_enum, nullable=False, server_default='pending'),
        sa.Column('refund_method', sa.String(length=50), nullable=True),
        sa.Column('transaction_reference', sa.String(length=100), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('request_date', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('approval_date', sa.DateTime(), nullable=True),
        sa.Column('processed_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], name='fk_refunds_invoice_id_invoices'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], name='fk_refunds_payment_id_payments'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name='fk_refunds_patient_id_patients'),
        sa.ForeignKeyConstraint(['requested_by_id'], ['users.id'], name='fk_refunds_requested_by_id_users'),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], name='fk_refunds_approved_by_id_users'),
        sa.ForeignKeyConstraint(['processed_by_id'], ['users.id'], name='fk_refunds_processed_by_id_users'),
        sa.ForeignKeyConstraint(['policy_id'], ['refund_policies.id'], name='fk_refunds_policy_id_refund_policies'),
    )
    op.create_index(op.f('ix_refunds_id'), 'refunds', ['id'], unique=False)
    op.create_index(op.f('ix_refunds_refund_number'), 'refunds', ['refund_number'], unique=True)
    
    # Add relationship columns to invoices table
    op.add_column('invoices', sa.Column('refund_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_invoices_refund_id_refunds',
        'invoices', 'refunds',
        ['refund_id'], ['id']
    )


def downgrade() -> None:
    # Drop foreign key and column from invoices
    op.drop_constraint('fk_invoices_refund_id_refunds', 'invoices', type_='foreignkey')
    op.drop_column('invoices', 'refund_id')
    
    # Drop refunds table indexes
    op.drop_index(op.f('ix_refunds_refund_number'), table_name='refunds')
    op.drop_index(op.f('ix_refunds_id'), table_name='refunds')
    
    # Drop refunds table
    op.drop_table('refunds')
    
    # Drop refund_policies table indexes
    op.drop_index(op.f('ix_refund_policies_id'), table_name='refund_policies')
    
    # Drop refund_policies table
    op.drop_table('refund_policies')
    
    # Drop refundstatus enum
    op.execute('DROP TYPE IF EXISTS refundstatus')
