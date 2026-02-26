"""
Lab Inventory CRUD Operations

CRUD operations for lab equipment and reagent inventory management.
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.lab_inventory_models import (
    LabEquipment, EquipmentMaintenanceRecord, EquipmentCalibrationRecord,
    LabReagent, ReagentUsageRecord, EquipmentStatus, ReagentStatus
)


# ==================== Equipment CRUD ====================

def create_equipment(db: Session, equipment_data: dict) -> LabEquipment:
    """Create a new lab equipment."""
    db_equipment = LabEquipment(**equipment_data)
    db.add(db_equipment)
    db.commit()
    db.refresh(db_equipment)
    return db_equipment


def get_equipment(db: Session, equipment_id: int) -> Optional[LabEquipment]:
    """Get equipment by ID."""
    return db.query(LabEquipment).filter(LabEquipment.id == equipment_id).first()


def get_equipment_list(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    status: Optional[str] = None,
    equipment_type: Optional[str] = None
) -> List[LabEquipment]:
    """Get list of equipment with filters."""
    query = db.query(LabEquipment).filter(LabEquipment.is_active == True)
    
    if search:
        query = query.filter(
            or_(
                LabEquipment.name.ilike(f"%{search}%"),
                LabEquipment.serial_number.ilike(f"%{search}%"),
                LabEquipment.inventory_number.ilike(f"%{search}%"),
                LabEquipment.manufacturer.ilike(f"%{search}%")
            )
        )
    
    if status:
        query = query.filter(LabEquipment.status == status)
    
    if equipment_type:
        query = query.filter(LabEquipment.equipment_type == equipment_type)
    
    return query.order_by(LabEquipment.name).offset(skip).limit(limit).all()


def update_equipment(db: Session, equipment_id: int, equipment_data: dict) -> Optional[LabEquipment]:
    """Update equipment."""
    db_equipment = get_equipment(db, equipment_id)
    if not db_equipment:
        return None
    
    for field, value in equipment_data.items():
        setattr(db_equipment, field, value)
    
    db.commit()
    db.refresh(db_equipment)
    return db_equipment


def delete_equipment(db: Session, equipment_id: int) -> bool:
    """Soft delete equipment."""
    db_equipment = get_equipment(db, equipment_id)
    if not db_equipment:
        return False
    
    db_equipment.is_active = False
    db.commit()
    return True


# ==================== Maintenance Records CRUD ====================

def create_maintenance_record(db: Session, record_data: dict) -> EquipmentMaintenanceRecord:
    """Create a maintenance record."""
    db_record = EquipmentMaintenanceRecord(**record_data)
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record


def get_maintenance_records(
    db: Session,
    equipment_id: int,
    skip: int = 0,
    limit: int = 50
) -> List[EquipmentMaintenanceRecord]:
    """Get maintenance records for equipment."""
    return db.query(EquipmentMaintenanceRecord).filter(
        EquipmentMaintenanceRecord.equipment_id == equipment_id
    ).order_by(
        EquipmentMaintenanceRecord.maintenance_date.desc()
    ).offset(skip).limit(limit).all()


# ==================== Calibration Records CRUD ====================

def create_calibration_record(db: Session, record_data: dict) -> EquipmentCalibrationRecord:
    """Create a calibration record."""
    db_record = EquipmentCalibrationRecord(**record_data)
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record


def get_calibration_records(
    db: Session,
    equipment_id: int,
    skip: int = 0,
    limit: int = 50
) -> List[EquipmentCalibrationRecord]:
    """Get calibration records for equipment."""
    return db.query(EquipmentCalibrationRecord).filter(
        EquipmentCalibrationRecord.equipment_id == equipment_id
    ).order_by(
        EquipmentCalibrationRecord.calibration_date.desc()
    ).offset(skip).limit(limit).all()


# ==================== Reagent CRUD ====================

def create_reagent(db: Session, reagent_data: dict) -> LabReagent:
    """Create a new reagent."""
    db_reagent = LabReagent(**reagent_data)
    db.add(db_reagent)
    db.commit()
    db.refresh(db_reagent)
    return db_reagent


def get_reagent(db: Session, reagent_id: int) -> Optional[LabReagent]:
    """Get reagent by ID."""
    return db.query(LabReagent).filter(LabReagent.id == reagent_id).first()


def get_reagent_list(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    low_stock_only: bool = False
) -> List[LabReagent]:
    """Get list of reagents with filters."""
    query = db.query(LabReagent).filter(LabReagent.is_active == True)
    
    if search:
        query = query.filter(
            or_(
                LabReagent.name.ilike(f"%{search}%"),
                LabReagent.catalog_number.ilike(f"%{search}%"),
                LabReagent.manufacturer.ilike(f"%{search}%")
            )
        )
    
    if status:
        query = query.filter(LabReagent.status == status)
    
    if category:
        query = query.filter(LabReagent.category == category)
    
    if low_stock_only:
        query = query.filter(
            LabReagent.current_stock <= LabReagent.minimum_stock_level
        )
    
    return query.order_by(LabReagent.name).offset(skip).limit(limit).all()


def update_reagent(db: Session, reagent_id: int, reagent_data: dict) -> Optional[LabReagent]:
    """Update reagent."""
    db_reagent = get_reagent(db, reagent_id)
    if not db_reagent:
        return None
    
    for field, value in reagent_data.items():
        setattr(db_reagent, field, value)
    
    db.commit()
    db.refresh(db_reagent)
    return db_reagent


def update_reagent_stock(
    db: Session,
    reagent_id: int,
    quantity_change: float,
    is_addition: bool = True
) -> Optional[LabReagent]:
    """Update reagent stock level."""
    db_reagent = get_reagent(db, reagent_id)
    if not db_reagent:
        return None
    
    if is_addition:
        db_reagent.current_stock = (db_reagent.current_stock or 0) + quantity_change
    else:
        db_reagent.current_stock = max(0, (db_reagent.current_stock or 0) - quantity_change)
    
    # Update status based on stock level
    _update_reagent_status(db_reagent)
    
    db.commit()
    db.refresh(db_reagent)
    return db_reagent


def _update_reagent_status(reagent: LabReagent):
    """Update reagent status based on stock and expiry."""
    from datetime import datetime
    
    # Check expiry
    if reagent.expiry_date and reagent.expiry_date < datetime.now():
        reagent.status = ReagentStatus.EXPIRED.value
        return
    
    # Check stock level
    if reagent.current_stock <= 0:
        reagent.status = ReagentStatus.OUT_OF_STOCK.value
    elif reagent.minimum_stock_level and reagent.current_stock <= reagent.minimum_stock_level:
        reagent.status = ReagentStatus.LOW_STOCK.value
    else:
        reagent.status = ReagentStatus.IN_STOCK.value


def delete_reagent(db: Session, reagent_id: int) -> bool:
    """Soft delete reagent."""
    db_reagent = get_reagent(db, reagent_id)
    if not db_reagent:
        return False
    
    db_reagent.is_active = False
    db.commit()
    return True


# ==================== Reagent Usage CRUD ====================

def record_reagent_usage(db: Session, usage_data: dict) -> ReagentUsageRecord:
    """Record reagent usage."""
    db_usage = ReagentUsageRecord(**usage_data)
    db.add(db_usage)
    
    # Update stock
    if db_usage.reagent_id:
        reagent = get_reagent(db, db_usage.reagent_id)
        if reagent:
            reagent.current_stock = max(0, (reagent.current_stock or 0) - float(db_usage.quantity_used))
            _update_reagent_status(reagent)
    
    db.commit()
    db.refresh(db_usage)
    return db_usage


def get_reagent_usage(
    db: Session,
    reagent_id: int,
    skip: int = 0,
    limit: int = 50
) -> List[ReagentUsageRecord]:
    """Get usage records for reagent."""
    return db.query(ReagentUsageRecord).filter(
        ReagentUsageRecord.reagent_id == reagent_id
    ).order_by(
        ReagentUsageRecord.usage_date.desc()
    ).offset(skip).limit(limit).all()


# ==================== Alerts ====================

def get_expiring_reagents(db: Session, days: int = 30) -> List[LabReagent]:
    """Get reagents expiring within specified days."""
    from datetime import timedelta
    expiry_threshold = datetime.now() + timedelta(days=days)
    
    return db.query(LabReagent).filter(
        LabReagent.is_active == True,
        LabReagent.expiry_date <= expiry_threshold,
        LabReagent.expiry_date >= datetime.now()
    ).order_by(LabReagent.expiry_date).all()


def get_low_stock_reagents(db: Session) -> List[LabReagent]:
    """Get reagents below minimum stock level."""
    return db.query(LabReagent).filter(
        LabReagent.is_active == True,
        LabReagent.current_stock <= LabReagent.minimum_stock_level,
        LabReagent.status != ReagentStatus.EXPIRED.value
    ).order_by(LabReagent.current_stock).all()


def get_equipment_due_maintenance(db: Session, days: int = 7) -> List[LabEquipment]:
    """Get equipment due for maintenance."""
    from datetime import timedelta
    maintenance_threshold = datetime.now() + timedelta(days=days)
    
    return db.query(LabEquipment).filter(
        LabEquipment.is_active == True,
        LabEquipment.next_maintenance_date <= maintenance_threshold,
        LabEquipment.status != EquipmentStatus.OUT_OF_SERVICE.value
    ).order_by(LabEquipment.next_maintenance_date).all()


def get_equipment_due_calibration(db: Session, days: int = 7) -> List[LabEquipment]:
    """Get equipment due for calibration."""
    from datetime import timedelta
    calibration_threshold = datetime.now() + timedelta(days=days)
    
    return db.query(LabEquipment).filter(
        LabEquipment.is_active == True,
        LabEquipment.next_calibration_date <= calibration_threshold,
        LabEquipment.status != EquipmentStatus.OUT_OF_SERVICE.value
    ).order_by(LabEquipment.next_calibration_date).all()
