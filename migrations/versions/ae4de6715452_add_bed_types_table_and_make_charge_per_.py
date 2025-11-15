"""add_bed_types_table_and_make_charge_per_day_required

Revision ID: ae4de6715452
Revises: 549ec22fe2c5
Create Date: 2025-11-12 19:28:48.904366

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae4de6715452'
down_revision: Union[str, Sequence[str], None] = '549ec22fe2c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create bed_types table and make charge_per_day required."""
    # Create bed_types table
    op.create_table('bed_types',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('default_charge_per_day', sa.String(length=20), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bed_types_id'), 'bed_types', ['id'], unique=False)
    op.create_index(op.f('ix_bed_types_name'), 'bed_types', ['name'], unique=True)
    op.create_index(op.f('ix_bed_types_code'), 'bed_types', ['code'], unique=True)
    
    # Insert default bed types
    op.execute("""
        INSERT INTO bed_types (name, code, description, default_charge_per_day, is_active, created_at)
        VALUES 
            ('Standard', 'STD', 'Standard bed', '50.00', true, NOW()),
            ('ICU', 'ICU', 'Intensive Care Unit bed', '200.00', true, NOW()),
            ('Private', 'PRIV', 'Private room bed', '150.00', true, NOW()),
            ('Semi-Private', 'SEMI', 'Semi-private bed', '100.00', true, NOW()),
            ('Ward', 'WARD', 'General ward bed', '30.00', true, NOW())
        ON CONFLICT (name) DO NOTHING;
    """)
    
    # Make charge_per_day NOT NULL for beds (set default to 0.00 for existing NULL values)
    op.execute("UPDATE beds SET charge_per_day = 0.00 WHERE charge_per_day IS NULL")
    op.alter_column('beds', 'charge_per_day',
                    existing_type=sa.Numeric(10, 2),
                    nullable=False,
                    server_default='0.00')
    
    # Make charge_per_day NOT NULL for wards (set default to 0.00 for existing NULL values)
    op.execute("UPDATE wards SET charge_per_day = 0.00 WHERE charge_per_day IS NULL")
    op.alter_column('wards', 'charge_per_day',
                    existing_type=sa.Numeric(10, 2),
                    nullable=False,
                    server_default='0.00')


def downgrade() -> None:
    """Downgrade schema - Revert charge_per_day to nullable and drop bed_types table."""
    # Revert charge_per_day to nullable
    op.alter_column('wards', 'charge_per_day',
                    existing_type=sa.Numeric(10, 2),
                    nullable=True,
                    server_default=None)
    op.alter_column('beds', 'charge_per_day',
                    existing_type=sa.Numeric(10, 2),
                    nullable=True,
                    server_default=None)
    
    # Drop bed_types table
    op.drop_index(op.f('ix_bed_types_code'), table_name='bed_types')
    op.drop_index(op.f('ix_bed_types_name'), table_name='bed_types')
    op.drop_index(op.f('ix_bed_types_id'), table_name='bed_types')
    op.drop_table('bed_types')
