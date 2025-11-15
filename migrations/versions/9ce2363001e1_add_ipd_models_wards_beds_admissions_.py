"""add_ipd_models_wards_beds_admissions_doctor_duties

Revision ID: 9ce2363001e1
Revises: 5d58e5cf533d
Create Date: 2025-11-11 19:45:47.954585

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9ce2363001e1'
down_revision: Union[str, Sequence[str], None] = '5d58e5cf533d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add IPD models (Wards, Beds, Admissions, Doctor Duties)."""
    # Create enum types first (PostgreSQL requirement)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE wardstatus AS ENUM ('active', 'inactive', 'maintenance');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE bedstatus AS ENUM ('available', 'occupied', 'reserved', 'maintenance');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE admissionstatus AS ENUM ('admitted', 'discharged', 'transferred', 'absconded');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create wards table
    op.create_table('wards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('ward_number', sa.String(length=50), nullable=True),
        sa.Column('ward_type', sa.String(length=50), nullable=True),
        sa.Column('capacity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_occupancy', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', postgresql.ENUM('active', 'inactive', 'maintenance', name='wardstatus', create_type=False), nullable=False, server_default='active'),
        sa.Column('floor', sa.String(length=50), nullable=True),
        sa.Column('building', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('charge_per_day', sa.Numeric(10, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('ward_number')
    )
    op.create_index(op.f('ix_wards_id'), 'wards', ['id'], unique=False)
    op.create_index(op.f('ix_wards_name'), 'wards', ['name'], unique=True)
    op.create_index(op.f('ix_wards_ward_number'), 'wards', ['ward_number'], unique=True)
    
    # Create beds table
    op.create_table('beds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ward_id', sa.Integer(), nullable=False),
        sa.Column('bed_number', sa.String(length=50), nullable=False),
        sa.Column('bed_name', sa.String(length=100), nullable=True),
        sa.Column('status', postgresql.ENUM('available', 'occupied', 'reserved', 'maintenance', name='bedstatus', create_type=False), nullable=False, server_default='available'),
        sa.Column('bed_type', sa.String(length=50), nullable=True),
        sa.Column('charge_per_day', sa.Numeric(10, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.ForeignKeyConstraint(['ward_id'], ['wards.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_beds_id'), 'beds', ['id'], unique=False)
    op.create_index(op.f('ix_beds_bed_number'), 'beds', ['bed_number'], unique=False)
    
    # Create admissions table
    op.create_table('admissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('encounter_id', sa.Integer(), nullable=True),
        sa.Column('ward_id', sa.Integer(), nullable=False),
        sa.Column('bed_id', sa.Integer(), nullable=False),
        sa.Column('admitted_by_id', sa.Integer(), nullable=False),
        sa.Column('discharged_by_id', sa.Integer(), nullable=True),
        sa.Column('admission_number', sa.String(length=50), nullable=False),
        sa.Column('status', postgresql.ENUM('admitted', 'discharged', 'transferred', 'absconded', name='admissionstatus', create_type=False), nullable=False, server_default='admitted'),
        sa.Column('admission_date', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('discharge_date', sa.DateTime(), nullable=True),
        sa.Column('expected_discharge_date', sa.DateTime(), nullable=True),
        sa.Column('admission_reason', sa.Text(), nullable=True),
        sa.Column('diagnosis', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('transferred_from_ward_id', sa.Integer(), nullable=True),
        sa.Column('transferred_to_ward_id', sa.Integer(), nullable=True),
        sa.Column('transfer_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        sa.ForeignKeyConstraint(['encounter_id'], ['encounters.id'], ),
        sa.ForeignKeyConstraint(['ward_id'], ['wards.id'], ),
        sa.ForeignKeyConstraint(['bed_id'], ['beds.id'], ),
        sa.ForeignKeyConstraint(['admitted_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['discharged_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['transferred_from_ward_id'], ['wards.id'], ),
        sa.ForeignKeyConstraint(['transferred_to_ward_id'], ['wards.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('admission_number')
    )
    op.create_index(op.f('ix_admissions_id'), 'admissions', ['id'], unique=False)
    op.create_index(op.f('ix_admissions_admission_number'), 'admissions', ['admission_number'], unique=True)
    
    # Create doctor_duties table
    op.create_table('doctor_duties',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=False),
        sa.Column('duty_date', sa.DateTime(), nullable=False),
        sa.Column('shift_start', sa.DateTime(), nullable=False),
        sa.Column('shift_end', sa.DateTime(), nullable=False),
        sa.Column('shift_type', sa.String(length=50), nullable=True),
        sa.Column('is_on_duty', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='scheduled'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_doctor_duties_id'), 'doctor_duties', ['id'], unique=False)
    op.create_index(op.f('ix_doctor_duties_duty_date'), 'doctor_duties', ['duty_date'], unique=False)
    
    # Add department_type to appointments table
    op.add_column('appointments', sa.Column('department_type', sa.String(length=20), nullable=True, server_default='opd'))


def downgrade() -> None:
    """Downgrade schema - Remove IPD models."""
    # Drop tables in reverse order
    op.drop_table('doctor_duties')
    op.drop_table('admissions')
    op.drop_table('beds')
    op.drop_table('wards')
    
    # Remove department_type from appointments
    op.drop_column('appointments', 'department_type')
    
    # Drop enum types (optional - may be used by other tables)
    # Note: We don't drop enums here as they might be used elsewhere
    # op.execute("DROP TYPE IF EXISTS admissionstatus")
    # op.execute("DROP TYPE IF EXISTS bedstatus")
    # op.execute("DROP TYPE IF EXISTS wardstatus")
