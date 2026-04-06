"""
Urine R/E (Urinalysis) Validation Service

Extends the base lab validation with Urine R/E-specific:
- Clinical validation rules (UTI, Hematuria, Parasites)
- Gender-specific field handling (Sperm cells)
- Age-specific reference ranges (Pus cells)
- Critical finding flags

Usage:
    from app.services.urine_re_validation import validate_urine_re_result, get_clinical_flags
"""
from dataclasses import dataclass
from datetime import date
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal

from app.services.lab_result_validation import (
    ValidationResult, ValidationError, FlagInfo
)


# Clinical thresholds for Urine R/E
URINE_RE_CLINICAL_THRESHOLDS = {
    # Pus cells thresholds
    "pus_cells": {
        "adult_male": {"max": 5, "unit": "/µL"},
        "adult_female": {"max": 10, "unit": "/µL"},
        "child": {"max": 5, "unit": "/µL"},
        "adult_age_threshold_days": 6570  # 18 years
    },
    # RBC thresholds
    "rbc": {
        "normal_max": 2,
        "unit": "/µL"
    },
    # pH range
    "ph": {
        "low": 4.5,
        "high": 8.0
    },
    # Specific Gravity range
    "specific_gravity": {
        "low": 1.005,
        "high": 1.030
    }
}


# Normal/abnormal value mappings
URINE_RE_NORMAL_VALUES = {
    "color": ["Pale Yellow", "Straw", "Amber"],
    "appearance": ["Clear"],
    "protein": ["Negative", "Trace"],
    "glucose": ["Negative"],
    "ketone": ["Negative"],
    "blood": ["Negative"],
    "bilirubin": ["Negative"],
    "urobilinogen": ["Normal"],
    "nitrite": ["Negative"],
    "leucocytes": ["Negative"],
    "epithelial_cells": ["Few"],
    "yeast_cells": ["Not Seen"],
    "casts": ["Not Seen", "Hyaline"],
    "crystals": ["Not Seen"],
    "sperm_cells": ["Not Seen"],
    "bacteria": ["Not Seen"],
    "parasite": ["Not Seen"]
}


@dataclass
class UrineREClinicalFlag:
    """Clinical flag for Urine R/E results"""
    field_code: str
    flag_type: str  # UTI, HEMATURIA, PARASITE, CASTR, BACTERIURIA
    severity: str  # normal, warning, critical
    message: str
    value: Any
    reference: str


def determine_pus_cell_range(sex: str, age_days: Optional[int] = None) -> Tuple[int, int, str]:
    """
    Determine the reference range for pus cells based on age and gender.
    
    Returns:
        Tuple of (low, high, range_text)
    """
    thresholds = URINE_RE_CLINICAL_THRESHOLDS["pus_cells"]
    
    # If age is provided and patient is adult (18+ years)
    if age_days is not None and age_days >= thresholds["adult_age_threshold_days"]:
        if sex == "M" or sex == "Male":
            return (0, thresholds["adult_male"]["max"], f"0-{thresholds['adult_male']['max']} /µL")
        else:
            return (0, thresholds["adult_female"]["max"], f"0-{thresholds['adult_female']['max']} /µL")
    else:
        # Children or unknown age
        return (0, thresholds["child"]["max"], f"0-{thresholds['child']['max']} /µL")


