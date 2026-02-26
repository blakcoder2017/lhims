"""add_category_and_dhis2_fields_to_diseases

Revision ID: add_category_dhis2_to_diseases
Revises: 
Create Date: 2026-02-21 23:31:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_category_dhis2_to_diseases'
down_revision: Union[str, Sequence[str], None] = 'lab_inventory_v1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add category and DHIMS2 fields to diseases table."""
    # First, create the enum type if it doesn't exist
    disease_category_enum = postgresql.ENUM(
        'infectious', 'ncd', 'maternal', 'child_health', 
        'injury', 'mental_health', 'eye_conditions', 'dental', 
        'skin', 'respiratory', 'other',
        name='diseasecategory',
        create_type=False
    )
    disease_category_enum.create(op.get_bind(), checkfirst=True)
    
    # Add category column with default 'other'
    op.add_column(
        'diseases',
        sa.Column(
            'category',
            disease_category_enum,
            server_default='other',
            nullable=False
        )
    )
    
    # Add DHIMS2 mapping fields
    op.add_column(
        'diseases',
        sa.Column(
            'dhis2_data_element_uid',
            sa.String(length=20),
            nullable=True
        )
    )
    
    op.add_column(
        'diseases',
        sa.Column(
            'dhis2_category_option_combo_uid',
            sa.String(length=20),
            nullable=True
        )
    )


def downgrade() -> None:
    """Remove category and DHIMS2 fields from diseases table."""
    op.drop_column('diseases', 'dhis2_category_option_combo_uid')
    op.drop_column('diseases', 'dhis2_data_element_uid')
    op.drop_column('diseases', 'category')
    
    # Drop the enum type
    op.execute('DROP TYPE IF EXISTS diseasecategory')
