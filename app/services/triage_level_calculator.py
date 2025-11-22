"""
Triage Level Calculation Service

This module provides functionality to automatically calculate triage levels
based on vital signs and patient presentation.
"""
from typing import Optional
from app.models.triage_models import TriageVitals


def calculate_triage_level_from_vitals(vitals: TriageVitals) -> tuple[Optional[str], Optional[str]]:
    """
    Automatically calculate triage level (P1/P2/P3) and category (Critical/Urgent/Routine)
    based on vital signs thresholds.
    
    Returns:
        Tuple of (triage_level, triage_category)
        - triage_level: "P1", "P2", or "P3" (or "Red", "Yellow", "Green")
        - triage_category: "Critical", "Urgent", or "Routine"
    """
    # Critical (P1/Red) - Immediate attention required
    if _is_critical(vitals):
        return ("P1", "Critical")
    
    # Urgent (P2/Yellow) - Needs prompt attention
    if _is_urgent(vitals):
        return ("P2", "Urgent")
    
    # Routine (P3/Green) - Standard care
    return ("P3", "Routine")


def _is_critical(vitals: TriageVitals) -> bool:
    """Check if vitals indicate critical condition (P1/Red)."""
    # Critical temperature thresholds
    if vitals.temperature:
        if vitals.temperature > 40.0 or vitals.temperature < 35.0:
            return True
    
    # Critical blood pressure (hypotension or severe hypertension)
    if vitals.systolic_bp:
        if vitals.systolic_bp < 80 or vitals.systolic_bp > 200:
            return True
    
    if vitals.diastolic_bp:
        if vitals.diastolic_bp > 120:
            return True
    
    # Critical heart rate (bradycardia or tachycardia)
    if vitals.pulse_rate:
        if vitals.pulse_rate < 40 or vitals.pulse_rate > 150:
            return True
    
    # Critical respiratory rate
    if vitals.respiratory_rate:
        if vitals.respiratory_rate < 8 or vitals.respiratory_rate > 30:
            return True
    
    # Critical oxygen saturation
    if vitals.oxygen_saturation:
        if vitals.oxygen_saturation < 90:
            return True
    
    # Severe pain
    if vitals.pain_scale:
        if vitals.pain_scale >= 9:
            return True
    
    return False


def _is_urgent(vitals: TriageVitals) -> bool:
    """Check if vitals indicate urgent condition (P2/Yellow)."""
    # Urgent temperature thresholds
    if vitals.temperature:
        if vitals.temperature > 39.0 or vitals.temperature < 35.5:
            return True
    
    # Urgent blood pressure
    if vitals.systolic_bp:
        if vitals.systolic_bp < 90 or vitals.systolic_bp > 180:
            return True
    
    if vitals.diastolic_bp:
        if vitals.diastolic_bp > 110:
            return True
    
    # Urgent heart rate
    if vitals.pulse_rate:
        if vitals.pulse_rate < 50 or vitals.pulse_rate > 120:
            return True
    
    # Urgent respiratory rate
    if vitals.respiratory_rate:
        if vitals.respiratory_rate < 10 or vitals.respiratory_rate > 25:
            return True
    
    # Urgent oxygen saturation
    if vitals.oxygen_saturation:
        if vitals.oxygen_saturation < 95:
            return True
    
    # Moderate to severe pain
    if vitals.pain_scale:
        if vitals.pain_scale >= 7:
            return True
    
    return False


def get_triage_level_priority(triage_level: Optional[str]) -> int:
    """
    Get numeric priority for queue ordering.
    Lower number = higher priority.
    """
    priority_map = {
        "P1": 1, "Red": 1,
        "P2": 2, "Yellow": 2,
        "P3": 3, "Green": 3,
    }
    return priority_map.get(triage_level, 4)  # Default to 4 (lowest priority)