def validate_urine_re_result(
    result_json: Dict[str, Any],
    patient_context: Optional[Dict[str, Any]] = None,
    schema_json: Optional[Dict[str, Any]] = None
) -> ValidationResult:
    """
    Validate Urine R/E results with clinical rules.
    
    Args:
        result_json: The urinalysis result data
        patient_context: Patient demographics (gender, date_of_birth)
        schema_json: Optional template schema
        
    Returns:
        ValidationResult with errors, flags, and clinical warnings
    """
    errors: List[ValidationError] = []
    flags: List[FlagInfo] = []
    warnings: List[str] = []
    clinical_flags: List[UrineREClinicalFlag] = []
    
    # Extract patient demographics
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
    
    # Normalize gender
    sex = None
    if patient_gender:
        if patient_gender.upper() in ["M", "MALE"]:
            sex = "M"
        elif patient_gender.upper() in ["F", "FEMALE"]:
            sex = "F"
    
    # =========================================================================
    # 1. Required Field Validation
    # =========================================================================
    required_fields = [
        "color", "appearance", "protein", "glucose", "ketone", "blood",
        "bilirubin", "urobilinogen", "nitrite", "leucocytes", "ph",
        "specific_gravity", "epithelial_cells", "pus_cells", "rbc",
        "yeast_cells", "casts", "crystals", "bacteria", "parasite"
    ]
    
    for field in required_fields:
        value = result_json.get(field)
        if value is None or value == "":
            errors.append(ValidationError(
                field_code=field,
                message=f"{field.replace('_', ' ').title()} is required"
            ))
    
    # =========================================================================
    # 2. Gender-specific Field Validation
    # =========================================================================
    # Sperm cells - only for males
    if sex == "F":
        # Disable/ignore sperm cells for females
        if result_json.get("sperm_cells"):
            # For females, this should be hidden or set to Not Seen
            warnings.append("Sperm cells field should not be visible for female patients")
    
    # =========================================================================
    # 3. Numeric Field Validation with Reference Ranges
    # =========================================================================
    
    # pH validation
    ph_value = result_json.get("ph")
    if ph_value is not None:
        try:
            ph_num = float(ph_value)
            ph_range = URINE_RE_CLINICAL_THRESHOLDS["ph"]
            if ph_num < ph_range["low"] or ph_num > ph_range["high"]:
                flags.append(FlagInfo(
                    field_code="ph",
                    flag="H" if ph_num > ph_range["high"] else "L",
                    value=ph_num,
                    low=ph_range["low"],
                    high=ph_range["high"],
                    text_range=f"{ph_range['low']} - {ph_range['high']}",
                    unit="pH"
                ))
                warnings.append(f"pH ({ph_num}) is outside normal range ({ph_range['low']}-{ph_range['high']})")
        except (ValueError, TypeError):
            errors.append(ValidationError(field_code="ph", message="pH must be a valid number"))
    
    # Specific Gravity validation
    sg_value = result_json.get("specific_gravity")
    if sg_value is not None:
        try:
            sg_num = float(sg_value)
            sg_range = URINE_RE_CLINICAL_THRESHOLDS["specific_gravity"]
            if sg_num < sg_range["low"] or sg_num > sg_range["high"]:
                flags.append(FlagInfo(
                    field_code="specific_gravity",
                    flag="H" if sg_num > sg_range["high"] else "L",
                    value=sg_num,
                    low=sg_range["low"],
                    high=sg_range["high"],
                    text_range=f"{sg_range['low']} - {sg_range['high']}",
                    unit="SG"
                ))
                warnings.append(f"Specific Gravity ({sg_num}) is outside normal range")
        except (ValueError, TypeError):
            errors.append(ValidationError(field_code="specific_gravity", message="Specific Gravity must be a valid number"))
    
    # =========================================================================
    # 4. Clinical Rule Validation
    # =========================================================================
    
    # Get key values
    nitrite = result_json.get("nitrite", "").lower()
    leucocytes = result_json.get("leucocytes", "").lower()
    rbc_value = result_json.get("rbc")
    pus_value = result_json.get("pus_cells")
    parasite = result_json.get("parasite", "").lower()
    casts = result_json.get("casts", "").lower()
    bacteria = result_json.get("bacteria", "").lower()
    
    # Rule 1: Possible UTI (Nitrite + Leucocytes)
    if nitrite == "positive" and leucocytes in ["+", "++", "+++"]:
        clinical_flags.append(UrineREClinicalFlag(
            field_code="nitrite",
            flag_type="UTI",
            severity="warning",
            message="Possible Urinary Tract Infection - Positive Nitrite with Leucocyturia",
            value=f"Nitrite: {nitrite}, Leucocytes: {leucocytes}",
            reference="Consider urine culture"
        ))
        warnings.append("CLINICAL: Possible UTI detected - Positive Nitrite with significant Leucocyturia")
    
    # Rule 2: Hematuria (RBC > reference)
    if rbc_value is not None:
        try:
            rbc_num = int(rbc_value)
            rbc_max = URINE_RE_CLINICAL_THRESHOLDS["rbc"]["normal_max"]
            if rbc_num > rbc_max:
                clinical_flags.append(UrineREClinicalFlag(
                    field_code="rbc",
                    flag_type="HEMATURIA",
                    severity="warning",
                    message=f"Hematuria detected - RBC ({rbc_num}) exceeds reference range ({rbc_max})",
                    value=rbc_num,
                    reference=f"0-{rbc_max} /µL"
                ))
                warnings.append(f"CLINICAL: Hematuria - RBC count ({rbc_num}) is above normal ({rbc_max})")
        except (ValueError, TypeError):
            pass
    
    # Rule 3: Pyuria (Pus cells elevated based on gender/age)
    if pus_value is not None:
        try:
            pus_num = int(pus_value)
            pus_low, pus_high, pus_text = determine_pus_cell_range(sex, age_days)
            if pus_num > pus_high:
                clinical_flags.append(UrineREClinicalFlag(
                    field_code="pus_cells",
                    flag_type="PYURIA",
                    severity="warning",
                    message=f"Pyuria detected - Pus cells ({pus_num}) exceeds reference range ({pus_text})",
                    value=pus_num,
                    reference=pus_text
                ))
                warnings.append(f"CLINICAL: Pyuria - Pus cells ({pus_num}) above reference ({pus_text})")
        except (ValueError, TypeError):
            pass
    
    # Rule 4: Critical Parasite
    if parasite != "not seen" and parasite != "":
        clinical_flags.append(UrineREClinicalFlag(
            field_code="parasite",
            flag_type="PARASITE",
            severity="critical",
            message=f"CRITICAL: Parasite detected - {parasite}",
            value=parasite,
            reference="Urgent clinical review required"
        ))
        warnings.append(f"CRITICAL: Parasite ({parasite}) detected - Requires immediate attention")
    
    # Rule 5: Pathological Casts
    if casts in ["rbc casts", "wbc casts", "granular"]:
        severity = "critical" if casts in ["rbc casts", "wbc casts"] else "warning"
        clinical_flags.append(UrineREClinicalFlag(
            field_code="casts",
            flag_type="CASTR",
            severity=severity,
            message=f"Pathological casts detected - {casts}",
            value=casts,
            reference="Renal involvement possible - clinical correlation required"
        ))
        warnings.append(f"CLINICAL: Pathological casts ({casts}) detected")
    
    # Rule 6: Significant Bacteriuria with UTI symptoms
    if bacteria in ["moderate", "many"] and nitrite == "positive":
        clinical_flags.append(UrineREClinicalFlag(
            field_code="bacteria",
            flag_type="BACTERIURIA",
            severity="warning",
            message="Probable UTI - Significant bacteriuria with positive nitrite",
            value=f"Bacteria: {bacteria}, Nitrite: {nitrite}",
            reference="Consider urine culture and sensitivity"
        ))
        warnings.append("CLINICAL: Probable UTI - Significant bacteriuria with positive nitrite")
    
    # =========================================================================
    # 5. Select Field Value Validation (Normal/Abnormal)
    # =========================================================================
    
    for field, normal_values in URINE_RE_NORMAL_VALUES.items():
        value = result_json.get(field)
        if value and value not in normal_values:
            flags.append(FlagInfo(
                field_code=field,
                flag="H",
                value=value,
                text_range=", ".join(normal_values)
            ))
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        flags=flags,
        warnings=warnings
    )


