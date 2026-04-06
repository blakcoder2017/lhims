"""
Result Interpretation Service

Automated result interpretation and flagging for laboratory results.
Handles numeric results (LOW/NORMAL/HIGH/CRITICAL) and qualitative results.

Features:
- Numeric result auto-flagging based on reference ranges
- Qualitative result interpretation
- Override logging with audit trail
- Role-based override restrictions

Author: Hospital EMR System
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy.dialects import postgresql

from app.models.lab_template_models import LabReferenceRange, LabAuditEvent
from app.models.lab_models import ReferenceRange


class ResultFlag(str, Enum):
    """Result flag enumeration"""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL_LOW = "CRITICAL_LOW"
    CRITICAL_HIGH = "CRITICAL_HIGH"
    INVALID = "INVALID"
    NOT_DONE = "NOT_DONE"
    NOT_APPLICABLE = "NOT_APPLICABLE"  # No reference range defined for this test


class ResultInterpretation:
    """Result interpretation result"""
    def __init__(
        self,
        flag: ResultFlag,
        value: Any,
        unit: Optional[str] = None,
        reference_low: Optional[Decimal] = None,
        reference_high: Optional[Decimal] = None,
        critical_low: Optional[Decimal] = None,
        critical_high: Optional[Decimal] = None,
        interpretation: Optional[str] = None,
        is_overridden: bool = False,
        override_note: Optional[str] = None
    ):
        self.flag = flag
        self.value = value
        self.unit = unit
        self.reference_low = reference_low
        self.reference_high = reference_high
        self.critical_low = critical_low
        self.critical_high = critical_high
        self.interpretation = interpretation
        self.is_overridden = is_overridden
        self.override_note = override_note
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "flag": self.flag.value if isinstance(self.flag, Enum) else self.flag,
            "value": float(self.value) if isinstance(self.value, Decimal) else self.value,
            "unit": self.unit,
            "reference_low": float(self.reference_low) if self.reference_low is not None else None,
            "reference_high": float(self.reference_high) if self.reference_high is not None else None,
            "critical_low": float(self.critical_low) if self.critical_low is not None else None,
            "critical_high": float(self.critical_high) if self.critical_high is not None else None,
            "interpretation": self.interpretation,
            "is_overridden": self.is_overridden,
            "override_note": self.override_note
        }


def interpret_numeric_result(
    value: float,
    reference_low: Optional[float] = None,
    reference_high: Optional[float] = None,
    critical_low: Optional[float] = None,
    critical_high: Optional[float] = None,
    unit: Optional[str] = None
) -> ResultInterpretation:
    """
    Interpret a numeric result against reference ranges.
    
    Args:
        value: The numeric result value
        reference_low: Lower limit of normal range
        reference_high: Upper limit of normal range
        critical_low: Critical low value
        critical_high: Critical high value
        unit: Unit of measurement
    
    Returns:
        ResultInterpretation with flag and details
    """
    # Handle missing reference range - don't flag as abnormal if no reference range exists
    if reference_low is None and reference_high is None:
        return ResultInterpretation(
            flag=ResultFlag.NOT_APPLICABLE,  # No reference range - no flag
            value=value,
            unit=unit,
            interpretation="No reference range available"
        )
    
    # Check for critical values first (most important)
    if critical_low is not None and value <= critical_low:
        return ResultInterpretation(
            flag=ResultFlag.CRITICAL_LOW,
            value=value,
            unit=unit,
            reference_low=reference_low,
            reference_high=reference_high,
            critical_low=critical_low,
            critical_high=critical_high,
            interpretation=f"CRITICAL LOW: Value {value} is below critical threshold {critical_low}"
        )
    
    if critical_high is not None and value >= critical_high:
        return ResultInterpretation(
            flag=ResultFlag.CRITICAL_HIGH,
            value=value,
            unit=unit,
            reference_low=reference_low,
            reference_high=reference_high,
            critical_low=critical_low,
            critical_high=critical_high,
            interpretation=f"CRITICAL HIGH: Value {value} is above critical threshold {critical_high}"
        )
    
    # Check normal range
    if reference_low is not None and value < reference_low:
        return ResultInterpretation(
            flag=ResultFlag.LOW,
            value=value,
            unit=unit,
            reference_low=reference_low,
            reference_high=reference_high,
            critical_low=critical_low,
            critical_high=critical_high,
            interpretation=f"Low: Value {value} is below normal range ({reference_low}-{reference_high})"
        )
    
    if reference_high is not None and value > reference_high:
        return ResultInterpretation(
            flag=ResultFlag.HIGH,
            value=value,
            unit=unit,
            reference_low=reference_low,
            reference_high=reference_high,
            critical_low=critical_low,
            critical_high=critical_high,
            interpretation=f"High: Value {value} is above normal range ({reference_low}-{reference_high})"
        )
    
    # Normal range
    return ResultInterpretation(
        flag=ResultFlag.NORMAL,
        value=value,
        unit=unit,
        reference_low=reference_low,
        reference_high=reference_high,
        critical_low=critical_low,
        critical_high=critical_high,
        interpretation=f"Normal: Value {value} is within normal range ({reference_low}-{reference_high})"
    )


# Qualitative result interpretations for common tests
QUALITATIVE_INTERPRETATIONS = {
    # Blood grouping
    "blood_group": {
        "A": "Blood Group A",
        "B": "Blood Group B",
        "AB": "Blood Group AB",
        "O": "Blood Group O",
        "Rh positive": "Rhesus Positive",
        "Rh negative": "Rhesus Negative"
    },
    # Rapid tests
    "hiv": {
        "negative": "Non-reactive for HIV",
        "positive": "Reactive for HIV - Confirmatory testing required",
        "invalid": "Invalid result - Repeat test"
    },
    "hepatitis_b": {
        "negative": "Non-reactive for HBsAg",
        "positive": "Reactive for HBsAg - Indicates active HBV infection",
        "indeterminate": "Indeterminate - Repeat testing required"
    },
    "hepatitis_c": {
        "negative": "Non-reactive for HCV",
        "positive": "Reactive for HCV - Confirmatory testing required"
    },
    "syphilis": {
        "negative": "Non-reactive for syphilis",
        "positive": "Reactive for syphilis - Treatment required",
        "weakly_positive": "Weakly reactive - Repeat testing recommended"
    },
    "malaria": {
        "negative": "No malaria parasites detected",
        "positive": "Malaria parasites detected",
        "pf": "Plasmodium falciparum detected",
        "pv": "Plasmodium vivax detected",
        "pm": "Plasmodium malariae detected",
        "po": "Plasmodium ovale detected"
    },
    "pregnancy_test": {
        "negative": "Not pregnant",
        "positive": "Pregnant",
        "invalid": "Invalid result - Repeat test"
    },
    "sickling": {
        "negative": "No sickle cells detected - Normal hemoglobin",
        "positive": "Sickle cells detected - Sickle cell trait/disease",
        "trait": "Sickle cell trait (AS)",
        "disease": "Sickle cell disease (SS)"
    },
    "urine_leukocytes": {
        "negative": "No leukocytes detected",
        "positive": "Leukocytes present - Indicates infection or inflammation"
    },
    "urine_nitrite": {
        "negative": "No nitrites detected",
        "positive": "Nitrites present - Indicates bacterial infection"
    },
    "urine_protein": {
        "negative": "No protein detected",
        "trace": "Trace protein - May be normal or early kidney issue",
        "positive": "Protein detected - May indicate kidney disease"
    },
    "urine_glucose": {
        "negative": "No glucose detected",
        "positive": "Glucose detected - May indicate diabetes"
    },
    "urine_blood": {
        "negative": "No blood detected",
        "positive": "Blood detected - Requires further investigation"
    }
}


def interpret_qualitative_result(
    value: str,
    field_code: Optional[str] = None,
    result_set: Optional[Dict[str, str]] = None
) -> ResultInterpretation:
    """
    Interpret a qualitative result based on known result sets.
    
    Args:
        value: The qualitative result value
        field_code: Field code for lookup
        result_set: Custom result set for interpretation
    
    Returns:
        ResultInterpretation with flag and details
    """
    if not value:
        return ResultInterpretation(
            flag=ResultFlag.INVALID,
            value=value,
            interpretation="No result provided"
        )
    
    value_lower = value.lower().strip()
    
    # Check field-specific interpretations first
    if field_code and field_code.lower() in QUALITATIVE_INTERPRETATIONS:
        field_interp = QUALITATIVE_INTERPRETATIONS[field_code.lower()]
        # Try exact match first
        if value in field_interp:
            interpretation = field_interp[value]
        # Try lowercase match
        elif value_lower in [k.lower() for k in field_interp.keys()]:
            for k, v in field_interp.items():
                if k.lower() == value_lower:
                    interpretation = v
                    break
            else:
                interpretation = value
        else:
            interpretation = value
    elif result_set:
        interpretation = result_set.get(value, value)
    else:
        interpretation = value
    
    # Determine flag based on value
    positive_values = ["positive", "reactive", "yes", "high", "abnormal"]
    negative_values = ["negative", "non-reactive", "no", "normal", "not detected"]
    
    if value_lower in positive_values or any(p in value_lower for p in positive_values):
        if "critical" in interpretation.lower() or "confirmatory" in interpretation.lower():
            flag = ResultFlag.HIGH  # Using HIGH as general "attention needed" flag
        else:
            flag = ResultFlag.HIGH
    elif value_lower in negative_values or any(n in value_lower for n in negative_values):
        flag = ResultFlag.NORMAL
    else:
        flag = ResultFlag.NORMAL  # Default for other qualitative results
    
    return ResultInterpretation(
        flag=flag,
        value=value,
        interpretation=interpretation
    )


def log_reference_range_override(
    db: Session,
    entity_type: str,
    entity_id: str,
    field_code: str,
    original_flag: str,
    new_flag: str,
    override_note: str,
    user_id: int
) -> LabAuditEvent:
    """
    Log a reference range override for audit purposes.
    
    Args:
        db: Database session
        entity_type: Type of entity (e.g., "lab_order")
        entity_id: ID of the entity
        field_code: Field code that was overridden
        original_flag: Original flag before override
        new_flag: New flag after override
        override_note: Reason for override
        user_id: User who made the override
    
    Returns:
        Created LabAuditEvent
    """
    event = LabAuditEvent(
        entity_type=entity_type,
        entity_id=str(entity_id),
        action="reference_range_override",
        old_json={
            "field_code": field_code,
            "flag": original_flag
        },
        new_json={
            "field_code": field_code,
            "flag": new_flag,
            "override_note": override_note
        },
        user_id=user_id
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def can_override_flag(user_role: str) -> bool:
    """
    Check if a user role can override reference range flags.
    
    Args:
        user_role: User's role name
    
    Returns:
        True if user can override
    """
    # Only Lab Scientist, Senior Lab Scientist, and Admin can override
    allowed_roles = [
        "Admin",
        "Lab Scientist",
        "Senior Lab Scientist",
        "Lab Manager"
    ]
    return user_role in allowed_roles


def interpret_results_batch(
    db: Session,
    results: Dict[str, Any],
    patient_age_days: Optional[int] = None,
    patient_sex: Optional[str] = None,
    template_fields: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Interpret a batch of results with their flags.
    
    Args:
        db: Database session
        results: Dictionary of field_code -> value
        patient_age_days: Patient age in days
        patient_sex: Patient sex
        template_fields: Template field definitions with types
    
    Returns:
        Dictionary with interpreted results and flags
    """
    from app.services.reference_range_engine import get_field_reference_range
    
    interpreted_results = {}
    flags = {}
    
    for field_code, value in results.items():
        if value is None:
            continue
        
        # Get field definition if available
        field_def = None
        if template_fields and field_code in template_fields:
            field_def = template_fields[field_code]
        
        field_type = field_def.get("type", "text") if field_def else "text"
        
        # Get reference range for numeric fields
        ref_range = None
        if field_type == "numeric":
            ref_range = get_field_reference_range(
                db=db,
                field_code=field_code,
                patient_age_days=patient_age_days,
                patient_sex=patient_sex
            )
        
        # Interpret based on type.
        # Values from JSON form submissions arrive as strings even for numeric fields,
        # so always attempt float conversion rather than relying on isinstance checks.
        numeric_value = None
        if field_type == "numeric":
            try:
                numeric_value = float(value)
            except (ValueError, TypeError):
                pass

        if field_type == "numeric" and numeric_value is not None:
            # Check if reference range exists before interpreting
            has_reference_range = ref_range is not None and (ref_range.low is not None or ref_range.high is not None)

            interpretation = interpret_numeric_result(
                value=numeric_value,
                reference_low=float(ref_range.low) if ref_range and ref_range.low else None,
                reference_high=float(ref_range.high) if ref_range and ref_range.high else None,
                critical_low=float(ref_range.critical_low) if ref_range and ref_range.critical_low else None,
                critical_high=float(ref_range.critical_high) if ref_range and ref_range.critical_high else None,
                unit=ref_range.unit if ref_range else None
            )

            interpreted_results[field_code] = interpretation.to_dict()
            # Only store a flag when there is an actual reference range to compare against
            if has_reference_range:
                flags[field_code] = interpretation.flag.value if isinstance(interpretation.flag, Enum) else interpretation.flag
        else:
            # Qualitative interpretation (text, choice, or un-parseable numeric)
            field_code_for_lookup = field_def.get("code", field_code) if field_def else field_code
            interpretation = interpret_qualitative_result(
                value=str(value),
                field_code=field_code_for_lookup
            )
            interpreted_results[field_code] = interpretation.to_dict()
            flags[field_code] = interpretation.flag.value if isinstance(interpretation.flag, Enum) else interpretation.flag
    
    return {
        "interpreted_results": interpreted_results,
        "flags": flags
    }
