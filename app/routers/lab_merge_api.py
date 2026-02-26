"""
Lab Merge API - Unified Lab Operations

This module provides unified API endpoints for:
- Merging lab tests and templates
- Reference range management
- Result interpretation
- Test template retrieval

All endpoints maintain backward compatibility with existing system.

Author: Hospital EMR System
"""

from datetime import date
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from decimal import Decimal

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.models.lab_catalog_models import LabTest
from app.models.lab_template_models import LabTemplate, LabTemplateVersion, LabReferenceRange, LabOptionSet
from app.models.lab_models import ReferenceRange
from app.models.patient_models import Patient
from app.services.reference_range_engine import (
    get_unified_reference_range,
    calculate_age_in_days,
    validate_test_applicability,
    get_age_bracket,
    ReferenceRangeResult
)
from app.services.result_interpretation import (
    interpret_numeric_result,
    interpret_qualitative_result,
    interpret_results_batch,
    ResultFlag,
    can_override_flag,
    log_reference_range_override
)

router = APIRouter(prefix="/lab", tags=["Lab - Unified Operations"])


# ============= Request/Response Models =============

class PatientContext(BaseModel):
    """Patient context for reference range lookup"""
    patient_id: Optional[int] = None
    date_of_birth: Optional[date] = None
    sex: str = "ANY"  # M, F, ANY
    facility_id: Optional[int] = None


class ReferenceRangeLookupRequest(BaseModel):
    """Request for reference range lookup"""
    field_code: Optional[str] = None
    test_id: Optional[int] = None
    test_name: Optional[str] = None
    patient: PatientContext


class ReferenceRangeResponse(BaseModel):
    """Reference range response"""
    low: Optional[float] = None
    high: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    unit: Optional[str] = None
    text_range: Optional[str] = None
    interpretation: Optional[str] = None
    source_table: str
    range_id: Optional[str] = None
    is_fallback: bool = False


class ResultInterpretationRequest(BaseModel):
    """Request for result interpretation"""
    results: Dict[str, Any]  # field_code -> value
    patient: PatientContext
    template_fields: Optional[Dict[str, Any]] = None


class ResultInterpretationResponse(BaseModel):
    """Result interpretation response"""
    interpreted_results: Dict[str, Any]
    flags: Dict[str, str]


class TestMergeRequest(BaseModel):
    """Request for merging test templates"""
    test_name: str
    test_code: Optional[str] = None
    test_category: str
    discipline: str  # HEMATOLOGY, CHEMISTRY, MICROBIOLOGY, etc.
    template_schema: Dict[str, Any]
    reference_ranges: List[Dict[str, Any]] = []


class TestMergeResponse(BaseModel):
    """Response for merged test"""
    test_id: int
    template_id: str
    message: str


class ReferenceRangeMergeRequest(BaseModel):
    """Request for merging reference ranges"""
    field_code: str
    test_name: Optional[str] = None
    sex: str = "ANY"  # M, F, ANY
    age_min_days: Optional[int] = None
    age_max_days: Optional[int] = None
    low: Optional[float] = None
    high: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    unit: Optional[str] = None
    text_range: Optional[str] = None
    facility_id: Optional[int] = None


class ReferenceRangeMergeResponse(BaseModel):
    """Response for merged reference range"""
    range_id: str
    message: str


class FlagOverrideRequest(BaseModel):
    """Request for overriding a result flag"""
    lab_order_id: int
    field_code: str
    original_flag: str
    new_flag: str
    override_note: str


# ============= Reference Range Endpoints =============

@router.post("/reference-ranges/lookup", response_model=ReferenceRangeResponse)
def lookup_reference_range(
    request: ReferenceRangeLookupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Lab Staff", "Doctor", "Nurse"]))
):
    """
    Lookup reference range for a specific test/field.
    
    Automatically selects the most appropriate range based on:
    - Patient sex (M, F, or ANY)
    - Patient age (in days)
    - Facility (if applicable)
    """
    # Calculate age in days if date_of_birth provided
    patient_age_days = None
    if request.patient.date_of_birth:
        patient_age_days = calculate_age_in_days(request.patient.date_of_birth)
    
    result = get_unified_reference_range(
        db=db,
        field_code=request.field_code,
        test_id=request.test_id,
        test_name=request.test_name,
        patient_age_days=patient_age_days,
        patient_sex=request.patient.sex,
        facility_id=request.patient.facility_id
    )
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No reference range found for field '{request.field_code or request.test_name}'"
        )
    
    return ReferenceRangeResponse(
        low=float(result.low) if result.low else None,
        high=float(result.high) if result.high else None,
        critical_low=float(result.critical_low) if result.critical_low else None,
        critical_high=float(result.critical_high) if result.critical_high else None,
        unit=result.unit,
        text_range=result.text_range,
        interpretation=result.interpretation,
        source_table=result.source_table,
        range_id=str(result.range_id) if result.range_id else None,
        is_fallback=result.is_fallback
    )