def get_clinical_flags(
    result_json: Dict[str, Any],
    patient_context: Optional[Dict[str, Any]] = None
) -> List[UrineREClinicalFlag]:
    """
    Get clinical flags for Urine R/E results.
    This is a simplified version that only returns clinical flags.
    
    Args:
        result_json: The urinalysis result data
        patient_context: Patient demographics
        
    Returns:
        List of UrineREClinicalFlag objects
    """
    # Extract demographics
    patient_gender = patient_context.get("gender") if patient_context else None
    patient_dob = patient_context.get("date_of_birth") if patient_context else None
    
    # Calculate age
    age_days = None
    if patient_dob:
        if isinstance(patient_dob, str):
            try:
                patient_dob = date.fromisoformat(patient_dob)
            except:
                patient_dob = None
        if patient_dob:
            age_days = (date.today() - patient_dob).days
    
    # Normalize gender
    sex = None
    if patient_gender:
        if patient_gender.upper() in ["M", "MALE"]:
            sex = "M"
        elif patient_gender.upper() in ["F", "FEMALE"]:
            sex = "F"
    
    clinical_flags: List[UrineREClinicalFlag] = []
    
    # Get key values
    nitrite = str(result_json.get("nitrite", "")).lower()
    leucocytes = str(result_json.get("leucocytes", "")).lower()
    rbc_value = result_json.get("rbc")
    pus_value = result_json.get("pus_cells")
    parasite = str(result_json.get("parasite", "")).lower()
    casts = str(result_json.get("casts", "")).lower()
    bacteria = str(result_json.get("bacteria", "")).lower()
    
    # UTI
    if nitrite == "positive" and leucocytes in ["+", "++", "+++"]:
        clinical_flags.append(UrineREClinicalFlag(
            field_code="nitrite",
            flag_type="UTI",
            severity="warning",
            message="Possible Urinary Tract Infection",
            value=f"Nitrite: {nitrite}, Leucocytes: {leucocytes}",
            reference="Consider urine culture"
        ))
    
    # Hematuria
    if rbc_value is not None:
        try:
            if int(rbc_value) > 2:
                clinical_flags.append(UrineREClinicalFlag(
                    field_code="rbc",
                    flag_type="HEMATURIA",
                    severity="warning",
                    message="Hematuria detected",
                    value=rbc_value,
                    reference="0-2 /µL"
                ))
        except (ValueError, TypeError):
            pass
    
    # Pyuria
    if pus_value is not None:
        try:
            pus_num = int(pus_value)
            _, pus_high, pus_text = determine_pus_cell_range(sex, age_days)
            if pus_num > pus_high:
                clinical_flags.append(UrineREClinicalFlag(
                    field_code="pus_cells",
                    flag_type="PYURIA",
                    severity="warning",
                    message="Pyuria detected",
                    value=pus_num,
                    reference=pus_text
                ))
        except (ValueError, TypeError):
            pass
    
    # Critical Parasite
    if parasite != "not seen" and parasite != "":
        clinical_flags.append(UrineREClinicalFlag(
            field_code="parasite",
            flag_type="PARASITE",
            severity="critical",
            message=f"CRITICAL: Parasite detected - {parasite}",
            value=parasite,
            reference="Urgent clinical review required"
        ))
    
    # Pathological Casts
    if casts in ["rbc casts", "wbc casts", "granular"]:
        severity = "critical" if casts in ["rbc casts", "wbc casts"] else "warning"
        clinical_flags.append(UrineREClinicalFlag(
            field_code="casts",
            flag_type="CASTR",
            severity=severity,
            message=f"Pathological casts - {casts}",
            value=casts,
            reference="Clinical correlation required"
        ))
    
    # Bacteriuria
    if bacteria in ["moderate", "many"] and nitrite == "positive":
        clinical_flags.append(UrineREClinicalFlag(
            field_code="bacteria",
            flag_type="BACTERIURIA",
            severity="warning",
            message="Significant bacteriuria with UTI symptoms",
            value=f"Bacteria: {bacteria}",
            reference="Consider culture"
        ))
    
    return clinical_flags


