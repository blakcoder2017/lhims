"""add_birth_labour_delivery_fields

Revision ID: add_birth_labour_delivery_fields
Revises: d255e826bc61
Create Date: 2026-02-21 23:31:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_birth_labour_delivery_fields'
down_revision: Union[str, Sequence[str], None] = 'd255e826bc61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add labour, delivery, medication and maternal health fields to birth_records."""
    # Add labour and delivery details
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS referral_reason TEXT')
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS duration_of_labour_hours NUMERIC(10, 2)')
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS partograph_used BOOLEAN DEFAULT FALSE')
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS placenta_delivered VARCHAR(20)')
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS estimated_blood_loss_ml INTEGER')
    
    # Add medication fields
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS uterotonic_drug VARCHAR(100)')
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS other_medications TEXT')
    
    # Add maternal health fields
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS tetanus_status VARCHAR(20)')
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS iptp_doses INTEGER')
    
    # Add stillbirth details
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS fetal_death_date DATE')
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS fetal_death_time TIME')
    
    # Add newborn care fields
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS skin_to_skin BOOLEAN DEFAULT FALSE')
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS kangaroo_care BOOLEAN DEFAULT FALSE')
    
    # Create indexes for commonly queried fields
    op.execute('CREATE INDEX IF NOT EXISTS idx_birth_records_facility_district ON birth_records(facility_name, district)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_birth_records_birth_date ON birth_records(birth_date)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_birth_records_birth_outcome ON birth_records(birth_outcome)')
    
    # Add comments for documentation
    op.execute("COMMENT ON COLUMN birth_records.referral_reason IS 'Reason for referral from/to another facility'")
    op.execute("COMMENT ON COLUMN birth_records.duration_of_labour_hours IS 'Total duration of labour in hours'")
    op.execute("COMMENT ON COLUMN birth_records.partograph_used IS 'Whether partograph was used to monitor labour'")
    op.execute("COMMENT ON COLUMN birth_records.placenta_delivered IS 'Status of placenta delivery: complete, incomplete, retained'")
    op.execute("COMMENT ON COLUMN birth_records.estimated_blood_loss_ml IS 'Estimated blood loss during delivery in millilitres'")
    op.execute("COMMENT ON COLUMN birth_records.uterotonic_drug IS 'Uterotonic drug given after delivery (e.g., Oxytocin, Misoprostol)'")
    op.execute("COMMENT ON COLUMN birth_records.other_medications IS 'Other medications given during delivery'")
    op.execute("COMMENT ON COLUMN birth_records.tetanus_status IS 'Maternal tetanus immunisation status: protected, not_protected, unknown'")
    op.execute("COMMENT ON COLUMN birth_records.iptp_doses IS 'Number of IPTp (Intermittent Preventive Treatment in pregnancy) doses received'")
    op.execute("COMMENT ON COLUMN birth_records.fetal_death_date IS 'Date of fetal death (for stillbirths)'")
    op.execute("COMMENT ON COLUMN birth_records.fetal_death_time IS 'Time of fetal death (for stillbirths)'")
    op.execute("COMMENT ON COLUMN birth_records.skin_to_skin IS 'Whether skin-to-skin contact was initiated within 1 hour of birth'")
    op.execute("COMMENT ON COLUMN birth_records.kangaroo_care IS 'Whether Kangaroo Mother Care was provided (for LBW babies)'")


def downgrade() -> None:
    """Remove labour, delivery, medication and maternal health fields from birth_records."""
    # Drop indexes
    op.execute('DROP INDEX IF EXISTS idx_birth_records_facility_district')
    op.execute('DROP INDEX IF EXISTS idx_birth_records_birth_date')
    op.execute('DROP INDEX IF EXISTS idx_birth_records_birth_outcome')
    
    # Drop columns
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS kangaroo_care')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS skin_to_skin')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS fetal_death_time')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS fetal_death_date')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS iptp_doses')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS tetanus_status')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS other_medications')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS uterotonic_drug')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS estimated_blood_loss_ml')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS placenta_delivered')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS partograph_used')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS duration_of_labour_hours')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS referral_reason')
