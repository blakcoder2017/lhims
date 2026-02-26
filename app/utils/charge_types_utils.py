"""
Utility functions for charge type management.
Provides a centralized way to get charge types from configuration or defaults.
"""

DEFAULT_CHARGE_TYPES = [
    "consultation",
    "lab_test",
    "radiology",
    "pharmacy",
    "procedure",
    "admission",
    "antenatal",
    "other"
]


def get_charge_types(db) -> list:
    """
    Get charge types from hospital settings or return defaults.
    
    This function checks if custom charge types are configured in hospital settings.
    If configured, it returns those. Otherwise, it returns the default charge types.
    
    Args:
        db: SQLAlchemy database session
        
    Returns:
        list: List of charge type strings
    """
    from app.models.hospital_settings_models import HospitalSettings
    
    settings = db.query(HospitalSettings).first()
    
    if settings and settings.charge_types_config:
        return settings.charge_types_config
    
    return DEFAULT_CHARGE_TYPES.copy()


def get_charge_type_display_name(charge_type: str) -> str:
    """
    Get a human-readable display name for a charge type.
    
    Args:
        charge_type: The charge type string (e.g., 'lab_test')
        
    Returns:
        str: Human-readable name (e.g., 'Lab Test')
    """
    return charge_type.replace('_', ' ').title()
