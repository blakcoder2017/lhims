"""
Reference Range Audit API

Read-only API endpoints for reference range auditing and reporting.
These endpoints do not modify any data - they only provide diagnostic information.

Endpoints:
- GET /lab/audit/range-coverage - Coverage report showing fields with/without ranges
- GET /lab/audit/unit-mismatches - Unit validation report
- GET /lab/audit/health-status - Overall health check
- GET /lab/audit/age-gap-analysis - Age range coverage analysis
- GET /lab/audit/field/{field_code} - Detailed report for specific field

Access: Admin, Lab Manager, Lab Staff
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.db.database import get_db
from app.core.deps import role_required
from app.core.templates import templates
from app.services.reference_range_audit import (
    get_range_coverage_report,
    get_unit_mismatch_report,
    get_range_health_status,
    get_age_gap_analysis,
    get_detailed_field_report
)

router = APIRouter(prefix="/lab/audit", tags=["Lab Reference Range Audit"])


@router.get("/dashboard", name="lab_reference_range_audit_dashboard")
def audit_dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Manager", "Lab Staff"]))
):
    """
    Reference Range Audit Dashboard HTML page.
    
    Provides a user-friendly interface for viewing reference range health status.
    This is a read-only audit function - no data is modified.
    """
    health_status = get_range_health_status(db)
    coverage = get_range_coverage_report(db)
    unit_mismatches = get_unit_mismatch_report(db)
    age_gap = get_age_gap_analysis(db)
    
    return templates.TemplateResponse(
        "lab/reference_range_audit.html",
        {
            "request": request,
            "health_status": health_status,
            "coverage": coverage,
            "unit_mismatches": unit_mismatches,
            "age_gap": age_gap,
            "current_user": current_user,
            "user_role": current_user.role.name if current_user.role else "Guest",
        }
    )


@router.get("/range-coverage", name="lab_audit_range_coverage")
def audit_range_coverage(
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Manager", "Lab Staff"]))
):
    """
    Get reference range coverage report.
    
    Shows which template fields have reference ranges defined
    and which fields are missing ranges.
    
    This is a read-only audit function - no data is modified.
    """
    return get_range_coverage_report(db)


@router.get("/unit-mismatches", name="lab_audit_unit_mismatches")
def audit_unit_mismatches(
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Manager", "Lab Staff"]))
):
    """
    Get unit mismatch report.
    
    Identifies template fields where the unit defined in the template
    does not match the unit in the reference range.
    
    This is a read-only audit function - no data is modified.
    """
    return get_unit_mismatch_report(db)


@router.get("/health-status", name="lab_audit_health_status")
def audit_health_status(
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Manager", "Lab Staff"]))
):
    """
    Get overall reference range health status.
    
    Provides a comprehensive health check including:
    - Coverage percentage
    - Unit mismatches
    - Orphaned ranges
    - Critical value configuration
    - Sex distribution
    
    This is a read-only audit function - no data is modified.
    """
    return get_range_health_status(db)


@router.get("/age-gap-analysis", name="lab_audit_age_gap_analysis")
def audit_age_gap_analysis(
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Manager", "Lab Staff"]))
):
    """
    Get age range gap analysis.
    
    Shows which age groups have reference range coverage
    for each field, helping identify pediatric range gaps.
    
    This is a read-only audit function - no data is modified.
    """
    return get_age_gap_analysis(db)


@router.get("/field/{field_code}", name="lab_audit_field_detail")
def audit_field_detail(
    field_code: str,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Manager", "Lab Staff"]))
):
    """
    Get detailed reference range information for a specific field.
    
    Returns all reference ranges defined for the given field code,
    including age and sex breakdowns.
    
    This is a read-only audit function - no data is modified.
    """
    return get_detailed_field_report(db, field_code)


@router.get("/", name="lab_audit_dashboard")
def audit_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Manager", "Lab Staff"]))
):
    """
    Get complete audit dashboard.
    
    Returns a summary of all audit information in one call.
    Useful for dashboard display.
    
    This is a read-only audit function - no data is modified.
    """
    health = get_range_health_status(db)
    coverage = get_range_coverage_report(db)
    unit_issues = get_unit_mismatch_report(db)
    age_analysis = get_age_gap_analysis(db)
    
    return {
        "generated_at": "now",
        "health_status": health["status"],
        "health_message": health["message"],
        "summary": {
            "total_template_fields": coverage["total_template_fields"],
            "coverage_percentage": coverage["coverage_percentage"],
            "fields_without_ranges": coverage["fields_without_ranges"],
            "unit_mismatches": unit_issues["mismatches_count"],
            "orphaned_ranges": len(health.get("orphaned_range_codes", []))
        },
        "top_uncovered_fields": coverage.get("uncovered_fields", [])[:10],
        "top_unit_mismatches": unit_issues.get("mismatches", [])[:10],
        "age_gap_summary": age_analysis.get("bracket_summary", {}),
        "recommendations": health.get("recommendations", [])
    }
