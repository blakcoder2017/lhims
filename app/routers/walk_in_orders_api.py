"""
Walk-in Orders API Routes

Routes for managing walk-in lab orders, radiology orders, and procedures.
Front desk can create and check-in walk-in orders.
"""
from fastapi import APIRouter, Depends, Request, Query, HTTPException, Form, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from typing import Optional, List
from datetime import datetime

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.models.encounter_models import LabOrder, RadiologyOrder, OrderStatus
from app.models.procedure_models import Procedure, ProcedureStatus
from app.crud import encounter_crud, procedure_crud, service_pricing_crud
from app.schemas.encounter_schemas import LabOrderCreate, RadiologyOrderCreate
from app.schemas.procedure_schemas import ProcedureCreate
from app.services import (
    create_charge_for_lab_order,
    create_charge_for_radiology_order,
    create_charge_for_procedure
)

router = APIRouter(tags=["Walk-in Orders"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/walk-in-orders", name="walk_in_orders_dashboard")
def walk_in_orders_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin"])),
    order_type: Optional[str] = Query(None, description="Filter by order type: lab, radiology, procedure")
):
    """Dashboard for front desk to view and manage walk-in orders"""
    # Get all walk-in orders that haven't been checked in
    walk_in_lab_orders = db.query(LabOrder).options(
        joinedload(LabOrder.patient),
        joinedload(LabOrder.ordered_by)
    ).filter(
        LabOrder.is_walk_in == True,
        LabOrder.checked_in_at.is_(None),
        LabOrder.is_active == True
    ).order_by(LabOrder.ordered_at.desc()).all()
    
    walk_in_radiology_orders = db.query(RadiologyOrder).options(
        joinedload(RadiologyOrder.patient),
        joinedload(RadiologyOrder.ordered_by)
    ).filter(
        RadiologyOrder.is_walk_in == True,
        RadiologyOrder.checked_in_at.is_(None),
        RadiologyOrder.is_active == True
    ).order_by(RadiologyOrder.ordered_at.desc()).all()
    
    walk_in_procedures = db.query(Procedure).options(
        joinedload(Procedure.patient),
        joinedload(Procedure.ordered_by)
    ).filter(
        Procedure.is_walk_in == True,
        Procedure.checked_in_at.is_(None),
        Procedure.is_active == True
    ).order_by(Procedure.created_at.desc()).all()
    
    # Get service pricing for dropdowns
    lab_tests = service_pricing_crud.get_service_pricing_by_charge_type(db, "lab_test")
    radiology_studies = service_pricing_crud.get_service_pricing_by_charge_type(db, "radiology")
    procedures = service_pricing_crud.get_service_pricing_by_charge_type(db, "procedure")
    
    context = {
        "request": request,
        "title": "Walk-in Orders",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "walk_in_lab_orders": walk_in_lab_orders,
        "walk_in_radiology_orders": walk_in_radiology_orders,
        "walk_in_procedures": walk_in_procedures,
        "order_type": order_type,
        "lab_tests": lab_tests,
        "radiology_studies": radiology_studies,
        "procedures": procedures
    }
    return templates.TemplateResponse("front_office/walk_in_orders.html", context)


@router.post("/walk-in-orders/lab/create", name="create_walk_in_lab_order", status_code=status.HTTP_302_FOUND)
def create_walk_in_lab_order(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin"])),
    patient_id: int = Form(...),
    test_name: str = Form(...),
    test_code: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
    priority: str = Form("routine"),
):
    """Create a walk-in lab order"""
    try:
        lab_order_data = LabOrderCreate(
            encounter_id=None,
            patient_id=patient_id,
            ordered_by_id=current_user.id,
            test_name=test_name,
            test_code=test_code if test_code else None,
            instructions=instructions if instructions else None,
            priority=priority,
            is_walk_in=True
        )
        
        new_order = encounter_crud.create_lab_order(db, lab_order_data)
        
        try:
            create_charge_for_lab_order(db, new_order, current_user.id)
        except Exception as billing_error:
            print(f"Warning: Unable to create walk-in lab charge for order {new_order.id}: {billing_error}")
        
        return RedirectResponse(
            url=f"/walk-in-orders?status=lab_order_created",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/walk-in-orders?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/walk-in-orders/radiology/create", name="create_walk_in_radiology_order", status_code=status.HTTP_302_FOUND)
def create_walk_in_radiology_order(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin"])),
    patient_id: int = Form(...),
    study_type: str = Form(...),
    study_code: Optional[str] = Form(None),
    body_part: Optional[str] = Form(None),
    clinical_indication: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
    priority: str = Form("routine"),
):
    """Create a walk-in radiology order"""
    try:
        radiology_order_data = RadiologyOrderCreate(
            encounter_id=None,
            patient_id=patient_id,
            ordered_by_id=current_user.id,
            study_type=study_type,
            study_code=study_code if study_code else None,
            body_part=body_part if body_part else None,
            clinical_indication=clinical_indication if clinical_indication else None,
            instructions=instructions if instructions else None,
            priority=priority,
            is_walk_in=True
        )
        
        new_order = encounter_crud.create_radiology_order(db, radiology_order_data)
        
        try:
            create_charge_for_radiology_order(db, new_order, current_user.id)
        except Exception as billing_error:
            print(f"Warning: Unable to create walk-in radiology charge for order {new_order.id}: {billing_error}")
        
        return RedirectResponse(
            url=f"/walk-in-orders?status=radiology_order_created",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/walk-in-orders?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/walk-in-orders/procedure/create", name="create_walk_in_procedure", status_code=status.HTTP_302_FOUND)
def create_walk_in_procedure(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin"])),
    patient_id: int = Form(...),
    procedure_name: str = Form(...),
    procedure_code: Optional[str] = Form(None),
    procedure_type: str = Form(...),
    description: Optional[str] = Form(None),
    indication: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
):
    """Create a walk-in procedure"""
    try:
        from app.models.procedure_models import ProcedureType
        
        procedure_data = ProcedureCreate(
            patient_id=patient_id,
            encounter_id=None,
            ordered_by_id=current_user.id,
            procedure_name=procedure_name,
            procedure_code=procedure_code if procedure_code else None,
            procedure_type=ProcedureType(procedure_type),
            description=description if description else None,
            indication=indication if indication else None,
            location=location if location else None,
            status=ProcedureStatus.SCHEDULED,
            is_walk_in=True
        )
        
        procedure = procedure_crud.create_procedure(db, procedure_data)
        
        try:
            create_charge_for_procedure(db, procedure, current_user.id)
        except Exception as billing_error:
            print(f"Warning: Unable to create walk-in procedure charge for procedure {procedure.id}: {billing_error}")
        
        return RedirectResponse(
            url=f"/walk-in-orders?status=procedure_created",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/walk-in-orders?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/walk-in-orders/lab/{order_id}/check-in", name="check_in_walk_in_lab_order", status_code=status.HTTP_302_FOUND)
def check_in_walk_in_lab_order(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin"]))
):
    """Check in a walk-in lab order"""
    try:
        lab_order = db.query(LabOrder).filter(LabOrder.id == order_id).first()
        if not lab_order:
            raise HTTPException(status_code=404, detail="Lab order not found")
        
        if not lab_order.is_walk_in:
            raise ValueError("This is not a walk-in order")
        
        if lab_order.checked_in_at:
            raise ValueError("This order has already been checked in")
        
        lab_order.checked_in_at = datetime.now()
        lab_order.checked_in_by_id = current_user.id
        lab_order.status = OrderStatus.ORDERED
        
        db.commit()
        
        return RedirectResponse(
            url=f"/walk-in-orders?status=lab_order_checked_in",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/walk-in-orders?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/walk-in-orders/radiology/{order_id}/check-in", name="check_in_walk_in_radiology_order", status_code=status.HTTP_302_FOUND)
def check_in_walk_in_radiology_order(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin"]))
):
    """Check in a walk-in radiology order"""
    try:
        radiology_order = db.query(RadiologyOrder).filter(RadiologyOrder.id == order_id).first()
        if not radiology_order:
            raise HTTPException(status_code=404, detail="Radiology order not found")
        
        if not radiology_order.is_walk_in:
            raise ValueError("This is not a walk-in order")
        
        if radiology_order.checked_in_at:
            raise ValueError("This order has already been checked in")
        
        radiology_order.checked_in_at = datetime.now()
        radiology_order.checked_in_by_id = current_user.id
        radiology_order.status = OrderStatus.ORDERED
        
        db.commit()
        
        return RedirectResponse(
            url=f"/walk-in-orders?status=radiology_order_checked_in",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/walk-in-orders?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/walk-in-orders/procedure/{procedure_id}/check-in", name="check_in_walk_in_procedure", status_code=status.HTTP_302_FOUND)
def check_in_walk_in_procedure(
    request: Request,
    procedure_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin"]))
):
    """Check in a walk-in procedure"""
    try:
        procedure = db.query(Procedure).filter(Procedure.id == procedure_id).first()
        if not procedure:
            raise HTTPException(status_code=404, detail="Procedure not found")
        
        if not procedure.is_walk_in:
            raise ValueError("This is not a walk-in procedure")
        
        if procedure.checked_in_at:
            raise ValueError("This procedure has already been checked in")
        
        procedure.checked_in_at = datetime.now()
        procedure.checked_in_by_id = current_user.id
        
        db.commit()
        
        return RedirectResponse(
            url=f"/walk-in-orders?status=procedure_checked_in",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/walk-in-orders?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )

