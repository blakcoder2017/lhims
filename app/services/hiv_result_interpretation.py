"""
HIV 1 & 2 Screening Result Interpretation Service

Handles automated result interpretation and validation for HIV tests
following Ghana NHIS guidelines and national HIV testing algorithms.

Features:
- Auto-calculation of final interpretation based on screening and confirmation results
- Validation of test workflow (screening → confirmation when reactive)
- Rapid kit traceability
- NHIS claim validation
- Audit trail for result changes

Author: LHIMS Lab Module
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, Literal
from enum import Enum
from dataclasses import dataclass


class HIVScreeningResult(str, Enum):
    """HIV Screening (First Response) results"""
    REACTIVE = "Reactive"
    NON_REACTIVE = "Non-Reactive"
    INVALID = "Invalid"


class HIVConfirmationResult(str, Enum):
    """HIV Confirmation test results"""
    POSITIVE = "Positive"
    NEGATIVE = "Negative"
    INDETERMINATE = "Indeterminate"


class HIVFinalInterpretation(str, Enum):
    """Final HIV test interpretations"""
    NEGATIVE = "HIV 1 & 2: Negative"
    POSITIVE = "HIV 1 & 2: Positive"
    INDETERMINATE = "Indeterminate – Repeat testing recommended"


class RapidKitResult(str, Enum):
    """Rapid test kit results"""
    REACTIVE = "Reactive"
    NON_REACTIVE = "Non-Reactive"
    NOT_USED = "Not Used"


@dataclass
class HIVValidationResult:
    """Validation result for HIV test"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    can_submit_claim: bool
    result_finalized: bool


@dataclass
class HIVInterpretationResult:
    """Interpretation result for HIV test"""
    final_interpretation: str
    flag: str  # NORMAL, ABNORMAL, INVALID, PENDING
    requires_confirmation: bool
    is_final: bool
    interpretation_note: Optional[str] = None


