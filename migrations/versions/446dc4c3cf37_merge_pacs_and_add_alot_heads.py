"""merge_pacs_and_add_alot_heads

Revision ID: 446dc4c3cf37
Revises: 5c95194086bd, 23d7905a6d81
Create Date: 2025-11-10 11:35:30.098877

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '446dc4c3cf37'
down_revision: Union[str, Sequence[str], None] = ('5c95194086bd', '23d7905a6d81')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
