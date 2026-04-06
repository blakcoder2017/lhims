"""
Hepatitis B Viral Profile Result Interpretation Service

Handles automated result interpretation and validation for Hepatitis B tests
following Ghana NHIS guidelines and standard clinical virology practices.

Features:
- Auto-calculation of clinical interpretation based on HBV marker patterns
- Pattern recognition for different phases of HBV infection
- Validation of complete panel results
- NHIS claim readiness verification
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


class HepBPattern(str, Enum):
    """Hepatitis B serological patterns"""
    ACUTE_INFECTION = "acute_infection"
    CHRONIC_HIGH_REPLICATION = "chronic_high_replication"
    CHRONIC_LOW_REPLICATION = "chronic_low_replication"
    RESOLVED_INFECTION = "resolved_infection"
    VACCINE_IMMUNITY = "vaccine_immunity"
    PREVIOUS_EXPOSURE = "previous_exposure"
    ISOLATED_CORE = "isolated_core"
    NEGATIVE = "negative"
    INCOMPLETE = "incomplete"


class HepBFinalInterpretation(str, Enum):
    """Final HBV test interpretations"""
    ACUTE_HBV = "Acute HBV Infection (HBsAg+, HBeAg+)"
    CHRONIC_HBV_HIGH = "Chronic HBV Infection - High Replication (HBsAg+, HBeAg+)"
    CHRONIC_HBV_LOW = "Chronic HBV Infection - Low Replication (HBsAg+, HBeAb+)"
    RESOLVED_HBV = "Resolved HBV Infection (HBsAg-, HBsAb+, HBcAb+)"
    VACCINE_IMMUNITY = "Immunity due to vaccination (HBsAg-, HBsAb+, HBcAb-)"
    PREVIOUS_EXPOSURE = "Previous HBV Exposure (HBsAg-, HBcAb+, HBsAb-/+)"
    ISOLATED_CORE = "Isolated Core Antibody (HBcAb+ only) - Possible false positive or occult infection"
    NEGATIVE = "No evidence of HBV infection"
    INCOMPLETE = "Incomplete/Indeterminate - Repeat testing recommended"


@dataclass
class HepBInterpretationResult:
    """Interpretation result for Hepatitis B test"""
    final_interpretation: str
    pattern: str
    flag: str  # NORMAL, ABNORMAL, PENDING
    is_final: bool
    interpretation_note: Optional[str] = None
    recommendation: Optional[str] = None
    is_claim_ready: bool = False


class HepatitisBResultInterpreter:
    """
    Interpreter for Hepatitis B Viral Profile results.
    
    Handles pattern recognition and clinical interpretation based on
    the five main HBV serological markers.
    """
    
    FIELD_HBSAG = "hbsag"
    FIELD_HBSAB = "hbsab"
    FIELD_HBEAG = "hbeag"
    FIELD_HBEAB = "hbeab"
    FIELD_HBCAB = "hbcab"
    
    VALUE_REACTIVE = "Reactive"
    VALUE_NON_REACTIVE = "Non-Reactive"
    
    def __init__(self):
        """Initialize the interpreter with pattern definitions"""
        self.patterns = {
            HepBPattern.ACUTE_INFECTION: {
                "hbsag": self.VALUE_REACTIVE,
                "hbeag": self.VALUE_REACTIVE,
                "hbcab": self.VALUE_REACTIVE,
                "description": "Acute HBV Infection - High viral replication"
            },
            HepBPattern.CHRONIC_HIGH_REPLICATION: {
                "hbsag": self.VALUE_REACTIVE,
                "hbcab": self.VALUE_REACTIVE,
                "hbeag": self.VALUE_REACTIVE,
                "hbeab": self.VALUE_NON_REACTIVE,
                "description": "Chronic HBV Infection - High replication (HBeAg positive)"
            },
            HepBPattern.CHRONIC_LOW_REPLICATION: {
                "hbsag": self.VALUE_REACTIVE,
                "hbcab": self.VALUE_REACTIVE,
                "hbeab": self.VALUE_REACTIVE,
                "hbeag": self.VALUE_NON_REACTIVE,
                "description": "Chronic HBV Infection - Low replication (HBeAb positive)"
            },
            HepBPattern.RESOLVED_INFECTION: {
                "hbsag": self.VALUE_NON_REACTIVE,
                "hbsab": self.VALUE_REACTIVE,
                "hbcab": self.VALUE_REACTIVE,
                "description": "Resolved HBV infection with immunity"
            },
            HepBPattern.VACCINE_IMMUNITY: {
                "hbsag": self.VALUE_NON_REACTIVE,
                "hbsab": self.VALUE_REACTIVE,
                "hbcab": self.VALUE_NON_REACTIVE,
                "description": "Immunity due to vaccination"
            },
            HepBPattern.PREVIOUS_EXPOSURE: {
                "hbsag": self.VALUE_NON_REACTIVE,
                "hbcab": self.VALUE_REACTIVE,
                "description": "Previous HBV exposure"
            },
            HepBPattern.ISOLATED_CORE: {
                "hbsag": self.VALUE_NON_REACTIVE,
                "hbcab": self.VALUE_REACTIVE,
                "description": "Isolated anti-HBc - requires follow up"
            },
            HepBPattern.NEGATIVE: {
                "hbsag": self.VALUE_NON_REACTIVE,
                "hbsab": self.VALUE_NON_REACTIVE,
                "hbcab": self.VALUE_NON_REACTIVE,
                "description": "No evidence of HBV infection"
            }
        }
    
    def _normalize_value(self, value: Any) -> str:
        """Normalize result value for comparison"""
        if value is None:
            return ""
        return str(value).strip()
    
    def _matches_pattern(self, results: Dict[str, Any], pattern: Dict[str, str]) -> bool:
        """Check if results match a specific pattern"""
        for field, expected in pattern.items():
            actual = self._normalize_value(results.get(field))
            expected_normalized = self._normalize_value(expected)
            if actual != expected_normalized:
                return False
        return True
    
    def _identify_pattern(self, results: Dict[str, Any]) -> HepBPattern:
        """
        Identify the HBV serological pattern from results.
        
        Pattern priority (most specific first):
        1. Acute infection
        2. Chronic high replication
        3. Chronic low replication
        4. Resolved infection
        5. Vaccine immunity
        6. Previous exposure
        7. Isolated core
        8. Negative
        9. Incomplete
        """
        # Check if all required fields are present
        required_fields = [self.FIELD_HBSAG, self.FIELD_HBCAB]
        missing_fields = [f for f in required_fields if not results.get(f)]
        
        if missing_fields:
            return HepBPattern.INCOMPLETE
        
        hbsag = self._normalize_value(results.get(self.FIELD_HBSAG))
        hbsab = self._normalize_value(results.get(self.FIELD_HBSAB))
        hbeag = self._normalize_value(results.get(self.FIELD_HBEAG))
        hbeab = self._normalize_value(results.get(self.FIELD_HBEAB))
        hbcab = self._normalize_value(results.get(self.FIELD_HBCAB))
        
        # Acute infection: HBsAg+, HBeAg+, HBcAb+
        if hbsag == self.VALUE_REACTIVE and hbeag == self.VALUE_REACTIVE and hbcab == self.VALUE_REACTIVE:
            return HepBPattern.ACUTE_INFECTION
        
        # Chronic high replication: HBsAg+, HBcAb+, HBeAg+, HBeAb-
        if hbsag == self.VALUE_REACTIVE and hbcab == self.VALUE_REACTIVE and hbeag == self.VALUE_REACTIVE and hbeab == self.VALUE_NON_REACTIVE:
            return HepBPattern.CHRONIC_HIGH_REPLICATION
        
        # Chronic low replication: HBsAg+, HBcAb+, HBeAb+, HBeAg-
        if hbsag == self.VALUE_REACTIVE and hbcab == self.VALUE_REACTIVE and hbeab == self.VALUE_REACTIVE and hbeag == self.VALUE_NON_REACTIVE:
            return HepBPattern.CHRONIC_LOW_REPLICATION
        
        # Resolved infection: HBsAg-, HBsAb+, HBcAb+
        if hbsag == self.VALUE_NON_REACTIVE and hbsab == self.VALUE_REACTIVE and hbcab == self.VALUE_REACTIVE:
            return HepBPattern.RESOLVED_INFECTION
        
        # Vaccine immunity: HBsAg-, HBsAb+, HBcAb-
        if hbsag == self.VALUE_NON_REACTIVE and hbsab == self.VALUE_REACTIVE and hbcab == self.VALUE_NON_REACTIVE:
            return HepBPattern.VACCINE_IMMUNITY
        
        # Previous exposure: HBsAg-, HBcAb+, (HBsAb may be + or -)
        if hbsag == self.VALUE_NON_REACTIVE and hbcab == self.VALUE_REACTIVE:
            return HepBPattern.PREVIOUS_EXPOSURE
        
        # Isolated core: This is covered by previous_exposure when HBsAb is Non-Reactive
        # But we'll handle it explicitly
        
        # Negative: All markers negative
        if hbsag == self.VALUE_NON_REACTIVE and hbsab == self.VALUE_NON_REACTIVE and hbcab == self.VALUE_NON_REACTIVE:
            return HepBPattern.NEGATIVE
        
        # Default to incomplete if nothing matches
        return HepBPattern.INCOMPLETE
    
    def _get_interpretation(self, pattern: HepBPattern) -> tuple[str, str, str, str]:
        """Get interpretation details for a pattern"""
        interpretations = {
            HepBPattern.ACUTE_INFECTION: (
                HepBFinalInterpretation.ACUTE_HBV.value,
                "ABNORMAL",
                "High viral replication - patient is highly infectious. Acute HBV infection confirmed.",
                "Notify clinician immediately. Consider transmission prevention measures. Monitor liver function."
            ),
            HepBPattern.CHRONIC_HIGH_REPLICATION: (
                HepBFinalInterpretation.CHRONIC_HBV_HIGH.value,
                "ABNORMAL",
                "Chronic HBV infection with active viral replication (HBeAg positive).",
                "Refer for HBV DNA viral load and liver function tests. Consider antiviral therapy evaluation."
            ),
            HepBPattern.CHRONIC_LOW_REPLICATION: (
                HepBFinalInterpretation.CHRONIC_HBV_LOW.value,
                "ABNORMAL",
                "Chronic HBV infection with lower viral activity (HBeAg negative chronic hepatitis).",
                "Monitor regularly. Consider antiviral therapy based on clinical assessment and HBV DNA levels."
            ),
            HepBPattern.RESOLVED_INFECTION: (
                HepBFinalInterpretation.RESOLVED_HBV.value,
                "NORMAL",
                "Past HBV infection with recovery and immunity. Patient is not infectious.",
                "Patient is immune. No specific treatment needed. No vaccination required."
            ),
            HepBPattern.VACCINE_IMMUNITY: (
                HepBFinalInterpretation.VACCINE_IMMUNITY.value,
                "NORMAL",
                "Protective immunity from successful vaccination.",
                "Patient is immune. No vaccination needed."
            ),
            HepBPattern.PREVIOUS_EXPOSURE: (
                HepBFinalInterpretation.PREVIOUS_EXPOSURE.value,
                "NORMAL",
                "Past exposure to HBV. May indicate resolved infection or occult HBV.",
                "Consider HBV DNA testing to rule out occult infection, especially if immunocompromised."
            ),
            HepBPattern.ISOLATED_CORE: (
                HepBFinalInterpretation.ISOLATED_CORE.value,
                "PENDING",
                "Isolated anti-HBc detected. Possible false positive, window period, or occult infection.",
                "Repeat testing. Consider HBV DNA. Evaluate for false positive result."
            ),
            HepBPattern.NEGATIVE: (
                HepBFinalInterpretation.NEGATIVE.value,
                "NORMAL",
                "No serological evidence of HBV infection.",
                "Patient is susceptible to HBV infection. Consider vaccination if at risk."
            ),
            HepBPattern.INCOMPLETE: (
                HepBFinalInterpretation.INCOMPLETE.value,
                "PENDING",
                "Incomplete results. Cannot provide final interpretation.",
                "Complete all required markers before finalizing report."
            )
        }
        
        return interpretations.get(pattern, (
            HepBFinalInterpretation.INCOMPLETE.value,
            "PENDING",
            "Unable to determine interpretation.",
            "Review results and repeat testing if necessary."
        ))
    
    def interpret_result(
        self,
        hbsag: Optional[str] = None,
        hbsab: Optional[str] = None,
        hbeag: Optional[str] = None,
        hbeab: Optional[str] = None,
        hbcab: Optional[str] = None
    ) -> HepBInterpretationResult:
        """
        Calculate clinical interpretation based on HBV marker results.
        
        Args:
            hbsag: HBsAg result (Reactive/Non-Reactive)
            hbsab: HBsAb result (Reactive/Non-Reactive)
            hbeag: HBeAg result (Reactive/Non-Reactive)
            hbeab: HBeAb result (Reactive/Non-Reactive)
            hbcab: HBcAb result (Reactive/Non-Reactive)
        
        Returns:
            HepBInterpretationResult with interpretation and flag
        """
        results = {
            self.FIELD_HBSAG: hbsag,
            self.FIELD_HBSAB: hbsab,
            self.FIELD_HBEAG: hbeag,
            self.FIELD_HBEAB: hbeab,
            self.FIELD_HBCAB: hbcab
        }
        
        pattern = self._identify_pattern(results)
        interpretation, flag, note, recommendation = self._get_interpretation(pattern)
        
        # Determine if result is final
        is_final = pattern != HepBPattern.INCOMPLETE
        
        # Determine claim readiness
        is_claim_ready = is_final and all([
            hbsag, hbsab, hbeag, hbeab, hbcab
        ])
        
        return HepBInterpretationResult(
            final_interpretation=interpretation,
            pattern=pattern.value,
            flag=flag,
            is_final=is_final,
            interpretation_note=note,
            recommendation=recommendation,
            is_claim_ready=is_claim_ready
        )
    
    def calculate_final_interpretation(self, results: Dict[str, Any]) -> str:
        """
        Calculate final interpretation from raw results dictionary.
        
        Args:
            results: Dictionary with HBV marker results
        
        Returns:
            Final interpretation string
        """
        interpretation = self.interpret_result(
            hbsag=results.get(self.FIELD_HBSAG),
            hbsab=results.get(self.FIELD_HBSAB),
            hbeag=results.get(self.FIELD_HBEAG),
            hbeab=results.get(self.FIELD_HBEAB),
            hbcab=results.get(self.FIELD_HBCAB)
        )
        
        return interpretation.final_interpretation
    
    def generate_interpretation_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive interpretation report.
        
        Args:
            results: Dictionary with HBV marker results
        
        Returns:
            Dictionary with interpretation, validation, and claim readiness
        """
        interpretation = self.interpret_result(
            hbsag=results.get(self.FIELD_HBSAG),
            hbsab=results.get(self.FIELD_HBSAB),
            hbeag=results.get(self.FIELD_HBEAG),
            hbeab=results.get(self.FIELD_HBEAB),
            hbcab=results.get(self.FIELD_HBCAB)
        )
        
        # Validate required fields
        required_fields = [
            self.FIELD_HBSAG,
            self.FIELD_HBSAB,
            self.FIELD_HBEAG,
            self.FIELD_HBEAB,
            self.FIELD_HBCAB
        ]
        
        missing_fields = [f for f in required_fields if not results.get(f)]
        
        # Build report
        report = {
            "test_name": "Hepatitis B Viral Profile",
            "nhis_code": "HEP_B_PROF",
            "interpretation": interpretation.final_interpretation,
            "pattern": interpretation.pattern,
            "flag": interpretation.flag,
            "is_final": interpretation.is_final,
            "note": interpretation.interpretation_note,
            "recommendation": interpretation.recommendation,
            "validation": {
                "is_complete": len(missing_fields) == 0,
                "missing_fields": missing_fields,
                "all_markers_recorded": all([results.get(f) for f in required_fields])
            },
            "claim_readiness": {
                "is_ready": interpretation.is_claim_ready,
                "can_claim": interpretation.is_final and len(missing_fields) == 0,
                "reason": "All markers complete and interpreted" if interpretation.is_claim_ready else "Incomplete results"
            },
            "markers": {
                "hbsag": {
                    "result": results.get(self.FIELD_HBSAG),
                    "label": "HBsAg (Hepatitis B Surface Antigen)"
                },
                "hbsab": {
                    "result": results.get(self.FIELD_HBSAB),
                    "label": "HBsAb (Hepatitis B Surface Antibody)"
                },
                "hbeag": {
                    "result": results.get(self.FIELD_HBEAG),
                    "label": "HBeAg (Hepatitis B e Antigen)"
                },
                "hbeab": {
                    "result": results.get(self.FIELD_HBEAB),
                    "label": "HBeAb (Anti-HBe)"
                },
                "hbcab": {
                    "result": results.get(self.FIELD_HBCAB),
                    "label": "HBcAb (Anti-HBc)"
                }
            }
        }
        
        return report
    
    def validate_for_claim(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate results are ready for NHIS claim submission.
        
        Args:
            results: Dictionary with HBV marker results
        
        Returns:
            Validation result with claim readiness status
        """
        interpretation = self.interpret_result(
            hbsag=results.get(self.FIELD_HBSAG),
            hbsab=results.get(self.FIELD_HBSAB),
            hbeag=results.get(self.FIELD_HBEAG),
            hbeab=results.get(self.FIELD_HBEAB),
            hbcab=results.get(self.FIELD_HBCAB)
        )
        
        required_fields = [
            self.FIELD_HBSAG,
            self.FIELD_HBSAB,
            self.FIELD_HBEAG,
            self.FIELD_HBEAB,
            self.FIELD_HBCAB
        ]
        
        missing_fields = [f for f in required_fields if not results.get(f)]
        
        return {
            "can_submit_claim": interpretation.is_claim_ready,
            "is_finalized": interpretation.is_final,
            "missing_required_fields": missing_fields,
            "validation_errors": [
                f"Missing required field: {field}" for field in missing_fields
            ] if missing_fields else [],
            "block_reason": None if interpretation.is_claim_ready else (
                "Result not finalized" if not interpretation.is_final else 
                "Required fields are empty" if missing_fields else "Unknown"
            )
        }


# Singleton instance for reuse
_hep_b_interpreter: Optional[HepatitisBResultInterpreter] = None


def get_hep_b_interpreter() -> HepatitisBResultInterpreter:
    """Get singleton instance of Hepatitis B interpreter"""
    global _hep_b_interpreter
    if _hep_b_interpreter is None:
        _hep_b_interpreter = HepatitisBResultInterpreter()
    return _hep_b_interpreter


def interpret_hep_b_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to interpret Hepatitis B results.
    
    Args:
        results: Dictionary with HBV marker results
    
    Returns:
        Interpretation report dictionary
    """
    return get_hep_b_interpreter().generate_interpretation_report(results)


def validate_hep_b_claim_readiness(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to validate NHIS claim readiness.
    
    Args:
        results: Dictionary with HBV marker results
    
    Returns:
        Validation result dictionary
    """
    return get_hep_b_interpreter().validate_for_claim(results)
