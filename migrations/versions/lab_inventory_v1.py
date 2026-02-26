"""Add lab inventory models

Revision ID: lab_inventory_v1
Revises: add_pharmacy_ghana_ready
Create Date: 2026-02-14 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'lab_inventory_v1'
down_revision: Union[str, Sequence[str], None] = 'add_pharmacy_ghana_ready'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add lab inventory tables."""
    
    # Create lab_equipment table
    op.create_table('lab_equipment',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('equipment_type', sa.String(length=50), nullable=False),
        sa.Column('manufacturer', sa.String(length=255), nullable=True),
        sa.Column('model', sa.String(length=255), nullable=True),
        sa.Column('serial_number', sa.String(length=100), nullable=True),
        sa.Column('inventory_number', sa.String(length=100), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='operational'),
        sa.Column('purchase_date', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('purchase_cost', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('warranty_expiry', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('last_maintenance_date', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('next_maintenance_date', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('maintenance_interval_days', sa.Integer(), nullable=True),
        sa.Column('last_calibration_date', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('next_calibration_date', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('calibration_interval_days', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_lab_equipment'))
    )
    op.create_index(op.f('ix_lab_equipment_name'), 'lab_equipment', ['name'], unique=False)
    op.create_index(op.f('ix_lab_equipment_serial_number'), 'lab_equipment', ['serial_number'], unique=True)
    
    # Create equipment_maintenance_records table
    op.create_table('equipment_maintenance_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('equipment_id', sa.Integer(), nullable=False),
        sa.Column('maintenance_type', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('performed_by', sa.String(length=255), nullable=True),
        sa.Column('cost', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('maintenance_date', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('next_due_date', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['equipment_id'], ['lab_equipment.id'], name=op.f('fk_equipment_maintenance_records_equipment')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_equipment_maintenance_records'))
    )
    
    # Create equipment_calibration_records table
    op.create_table('equipment_calibration_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('equipment_id', sa.Integer(), nullable=False),
        sa.Column('calibration_type', sa.String(length=100), nullable=False),
        sa.Column('performed_by', sa.String(length=255), nullable=True),
        sa.Column('performed_at_location', sa.String(length=255), nullable=True),
        sa.Column('is_passed', sa.Boolean(), nullable=True),
        sa.Column('deviations', sa.Text(), nullable=True),
        sa.Column('reference_standard', sa.String(length=255), nullable=True),
        sa.Column('certificate_number', sa.String(length=100), nullable=True),
        sa.Column('calibration_date', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('next_due_date', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['equipment_id'], ['lab_equipment.id'], name=op.f('fk_equipment_calibration_records_equipment')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_equipment_calibration_records'))
    )
    
    # Create lab_reagents table
    op.create_table('lab_reagents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('catalog_number', sa.String(length=100), nullable=True),
        sa.Column('manufacturer', sa.String(length=255), nullable=True),
        sa.Column('supplier', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('current_stock', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('minimum_stock_level', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('lot_number', sa.String(length=100), nullable=True),
        sa.Column('batch_number', sa.String(length=100), nullable=True),
        sa.Column('manufacture_date', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('expiry_date', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('storage_conditions', sa.String(length=255), nullable=True),
        sa.Column('storage_location', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='in_stock'),
        sa.Column('unit_cost', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_lab_reagents'))
    )
    op.create_index(op.f('ix_lab_reagents_name'), 'lab_reagents', ['name'], unique=False)
    op.create_index(op.f('ix_lab_reagents_category'), 'lab_reagents', ['category'], unique=False)
    
    # Create reagent_usage_records table
    op.create_table('reagent_usage_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('reagent_id', sa.Integer(), nullable=False),
        sa.Column('quantity_used', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('lab_order_id', sa.Integer(), nullable=True),
        sa.Column('used_by_id', sa.Integer(), nullable=True),
        sa.Column('usage_date', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['lab_order_id'], ['lab_orders.id'], name=op.f('fk_reagent_usage_records_lab_order')),
        sa.ForeignKeyConstraint(['reagent_id'], ['lab_reagents.id'], name=op.f('fk_reagent_usage_records_reagent')),
        sa.ForeignKeyConstraint(['used_by_id'], ['users.id'], name=op.f('fk_reagent_usage_records_used_by')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_reagent_usage_records'))
    )


def downgrade() -> None:
    """Downgrade schema - Drop lab inventory tables."""
    op.drop_table('reagent_usage_records')
    op.drop_index(op.f('ix_lab_reagents_category'), table_name='lab_reagents')
    op.drop_index(op.f('ix_lab_reagents_name'), table_name='lab_reagents')
    op.drop_table('lab_reagents')
    op.drop_table('equipment_calibration_records')
    op.drop_table('equipment_maintenance_records')
    op.drop_index(op.f('ix_lab_equipment_serial_number'), table_name='lab_equipment')
    op.drop_index(op.f('ix_lab_equipment_name'), table_name='lab_equipment')
    op.drop_table('lab_equipment')
