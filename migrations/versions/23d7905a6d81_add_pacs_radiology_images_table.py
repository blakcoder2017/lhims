"""add pacs radiology images table

Revision ID: 23d7905a6d81
Revises: 669d16d611ce
Create Date: 2025-11-10 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '23d7905a6d81'
down_revision: Union[str, Sequence[str], None] = '669d16d611ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum types
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE imagestatus AS ENUM ('uploaded', 'processing', 'available', 'archived', 'deleted');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE imagetype AS ENUM ('xray', 'ct', 'mri', 'ultrasound', 'mammography', 'fluoroscopy', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.create_table('radiology_images',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('radiology_order_id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('uploaded_by_id', sa.Integer(), nullable=False),
    sa.Column('image_number', sa.String(length=50), nullable=False),
    sa.Column('image_type', postgresql.ENUM('xray', 'ct', 'mri', 'ultrasound', 'mammography', 'fluoroscopy', 'other', name='imagetype', create_type=False), nullable=False),
    sa.Column('dicom_series_uid', sa.String(length=100), nullable=True),
    sa.Column('dicom_study_uid', sa.String(length=100), nullable=True),
    sa.Column('dicom_instance_uid', sa.String(length=100), nullable=True),
    sa.Column('file_path', sa.String(length=500), nullable=False),
    sa.Column('file_name', sa.String(length=255), nullable=False),
    sa.Column('file_size', sa.Integer(), nullable=True),
    sa.Column('file_format', sa.String(length=50), nullable=True),
    sa.Column('mime_type', sa.String(length=100), nullable=True),
    sa.Column('modality', sa.String(length=20), nullable=True),
    sa.Column('body_part', sa.String(length=100), nullable=True),
    sa.Column('study_description', sa.String(length=500), nullable=True),
    sa.Column('series_description', sa.String(length=500), nullable=True),
    sa.Column('image_width', sa.Integer(), nullable=True),
    sa.Column('image_height', sa.Integer(), nullable=True),
    sa.Column('bits_per_pixel', sa.Integer(), nullable=True),
    sa.Column('number_of_frames', sa.Integer(), nullable=True),
    sa.Column('acquisition_date', sa.DateTime(), nullable=True),
    sa.Column('acquisition_time', sa.String(length=20), nullable=True),
    sa.Column('status', postgresql.ENUM('uploaded', 'processing', 'available', 'archived', 'deleted', name='imagestatus', create_type=False), nullable=False),
    sa.Column('storage_location', sa.String(length=200), nullable=True),
    sa.Column('storage_tier', sa.String(length=50), nullable=True),
    sa.Column('thumbnail_path', sa.String(length=500), nullable=True),
    sa.Column('is_public', sa.Boolean(), nullable=True),
    sa.Column('access_level', sa.String(length=50), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('uploaded_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('processed_at', sa.DateTime(), nullable=True),
    sa.Column('archived_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['radiology_order_id'], ['radiology_orders.id'], ),
    sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_radiology_images_id'), 'radiology_images', ['id'], unique=False)
    op.create_index(op.f('ix_radiology_images_image_number'), 'radiology_images', ['image_number'], unique=True)
    op.create_index(op.f('ix_radiology_images_dicom_series_uid'), 'radiology_images', ['dicom_series_uid'], unique=False)
    op.create_index(op.f('ix_radiology_images_dicom_study_uid'), 'radiology_images', ['dicom_study_uid'], unique=False)
    op.create_index(op.f('ix_radiology_images_dicom_instance_uid'), 'radiology_images', ['dicom_instance_uid'], unique=True)
    
    op.create_table('image_annotations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('image_id', sa.Integer(), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('annotation_type', sa.String(length=50), nullable=False),
    sa.Column('annotation_data', sa.Text(), nullable=False),
    sa.Column('measurement_value', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('measurement_unit', sa.String(length=20), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['image_id'], ['radiology_images.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('image_annotations')
    op.drop_index(op.f('ix_radiology_images_dicom_instance_uid'), table_name='radiology_images')
    op.drop_index(op.f('ix_radiology_images_dicom_study_uid'), table_name='radiology_images')
    op.drop_index(op.f('ix_radiology_images_dicom_series_uid'), table_name='radiology_images')
    op.drop_index(op.f('ix_radiology_images_image_number'), table_name='radiology_images')
    op.drop_index(op.f('ix_radiology_images_id'), table_name='radiology_images')
    op.drop_table('radiology_images')
    op.execute('DROP TYPE IF EXISTS imagetype')
    op.execute('DROP TYPE IF EXISTS imagestatus')
