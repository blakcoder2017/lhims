from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from uuid import UUID
from app.models.lab_catalog_models import LabTest
from app.models.lab_models import ReferenceRange
from app.models.lab_template_models import LabReferenceRange
from app.models.encounter_models import LabOrder
from app.schemas.lab_catalog_schemas import LabTestCreate, LabTestUpdate, ReferenceRangeCreate, ReferenceRangeUpdate


def create_lab_test(db: Session, test: LabTestCreate) -> LabTest:
    """Create a new lab test"""
    # Check for duplicate test_code (non-empty)
    if test.test_code and test.test_code.strip():
        existing = db.query(LabTest).filter(
            LabTest.test_code == test.test_code.strip(),
            LabTest.is_active == True
        ).first()
        if existing:
            raise ValueError(f"Lab test with code '{test.test_code}' already exists")
    
    # If test_code is empty or None, generate a unique numeric one
    if not test.test_code or not test.test_code.strip():
        # Find the highest existing numeric test_code and increment
        existing_tests = db.query(LabTest).filter(
            LabTest.test_code.op('~')(r'^[0-9]+')
        ).all()
        max_code = 0
        for t in existing_tests:
            try:
                code_num = int(t.test_code)
                if code_num > max_code:
                    max_code = code_num
            except (ValueError, TypeError):
                pass
        test.test_code = str(max_code + 1)
    
    db_test = LabTest(**test.dict())
    db.add(db_test)
    db.commit()
    db.refresh(db_test)
    return db_test


def get_lab_test(db: Session, test_id: int) -> Optional[LabTest]:
    """Get a lab test by ID"""
    return db.query(LabTest).filter(
        LabTest.id == test_id,
        LabTest.is_active == True
    ).first()


def get_lab_test_by_id_any_status(db: Session, test_id: int) -> Optional[LabTest]:
    """Get a lab test by ID regardless of active status"""
    return db.query(LabTest).filter(LabTest.id == test_id).first()


def get_lab_test_by_code(db: Session, test_code: str) -> Optional[LabTest]:
    """Get a lab test by code"""
    return db.query(LabTest).filter(
        LabTest.test_code == test_code,
        LabTest.is_active == True
    ).first()


def get_lab_tests(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None, category: Optional[str] = None) -> List[LabTest]:
    """Get all lab tests with optional search and category filter"""
    query = db.query(LabTest).filter(LabTest.is_active == True)
    
    if search:
        query = query.filter(
            or_(
                LabTest.test_name.ilike(f"%{search}%"),
                LabTest.test_code.ilike(f"%{search}%"),
                LabTest.description.ilike(f"%{search}%")
            )
        )
    
    if category:
        query = query.filter(LabTest.test_category == category)
    
    return query.order_by(LabTest.test_name).offset(skip).limit(limit).all()


def update_lab_test(db: Session, test_id: int, test_update: LabTestUpdate) -> Optional[LabTest]:
    """Update a lab test"""
    db_test = db.query(LabTest).filter(LabTest.id == test_id).first()
    if not db_test:
        return None
    
    update_data = test_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_test, field, value)
    
    db.commit()
    db.refresh(db_test)
    return db_test


def delete_lab_test(db: Session, test_id: int) -> dict:
    """Soft delete a lab test with check for related orders"""
    db_test = db.query(LabTest).filter(LabTest.id == test_id).first()
    if not db_test:
        return {"success": False, "message": "Test not found", "error": "not_found"}
    
    # Check for active lab orders using this test (pending, ordered, or in_progress)
    from app.models.encounter_models import OrderStatus
    active_orders = db.query(LabOrder).filter(
        LabOrder.lab_test_id == test_id,
        LabOrder.status.in_([OrderStatus.PENDING, OrderStatus.ORDERED, OrderStatus.IN_PROGRESS])
    ).count()
    
    if active_orders > 0:
        return {
            "success": False, 
            "message": f"Cannot delete: {active_orders} active lab order(s) are using this test. Please resolve these orders first.",
            "error": "has_related_orders",
            "order_count": active_orders
        }
    
    db_test.is_active = False
    db.commit()
    return {"success": True, "message": "Lab test deleted successfully", "id": test_id}


