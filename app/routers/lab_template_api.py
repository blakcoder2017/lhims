"""Lab Template Management API - Admin/Lab Manager only"""
from uuid import UUID
from fastapi import APIRouter, Body, Depends, Form, HTTPException, Request, status, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.deps import role_required
from app.core.templates import templates
from app.crud import lab_template_crud
from app.services.lab_template_schema import validate_template_schema
from app.models.lab_template_models import LabTemplate, LabTemplateVersion

router = APIRouter(prefix="/lab/templates", tags=["Lab Templates"])


@router.get("", name="lab_templates_list")
def list_templates(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Lab Staff"])),
    discipline: str | None = None,
    status_filter: str | None = None,
):
    """List lab templates with optional filters."""
    tmpls = lab_template_crud.get_templates(db, discipline=discipline, status=status_filter)
    return templates.TemplateResponse(
        "lab/templates_list.html",
        {
            "request": request,
            "templates": tmpls,
            "discipline": discipline,
            "status_filter": status_filter,
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


@router.get("/lab/templates/{template_id}/versions/{version}", name="lab_template_version_detail")
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
    version: int | None = None,
    db: Session = Depends(get_db),
    validate_checksum: bool = True,
):
    """Resolve template schema - returns published version (specific or latest)."""
    pub = lab_template_crud.get_published_version(db, template_id, version=version)
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
    version: int | None = None,
    age_days: int | None = None,
    age_years: int | None = None,
    sex: str | None = None,
):
    """Preview template with simulated patient context. Renders form with ref ranges and highlights abnormal/critical."""
    pub = lab_template_crud.get_published_version(db, template_id, version=version)
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
    
    ad = age_days
    if ad is None and age_years is not None:
        ad = int(age_years) * 365
    ref_ranges = {}
    for fdef in (schema_json.get("fields") or {}).values():
        if fdef.get("type") == "numeric":
            rr = lab_template_crud.get_reference_range(db, fdef.get("code"), sex or "ANY", ad)
            if rr and (rr.low is not None or rr.high is not None):
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
            "simulated_sex": sex or "ANY",
            "result_json": {},
            "current_user": current_user,
            "user_role": current_user.role.name if current_user.role else "Guest",
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
