"""
Reference Range Engine Service

Unified reference range selection engine that intelligently selects the most appropriate
reference range based on patient demographics (age, sex) with fallback logic.

Selection Priority:
1. Sex-specific → Both sexes → Default (ANY)
2. Age-specific → Adult → Global fallback
3. Facility-specific → Default facility

Author: Hospital EMR System
"""

from datetime import date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.lab_template_models import LabReferenceRange
from app.models.lab_models import ReferenceRange


class ReferenceRangeResult:
    """Result of reference range lookup"""
    def __init__(
        self,
        low: Optional[Decimal] = None,
        high: Optional[Decimal] = None,
        critical_low: Optional[Decimal] = None,
        critical_high: Optional[Decimal] = None,
        unit: Optional[str] = None,
        text_range: Optional[str] = None,
        interpretation: Optional[str] = None,
        source_table: str = "lab_reference_ranges",
        range_id: Any = None,
        is_fallback: bool = False
    ):
        self.low = low
        self.high = high
        self.critical_low = critical_low
        self.critical_high = critical_high
        self.unit = unit
        self.text_range = text_range
        self.interpretation = interpretation
        self.source_table = source_table
        self.range_id = range_id
        self.is_fallback = is_fallback
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "low": float(self.low) if self.low is not None else None,
            "high": float(self.high) if self.high is not None else None,
            "critical_low": float(self.critical_low) if self.critical_low is not None else None,
            "critical_high": float(self.critical_high) if self.critical_high is not None else None,
            "unit": self.unit,
            "text_range": self.text_range,
            "interpretation": self.interpretation,
            "source_table": self.source_table,
            "range_id": str(self.range_id) if self.range_id else None,
            "is_fallback": self.is_fallback
        }


def calculate_age_in_days(date_of_birth: date, reference_date: Optional[date] = None) -> int:
    """Calculate age in days from date of birth"""
    if reference_date is None:
        reference_date = date.today()
    return (reference_date - date_of_birth).days


def normalize_sex(sex: Optional[str]) -> str:
    """Normalize sex value for comparison"""
    if not sex:
        return "ANY"
    sex_upper = sex.upper()
    if sex_upper in ["M", "MALE"]:
        return "M"
    elif sex_upper in ["F", "FEMALE"]:
        return "F"
    return "ANY"


def get_field_reference_range(
    db: Session,
    field_code: str,
    patient_age_days: Optional[int] = None,
    patient_sex: Optional[str] = None,
    facility_id: Optional[int] = None
) -> Optional[ReferenceRangeResult]:
    """
    Get the most appropriate reference range for a field code.
    
    Priority:
    1. Exact sex match + exact age match
    2. Exact sex match + age range overlap
    3. ANY sex + exact age match
    4. ANY sex + age range overlap
    5. Facility-specific + exact match
    6. Global fallback
    
    Args:
        db: Database session
        field_code: The field code to look up (e.g., "Hb", "WBC")
        patient_age_days: Patient's age in days
        patient_sex: Patient's sex (M, F, or ANY)
        facility_id: Facility ID for multi-facility support
    
    Returns:
        ReferenceRangeResult or None
    """
    if not field_code:
        return None
    
    sex = normalize_sex(patient_sex)
    
    # Build base query
    query = db.query(LabReferenceRange).filter(
        LabReferenceRange.field_code == field_code
    )
    
    # Get all matching ranges first
    all_ranges = query.all()
    
    if not all_ranges:
        return None
    
    # Score each range based on specificity
    scored_ranges = []
    for rr in all_ranges:
        score = 0
        notes = []
        
        # Sex specificity (higher = more specific)
        if rr.sex == sex:
            score += 100
            notes.append(f"exact_sex({sex})")
        elif rr.sex == "ANY":
            score += 10
            notes.append("any_sex")
        else:
            continue  # Skip non-matching sex
        
        # Age specificity
        if patient_age_days is not None:
            age_match = False
            if rr.age_min_days is not None and rr.age_max_days is not None:
                if rr.age_min_days <= patient_age_days <= rr.age_max_days:
                    score += 50
                    age_match = True
                    notes.append(f"exact_age({patient_age_days})")
            elif rr.age_min_days is not None and rr.age_max_days is None:
                if patient_age_days >= rr.age_min_days:
                    score += 30
                    age_match = True
                    notes.append(f"min_age({rr.age_min_days})")
            elif rr.age_min_days is None and rr.age_max_days is not None:
                if patient_age_days <= rr.age_max_days:
                    score += 30
                    age_match = True
                    notes.append(f"max_age({rr.age_max_days})")
            else:
                # No age restriction = global
                score += 5
                notes.append("no_age_restriction")
        
        # Facility specificity
        if facility_id is not None:
            if rr.facility_id == facility_id:
                score += 20
                notes.append(f"facility({facility_id})")
            elif rr.facility_id is None:
                score += 1
                notes.append("default_facility")
        
        scored_ranges.append((score, rr, notes))
    
    if not scored_ranges:
        return None
    
    # Sort by score (highest first)
    scored_ranges.sort(key=lambda x: x[0], reverse=True)
    best_range = scored_ranges[0][1]
    is_fallback = scored_ranges[0][0] < 100
    
    return ReferenceRangeResult(
        low=best_range.low,
        high=best_range.high,
        critical_low=best_range.critical_low,
        critical_high=best_range.critical_high,
        unit=best_range.unit,
        text_range=best_range.text_range,
        source_table="lab_reference_ranges",
        range_id=best_range.id,
        is_fallback=is_fallback
    )


