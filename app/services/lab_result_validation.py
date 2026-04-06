"""
Lab Result Validation and Flagging Service

Functions:
- validate_result(): validates required fields, requiredIf rules, numeric parsing, min/max ranges
- lookup_reference_range(): matches by field_code + sex + age in days + facility
- compute_flags(): computes L/H/CRITICAL flags based on reference ranges
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.lab_template_models import LabReferenceRange


@dataclass
class ValidationError:
    """Single validation error"""
    field_code: str
    message: str


@dataclass
class FlagInfo:
    """Flag information for a field"""
    field_code: str
    flag: str  # L, H, CRITICAL, or None
    value: Any
    low: Optional[float] = None
    high: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    text_range: Optional[str] = None
    unit: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validation"""
    is_valid: bool
    errors: List[ValidationError]
    flags: List[FlagInfo]
    warnings: List[str]


def validate_result(
    schema_json: Dict[str, Any],
    result_json: Dict[str, Any],
    patient_context: Optional[Dict[str, Any]] = None
) -> ValidationResult:
    """
    Validate result against schema rules.
    
    Args:
        schema_json: The template schema
        result_json: The result data to validate
        patient_context: Optional patient info (gender, date_of_birth)
        
    Returns:
        ValidationResult with errors and flags
    """
    errors: List[ValidationError] = []
    flags: List[FlagInfo] = []
    warnings: List[str] = []
    
    fields = schema_json.get("fields", {})
    rules = schema_json.get("rules", {})
    required_if_rules = rules.get("requiredIf", [])
    
    patient_gender = patient_context.get("gender") if patient_context else None
    patient_dob = patient_context.get("date_of_birth") if patient_context else None
    
    # Calculate age in days
    age_days = None
    if patient_dob:
        if isinstance(patient_dob, str):
            try:
                patient_dob = date.fromisoformat(patient_dob)
            except:
                patient_dob = None
        if patient_dob:
            age_days = (date.today() - patient_dob).days
    
    for field_code, field_def in fields.items():
        field_type = field_def.get("type")
        value = result_json.get(field_code)
        
        # Skip if field not present
        if value is None or value == "":
            # Check if required
            if field_def.get("required"):
                # Check requiredIf rules
                is_required = True
                for req_rule in required_if_rules:
                    target = req_rule.get("target") or req_rule.get("target_code")
                    if target == field_code:
                        condition = req_rule.get("showIf") or req_rule.get("if")
                        if condition:
                            cond_field = condition.get("field")
                            cond_op = condition.get("op", "==")
                            cond_value = condition.get("value")
                            actual_value = result_json.get(cond_field)
                            
                            if cond_op == "==":
                                if actual_value != cond_value:
                                    is_required = False
                                    break
                            elif cond_op == "!=":
                                if actual_value == cond_value:
                                    is_required = False
                                    break
                
                if is_required:
                    errors.append(ValidationError(
                        field_code=field_code,
                        message=f"{field_def.get('label', field_code)} is required"
                    ))
            continue
        
        # Validate numeric fields
        if field_type == "numeric":
            try:
                num_value = float(value) if isinstance(value, (int, float, Decimal)) else float(value)
            except (ValueError, InvalidOperation):
                errors.append(ValidationError(
                    field_code=field_code,
                    message=f"{field_def.get('label', field_code)} must be a valid number"
                ))
                continue
            
            # Check min/max plausible ranges from schema
            if "min" in field_def:
                if num_value < field_def["min"]:
                    warnings.append(f"{field_def.get('label', field_code)} below schema minimum")
            if "max" in field_def:
                if num_value > field_def["max"]:
                    warnings.append(f"{field_def.get('label', field_code)} above schema maximum")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        flags=flags,  # Flags computed separately
        warnings=warnings
    )


def lookup_reference_range(
    db: Session,
    field_code: str,
    sex: Optional[str] = None,
    age_days: Optional[int] = None,
    facility_id: Optional[int] = None
) -> Optional[LabReferenceRange]:
    """
    Lookup reference range by field_code + sex + age in days + facility.
    
    Priority:
    1. Exact match (sex + age range + facility)
    2. Sex match (sex + age range, any facility)
    3. Default (ANY sex + age range)
    """
    # Build query - try most specific first
    queries = [
        # Exact match with facility
        {"field_code": field_code, "sex": sex, "facility_id": facility_id},
        # Exact match without facility
        {"field_code": field_code, "sex": sex, "facility_id": None},
        # Any facility, sex match
        {"field_code": field_code, "sex": sex},
        # Default ANY
        {"field_code": field_code, "sex": "ANY"},
    ]
    
    for query_dict in queries:
        query = db.query(LabReferenceRange).filter(
            LabReferenceRange.field_code == query_dict["field_code"]
        )
        
        q_sex = query_dict.get("sex")
        if q_sex:
            query = query.filter(LabReferenceRange.sex.in_([q_sex, "ANY"]))
        
        q_facility = query_dict.get("facility_id")
        if q_facility is not None:
            query = query.filter(
                (LabReferenceRange.facility_id == q_facility) | 
                (LabReferenceRange.facility_id.is_(None))
            )
        
        # Filter by age range if provided
        if age_days is not None:
            query = query.filter(
                (LabReferenceRange.age_min_days.is_(None)) | 
                (LabReferenceRange.age_min_days <= age_days)
            )
            query = query.filter(
                (LabReferenceRange.age_max_days.is_(None)) | 
                (LabReferenceRange.age_max_days >= age_days)
            )
        
        # Order by specificity (more specific sex first)
        query = query.order_by(
            LabReferenceRange.sex.desc()  # Specific sex before ANY
        )
        
        result = query.first()
        if result:
            return result
    
    return None