@router.post("/reference-ranges/merge", response_model=ReferenceRangeMergeResponse)
def merge_reference_range(
    request: ReferenceRangeMergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Lab Scientist"]))
):
    """
    Create or update a reference range.
    
    For new ranges, leave id empty.
    For updates, specify the range id.
    """
    # Check if range already exists
    existing = db.query(LabReferenceRange).filter(
        LabReferenceRange.field_code == request.field_code,
        LabReferenceRange.sex == request.sex,
        LabReferenceRange.age_min_days == request.age_min_days,
        LabReferenceRange.age_max_days == request.age_max_days,
        LabReferenceRange.facility_id == request.facility_id
    ).first()
    
    if existing:
        # Update existing
        if request.low is not None:
            existing.low = Decimal(str(request.low))
        if request.high is not None:
            existing.high = Decimal(str(request.high))
        if request.critical_low is not None:
            existing.critical_low = Decimal(str(request.critical_low))
        if request.critical_high is not None:
            existing.critical_high = Decimal(str(request.critical_high))
        if request.unit:
            existing.unit = request.unit
        if request.text_range:
            existing.text_range = request.text_range
        
        db.commit()
        db.refresh(existing)
        
        return ReferenceRangeMergeResponse(
            range_id=str(existing.id),
            message="Reference range updated successfully"
        )
    else:
        # Create new
        new_range = LabReferenceRange(
            field_code=request.field_code,
            sex=request.sex,
            age_min_days=request.age_min_days,
            age_max_days=request.age_max_days,
            low=Decimal(str(request.low)) if request.low else None,
            high=Decimal(str(request.high)) if request.high else None,
            critical_low=Decimal(str(request.critical_low)) if request.critical_low else None,
            critical_high=Decimal(str(request.critical_high)) if request.critical_high else None,
            unit=request.unit,
            text_range=request.text_range,
            facility_id=request.facility_id
        )
        db.add(new_range)
        db.commit()
        db.refresh(new_range)
        
        return ReferenceRangeMergeResponse(
            range_id=str(new_range.id),
            message="Reference range created successfully"
        )


# ============= Result Interpretation Endpoints =============

@router.post("/results/interpret", response_model=ResultInterpretationResponse)
def interpret_results(
    request: ResultInterpretationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Lab Staff", "Doctor", "Nurse"]))
):
    """
    Interpret lab results and auto-flag based on reference ranges.
    
    Returns interpreted results with flags:
    - LOW: Below normal range
    - NORMAL: Within normal range
    - HIGH: Above normal range
    - CRITICAL_LOW: Below critical threshold
    - CRITICAL_HIGH: Above critical threshold
    """
    # Calculate age in days
    patient_age_days = None
    if request.patient.date_of_birth:
        patient_age_days = calculate_age_in_days(request.patient.date_of_birth)
    
    result = interpret_results_batch(
        db=db,
        results=request.results,
        patient_age_days=patient_age_days,
        patient_sex=request.patient.sex,
        template_fields=request.template_fields
    )
    
    return ResultInterpretationResponse(
        interpreted_results=result["interpreted_results"],
        flags=result["flags"]
    )


@router.post("/results/override-flag")
def override_result_flag(
    request: FlagOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Lab Scientist"]))
):
    """
    Override a result flag with audit logging.
    
    Only Lab Scientist, Senior Lab Scientist, and Admin roles can override flags.
    All overrides are logged for audit purposes.
    """
    # Check role permission
    user_role = current_user.role.name if current_user.role else "Guest"
    if not can_override_flag(user_role):
        raise HTTPException(
            status_code=403,
            detail=f"Role '{user_role}' is not authorized to override flags"
        )
    
    # Log the override
    log_reference_range_override(
        db=db,
        entity_type="lab_order",
        entity_id=str(request.lab_order_id),
        field_code=request.field_code,
        original_flag=request.original_flag,
        new_flag=request.new_flag,
        override_note=request.override_note,
        user_id=current_user.id
    )
    
    return {
        "success": True,
        "message": "Flag override logged successfully",
        "overridden_by": current_user.username,
        "user_role": user_role
    }


# ============= Test Template Endpoints =============

