"""add nhis claims table

Revision ID: 669d16d611ce
Revises: 73b94ffa061a
Create Date: 2025-11-09 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '669d16d611ce'
down_revision: Union[str, Sequence[str], None] = '73b94ffa061a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create claimstatus enum type
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE claimstatus AS ENUM ('draft', 'pending', 'submitted', 'processing', 'approved', 'rejected', 'paid', 'cancelled');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.create_table('nhis_claims',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('encounter_id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('invoice_id', sa.Integer(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('claim_number', sa.String(length=50), nullable=False),
    sa.Column('nhis_number', sa.String(length=50), nullable=False),
    sa.Column('facility_code', sa.String(length=50), nullable=True),
    sa.Column('claim_date', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('status', postgresql.ENUM('draft', 'pending', 'submitted', 'processing', 'approved', 'rejected', 'paid', 'cancelled', name='claimstatus', create_type=False), nullable=False),
    sa.Column('claim_data', sa.Text(), nullable=True),
    sa.Column('diagnosis_codes', sa.Text(), nullable=True),
    sa.Column('service_codes', sa.Text(), nullable=True),
    sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('nhis_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('co_pay_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('submitted_at', sa.DateTime(), nullable=True),
    sa.Column('submission_reference', sa.String(length=100), nullable=True),
    sa.Column('response_data', sa.Text(), nullable=True),
    sa.Column('processed_at', sa.DateTime(), nullable=True),
    sa.Column('approved_amount', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('rejection_reason', sa.Text(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['encounter_id'], ['encounters.id'], ),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_nhis_claims_id'), 'nhis_claims', ['id'], unique=False)
    op.create_index(op.f('ix_nhis_claims_claim_number'), 'nhis_claims', ['claim_number'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_nhis_claims_claim_number'), table_name='nhis_claims')
    op.drop_index(op.f('ix_nhis_claims_id'), table_name='nhis_claims')
    op.drop_table('nhis_claims')
    op.execute('DROP TYPE IF EXISTS claimstatus')
