"""add_ward_types_table

Revision ID: ab1649f023bd
Revises: c9981b91e262
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ab1649f023bd'
down_revision: Union[str, Sequence[str], None] = 'c9981b91e262'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add ward_types table."""
    # Create ward_types table
    op.create_table('ward_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_ward_types_id'), 'ward_types', ['id'], unique=False)
    op.create_index(op.f('ix_ward_types_name'), 'ward_types', ['name'], unique=True)
    op.create_index(op.f('ix_ward_types_code'), 'ward_types', ['code'], unique=True)
    
    # Insert default ward types
    op.execute("""
        INSERT INTO ward_types (name, code, description, is_active) VALUES
        ('General', 'GEN', 'General ward for standard patient care', true),
        ('ICU', 'ICU', 'Intensive Care Unit for critical patients', true),
        ('Pediatric', 'PED', 'Pediatric ward for children', true),
        ('Maternity', 'MAT', 'Maternity ward for expectant mothers and newborns', true),
        ('Surgical', 'SUR', 'Surgical ward for post-operative care', true),
        ('Emergency', 'ER', 'Emergency ward for acute care', true),
        ('Isolation', 'ISO', 'Isolation ward for infectious diseases', true),
        ('Private', 'PRV', 'Private ward for premium care', true)
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    """Downgrade schema - Remove ward_types table."""
    op.drop_index(op.f('ix_ward_types_code'), table_name='ward_types')
    op.drop_index(op.f('ix_ward_types_name'), table_name='ward_types')
    op.drop_index(op.f('ix_ward_types_id'), table_name='ward_types')
    op.drop_table('ward_types')
