"""
Procedure API Routes

Routes for procedure management including CRUD operations.
"""
from fastapi import APIRouter, Depends, Request, Query, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.crud import procedure_crud
from app.schemas.procedure_schemas import ProcedureCreate, ProcedureUpdate, Procedure
from app.models.procedure_models import ProcedureType, ProcedureStatus
from app.services import create_charge_for_procedure

router = APIRouter(prefix="/procedures", tags=["Procedures"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", name="procedures_list")
def procedures_list(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    patient_id: Optional[int] = Query(None),
    encounter_id: Optional[int] = Query(None),
    procedure_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician"]))
):
    """List all procedures with filtering and pagination."""
    skip = (page - 1) * per_page
    
    # Parse procedure_type and status
    proc_type = None
    if procedure_type:
        try:
            proc_type = ProcedureType(procedure_type)
        except ValueError:
            pass
    
    proc_status = None
    if status:
        try:
            proc_status = ProcedureStatus(status)
        except ValueError:
            pass
    
    procedures, total_count = procedure_crud.get_procedures(
        db, skip=skip, limit=per_page,
        patient_id=patient_id,
        encounter_id=encounter_id,
        procedure_type=proc_type,
        status=proc_status
    )
    
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    context = {
        "request": request,
        "title": "Procedures Management",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "procedures": procedures,
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages,
        "patient_id": patient_id,
        "encounter_id": encounter_id,
        "procedure_type_filter": procedure_type,
        "status_filter": status,
        "procedure_types": [pt.value for pt in ProcedureType],
        "statuses": [stat.value for stat in ProcedureStatus]
    }
    return templates.TemplateResponse("procedures/procedures_list.html", context)


@router.get("/create", name="procedure_create_form")
def procedure_create_form(
    request: Request,
    patient_id: Optional[int] = Query(None),
    encounter_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor"]))
):
    """Form to create a new procedure."""
    from app.crud import patient_crud, encounter_crud
    
    patient = None
    encounter = None
    
    if patient_id:
        patient = patient_crud.get_patient(db, patient_id)
    if encounter_id:
        encounter = encounter_crud.get_encounter(db, encounter_id)
        if encounter and not patient:
            patient = encounter.patient
    
    # Get active procedure catalog items for dropdown
    from app.crud import procedure_catalog_crud
    procedure_catalog_items, _ = procedure_catalog_crud.search_procedure_catalog(
        db, query=None, skip=0, limit=1000, active_only=True
    )
    
    context = {
        "request": request,
        "title": "Create Procedure",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient,
        "encounter": encounter,
        "procedure_types": [pt.value for pt in ProcedureType],
        "statuses": [stat.value for stat in ProcedureStatus],
        "procedure_catalog_items": procedure_catalog_items
    }
    return templates.TemplateResponse("procedures/procedure_form.html", context)


@router.post("/create", name="create_procedure", status_code=302)
def create_procedure(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor"])),
    patient_id: int = Form(...),
    encounter_id: Optional[int] = Form(None),
    procedure_catalog_id: Optional[int] = Form(None),
    procedure_name: str = Form(...),
    procedure_code: Optional[str] = Form(None),
    procedure_type: str = Form(...),
    description: Optional[str] = Form(None),
    indication: Optional[str] = Form(None),
    scheduled_date: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    anesthesia_type: Optional[str] = Form(None),
    anesthesia_provider: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    status: str = Form("scheduled")
):
    """Create a new procedure."""
    try:
        proc_type = ProcedureType(procedure_type)
        proc_status = ProcedureStatus(status)
        
        scheduled_date_obj = None
        if scheduled_date:
            scheduled_date_obj = datetime.strptime(scheduled_date, "%Y-%m-%dT%H:%M")
        
        procedure_data = ProcedureCreate(
            patient_id=patient_id,
            encounter_id=encounter_id if encounter_id else None,
            procedure_catalog_id=procedure_catalog_id if procedure_catalog_id else None,
            ordered_by_id=current_user.id,
            procedure_name=procedure_name,
            procedure_code=procedure_code,
            procedure_type=proc_type,
            description=description,
            indication=indication,
            scheduled_date=scheduled_date_obj,
            location=location,
            anesthesia_type=anesthesia_type,
            anesthesia_provider=anesthesia_provider,
            notes=notes,
            status=proc_status
        )
        
        procedure = procedure_crud.create_procedure(db, procedure_data)
        
        try:
            create_charge_for_procedure(db, procedure, current_user.id)
        except Exception as billing_error:
            print(f"Warning: Unable to create procedure charge for procedure {procedure.id}: {billing_error}")
        
        # Redirect based on context
        if encounter_id:
            return RedirectResponse(
                url=f"/encounters/{encounter_id}?status=procedure_added",
                status_code=302
            )
        elif patient_id:
            return RedirectResponse(
                url=f"/patients/{patient_id}?status=procedure_added",
                status_code=302
            )
        else:
            return RedirectResponse(
                url=request.url_for("procedure_detail", procedure_id=procedure.id),
                status_code=302
            )
    except Exception as e:
        return RedirectResponse(
            url=request.url_for("procedure_create_form") + f"?error={str(e)}",
            status_code=302
        )


@router.get("/{procedure_id}", name="procedure_detail")
def procedure_detail(
    request: Request,
    procedure_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician"]))
):
    """View procedure details."""
    procedure = procedure_crud.get_procedure(db, procedure_id)
    if not procedure:
        raise HTTPException(status_code=404, detail="Procedure not found")
    
    context = {
        "request": request,
        "title": f"Procedure: {procedure.procedure_number}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "procedure": procedure
    }
    return templates.TemplateResponse("procedures/procedure_detail.html", context)


@router.get("/{procedure_id}/edit", name="procedure_edit_form")
def procedure_edit_form(
    request: Request,
    procedure_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor"]))
):
    """Form to edit a procedure."""
    procedure = procedure_crud.get_procedure(db, procedure_id)
    if not procedure:
        raise HTTPException(status_code=404, detail="Procedure not found")
    
    # Get active procedure catalog items for dropdown
    from app.crud import procedure_catalog_crud
    procedure_catalog_items, _ = procedure_catalog_crud.search_procedure_catalog(
        db, query=None, skip=0, limit=1000, active_only=True
    )
    
    context = {
        "request": request,
        "title": f"Edit Procedure: {procedure.procedure_number}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "procedure": procedure,
        "procedure_types": [pt.value for pt in ProcedureType],
        "statuses": [stat.value for stat in ProcedureStatus],
        "procedure_catalog_items": procedure_catalog_items
    }
    return templates.TemplateResponse("procedures/procedure_form.html", context)


@router.post("/{procedure_id}/update", name="update_procedure", status_code=302)
def update_procedure(
    request: Request,
    procedure_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor"])),
    procedure_catalog_id: Optional[int] = Form(None),
    procedure_name: Optional[str] = Form(None),
    procedure_type: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    start_time: Optional[str] = Form(None),
    end_time: Optional[str] = Form(None),
    performed_by_id: Optional[int] = Form(None),
    findings: Optional[str] = Form(None),
    complications: Optional[str] = Form(None),
    outcome: Optional[str] = Form(None),
    notes: Optional[str] = Form(None)
):
    """Update a procedure."""
    try:
        # Check payment if status is being changed to COMPLETED
        if status and ProcedureStatus(status) == ProcedureStatus.COMPLETED:
            procedure = procedure_crud.get_procedure(db, procedure_id)
            if procedure:
                from app.utils.payment_verification import (
                    check_payment_required_and_paid,
                    is_cash_patient
                )
                from app.models.billing_models import ChargeType
                
                patient_id = procedure.patient_id
                if patient_id and is_cash_patient(db, patient_id):
                    payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
                        db, patient_id, ChargeType.PROCEDURE,
                        encounter_id=procedure.encounter_id,
                        procedure_id=procedure_id
                    )
                    
                    if payment_required and not payment_paid:
                        # Block completion - redirect back with payment required error
                        invoice_id = invoice.id if invoice else None
                        invoice_balance = invoice.balance if invoice else None
                        return RedirectResponse(
                            url=request.url_for("procedure_detail", procedure_id=procedure_id) + f"?error=payment_required&invoice_id={invoice_id}&balance={invoice_balance}",
                            status_code=302
                        )
        
        update_data = {}
        
        if procedure_catalog_id is not None:
            update_data["procedure_catalog_id"] = procedure_catalog_id if procedure_catalog_id else None
        if procedure_name:
            update_data["procedure_name"] = procedure_name
        if procedure_type:
            update_data["procedure_type"] = ProcedureType(procedure_type)
        if status:
            update_data["status"] = ProcedureStatus(status)
        if start_time:
            update_data["start_time"] = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
        if end_time:
            update_data["end_time"] = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")
        if performed_by_id:
            update_data["performed_by_id"] = performed_by_id
        if findings is not None:
            update_data["findings"] = findings
        if complications is not None:
            update_data["complications"] = complications
        if outcome is not None:
            update_data["outcome"] = outcome
        if notes is not None:
            update_data["notes"] = notes
        
        procedure_update = ProcedureUpdate(**update_data)
        procedure = procedure_crud.update_procedure(db, procedure_id, procedure_update)
        
        if not procedure:
            raise HTTPException(status_code=404, detail="Procedure not found")
        
        return RedirectResponse(
            url=request.url_for("procedure_detail", procedure_id=procedure_id),
            status_code=302
        )
    except Exception as e:
        return RedirectResponse(
            url=request.url_for("procedure_edit_form", procedure_id=procedure_id) + f"?error={str(e)}",
            status_code=302
        )

