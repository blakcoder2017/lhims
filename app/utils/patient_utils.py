"""
Patient Utility Functions

Utility functions for patient-related calculations.
"""
from datetime import date
from typing import Optional


def calculate_age(date_of_birth: date, reference_date: Optional[date] = None) -> dict:
    """
    Calculate age from date of birth.
    
    Args:
        date_of_birth: Patient's date of birth
        reference_date: Reference date (defaults to today)
        
    Returns:
        Dictionary with 'years', 'months', 'days', and 'display' keys
    """
    if reference_date is None:
        reference_date = date.today()
    
    # Calculate age
    years = reference_date.year - date_of_birth.year
    months = reference_date.month - date_of_birth.month
    days = reference_date.day - date_of_birth.day
    
    # Adjust for negative days/months
    if days < 0:
        months -= 1
        # Get days in previous month
        if reference_date.month == 1:
            prev_month_days = 31  # December has 31 days
        else:
            from calendar import monthrange
            prev_month_days = monthrange(reference_date.year, reference_date.month - 1)[1]
        days += prev_month_days
    
    if months < 0:
        years -= 1
        months += 12
    
    # Create display string
    if years > 0:
        if months > 0:
            display = f"{years} year{'s' if years != 1 else ''}, {months} month{'s' if months != 1 else ''}"
        else:
            display = f"{years} year{'s' if years != 1 else ''}"
    elif months > 0:
        display = f"{months} month{'s' if months != 1 else ''}"
    else:
        display = f"{days} day{'s' if days != 1 else ''}"
    
    return {
        "years": years,
        "months": months,
        "days": days,
        "display": display,
        "age_in_years": years + (months / 12.0) + (days / 365.0)  # Approximate age in years as float
    }

