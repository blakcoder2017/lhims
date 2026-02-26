"""
Lab Sample Auto-Creation Service

This module provides automatic sample creation functionality when lab orders are placed.
"""
from datetime import datetime
from typing import Optional, List
import uuid
from sqlalchemy.orm import Session

from app.models.lab_models import LabSample, SampleStatus
from app.models.encounter_models import LabOrder


def generate_barcode() -> str:
    """
    Generate a unique barcode for lab samples.
    Format: LAB-YYYYMMDD-HHMMSS-XXXXXXXX
    """
    prefix = "LAB"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"{prefix}-{timestamp}-{unique_id}"


def get_default_specimen_type(test_name: str, test_code: Optional[str] = None) -> str:
    """
    Determine the default specimen type based on test name or code.
    This is a simple heuristic - can be enhanced with more comprehensive mapping.
    """
    test_lower = test_name.lower() if test_name else ""
    test_code_lower = test_code.lower() if test_code else ""
    
    # Blood tests
    blood_indicators = ["blood", "hematology", "hemogram", "cbc", "bf", "esr", 
                       "glucose", "lipid", "liver", "renal", "thyroid", "iron",
                       "hb", "wbc", "platelet", " coagulation", "pt", "aptt", "inr"]
    
    # Urine tests
    urine_indicators = ["urine", "urinalysis", "mcu", "culture urine"]
    
    # Stool tests
    stool_indicators = ["stool", "feces", " occult", "ova", "parasite"]
    
    # Sputum tests
    sputum_indicators = ["sputum", "afb", "tb"]
    
    # Swab tests
    swab_indicators = ["swab", "throat", "wound", "vaginal", "hsv", "stool culture"]
    
    # CSF tests
    csf_indicators = ["csf", "spinal", "meningitis"]
    
    # Check blood indicators
    for indicator in blood_indicators:
        if indicator in test_lower or indicator in test_code_lower:
            return "Blood"
    
    # Check urine indicators
    for indicator in urine_indicators:
        if indicator in test_lower or indicator in test_code_lower:
            return "Urine"
    
    # Check stool indicators
    for indicator in stool_indicators:
        if indicator in test_lower or indicator in test_code_lower:
            return "Stool"
    
    # Check sputum indicators
    for indicator in sputum_indicators:
        if indicator in test_lower or indicator in test_code_lower:
            return "Sputum"
    
    # Check swab indicators
    for indicator in swab_indicators:
        if indicator in test_lower or indicator in test_code_lower:
            return "Swab"
    
    # Check CSF indicators
    for indicator in csf_indicators:
        if indicator in test_lower or indicator in test_code_lower:
            return "CSF"
    
    # Default to Blood for unknown tests
    return "Blood"


def auto_create_lab_sample(
    db: Session,
    lab_order: LabOrder,
    collected_by_id: int,
    sample_type: Optional[str] = None,
    collection_method: Optional[str] = None,
    collection_site: Optional[str] = None,
    storage_location: Optional[str] = None,
    auto_collect: bool = False
) -> LabSample:
    """
    Automatically create a lab sample for a lab order.
    
    Args:
        db: Database session
        lab_order: The lab order to create sample for
        collected_by_id: User ID of the person collecting the sample
        sample_type: Optional specimen type (auto-detected if not provided)
        collection_method: Optional collection method
        collection_site: Optional collection site
        storage_location: Optional storage location
        auto_collect: If True, mark sample as COLLECTED immediately
        
    Returns:
        Created LabSample instance
    """
    # Auto-detect specimen type if not provided
    if not sample_type:
        sample_type = get_default_specimen_type(
            lab_order.test_name, 
            lab_order.test_code
        )
    
    # Generate barcode
    barcode = generate_barcode()
    
    # Determine initial status
    if auto_collect:
        status = SampleStatus.COLLECTED
        collected_at = datetime.now()
    else:
        status = SampleStatus.COLLECTED  # Start as collected, waiting for receive
        collected_at = datetime.now()
    
    # Create the sample
    db_sample = LabSample(
        lab_order_id=lab_order.id,
        collected_by_id=collected_by_id,
        barcode=barcode,
        sample_type=sample_type,
        collection_method=collection_method,
        collection_site=collection_site,
        storage_location=storage_location,
        status=status.value,
        collected_at=collected_at
    )
    
    db.add(db_sample)
    db.commit()
    db.refresh(db_sample)
    
    return db_sample


def auto_create_samples_for_multiple_orders(
    db: Session,
    lab_orders: List[LabOrder],
    collected_by_id: int,
    sample_type_map: Optional[dict] = None,
    auto_collect: bool = False
) -> List[LabSample]:
    """
    Create samples for multiple lab orders at once.
    
    Args:
        db: Database session
        lab_orders: List of lab orders to create samples for
        collected_by_id: User ID of the person collecting samples
        sample_type_map: Optional dict mapping order_id to specimen type
        auto_collect: If True, mark samples as COLLECTED immediately
        
    Returns:
        List of created LabSample instances
    """
    created_samples = []
    
    for order in lab_orders:
        sample_type = None
        if sample_type_map and order.id in sample_type_map:
            sample_type = sample_type_map[order.id]
        
        try:
            sample = auto_create_lab_sample(
                db=db,
                lab_order=order,
                collected_by_id=collected_by_id,
                sample_type=sample_type,
                auto_collect=auto_collect
            )
            created_samples.append(sample)
        except Exception as e:
            print(f"Error creating sample for order {order.id}: {e}")
            # Continue with other orders even if one fails
    
    return created_samples


def create_sample_if_not_exists(
    db: Session,
    lab_order_id: int,
    collected_by_id: int,
    sample_type: Optional[str] = None
) -> Optional[LabSample]:
    """
    Check if a sample already exists for a lab order, and create one if not.
    
    Args:
        db: Database session
        lab_order_id: The lab order ID
        collected_by_id: User ID of the person collecting the sample
        sample_type: Optional specimen type
        
    Returns:
        Existing or new LabSample instance, or None if order not found
    """
    # Check if sample already exists
    existing_sample = db.query(LabSample).filter(
        LabSample.lab_order_id == lab_order_id,
        LabSample.is_active == True
    ).first()
    
    if existing_sample:
        return existing_sample
    
    # Get the lab order
    lab_order = db.query(LabOrder).filter(LabOrder.id == lab_order_id).first()
    if not lab_order:
        return None
    
    # Create new sample
    return auto_create_lab_sample(
        db=db,
        lab_order=lab_order,
        collected_by_id=collected_by_id,
        sample_type=sample_type
    )
