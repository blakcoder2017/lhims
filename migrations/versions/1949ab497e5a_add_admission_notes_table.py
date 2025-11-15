"""add_admission_notes_table

Revision ID: 1949ab497e5a
Revises: ae4de6715452
Create Date: 2025-11-13 19:51:47.813066

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1949ab497e5a'
down_revision: Union[str, Sequence[str], None] = 'ae4de6715452'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create admission_notes table
    op.create_table('admission_notes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('admission_id', sa.Integer(), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('note', sa.Text(), nullable=False),
    sa.Column('note_type', sa.String(length=50), nullable=True, server_default='general'),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
    sa.ForeignKeyConstraint(['admission_id'], ['admissions.id'], ),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admission_notes_id'), 'admission_notes', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_admission_notes_id'), table_name='admission_notes')
    op.drop_table('admission_notes')