class HIVResultInterpreter:
    """
    Interpreter for HIV 1 & 2 Screening results.
    
    Implements Ghana NHIS-compliant HIV testing algorithm:
    1. Screening (Retroscreening/First Response)
    2. Confirmation (if Reactive)
    3. Final Interpretation
    """
    
    # Field codes used in the template
    FIELD_FIRST_RESPONSE = "first_response"
    FIELD_CONFIRMATION = "confirmation_result"
    FIELD_BIO_LINE = "bio_line"
    FIELD_ORAQUICK = "oraquick"
    FIELD_DETERMINE = "determine"
    FIELD_WONDFO = "wondfo"
    FIELD_FINAL_INTERPRETATION = "final_interpretation"
    FIELD_COMMENTS = "comments"
    
    # Rapid kit field codes
    RAPID_KIT_FIELDS = [FIELD_BIO_LINE, FIELD_ORAQUICK, FIELD_DETERMINE, FIELD_WONDFO]
    
    def interpret_result(
        self,
        first_response: Optional[str] = None,
        confirmation_result: Optional[str] = None,
        rapid_kits: Optional[Dict[str, str]] = None
    ) -> HIVInterpretationResult:
        """
        Calculate final interpretation based on screening and confirmation results.
        
        Interpretation Logic:
        - Non-Reactive → HIV 1 & 2: Negative
        - Reactive + Positive → HIV 1 & 2: Positive
        - Reactive + Indeterminate → Indeterminate – Repeat testing recommended
        - Reactive + Negative → HIV 1 & 2: Positive (default, rare case)
        - Reactive + No confirmation → Requires confirmation (incomplete)
        - Invalid → Invalid – Repeat testing recommended
        """
        
        # Handle Invalid result
        if first_response == HIVScreeningResult.INVALID.value:
            return HIVInterpretationResult(
                final_interpretation=HIVFinalInterpretation.INDETERMINATE.value,
                flag="INVALID",
                requires_confirmation=False,
                is_final=False,
                interpretation_note="Invalid test result detected. Sample may be insufficient or test procedure error. Repeat testing recommended."
            )
        
        # Handle Non-Reactive (Negative)
        if first_response == HIVScreeningResult.NON_REACTIVE.value:
            return HIVInterpretationResult(
                final_interpretation=HIVFinalInterpretation.NEGATIVE.value,
                flag="NORMAL",
                requires_confirmation=False,
                is_final=True,
                interpretation_note="HIV 1 & 2: Negative. No further testing required based on screening result."
            )
        
        # Handle Reactive - requires confirmation
        if first_response == HIVScreeningResult.REACTIVE.value:
            # Check if confirmation is provided
            if confirmation_result is None:
                return HIVInterpretationResult(
                    final_interpretation="Pending Confirmation",
                    flag="PENDING",
                    requires_confirmation=True,
                    is_final=False,
                    interpretation_note="First Response is Reactive. Confirmation test is required before final interpretation."
                )
            
            # Confirmation is provided - determine final result
            if confirmation_result == HIVConfirmationResult.POSITIVE.value:
                return HIVInterpretationResult(
                    final_interpretation=HIVFinalInterpretation.POSITIVE.value,
                    flag="ABNORMAL",
                    requires_confirmation=False,
                    is_final=True,
                    interpretation_note="HIV 1 & 2: Positive. Confirmatory test is Positive. Client should be linked to HIV care and treatment services."
                )
            
            elif confirmation_result == HIVConfirmationResult.INDETERMINATE.value:
                return HIVInterpretationResult(
                    final_interpretation=HIVFinalInterpretation.INDETERMINATE.value,
                    flag="INDETERMINATE",
                    requires_confirmation=False,
                    is_final=True,
                    interpretation_note="Indeterminate – Repeat testing recommended. New sample should be collected and testing repeated after 2 weeks."
                )
            
            elif confirmation_result == HIVConfirmationResult.NEGATIVE.value:
                # Rare case - treat as positive per Ghana algorithm
                return HIVInterpretationResult(
                    final_interpretation=HIVFinalInterpretation.POSITIVE.value,
                    flag="ABNORMAL",
                    requires_confirmation=False,
                    is_final=True,
                    interpretation_note="HIV 1 & 2: Positive. Despite negative confirmation, screening was reactive. Recommend repeat testing and counseling."
                )
        
        # Default - incomplete result
        return HIVInterpretationResult(
            final_interpretation="Result Pending",
            flag="PENDING",
            requires_confirmation=False,
            is_final=False,
            interpretation_note="Incomplete result. First Response is required."
        )
    
    def validate_test(
        self,
        first_response: Optional[str] = None,
        confirmation_result: Optional[str] = None,
        rapid_kits: Optional[Dict[str, str]] = None,
        specimen_date: Optional[datetime] = None,
        diagnosis: Optional[str] = None
    ) -> HIVValidationResult:
        """
        Validate HIV test results for completeness and NHIS compliance.
        
        Validation Rules:
        1. First Response is required
        2. Confirmation required if First Response = Reactive
        3. At least one rapid kit must be recorded
        4. Invalid results flagged for repeat
        5. Claim requires finalized result
        """
        
        errors = []
        warnings = []
        
        # Rule 1: First Response required
        if first_response is None:
            errors.append("First Response (Retroscreening) is required")
        
        # Rule 2: Confirmation required if Reactive
        if first_response == HIVScreeningResult.REACTIVE.value:
            if confirmation_result is None:
                errors.append("Confirmation result is required when First Response is Reactive")
        
        # Rule 3: At least one rapid kit must be recorded
        if rapid_kits:
            kits_recorded = sum(
                1 for kit_result in rapid_kits.values() 
                if kit_result and kit_result != RapidKitResult.NOT_USED.value
            )
            if kits_recorded == 0:
                warnings.append("No rapid test kit results recorded. At least one kit should be documented for traceability.")
        
        # Rule 4: Invalid result handling
        if first_response == HIVScreeningResult.INVALID.value:
            warnings.append("Invalid test result detected. Repeat testing is required.")
        
        # Rule 5: NHIS claim requirements
        can_submit_claim = True
        if not first_response:
            can_submit_claim = False
        
        # Check if result is finalized
        result_finalized = first_response is not None
        
        if first_response == HIVScreeningResult.REACTIVE.value and confirmation_result is None:
            result_finalized = False
            can_submit_claim = False
            errors.append("Cannot submit claim - confirmation test pending")
        
        return HIVValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            can_submit_claim=can_submit_claim,
            result_finalized=result_finalized
        )
    
    def calculate_final_interpretation(self, results: Dict[str, Any]) -> str:
        """
        Calculate final interpretation from raw results dictionary.
        
        Args:
            results: Dictionary containing test results with field codes
            
        Returns:
            Final interpretation string
        """
        first_response = results.get(self.FIELD_FIRST_RESPONSE)
        confirmation_result = results.get(self.FIELD_CONFIRMATION)
        
        # Extract rapid kit results
        rapid_kits = {}
        for kit_field in self.RAPID_KIT_FIELDS:
            if kit_field in results:
                rapid_kits[kit_field] = results[kit_field]
        
        # Get interpretation
        interpretation = self.interpret_result(
            first_response=first_response,
            confirmation_result=confirmation_result,
            rapid_kits=rapid_kits
        )
        
        return interpretation.final_interpretation
    
    def generate_interpretation_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive interpretation report.
        
        Args:
            results: Dictionary containing all test results
            
        Returns:
            Dictionary with interpretation, validation, and claim readiness
        """
        first_response = results.get(self.FIELD_FIRST_RESPONSE)
        confirmation_result = results.get(self.FIELD_CONFIRMATION)
        
        rapid_kits = {}
        for kit_field in self.RAPID_KIT_FIELDS:
            if kit_field in results:
                rapid_kits[kit_field] = results[kit_field]
        
        # Get interpretation
        interpretation = self.interpret_result(
            first_response=first_response,
            confirmation_result=confirmation_result,
            rapid_kits=rapid_kits
        )
        
        # Get validation
        validation = self.validate_test(
            first_response=first_response,
            confirmation_result=confirmation_result,
            rapid_kits=rapid_kits
        )
        
        # Build report sections for display
        report_sections = []
        
        # A. Retroscreening
        report_sections.append({
            "title": "A. RETROSCREENING (First Response)",
            "fields": [
                {"label": "First Response", "value": first_response or "Not recorded"}
            ]
        })
        
        # B. Confirmation (if applicable)
        if first_response == HIVScreeningResult.REACTIVE.value:
            report_sections.append({
                "title": "B. CONFIRMATION TEST",
                "fields": [
                    {"label": "Confirmation Result", "value": confirmation_result or "Pending"}
                ]
            })
        
        # C. Rapid Test Kits
        kit_fields = []
        kit_labels = {
            self.FIELD_BIO_LINE: "Bio Line",
            self.FIELD_ORAQUICK: "OraQuick",
            self.FIELD_DETERMINE: "Determine",
            self.FIELD_WONDFO: "Wondfo"
        }
        for kit_field, label in kit_labels.items():
            kit_fields.append({
                "label": label,
                "value": rapid_kits.get(kit_field, "Not recorded")
            })
        
        report_sections.append({
            "title": "C. RAPID TEST KITS USED",
            "fields": kit_fields
        })
        
        # D. Final Interpretation
        report_sections.append({
            "title": "D. FINAL INTERPRETATION",
            "fields": [
                {"label": "Interpretation", "value": interpretation.final_interpretation},
                {"label": "Status", "value": "Final" if interpretation.is_final else "Pending"}
            ],
            "note": interpretation.interpretation_note
        })
        
        return {
            "test_name": "HIV 1 & 2 Screening",
            "nhis_code": "HIV001",
            "interpretation": interpretation.final_interpretation,
            "flag": interpretation.flag,
            "is_final": interpretation.is_final,
            "note": interpretation.interpretation_note,
            "validation": {
                "is_valid": validation.is_valid,
                "errors": validation.errors,
                "warnings": validation.warnings,
                "can_submit_claim": validation.can_submit_claim,
                "result_finalized": validation.result_finalized
            },
            "report_sections": report_sections,
            "display_order": [
                "Retroscreening (First Response)",
                "Confirmation",
                "Rapid Test Kits Used",
                "Bio Line",
                "OraQuick",
                "Determine",
                "Wondfo"
            ]
        }


# Singleton instance for use across the application
hiv_interpreter = HIVResultInterpreter()


def interpret_hiv_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to interpret HIV test results.
    
    Args:
        results: Dictionary containing test results
        
    Returns:
        Interpretation report dictionary
    """
    return hiv_interpreter.generate_interpretation_report(results)


def validate_hiv_for_claim(
    results: Dict[str, Any],
    specimen_date: Optional[datetime] = None,
    diagnosis: Optional[str] = None
) -> HIVValidationResult:
    """
    Validate HIV test results for NHIS claim submission.
    
    Args:
        results: Dictionary containing test results
        specimen_date: Date specimen was collected
        diagnosis: Patient diagnosis
        
    Returns:
        Validation result
    """
    first_response = results.get(hiv_interpreter.FIELD_FIRST_RESPONSE)
    confirmation_result = results.get(hiv_interpreter.FIELD_CONFIRMATION)
    
    rapid_kits = {}
    for kit_field in hiv_interpreter.RAPID_KIT_FIELDS:
        if kit_field in results:
            rapid_kits[kit_field] = results[kit_field]
    
    return hiv_interpreter.validate_test(
        first_response=first_response,
        confirmation_result=confirmation_result,
        rapid_kits=rapid_kits,
        specimen_date=specimen_date,
        diagnosis=diagnosis
    )
