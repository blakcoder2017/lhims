"""add_opd_visit_to_orders

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-01-15 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add opd_visit_id and admission_id to order tables."""
    
    # Add opd_visit_id and admission_id to lab_orders table
    op.add_column('lab_orders', sa.Column('opd_visit_id', sa.Integer(), nullable=True))
    op.add_column('lab_orders', sa.Column('admission_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_lab_orders_opd_visit', 'lab_orders', 'opd_visits', ['opd_visit_id'], ['id'])
    op.create_foreign_key('fk_lab_orders_admission', 'lab_orders', 'admissions', ['admission_id'], ['id'])
    op.create_index('ix_lab_orders_opd_visit', 'lab_orders', ['opd_visit_id'], unique=False)
    op.create_index('ix_lab_orders_admission', 'lab_orders', ['admission_id'], unique=False)
    
    # Add opd_visit_id and admission_id to radiology_orders table
    op.add_column('radiology_orders', sa.Column('opd_visit_id', sa.Integer(), nullable=True))
    op.add_column('radiology_orders', sa.Column('admission_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_radiology_orders_opd_visit', 'radiology_orders', 'opd_visits', ['opd_visit_id'], ['id'])
    op.create_foreign_key('fk_radiology_orders_admission', 'radiology_orders', 'admissions', ['admission_id'], ['id'])
    op.create_index('ix_radiology_orders_opd_visit', 'radiology_orders', ['opd_visit_id'], unique=False)
    op.create_index('ix_radiology_orders_admission', 'radiology_orders', ['admission_id'], unique=False)
    
    # Add opd_visit_id and admission_id to prescriptions table
    op.add_column('prescriptions', sa.Column('opd_visit_id', sa.Integer(), nullable=True))
    op.add_column('prescriptions', sa.Column('admission_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_prescriptions_opd_visit', 'prescriptions', 'opd_visits', ['opd_visit_id'], ['id'])
    op.create_foreign_key('fk_prescriptions_admission', 'prescriptions', 'admissions', ['admission_id'], ['id'])
    op.create_index('ix_prescriptions_opd_visit', 'prescriptions', ['opd_visit_id'], unique=False)
    op.create_index('ix_prescriptions_admission', 'prescriptions', ['admission_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - Remove opd_visit_id and admission_id from order tables."""
    
    # Remove from prescriptions table
    op.drop_index('ix_prescriptions_admission', table_name='prescriptions')
    op.drop_index('ix_prescriptions_opd_visit', table_name='prescriptions')
    op.drop_constraint('fk_prescriptions_admission', 'prescriptions', type_='foreignkey')
    op.drop_constraint('fk_prescriptions_opd_visit', 'prescriptions', type_='foreignkey')
    op.drop_column('prescriptions', 'admission_id')
    op.drop_column('prescriptions', 'opd_visit_id')
    
    # Remove from radiology_orders table
    op.drop_index('ix_radiology_orders_admission', table_name='radiology_orders')
    op.drop_index('ix_radiology_orders_opd_visit', table_name='radiology_orders')
    op.drop_constraint('fk_radiology_orders_admission', 'radiology_orders', type_='foreignkey')
    op.drop_constraint('fk_radiology_orders_opd_visit', 'radiology_orders', type_='foreignkey')
    op.drop_column('radiology_orders', 'admission_id')
    op.drop_column('radiology_orders', 'opd_visit_id')
    
    # Remove from lab_orders table
    op.drop_index('ix_lab_orders_admission', table_name='lab_orders')
    op.drop_index('ix_lab_orders_opd_visit', table_name='lab_orders')
    op.drop_constraint('fk_lab_orders_admission', 'lab_orders', type_='foreignkey')
    op.drop_constraint('fk_lab_orders_opd_visit', 'lab_orders', type_='foreignkey')
    op.drop_column('lab_orders', 'admission_id')
    op.drop_column('lab_orders', 'opd_visit_id')