def get_test_reference_range(
    db: Session,
    test_id: Optional[int] = None,
    test_name: Optional[str] = None,
    patient_age_years: Optional[int] = None,
    patient_sex: Optional[str] = None
) -> Optional[ReferenceRangeResult]:
    """
    Get reference range from the test-level reference_ranges table.
    
    Priority:
    1. Exact sex match + exact age match
    2. Exact sex match + age range overlap
    3. ANY sex + exact age match
    4. ANY sex + age range overlap
    5. Default adult fallback
    
    Args:
        db: Database session
        test_id: Lab test ID
        test_name: Lab test name
        patient_age_years: Patient's age in years
        patient_sex: Patient's sex
    
    Returns:
        ReferenceRangeResult or None
    """
    if not test_id and not test_name:
        return None
    
    sex = normalize_sex(patient_sex)
    
    # Build base query
    query = db.query(ReferenceRange).filter(
        ReferenceRange.is_active == True
    )
    
    if test_id:
        query = query.filter(ReferenceRange.test_id == test_id)
    elif test_name:
        query = query.filter(ReferenceRange.test_name == test_name)
    
    all_ranges = query.all()
    
    if not all_ranges:
        return None
    
    # Score each range
    scored_ranges = []
    for rr in all_ranges:
        score = 0
        
        # Sex specificity
        if rr.gender and rr.gender.upper() == sex:
            score += 100
        elif not rr.gender or rr.gender.upper() in ["ANY", "BOTH"]:
            score += 10
        
        # Age specificity (convert years to comparable)
        if patient_age_years is not None:
            age_match = False
            if rr.age_min is not None and rr.age_max is not None:
                if rr.age_min <= patient_age_years <= rr.age_max:
                    score += 50
                    age_match = True
            elif rr.age_min is not None and rr.age_max is None:
                if patient_age_years >= rr.age_min:
                    score += 30
                    age_match = True
            elif rr.age_min is None and rr.age_max is not None:
                if patient_age_years <= rr.age_max:
                    score += 30
                    age_match = True
            else:
                score += 5  # No age restriction
        
        scored_ranges.append((score, rr))
    
    if not scored_ranges:
        return None
    
    scored_ranges.sort(key=lambda x: x[0], reverse=True)
    best_range = scored_ranges[0][1]
    is_fallback = scored_ranges[0][0] < 100
    
    return ReferenceRangeResult(
        low=best_range.normal_min,
        high=best_range.normal_max,
        critical_low=best_range.critical_low,
        critical_high=best_range.critical_high,
        unit=best_range.unit,
        source_table="reference_ranges",
        range_id=best_range.id,
        is_fallback=is_fallback
    )