def create_reference_range(db: Session, range_data: ReferenceRangeCreate) -> ReferenceRange:
    """Create a reference range"""
    db_range = ReferenceRange(**range_data.dict())
    db.add(db_range)
    db.commit()
    db.refresh(db_range)
    return db_range


def get_reference_ranges(db: Session, test_id: Optional[int] = None, test_name: Optional[str] = None) -> List[ReferenceRange]:
    """Get reference ranges"""
    query = db.query(ReferenceRange).filter(ReferenceRange.is_active == True)
    
    if test_id:
        query = query.filter(ReferenceRange.test_id == test_id)
    elif test_name:
        query = query.filter(ReferenceRange.test_name == test_name)
    
    return query.all()


def update_reference_range(db: Session, range_id: int, range_update: ReferenceRangeUpdate) -> Optional[ReferenceRange]:
    """Update a reference range"""
    db_range = db.query(ReferenceRange).filter(ReferenceRange.id == range_id).first()
    if not db_range:
        return None
    
    update_data = range_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_range, field, value)
    
    db.commit()
    db.refresh(db_range)
    return db_range


def toggle_lab_test_status(db: Session, test_id: int, activate: bool) -> Optional[dict]:
    """
    Activate or deactivate a lab test.
    
    Args:
        db: Database session
        test_id: ID of the lab test
        activate: True to activate, False to deactivate
    
    Returns:
        Dictionary with success status and message
    """
    db_test = db.query(LabTest).filter(LabTest.id == test_id).first()
    if not db_test:
        return {"success": False, "message": "Test not found", "error": "not_found"}
    
    # Check if trying to activate a test that already has that status
    if activate and db_test.is_active:
        return {"success": False, "message": "Test is already active", "error": "already_active"}
    
    if not activate and not db_test.is_active:
        return {"success": False, "message": "Test is already inactive", "error": "already_inactive"}
    
    # Check for active lab orders when deactivating
    if not activate:
        from app.models.encounter_models import OrderStatus
        active_orders = db.query(LabOrder).filter(
            LabOrder.lab_test_id == test_id,
            LabOrder.status.in_([OrderStatus.PENDING, OrderStatus.ORDERED, OrderStatus.IN_PROGRESS])
        ).count()
        
        if active_orders > 0:
            return {
                "success": False,
                "message": f"Cannot deactivate: {active_orders} active lab order(s) are using this test. Please resolve these orders first.",
                "error": "has_related_orders",
                "order_count": active_orders
            }
    
    db_test.is_active = activate
    db.commit()
    db.refresh(db_test)
    
    action = "activated" if activate else "deactivated"
    return {
        "success": True,
        "message": f"Lab test {action} successfully",
        "id": test_id,
        "is_active": activate
    }


def get_all_lab_tests(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None, category: Optional[str] = None, include_inactive: bool = False) -> List[LabTest]:
    """
    Get all lab tests with optional search and category filter.
    Optionally includes inactive tests.
    """
    query = db.query(LabTest)
    
    if not include_inactive:
        query = query.filter(LabTest.is_active == True)
    
    if search:
        query = query.filter(
            or_(
                LabTest.test_name.ilike(f"%{search}%"),
                LabTest.test_code.ilike(f"%{search}%"),
                LabTest.description.ilike(f"%{search}%")
            )
        )
    
    if category:
        query = query.filter(LabTest.test_category == category)
    
    return query.order_by(LabTest.test_name).offset(skip).limit(limit).all()


