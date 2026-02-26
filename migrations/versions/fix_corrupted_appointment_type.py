"""fix_corrupted_appointment_type - Fix corrupted appointment_type values in scheduled_appointments

Revision ID: fix_corrupted_appointment_type
Revises: 7161e96c17d1
Create Date: 2026-02-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_corrupted_appointment_type'
down_revision: Union[str, Sequence[str], None] = '7161e96c17d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix corrupted appointment_type values.

    The appointment_type column should contain valid AppointmentType values:
    consultation, follow_up, procedure, emergency, lab_work, radiology, other, walk_in

    The status column should contain valid AppointmentStatus values:
    scheduled, confirmed, checked_in, in_progress, cancelled, completed, no_show, rescheduled

    This migration fixes rows where status values were incorrectly placed in appointment_type.
    """
    # Update rows where appointment_type contains status values
    op.execute("""
        UPDATE scheduled_appointments
        SET appointment_type = 'consultation'
        WHERE appointment_type IN (
            'scheduled', 'confirmed', 'checked_in', 'in_progress',
            'cancelled', 'completed', 'no_show', 'rescheduled'
        )
        AND appointment_type NOT IN (
            'consultation', 'follow_up', 'procedure', 'emergency',
            'lab_work', 'radiology', 'other', 'walk_in'
        )
    """)


def downgrade() -> None:
    """This is a data fix, not reversible."""
    pass
