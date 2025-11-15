"""Finalize TriageVitals relationships

Revision ID: 72e2dc0c34b9
Revises: 6a3fa827853a
Create Date: 2025-11-09 03:05:11.430186

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72e2dc0c34b9'
down_revision: Union[str, Sequence[str], None] = '6a3fa827853a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create triage_vitals table
    op.create_table('triage_vitals',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('recorded_by_id', sa.Integer(), nullable=False),
    sa.Column('temperature', sa.Float(), nullable=False),
    sa.Column('blood_pressure', sa.String(length=50), nullable=False),
    sa.Column('recorded_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['recorded_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_triage_vitals_id'), 'triage_vitals', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop triage_vitals table
    op.drop_index(op.f('ix_triage_vitals_id'), table_name='triage_vitals')
    op.drop_table('triage_vitals')
