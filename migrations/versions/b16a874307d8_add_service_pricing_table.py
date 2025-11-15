"""add_service_pricing_table

Revision ID: b16a874307d8
Revises: 612fbff46dd1
Create Date: 2025-11-11 10:50:42.965992

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b16a874307d8'
down_revision: Union[str, Sequence[str], None] = '612fbff46dd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('service_pricing',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('service_name', sa.String(length=200), nullable=False),
    sa.Column('service_code', sa.String(length=50), nullable=True),
    sa.Column('charge_type', sa.String(length=50), nullable=False),
    sa.Column('category', sa.String(length=100), nullable=True),
    sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=10), nullable=False, server_default='GHS'),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('updated_by_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_service_pricing_id'), 'service_pricing', ['id'], unique=False)
    op.create_index(op.f('ix_service_pricing_service_name'), 'service_pricing', ['service_name'], unique=True)
    op.create_index(op.f('ix_service_pricing_service_code'), 'service_pricing', ['service_code'], unique=True)
    op.create_index(op.f('ix_service_pricing_charge_type'), 'service_pricing', ['charge_type'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_service_pricing_charge_type'), table_name='service_pricing')
    op.drop_index(op.f('ix_service_pricing_service_code'), table_name='service_pricing')
    op.drop_index(op.f('ix_service_pricing_service_name'), table_name='service_pricing')
    op.drop_index(op.f('ix_service_pricing_id'), table_name='service_pricing')
    op.drop_table('service_pricing')
