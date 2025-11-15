"""add_patient_number_field

Revision ID: 612fbff46dd1
Revises: a76075972d71
Create Date: 2025-11-11 09:56:04.031383

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '612fbff46dd1'
down_revision: Union[str, Sequence[str], None] = 'a76075972d71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add patient_number column to patients table
    op.add_column('patients', sa.Column('patient_number', sa.String(), nullable=True))
    # Create index on patient_number
    op.create_index(op.f('ix_patients_patient_number'), 'patients', ['patient_number'], unique=True)
    
    # Generate patient numbers for existing patients
    # This will be done in a data migration script if needed
    # For now, new patients will get auto-generated numbers


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_patients_patient_number'), table_name='patients')
    op.drop_column('patients', 'patient_number')
