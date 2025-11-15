"""add_comprehensive_vital_signs_fields

Revision ID: 6c495c397f81
Revises: 58c5cec3df4f
Create Date: 2025-11-11 12:41:45.269445

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '6c495c397f81'
down_revision: Union[str, Sequence[str], None] = '58c5cec3df4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new vital signs fields to triage_vitals table
    op.add_column('triage_vitals', sa.Column('systolic_bp', sa.Integer(), nullable=True))
    op.add_column('triage_vitals', sa.Column('diastolic_bp', sa.Integer(), nullable=True))
    op.add_column('triage_vitals', sa.Column('pulse_rate', sa.Integer(), nullable=True))
    op.add_column('triage_vitals', sa.Column('respiratory_rate', sa.Integer(), nullable=True))
    op.add_column('triage_vitals', sa.Column('oxygen_saturation', sa.Integer(), nullable=True))
    op.add_column('triage_vitals', sa.Column('weight', sa.Numeric(precision=5, scale=2), nullable=True))
    op.add_column('triage_vitals', sa.Column('height', sa.Numeric(precision=5, scale=2), nullable=True))
    op.add_column('triage_vitals', sa.Column('bmi', sa.Numeric(precision=5, scale=2), nullable=True))
    op.add_column('triage_vitals', sa.Column('pain_scale', sa.Integer(), nullable=True))
    
    # Make blood_pressure nullable (it was required before, now optional)
    op.alter_column('triage_vitals', 'blood_pressure',
                    existing_type=sa.String(50),
                    nullable=True)


def downgrade() -> None:
    # Remove the new columns
    op.drop_column('triage_vitals', 'pain_scale')
    op.drop_column('triage_vitals', 'bmi')
    op.drop_column('triage_vitals', 'height')
    op.drop_column('triage_vitals', 'weight')
    op.drop_column('triage_vitals', 'oxygen_saturation')
    op.drop_column('triage_vitals', 'respiratory_rate')
    op.drop_column('triage_vitals', 'pulse_rate')
    op.drop_column('triage_vitals', 'diastolic_bp')
    op.drop_column('triage_vitals', 'systolic_bp')
    
    # Make blood_pressure required again
    op.alter_column('triage_vitals', 'blood_pressure',
                    existing_type=sa.String(50),
                    nullable=False)
