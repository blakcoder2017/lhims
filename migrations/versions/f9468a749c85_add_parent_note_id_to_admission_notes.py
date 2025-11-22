"""add_parent_note_id_to_admission_notes

Revision ID: f9468a749c85
Revises: f0d61f438a43
Create Date: 2025-11-18 00:22:20.357613

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f9468a749c85'
down_revision: Union[str, Sequence[str], None] = 'f0d61f438a43'  # Based on differential diagnosis migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add parent_note_id column to admission_notes for threaded replies
    op.add_column('admission_notes', sa.Column('parent_note_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_admission_notes_parent_note_id', 'admission_notes', 'admission_notes', ['parent_note_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove parent_note_id column from admission_notes
    # First, drop the foreign key constraint if it exists
    from sqlalchemy import inspect
    from sqlalchemy.exc import ProgrammingError
    
    # Try to drop the constraint, ignore if it doesn't exist
    try:
        op.drop_constraint('fk_admission_notes_parent_note_id', 'admission_notes', type_='foreignkey')
    except ProgrammingError:
        pass  # Constraint might not exist
    
    # Drop the column if it exists
    try:
        op.drop_column('admission_notes', 'parent_note_id')
    except ProgrammingError:
        pass  # Column might not exist
