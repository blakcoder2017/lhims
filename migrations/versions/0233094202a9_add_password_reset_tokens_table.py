"""add password reset tokens table

Revision ID: 0233094202a9
Revises: 446dc4c3cf37
Create Date: 2025-11-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0233094202a9'
down_revision: Union[str, None] = '446dc4c3cf37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(255), nullable=False),
        sa.Column('token_type', sa.String(20), nullable=False),  # 'email' or 'sms'
        sa.Column('phone_number', sa.String(20), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('otp_code', sa.String(6), nullable=True),  # For SMS
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_reset_token', 'password_reset_tokens', ['token'], unique=True)
    op.create_index('idx_reset_user', 'password_reset_tokens', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_reset_user', table_name='password_reset_tokens')
    op.drop_index('idx_reset_token', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
