"""
Enhanced Validation and Error Handling Utilities

This module provides enhanced validation functions and error handling
for forms and API endpoints.
"""
from typing import Optional, Dict, Any, List
from fastapi import Request, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
import json


def format_validation_errors(errors: List[Dict[str, Any]]) -> str:
    """
    Format Pydantic validation errors into a user-friendly message.
    
    Args:
        errors: List of error dictionaries from Pydantic
        
    Returns:
        Formatted error message string
    """
    error_messages = []
    for error in errors:
        field = ".".join(str(loc) for loc in error.get("loc", []))
        message = error.get("msg", "Invalid value")
        error_messages.append(f"{field}: {message}")
    
    return "; ".join(error_messages)


def get_field_error(errors: List[Dict[str, Any]], field_name: str) -> Optional[str]:
    """
    Get the error message for a specific field.
    
    Args:
        errors: List of error dictionaries from Pydantic
        field_name: Name of the field to get error for
        
    Returns:
        Error message for the field or None
    """
    for error in errors:
        loc = error.get("loc", [])
        if len(loc) > 0 and str(loc[-1]) == field_name:
            return error.get("msg", "Invalid value")
    return None


def validate_required_fields(form_data: Dict[str, Any], required_fields: List[str]) -> Optional[str]:
    """
    Validate that all required fields are present and not empty.
    
    Args:
        form_data: Dictionary of form data
        required_fields: List of required field names
        
    Returns:
        Error message if validation fails, None otherwise
    """
    missing_fields = []
    for field in required_fields:
        value = form_data.get(field)
        if not value or (isinstance(value, str) and value.strip() == ""):
            missing_fields.append(field)
    
    if missing_fields:
        return f"Missing required fields: {', '.join(missing_fields)}"
    return None


def validate_numeric_field(value: Any, field_name: str, min_value: Optional[float] = None, 
                          max_value: Optional[float] = None) -> Optional[str]:
    """
    Validate a numeric field.
    
    Args:
        value: Value to validate
        field_name: Name of the field
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Error message if validation fails, None otherwise
    """
    try:
        num_value = float(value)
        if min_value is not None and num_value < min_value:
            return f"{field_name} must be at least {min_value}"
        if max_value is not None and num_value > max_value:
            return f"{field_name} must be at most {max_value}"
        return None
    except (ValueError, TypeError):
        return f"{field_name} must be a valid number"


def validate_date_format(date_string: str, field_name: str = "Date") -> Optional[str]:
    """
    Validate date format (YYYY-MM-DD).
    
    Args:
        date_string: Date string to validate
        field_name: Name of the field
        
    Returns:
        Error message if validation fails, None otherwise
    """
    try:
        from datetime import datetime
        datetime.strptime(date_string, "%Y-%m-%d")
        return None
    except (ValueError, TypeError):
        return f"{field_name} must be in YYYY-MM-DD format"


def validate_email(email: str) -> Optional[str]:
    """
    Basic email validation.
    
    Args:
        email: Email string to validate
        
    Returns:
        Error message if validation fails, None otherwise
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return "Invalid email format"
    return None


def validate_phone_number(phone: str) -> Optional[str]:
    """
    Basic phone number validation (allows digits, spaces, dashes, parentheses).
    
    Args:
        phone: Phone number string to validate
        
    Returns:
        Error message if validation fails, None otherwise
    """
    import re
    # Remove common phone number characters for validation
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    if not cleaned.isdigit() or len(cleaned) < 7:
        return "Phone number must contain at least 7 digits"
    return None


def handle_validation_error(
    request: Request,
    errors: List[Dict[str, Any]],
    redirect_url: str,
    error_param: str = "error"
) -> RedirectResponse:
    """
    Handle validation errors by redirecting with error message.
    
    Args:
        request: FastAPI request object
        errors: List of validation errors
        redirect_url: URL to redirect to
        error_param: Query parameter name for error
        
    Returns:
        RedirectResponse with error message
    """
    error_message = format_validation_errors(errors)
    # URL encode the error message
    from urllib.parse import quote
    encoded_error = quote(error_message)
    redirect_url_with_error = f"{redirect_url}?{error_param}={encoded_error}"
    return RedirectResponse(url=redirect_url_with_error, status_code=302)


def create_error_response(
    request: Request,
    status_code: int,
    message: str,
    details: Optional[Dict[str, Any]] = None
):
    """
    Create a standardized error response.
    
    Args:
        request: FastAPI request object
        status_code: HTTP status code
        message: Error message
        details: Additional error details
        
    Returns:
        JSONResponse or TemplateResponse depending on request type
    """
    from fastapi.templating import Jinja2Templates
    import os
    
    # Check if this is an API request
    if request.url.path.startswith("/api/"):
        error_data = {"detail": message}
        if details:
            error_data["details"] = details
        return JSONResponse(status_code=status_code, content=error_data)
    
    # For UI requests, render error template
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
    
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "status_code": status_code,
            "detail": message,
            "details": details
        },
        status_code=status_code
    )

