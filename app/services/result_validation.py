"""
Result Validation Service

This module provides validation for lab and radiology results against
reference ranges and quality control standards.
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, List, Any
from decimal import Decimal
from datetime import datetime

from app.models.lab_models import ReferenceRange, QCRecord, QCStatus
from app.models.encounter_models import LabOrder
from app.models.lab_catalog_models import LabTest


class ValidationResult:
    """Result of validation check"""
    def __init__(self, is_valid: bool, status: str, message: str, warnings: List[str] = None):
        self.is_valid = is_valid
        self.status = status  # "normal", "abnormal", "critical", "invalid"
        self.message = message
        self.warnings = warnings or []


def parse_numeric_result(result_text: str) -> Optional[Decimal]:
    """
    Try to extract numeric value from result text.
    Returns the first numeric value found, or None.
    """
    import re
    # Look for numeric patterns (including decimals)
    patterns = [
        r'(\d+\.?\d*)',  # Simple number
        r'(\d+\.?\d*)\s*(mg/dl|g/dl|mmol/l|units|%)',  # Number with units
    ]
    
    for pattern in patterns:
        match = re.search(pattern, result_text, re.IGNORECASE)
        if match:
            try:
                return Decimal(match.group(1))
            except (ValueError, TypeError):
                continue
    
    return None


def check_reference_range(
    db: Session,
    lab_order: LabOrder,
    result_value: Optional[Decimal],
    patient_age_years: Optional[int] = None,
    patient_gender: Optional[str] = None
) -> ValidationResult:
    """
    Check lab result against reference ranges.
    
    Args:
        db: Database session
        lab_order: The lab order with result
        result_value: Numeric value extracted from result
        patient_age_years: Patient age in years
        patient_gender: Patient gender
        
    Returns:
        ValidationResult with validation status
    """
    if not result_value:
        return ValidationResult(
            is_valid=True,
            status="normal",
            message="Result entered (non-numeric value)",
            warnings=["Could not extract numeric value for range checking"]
        )
    
    # Find matching reference ranges
    query = db.query(ReferenceRange).filter(
        ReferenceRange.is_active == True
    )
    
    # Try to match by test name or code
    if lab_order.test_name:
        query = query.filter(
            ReferenceRange.test_name.ilike(f"%{lab_order.test_name}%")
        )
    elif lab_order.test_code:
        query = query.filter(
            ReferenceRange.test_code == lab_order.test_code
        )
    
    ranges = query.all()
    
    if not ranges:
        return ValidationResult(
            is_valid=True,
            status="normal",
            message="Result entered (no reference range defined)",
            warnings=["No reference range found for this test"]
        )
    
    # Find best matching range (considering age and gender)
    best_range = None
    for ref_range in ranges:
        # Check age match
        age_match = True
        if ref_range.age_min is not None and patient_age_years:
            if patient_age_years < ref_range.age_min:
                age_match = False
        if ref_range.age_max is not None and patient_age_years:
            if patient_age_years > ref_range.age_max:
                age_match = False
        
        # Check gender match
        gender_match = True
        if ref_range.gender and patient_gender:
            if ref_range.gender.lower() != patient_gender.lower():
                gender_match = False
        
        if age_match and gender_match:
            best_range = ref_range
            break
    
    # If no specific match, use first range without age/gender restrictions
    if not best_range and ranges:
        for ref_range in ranges:
            if not ref_range.age_min and not ref_range.age_max and not ref_range.gender:
                best_range = ref_range
                break
        if not best_range:
            best_range = ranges[0]
    
    if not best_range:
        return ValidationResult(
            is_valid=True,
            status="normal",
            message="Result entered",
            warnings=["No matching reference range found"]
        )
    
    # Check against range
    warnings = []
    status = "normal"
    message = "Result within normal range"
    
    if best_range.normal_min and result_value < best_range.normal_min:
        status = "abnormal"
        message = f"Result below normal range (min: {best_range.normal_min})"
        warnings.append("Low value detected")
        
        # Check if critical
        if best_range.critical_low and result_value <= best_range.critical_low:
            status = "critical"
            message = f"CRITICAL: Result critically low (min: {best_range.normal_min}, critical: {best_range.critical_low})"
    
    elif best_range.normal_max and result_value > best_range.normal_max:
        status = "abnormal"
        message = f"Result above normal range (max: {best_range.normal_max})"
        warnings.append("High value detected")
        
        # Check if critical
        if best_range.critical_high and result_value >= best_range.critical_high:
            status = "critical"
            message = f"CRITICAL: Result critically high (max: {best_range.normal_max}, critical: {best_range.critical_high})"
    
    return ValidationResult(
        is_valid=True,
        status=status,
        message=message,
        warnings=warnings
    )


def validate_lab_result(
    db: Session,
    lab_order: LabOrder,
    result_text: str
) -> ValidationResult:
    """
    Validate a lab result against reference ranges and QC standards.
    
    Args:
        db: Database session
        lab_order: The lab order with result
        result_text: The result text entered
        
    Returns:
        ValidationResult with validation status
    """
    # Basic validation
    if not result_text or not result_text.strip():
        return ValidationResult(
            is_valid=False,
            status="invalid",
            message="Result cannot be empty"
        )
    
    # Get patient information for age/gender-specific ranges
    # Check both encounter.patient and direct patient_id (for walk-in orders)
    patient = None
    if lab_order.encounter and lab_order.encounter.patient:
        patient = lab_order.encounter.patient
    elif lab_order.patient_id:
        # For walk-in orders, get patient directly from lab_order.patient_id
        from app.models.patient_models import Patient
        patient = db.query(Patient).filter(Patient.id == lab_order.patient_id).first()
    
    if not patient:
        # No patient found - skip age/gender specific validation
        return ValidationResult(
            is_valid=True,
            status="normal",
            message="Result recorded (no patient data for validation)"
        )
    
    patient_age_years = None
    if patient.date_of_birth:
        from datetime import date
        today = date.today()
        patient_age_years = today.year - patient.date_of_birth.year - (
            (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
        )
    
    patient_gender = patient.gender
    
    # Try to extract numeric value
    result_value = parse_numeric_result(result_text)
    
    # Check against reference ranges
    validation = check_reference_range(
        db, lab_order, result_value, patient_age_years, patient_gender
    )
    
    # Check QC status for this order
    qc_records = db.query(QCRecord).filter(
        QCRecord.lab_order_id == lab_order.id,
        QCRecord.status.in_([QCStatus.FAILED.value, QCStatus.OUT_OF_RANGE.value])
    ).all()
    
    if qc_records:
        validation.warnings.append("QC check failed for this order")
        if validation.status == "normal":
            validation.status = "abnormal"
            validation.message = "Result entered but QC check failed"
    
    return validation


def validate_radiology_report(
    db: Session,
    radiology_order,
    report_text: str
) -> ValidationResult:
    """
    Validate a radiology report.
    Currently basic validation - can be enhanced with structured report validation.
    
    Args:
        db: Database session
        radiology_order: The radiology order
        report_text: The report text entered
        
    Returns:
        ValidationResult with validation status
    """
    if not report_text or not report_text.strip():
        return ValidationResult(
            is_valid=False,
            status="invalid",
            message="Report cannot be empty"
        )
    
    # Basic length check
    if len(report_text.strip()) < 10:
        return ValidationResult(
            is_valid=True,
            status="normal",
            message="Report entered",
            warnings=["Report seems very short - please verify completeness"]
        )
    
    return ValidationResult(
        is_valid=True,
        status="normal",
        message="Report entered and validated"
    )

