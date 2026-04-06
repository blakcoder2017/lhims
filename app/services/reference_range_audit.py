"""
Reference Range Audit Service

Provides read-only audit and reporting functions for reference range management.
These functions are non-disruptive and do not modify any data.

Functions:
- get_range_coverage_report: Shows which template fields have ranges defined
- get_unit_mismatch_report: Identifies template fields with unit mismatches
- get_range_health_status: Overall health check for reference ranges
- get_age_gap_analysis: Shows age range coverage for each field
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.lab_template_models import LabTemplateVersion, LabReferenceRange
from app.models.lab_models import ReferenceRange


def get_all_template_field_codes(db: Session) -> Dict[str, Any]:
    """
    Get all field codes from published templates with their units.
    Returns dict mapping field_code -> {unit, template_names}
    """
    templates = db.query(LabTemplateVersion).filter(
        LabTemplateVersion.status == "PUBLISHED"
    ).all()
    
    field_info = {}
    for template in templates:
        schema = template.schema_json
        if not schema:
            continue
            
        template_name = schema.get("meta", {}).get("name") or "Unknown"
        fields = schema.get("fields", {})
        
        if isinstance(fields, dict):
            for field_id, field_def in fields.items():
                if isinstance(field_def, dict):
                    code = field_def.get("code") or field_id
                    unit = field_def.get("unit") or field_def.get("default_unit")
                    
                    if code not in field_info:
                        field_info[code] = {
                            "unit": unit,
                            "templates": [],
                            "field_type": field_def.get("type") or field_def.get("field_type")
                        }
                    if template_name not in field_info[code]["templates"]:
                        field_info[code]["templates"].append(template_name)
    
    return field_info


def get_range_coverage_report(db: Session) -> Dict[str, Any]:
    """
    Generate a coverage report showing which template fields have reference ranges defined.
    This is a read-only audit function that doesn't modify any data.
    """
    # Get all field codes from templates
    field_info = get_all_template_field_codes(db)
    
    # Get all defined reference ranges
    defined_ranges = db.query(LabReferenceRange.field_code).distinct().all()
    defined_codes = set([r[0] for r in defined_ranges])
    
    # Categorize fields
    covered_fields = []
    uncovered_fields = []
    
    for code, info in field_info.items():
        if code in defined_codes:
            covered_fields.append({
                "field_code": code,
                "unit": info.get("unit"),
                "field_type": info.get("field_type"),
                "templates": info.get("templates", [])
            })
        else:
            uncovered_fields.append({
                "field_code": code,
                "unit": info.get("unit"),
                "field_type": info.get("field_type"),
                "templates": info.get("templates", [])
            })
    
    return {
        "total_template_fields": len(field_info),
        "fields_with_ranges": len(covered_fields),
        "fields_without_ranges": len(uncovered_fields),
        "coverage_percentage": round(len(covered_fields) / len(field_info) * 100, 1) if field_info else 0,
        "covered_fields": covered_fields,
        "uncovered_fields": uncovered_fields
    }


def get_unit_mismatch_report(db: Session) -> Dict[str, Any]:
    """
    Check if template field units match reference range units.
    Returns list of potential mismatches for review (read-only).
    """
    field_info = get_all_template_field_codes(db)
    
    mismatches = []
    matches = []
    
    # Get all reference ranges grouped by field_code
    ranges = db.query(LabReferenceRange).all()
    range_by_code = {}
    for rr in ranges:
        if rr.field_code not in range_by_code:
            range_by_code[rr.field_code] = []
        range_by_code[rr.field_code].append(rr.unit)
    
    for code, info in field_info.items():
        template_unit = info.get("unit")
        if not template_unit:
            continue
            
        # Get units from reference ranges
        range_units = list(set(range_by_code.get(code, [])))
        
        if not range_units:
            continue
            
        # Check for mismatch
        if template_unit not in range_units and None not in range_units:
            # Check if it's actually a mismatch (not just different case)
            normalized_template = template_unit.lower().strip()
            normalized_range = [u.lower().strip() for u in range_units if u]
            
            if normalized_template not in normalized_range:
                mismatches.append({
                    "field_code": code,
                    "template_unit": template_unit,
                    "reference_range_units": range_units,
                    "templates": info.get("templates", [])
                })
            else:
                matches.append({
                    "field_code": code,
                    "template_unit": template_unit,
                    "reference_range_units": range_units
                })
    
    return {
        "total_fields_checked": len(field_info),
        "mismatches": mismatches,
        "mismatches_count": len(mismatches),
        "matches_count": len(matches),
        "warning": "Review mismatches to ensure correct interpretation of results"
    }


def get_range_health_status(db: Session) -> Dict[str, Any]:
    """
    Overall health check for reference range system.
    Returns read-only diagnostic information.
    """
    # Get coverage
    coverage = get_range_coverage_report(db)
    
    # Get unit mismatches
    unit_issues = get_unit_mismatch_report(db)
    
    # Check for orphaned ranges (ranges for fields not in any template)
    all_template_codes = set(get_all_template_field_codes(db).keys())
    all_range_codes = set([r[0] for r in db.query(LabReferenceRange.field_code).distinct().all()])
    orphaned_ranges = all_range_codes - all_template_codes
    
    # Count ranges by sex category
    sex_distribution = {}
    for sex in ['M', 'F', 'ANY']:
        count = db.query(LabReferenceRange).filter(LabReferenceRange.sex == sex).count()
        sex_distribution[sex] = count
    
    # Count ranges with critical values
    critical_ranges = db.query(LabReferenceRange).filter(
        or_(
            LabReferenceRange.critical_low.isnot(None),
            LabReferenceRange.critical_high.isnot(None)
        )
    ).count()
    
    # Overall status
    issues_count = len(unit_issues.get("mismatches", [])) + len(coverage.get("uncovered_fields", []))
    
    if issues_count == 0:
        status = "HEALTHY"
        message = "All reference ranges are properly configured"
    elif issues_count < 5:
        status = "WARNING"
        message = f"{issues_count} minor issues found - review recommended"
    else:
        status = "CRITICAL"
        message = f"{issues_count} issues require attention"
    
    return {
        "status": status,
        "message": message,
        "summary": {
            "total_template_fields": coverage["total_template_fields"],
            "fields_with_ranges": coverage["fields_with_ranges"],
            "fields_without_ranges": coverage["fields_without_ranges"],
            "coverage_percentage": coverage["coverage_percentage"],
            "unit_mismatches": unit_issues["mismatches_count"],
            "orphaned_ranges": len(orphaned_ranges),
            "ranges_with_critical_values": critical_ranges,
            "sex_distribution": sex_distribution
        },
        "orphaned_range_codes": sorted(list(orphaned_ranges)),
        "recommendations": _generate_recommendations(coverage, unit_issues, orphaned_ranges)
    }


def _generate_recommendations(coverage: Dict, unit_issues: Dict, orphaned_ranges: set) -> List[str]:
    """Generate non-disruptive recommendations based on analysis."""
    recommendations = []
    
    if coverage.get("uncovered_fields"):
        recommendations.append(
            f"Consider adding reference ranges for {len(coverage['uncovered_fields'])} "
            f"template fields that currently have no ranges defined"
        )
    
    if unit_issues.get("mismatches"):
        recommendations.append(
            f"Review {len(unit_issues['mismatches'])} fields where template units "
            f"don't match reference range units"
        )
    
    if orphaned_ranges:
        recommendations.append(
            f"Consider removing {len(orphaned_ranges)} reference ranges that don't "
            f"correspond to any template field"
        )
    
    if not recommendations:
        recommendations.append("Reference range system is properly configured")
    
    return recommendations


def get_age_gap_analysis(db: Session) -> Dict[str, Any]:
    """
    Analyze age range coverage for each field.
    Shows which age groups have coverage and which are missing.
    """
    # Age brackets in days
    age_brackets = {
        "NEWBORN (0-28 days)": (0, 28),
        "INFANT (29-365 days)": (29, 365),
        "CHILD (1-12 years)": (365, 4380),
        "ADOLESCENT (13-18 years)": (4380, 6570),
        "ADULT (19-60 years)": (6570, 21900),
        "ELDERLY (60+ years)": (21900, 30000)
    }
    
    # Get all unique field codes with ranges
    field_codes = db.query(LabReferenceRange.field_code).distinct().all()
    field_codes = [r[0] for r in field_codes]
    
    field_age_coverage = []
    
    for code in field_codes:
        ranges = db.query(LabReferenceRange).filter(
            LabReferenceRange.field_code == code
        ).all()
        
        # Determine which age brackets are covered
        covered_brackets = set()
        for rr in ranges:
            min_age = rr.age_min_days or 0
            max_age = rr.age_max_days or 30000
            
            for bracket_name, (bracket_min, bracket_max) in age_brackets.items():
                if min_age <= bracket_max and max_age >= bracket_min:
                    covered_brackets.add(bracket_name)
        
        field_age_coverage.append({
            "field_code": code,
            "total_ranges": len(ranges),
            "covered_brackets": sorted(list(covered_brackets)),
            "missing_brackets": sorted(set(age_brackets.keys()) - covered_brackets)
        })
    
    # Summary by bracket
    bracket_summary = {name: 0 for name in age_brackets.keys()}
    for fa in field_age_coverage:
        for bracket in fa["covered_brackets"]:
            bracket_summary[bracket] += 1
    
    return {
        "total_fields_with_ranges": len(field_codes),
        "age_brackets": list(age_brackets.keys()),
        "field_age_coverage": field_age_coverage,
        "bracket_summary": bracket_summary,
        "recommendation": "Ensure critical pediatric ranges are defined for all commonly tested parameters"
    }


def get_detailed_field_report(db: Session, field_code: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific field's reference ranges.
    """
    ranges = db.query(LabReferenceRange).filter(
        LabReferenceRange.field_code == field_code
    ).all()
    
    if not ranges:
        return {
            "field_code": field_code,
            "exists": False,
            "message": "No reference ranges found for this field"
        }
    
    range_details = []
    for rr in ranges:
        age_range = "All ages"
        if rr.age_min_days is not None or rr.age_max_days is not None:
            min_age = rr.age_min_days or 0
            max_age = rr.age_max_days or "Any"
            if isinstance(max_age, int):
                years = max_age // 365
                age_range = f"{min_age}-{max_age} days ({min_age//365}-{years} years)"
            else:
                age_range = f"{min_age}+ days"
        
        range_details.append({
            "sex": rr.sex,
            "age_range": age_range,
            "low": float(rr.low) if rr.low is not None else None,
            "high": float(rr.high) if rr.high is not None else None,
            "unit": rr.unit,
            "critical_low": float(rr.critical_low) if rr.critical_low is not None else None,
            "critical_high": float(rr.critical_high) if rr.critical_high is not None else None,
            "text_range": rr.text_range,
            "gestational_age_based": rr.is_gestational_age_based
        })
    
    return {
        "field_code": field_code,
        "exists": True,
        "total_ranges": len(ranges),
        "ranges": range_details
    }
