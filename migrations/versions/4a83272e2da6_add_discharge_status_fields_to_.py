"""add_discharge_status_fields_to_admissions

Revision ID: 4a83272e2da6
Revises: 8c81931dced9
Create Date: 2025-11-18 09:55:48.053663

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a83272e2da6'
down_revision: Union[str, Sequence[str], None] = '8c81931dced9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create DischargeStatus enum type
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE dischargestatus AS ENUM ('normal', 'death', 'referral');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Add discharge columns to admissions table
    op.add_column('admissions', sa.Column('discharge_status', sa.Enum('normal', 'death', 'referral', name='dischargestatus', create_type=False), nullable=True))
    op.add_column('admissions', sa.Column('discharge_diagnosis', sa.Text(), nullable=True))
    op.add_column('admissions', sa.Column('discharge_notes', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove discharge columns
    op.drop_column('admissions', 'discharge_notes')
    op.drop_column('admissions', 'discharge_diagnosis')
    op.drop_column('admissions', 'discharge_status')
    
    # Drop enum type (only if no other tables use it)
    op.execute("DROP TYPE IF EXISTS dischargestatus")
