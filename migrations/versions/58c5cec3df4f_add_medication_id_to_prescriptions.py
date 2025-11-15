"""add_medication_id_to_prescriptions

Revision ID: 58c5cec3df4f
Revises: 4245aa8002ff
Create Date: 2025-11-11 11:43:04.165059

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58c5cec3df4f'
down_revision: Union[str, Sequence[str], None] = '4245aa8002ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add medication_id column to prescriptions table
    op.add_column('prescriptions', sa.Column('medication_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_prescriptions_medication_id_medications',
        'prescriptions', 'medications',
        ['medication_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index(op.f('ix_prescriptions_medication_id'), 'prescriptions', ['medication_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove medication_id column from prescriptions table
    op.drop_index(op.f('ix_prescriptions_medication_id'), table_name='prescriptions')
    op.drop_constraint('fk_prescriptions_medication_id_medications', 'prescriptions', type_='foreignkey')
    op.drop_column('prescriptions', 'medication_id')
