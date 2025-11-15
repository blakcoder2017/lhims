"""make_national_id_optional_phase1

Revision ID: 5d58e5cf533d
Revises: 6c495c397f81
Create Date: 2025-11-11 19:33:32.520074

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d58e5cf533d'
down_revision: Union[str, Sequence[str], None] = '6c495c397f81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Make national_id nullable (already nullable, but ensure unique index allows NULLs)."""
    # national_id was already created as nullable=True in migration 82cc700994b4
    # PostgreSQL unique indexes allow multiple NULL values by default
    # This migration is a no-op but documents the change for Phase 1
    # The model and schema have been updated to reflect that national_id is optional
    pass


def downgrade() -> None:
    """Downgrade schema - No changes needed."""
    # national_id remains nullable even after downgrade
    pass
