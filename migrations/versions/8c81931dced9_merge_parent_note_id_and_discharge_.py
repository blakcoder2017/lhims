"""merge parent_note_id and discharge_clearances

Revision ID: 8c81931dced9
Revises: ('f9468a749c85', '0fc735668649')
Create Date: 2025-11-18 00:33:34.079290

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c81931dced9'
down_revision: Union[str, Sequence[str], None] = ('f9468a749c85', '0fc735668649')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
