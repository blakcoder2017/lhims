from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Enum, Numeric, event
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql
from app.db.database import Base
import enum
from decimal import Decimal


class SampleStatus(str, enum.Enum):
    """Sample status enumeration"""
    COLLECTED = "collected"
    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class QCStatus(str, enum.Enum):
    """Quality control status enumeration"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    OUT_OF_RANGE = "out_of_range"


class LabSample(Base):
    """
    SQLAlchemy Model for lab sample tracking with barcoding.
    Tracks individual samples from collection to completion.
    """
    __tablename__ = "lab_samples"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    lab_order_id = Column(Integer, ForeignKey("lab_orders.id"), nullable=False)
    collected_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Who collected the sample
    received_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Who received the sample in lab
    
    # Barcode Information
    barcode = Column(String(100), unique=True, nullable=False, index=True)  # Unique barcode
    barcode_type = Column(String(50), nullable=True, default="CODE128")  # Barcode type
    
    # Sample Information
    sample_type = Column(String(100), nullable=True)  # e.g., "Blood", "Urine", "Stool"
    collection_method = Column(String(100), nullable=True)  # Collection method
    collection_site = Column(String(100), nullable=True)  # Collection site
    
    # Status Tracking
    status = Column(postgresql.ENUM(SampleStatus, values_callable=lambda x: [e.value for e in x], name='samplestatus', create_type=False), nullable=False, default=SampleStatus.COLLECTED)
    
    # Dates
    collected_at = Column(DateTime, nullable=True)  # When sample was collected
    received_at = Column(DateTime, nullable=True)  # When sample was received in lab
    processing_started_at = Column(DateTime, nullable=True)  # When processing started
    completed_at = Column(DateTime, nullable=True)  # When processing completed
    
    # Storage Information
    storage_location = Column(String(100), nullable=True)  # Storage location
    storage_temperature = Column(String(50), nullable=True)  # Storage temperature
    
    # Notes
    notes = Column(Text, nullable=True)  # Additional notes
    rejection_reason = Column(Text, nullable=True)  # Reason if rejected
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    lab_order = relationship("LabOrder", back_populates="samples")
    collected_by = relationship("User", foreign_keys=[collected_by_id])
    received_by = relationship("User", foreign_keys=[received_by_id])
    qc_records = relationship("QCRecord", back_populates="sample")
    
    def __repr__(self):
        return f"<LabSample(id={self.id}, barcode='{self.barcode}', status={self.status.value})>"


def validate_lab_sample_before_insert(mapper, connection, target):
    """Validate that lab_order_id is not None before inserting/updating a LabSample."""
    if target.lab_order_id is None:
        raise ValueError("lab_order_id cannot be None for LabSample. A valid lab order must be associated with each sample.")


# Register event listeners for LabSample
event.listen(LabSample, 'before_insert', validate_lab_sample_before_insert)
event.listen(LabSample, 'before_update', validate_lab_sample_before_insert)


class QCRecord(Base):
    """
    SQLAlchemy Model for quality control records.
    Tracks QC tests performed on lab equipment and reagents.
    """
    __tablename__ = "qc_records"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    lab_order_id = Column(Integer, ForeignKey("lab_orders.id"), nullable=True)  # Optional: linked to specific order
    sample_id = Column(Integer, ForeignKey("lab_samples.id"), nullable=True)  # Optional: linked to specific sample
    performed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Who performed QC
    
    # QC Information
    qc_type = Column(String(100), nullable=False)  # e.g., "Equipment QC", "Reagent QC", "Sample QC"
    qc_test_name = Column(String(255), nullable=False)  # Name of QC test
    equipment_name = Column(String(255), nullable=True)  # Equipment used
    reagent_lot = Column(String(100), nullable=True)  # Reagent lot number
    
    # QC Results
    status = Column(postgresql.ENUM(QCStatus, values_callable=lambda x: [e.value for e in x], name='qcstatus', create_type=False), nullable=False, default=QCStatus.PENDING)
    expected_value = Column(Numeric(10, 4), nullable=True)  # Expected QC value
    actual_value = Column(Numeric(10, 4), nullable=True)  # Actual QC value
    deviation = Column(Numeric(10, 4), nullable=True)  # Deviation from expected
    deviation_percentage = Column(Numeric(5, 2), nullable=True)  # Deviation percentage
    
    # Reference Ranges
    lower_limit = Column(Numeric(10, 4), nullable=True)  # Lower acceptable limit
    upper_limit = Column(Numeric(10, 4), nullable=True)  # Upper acceptable limit
    
    # Notes
    notes = Column(Text, nullable=True)  # QC notes
    corrective_action = Column(Text, nullable=True)  # Corrective action if failed
    
    # Dates
    performed_at = Column(DateTime, nullable=False, server_default=func.now())
    expiry_date = Column(DateTime, nullable=True)  # When QC expires
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    lab_order = relationship("LabOrder")
    sample = relationship("LabSample", back_populates="qc_records")
    performed_by = relationship("User", foreign_keys=[performed_by_id])
    
    def __repr__(self):
        return f"<QCRecord(id={self.id}, qc_test_name='{self.qc_test_name}', status={self.status.value})>"


class ReferenceRange(Base):
    """
    SQLAlchemy Model for test reference ranges.
    Stores normal/abnormal ranges for lab tests.
    """
    __tablename__ = "reference_ranges"

    id = Column(Integer, primary_key=True, index=True)
    
    # Test Information
    test_id = Column(Integer, ForeignKey("lab_tests.id"), nullable=True)  # Link to lab test catalog
    test_name = Column(String(255), nullable=False, index=True)  # Test name
    test_code = Column(String(50), nullable=True, index=True)  # Test code (e.g., LOINC)
    
    # Patient Demographics (for age/gender-specific ranges)
    age_min = Column(Integer, nullable=True)  # Minimum age in years
    age_max = Column(Integer, nullable=True)  # Maximum age in years
    gender = Column(String(20), nullable=True)  # Gender-specific range
    
    # Reference Values
    normal_min = Column(Numeric(10, 4), nullable=True)  # Normal range minimum
    normal_max = Column(Numeric(10, 4), nullable=True)  # Normal range maximum
    critical_low = Column(Numeric(10, 4), nullable=True)  # Critical low value
    critical_high = Column(Numeric(10, 4), nullable=True)  # Critical high value
    
    # Units
    unit = Column(String(50), nullable=True)  # Unit of measurement
    
    # Notes
    notes = Column(Text, nullable=True)  # Additional notes
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    test = relationship("LabTest", back_populates="reference_ranges")
    
    def __repr__(self):
        return f"<ReferenceRange(id={self.id}, test_name='{self.test_name}')>"

