"""Add lab_audit_event table for lab-specific audit trail

Revision ID: lab_audit_event
Revises: lab_template_system
Create Date: 2026-02-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'lab_audit_event'
down_revision: Union[str, Sequence[str], None] = 'lab_template_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'lab_audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),  # lab_order, lab_template, etc.
        sa.Column('entity_id', sa.String(100), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),  # create, update, submit, verify, authorize, amend
        sa.Column('old_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lab_audit_events_entity', 'lab_audit_events', ['entity_type', 'entity_id'])
    op.create_index('ix_lab_audit_events_created_at', 'lab_audit_events', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_lab_audit_events_created_at', 'lab_audit_events')
    op.drop_index('ix_lab_audit_events_entity', 'lab_audit_events')
    op.drop_table('lab_audit_events')
