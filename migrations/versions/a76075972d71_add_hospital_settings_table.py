"""add_hospital_settings_table

Revision ID: a76075972d71
Revises: 0233094202a9
Create Date: 2025-11-11 09:29:09.059372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a76075972d71'
down_revision: Union[str, Sequence[str], None] = '0233094202a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('hospital_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('hospital_name', sa.String(length=255), nullable=False, server_default='Local Health Information Management System'),
    sa.Column('hospital_address', sa.Text(), nullable=True),
    sa.Column('hospital_phone', sa.String(length=50), nullable=True),
    sa.Column('hospital_email', sa.String(length=255), nullable=True),
    sa.Column('hospital_website', sa.String(length=255), nullable=True),
    sa.Column('logo_path', sa.String(length=500), nullable=True),
    sa.Column('logo_url', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hospital_settings_id'), 'hospital_settings', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_hospital_settings_id'), table_name='hospital_settings')
    op.drop_table('hospital_settings')
