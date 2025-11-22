"""add_procedure_catalog_id_to_procedures

Revision ID: 53e1c97d2944
Revises: ddf455d3850c
Create Date: 2025-11-20 14:52:42.795185

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53e1c97d2944'
down_revision: Union[str, Sequence[str], None] = 'ddf455d3850c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add procedure_catalog_id foreign key column to procedures table
    op.add_column('procedures', sa.Column('procedure_catalog_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_procedures_procedure_catalog_id',
        'procedures',
        'procedure_catalog',
        ['procedure_catalog_id'],
        ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove procedure_catalog_id foreign key and column
    op.drop_constraint('fk_procedures_procedure_catalog_id', 'procedures', type_='foreignkey')
    op.drop_column('procedures', 'procedure_catalog_id')
