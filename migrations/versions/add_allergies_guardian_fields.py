"""Add allergies and guardian fields to admission

Revision ID: add_allergies_guardian_fields
Revises: 866b026e17f1
Create Date: 2026-02-22 11:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from typing import Union, Sequence

# revision identifiers, used by Alembic.
revision: str = 'add_allergies_guardian_fields'
down_revision: Union[str, Sequence[str], None] = '866b026e17f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add allergies field
    op.add_column('admissions', sa.Column('allergies', sa.Text(), nullable=True))
    
    # Add guardian fields
    op.add_column('admissions', sa.Column('guardian_name', sa.String(200), nullable=True))
    op.add_column('admissions', sa.Column('guardian_phone', sa.String(20), nullable=True))
    op.add_column('admissions', sa.Column('guardian_relationship', sa.String(50), nullable=True))
    op.add_column('admissions', sa.Column('guardian_address', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove guardian fields
    op.drop_column('admissions', 'guardian_address')
    op.drop_column('admissions', 'guardian_relationship')
    op.drop_column('admissions', 'guardian_phone')
    op.drop_column('admissions', 'guardian_name')
    
    # Remove allergies field
    op.drop_column('admissions', 'allergies')
