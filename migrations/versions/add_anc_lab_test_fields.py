"""Add ANC lab test fields for DHIMS2 compliance

Adds HIV, Syphilis, Hepatitis B/C, and Urinalysis test tracking
to antenatal_visits table for Ghana Health Service reporting.

Revision ID: add_anc_lab_test_fields
Revises: 
Create Date: 2026-02-24
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_anc_lab_test_fields'
down_revision = None  # Set to appropriate parent revision
branch_labels = None
depends_on = None


def upgrade():
    # Add HIV test fields
    op.add_column('antenatal_visits', sa.Column('hiv_tested', sa.Boolean(), nullable=True))
    op.add_column('antenatal_visits', sa.Column('hiv_result', sa.String(20), nullable=True))
    op.add_column('antenatal_visits', sa.Column('hiv_test_date', sa.Date(), nullable=True))
    
    # Add Syphilis test fields
    op.add_column('antenatal_visits', sa.Column('syphilis_tested', sa.Boolean(), nullable=True))
    op.add_column('antenatal_visits', sa.Column('syphilis_result', sa.String(20), nullable=True))
    op.add_column('antenatal_visits', sa.Column('syphilis_test_date', sa.Date(), nullable=True))
    
    # Add Hepatitis B test fields
    op.add_column('antenatal_visits', sa.Column('hepatitis_b_tested', sa.Boolean(), nullable=True))
    op.add_column('antenatal_visits', sa.Column('hepatitis_b_result', sa.String(20), nullable=True))
    op.add_column('antenatal_visits', sa.Column('hepatitis_b_test_date', sa.Date(), nullable=True))
    
    # Add Hepatitis C test fields
    op.add_column('antenatal_visits', sa.Column('hepatitis_c_tested', sa.Boolean(), nullable=True))
    op.add_column('antenatal_visits', sa.Column('hepatitis_c_result', sa.String(20), nullable=True))
    op.add_column('antenatal_visits', sa.Column('hepatitis_c_test_date', sa.Date(), nullable=True))
    
    # Add Urinalysis fields
    op.add_column('antenatal_visits', sa.Column('urinalysis_done', sa.Boolean(), nullable=True))
    op.add_column('antenatal_visits', sa.Column('urinalysis_result', sa.String(50), nullable=True))


def downgrade():
    # Drop Urinalysis fields
    op.drop_column('antenatal_visits', 'urinalysis_result')
    op.drop_column('antenatal_visits', 'urinalysis_done')
    
    # Drop Hepatitis C fields
    op.drop_column('antenatal_visits', 'hepatitis_c_test_date')
    op.drop_column('antenatal_visits', 'hepatitis_c_result')
    op.drop_column('antenatal_visits', 'hepatitis_c_tested')
    
    # Drop Hepatitis B fields
    op.drop_column('antenatal_visits', 'hepatitis_b_test_date')
    op.drop_column('antenatal_visits', 'hepatitis_b_result')
    op.drop_column('antenatal_visits', 'hepatitis_b_tested')
    
    # Drop Syphilis fields
    op.drop_column('antenatal_visits', 'syphilis_test_date')
    op.drop_column('antenatal_visits', 'syphilis_result')
    op.drop_column('antenatal_visits', 'syphilis_tested')
    
    # Drop HIV fields
    op.drop_column('antenatal_visits', 'hiv_test_date')
    op.drop_column('antenatal_visits', 'hiv_result')
    op.drop_column('antenatal_visits', 'hiv_tested')
