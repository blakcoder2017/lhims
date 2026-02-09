"""add clinical encounter and cpoe models

Revision ID: be121fa1ffe8
Revises: 31350ee33b80
Create Date: 2025-01-XX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'be121fa1ffe8'
down_revision: Union[str, Sequence[str], None] = '31350ee33b80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum types first (PostgreSQL requirement)
    # Using DO blocks to check if type exists before creating
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE encounterstatus AS ENUM ('in_progress', 'completed', 'cancelled');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE orderstatus AS ENUM ('pending', 'ordered', 'in_progress', 'completed', 'cancelled');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create encounters table
    op.create_table('encounters',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('appointment_id', sa.Integer(), nullable=True),
    sa.Column('clinician_id', sa.Integer(), nullable=False),
    sa.Column('status', postgresql.ENUM('in_progress', 'completed', 'cancelled', name='encounterstatus', create_type=False), nullable=False),
    sa.Column('encounter_date', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('chief_complaint', sa.Text(), nullable=True),
    sa.Column('history_of_present_illness', sa.Text(), nullable=True),
    sa.Column('past_medical_history', sa.Text(), nullable=True),
    sa.Column('allergies', sa.Text(), nullable=True),
    sa.Column('medications', sa.Text(), nullable=True),
    sa.Column('physical_examination', sa.Text(), nullable=True),
    sa.Column('assessment', sa.Text(), nullable=True),
    sa.Column('plan', sa.Text(), nullable=True),
    sa.Column('primary_diagnosis_code', sa.String(length=20), nullable=True),
    sa.Column('primary_diagnosis_description', sa.String(length=500), nullable=True),
    sa.Column('secondary_diagnosis_codes', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ),
    sa.ForeignKeyConstraint(['clinician_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_encounters_id'), 'encounters', ['id'], unique=False)
    
    # Create lab_orders table
    op.create_table('lab_orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('encounter_id', sa.Integer(), nullable=False),
    sa.Column('ordered_by_id', sa.Integer(), nullable=False),
    sa.Column('test_name', sa.String(length=200), nullable=False),
    sa.Column('test_code', sa.String(length=50), nullable=True),
    sa.Column('instructions', sa.Text(), nullable=True),
    sa.Column('priority', sa.String(length=20), nullable=True),
    sa.Column('status', postgresql.ENUM('pending', 'ordered', 'in_progress', 'completed', 'cancelled', name='orderstatus', create_type=False), nullable=False),
    sa.Column('ordered_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('result', sa.Text(), nullable=True),
    sa.Column('result_entered_by_id', sa.Integer(), nullable=True),
    sa.Column('result_entered_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['encounter_id'], ['encounters.id'], ),
    sa.ForeignKeyConstraint(['ordered_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['result_entered_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lab_orders_id'), 'lab_orders', ['id'], unique=False)
    
    # Create radiology_orders table
    op.create_table('radiology_orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('encounter_id', sa.Integer(), nullable=False),
    sa.Column('ordered_by_id', sa.Integer(), nullable=False),
    sa.Column('study_type', sa.String(length=200), nullable=False),
    sa.Column('study_code', sa.String(length=50), nullable=True),
    sa.Column('body_part', sa.String(length=100), nullable=True),
    sa.Column('clinical_indication', sa.Text(), nullable=True),
    sa.Column('instructions', sa.Text(), nullable=True),
    sa.Column('priority', sa.String(length=20), nullable=True),
    sa.Column('status', postgresql.ENUM('pending', 'ordered', 'in_progress', 'completed', 'cancelled', name='orderstatus', create_type=False), nullable=False),
    sa.Column('ordered_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('report', sa.Text(), nullable=True),
    sa.Column('report_entered_by_id', sa.Integer(), nullable=True),
    sa.Column('report_entered_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['encounter_id'], ['encounters.id'], ),
    sa.ForeignKeyConstraint(['ordered_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['report_entered_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_radiology_orders_id'), 'radiology_orders', ['id'], unique=False)
    
    # Create prescriptions table
    op.create_table('prescriptions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('encounter_id', sa.Integer(), nullable=False),
    sa.Column('prescribed_by_id', sa.Integer(), nullable=False),
    sa.Column('medication_name', sa.String(length=200), nullable=False),
    sa.Column('medication_code', sa.String(length=50), nullable=True),
    sa.Column('dosage', sa.String(length=100), nullable=False),
    sa.Column('frequency', sa.String(length=100), nullable=False),
    sa.Column('duration', sa.String(length=100), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=True),
    sa.Column('instructions', sa.Text(), nullable=True),
    sa.Column('status', postgresql.ENUM('pending', 'ordered', 'in_progress', 'completed', 'cancelled', name='orderstatus', create_type=False), nullable=False),
    sa.Column('prescribed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('dispensed_at', sa.DateTime(), nullable=True),
    sa.Column('dispensed_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['encounter_id'], ['encounters.id'], ),
    sa.ForeignKeyConstraint(['prescribed_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['dispensed_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prescriptions_id'), 'prescriptions', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order
    op.drop_index(op.f('ix_prescriptions_id'), table_name='prescriptions')
    op.drop_table('prescriptions')
    
    op.drop_index(op.f('ix_radiology_orders_id'), table_name='radiology_orders')
    op.drop_table('radiology_orders')
    
    op.drop_index(op.f('ix_lab_orders_id'), table_name='lab_orders')
    op.drop_table('lab_orders')
    
    op.drop_index(op.f('ix_encounters_id'), table_name='encounters')
    op.drop_table('encounters')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS orderstatus")
    op.execute("DROP TYPE IF EXISTS encounterstatus")

