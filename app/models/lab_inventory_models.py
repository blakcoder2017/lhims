"""
Lab Inventory Models

SQLAlchemy models for lab equipment and reagent inventory management.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Numeric, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class EquipmentStatus(str, enum.Enum):
    """Equipment status enumeration"""
    OPERATIONAL = "operational"
    UNDER_MAINTENANCE = "under_maintenance"
    CALIBRATION = "calibration"
    OUT_OF_SERVICE = "out_of_service"


class EquipmentType(str, enum.Enum):
    """Equipment type enumeration"""
    ANALYZER = "analyzer"
    CENTRIFUGE = "centrifuge"
    MICROSCOPE = "microscope"
    INCUBATOR = "incubator"
    AUTOCLAVE = "autoclave"
    REFRIGERATOR = "refrigerator"
    FREEZER = "freezer"
    SPECTROMETER = "spectrometer"
    OTHER = "other"


class ReagentStatus(str, enum.Enum):
    """Reagent status enumeration"""
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    EXPIRED = "expired"
    QUARANTINE = "quarantine"


class LabEquipment(Base):
    """
    SQLAlchemy Model for lab equipment inventory.
    Tracks lab equipment maintenance, calibration, and status.
    """
    __tablename__ = "lab_equipment"

    id = Column(Integer, primary_key=True, index=True)
    
    # Equipment Information
    name = Column(String(255), nullable=False)
    equipment_type = Column(String(50), nullable=False)  # EquipmentType enum
    manufacturer = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    serial_number = Column(String(100), nullable=True, unique=True)
    inventory_number = Column(String(100), nullable=True, unique=True)
    
    # Location
    location = Column(String(255), nullable=True)  # Lab section/room
    department = Column(String(100), nullable=True)
    
    # Status
    status = Column(String(50), nullable=False, default=EquipmentStatus.OPERATIONAL.value)
    
    # Purchase Information
    purchase_date = Column(DateTime, nullable=True)
    purchase_cost = Column(Numeric(12, 2), nullable=True)
    warranty_expiry = Column(DateTime, nullable=True)
    
    # Maintenance
    last_maintenance_date = Column(DateTime, nullable=True)
    next_maintenance_date = Column(DateTime, nullable=True)
    maintenance_interval_days = Column(Integer, nullable=True)  # Days between maintenance
    
    # Calibration
    last_calibration_date = Column(DateTime, nullable=True)
    next_calibration_date = Column(DateTime, nullable=True)
    calibration_interval_days = Column(Integer, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    maintenance_records = relationship("EquipmentMaintenanceRecord", back_populates="equipment")
    calibration_records = relationship("EquipmentCalibrationRecord", back_populates="equipment")
    
    def __repr__(self):
        return f"<LabEquipment(id={self.id}, name='{self.name}', status='{self.status}')>"


class EquipmentMaintenanceRecord(Base):
    """
    SQLAlchemy Model for equipment maintenance records.
    """
    __tablename__ = "equipment_maintenance_records"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key
    equipment_id = Column(Integer, ForeignKey("lab_equipment.id"), nullable=False)
    
    # Maintenance Information
    maintenance_type = Column(String(100), nullable=False)  # Preventive, Corrective, Emergency
    description = Column(Text, nullable=True)
    performed_by = Column(String(255), nullable=True)
    cost = Column(Numeric(12, 2), nullable=True)
    
    # Dates
    maintenance_date = Column(DateTime, nullable=False)
    next_due_date = Column(DateTime, nullable=True)
    
    # Status
    is_completed = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    equipment = relationship("LabEquipment", back_populates="maintenance_records")
    
    def __repr__(self):
        return f"<EquipmentMaintenanceRecord(id={self.id}, equipment_id={self.equipment_id}, type='{self.maintenance_type}')>"


class EquipmentCalibrationRecord(Base):
    """
    SQLAlchemy Model for equipment calibration records.
    """
    __tablename__ = "equipment_calibration_records"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key
    equipment_id = Column(Integer, ForeignKey("lab_equipment.id"), nullable=False)
    
    # Calibration Information
    calibration_type = Column(String(100), nullable=False)  # Routine, Full, Performance
    performed_by = Column(String(255), nullable=True)
    performed_at_location = Column(String(255), nullable=True)
    
    # Results
    is_passed = Column(Boolean, nullable=True)
    deviations = Column(Text, nullable=True)
    
    # Reference Standards
    reference_standard = Column(String(255), nullable=True)
    certificate_number = Column(String(100), nullable=True)
    
    # Dates
    calibration_date = Column(DateTime, nullable=False)
    next_due_date = Column(DateTime, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    equipment = relationship("LabEquipment", back_populates="calibration_records")
    
    def __repr__(self):
        return f"<EquipmentCalibrationRecord(id={self.id}, equipment_id={self.equipment_id}, passed={self.is_passed})>"


class LabReagent(Base):
    """
    SQLAlchemy Model for lab reagent inventory.
    Tracks reagent stock levels, expiry, and usage.
    """
    __tablename__ = "lab_reagents"

    id = Column(Integer, primary_key=True, index=True)
    
    # Reagent Information
    name = Column(String(255), nullable=False)
    catalog_number = Column(String(100), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    supplier = Column(String(255), nullable=True)
    
    # Category
    category = Column(String(100), nullable=True)  # Hematology, Chemistry, Microbiology, etc.
    
    # Stock Information
    current_stock = Column(Numeric(10, 2), nullable=False, default=0)
    unit = Column(String(50), nullable=True)  # ml, liters, kits, pieces
    minimum_stock_level = Column(Numeric(10, 2), nullable=True)
    
    # Batch/Lot Information
    lot_number = Column(String(100), nullable=True)
    batch_number = Column(String(100), nullable=True)
    
    # Expiry
    manufacture_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    
    # Storage
    storage_conditions = Column(String(255), nullable=True)  # Room temp, 2-8C, -20C, etc.
    storage_location = Column(String(255), nullable=True)
    
    # Status
    status = Column(String(50), nullable=False, default=ReagentStatus.IN_STOCK.value)
    
    # Cost
    unit_cost = Column(Numeric(12, 2), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    usage_records = relationship("ReagentUsageRecord", back_populates="reagent")
    
    def __repr__(self):
        return f"<LabReagent(id={self.id}, name='{self.name}', stock={self.current_stock}, status='{self.status}')>"


class ReagentUsageRecord(Base):
    """
    SQLAlchemy Model for reagent usage tracking.
    """
    __tablename__ = "reagent_usage_records"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key
    reagent_id = Column(Integer, ForeignKey("lab_reagents.id"), nullable=False)
    
    # Usage Information
    quantity_used = Column(Numeric(10, 2), nullable=False)
    lab_order_id = Column(Integer, ForeignKey("lab_orders.id"), nullable=True)  # Optional: link to specific order
    
    # Who and When
    used_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    usage_date = Column(DateTime, nullable=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    reagent = relationship("LabReagent", back_populates="usage_records")
    
    def __repr__(self):
        return f"<ReagentUsageRecord(id={self.id}, reagent_id={self.reagent_id}, quantity={self.quantity_used})>"
