"""fix_appointmenttype_enum - Add missing values to appointmenttype enum

Revision ID: fix_appointmenttype_enum
Revises: 7161e96c17d1
Create Date: 2026-02-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_appointmenttype_enum'
down_revision: Union[str, Sequence[str], None] = '7161e96c17d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing values to appointmenttype enum to match Python AppointmentType enum."""
    # The appointmenttype enum should have these values:
    # consultation, follow_up, procedure, emergency, lab_work, radiology, other, walk_in
    #
    # Current database values: emergency, follow_up, scheduled, walk_in (incomplete)
    #
    # Add missing values one by one (PostgreSQL requires sequential ALTER TYPE for enums)
    
    # Get current enum values to check what needs to be added
    op.execute("""
        DO $$
        BEGIN
            -- Add 'consultation' if not exists
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
                WHERE pg_type.typname = 'appointmenttype' 
                AND pg_enum.enumlabel = 'consultation'
            ) THEN
                ALTER TYPE appointmenttype ADD VALUE IF NOT EXISTS 'consultation';
            END IF;
            
            -- Add 'procedure' if not exists
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
                WHERE pg_type.typname = 'appointmenttype' 
                AND pg_enum.enumlabel = 'procedure'
            ) THEN
                ALTER TYPE appointmenttype ADD VALUE IF NOT EXISTS 'procedure';
            END IF;
            
            -- Add 'lab_work' if not exists
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
                WHERE pg_type.typname = 'appointmenttype' 
                AND pg_enum.enumlabel = 'lab_work'
            ) THEN
                ALTER TYPE appointmenttype ADD VALUE IF NOT EXISTS 'lab_work';
            END IF;
            
            -- Add 'radiology' if not exists
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
                WHERE pg_type.typname = 'appointmenttype' 
                AND pg_enum.enumlabel = 'radiology'
            ) THEN
                ALTER TYPE appointmenttype ADD VALUE IF NOT EXISTS 'radiology';
            END IF;
            
            -- Add 'other' if not exists
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
                WHERE pg_type.typname = 'appointmenttype' 
                AND pg_enum.enumlabel = 'other'
            ) THEN
                ALTER TYPE appointmenttype ADD VALUE IF NOT EXISTS 'other';
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Remove the added values from appointmenttype enum."""
    # Note: PostgreSQL doesn't support removing enum values easily
    # This is a one-way migration to fix the enum
    pass
