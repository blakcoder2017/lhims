"""Add lab template system - templates, versions, option sets, result workflow

Revision ID: lab_template_system
Revises: add_nhis_expiry
Create Date: 2026-02-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'lab_template_system'
down_revision: Union[str, Sequence[str], None] = 'c950b576837a'  # add_opd_visit_completion_outcome
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # 1. lab_option_set
    op.create_table(
        'lab_option_sets',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('code', sa.String(100), nullable=False),
        sa.Column('options_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lab_option_sets_code', 'lab_option_sets', ['code'], unique=True)

    # 2. lab_template
    op.create_table(
        'lab_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('discipline', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='DRAFT'),
        sa.Column('current_version', sa.Integer(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lab_templates_discipline', 'lab_templates', ['discipline'], unique=False)
    op.create_index('ix_lab_templates_status', 'lab_templates', ['status'], unique=False)

    # 3. lab_template_version
    op.create_table(
        'lab_template_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='DRAFT'),
        sa.Column('schema_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('change_note', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['lab_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_id', 'version', name='uq_lab_template_version')
    )

    # 4. lab_reference_range (field-based for templates)
    op.create_table(
        'lab_reference_ranges',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('field_code', sa.String(100), nullable=False),
        sa.Column('sex', sa.String(10), nullable=True, server_default='ANY'),
        sa.Column('age_min_days', sa.Integer(), nullable=True),
        sa.Column('age_max_days', sa.Integer(), nullable=True),
        sa.Column('low', sa.Numeric(20, 6), nullable=True),
        sa.Column('high', sa.Numeric(20, 6), nullable=True),
        sa.Column('text_range', sa.String(255), nullable=True),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('facility_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_lab_reference_ranges_field_code', 'lab_reference_ranges', ['field_code'], unique=False)

    # 5. Add template columns to lab_tests
    op.add_column('lab_tests', sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('lab_tests', sa.Column('template_version', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_lab_tests_template_id', 'lab_tests', 'lab_templates',
        ['template_id'], ['id'], ondelete='SET NULL'
    )

    # 6. Add template/result workflow columns to lab_orders
    op.add_column('lab_orders', sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('lab_orders', sa.Column('template_version_used', sa.Integer(), nullable=True))
    op.add_column('lab_orders', sa.Column('result_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('lab_orders', sa.Column('result_status', sa.String(50), nullable=True))
    op.add_column('lab_orders', sa.Column('flags_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('lab_orders', sa.Column('verified_by_id', sa.Integer(), nullable=True))
    op.add_column('lab_orders', sa.Column('verified_at', sa.DateTime(), nullable=True))
    op.add_column('lab_orders', sa.Column('authorized_by_id', sa.Integer(), nullable=True))
    op.add_column('lab_orders', sa.Column('authorized_at', sa.DateTime(), nullable=True))
    op.add_column('lab_orders', sa.Column('previous_version_id', sa.Integer(), nullable=True))
    op.add_column('lab_orders', sa.Column('amend_reason', sa.Text(), nullable=True))
    op.add_column('lab_orders', sa.Column('critical_called', sa.Boolean(), nullable=True))
    op.add_column('lab_orders', sa.Column('critical_called_at', sa.DateTime(), nullable=True))
    op.add_column('lab_orders', sa.Column('critical_called_to', sa.String(255), nullable=True))

    op.create_foreign_key(
        'fk_lab_orders_template_id', 'lab_orders', 'lab_templates',
        ['template_id'], ['id'], ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_lab_orders_verified_by', 'lab_orders', 'users',
        ['verified_by_id'], ['id'], ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_lab_orders_authorized_by', 'lab_orders', 'users',
        ['authorized_by_id'], ['id'], ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_lab_orders_previous_version', 'lab_orders', 'lab_orders',
        ['previous_version_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_lab_orders_previous_version', 'lab_orders', type_='foreignkey')
    op.drop_constraint('fk_lab_orders_authorized_by', 'lab_orders', type_='foreignkey')
    op.drop_constraint('fk_lab_orders_verified_by', 'lab_orders', type_='foreignkey')
    op.drop_constraint('fk_lab_orders_template_id', 'lab_orders', type_='foreignkey')

    op.drop_column('lab_orders', 'critical_called_to')
    op.drop_column('lab_orders', 'critical_called_at')
    op.drop_column('lab_orders', 'critical_called')
    op.drop_column('lab_orders', 'amend_reason')
    op.drop_column('lab_orders', 'previous_version_id')
    op.drop_column('lab_orders', 'authorized_at')
    op.drop_column('lab_orders', 'authorized_by_id')
    op.drop_column('lab_orders', 'verified_at')
    op.drop_column('lab_orders', 'verified_by_id')
    op.drop_column('lab_orders', 'flags_json')
    op.drop_column('lab_orders', 'result_status')
    op.drop_column('lab_orders', 'result_json')
    op.drop_column('lab_orders', 'template_version_used')
    op.drop_column('lab_orders', 'template_id')

    op.drop_constraint('fk_lab_tests_template_id', 'lab_tests', type_='foreignkey')
    op.drop_column('lab_tests', 'template_version')
    op.drop_column('lab_tests', 'template_id')

    op.drop_index('ix_lab_reference_ranges_field_code', table_name='lab_reference_ranges')
    op.drop_table('lab_reference_ranges')

    op.drop_table('lab_template_versions')
    op.drop_index('ix_lab_templates_status', table_name='lab_templates')
    op.drop_index('ix_lab_templates_discipline', table_name='lab_templates')
    op.drop_table('lab_templates')

    op.drop_index('ix_lab_option_sets_code', table_name='lab_option_sets')
    op.drop_table('lab_option_sets')
