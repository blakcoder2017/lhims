"""merge heads

Revision ID: 803bec0a2275
Revises: 2091a86885bd, 24ae069a97c5
Create Date: 2026-02-23 12:16:09.210951

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '803bec0a2275'
down_revision: Union[str, Sequence[str], None] = ('2091a86885bd', '24ae069a97c5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
