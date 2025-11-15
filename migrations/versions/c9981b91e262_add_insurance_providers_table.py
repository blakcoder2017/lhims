"""add_insurance_providers_table

Revision ID: c9981b91e262
Revises: 9ce2363001e1
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c9981b91e262'
down_revision: Union[str, Sequence[str], None] = '9ce2363001e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add insurance_providers table."""
    # Create insurance_providers table
    op.create_table('insurance_providers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('contact_person', sa.String(length=100), nullable=True),
        sa.Column('phone_number', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=100), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('co_pay_rate', sa.String(length=20), nullable=True),
        sa.Column('billing_email', sa.String(length=100), nullable=True),
        sa.Column('billing_address', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_insurance_providers_id'), 'insurance_providers', ['id'], unique=False)
    op.create_index(op.f('ix_insurance_providers_name'), 'insurance_providers', ['name'], unique=True)
    op.create_index(op.f('ix_insurance_providers_code'), 'insurance_providers', ['code'], unique=True)


def downgrade() -> None:
    """Downgrade schema - Remove insurance_providers table."""
    op.drop_index(op.f('ix_insurance_providers_code'), table_name='insurance_providers')
    op.drop_index(op.f('ix_insurance_providers_name'), table_name='insurance_providers')
    op.drop_index(op.f('ix_insurance_providers_id'), table_name='insurance_providers')
    op.drop_table('insurance_providers')
