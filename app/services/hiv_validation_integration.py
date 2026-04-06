"""
HIV-Specific Validation Integration

This module integrates HIV test validation with the existing lab result validation service.
It adds HIV-specific validation rules and interpretation to the standard validation flow.

Author: LHIMS Lab Module
"""

from typing import Dict, Any, List, Optional, Callable
from app.services.lab_result_validation import ValidationResult, ValidationError
from app.services.hiv_result_interpretation import (
    HIVResultInterpreter,
    hiv_interpreter,
    interpret_hiv_results,
    validate_hiv_for_claim
)


# HIV-specific field codes
HIV_FIELD_FIRST_RESPONSE = "first_response"
HIV_FIELD_CONFIRMATION = "confirmation_result"
HIV_FIELD_BIO_LINE = "bio_line"
HIV_FIELD_ORAQUICK = "oraquick"
HIV_FIELD_DETERMINE = "determine"
HIV_FIELD_WONDFO = "wondfo"
HIV_FIELD_FINAL_INTERPRETATION = "final_interpretation"

HIV_RAPID_KIT_FIELDS = [
    HIV_FIELD_BIO_LINE,
    HIV_FIELD_ORAQUICK,
    HIV_FIELD_DETERMINE,
    HIV_FIELD_WONDFO
]


def is_hiv_template(schema_json: Dict[str, Any]) -> bool:
    """
    Check if the schema is for an HIV test.
    
    Args:
        schema_json: The template schema
        
    Returns:
        True if this is an HIV template
    """
    meta = schema_json.get("meta", {})
    name = meta.get("name", "").lower()
    discipline = meta.get("discipline", "").lower()
    nhis_code = meta.get("nhis_code", "")
    
    return (
        "hiv" in name or
        "hiv" in discipline or
        nhis_code == "HIV001" or
        HIV_FIELD_FIRST_RESPONSE in schema_json.get("fields", {})
    )


def validate_hiv_result(
    schema_json: Dict[str, Any],
    result_json: Dict[str, Any],
    patient_context: Optional[Dict[str, Any]] = None
) -> ValidationResult:
    """
    Validate HIV test results with specialized validation logic.
    
    This function extends the standard validation with HIV-specific rules:
    1. First Response validation
    2. Confirmation required when Reactive
    3. At least one rapid kit recorded
    4. Invalid result handling
    5. Final interpretation calculation
    
    Args:
        schema_json: The template schema
        result_json: The result data to validate
        patient_context: Optional patient info
        
    Returns:
        ValidationResult with HIV-specific validation
    """
    # First, run standard validation
    from app.services.lab_result_validation import validate_result
    base_result = validate_result(schema_json, result_json, patient_context)
    
    # Extract HIV-specific fields
    first_response = result_json.get(HIV_FIELD_FIRST_RESPONSE)
    confirmation_result = result_json.get(HIV_FIELD_CONFIRMATION)
    
    rapid_kits = {}
    for kit_field in HIV_RAPID_KIT_FIELDS:
        if kit_field in result_json:
            rapid_kits[kit_field] = result_json[kit_field]
    
    # Get HIV-specific validation
    hiv_validation = hiv_interpreter.validate_test(
        first_response=first_response,
        confirmation_result=confirmation_result,
        rapid_kits=rapid_kits
    )
    
    # Convert HIV validation errors to ValidationError format
    for error in hiv_validation.errors:
        base_result.errors.append(ValidationError(
            field_code="hiv_workflow",
            message=error
        ))
    
    # Add warnings
    for warning in hiv_validation.warnings:
        base_result.warnings.append(warning)
    
    # Update validity based on HIV validation
    if not hiv_validation.is_valid:
        base_result.is_valid = False
    
    # Calculate final interpretation
    if first_response:
        interpretation = hiv_interpreter.interpret_result(
            first_response=first_response,
            confirmation_result=confirmation_result,
            rapid_kits=rapid_kits
        )
        
        # Add interpretation to result if not present
        if HIV_FIELD_FINAL_INTERPRETATION not in result_json:
            result_json[HIV_FIELD_FINAL_INTERPRETATION] = interpretation.final_interpretation
        
        # Add warning if interpretation not finalized
        if not interpretation.is_final:
            base_result.warnings.append(
                f"Result not finalized: {interpretation.interpretation_note}"
            )
    
    return base_result


