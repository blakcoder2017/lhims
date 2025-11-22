"""add_triage_level_assignment

Revision ID: 866b026e17f1
Revises: 0849a2dfc8fa
Create Date: 2025-11-17 22:27:09.736156

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '866b026e17f1'
down_revision: Union[str, None] = '0849a2dfc8fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add triage level assignment columns to triage_vitals table
    op.add_column('triage_vitals', sa.Column('triage_level', sa.String(length=20), nullable=True))
    op.add_column('triage_vitals', sa.Column('triage_category', sa.String(length=50), nullable=True))
    op.add_column('triage_vitals', sa.Column('triage_assigned_by_id', sa.Integer(), nullable=True))
    op.add_column('triage_vitals', sa.Column('triage_assigned_at', sa.DateTime(), nullable=True))
    
    # Create foreign key constraint for triage_assigned_by_id
    op.create_foreign_key(
        'fk_triage_vitals_triage_assigned_by_id_users',
        'triage_vitals',
        'users',
        ['triage_assigned_by_id'],
        ['id']
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint('fk_triage_vitals_triage_assigned_by_id_users', 'triage_vitals', type_='foreignkey')
    
    # Drop triage level columns
    op.drop_column('triage_vitals', 'triage_assigned_at')
    op.drop_column('triage_vitals', 'triage_assigned_by_id')
    op.drop_column('triage_vitals', 'triage_category')
    op.drop_column('triage_vitals', 'triage_level')