def get_unified_reference_range(
    db: Session,
    field_code: Optional[str] = None,
    test_id: Optional[int] = None,
    test_name: Optional[str] = None,
    patient_age_days: Optional[int] = None,
    patient_age_years: Optional[int] = None,
    patient_sex: Optional[str] = None,
    facility_id: Optional[int] = None
) -> Optional[ReferenceRangeResult]:
    """
    Unified reference range lookup that tries multiple sources.
    
    Priority:
    1. Field-based reference range (lab_reference_ranges) - most specific
    2. Test-level reference range (reference_ranges) - fallback
    
    Args:
        db: Database session
        field_code: Field code for template-based results
        test_id: Test ID for catalog-based results
        test_name: Test name for catalog-based results
        patient_age_days: Patient age in days (for field-based lookup)
        patient_age_years: Patient age in years (for test-based lookup)
        patient_sex: Patient sex
        facility_id: Facility ID
    
    Returns:
        ReferenceRangeResult or None
    """
    # Try field-based reference range first (more specific)
    if field_code:
        result = get_field_reference_range(
            db=db,
            field_code=field_code,
            patient_age_days=patient_age_days,
            patient_sex=patient_sex,
            facility_id=facility_id
        )
        if result:
            return result
    
    # Fall back to test-level reference range
    if test_id or test_name:
        return get_test_reference_range(
            db=db,
            test_id=test_id,
            test_name=test_name,
            patient_age_years=patient_age_years,
            patient_sex=patient_sex
        )
    
    return None


# Age bracket constants for Ghana healthcare context
AGE_BRACKETS = {
    "NEWBORN": (0, 28),           # 0-28 days
    "INFANT": (29, 365),          # 1-12 months
    "TODDLER": (1, 3),            # 1-3 years
    "PRESCHOOL": (3, 5),          # 3-5 years
    "SCHOOL_AGE": (6, 12),        # 6-12 years
    "ADOLESCENT": (13, 18),       # 13-18 years
    "ADULT": (19, 60),            # 19-60 years
    "ELDERLY": (61, 150)          # 60+ years
}


def get_age_bracket(age_days: int) -> str:
    """Get the age bracket name for a given age in days"""
    age_years = age_days / 365.25
    
    if age_days <= 28:
        return "NEWBORN"
    elif age_days <= 365:
        return "INFANT"
    elif age_years < 3:
        return "TODDLER"
    elif age_years < 5:
        return "PRESCHOOL"
    elif age_years < 6:
        return "SCHOOL_AGE"
    elif age_years < 13:
        return "ADOLESCENT"
    elif age_years < 60:
        return "ADULT"
    else:
        return "ELDERLY"


def validate_test_applicability(
    test_category: str,
    patient_age_days: int,
    patient_sex: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate if a test is applicable for a patient based on age/sex.
    
    Returns dict with:
        - is_applicable: bool
        - warnings: list of warnings
        - age_bracket: str
    """
    age_bracket = get_age_bracket(patient_age_days)
    warnings = []
    
    # Some tests have age restrictions in Ghana
    restricted_tests = {
        "PSA": {"min_age": 40, "sex": "M"},
        "PREGNANCY_TEST": {"max_age": 60, "sex": "F"},
        "PROLACTIN": {"min_age": 18},
        "TESTOSTERONE": {"min_age": 18, "sex": "M"},
        "FOLLICLE_STIMULATING_HORMONE": {"min_age": 18},
        "LUTEINIZING_HORMONE": {"min_age": 18},
        "ESTRADIOL": {"min_age": 18},
        "PROGESTERONE": {"min_age": 18},
        "CORTISOL": {"min_age": 18},
        "THYROID_PROFILE": {"min_age": 0},  # Can be done at any age
    }
    
    test_upper = test_category.upper()
    
    if test_upper in restricted_tests:
        restrictions = restricted_tests[test_upper]
        
        # Check age
        if "min_age" in restrictions and patient_age_days < restrictions["min_age"] * 365:
            warnings.append(f"{test_category} typically not performed under {restrictions['min_age']} years")
        
        if "max_age" in restrictions and patient_age_days > restrictions["max_age"] * 365:
            warnings.append(f"{test_category} may not be appropriate for age > {restrictions['max_age']} years")
        
        # Check sex
        if "sex" in restrictions:
            if patient_sex and patient_sex.upper() != restrictions["sex"].upper():
                warnings.append(f"{test_category} is typically performed on {restrictions['sex']} patients")
    
    return {
        "is_applicable": len(warnings) == 0,
        "warnings": warnings,
        "age_bracket": age_bracket
    }