def get_hiv_claim_status(
    result_json: Dict[str, Any],
    specimen_date: Optional[str] = None,
    diagnosis: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get NHIS claim status for HIV test.
    
    Args:
        result_json: The result data
        specimen_date: Specimen collection date (ISO format string)
        diagnosis: Patient diagnosis
        
    Returns:
        Dictionary with claim readiness status
    """
    from datetime import datetime
    
    spec_date = None
    if specimen_date:
        try:
            spec_date = datetime.fromisoformat(specimen_date.replace("Z", "+00:00"))
        except:
            pass
    
    validation = validate_hiv_for_claim(
        results=result_json,
        specimen_date=spec_date,
        diagnosis=diagnosis
    )
    
    return {
        "can_submit_claim": validation.can_submit_claim,
        "result_finalized": validation.result_finalized,
        "is_valid": validation.is_valid,
        "errors": validation.errors,
        "warnings": validation.warnings,
        "required_for_claim": [
            "first_response (Retroscreening)",
            "final_interpretation",
            "specimen_date",
            "diagnosis"
        ],
        "missing_fields": [
            field for field in ["first_response", "final_interpretation", "specimen_date", "diagnosis"]
            if field not in result_json or not result_json.get(field)
        ]
    }


def format_hiv_report(
    result_json: Dict[str, Any],
    include_interpretation: bool = True
) -> Dict[str, Any]:
    """
    Format HIV test results for report display.
    
    Args:
        result_json: The result data
        include_interpretation: Whether to include auto-calculated interpretation
        
    Returns:
        Formatted report dictionary
    """
    report = {
        "test_name": "HIV 1 & 2 Screening",
        "nhis_code": "HIV001",
        "sections": []
    }
    
    # A. Retroscreening
    report["sections"].append({
        "title": "A. RETROSCREENING",
        "order": 1,
        "items": [
            {
                "label": "First Response",
                "code": HIV_FIELD_FIRST_RESPONSE,
                "value": result_json.get(HIV_FIELD_FIRST_RESPONSE, "Not recorded"),
                "reference": "Normal: Non-Reactive"
            }
        ]
    })
    
    # B. Confirmation Test
    confirmation_value = result_json.get(HIV_FIELD_CONFIRMATION)
    if confirmation_value or result_json.get(HIV_FIELD_FIRST_RESPONSE) == "Reactive":
        report["sections"].append({
            "title": "B. CONFIRMATION TEST",
            "order": 2,
            "items": [
                {
                    "label": "Confirmation Result",
                    "code": HIV_FIELD_CONFIRMATION,
                    "value": confirmation_value or "Pending",
                    "note": "Required if First Response is Reactive"
                }
            ]
        })
    
    # C. Rapid Test Kits
    kits = []
    kit_labels = {
        HIV_FIELD_BIO_LINE: "Bio Line",
        HIV_FIELD_ORAQUICK: "OraQuick",
        HIV_FIELD_DETERMINE: "Determine",
        HIV_FIELD_WONDFO: "Wondfo"
    }
    for kit_field, label in kit_labels.items():
        kits.append({
            "label": label,
            "code": kit_field,
            "value": result_json.get(kit_field, "Not recorded")
        })
    
    report["sections"].append({
        "title": "C. RAPID TEST KITS USED",
        "order": 3,
        "items": kits
    })
    
    # D. Final Interpretation
    if include_interpretation:
        interpretation = interpret_hiv_results(result_json)
        report["sections"].append({
            "title": "D. FINAL INTERPRETATION",
            "order": 4,
            "items": [
                {
                    "label": "Interpretation",
                    "code": HIV_FIELD_FINAL_INTERPRETATION,
                    "value": interpretation.get("interpretation", "Pending"),
                    "note": interpretation.get("note")
                }
            ],
            "flag": interpretation.get("flag"),
            "is_final": interpretation.get("is_final")
        })
    
    # Comments
    if result_json.get("comments"):
        report["sections"].append({
            "title": "E. COMMENTS",
            "order": 5,
            "items": [
                {
                    "label": "Comments",
                    "value": result_json.get("comments")
                }
            ]
        })
    
    # Set display order
    report["display_order"] = [
        "Retroscreening (First Response)",
        "Confirmation",
        "Rapid Test Kits Used",
        "Bio Line",
        "OraQuick",
        "Determine",
        "Wondfo",
        "Final Interpretation"
    ]
    
    return report


def export_hiv_results_csv(result_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Export HIV results in CSV-compatible format.
    
    Args:
        result_json: The result data
        
    Returns:
        List of dictionaries suitable for CSV export
    """
    interpretation = interpret_hiv_results(result_json)
    
    return [
        {
            "test_name": "HIV 1 & 2 Screening",
            "nhis_code": "HIV001",
            "field": "first_response",
            "label": "First Response (Retroscreening)",
            "value": result_json.get(HIV_FIELD_FIRST_RESPONSE, ""),
            "reference_range": "Non-Reactive = Normal"
        },
        {
            "test_name": "HIV 1 & 2 Screening",
            "nhis_code": "HIV001",
            "field": "confirmation_result",
            "label": "Confirmation Result",
            "value": result_json.get(HIV_FIELD_CONFIRMATION, ""),
            "reference_range": ""
        },
        {
            "test_name": "HIV 1 & 2 Screening",
            "nhis_code": "HIV001",
            "field": "bio_line",
            "label": "Bio Line",
            "value": result_json.get(HIV_FIELD_BIO_LINE, ""),
            "reference_range": ""
        },
        {
            "test_name": "HIV 1 & 2 Screening",
            "nhis_code": "HIV001",
            "field": "oraquick",
            "label": "OraQuick",
            "value": result_json.get(HIV_FIELD_ORAQUICK, ""),
            "reference_range": ""
        },
        {
            "test_name": "HIV 1 & 2 Screening",
            "nhis_code": "HIV001",
            "field": "determine",
            "label": "Determine",
            "value": result_json.get(HIV_FIELD_DETERMINE, ""),
            "reference_range": ""
        },
        {
            "test_name": "HIV 1 & 2 Screening",
            "nhis_code": "HIV001",
            "field": "wondfo",
            "label": "Wondfo",
            "value": result_json.get(HIV_FIELD_WONDFO, ""),
            "reference_range": ""
        },
        {
            "test_name": "HIV 1 & 2 Screening",
            "nhis_code": "HIV001",
            "field": "final_interpretation",
            "label": "Final Interpretation",
            "value": interpretation.get("interpretation", ""),
            "reference_range": ""
        },
        {
            "test_name": "HIV 1 & 2 Screening",
            "nhis_code": "HIV001",
            "field": "comments",
            "label": "Comments",
            "value": result_json.get("comments", ""),
            "reference_range": ""
        }
    ]


# Hook function to integrate with lab_result_validation
def hiv_validation_hook(
    schema_json: Dict[str, Any],
    result_json: Dict[str, Any],
    patient_context: Optional[Dict[str, Any]] = None
) -> ValidationResult:
    """
    Hook function to add HIV validation to the standard validation flow.
    
    This function can be registered with the lab result validation service
    to provide HIV-specific validation.
    
    Args:
        schema_json: The template schema
        result_json: The result data
        patient_context: Optional patient info
        
    Returns:
        ValidationResult with HIV-specific validation
    """
    if is_hiv_template(schema_json):
        return validate_hiv_result(schema_json, result_json, patient_context)
    return None  # Return None to indicate no HIV-specific handling
