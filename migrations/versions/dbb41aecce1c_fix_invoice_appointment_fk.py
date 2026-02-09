"""fix invoice appointment foreign key

Revision ID: dbb41aecce1c
Revises: restructure_appointments
Create Date: 2026-01-09 21:17:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'dbb41aecce1c'
down_revision: Union[str, Sequence[str], None] = 'restructure_appointments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the old foreign key constraint that references the non-existent 'appointments' table
    # and create a new one that references 'scheduled_appointments'
    
    # First, drop the old FK constraint if it exists
    op.execute('ALTER TABLE invoices DROP CONSTRAINT IF EXISTS invoices_appointment_id_fkey')
    
    # Add the new FK constraint pointing to scheduled_appointments
    op.execute('ALTER TABLE invoices ADD CONSTRAINT invoices_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES scheduled_appointments(id)')


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the new FK constraint
    op.execute('ALTER TABLE invoices DROP CONSTRAINT IF EXISTS invoices_appointment_id_fkey')
    
    # Restore the old FK constraint (pointing to non-existent table - this is intentional for downgrade)
    # Note: This will fail if the appointments table doesn't exist, which is expected during downgrade
    op.execute('ALTER TABLE invoices ADD CONSTRAINT invoices_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES appointments(id)')
