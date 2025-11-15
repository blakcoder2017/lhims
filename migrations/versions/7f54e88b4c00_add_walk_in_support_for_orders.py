"""add_walk_in_support_for_orders

Revision ID: 7f54e88b4c00
Revises: 1949ab497e5a
Create Date: 2025-11-13 19:53:43.663365

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f54e88b4c00'
down_revision: Union[str, Sequence[str], None] = '1949ab497e5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Make encounter_id optional in lab_orders and add walk-in fields
    op.alter_column('lab_orders', 'encounter_id', nullable=True)
    op.add_column('lab_orders', sa.Column('patient_id', sa.Integer(), nullable=True))
    op.add_column('lab_orders', sa.Column('is_walk_in', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('lab_orders', sa.Column('checked_in_at', sa.DateTime(), nullable=True))
    op.add_column('lab_orders', sa.Column('checked_in_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_lab_orders_patient_id', 'lab_orders', 'patients', ['patient_id'], ['id'])
    op.create_foreign_key('fk_lab_orders_checked_in_by', 'lab_orders', 'users', ['checked_in_by_id'], ['id'])
    
    # Make encounter_id optional in radiology_orders and add walk-in fields
    op.alter_column('radiology_orders', 'encounter_id', nullable=True)
    op.add_column('radiology_orders', sa.Column('patient_id', sa.Integer(), nullable=True))
    op.add_column('radiology_orders', sa.Column('is_walk_in', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('radiology_orders', sa.Column('checked_in_at', sa.DateTime(), nullable=True))
    op.add_column('radiology_orders', sa.Column('checked_in_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_radiology_orders_patient_id', 'radiology_orders', 'patients', ['patient_id'], ['id'])
    op.create_foreign_key('fk_radiology_orders_checked_in_by', 'radiology_orders', 'users', ['checked_in_by_id'], ['id'])
    
    # Add walk-in fields to procedures
    op.add_column('procedures', sa.Column('is_walk_in', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('procedures', sa.Column('checked_in_at', sa.DateTime(), nullable=True))
    op.add_column('procedures', sa.Column('checked_in_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_procedures_checked_in_by', 'procedures', 'users', ['checked_in_by_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove walk-in fields from procedures
    op.drop_constraint('fk_procedures_checked_in_by', 'procedures', type_='foreignkey')
    op.drop_column('procedures', 'checked_in_by_id')
    op.drop_column('procedures', 'checked_in_at')
    op.drop_column('procedures', 'is_walk_in')
    
    # Remove walk-in fields from radiology_orders and make encounter_id required
    op.drop_constraint('fk_radiology_orders_checked_in_by', 'radiology_orders', type_='foreignkey')
    op.drop_constraint('fk_radiology_orders_patient_id', 'radiology_orders', type_='foreignkey')
    op.drop_column('radiology_orders', 'checked_in_by_id')
    op.drop_column('radiology_orders', 'checked_in_at')
    op.drop_column('radiology_orders', 'is_walk_in')
    op.drop_column('radiology_orders', 'patient_id')
    op.alter_column('radiology_orders', 'encounter_id', nullable=False)
    
    # Remove walk-in fields from lab_orders and make encounter_id required
    op.drop_constraint('fk_lab_orders_checked_in_by', 'lab_orders', type_='foreignkey')
    op.drop_constraint('fk_lab_orders_patient_id', 'lab_orders', type_='foreignkey')
    op.drop_column('lab_orders', 'checked_in_by_id')
    op.drop_column('lab_orders', 'checked_in_at')
    op.drop_column('lab_orders', 'is_walk_in')
    op.drop_column('lab_orders', 'patient_id')
    op.alter_column('lab_orders', 'encounter_id', nullable=False)
