"""add_diagnoses_wound_care_and_procedure_admission_id

Revision ID: add_diagnoses_wound_care
Revises: 0fc735668649
Create Date: 2026-02-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_diagnoses_wound_care'
down_revision: Union[str, Sequence[str], None] = 'add_pharmacy_ghana_ready'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # Create diagnosis_type enum
    diagnosis_type_enum = postgresql.ENUM(
        'admission', 'working', 'discharge', 'complicating',
        name='diagnosistype', create_type=False
    )
    diagnosis_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Create admission_diagnoses table
    op.create_table('admission_diagnoses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admission_id', sa.Integer(), nullable=False),
        sa.Column('diagnosed_by_id', sa.Integer(), nullable=False),
        sa.Column('diagnosis', sa.Text(), nullable=False),
        sa.Column('icd_code', sa.String(length=20), nullable=True),
        sa.Column('diagnosis_type', diagnosis_type_enum, nullable=False),
        sa.Column('diagnosed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.ForeignKeyConstraint(['admission_id'], ['admissions.id'], ),
        sa.ForeignKeyConstraint(['diagnosed_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admission_diagnoses_id'), 'admission_diagnoses', ['id'], unique=False)
    
    # Create wound_care_type enum
    wound_care_type_enum = postgresql.ENUM(
        'surgical', 'traumatic', 'pressure', 'diabetic', 'burns', 'other',
        name='woundcaretype', create_type=False
    )
    wound_care_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Create wound_condition enum
    wound_condition_enum = postgresql.ENUM(
        'clean', 'infected', 'granulating', 'necrotic', 'healed',
        name='woundcondition', create_type=False
    )
    wound_condition_enum.create(op.get_bind(), checkfirst=True)
    
    # Create wound_care table
    op.create_table('wound_care',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admission_id', sa.Integer(), nullable=False),
        sa.Column('performed_by_id', sa.Integer(), nullable=False),
        sa.Column('wound_location', sa.String(length=200), nullable=False),
        sa.Column('wound_type', wound_care_type_enum, nullable=False),
        sa.Column('wound_description', sa.Text(), nullable=True),
        sa.Column('dressing_date', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('dressing_type', sa.String(length=100), nullable=True),
        sa.Column('wound_condition', wound_condition_enum, nullable=True),
        sa.Column('length_cm', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('width_cm', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('depth_cm', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('exudate_type', sa.String(length=50), nullable=True),
        sa.Column('exudate_amount', sa.String(length=20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('next_dressing_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.ForeignKeyConstraint(['admission_id'], ['admissions.id'], ),
        sa.ForeignKeyConstraint(['performed_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_wound_care_id'), 'wound_care', ['id'], unique=False)
    
    # Add admission_id column to procedures table (nullable for backward compatibility)
    op.add_column('procedures', sa.Column('admission_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_procedures_admission_id',
        'procedures', 'admissions',
        ['admission_id'], ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove admission_id from procedures
    op.drop_constraint('fk_procedures_admission_id', 'procedures', type_='foreignkey')
    op.drop_column('procedures', 'admission_id')
    
    # Drop wound_care table
    op.drop_index(op.f('ix_wound_care_id'), table_name='wound_care')
    op.drop_table('wound_care')
    
    # Drop wound_condition enum
    wound_condition_enum = postgresql.ENUM(
        'clean', 'infected', 'granulating', 'necrotic', 'healed',
        name='woundcondition', create_type=False
    )
    wound_condition_enum.drop(op.get_bind(), checkfirst=True)
    
    # Drop wound_care_type enum
    wound_care_type_enum = postgresql.ENUM(
        'surgical', 'traumatic', 'pressure', 'diabetic', 'burns', 'other',
        name='woundcaretype', create_type=False
    )
    wound_care_type_enum.drop(op.get_bind(), checkfirst=True)
    
    # Drop admission_diagnoses table
    op.drop_index(op.f('ix_admission_diagnoses_id'), table_name='admission_diagnoses')
    op.drop_table('admission_diagnoses')
    
    # Drop diagnosis_type enum
    diagnosis_type_enum = postgresql.ENUM(
        'admission', 'working', 'discharge', 'complicating',
        name='diagnosistype', create_type=False
    )
    diagnosis_type_enum.drop(op.get_bind(), checkfirst=True)
