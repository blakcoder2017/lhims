"""add_auto_closed_status_to_encounters - Add AUTO_CLOSED status to encounterstatus enum

Revision ID: add_auto_closed_status_to_encounters
Revises: 
Create Date: 2026-02-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_auto_closed_status_to_encounters'
down_revision: Union[str, Sequence[str], None] = 'fix_corrupted_appointment_type'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add AUTO_CLOSED status to encounterstatus enum for automatic encounter closure."""
    op.execute("""
        DO $$
        BEGIN
            -- Add 'auto_closed' if not exists
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
                WHERE pg_type.typname = 'encounterstatus' 
                AND pg_enum.enumlabel = 'auto_closed'
            ) THEN
                ALTER TYPE encounterstatus ADD VALUE IF NOT EXISTS 'auto_closed';
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Remove the AUTO_CLOSED status from encounterstatus enum."""
    # Note: PostgreSQL doesn't support removing enum values easily
    # This is a one-way migration
    pass
