"""add_discharge_clearance_model

Revision ID: 0fc735668649
Revises: 37a5a3afe701
Create Date: 2025-11-17 22:38:49.087258

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0fc735668649'
down_revision: Union[str, None] = '37a5a3afe701'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create discharge_clearances table
    op.create_table(
        'discharge_clearances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admission_id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('payment_cleared', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('payment_cleared_at', sa.DateTime(), nullable=True),
        sa.Column('payment_cleared_by_id', sa.Integer(), nullable=True),
        sa.Column('nursing_cleared', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('nursing_cleared_at', sa.DateTime(), nullable=True),
        sa.Column('nursing_cleared_by_id', sa.Integer(), nullable=True),
        sa.Column('payment_notes', sa.Text(), nullable=True),
        sa.Column('nursing_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['admission_id'], ['admissions.id'], name='fk_discharge_clearances_admission_id_admissions'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name='fk_discharge_clearances_patient_id_patients'),
        sa.ForeignKeyConstraint(['payment_cleared_by_id'], ['users.id'], name='fk_discharge_clearances_payment_cleared_by_id_users'),
        sa.ForeignKeyConstraint(['nursing_cleared_by_id'], ['users.id'], name='fk_discharge_clearances_nursing_cleared_by_id_users'),
        sa.UniqueConstraint('admission_id', name='uq_discharge_clearances_admission_id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_discharge_clearances_id'), 'discharge_clearances', ['id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_discharge_clearances_id'), table_name='discharge_clearances')
    
    # Drop discharge_clearances table
    op.drop_table('discharge_clearances')