@router.get("/tests/{test_id}/template")
def get_test_template(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Lab Staff", "Doctor", "Nurse"]))
):
    """
    Get the template and reference ranges for a specific test.
    
    Returns:
    - Test details
    - Template schema (if available)
    - Reference ranges
    """
    # Get test
    test = db.query(LabTest).filter(LabTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Get template if linked
    template = None
    template_version = None
    if test.template_id:
        template = db.query(LabTemplate).filter(LabTemplate.id == test.template_id).first()
        if template and template.current_version:
            template_version = db.query(LabTemplateVersion).filter(
                LabTemplateVersion.template_id == template.id,
                LabTemplateVersion.version == template.current_version,
                LabTemplateVersion.status == "PUBLISHED"
            ).first()
    
    # Get reference ranges
    ref_ranges = db.query(LabReferenceRange).filter(
        LabReferenceRange.field_code.in_(
            [f["code"] for f in template_version.schema_json.get("fields", {}).values()] 
            if template_version else []
        )
    ).all()
    
    return {
        "test": {
            "id": test.id,
            "test_name": test.test_name,
            "test_code": test.test_code,
            "test_category": test.test_category,
            "test_type": test.test_type,
            "specimen_type": test.specimen_type,
            "description": test.description
        },
        "template": {
            "id": str(template.id) if template else None,
            "name": template.name if template else None,
            "discipline": template.discipline if template else None,
            "version": template.current_version if template else None,
            "schema_json": template_version.schema_json if template_version else None
        } if template else None,
        "reference_ranges": [
            {
                "field_code": rr.field_code,
                "sex": rr.sex,
                "age_min_days": rr.age_min_days,
                "age_max_days": rr.age_max_days,
                "low": float(rr.low) if rr.low else None,
                "high": float(rr.high) if rr.high else None,
                "critical_low": float(rr.critical_low) if rr.critical_low else None,
                "critical_high": float(rr.critical_high) if rr.critical_high else None,
                "unit": rr.unit,
                "text_range": rr.text_range
            }
            for rr in ref_ranges
        ]
    }


@router.post("/tests/merge", response_model=TestMergeResponse)
def merge_test(
    request: TestMergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Lab Scientist"]))
):
    """
    Create or update a test with template and reference ranges.
    
    This endpoint unifies:
    - Lab test creation
    - Template creation
    - Reference range population
    """
    # Check if test exists
    existing_test = None
    if request.test_code:
        existing_test = db.query(LabTest).filter(
            LabTest.test_code == request.test_code
        ).first()
    
    if existing_test:
        # Update test
        existing_test.test_name = request.test_name
        existing_test.test_category = request.test_category
        existing_test.test_type = request.discipline
        db.commit()
        db.refresh(existing_test)
        test_id = existing_test.id
        message = "Test updated successfully"
    else:
        # Create test
        new_test = LabTest(
            test_name=request.test_name,
            test_code=request.test_code,
            test_category=request.test_category,
            test_type=request.discipline,
            template_id=None
        )
        db.add(new_test)
        db.commit()
        db.refresh(new_test)
        test_id = new_test.id
        message = "Test created successfully"
    
    # Create or update template
    template = db.query(LabTemplate).filter(
        LabTemplate.discipline == request.discipline,
        LabTemplate.name == request.test_name
    ).first()
    
    if not template:
        # Create new template
        template = LabTemplate(
            name=request.test_name,
            discipline=request.discipline,
            status="DRAFT",
            created_by_id=current_user.id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
    
    # Create initial version
    template_version = LabTemplateVersion(
        template_id=template.id,
        version=1,
        status="DRAFT",
        schema_json=request.template_schema,
        created_by_id=current_user.id
    )
    db.add(template_version)
    db.commit()
    
    # Create reference ranges
    created_ranges = 0
    for rr_data in request.reference_ranges:
        rr = LabReferenceRange(
            field_code=rr_data.get("field_code", ""),
            sex=rr_data.get("sex", "ANY"),
            age_min_days=rr_data.get("age_min_days"),
            age_max_days=rr_data.get("age_max_days"),
            low=Decimal(str(rr_data["low"])) if rr_data.get("low") else None,
            high=Decimal(str(rr_data["high"])) if rr_data.get("high") else None,
            critical_low=Decimal(str(rr_data["critical_low"])) if rr_data.get("critical_low") else None,
            critical_high=Decimal(str(rr_data["critical_high"])) if rr_data.get("critical_high") else None,
            unit=rr_data.get("unit"),
            text_range=rr_data.get("text_range")
        )
        db.add(rr)
        created_ranges += 1
    
    db.commit()
    
    return TestMergeResponse(
        test_id=test_id,
        template_id=str(template.id),
        message=f"{message}. Created template with {created_ranges} reference ranges."
    )


# ============= Validation Endpoints =============

@router.get("/tests/validate-applicability")
def validate_test_applicability_endpoint(
    test_category: str = Query(..., description="Test category/name"),
    date_of_birth: date = Query(..., description="Patient date of birth"),
    sex: str = Query("ANY", description="Patient sex"),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Lab Staff", "Doctor", "Nurse"]))
):
    """
    Validate if a test is applicable for a patient.
    
    Returns:
    - is_applicable: Whether test is appropriate
    - warnings: List of warnings
    - age_bracket: Patient's age bracket
    """
    age_days = calculate_age_in_days(date_of_birth)
    
    result = validate_test_applicability(
        test_category=test_category,
        patient_age_days=age_days,
        patient_sex=sex
    )
    
    return result
