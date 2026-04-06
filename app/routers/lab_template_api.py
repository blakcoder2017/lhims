"""Lab Template Management API - Admin/Lab Manager only"""
from datetime import datetime
from uuid import UUID
import random
from fastapi import APIRouter, Body, Depends, Form, HTTPException, Request, status, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.deps import role_required
from app.core.templates import templates
from app.crud import lab_template_crud
from app.services.lab_template_schema import validate_template_schema
from app.models.lab_template_models import LabTemplate, LabTemplateVersion

router = APIRouter(prefix="/lab/templates", tags=["Lab Templates"])


@router.get("/disciplines", name="lab_templates_disciplines")
def list_disciplines(
    db: Session = Depends(get_db),
):
    """Get all unique disciplines from templates."""
    disciplines = lab_template_crud.get_all_disciplines(db)
    return {"disciplines": disciplines}


@router.get("/", name="lab_templates_list")
def list_templates(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Staff"])),
    discipline: str | None = None,
    status_filter: str | None = None,
    q: str | None = Query(None, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=200, description="Items per page (max 200)"),
):
    """List lab templates with optional filters and pagination."""
    # Allow page_size=0 to show all
    if page_size == 0:
        page_size = 200
    
    template_list, total = lab_template_crud.search_templates(
        db, query=q, discipline=discipline, status=status_filter,
        include_deleted=False, page=page, page_size=page_size
    )
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1
    
    # Get all unique disciplines for the filter dropdown
    all_disciplines = lab_template_crud.get_all_disciplines(db)
    
    return templates.TemplateResponse(
        "lab/templates_list.html",
        {
            "request": request,
            "templates": template_list,
            "discipline": discipline,
            "status_filter": status_filter,
            "search_query": q,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "all_disciplines": all_disciplines,
            "current_user": current_user,
            "user_role": current_user.role.name if current_user.role else "Guest",
        },
    )


@router.get("/new", name="lab_template_new")
def new_template_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
):
    """Create new template page."""
    return templates.TemplateResponse(
        "lab/template_new.html",
        {
            "request": request,
            "current_user": current_user,
            "user_role": current_user.role.name if current_user.role else "Guest",
        },
    )


@router.post("", name="lab_template_create", status_code=status.HTTP_302_FOUND)
def create_template(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
    name: str = Form(...),
    discipline: str = Form(...),
):
    """Create template with initial draft schema."""
    from fastapi.responses import RedirectResponse
    schema_json = {
        "meta": {"name": name, "discipline": discipline, "version": 1},
        "layout": {"sections": [{"id": "sec_main", "title": "Results", "rows": [{"columns": [{"width": 12, "items": []}]}]}]},
        "fields": {},
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": [],
    }
    valid, errors = validate_template_schema(schema_json)
    if not valid:
        raise HTTPException(status_code=400, detail={"errors": errors})
    tmpl = lab_template_crud.create_template(db, name, discipline, current_user.id, schema_json)
    return RedirectResponse(url=f"/lab/templates/{tmpl.id}", status_code=302)


