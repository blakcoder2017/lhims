"""add_opd_visits_and_update_encounters_billing

Revision ID: a1b2c3d4e5f6
Revises: 6f4520413ad0
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '6f4520413ad0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add OPD visits table and update encounters/billing tables."""
    
    # Create enum type for OPD visit status
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE opdvisitstatus AS ENUM ('active', 'completed', 'cancelled');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create opd_visits table
    op.create_table('opd_visits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('appointment_id', sa.Integer(), nullable=True),
        sa.Column('opd_number', sa.String(length=50), nullable=False),
        sa.Column('visit_date', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('status', postgresql.ENUM('active', 'completed', 'cancelled', name='opdvisitstatus', create_type=False), nullable=False, server_default='active'),
        sa.Column('payment_status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('consultation_charge_created', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('total_charges', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('visit_type', sa.String(length=50), nullable=True),
        sa.Column('chief_complaint', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('opd_number')
    )
    op.create_index(op.f('ix_opd_visits_id'), 'opd_visits', ['id'], unique=False)
    op.create_index(op.f('ix_opd_visits_opd_number'), 'opd_visits', ['opd_number'], unique=True)
    op.create_index('ix_opd_visits_patient', 'opd_visits', ['patient_id'], unique=False)
    op.create_index('ix_opd_visits_visit_date', 'opd_visits', ['visit_date'], unique=False)
    
    # Add opd_visit_id to encounters table
    op.add_column('encounters', sa.Column('opd_visit_id', sa.Integer(), nullable=True))
    op.add_column('encounters', sa.Column('admission_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_encounters_opd_visit', 'encounters', 'opd_visits', ['opd_visit_id'], ['id'])
    op.create_foreign_key('fk_encounters_admission', 'encounters', 'admissions', ['admission_id'], ['id'])
    op.create_index('ix_encounters_opd_visit', 'encounters', ['opd_visit_id'], unique=False)
    op.create_index('ix_encounters_admission', 'encounters', ['admission_id'], unique=False)
    
    # Add opd_visit_id and admission_id to invoices table
    op.add_column('invoices', sa.Column('opd_visit_id', sa.Integer(), nullable=True))
    op.add_column('invoices', sa.Column('admission_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_invoices_opd_visit', 'invoices', 'opd_visits', ['opd_visit_id'], ['id'])
    op.create_foreign_key('fk_invoices_admission', 'invoices', 'admissions', ['admission_id'], ['id'])
    op.create_index('ix_invoices_opd_visit', 'invoices', ['opd_visit_id'], unique=False)
    op.create_index('ix_invoices_admission', 'invoices', ['admission_id'], unique=False)
    
    # Add opd_visit_id and admission_id to charges table
    op.add_column('charges', sa.Column('opd_visit_id', sa.Integer(), nullable=True))
    op.add_column('charges', sa.Column('admission_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_charges_opd_visit', 'charges', 'opd_visits', ['opd_visit_id'], ['id'])
    op.create_foreign_key('fk_charges_admission', 'charges', 'admissions', ['admission_id'], ['id'])
    op.create_index('ix_charges_opd_visit', 'charges', ['opd_visit_id'], unique=False)
    op.create_index('ix_charges_admission', 'charges', ['admission_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - Remove OPD visits table and related columns."""
    
    # Remove indexes and foreign keys from charges table
    op.drop_index('ix_charges_admission', table_name='charges')
    op.drop_index('ix_charges_opd_visit', table_name='charges')
    op.drop_constraint('fk_charges_admission', 'charges', type_='foreignkey')
    op.drop_constraint('fk_charges_opd_visit', 'charges', type_='foreignkey')
    op.drop_column('charges', 'admission_id')
    op.drop_column('charges', 'opd_visit_id')
    
    # Remove indexes and foreign keys from invoices table
    op.drop_index('ix_invoices_admission', table_name='invoices')
    op.drop_index('ix_invoices_opd_visit', table_name='invoices')
    op.drop_constraint('fk_invoices_admission', 'invoices', type_='foreignkey')
    op.drop_constraint('fk_invoices_opd_visit', 'invoices', type_='foreignkey')
    op.drop_column('invoices', 'admission_id')
    op.drop_column('invoices', 'opd_visit_id')
    
    # Remove indexes and foreign keys from encounters table
    op.drop_index('ix_encounters_admission', table_name='encounters')
    op.drop_index('ix_encounters_opd_visit', table_name='encounters')
    op.drop_constraint('fk_encounters_admission', 'encounters', type_='foreignkey')
    op.drop_constraint('fk_encounters_opd_visit', 'encounters', type_='foreignkey')
    op.drop_column('encounters', 'admission_id')
    op.drop_column('encounters', 'opd_visit_id')
    
    # Drop opd_visits table
    op.drop_table('opd_visits')
    
    # Drop enum type
    op.execute("DROP TYPE IF EXISTS opdvisitstatus")

