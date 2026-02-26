"""
Lab Template Rendering Service

Provides utilities for rendering lab template forms and results.
"""
from typing import Dict, Any, Optional, List
from datetime import date, datetime


def render_form_context(
    schema_json: Dict[str, Any],
    result_json: Optional[Dict[str, Any]] = None,
    patient_context: Optional[Dict[str, Any]] = None,
    option_sets: Optional[Dict[str, List[str]]] = None,
    ref_ranges: Optional[Dict[str, Dict[str, Any]]] = None,
    flags_json: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Build context for rendering a template form.
    
    Args:
        schema_json: The template schema definition
        result_json: Existing results (from lab_orders.result_json)
        patient_context: Patient demographics for reference range lookup
        option_sets: Dictionary of option set code -> options list
        ref_ranges: Dictionary of field code -> range info
        flags_json: Dictionary of field code -> flag status
    
    Returns:
        Dictionary with all context needed by the Jinja2 templates
    """
    fields = schema_json.get("fields", {})
    layout = schema_json.get("layout", {})
    sections = layout.get("sections", [])
    
    # Ensure result_json is a dict
    if result_json is None:
        result_json = {}
    
    # Ensure patient_context has defaults
    if patient_context is None:
        patient_context = {}
    
    # Ensure option_sets is a dict
    if option_sets is None:
        option_sets = {}
    
    # Ensure ref_ranges is a dict
    if ref_ranges is None:
        ref_ranges = {}
    
    # Ensure flags_json is a dict
    if flags_json is None:
        flags_json = {}
    
    # Build the context
    context = {
        "schema_json": schema_json,
        "result_json": result_json,
        "patient_context": patient_context,
        "option_sets": option_sets,
        "ref_ranges": ref_ranges,
        "flags_json": flags_json,
        "fields": fields,
        "layout": layout,
        "sections": sections,
        "meta": schema_json.get("meta", {}),
    }
    
    return context


def evaluate_visibility(
    schema_json: Dict[str, Any],
    result_json: Dict[str, Any]
) -> Dict[str, bool]:
    """
    Evaluate visibility rules for all fields.
    
    Args:
        schema_json: The template schema definition
        result_json: Current form values
    
    Returns:
        Dictionary of field_id -> visible (bool)
    """
    fields = schema_json.get("fields", {})
    rules = schema_json.get("rules", {})
    visibility_rules = rules.get("visibility", {})
    
    # Start with all fields visible
    visibility = {field_id: True for field_id in fields.keys()}
    
    # Apply each visibility rule
    for rule in visibility_rules:
        target = rule.get("target") or rule.get("target_code")
        condition = rule.get("showIf") or rule.get("if")
        
        if not target or not condition:
            continue
        
        field = condition.get("field")
        op = condition.get("op")
        value = condition.get("value")
        
        if not field or not op:
            continue
        
        # Get current value of the trigger field
        current_value = result_json.get(field)
        
        # Evaluate condition
        is_visible = _evaluate_condition(current_value, op, value)
        
        visibility[target] = is_visible
    
    return visibility


def evaluate_required_if(
    schema_json: Dict[str, Any],
    result_json: Dict[str, Any]
) -> Dict[str, bool]:
    """
    Evaluate requiredIf rules for all fields.
    
    Args:
        schema_json: The template schema definition  
        result_json: Current form values
    
    Returns:
        Dictionary of field_id -> required (bool)
    """
    fields = schema_json.get("fields", {})
    rules = schema_json.get("rules", {})
    required_rules = rules.get("requiredIf", {})
    
    # Start with base required status from field definition
    required = {
        field_id: fields[field_id].get("required", False) 
        for field_id in fields.keys()
    }
    
    # Apply each requiredIf rule
    for rule in required_rules:
        target = rule.get("target") or rule.get("target_code")
        condition = rule.get("if") or rule.get("showIf")
        
        if not target or not condition:
            continue
        
        field = condition.get("field")
        op = condition.get("op")
        value = condition.get("value")
        
        if not field or not op:
            continue
        
        # Get current value of the trigger field
        current_value = result_json.get(field)
        
        # Evaluate condition
        is_required = _evaluate_condition(current_value, op, value)
        
        if is_required:
            required[target] = True
    
    return required


def _evaluate_condition(actual_value: Any, operator: str, expected_value: Any) -> bool:
    """Evaluate a single condition."""
    if operator == "==":
        return actual_value == expected_value
    elif operator == "!=":
        return actual_value != expected_value
    elif operator == "contains":
        if isinstance(actual_value, str):
            return expected_value in actual_value
        return False
    elif operator == "not contains":
        if isinstance(actual_value, str):
            return expected_value not in actual_value
        return True
    elif operator == "in":
        if isinstance(expected_value, list):
            return actual_value in expected_value
        return False
    elif operator == "not in":
        if isinstance(expected_value, list):
            return actual_value not in expected_value
        return True
    elif operator == ">":
        try:
            return float(actual_value) > float(expected_value)
        except (TypeError, ValueError):
            return False
    elif operator == "<":
        try:
            return float(actual_value) < float(expected_value)
        except (TypeError, ValueError):
            return False
    elif operator == ">=":
        try:
            return float(actual_value) >= float(expected_value)
        except (TypeError, ValueError):
            return False
    elif operator == "<=":
        try:
            return float(actual_value) <= float(expected_value)
        except (TypeError, ValueError):
            return False
    
    return False


def evaluate_calculated_fields(
    schema_json: Dict[str, Any],
    result_json: Dict[str, Any],
    patient_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluate calculated fields based on formulas.
    
    Args:
        schema_json: The template schema definition
        result_json: Existing results (will be modified)
        patient_context: Patient demographics (optional)
    
    Returns:
        Modified result_json with calculated values added
    """
    calculated = schema_json.get("calculated", [])
    
    # Make a copy to avoid modifying original
    result = dict(result_json)
    
    for calc in calculated:
        target_code = calc.get("target_code")
        formula = calc.get("formula")
        
        if not target_code or not formula:
            continue
        
        # Try to evaluate the formula
        try:
            value = _evaluate_formula(formula, result)
            result[target_code] = value
        except Exception:
            # If formula fails, leave field empty
            result[target_code] = None
    
    return result


def _evaluate_formula(formula: str, values: Dict[str, Any]) -> Optional[float]:
    """
    Simple formula evaluator.
    Supports basic arithmetic: +, -, *, /, parentheses
    """
    import re
    
    # Replace field codes with values
    def replace_field(match):
        code = match.group(0)
        val = values.get(code)
        if val is None:
            return "0"
        try:
            return str(float(val))
        except (TypeError, ValueError):
            return "0"
    
    # Find all field codes (word characters)
    expr = re.sub(r'[a-zA-Z_][a-zA-Z0-9_]*', replace_field, formula)
    
    # Validate expression only contains safe characters
    if not re.match(r'^[\d\s+\-*/.()]+$', expr):
        return None
    
    try:
        result = eval(expr, {"__builtins__": {}}, {})
        if isinstance(result, float):
            return round(result, 6)
        return result
    except Exception:
        return None


def get_field_with_context(
    field_id: str,
    field_def: Dict[str, Any],
    result_json: Dict[str, Any],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Get a field with all its context for rendering.
    
    Args:
        field_id: The field identifier
        field_def: Field definition from schema
        result_json: Current values
        context: Full render context
    
    Returns:
        Enhanced field definition with value and status
    """
    code = field_def.get("code", field_id)
    
    return {
        **field_def,
        "field_id": field_id,
        "value": result_json.get(code),
        "flag": context.get("flags_json", {}).get(code),
        "ref_range": context.get("ref_ranges", {}).get(code),
    }