def format_urine_re_report(
    result_json: Dict[str, Any],
    patient_context: Optional[Dict[str, Any]] = None,
    include_reference: bool = True
) -> Dict[str, Any]:
    """
    Format Urine R/E results for NHIS-compliant report.
    
    Args:
        result_json: The urinalysis result data
        patient_context: Patient demographics
        include_reference: Whether to include reference ranges
        
    Returns:
        Formatted report dictionary
    """
    # Organize results by section
    report = {
        "test_name": "Urine R/E (Urinalysis)",
        "sections": {}
    }
    
    # A. Macroscopy
    macroscopy = {
        "title": "A. MACROSCOPY",
        "parameters": {}
    }
    for field in ["color", "appearance"]:
        value = result_json.get(field, "Not Done")
        ref = ", ".join(URINE_RE_NORMAL_VALUES.get(field, [])) if include_reference else None
        is_abnormal = value not in URINE_RE_NORMAL_VALUES.get(field, [])
        macroscopy["parameters"][field] = {
            "label": field.replace("_", " ").title(),
            "value": value,
            "reference": ref,
            "abnormal": is_abnormal
        }
    report["sections"]["macroscopy"] = macroscopy
    
    # B. Chemical Analysis
    chemical = {
        "title": "B. CHEMICAL ANALYSIS",
        "parameters": {}
    }
    chem_fields = ["protein", "glucose", "ketone", "blood", "bilirubin", 
                   "urobilinogen", "nitrite", "leucocytes", "ph", "specific_gravity"]
    for field in chem_fields:
        value = result_json.get(field, "Not Done")
        if field in ["ph", "specific_gravity"]:
            # Numeric fields
            if field == "ph":
                ref = "4.5 - 8.0" if include_reference else None
                try:
                    is_abnormal = float(value) < 4.5 or float(value) > 8.0
                except:
                    is_abnormal = False
            else:
                ref = "1.005 - 1.030" if include_reference else None
                try:
                    is_abnormal = float(value) < 1.005 or float(value) > 1.030
                except:
                    is_abnormal = False
        else:
            # Select fields
            ref = ", ".join(URINE_RE_NORMAL_VALUES.get(field, [])) if include_reference else None
            is_abnormal = value not in URINE_RE_NORMAL_VALUES.get(field, [])
        
        chemical["parameters"][field] = {
            "label": field.replace("_", " ").title(),
            "value": value,
            "reference": ref,
            "abnormal": is_abnormal
        }
    report["sections"]["chemical"] = chemical
    
    # C. Microscopy
    microscopy = {
        "title": "C. MICROSCOPY",
        "parameters": {}
    }
    micro_fields = ["epithelial_cells", "pus_cells", "rbc", "yeast_cells", 
                   "casts", "crystals", "sperm_cells", "bacteria", "parasite"]
    for field in micro_fields:
        value = result_json.get(field, "Not Done")
        
        # Skip sperm cells for females
        if field == "sperm_cells" and patient_context:
            gender = patient_context.get("gender", "").upper()
            if gender in ["F", "FEMALE"]:
                continue
        
        ref = ", ".join(URINE_RE_NORMAL_VALUES.get(field, [])) if include_reference else None
        is_abnormal = value not in URINE_RE_NORMAL_VALUES.get(field, [])
        
        microscopy["parameters"][field] = {
            "label": field.replace("_", " ").title(),
            "value": value,
            "reference": ref,
            "abnormal": is_abnormal
        }
    report["sections"]["microscopy"] = microscopy
    
    # Interpretation & Remarks
    interpretation = {
        "title": "INTERPRETATION & COMMENTS",
        "parameters": {}
    }
    for field in ["clinical_interpretation", "remarks"]:
        value = result_json.get(field)
        if value:
            interpretation["parameters"][field] = {
                "label": field.replace("_", " ").title(),
                "value": value
            }
    report["sections"]["interpretation"] = interpretation
    
    # Add clinical flags
    clinical_flags = get_clinical_flags(result_json, patient_context)
    if clinical_flags:
        report["clinical_flags"] = [
            {
                "type": flag.flag_type,
                "severity": flag.severity,
                "message": flag.message,
                "value": flag.value,
                "reference": flag.reference
            }
            for flag in clinical_flags
        ]
    
    return report
