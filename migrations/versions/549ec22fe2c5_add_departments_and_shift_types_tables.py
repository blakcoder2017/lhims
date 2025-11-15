"""add_departments_and_shift_types_tables

Revision ID: 549ec22fe2c5
Revises: dbfa0a47ef24
Create Date: 2025-11-12 19:07:50.740115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '549ec22fe2c5'
down_revision: Union[str, Sequence[str], None] = 'dbfa0a47ef24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create departments and shift_types tables."""
    # Create departments table
    op.create_table('departments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_departments_id'), 'departments', ['id'], unique=False)
    op.create_index(op.f('ix_departments_name'), 'departments', ['name'], unique=True)
    op.create_index(op.f('ix_departments_code'), 'departments', ['code'], unique=True)
    
    # Create shift_types table
    op.create_table('shift_types',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('default_start_hour', sa.Integer(), nullable=True),
    sa.Column('default_end_hour', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_shift_types_id'), 'shift_types', ['id'], unique=False)
    op.create_index(op.f('ix_shift_types_name'), 'shift_types', ['name'], unique=True)
    op.create_index(op.f('ix_shift_types_code'), 'shift_types', ['code'], unique=True)
    
    # Insert default departments
    op.execute("""
        INSERT INTO departments (name, code, description, is_active, created_at)
        VALUES 
            ('General Medicine', 'GEN-MED', 'General Medicine Department', true, NOW()),
            ('Pediatrics', 'PEDS', 'Pediatrics Department', true, NOW()),
            ('Obstetrics & Gynecology', 'OB-GYN', 'Obstetrics & Gynecology Department', true, NOW()),
            ('Antenatal', 'ANT', 'Antenatal Care Department', true, NOW()),
            ('Emergency', 'EMER', 'Emergency Department', true, NOW()),
            ('Surgery', 'SURG', 'Surgery Department', true, NOW()),
            ('Orthopedics', 'ORTHO', 'Orthopedics Department', true, NOW()),
            ('Cardiology', 'CARD', 'Cardiology Department', true, NOW()),
            ('Dermatology', 'DERM', 'Dermatology Department', true, NOW())
        ON CONFLICT (name) DO NOTHING;
    """)
    
    # Insert default shift types
    op.execute("""
        INSERT INTO shift_types (name, code, description, default_start_hour, default_end_hour, is_active, created_at)
        VALUES 
            ('Morning', 'MORN', 'Morning shift (8:00 - 16:00)', 8, 16, true, NOW()),
            ('Evening', 'EVE', 'Evening shift (16:00 - 00:00)', 16, 0, true, NOW()),
            ('Night', 'NIGHT', 'Night shift (00:00 - 8:00)', 0, 8, true, NOW()),
            ('Full Day', 'FULL', 'Full day shift (8:00 - 20:00)', 8, 20, true, NOW()),
            ('Overnight', 'OVERNIGHT', 'Overnight shift (20:00 - 8:00 next day)', 20, 8, true, NOW())
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    """Downgrade schema - Drop departments and shift_types tables."""
    op.drop_index(op.f('ix_shift_types_code'), table_name='shift_types')
    op.drop_index(op.f('ix_shift_types_name'), table_name='shift_types')
    op.drop_index(op.f('ix_shift_types_id'), table_name='shift_types')
    op.drop_table('shift_types')
    op.drop_index(op.f('ix_departments_code'), table_name='departments')
    op.drop_index(op.f('ix_departments_name'), table_name='departments')
    op.drop_index(op.f('ix_departments_id'), table_name='departments')
    op.drop_table('departments')
