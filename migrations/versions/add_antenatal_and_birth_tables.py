"""add antenatal_visits and birth_records tables

Revision ID: antenatal_birth_01
Revises: fluid_balance_01
Create Date: 2025-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'antenatal_birth_01'
down_revision: Union[str, None] = 'fluid_balance_01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # antenatal_visits
    op.create_table(
        'antenatal_visits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('encounter_id', sa.Integer(), nullable=True),
        sa.Column('recorded_by_id', sa.Integer(), nullable=True),
        sa.Column('visit_date', sa.Date(), nullable=False),
        sa.Column('visit_number', sa.Integer(), nullable=True),
        sa.Column('gestational_weeks', sa.Numeric(5, 2), nullable=True),
        sa.Column('lmp', sa.Date(), nullable=True),
        sa.Column('edd', sa.Date(), nullable=True),
        sa.Column('blood_pressure_systolic', sa.Integer(), nullable=True),
        sa.Column('blood_pressure_diastolic', sa.Integer(), nullable=True),
        sa.Column('weight_kg', sa.Numeric(6, 2), nullable=True),
        sa.Column('height_cm', sa.Numeric(5, 2), nullable=True),
        sa.Column('bmi', sa.Numeric(5, 2), nullable=True),
        sa.Column('fetal_heart_rate', sa.Integer(), nullable=True),
        sa.Column('fundal_height_cm', sa.Numeric(5, 2), nullable=True),
        sa.Column('fetal_position', sa.String(50), nullable=True),
        sa.Column('fetal_movement', sa.String(50), nullable=True),
        sa.Column('hemoglobin', sa.Numeric(5, 2), nullable=True),
        sa.Column('urine_protein', sa.String(20), nullable=True),
        sa.Column('blood_group', sa.String(10), nullable=True),
        sa.Column('rhesus_factor', sa.String(5), nullable=True),
        sa.Column('risk_factors', sa.Text(), nullable=True),
        sa.Column('complications', sa.Text(), nullable=True),
        sa.Column('counseling_given', sa.Text(), nullable=True),
        sa.Column('supplements_prescribed', sa.Text(), nullable=True),
        sa.Column('next_visit_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        sa.ForeignKeyConstraint(['encounter_id'], ['encounters.id'], ),
        sa.ForeignKeyConstraint(['recorded_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_antenatal_visits_id'), 'antenatal_visits', ['id'], unique=False)
    op.create_index(op.f('ix_antenatal_visits_patient_id'), 'antenatal_visits', ['patient_id'], unique=False)

    # birth_records
    op.create_table(
        'birth_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mother_patient_id', sa.Integer(), nullable=False),
        sa.Column('admission_id', sa.Integer(), nullable=True),
        sa.Column('encounter_id', sa.Integer(), nullable=True),
        sa.Column('birth_date', sa.Date(), nullable=False),
        sa.Column('birth_time', sa.Time(), nullable=True),
        sa.Column('delivery_type', sa.String(20), nullable=False, server_default=sa.text("'vaginal'")),
        sa.Column('birth_outcome', sa.String(20), nullable=False, server_default=sa.text("'live'")),
        sa.Column('gender', sa.String(10), nullable=True),
        sa.Column('weight_kg', sa.Numeric(5, 3), nullable=True),
        sa.Column('length_cm', sa.Numeric(5, 2), nullable=True),
        sa.Column('head_circumference_cm', sa.Numeric(5, 2), nullable=True),
        sa.Column('apgar_1min', sa.Integer(), nullable=True),
        sa.Column('apgar_5min', sa.Integer(), nullable=True),
        sa.Column('apgar_10min', sa.Integer(), nullable=True),
        sa.Column('delivered_by_id', sa.Integer(), nullable=True),
        sa.Column('assisted_by_id', sa.Integer(), nullable=True),
        sa.Column('birth_number', sa.String(50), nullable=True),
        sa.Column('gravida', sa.Integer(), nullable=True),
        sa.Column('para', sa.Integer(), nullable=True),
        sa.Column('complications', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=True),
        sa.ForeignKeyConstraint(['mother_patient_id'], ['patients.id'], ),
        sa.ForeignKeyConstraint(['admission_id'], ['admissions.id'], ),
        sa.ForeignKeyConstraint(['encounter_id'], ['encounters.id'], ),
        sa.ForeignKeyConstraint(['delivered_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['assisted_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_birth_records_id'), 'birth_records', ['id'], unique=False)
    op.create_index(op.f('ix_birth_records_birth_number'), 'birth_records', ['birth_number'], unique=True)
    op.create_index(op.f('ix_birth_records_mother_patient_id'), 'birth_records', ['mother_patient_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_birth_records_mother_patient_id'), table_name='birth_records')
    op.drop_index(op.f('ix_birth_records_birth_number'), table_name='birth_records')
    op.drop_index(op.f('ix_birth_records_id'), table_name='birth_records')
    op.drop_table('birth_records')
    op.drop_index(op.f('ix_antenatal_visits_patient_id'), table_name='antenatal_visits')
    op.drop_index(op.f('ix_antenatal_visits_id'), table_name='antenatal_visits')
    op.drop_table('antenatal_visits')
