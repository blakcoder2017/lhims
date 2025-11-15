"""add_appointments_and_financial_screening

Revision ID: 31350ee33b80
Revises: b6b2721b3e1d
Create Date: 2025-11-09 08:40:27.836536

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '31350ee33b80'
down_revision: Union[str, Sequence[str], None] = 'b6b2721b3e1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum types first (PostgreSQL requirement)
    # Using DO blocks to check if type exists before creating
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE paymentmechanism AS ENUM ('CASH', 'NHIS', 'PRIVATE_INSURANCE', 'SELF_PAY');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE appointmenttype AS ENUM ('WALK_IN', 'SCHEDULED', 'EMERGENCY', 'FOLLOW_UP');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE appointmentstatus AS ENUM ('SCHEDULED', 'CHECKED_IN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create appointments table
    op.create_table('appointments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('department', sa.String(length=100), nullable=False),
    sa.Column('assigned_clinician_id', sa.Integer(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('appointment_type', postgresql.ENUM('WALK_IN', 'SCHEDULED', 'EMERGENCY', 'FOLLOW_UP', name='appointmenttype', create_type=False), nullable=False),
    sa.Column('status', postgresql.ENUM('SCHEDULED', 'CHECKED_IN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW', name='appointmentstatus', create_type=False), nullable=False),
    sa.Column('priority', sa.Integer(), nullable=True),
    sa.Column('scheduled_date', sa.DateTime(), nullable=False),
    sa.Column('checked_in_at', sa.DateTime(), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('chief_complaint', sa.String(length=500), nullable=True),
    sa.Column('notes', sa.String(length=1000), nullable=True),
    sa.Column('queue_number', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['assigned_clinician_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_appointments_id'), 'appointments', ['id'], unique=False)
    
    # Add financial screening columns to patients table
    op.add_column('patients', sa.Column('payment_mechanism', postgresql.ENUM('CASH', 'NHIS', 'PRIVATE_INSURANCE', 'SELF_PAY', name='paymentmechanism', create_type=False), nullable=True))
    op.add_column('patients', sa.Column('nhis_number', sa.String(), nullable=True))
    op.add_column('patients', sa.Column('insurance_provider', sa.String(), nullable=True))
    op.add_column('patients', sa.Column('insurance_policy_number', sa.String(), nullable=True))
    op.create_index(op.f('ix_patients_nhis_number'), 'patients', ['nhis_number'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop columns first
    op.drop_index(op.f('ix_patients_nhis_number'), table_name='patients')
    op.drop_column('patients', 'insurance_policy_number')
    op.drop_column('patients', 'insurance_provider')
    op.drop_column('patients', 'nhis_number')
    op.drop_column('patients', 'payment_mechanism')
    
    # Drop appointments table
    op.drop_index(op.f('ix_appointments_id'), table_name='appointments')
    op.drop_table('appointments')
    
    # Drop enum types (must be done after dropping tables/columns that use them)
    op.execute('DROP TYPE IF EXISTS paymentmechanism')
    op.execute('DROP TYPE IF EXISTS appointmenttype')
    op.execute('DROP TYPE IF EXISTS appointmentstatus')
