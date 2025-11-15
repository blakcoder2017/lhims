"""add_detained_status_to_encounters

Revision ID: ef41500e9f15
Revises: 7893fc7097d2
Create Date: 2025-11-12 11:52:03.142098

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef41500e9f15'
down_revision: Union[str, Sequence[str], None] = '7893fc7097d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 'detained' status to encounterstatus enum."""
    # Add 'detained' value to the existing encounterstatus enum
    op.execute("""
        ALTER TYPE encounterstatus ADD VALUE IF NOT EXISTS 'detained';
    """)


def downgrade() -> None:
    """Remove 'detained' status from encounterstatus enum."""
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # In production, you'd need to:
    # 1. Create a new enum without 'detained'
    # 2. Update all records to use the new enum
    # 3. Drop the old enum and rename the new one
    # For now, we'll leave a comment
    pass
    # op.execute("""
    #     -- This requires manual intervention:
    #     -- 1. Update all 'detained' encounters to 'in_progress' or 'completed'
    #     -- 2. Recreate the enum type without 'detained'
    #     -- 3. Update the column to use the new enum
    # """)
