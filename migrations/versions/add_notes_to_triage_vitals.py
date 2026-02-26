"""Add notes column to triage_vitals table

Revision ID: add_notes_to_triage_vitals
Revises: 
Create Date: 2026-02-21 16:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_notes_to_triage_vitals'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add notes column to triage_vitals table."""
    op.add_column('triage_vitals', sa.Column('notes', sa.Text(), nullable=True))


def downgrade():
    """Remove notes column from triage_vitals table."""
    op.drop_column('triage_vitals', 'notes')