def compute_flags(
    db: Session,
    schema_json: Dict[str, Any],
    result_json: Dict[str, Any],
    patient_context: Optional[Dict[str, Any]] = None
) -> List[FlagInfo]:
    """
    Compute flags for result values based on reference ranges.
    
    Flags:
    - L: Value below normal range
    - H: Value above normal range
    - CRITICAL: Value at or beyond critical threshold
    """
    flags: List[FlagInfo] = []
    
    fields = schema_json.get("fields", {})
    
    patient_gender = patient_context.get("gender") if patient_context else None
    patient_dob = patient_context.get("date_of_birth") if patient_context else None
    
    # Calculate age in days
    age_days = None
    if patient_dob:
        if isinstance(patient_dob, str):
            try:
                patient_dob = date.fromisoformat(patient_dob)
            except:
                patient_dob = None
        if patient_dob:
            age_days = (date.today() - patient_dob).days
    
    facility_id = patient_context.get("facility_id") if patient_context else None
    
    for field_code, field_def in fields.items():
        field_type = field_def.get("type")
        value = result_json.get(field_code)
        
        # Only flag numeric fields
        if field_type != "numeric":
            continue
        
        if value is None or value == "":
            continue
        
        # Try to parse as number
        try:
            num_value = float(value) if isinstance(value, (int, float, Decimal)) else float(value)
        except (ValueError, InvalidOperation):
            continue
        
        # Lookup reference range
        ref_range = lookup_reference_range(
            db, field_code, patient_gender, age_days, facility_id
        )
        
        if not ref_range:
            # Also try field_code with prefix (common pattern)
            ref_range = lookup_reference_range(
                db, f"{field_code}_result", patient_gender, age_days, facility_id
            )
        
        # Skip if no reference range OR if reference range has no numeric bounds defined
        if not ref_range or (ref_range.low is None and ref_range.high is None):
            continue
        
        # Determine flag
        flag = None
        
        # Check critical first
        if ref_range.critical_low is not None and num_value <= ref_range.critical_low:
            flag = "CRITICAL"
        elif ref_range.critical_high is not None and num_value >= ref_range.critical_high:
            flag = "CRITICAL"
        # Then check normal range
        elif ref_range.low is not None and num_value < ref_range.low:
            flag = "L"
        elif ref_range.high is not None and num_value > ref_range.high:
            flag = "H"
        
        if flag:
            flags.append(FlagInfo(
                field_code=field_code,
                flag=flag,
                value=num_value,
                low=float(ref_range.low) if ref_range.low else None,
                high=float(ref_range.high) if ref_range.high else None,
                critical_low=float(ref_range.critical_low) if ref_range.critical_low else None,
                critical_high=float(ref_range.critical_high) if ref_range.critical_high else None,
                text_range=ref_range.text_range,
                unit=ref_range.unit
            ))
    
    return flags


def validate_and_flag(
    db: Session,
    schema_json: Dict[str, Any],
    result_json: Dict[str, Any],
    patient_context: Optional[Dict[str, Any]] = None
) -> ValidationResult:
    """
    Combined validation and flagging.
    """
    validation = validate_result(schema_json, result_json, patient_context)
    flags = compute_flags(db, schema_json, result_json, patient_context)
    
    return ValidationResult(
        is_valid=validation.is_valid,
        errors=validation.errors,
        flags=flags,
        warnings=validation.warnings
    )


def get_flags_dict(flags: List[FlagInfo]) -> Dict[str, Dict[str, Any]]:
    """
    Convert flags list to dict keyed by field_code for easy lookup.
    """
    result = {}
    for f in flags:
        result[f.field_code] = {
            "flag": f.flag,
            "value": f.value,
            "low": f.low,
            "high": f.high,
            "critical_low": f.critical_low,
            "critical_high": f.critical_high,
            "text_range": f.text_range,
            "unit": f.unit
        }
    return result


def has_critical_flags(flags) -> bool:
    """
    Check if any flag in the list is critical.
    
    Args:
        flags: List of FlagInfo objects or dict with flag information
    
    Returns:
        True if any flag is CRITICAL, False otherwise
    """
    if not flags:
        return False
    
    # Handle list of FlagInfo objects
    if isinstance(flags, list):
        for flag in flags:
            if hasattr(flag, 'flag') and flag.flag == 'CRITICAL':
                return True
    # Handle dict (stored flags_json)
    elif isinstance(flags, dict):
        for field_code, flag_info in flags.items():
            if isinstance(flag_info, dict) and flag_info.get('flag') == 'CRITICAL':
                return True
            elif hasattr(flag_info, 'flag') and flag_info.flag == 'CRITICAL':
                return True
    
    return False
