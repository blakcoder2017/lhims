"""fix_appointment_fk_to_scheduled_appointments

Revision ID: cdd784e99ee7
Revises: add_queue_entry_id_to_opd_visits
Create Date: 2026-01-10 01:36:51.804424

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cdd784e99ee7'
down_revision: Union[str, Sequence[str], None] = 'e9784c96e38d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # First, set invalid appointment_id references to NULL
    # This is needed because encounters may reference appointments that don't exist in scheduled_appointments
    op.execute("UPDATE encounters SET appointment_id = NULL WHERE appointment_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM scheduled_appointments WHERE id = encounters.appointment_id)")
    op.execute("UPDATE invoices SET appointment_id = NULL WHERE appointment_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM scheduled_appointments WHERE id = invoices.appointment_id)")

    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('encounters') as batch_op:
        batch_op.drop_constraint('encounters_appointment_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key('encounters_appointment_id_fkey', 'scheduled_appointments', ['appointment_id'], ['id'])

    with op.batch_alter_table('invoices') as batch_op:
        batch_op.drop_constraint('invoices_appointment_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key('invoices_appointment_id_fkey', 'scheduled_appointments', ['appointment_id'], ['id'])

    with op.batch_alter_table('opd_visits') as batch_op:
        batch_op.drop_constraint('opd_visits_appointment_id_fkey', type_='foreignkey')
        batch_op.drop_column('appointment_id')

    # Now drop the old appointments table
    op.drop_index('ix_appointments_id', table_name='appointments')
    op.drop_table('appointments')


def downgrade() -> None:
    """Downgrade schema."""
    # Drop new FK constraints
    op.drop_constraint('invoices_appointment_id_fkey', 'invoices', type_='foreignkey')
    op.drop_constraint('encounters_appointment_id_fkey', 'encounters', type_='foreignkey')
    
    # Recreate appointments table
    op.create_table('appointments',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('patient_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('department', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('assigned_clinician_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('created_by_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('appointment_type', postgresql.ENUM('WALK_IN', 'SCHEDULED', 'EMERGENCY', 'FOLLOW_UP', name='appointmenttype'), autoincrement=False, nullable=False),
    sa.Column('status', postgresql.ENUM('SCHEDULED', 'CHECKED_IN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW', name='appointmentstatus'), autoincrement=False, nullable=False),
    sa.Column('priority', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('scheduled_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('checked_in_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('started_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('completed_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('chief_complaint', sa.VARCHAR(length=500), autoincrement=False, nullable=True),
    sa.Column('notes', sa.VARCHAR(length=1000), autoincrement=False, nullable=True),
    sa.Column('queue_number', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('is_active', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=True),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('department_type', sa.VARCHAR(length=20), server_default=sa.text("'opd'::character varying"), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['assigned_clinician_id'], ['users.id'], name='appointments_assigned_clinician_id_fkey'),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name='appointments_created_by_id_fkey'),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name='appointments_patient_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='appointments_pkey')
    )
    op.create_index('ix_appointments_id', 'appointments', ['id'], unique=False)
    
    # Restore FK constraints pointing to appointments
    op.create_foreign_key('encounters_appointment_id_fkey', 'encounters', 'appointments', ['appointment_id'], ['id'])
    op.create_foreign_key('invoices_appointment_id_fkey', 'invoices', 'appointments', ['appointment_id'], ['id'])
    op.create_foreign_key('opd_visits_appointment_id_fkey', 'opd_visits', 'appointments', ['appointment_id'], ['id'])
    
    # Restore column
    op.add_column('opd_visits', sa.Column('appointment_id', sa.INTEGER(), autoincrement=False, nullable=True))
