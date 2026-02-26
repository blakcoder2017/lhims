"""Add DHIMS2 integration tables

Revision ID: add_dhims2_integration
Revises: fix_appointmenttype_enum
Create Date: 2026-02-21
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# Revision identifiers
revision: str = 'add_dhims2_integration'
down_revision: Union[str, Sequence[str], None] = 'fix_appointmenttype_enum'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create DHIMS2 integration tables."""
    
    # Create enum types
    op.execute("""
        CREATE TYPE submissionrunstatus AS ENUM (
            'draft',
            'validation_failed',
            'pending_approval',
            'approved',
            'submitted',
            'submit_failed',
            'locked'
        )
    """)
    
    op.execute("""
        CREATE TYPE validationstatus AS ENUM (
            'pass',
            'warn',
            'fail'
        )
    """)
    
    # Create dhims2_instances table
    op.create_table(
        'dhims2_instances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('base_url', sa.String(length=500), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=True, server_default='30'),
        sa.Column('verify_tls', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('max_retries', sa.Integer(), nullable=True, server_default='5'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dhims2_instances_id'), 'dhims2_instances', ['id'])
    op.create_index(op.f('ix_dhims2_instances_name'), 'dhims2_instances', ['name'], unique=True)
    
    # Create dhims2_mappings table
    op.create_table(
        'dhims2_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('instance_id', sa.Integer(), nullable=False),
        sa.Column('internal_metric_key', sa.String(length=100), nullable=False),
        sa.Column('dhis2_data_element_uid', sa.String(length=20), nullable=False),
        sa.Column('dhis2_category_option_combo_uid', sa.String(length=20), nullable=True),
        sa.Column('dhis2_attribute_option_combo_uid', sa.String(length=20), nullable=True),
        sa.Column('dhis2_dataset_uid', sa.String(length=20), nullable=True),
        sa.Column('value_type', sa.String(length=20), nullable=True, server_default='numeric'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('validation_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['instance_id'], ['dhims2_instances.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dhims2_mappings_id'), 'dhims2_mappings', ['id'])
    op.create_index(op.f('ix_dhims2_mappings_internal_metric_key'), 'dhims2_mappings', ['internal_metric_key'])
    
    # Create dhims2_org_unit_mappings table
    op.create_table(
        'dhims2_org_unit_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('instance_id', sa.Integer(), nullable=False),
        sa.Column('internal_org_id', sa.Integer(), nullable=False),
        sa.Column('internal_org_type', sa.String(length=50), nullable=False),
        sa.Column('dhis2_org_unit_uid', sa.String(length=20), nullable=False),
        sa.Column('dhis2_org_unit_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['instance_id'], ['dhims2_instances.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dhims2_org_unit_mappings_id'), 'dhims2_org_unit_mappings', ['id'])
    
    # Create dhims2_submission_runs table
    op.create_table(
        'dhims2_submission_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('instance_id', sa.Integer(), nullable=False),
        sa.Column('org_unit_uid', sa.String(length=20), nullable=False),
        sa.Column('period', sa.String(length=20), nullable=False),
        sa.Column('report_type', sa.String(length=100), nullable=False),
        sa.Column('dataset_uid', sa.String(length=20), nullable=True),
        sa.Column('status', sa.Enum('draft', 'validation_failed', 'pending_approval', 'approved', 'submitted', 'submit_failed', 'locked', name='submissionrunstatus'), nullable=False, server_default='draft'),
        sa.Column('payload_hash', sa.String(length=64), nullable=True),
        sa.Column('prepared_by', sa.Integer(), nullable=True),
        sa.Column('prepared_at', sa.DateTime(), nullable=True),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('dhis2_import_count', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('dhis2_response', sa.Text(), nullable=True),
        sa.Column('error_summary', sa.Text(), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('locked_at', sa.DateTime(), nullable=True),
        sa.Column('locked_by', sa.Integer(), nullable=True),
        sa.Column('lock_justification', sa.Text(), nullable=True),
        sa.Column('override_justification', sa.Text(), nullable=True),
        sa.Column('override_by', sa.Integer(), nullable=True),
        sa.Column('override_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['instance_id'], ['dhims2_instances.id']),
        sa.ForeignKeyConstraint(['prepared_by'], ['users.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.ForeignKeyConstraint(['locked_by'], ['users.id']),
        sa.ForeignKeyConstraint(['override_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dhims2_submission_runs_id'), 'dhims2_submission_runs', ['id'])
    op.create_index(op.f('ix_dhims2_submission_runs_status'), 'dhims2_submission_runs', ['status'])
    op.create_index(op.f('ix_dhims2_submission_runs_payload_hash'), 'dhims2_submission_runs', ['payload_hash'])
    
    # Create dhims2_submission_items table
    op.create_table(
        'dhims2_submission_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('internal_metric_key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.String(length=500), nullable=False),
        sa.Column('dhis2_data_element_uid', sa.String(length=20), nullable=False),
        sa.Column('dhis2_category_option_combo_uid', sa.String(length=20), nullable=True),
        sa.Column('dhis2_attribute_option_combo_uid', sa.String(length=20), nullable=True),
        sa.Column('validation_status', sa.Enum('pass', 'warn', 'fail', name='validationstatus'), nullable=False, server_default='pass'),
        sa.Column('validation_notes', sa.Text(), nullable=True),
        sa.Column('source_table', sa.String(length=100), nullable=True),
        sa.Column('source_record_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['dhims2_submission_runs.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dhims2_submission_items_id'), 'dhims2_submission_items', ['id'])
    op.create_index(op.f('ix_dhims2_submission_items_internal_metric_key'), 'dhims2_submission_items', ['internal_metric_key'])
    
    # Create dhims2_audit_logs table
    op.create_table(
        'dhims2_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=True),
        sa.Column('mapping_id', sa.Integer(), nullable=True),
        sa.Column('instance_id', sa.Integer(), nullable=True),
        sa.Column('before_status', sa.String(length=50), nullable=True),
        sa.Column('after_status', sa.String(length=50), nullable=True),
        sa.Column('justification', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['run_id'], ['dhims2_submission_runs.id']),
        sa.ForeignKeyConstraint(['mapping_id'], ['dhims2_mappings.id']),
        sa.ForeignKeyConstraint(['instance_id'], ['dhims2_instances.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dhims2_audit_logs_id'), 'dhims2_audit_logs', ['id'])
    op.create_index(op.f('ix_dhims2_audit_logs_created_at'), 'dhims2_audit_logs', ['created_at'])


def downgrade() -> None:
    """Drop DHIMS2 integration tables."""
    
    op.drop_table('dhims2_audit_logs')
    op.drop_table('dhims2_submission_items')
    op.drop_table('dhims2_submission_runs')
    op.drop_table('dhims2_org_unit_mappings')
    op.drop_table('dhims2_mappings')
    op.drop_table('dhims2_instances')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS validationstatus')
    op.execute('DROP TYPE IF EXISTS submissionrunstatus')
