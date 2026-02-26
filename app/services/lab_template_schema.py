"""
Lab Template Schema Validation
Validates template schema_json before publish.
"""
from typing import Dict, Any, List, Optional, Tuple


# Valid field types
FIELD_TYPES = {"numeric", "text", "choice", "multichoice", "datetime", "table", "repeat_group", "calculated"}

# Valid disciplines
DISCIPLINES = {
    "HEMATOLOGY", "CHEMISTRY", "MICROBIOLOGY", "SEROLOGY",
    "BLOODBANK", "PARASITOLOGY", "HISTOLOGY", "GENERAL"
}


def validate_template_schema(schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate template schema_json structure.
    Returns (is_valid, list of error messages).
    """
    errors: List[str] = []

    # Required top-level keys
    if "meta" not in schema:
        errors.append("Missing 'meta' section")
    if "layout" not in schema:
        errors.append("Missing 'layout' section")
    if "fields" not in schema:
        errors.append("Missing 'fields' section")

    if errors:
        return False, errors

    meta = schema.get("meta", {})
    layout = schema.get("layout", {})
    fields = schema.get("fields", {})
    rules = schema.get("rules", {})
    calculated = schema.get("calculated", [])

    # Meta validation
    if not meta.get("name"):
        errors.append("meta.name is required")
    if meta.get("discipline") and meta["discipline"] not in DISCIPLINES:
        errors.append(f"meta.discipline must be one of: {', '.join(DISCIPLINES)}")

    # Layout validation
    sections = layout.get("sections", [])
    if not sections:
        errors.append("layout.sections must have at least one section")

    all_item_ids = set()
    for sec in sections:
        if not isinstance(sec, dict):
            errors.append("Each layout section must be an object")
            continue
        sec_id = sec.get("id")
        if not sec_id:
            errors.append("Section must have 'id'")
        rows = sec.get("rows", [])
        for row in rows:
            if not isinstance(row, dict):
                continue
            for col in row.get("columns", []):
                if not isinstance(col, dict):
                    continue
                for item_id in col.get("items", []):
                    all_item_ids.add(item_id)

    # Fields validation
    for field_id, field_def in fields.items():
        if not isinstance(field_def, dict):
            errors.append(f"Field '{field_id}' must be an object")
            continue
        ftype = field_def.get("type")
        if not ftype:
            errors.append(f"Field '{field_id}' missing 'type'")
        elif ftype not in FIELD_TYPES:
            errors.append(f"Field '{field_id}' has invalid type '{ftype}'")
        code = field_def.get("code")
        if not code:
            errors.append(f"Field '{field_id}' missing 'code' (used for result_json storage)")
        if ftype == "numeric":
            if "decimals" in field_def and not isinstance(field_def["decimals"], int):
                errors.append(f"Field '{field_id}': decimals must be integer")
        if ftype in ("choice", "multichoice"):
            if "options" not in field_def and "optionSet" not in field_def:
                errors.append(f"Field '{field_id}' (choice/multichoice) must have 'options' or 'optionSet'")
        if ftype == "repeat_group":
            child_fields = field_def.get("childFields") or field_def.get("fields") or []
            if not child_fields:
                errors.append(f"Field '{field_id}' (repeat_group) must have 'childFields' array")
            for cf in child_fields:
                if not isinstance(cf, dict) or not cf.get("code"):
                    errors.append(f"Field '{field_id}': childFields must have objects with 'code'")
        if ftype == "table":
            row_set = field_def.get("rowOptionSet")
            col_set = field_def.get("colOptionSet")
            row_opts = field_def.get("rowOptions")
            col_opts = field_def.get("colOptions")
            if not row_set and not (row_opts and len(row_opts) > 0):
                errors.append(f"Field '{field_id}' (table) must have 'rowOptionSet' or non-empty 'rowOptions'")
            if not col_set and not (col_opts and len(col_opts) > 0):
                errors.append(f"Field '{field_id}' (table) must have 'colOptionSet' or non-empty 'colOptions'")

    # All layout items must exist in fields (or be section headers)
    for item_id in all_item_ids:
        if item_id not in fields and not item_id.startswith("sec_"):
            errors.append(f"Layout references unknown field/section '{item_id}'")

    # Rules validation
    visibility = rules.get("visibility", [])
    required_if = rules.get("requiredIf", [])
    for rule in visibility + required_if:
        if not isinstance(rule, dict):
            errors.append("Each rule must be an object")
            continue
        target = rule.get("target") or rule.get("target_code")
        if not target:
            errors.append("Rule missing 'target'")
        cond = rule.get("showIf") or rule.get("if")
        if cond and isinstance(cond, dict):
            if "field" not in cond:
                errors.append("Condition must have 'field'")
            if "op" not in cond:
                errors.append("Condition must have 'op'")

    # Calculated validation
    for calc in calculated:
        if not isinstance(calc, dict):
            continue
        if not calc.get("target_code"):
            errors.append("Calculated item missing target_code")
        if not calc.get("formula") and not calc.get("deps"):
            errors.append(f"Calculated '{calc.get('target_code')}' must have formula or deps")

    return len(errors) == 0, errors
