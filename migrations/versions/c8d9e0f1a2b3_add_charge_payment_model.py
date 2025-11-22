"""add_charge_payment_model

Revision ID: c8d9e0f1a2b3
Revises: b2c3d4e5f6a7
Create Date: 2025-11-19 17:06:56.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create charge_payments table
    op.create_table(
        'charge_payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_id', sa.Integer(), nullable=False),
        sa.Column('charge_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], name='fk_charge_payments_payment_id_payments'),
        sa.ForeignKeyConstraint(['charge_id'], ['charges.id'], name='fk_charge_payments_charge_id_charges'),
    )
    
    # Create indexes
    op.create_index(op.f('ix_charge_payments_id'), 'charge_payments', ['id'], unique=False)
    op.create_index('ix_charge_payments_payment_id', 'charge_payments', ['payment_id'], unique=False)
    op.create_index('ix_charge_payments_charge_id', 'charge_payments', ['charge_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_charge_payments_charge_id', table_name='charge_payments')
    op.drop_index('ix_charge_payments_payment_id', table_name='charge_payments')
    op.drop_index(op.f('ix_charge_payments_id'), table_name='charge_payments')
    
    # Drop charge_payments table
    op.drop_table('charge_payments')

