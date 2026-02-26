"""Add antenatal_visit_id column to birth_records

Revision ID: add_antenatal_visit_id_to_birth_records
Revises: 
Create Date: 2026-02-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_antenatal_visit_id_to_birth_records'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'birth_records',
        sa.Column('antenatal_visit_id', sa.Integer(), sa.ForeignKey('antenatal_visits.id'), nullable=True)
    )
    op.create_index(
        op.f('ix_birth_records_antenatal_visit_id'),
        'birth_records',
        ['antenatal_visit_id'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_birth_records_antenatal_visit_id'),
        table_name='birth_records'
    )
    op.drop_column('birth_records', 'antenatal_visit_id')
