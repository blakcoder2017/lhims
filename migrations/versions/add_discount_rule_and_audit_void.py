"""Add DiscountRule table and AuditAction VOID

Revision ID: add_discount_rule_and_audit_void
Revises: add_refund_models
Create Date: 2026-02-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_discount_rule_and_audit_void'
down_revision = 'add_refund_models'  # Use the refund models migration as parent
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add VOID to audit_action enum
    audit_action_enum = postgresql.ENUM(
        'create', 'update', 'delete', 'view', 'login', 'logout', 
        'export', 'print', 'approve', 'reject', 'void',
        name='auditaction', create_type=False
    )
    audit_action_enum.create(op.get_bind(), checkfirst=True)
    
    # Add discount_type enum
    discount_type_enum = postgresql.ENUM(
        'percentage', 'fixed',
        name='discounttype', create_type=False
    )
    discount_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Create discount_rules table
    op.create_table(
        'discount_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('discount_type', discount_type_enum, nullable=False),
        sa.Column('discount_value', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('applicable_services', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('patient_categories', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('min_invoice_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('max_discount_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('valid_from', sa.DateTime(), nullable=True),
        sa.Column('valid_to', sa.DateTime(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_discount_rules_id'), 'discount_rules', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_discount_rules_id'), table_name='discount_rules')
    op.drop_table('discount_rules')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS discounttype')
    # Note: Don't drop auditaction enum as it may have existing data
