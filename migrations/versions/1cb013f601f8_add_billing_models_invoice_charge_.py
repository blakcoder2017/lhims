"""add billing models invoice charge payment

Revision ID: 1cb013f601f8
Revises: b6cd6bc9ce08
Create Date: 2025-11-09 21:17:22.112187

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1cb013f601f8'
down_revision: Union[str, Sequence[str], None] = 'b6cd6bc9ce08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum types first (PostgreSQL requirement)
    # Using DO blocks to check if type exists before creating
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE invoicestatus AS ENUM ('draft', 'pending', 'partially_paid', 'paid', 'cancelled', 'refunded');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE paymentmethod AS ENUM ('cash', 'mobile_money', 'card', 'bank_transfer', 'nhis', 'private_insurance');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE chargetype AS ENUM ('consultation', 'lab_test', 'radiology', 'pharmacy', 'procedure', 'admission', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE paymentstatus AS ENUM ('pending', 'completed', 'failed', 'refunded');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.create_table('invoices',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('encounter_id', sa.Integer(), nullable=True),
    sa.Column('appointment_id', sa.Integer(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('invoice_number', sa.String(length=50), nullable=False),
    sa.Column('status', postgresql.ENUM('draft', 'pending', 'partially_paid', 'paid', 'cancelled', 'refunded', name='invoicestatus', create_type=False), nullable=False),
    sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('paid_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('balance', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('payment_mechanism', postgresql.ENUM('cash', 'mobile_money', 'card', 'bank_transfer', 'nhis', 'private_insurance', name='paymentmethod', create_type=False), nullable=True),
    sa.Column('nhis_number', sa.String(length=50), nullable=True),
    sa.Column('insurance_provider', sa.String(length=100), nullable=True),
    sa.Column('insurance_policy_number', sa.String(length=100), nullable=True),
    sa.Column('invoice_date', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('due_date', sa.DateTime(), nullable=True),
    sa.Column('paid_date', sa.DateTime(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['encounter_id'], ['encounters.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invoices_id'), 'invoices', ['id'], unique=False)
    op.create_index(op.f('ix_invoices_invoice_number'), 'invoices', ['invoice_number'], unique=True)
    op.create_table('charges',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('invoice_id', sa.Integer(), nullable=False),
    sa.Column('encounter_id', sa.Integer(), nullable=True),
    sa.Column('lab_order_id', sa.Integer(), nullable=True),
    sa.Column('radiology_order_id', sa.Integer(), nullable=True),
    sa.Column('prescription_id', sa.Integer(), nullable=True),
    sa.Column('charge_type', postgresql.ENUM('consultation', 'lab_test', 'radiology', 'pharmacy', 'procedure', 'admission', 'other', name='chargetype', create_type=False), nullable=False),
    sa.Column('description', sa.String(length=500), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('discount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['encounter_id'], ['encounters.id'], ),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
    sa.ForeignKeyConstraint(['lab_order_id'], ['lab_orders.id'], ),
    sa.ForeignKeyConstraint(['prescription_id'], ['prescriptions.id'], ),
    sa.ForeignKeyConstraint(['radiology_order_id'], ['radiology_orders.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_charges_id'), 'charges', ['id'], unique=False)
    op.create_table('payments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('invoice_id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('received_by_id', sa.Integer(), nullable=False),
    sa.Column('payment_number', sa.String(length=50), nullable=False),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('payment_method', postgresql.ENUM('cash', 'mobile_money', 'card', 'bank_transfer', 'nhis', 'private_insurance', name='paymentmethod', create_type=False), nullable=False),
    sa.Column('status', postgresql.ENUM('pending', 'completed', 'failed', 'refunded', name='paymentstatus', create_type=False), nullable=False),
    sa.Column('transaction_reference', sa.String(length=100), nullable=True),
    sa.Column('receipt_number', sa.String(length=50), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('payment_date', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['received_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)
    op.create_index(op.f('ix_payments_payment_number'), 'payments', ['payment_number'], unique=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_payments_payment_number'), table_name='payments')
    op.drop_index(op.f('ix_payments_id'), table_name='payments')
    op.drop_table('payments')
    op.drop_index(op.f('ix_charges_id'), table_name='charges')
    op.drop_table('charges')
    op.drop_index(op.f('ix_invoices_invoice_number'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_id'), table_name='invoices')
    op.drop_table('invoices')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS paymentstatus')
    op.execute('DROP TYPE IF EXISTS chargetype')
    op.execute('DROP TYPE IF EXISTS paymentmethod')
    op.execute('DROP TYPE IF EXISTS invoicestatus')
    # ### end Alembic commands ###
