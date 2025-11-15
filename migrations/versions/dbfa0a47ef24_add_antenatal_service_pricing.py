"""add_antenatal_service_pricing

Revision ID: dbfa0a47ef24
Revises: 2bc8e96bc3a4
Create Date: 2025-11-12 19:00:20.212663

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dbfa0a47ef24'
down_revision: Union[str, Sequence[str], None] = '2bc8e96bc3a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add default Antenatal service pricing."""
    # Insert default Antenatal service pricing if it doesn't exist
    op.execute("""
        INSERT INTO service_pricing (service_name, service_code, charge_type, category, unit_price, currency, description, is_active, created_at)
        SELECT 
            'Antenatal Consultation',
            'ANT-CONSULT',
            'antenatal',
            'Consultation',
            150.00,
            'GHS',
            'Antenatal care consultation and check-up',
            true,
            NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM service_pricing WHERE service_name = 'Antenatal Consultation'
        );
    """)
    
    op.execute("""
        INSERT INTO service_pricing (service_name, service_code, charge_type, category, unit_price, currency, description, is_active, created_at)
        SELECT 
            'Antenatal Care Package',
            'ANT-PACKAGE',
            'antenatal',
            'Package',
            500.00,
            'GHS',
            'Complete antenatal care package (includes multiple visits)',
            true,
            NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM service_pricing WHERE service_name = 'Antenatal Care Package'
        );
    """)


def downgrade() -> None:
    """Downgrade schema - Remove Antenatal service pricing."""
    op.execute("""
        DELETE FROM service_pricing 
        WHERE service_name IN ('Antenatal Consultation', 'Antenatal Care Package');
    """)
