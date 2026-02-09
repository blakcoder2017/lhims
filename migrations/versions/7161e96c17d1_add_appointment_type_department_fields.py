"""add_appointment_type_department_fields

Revision ID: 7161e96c17d1
Revises: restructure_appointments
Create Date: 2026-01-09 20:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7161e96c17d1'
down_revision: Union[str, Sequence[str], None] = 'restructure_appointments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add appointment_type, department, and scheduled_date fields to scheduled_appointments table."""
    
    # Create the appointmenttype enum if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE appointmenttype AS ENUM ('consultation', 'follow_up', 'procedure', 'emergency', 'lab_work', 'radiology', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Add department column
    op.add_column('scheduled_appointments', sa.Column('department', sa.String(length=100), nullable=True))
    
    # Add appointment_type column with default
    op.add_column('scheduled_appointments', sa.Column('appointment_type', postgresql.ENUM('consultation', 'follow_up', 'procedure', 'emergency', 'lab_work', 'radiology', 'other', name='appointmenttype', create_type=False), nullable=False, server_default='consultation'))
    
    # Rename appointment_date to scheduled_date (if needed) or add scheduled_date as alias
    # Since appointment_date already exists, we'll add a computed column approach via application logic
    # The model has a property for backward compatibility, so no DB change needed for appointment_date


def downgrade() -> None:
    """Remove appointment_type and department fields from scheduled_appointments table."""
    
    # Drop the columns
    op.drop_column('scheduled_appointments', 'appointment_type')
    op.drop_column('scheduled_appointments', 'department')
    
    # Drop the enum type (will fail if other tables use it, but that's ok for downgrade)
    op.execute('DROP TYPE IF EXISTS appointmenttype')