@router.get("/{template_id}", name="lab_template_builder")
def template_builder(
    request: Request,
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
):
    """Template builder page - loads latest draft."""
    tmpl = lab_template_crud.get_template(db, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    draft = lab_template_crud.get_draft_version(db, template_id)
    schema = draft.schema_json if draft else {}
    return templates.TemplateResponse(
        "lab/template_builder.html",
        {
            "request": request,
            "template": tmpl,
            "schema_json": schema,
            "current_user": current_user,
            "user_role": current_user.role.name if current_user.role else "Guest",
        },
    )


@router.get("/{template_id}/visual", name="lab_template_builder_visual")
def template_builder_visual(
    request: Request,
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
):
    """Visual template builder page - drag and drop interface."""
    tmpl = lab_template_crud.get_template(db, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    draft = lab_template_crud.get_draft_version(db, template_id)
    schema = draft.schema_json if draft else {}
    return templates.TemplateResponse(
        "lab/template_builder_visual.html",
        {
            "request": request,
            "template": tmpl,
            "schema_json": schema,
            "current_user": current_user,
            "user_role": current_user.role.name if current_user.role else "Guest",
        },
    )


@router.put("/{template_id}/draft", name="lab_template_save_draft")
def save_draft(
    template_id: UUID,
    schema_json: dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
):
    """Save draft schema (JSON body)."""
    tmpl = lab_template_crud.get_template(db, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    valid, errors = validate_template_schema(schema_json)
    if not valid:
        raise HTTPException(status_code=400, detail={"errors": errors})
    lab_template_crud.save_draft(db, template_id, schema_json, current_user.id)
    return {"status": "ok"}


@router.get("/{template_id}/versions/{version}", name="lab_template_version_detail")
def get_version_detail(
    request: Request,
    template_id: UUID,
    version: int,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Staff"])),
):
    """Get a specific version of a template (published or draft)."""
    from app.crud import lab_template_crud
    
    # First try to find published version
    ver = lab_template_crud.get_published_version(db, template_id, version=version)
    
    # If not found, check if it's a draft version
    if not ver:
        ver = db.query(LabTemplateVersion).filter(
            LabTemplateVersion.template_id == template_id,
            LabTemplateVersion.version == version,
            LabTemplateVersion.status == "DRAFT"
        ).first()
    
    if not ver:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Verify checksum if this is a published version
    checksum_valid = None
    if ver.status == "PUBLISHED" and ver.checksum:
        from app.crud.lab_template_crud import _compute_checksum
        computed = _compute_checksum(ver.schema_json)
        checksum_valid = (computed == ver.checksum)
    
    return {
        "id": str(ver.id),
        "template_id": str(ver.template_id),
        "version": ver.version,
        "status": ver.status,
        "schema_json": ver.schema_json,
        "change_note": ver.change_note,
        "checksum": ver.checksum,
        "checksum_valid": checksum_valid,
        "created_by_id": ver.created_by_id,
        "created_at": ver.created_at.isoformat() if ver.created_at else None
    }


@router.get("/{template_id}/resolve", name="lab_template_resolve")
def resolve_template(
    template_id: UUID,
    version: str | None = Query(None, description="Template version number"),
    db: Session = Depends(get_db),
    validate_checksum: bool = True,
):
    """Resolve template schema - returns published version (specific or latest)."""
    # Convert version string to int if provided
    version_int = None
    if version and version.strip():
        try:
            version_int = int(version)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid version format")
    
    pub = lab_template_crud.get_published_version(db, template_id, version=version_int)
    if not pub:
        raise HTTPException(status_code=404, detail="Published template version not found")
    
    # Optionally validate checksum
    checksum_valid = True
    if validate_checksum and pub.checksum:
        from app.crud.lab_template_crud import _compute_checksum
        computed = _compute_checksum(pub.schema_json)
        checksum_valid = (computed == pub.checksum)
    
    return {
        "schema_json": pub.schema_json, 
        "version": pub.version,
        "checksum": pub.checksum,
        "checksum_valid": checksum_valid
    }


@router.get("/{template_id}/preview", name="lab_template_preview")
def template_preview(
    request: Request,
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Staff"])),
    version: str | None = Query(None, description="Template version number"),
    age_days: str | None = Query(None, description="Age in days"),
    age_years: str | None = Query(None, description="Age in years"),
    sex: str | None = Query(None, description="Patient sex (M/F/ANY)"),
):
    """Preview template with simulated patient context. Renders form with ref ranges and highlights abnormal/critical."""
    # Convert query params from strings to appropriate types
    version_int = None
    if version and version.strip():
        try:
            version_int = int(version)
        except ValueError:
            pass  # Use latest version if invalid
    
    age_days_int = None
    if age_days and age_days.strip():
        try:
            age_days_int = int(age_days)
        except ValueError:
            pass
    
    age_years_int = None
    if age_years and age_years.strip():
        try:
            age_years_int = int(age_years)
        except ValueError:
            pass
    
    # Use the converted values
    sex_value = sex.strip() if sex and sex.strip() else None
    
    pub = lab_template_crud.get_published_version(db, template_id, version=version_int)
    if not pub:
        raise HTTPException(status_code=404, detail="Published template not found")
    schema_json = pub.schema_json
    
    # Make a deep copy to avoid mutating the original and handle format conversion
    import copy
    schema_json = copy.deepcopy(schema_json)
    
    # Handle both list format and dict format
    if isinstance(schema_json, list):
        # Convert list to dict format
        fields_dict = {}
        for fld in schema_json:
            if isinstance(fld, dict):
                field_id = fld.get('field_name') or fld.get('code') or fld.get('id')
                if field_id:
                    fields_dict[field_id] = fld
        schema_json = {
            "layout": {"sections": [{"title": "Results", "rows": [{"columns": [{"width": 12, "items": list(fields_dict.keys())}]}]}]},
            "fields": fields_dict,
            "rules": {"visibility": []},
            "calculated": []
        }
    elif isinstance(schema_json, dict):
        # Ensure dict format has required keys
        if "layout" not in schema_json:
            schema_json["layout"] = {"sections": []}
        if "fields" not in schema_json:
            schema_json["fields"] = {}
        if "rules" not in schema_json:
            schema_json["rules"] = {"visibility": []}
        if "calculated" not in schema_json:
            schema_json["calculated"] = []
        # Convert fields from list to dict if needed
        if isinstance(schema_json.get("fields"), list):
            fields_dict = {}
            for fld in schema_json["fields"]:
                if isinstance(fld, dict):
                    field_id = fld.get('field_name') or fld.get('code') or fld.get('id')
                    if field_id:
                        fields_dict[field_id] = fld
            schema_json["fields"] = fields_dict
    else:
        schema_json = None
    
    ad = age_days_int
    if ad is None and age_years_int is not None:
        ad = age_years_int * 365
    ref_ranges = {}
    for fdef in (schema_json.get("fields") or {}).values():
        if fdef.get("type") == "numeric":
            rr = lab_template_crud.get_reference_range(db, fdef.get("code"), sex_value or "ANY", ad)
            # Handle both numeric ranges and text-based interpretations
            if rr:
                # Include text_range if available (for interpretation-based ranges like CRP)
                if rr.text_range:
                    ref_ranges[fdef.get("code")] = {"low": None, "high": None, "text_range": rr.text_range, "unit": rr.unit or ""}
                # Only add numeric ranges when low or high is defined
                elif rr.low is not None or rr.high is not None:
                    ref_ranges[fdef.get("code")] = {"low": float(rr.low or 0), "high": float(rr.high or 0)}
    option_sets = {}
    for fld in (schema_json.get("fields") or {}).values():
        os_c = fld.get("optionSet")
        if os_c:
            os_obj = lab_template_crud.get_option_set(db, os_c)
            option_sets[os_c] = (os_obj.options_json or []) if os_obj else []
    has_critical = any(f.get("critical") for f in (schema_json.get("fields") or {}).values())
    return templates.TemplateResponse(
        "lab/template_preview.html",
        {
            "request": request,
            "template": lab_template_crud.get_template(db, template_id),
            "schema_json": schema_json,
            "ref_ranges": ref_ranges,
            "option_sets": option_sets,
            "has_critical_fields": has_critical,
            "simulated_age_days": ad,
            "simulated_sex": sex_value or "ANY",
            "result_json": {},
            "current_user": current_user,
            "user_role": current_user.role.name if current_user.role else "Guest",
            "now": datetime.now(),
        },
    )


@router.get("/{template_id}/preview/enhanced", name="lab_template_preview_enhanced")
def template_preview_enhanced(
    request: Request,
    template_id: UUID,
    db: Session = Depends(get_db),
    # Make enhanced preview accessible without authentication for testing
    current_user=None,
    version: str | None = Query(None, description="Template version number"),
    age_days: str | None = Query(None, description="Age in days"),
    age_years: str | None = Query(None, description="Age in years"),
    sex: str | None = Query(None, description="Patient sex (M/F/ANY)"),
    gestational_age: str | None = Query(None, description="Gestational age in weeks"),
    result_type: str | None = Query(None, description="Result type: normal, abnormal"),
):
    """Enhanced preview with auto-fill, print and PDF export features using official print template."""
    from datetime import datetime
    
    # Convert query params
    version_int = None
    if version and version.strip():
        try:
            version_int = int(version)
        except ValueError:
            pass
    
    age_days_int = None
    if age_days and age_days.strip():
        try:
            age_days_int = int(age_days)
        except ValueError:
            pass
    
    age_years_int = None
    if age_years and age_years.strip():
        try:
            age_years_int = int(age_years)
        except ValueError:
            pass
    
    gestational_age_int = None
    if gestational_age and gestational_age.strip():
        try:
            gestational_age_int = int(gestational_age)
        except ValueError:
            pass
    
    sex_value = sex.strip() if sex and sex.strip() else None
    
    # Get the template
    template = lab_template_crud.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    pub = lab_template_crud.get_published_version(db, template_id, version=version_int)
    if not pub:
        raise HTTPException(status_code=404, detail="Published template not found")
    schema_json = pub.schema_json
    
    import copy
    schema_json = copy.deepcopy(schema_json)
    
    # Handle both list and dict formats
    if isinstance(schema_json, list):
        fields_dict = {}
        for fld in schema_json:
            if isinstance(fld, dict):
                field_id = fld.get('field_name') or fld.get('code') or fld.get('id')
                if field_id:
                    fields_dict[field_id] = fld
        schema_json = {
            "layout": {"sections": [{"title": "Results", "rows": [{"columns": [{"width": 12, "items": list(fields_dict.keys())}]}]}]},
            "fields": fields_dict,
            "rules": {"visibility": []},
            "calculated": []
        }
    elif isinstance(schema_json, dict):
        # Ensure layout exists
        if "layout" not in schema_json:
            schema_json["layout"] = {"sections": []}
    else:
        schema_json = {"layout": {"sections": []}, "fields": {}, "rules": {"visibility": []}, "calculated": []}
    
    # Calculate age in days
    ad = age_days_int
    if not ad and age_years_int:
        ad = age_years_int * 365
    
    # Get reference ranges with age/sex/gender awareness
    ref_ranges = {}
    for fcode, fdef in (schema_json.get("fields") or {}).items():
        rr = lab_template_crud.get_reference_range_for_patient(
            db, template_id=template_id, 
            field_code=fcode, 
            age_days=ad, 
            sex=sex_value,
            gestational_age_weeks=gestational_age_int
        )
        # Handle reference ranges - support both numeric ranges and text-based interpretations
        if rr:
            # Always include text_range if available (for interpretation-based ranges)
            ref_range = {"low": None, "high": None, "unit": rr.unit or "", "text_range": rr.text_range}
            # Also add numeric ranges when both low and high are defined
            if rr.low is not None and rr.high is not None:
                ref_range["low"] = float(rr.low or 0)
                ref_range["high"] = float(rr.high or 0)
            # Add critical values from field definition if available
            if fdef.get("critical"):
                if isinstance(fdef.get("critical"), dict):
                    ref_range["critical_low"] = fdef.get("critical").get("low")
                    ref_range["critical_high"] = fdef.get("critical").get("high")
                elif hasattr(fdef.get("critical"), "low") and hasattr(fdef.get("critical"), "high"):
                    ref_range["critical_low"] = fdef.get("critical").low
                    ref_range["critical_high"] = fdef.get("critical").high
            ref_ranges[fcode] = ref_range
        # Also check for reference_range in field definition (template schema)
        if fcode not in ref_ranges and fdef.get("reference_range"):
            ref_ranges[fcode] = {"low": None, "high": None, "unit": fdef.get("unit", ""), "text_range": fdef.get("reference_range")}
    
    # Generate sample results from schema for preview
    sample_results = {}
    sample_flags = {}
    if schema_json and isinstance(schema_json, dict):
        fields = schema_json.get('fields', {})
        for field_code, field_def in fields.items():
            # Get default value or generate based on field type
            default_val = field_def.get('default_value') or field_def.get('default')
            if default_val is not None:
                sample_results[field_code] = default_val
            else:
                # Always generate a sample value for all fields
                field_type = field_def.get('field_type') or field_def.get('type') or ''
                
                # Check if it's numeric
                if field_type == 'numeric' or field_type == 'number' or field_type == 'integer':
                    # Generate a sample numeric value based on reference range and result_type
                    low = ref_ranges.get(field_code, {}).get('low', 0)
                    high = ref_ranges.get(field_code, {}).get('high', 100)
                    critical_low = ref_ranges.get(field_code, {}).get('critical_low')
                    critical_high = ref_ranges.get(field_code, {}).get('critical_high')
                    
                    if result_type == 'abnormal':
                        # Generate abnormal value (outside normal range)
                        if low is not None and high is not None and low < high:
                            range_size = high - low
                            if critical_low is not None and critical_high is not None:
                                if random.random() > 0.5:
                                    sample_results[field_code] = round(high + (range_size * 0.3), 1)
                                else:
                                    sample_results[field_code] = round(low - (range_size * 0.3), 1)
                            else:
                                if random.random() > 0.5:
                                    sample_results[field_code] = round(high + (range_size * 0.2), 1)
                                else:
                                    sample_results[field_code] = round(low - (range_size * 0.2), 1)
                        else:
                            sample_results[field_code] = 50.0
                    else:
                        # Generate normal value (within reference range)
                        if low is not None and high is not None and low < high:
                            sample_results[field_code] = round((low + high) / 2, 1)
                        else:
                            sample_results[field_code] = 50.0
                else:
                    # Generate sample value for non-numeric fields
                    options = field_def.get('options') or []
                    option_set = field_def.get('optionSet')
                    field_name = (field_def.get('label') or field_def.get('name') or field_code or '').lower()
                    
                    if options and len(options) > 0:
                        if result_type == 'abnormal':
                            sample_results[field_code] = options[len(options)-1] if len(options) > 1 else options[0]
                        else:
                            sample_results[field_code] = options[0]
                    elif option_set:
                        sample_results[field_code] = "Present" if result_type == 'abnormal' else "Not Seen"
                    elif 'gametocyte' in field_name:
                        sample_results[field_code] = "Seen" if result_type == 'abnormal' else "Not Seen"
                    elif 'trophozoite' in field_name or 'count' in field_name:
                        sample_results[field_code] = "15-20" if result_type == 'abnormal' else "1-5"
                    elif 'note' in field_name or 'comment' in field_name:
                        sample_results[field_code] = "Abnormal findings noted." if result_type == 'abnormal' else "Results normal."
                    elif 'species' in field_name or 'specie' in field_name:
                        sample_results[field_code] = "P. falciparum"
                    elif 'negative' in field_name or 'positive' in field_name:
                        sample_results[field_code] = "Positive" if result_type == 'abnormal' else "Negative"
                    else:
                        # Default value based on result_type
                        sample_results[field_code] = "Abnormal" if result_type == 'abnormal' else "Normal"
    
    # Create a mock lab_order for preview using the official print template
    class MockLabOrder:
        def __init__(self, template, schema_json):
            self.id = 0  # Preview mode
            self.test_name = template.name or "Lab Test"
            # Get test code from schema_json if available, otherwise use template discipline
            test_code = None
            if schema_json and isinstance(schema_json, dict):
                test_code = schema_json.get('code') or schema_json.get('test_code')
            self.test_code = test_code or template.discipline or "PREVIEW"
            self.status = "COMPLETED"
            self.result_json = sample_results
            self.flags_json = sample_flags
            self.reference_ranges_json = ref_ranges
            self.result_entered_at = datetime.now()
            self.ordered_at = datetime.now()
            self.result_status = "COMPLETED"
            self.template_id = template.id
            self.lab_test_id = None
            self.encounter = None
            self.patient_id = None
            self.ordered_by = current_user if current_user else None
            self.result_entered_by = current_user if current_user else None
            self.samples = []
    
    # Create a mock patient for preview
    class MockPatient:
        def __init__(self):
            self.id = 0
            self.first_name = "Preview"
            self.last_name = "Patient"
            self.full_name = "Preview Patient"
            self.date_of_birth = None
            self.age_years = age_years_int or 0
            self.age_days = ad or 0
            self.sex = sex_value or "M"
            self.gender = sex_value or "M"
            self.phone_number = "N/A (Preview)"
            self.address = "Preview Mode"
            self.patient_id = "PREVIEW-001"
            self.patient_number = "PREVIEW-001"
    
    # Create mock hospital settings
    class MockHospitalSettings:
        def __init__(self):
            self.hospital_name = "Preview Hospital"
            self.hospital_address = "Preview Mode"
            self.hospital_phone = "N/A"
            self.hospital_email = "preview@hospital.com"
            self.logo_url = None
            self.accreditation = None
            self.accreditation_number = None
    
    mock_lab_order = MockLabOrder(template, schema_json)
    mock_patient = MockPatient()
    mock_hospital_settings = MockHospitalSettings()
    
    return templates.TemplateResponse(
        "lab/print_lab_result.html",
        {
            "request": request,
            "lab_order": mock_lab_order,
            "patient": mock_patient,
            "result_json": sample_results,
            "flags_json": sample_flags,
            "schema_json": schema_json,
            "ref_ranges": ref_ranges,
            "hospital_settings": mock_hospital_settings,
            "samples": [],
            "now": datetime.now(),
            "turnaround_time": "Preview",
            "result_entered_by": current_user if current_user else None,
            "is_preview": True,
            "result_type": result_type or "normal",
        },
    )


@router.get("/{template_id}/versions", name="lab_template_versions")
def list_versions(
    request: Request,
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Staff"])),
):
    """List template versions."""
    tmpl = lab_template_crud.get_template(db, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    versions = lab_template_crud.get_template_versions(db, template_id)
    return templates.TemplateResponse(
        "lab/template_versions.html",
        {
            "request": request,
            "template": tmpl,
            "versions": versions,
            "current_user": current_user,
            "user_role": current_user.role.name if current_user.role else "Guest",
        },
    )


@router.post("/{template_id}/publish", name="lab_template_publish", status_code=status.HTTP_302_FOUND)
def publish_template(
    request: Request,
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
    change_note: str = Form(None),
):
    """Publish draft - validate and create published version."""
    from fastapi.responses import RedirectResponse
    tmpl = lab_template_crud.get_template(db, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    draft = lab_template_crud.get_draft_version(db, template_id)
    if not draft:
        raise HTTPException(status_code=400, detail="No draft to publish")
    valid, errors = validate_template_schema(draft.schema_json)
    if not valid:
        return RedirectResponse(
            url=f"/lab/templates/{template_id}?error=" + ",".join(errors[:3]),
            status_code=302
        )
    lab_template_crud.publish_version(db, template_id, change_note=change_note, created_by_id=current_user.id)
    return RedirectResponse(url=f"/lab/templates/{template_id}?published=1", status_code=302)


@router.post("/{template_id}/archive", name="lab_template_archive", status_code=status.HTTP_302_FOUND)
def archive_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
):
    from fastapi.responses import RedirectResponse
    lab_template_crud.archive_template(db, template_id)
    return RedirectResponse(url="/lab/templates", status_code=302)


# ============== Template Document Upload Endpoints ==============

import os
import uuid as uuid_module
from pathlib import Path
from fastapi import UploadFile, File
from fastapi.responses import FileResponse


# Configure upload directory
UPLOAD_DIR = Path("lab_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/{template_id}/documents", name="lab_template_upload_document")
async def upload_template_document(
    template_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    description: str = Form(None),
    category: str = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Staff"])),
):
    """Upload a document (SOP, form, instruction) to a template."""
    from app.models.lab_template_models import LabTemplateDocument
    
    # Verify template exists
    tmpl = lab_template_crud.get_template(db, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix or ".bin"
    unique_filename = f"{uuid_module.uuid4()}{file_ext}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    content = await file.read()
    file_path.write_bytes(content)
    
    # Create document record
    doc = LabTemplateDocument(
        template_id=template_id,
        filename=unique_filename,
        original_filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        file_size=len(content),
        file_path=str(file_path),
        description=description,
        category=category or "OTHER",
        uploaded_by_id=current_user.id,
    )
    db.add(doc)
    db.commit()
    
    return {
        "id": doc.id,
        "filename": doc.original_filename,
        "content_type": doc.content_type,
        "file_size": doc.file_size,
        "description": doc.description,
        "category": doc.category,
    }


@router.get("/{template_id}/documents", name="lab_template_list_documents")
def list_template_documents(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Staff", "Doctor", "Nurse"])),
):
    """List all documents attached to a template."""
    from app.models.lab_template_models import LabTemplateDocument
    
    # Verify template exists
    tmpl = lab_template_crud.get_template(db, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    
    docs = db.query(LabTemplateDocument).filter(
        LabTemplateDocument.template_id == template_id,
        LabTemplateDocument.is_active == True
    ).order_by(LabTemplateDocument.created_at.desc()).all()
    
    return [
        {
            "id": d.id,
            "filename": d.original_filename,
            "content_type": d.content_type,
            "file_size": d.file_size,
            "description": d.description,
            "category": d.category,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@router.get("/{template_id}/documents/{document_id}/download", name="lab_template_download_document")
def download_template_document(
    template_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Staff", "Doctor", "Nurse"])),
):
    """Download a document from a template."""
    from app.models.lab_template_models import LabTemplateDocument
    
    doc = db.query(LabTemplateDocument).filter(
        LabTemplateDocument.id == document_id,
        LabTemplateDocument.template_id == template_id,
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not Path(doc.file_path).exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return FileResponse(
        path=doc.file_path,
        filename=doc.original_filename,
        media_type=doc.content_type,
    )


@router.delete("/{template_id}/documents/{document_id}", name="lab_template_delete_document")
def delete_template_document(
    template_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
):
    """Delete (deactivate) a document from a template."""
    from app.models.lab_template_models import LabTemplateDocument
    
    doc = db.query(LabTemplateDocument).filter(
        LabTemplateDocument.id == document_id,
        LabTemplateDocument.template_id == template_id,
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Soft delete
    doc.is_active = False
    db.commit()
    
    return {"message": "Document deleted successfully"}


# ============== Search and Pagination ==============

@router.get("/search", name="lab_templates_search")
def search_templates(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Staff"])),
    q: str | None = Query(None, description="Search query (template name)"),
    discipline: str | None = Query(None, description="Filter by discipline"),
    status_filter: str | None = Query(None, description="Filter by status"),
    include_deleted: bool = Query(False, description="Include deleted templates"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """Search templates with filters and pagination."""
    templates, total = lab_template_crud.search_templates(
        db, query=q, discipline=discipline, status=status_filter,
        include_deleted=include_deleted, page=page, page_size=page_size
    )
    total_pages = (total + page_size - 1) // page_size
    return templates.TemplateResponse(
        "lab/templates_list.html",
        {
            "request": request,
            "templates": templates,
            "search_query": q,
            "discipline": discipline,
            "status_filter": status_filter,
            "include_deleted": include_deleted,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "current_user": current_user,
            "user_role": current_user.role.name if current_user.role else "Guest",
        },
    )


# ============== Template Cloning ==============

@router.get("/{template_id}/clone", name="lab_template_clone_page")
def clone_template_page(
    request: Request,
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
):
    """Page to clone a template."""
    tmpl = lab_template_crud.get_template(db, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return templates.TemplateResponse(
        "lab/template_clone.html",
        {
            "request": request,
            "template": tmpl,
            "current_user": current_user,
            "user_role": current_user.role.name if current_user.role else "Guest",
        },
    )


@router.post("/{template_id}/clone", name="lab_template_clone", status_code=status.HTTP_302_FOUND)
def clone_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
    name: str = Form(...),
    discipline: str = Form(...),
):
    """Clone an existing template."""
    from fastapi.responses import RedirectResponse
    new_tmpl = lab_template_crud.clone_template(db, template_id, name, discipline, current_user.id)
    if not new_tmpl:
        raise HTTPException(status_code=400, detail="Failed to clone template")
    return RedirectResponse(url=f"/lab/templates/{new_tmpl.id}", status_code=302)


# ============== Template Export/Import ==============

@router.get("/{template_id}/export", name="lab_template_export")
def export_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
):
    """Export template as JSON."""
    data = lab_template_crud.export_template(db, template_id)
    if not data:
        raise HTTPException(status_code=404, detail="Template not found")
    from fastapi.responses import JSONResponse
    return JSONResponse(content=data)


@router.get("/import", name="lab_template_import_page")
def import_template_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
):
    """Page to import a template."""
    return templates.TemplateResponse(
        "lab/template_import.html",
        {
            "request": request,
            "current_user": current_user,
            "user_role": current_user.role.name if current_user.role else "Guest",
        },
    )


@router.post("/import", name="lab_template_import", status_code=status.HTTP_302_FOUND)
def import_template(
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
):
    """Import template from JSON."""
    from fastapi.responses import RedirectResponse
    from fastapi import UploadFile, File
    import json
    
    # Note: This would need file upload handling - simplified version
    raise HTTPException(status_code=501, detail="Import endpoint requires file upload handling")


# ============== Version Comparison ==============

@router.get("/{template_id}/compare", name="lab_template_compare")
def compare_versions(
    request: Request,
    template_id: UUID,
    v1: int = Query(..., description="First version number"),
    v2: int = Query(..., description="Second version number"),
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Staff"])),
):
    """Compare two versions of a template."""
    version1 = lab_template_crud.get_version(db, template_id, v1)
    version2 = lab_template_crud.get_version(db, template_id, v2)
    if not version1:
        raise HTTPException(status_code=404, detail=f"Version {v1} not found")
    if not version2:
        raise HTTPException(status_code=404, detail=f"Version {v2} not found")
    
    # Simple diff: compare field counts and checksums
    fields1 = version1.schema_json.get("fields", {}) if version1.schema_json else {}
    fields2 = version2.schema_json.get("fields", {}) if version2.schema_json else {}
    
    return {
        "template_id": str(template_id),
        "version1": {
            "version": v1,
            "status": version1.status,
            "field_count": len(fields1),
            "checksum": version1.checksum,
            "change_note": version1.change_note,
            "created_at": version1.created_at.isoformat() if version1.created_at else None,
        },
        "version2": {
            "version": v2,
            "status": version2.status,
            "field_count": len(fields2),
            "checksum": version2.checksum,
            "change_note": version2.change_note,
            "created_at": version2.created_at.isoformat() if version2.created_at else None,
        },
        "field_diff": {
            "added": list(set(fields2.keys()) - set(fields1.keys())),
            "removed": list(set(fields1.keys()) - set(fields2.keys())),
            "common": list(set(fields1.keys()) & set(fields2.keys())),
        },
    }


# ============== Bulk Operations ==============

@router.post("/bulk-archive", name="lab_templates_bulk_archive")
def bulk_archive_templates(
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
    template_ids: list[UUID] = Body(...),
):
    """Archive multiple templates."""
    count = lab_template_crud.bulk_archive_templates(db, template_ids)
    return {"archived_count": count, "message": f"Archived {count} templates"}


@router.post("/bulk-unarchive", name="lab_templates_bulk_unarchive")
def bulk_unarchive_templates(
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
    template_ids: list[UUID] = Body(...),
):
    """Unarchive multiple templates."""
    count = lab_template_crud.bulk_unarchive_templates(db, template_ids)
    return {"unarchived_count": count, "message": f"Unarchived {count} templates"}


# ============== Usage Analytics ==============

@router.get("/{template_id}/usage", name="lab_template_usage")
def get_template_usage(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Staff"])),
):
    """Get usage statistics for a template."""
    stats = lab_template_crud.get_template_usage_stats(db, template_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Template not found")
    return stats


@router.get("/analytics/most-used", name="lab_templates_most_used")
def get_most_used_templates(
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Staff"])),
    limit: int = Query(10, ge=1, le=50),
):
    """Get most used templates."""
    templates = lab_template_crud.get_most_used_templates(db, limit)
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "discipline": t.discipline,
            "status": t.status,
            "usage_count": t.usage_count or 0,
            "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
        }
        for t in templates
    ]


# ============== Soft Delete ==============

@router.post("/{template_id}/soft-delete", name="lab_template_soft_delete")
def soft_delete_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
):
    """Soft delete a template."""
    tmpl = lab_template_crud.soft_delete_template(db, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deleted successfully"}


@router.post("/{template_id}/restore", name="lab_template_restore")
def restore_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
):
    """Restore a soft-deleted template."""
    tmpl = lab_template_crud.restore_template(db, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Deleted template not found")
    return {"message": "Template restored successfully"}


@router.get("/deleted", name="lab_templates_deleted")
def list_deleted_templates(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
):
    """List all deleted templates."""
    templates = lab_template_crud.get_deleted_templates(db)
    return templates.TemplateResponse(
        "lab/templates_deleted.html",
        {
            "request": request,
            "templates": templates,
            "current_user": current_user,
            "user_role": current_user.role.name if current_user.role else "Guest",
        },
    )