def get_template_reference_ranges(
    db: Session, 
    field_code: Optional[str] = None,
    limit: int = 500
) -> List[LabReferenceRange]:
    """Get template field reference ranges (parameter-level reference ranges)"""
    query = db.query(LabReferenceRange)
    
    if field_code:
        query = query.filter(LabReferenceRange.field_code == field_code)
    
    return query.order_by(LabReferenceRange.field_code).limit(limit).all()


def get_all_template_field_codes(db: Session) -> set:
    """Get all unique field codes from published lab template versions"""
    from app.models.lab_template_models import LabTemplateVersion
    
    # Get all published template versions
    templates = db.query(LabTemplateVersion).filter(
        LabTemplateVersion.status == "PUBLISHED"
    ).all()
    
    field_codes = set()
    for template in templates:
        schema = template.schema_json
        if schema and "fields" in schema:
            for field_id, field_def in schema["fields"].items():
                if isinstance(field_def, dict):
                    code = field_def.get("code") or field_id
                    field_codes.add(code)
    
    return field_codes


def get_missing_reference_ranges(db: Session) -> dict:
    """
    Find template field codes that don't have reference ranges defined.
    Returns a dict with 'all_fields' and 'missing_ranges' lists.
    """
    # Get all field codes from templates
    all_fields = get_all_template_field_codes(db)
    
    # Get all field codes that already have reference ranges
    existing_ranges = db.query(LabReferenceRange.field_code).distinct().all()
    existing_codes = set([r[0] for r in existing_ranges])
    
    # Find missing ones
    missing_codes = all_fields - existing_codes
    
    return {
        "total_template_fields": len(all_fields),
        "fields_with_ranges": len(existing_codes),
        "missing_ranges": sorted(list(missing_codes))
    }


def create_template_reference_range(
    db: Session,
    field_code: str,
    sex: str = "ANY",
    age_min_days: Optional[int] = None,
    age_max_days: Optional[int] = None,
    low: Optional[float] = None,
    high: Optional[float] = None,
    critical_low: Optional[float] = None,
    critical_high: Optional[float] = None,
    text_range: Optional[str] = None,
    unit: Optional[str] = None
) -> LabReferenceRange:
    """Create a new template reference range"""
    new_range = LabReferenceRange(
        field_code=field_code,
        sex=sex,
        age_min_days=age_min_days,
        age_max_days=age_max_days,
        low=low,
        high=high,
        critical_low=critical_low,
        critical_high=critical_high,
        text_range=text_range,
        unit=unit
    )
    db.add(new_range)
    db.commit()
    db.refresh(new_range)
    return new_range


def update_template_reference_range(
    db: Session,
    range_id: UUID,
    field_code: Optional[str] = None,
    sex: Optional[str] = None,
    age_min_days: Optional[int] = None,
    age_max_days: Optional[int] = None,
    low: Optional[float] = None,
    high: Optional[float] = None,
    critical_low: Optional[float] = None,
    critical_high: Optional[float] = None,
    text_range: Optional[str] = None,
    unit: Optional[str] = None
) -> Optional[LabReferenceRange]:
    """Update a template reference range"""
    from app.models.lab_template_models import LabReferenceRange as LabRefRange
    
    range_obj = db.query(LabRefRange).filter(LabRefRange.id == range_id).first()
    if not range_obj:
        return None
    
    if field_code is not None:
        range_obj.field_code = field_code
    if sex is not None:
        range_obj.sex = sex
    if age_min_days is not None:
        range_obj.age_min_days = age_min_days
    if age_max_days is not None:
        range_obj.age_max_days = age_max_days
    if low is not None:
        range_obj.low = low
    if high is not None:
        range_obj.high = high
    if critical_low is not None:
        range_obj.critical_low = critical_low
    if critical_high is not None:
        range_obj.critical_high = critical_high
    if text_range is not None:
        range_obj.text_range = text_range
    if unit is not None:
        range_obj.unit = unit
    
    db.commit()
    db.refresh(range_obj)
    return range_obj
