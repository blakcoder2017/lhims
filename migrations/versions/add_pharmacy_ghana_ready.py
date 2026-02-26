"""Add pharmacy Ghana-ready: dosage forms, pharmacy_drug, batches, ledger, dispense, interactions.

Revision ID: add_pharmacy_ghana_ready
Revises: 866b026e17f1
Create Date: 2026-02-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'add_pharmacy_ghana_ready'
down_revision: Union[str, Sequence[str], None] = '866b026e17f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # A1) dosage_form
    op.create_table(
        'pharmacy_dosage_form',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pharmacy_dosage_form_name', 'pharmacy_dosage_form', ['name'], unique=True)

    # pharmacy_supplier
    op.create_table(
        'pharmacy_supplier',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    # pharmacy_store
    op.create_table(
        'pharmacy_store',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('facility_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    # pharmacy_drug (formulation)
    op.create_table(
        'pharmacy_drug',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('item_code', sa.String(50), nullable=False),
        sa.Column('generic_name', sa.String(255), nullable=False),
        sa.Column('brand_name', sa.String(255), nullable=True),
        sa.Column('dosage_form_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_dosage_form.id'), nullable=False),
        sa.Column('strength_value', sa.Numeric(20, 6), nullable=True),
        sa.Column('strength_unit', sa.String(50), nullable=True),
        sa.Column('route', sa.String(50), nullable=True),
        sa.Column('concentration_value', sa.Numeric(20, 6), nullable=True),
        sa.Column('concentration_unit', sa.String(100), nullable=True),
        sa.Column('pack_size', sa.Integer(), nullable=True),
        sa.Column('reorder_level', sa.Numeric(20, 6), nullable=True),
        sa.Column('reorder_qty', sa.Numeric(20, 6), nullable=True),
        sa.Column('is_controlled', sa.Boolean(), server_default='false'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pharmacy_drug_item_code', 'pharmacy_drug', ['item_code'], unique=True)
    op.create_index('ix_pharmacy_drug_generic_name', 'pharmacy_drug', ['generic_name'])
    op.create_index('ix_pharmacy_drug_brand_name', 'pharmacy_drug', ['brand_name'])
    op.create_index('ix_pharmacy_drug_dosage_form_id', 'pharmacy_drug', ['dosage_form_id'])
    op.create_index('ix_pharmacy_drug_route', 'pharmacy_drug', ['route'])
    op.create_index('ix_pharmacy_drug_is_active', 'pharmacy_drug', ['is_active'])

    # pharmacy_batch
    op.create_table(
        'pharmacy_batch',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('drug_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_drug.id'), nullable=False),
        sa.Column('store_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_store.id'), nullable=False),
        sa.Column('batch_no', sa.String(100), nullable=False),
        sa.Column('expiry_date', sa.Date(), nullable=False),
        sa.Column('received_date', sa.Date(), nullable=True),
        sa.Column('unit_cost', sa.Numeric(20, 6), nullable=True),
        sa.Column('selling_price', sa.Numeric(20, 6), nullable=True),
        sa.Column('qty_on_hand', sa.Numeric(20, 6), nullable=False, server_default='0'),
        sa.Column('qty_reserved', sa.Numeric(20, 6), nullable=False, server_default='0'),
        sa.Column('status', sa.String(50), nullable=False, server_default='ACTIVE'),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_supplier.id'), nullable=True),
        sa.Column('invoice_ref', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pharmacy_batch_drug_store', 'pharmacy_batch', ['drug_id', 'store_id'])
    op.create_index('ix_pharmacy_batch_expiry', 'pharmacy_batch', ['expiry_date'])
    op.create_unique_constraint(
        'uq_pharmacy_batch_store_drug_batch_expiry',
        'pharmacy_batch',
        ['store_id', 'drug_id', 'batch_no', 'expiry_date']
    )

    # pharmacy_stock_ledger (immutable)
    op.create_table(
        'pharmacy_stock_ledger',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('store_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_store.id'), nullable=False),
        sa.Column('drug_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_drug.id'), nullable=False),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_batch.id'), nullable=True),
        sa.Column('movement_type', sa.String(50), nullable=False),
        sa.Column('qty_in', sa.Numeric(20, 6), nullable=False, server_default='0'),
        sa.Column('qty_out', sa.Numeric(20, 6), nullable=False, server_default='0'),
        sa.Column('unit_cost_snapshot', sa.Numeric(20, 6), nullable=True),
        sa.Column('selling_price_snapshot', sa.Numeric(20, 6), nullable=True),
        sa.Column('reference_type', sa.String(50), nullable=True),
        sa.Column('reference_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pharmacy_stock_ledger_store_drug_created', 'pharmacy_stock_ledger', ['store_id', 'drug_id', 'created_at'])
    op.create_index('ix_pharmacy_stock_ledger_batch_id', 'pharmacy_stock_ledger', ['batch_id'])
    op.create_index('ix_pharmacy_stock_ledger_movement_type', 'pharmacy_stock_ledger', ['movement_type'])

    # pharmacy_dispense
    op.create_table(
        'pharmacy_dispense',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('patient_id', sa.Integer(), sa.ForeignKey('patients.id'), nullable=False),
        sa.Column('encounter_id', sa.Integer(), sa.ForeignKey('encounters.id'), nullable=True),
        sa.Column('prescriber_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='DRAFT'),
        sa.Column('dispensed_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('dispensed_at', sa.DateTime(), nullable=True),
        sa.Column('payment_type', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pharmacy_dispense_patient_id', 'pharmacy_dispense', ['patient_id'])
    op.create_index('ix_pharmacy_dispense_encounter_id', 'pharmacy_dispense', ['encounter_id'])
    op.create_index('ix_pharmacy_dispense_status', 'pharmacy_dispense', ['status'])

    # pharmacy_dispense_item
    op.create_table(
        'pharmacy_dispense_item',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('dispense_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_dispense.id'), nullable=False),
        sa.Column('drug_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_drug.id'), nullable=False),
        sa.Column('dosage_instructions', sa.Text(), nullable=True),
        sa.Column('qty_prescribed', sa.Numeric(20, 6), nullable=True),
        sa.Column('qty_dispensed', sa.Numeric(20, 6), nullable=False),
        sa.Column('unit_selling_price', sa.Numeric(20, 6), nullable=True),
        sa.Column('total_amount', sa.Numeric(20, 6), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    # pharmacy_dispense_allocation (FEFO)
    op.create_table(
        'pharmacy_dispense_allocation',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('dispense_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_dispense_item.id'), nullable=False),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_batch.id'), nullable=False),
        sa.Column('qty_allocated', sa.Numeric(20, 6), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    # pharmacy_drug_interaction (pharmacy_drug based)
    op.create_table(
        'pharmacy_drug_interaction',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('drug_a_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_drug.id'), nullable=False),
        sa.Column('drug_b_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_drug.id'), nullable=False),
        sa.Column('severity', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('reference', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('drug_a_id', 'drug_b_id', name='uq_pharmacy_drug_interaction_pair')
    )

    # pharmacy_role_policy
    op.create_table(
        'pharmacy_role_policy',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('role_name', sa.String(100), nullable=False),
        sa.Column('can_view_unit_cost', sa.Boolean(), server_default='false'),
        sa.Column('can_view_margin', sa.Boolean(), server_default='false'),
        sa.Column('can_edit_selling_price', sa.Boolean(), server_default='false'),
        sa.Column('can_adjust_stock', sa.Boolean(), server_default='false'),
        sa.Column('can_approve_adjustment', sa.Boolean(), server_default='false'),
        sa.Column('can_dispense_controlled', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pharmacy_role_policy_role_name', 'pharmacy_role_policy', ['role_name'], unique=True)

    # patient_active_medication
    op.create_table(
        'patient_active_medication',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('patient_id', sa.Integer(), sa.ForeignKey('patients.id'), nullable=False),
        sa.Column('drug_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_drug.id'), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='ACTIVE'),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_patient_active_medication_patient_drug', 'patient_active_medication', ['patient_id', 'drug_id'])

    # Add pharmacy_drug_id to prescriptions (for prescribing safety)
    op.add_column('prescriptions', sa.Column('pharmacy_drug_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_prescriptions_pharmacy_drug', 'prescriptions', 'pharmacy_drug', ['pharmacy_drug_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_prescriptions_pharmacy_drug', 'prescriptions', type_='foreignkey')
    op.drop_column('prescriptions', 'pharmacy_drug_id')
    op.drop_table('patient_active_medication')
    op.drop_table('pharmacy_role_policy')
    op.drop_table('pharmacy_drug_interaction')
    op.drop_table('pharmacy_dispense_allocation')
    op.drop_table('pharmacy_dispense_item')
    op.drop_table('pharmacy_dispense')
    op.drop_table('pharmacy_stock_ledger')
    op.drop_table('pharmacy_batch')
    op.drop_table('pharmacy_drug')
    op.drop_table('pharmacy_store')
    op.drop_table('pharmacy_supplier')
    op.drop_table('pharmacy_dosage_form')
