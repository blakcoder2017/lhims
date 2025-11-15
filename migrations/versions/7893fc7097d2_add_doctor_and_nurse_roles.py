"""add_doctor_and_nurse_roles

Revision ID: 7893fc7097d2
Revises: ab1649f023bd
Create Date: 2025-11-12 11:40:32.692372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7893fc7097d2'
down_revision: Union[str, Sequence[str], None] = 'ab1649f023bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Doctor and Nurse roles, separating them from Clinician role."""
    # Insert new roles if they don't exist
    op.execute("""
        INSERT INTO roles (name, description)
        VALUES 
            ('Doctor', 'Physicians - Clinical encounters, diagnoses, and treatment orders'),
            ('Nurse', 'Nurses - Patient care, triage, and clinical support')
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    """Remove Doctor and Nurse roles."""
    # Note: This will fail if there are users assigned to these roles
    # In production, you'd want to migrate users back to Clinician first
    op.execute("""
        DELETE FROM roles WHERE name IN ('Doctor', 'Nurse');
    """)
