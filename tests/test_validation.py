"""
Tests for validation utilities.
"""
import pytest
from app.core.validation import (
    format_validation_errors,
    get_field_error,
    validate_required_fields,
    validate_numeric_field,
    validate_date_format,
    validate_email,
    validate_phone_number
)


@pytest.mark.unit
def test_format_validation_errors():
    """Test formatting validation errors."""
    errors = [
        {"loc": ["field1"], "msg": "Field is required", "type": "value_error"},
        {"loc": ["field2"], "msg": "Invalid format", "type": "type_error"}
    ]
    
    result = format_validation_errors(errors)
    assert "field1" in result
    assert "Field is required" in result
    assert "field2" in result
    assert "Invalid format" in result


@pytest.mark.unit
def test_get_field_error():
    """Test getting error for specific field."""
    errors = [
        {"loc": ["field1"], "msg": "Field is required", "type": "value_error"},
        {"loc": ["field2"], "msg": "Invalid format", "type": "type_error"}
    ]
    
    error1 = get_field_error(errors, "field1")
    assert error1 == "Field is required"
    
    error2 = get_field_error(errors, "field2")
    assert error2 == "Invalid format"
    
    error3 = get_field_error(errors, "field3")
    assert error3 is None


@pytest.mark.unit
def test_validate_required_fields():
    """Test required field validation."""
    form_data = {
        "field1": "value1",
        "field2": "",
        "field3": "value3"
    }
    
    # All fields present
    result = validate_required_fields(form_data, ["field1", "field3"])
    assert result is None
    
    # Missing field
    result = validate_required_fields(form_data, ["field1", "field2", "field4"])
    assert result is not None
    assert "field2" in result or "field4" in result


@pytest.mark.unit
def test_validate_numeric_field():
    """Test numeric field validation."""
    # Valid number
    assert validate_numeric_field("10", "test_field") is None
    assert validate_numeric_field("10.5", "test_field") is None
    
    # Invalid number
    assert validate_numeric_field("abc", "test_field") is not None
    
    # Min/Max validation
    assert validate_numeric_field("5", "test_field", min_value=10) is not None
    assert validate_numeric_field("15", "test_field", max_value=10) is not None
    assert validate_numeric_field("10", "test_field", min_value=5, max_value=15) is None


@pytest.mark.unit
def test_validate_date_format():
    """Test date format validation."""
    # Valid dates
    assert validate_date_format("2024-01-01") is None
    assert validate_date_format("1990-12-31") is None
    
    # Invalid dates
    assert validate_date_format("01-01-2024") is not None
    assert validate_date_format("2024/01/01") is not None
    assert validate_date_format("invalid") is not None


@pytest.mark.unit
def test_validate_email():
    """Test email validation."""
    # Valid emails
    assert validate_email("test@example.com") is None
    assert validate_email("user.name@domain.co.uk") is None
    
    # Invalid emails
    assert validate_email("invalid") is not None
    assert validate_email("test@") is not None
    assert validate_email("@example.com") is not None


@pytest.mark.unit
def test_validate_phone_number():
    """Test phone number validation."""
    # Valid phone numbers
    assert validate_phone_number("0244123456") is None
    assert validate_phone_number("0244 123 456") is None
    assert validate_phone_number("(0244) 123-456") is None
    
    # Invalid phone numbers
    assert validate_phone_number("123") is not None  # Too short
    assert validate_phone_number("abc123") is not None  # Contains letters

