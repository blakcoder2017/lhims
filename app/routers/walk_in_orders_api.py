"""
Walk-in Orders API Routes

Routes for managing walk-in lab orders, radiology orders, and procedures.
Front desk can create and check-in walk-in orders.
"""
from fastapi import APIRouter, Depends, Request, Query, HTTPException, Form, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List, Dict
from datetime import datetime, date

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.core.templates import templates
from app.models.user_models import User
from app.models.patient_models import Patient, PaymentMechanism
from app.models.encounter_models import (
    LabOrder,
    RadiologyOrder,
    OrderStatus,
    Prescription,
    EncounterStatus,
    Encounter,
)
from app.models.procedure_models import Procedure, ProcedureStatus
from app.models.billing_models import Charge, Invoice
from app.crud import encounter_crud, procedure_crud, service_pricing_crud, patient_crud, inventory_crud
from app.schemas.encounter_schemas import (
    LabOrderCreate,
    RadiologyOrderCreate,
    EncounterCreate,
    EncounterUpdate,
    PrescriptionCreate,
)
from app.schemas.procedure_schemas import ProcedureCreate
from app.schemas.patient_schemas import PatientCreate
from app.services import (
    create_charge_for_lab_order,
    create_charge_for_radiology_order,
    create_charge_for_procedure,
    create_charge_for_prescription,
)


def ensure_patient(
    db: Session,
    patient_id: Optional[int],
    walk_in_first_name: Optional[str],
    walk_in_last_name: Optional[str],
    walk_in_phone: Optional[str] = None,
) -> Patient:
    """
    Return an existing patient or create a minimal walk-in patient record.
    """
    if patient_id:
        patient = db.query(Patient).filter(Patient.id == patient_id, Patient.is_active == True).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        return patient
    
    if not walk_in_first_name or not walk_in_last_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide an existing patient or walk-in customer details."
        )
    
    walk_in_data = PatientCreate(
        first_name=walk_in_first_name.strip().title(),
        last_name=walk_in_last_name.strip().title(),
        date_of_birth=date.today(),
        gender="Unknown",
        phone_number=walk_in_phone.strip() if walk_in_phone else None,
        address=None,
        payment_mechanism=PaymentMechanism.CASH,
        national_id=None,
        nhis_number=None,
        insurance_provider=None,
        insurance_policy_number=None,
        languages_spoken=None,
    )
    return patient_crud.create_patient(db, walk_in_data)

router = APIRouter(tags=["Walk-in Orders"])


@router.get("/walk-in-orders", name="walk_in_orders_dashboard")
def walk_in_orders_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        role_required(
            ["Front Office", "Admin", "Lab Staff", "Radiology Staff", "Pharmacy Staff"]
        )
    ),
    order_type: Optional[str] = Query(None, description="Filter by order type: lab, radiology, procedure")
):
    """Dashboard for ancillary departments and front desk to manage walk-in services."""
    user_role = current_user.role.name
    can_check_in_orders = user_role in ["Front Office", "Admin"]
    can_create_lab_orders = user_role in ["Front Office", "Admin", "Lab Staff"]
    can_create_radiology_orders = user_role in ["Front Office", "Admin", "Radiology Staff"]
    can_create_procedures = user_role in ["Front Office", "Admin"]
    can_create_pharmacy_sales = user_role in ["Front Office", "Admin", "Pharmacy Staff"]
    
    # Pending walk-in orders awaiting payment confirmation
    walk_in_lab_orders = db.query(LabOrder).options(
        joinedload(LabOrder.patient),
        joinedload(LabOrder.ordered_by)
    ).filter(
        LabOrder.is_walk_in == True,
        LabOrder.checked_in_at.is_(None)
    ).order_by(LabOrder.ordered_at.desc()).all()
    
    walk_in_radiology_orders = db.query(RadiologyOrder).options(
        joinedload(RadiologyOrder.patient),
        joinedload(RadiologyOrder.ordered_by)
    ).filter(
        RadiologyOrder.is_walk_in == True,
        RadiologyOrder.checked_in_at.is_(None)
    ).order_by(RadiologyOrder.ordered_at.desc()).all()
    
    walk_in_procedures = db.query(Procedure).options(
        joinedload(Procedure.patient),
        joinedload(Procedure.ordered_by)
    ).filter(
        Procedure.is_walk_in == True,
        Procedure.checked_in_at.is_(None),
        Procedure.is_active == True
    ).order_by(Procedure.created_at.desc()).all()
    
    walk_in_pharmacy_sales = db.query(Prescription).options(
        joinedload(Prescription.encounter).joinedload(Encounter.patient),
        joinedload(Prescription.prescribed_by)
    ).filter(
        Prescription.is_walk_in == True,
        Prescription.checked_in_at.is_(None),
        Prescription.status.in_([
            OrderStatus.PENDING.value,
            OrderStatus.ORDERED.value,
            OrderStatus.IN_PROGRESS.value
        ])
    ).order_by(Prescription.prescribed_at.desc()).all()
    
    # Service pricing for dropdown selections
    lab_tests = service_pricing_crud.get_service_pricing_by_charge_type(db, "lab_test")
    radiology_studies = service_pricing_crud.get_service_pricing_by_charge_type(db, "radiology")
    procedures = service_pricing_crud.get_service_pricing_by_charge_type(db, "procedure")
    
    # Load medications from pharmacy inventory database instead of service pricing
    medications = inventory_crud.get_medications(db, skip=0, limit=500, search=None)
    
    # Load procedure catalog for dropdown
    from app.models.procedure_catalog_models import ProcedureCatalog
    procedure_catalogs = db.query(ProcedureCatalog).filter(
        ProcedureCatalog.is_active == True
    ).order_by(ProcedureCatalog.procedure_name).all()
    procedure_catalog_list = [
        {"id": p.id, "name": p.procedure_name, "cash_price": float(p.cash_price) if p.cash_price else 0}
        for p in procedure_catalogs
    ]
    
    def build_invoice_map(query_filter) -> Dict[int, Invoice]:
        charges = db.query(Charge).options(joinedload(Charge.invoice)).filter(*query_filter).all()
        invoice_map: Dict[int, Invoice] = {}
        for charge in charges:
            if charge.invoice:
                if charge.lab_order_id:
                    invoice_map[charge.lab_order_id] = charge.invoice
                elif charge.radiology_order_id:
                    invoice_map[charge.radiology_order_id] = charge.invoice
                elif charge.prescription_id:
                    invoice_map[charge.prescription_id] = charge.invoice
        return invoice_map
    
    lab_invoice_map = {}
    if walk_in_lab_orders:
        lab_ids = [order.id for order in walk_in_lab_orders]
        lab_invoice_map = build_invoice_map([Charge.lab_order_id.in_(lab_ids)])
    
    radiology_invoice_map = {}
    if walk_in_radiology_orders:
        rad_ids = [order.id for order in walk_in_radiology_orders]
        radiology_invoice_map = build_invoice_map([Charge.radiology_order_id.in_(rad_ids)])
    
    pharmacy_invoice_map = {}
    if walk_in_pharmacy_sales:
        pharm_ids = [sale.id for sale in walk_in_pharmacy_sales]
        pharmacy_invoice_map = build_invoice_map([Charge.prescription_id.in_(pharm_ids)])
    
    context = {
        "request": request,
        "title": "Walk-in Orders",
        "current_user": current_user,
        "user_role": user_role,
        "walk_in_lab_orders": walk_in_lab_orders,
        "walk_in_radiology_orders": walk_in_radiology_orders,
        "walk_in_procedures": walk_in_procedures,
        "walk_in_pharmacy_sales": walk_in_pharmacy_sales,
        "lab_invoice_map": lab_invoice_map,
        "radiology_invoice_map": radiology_invoice_map,
        "pharmacy_invoice_map": pharmacy_invoice_map,
        "order_type": order_type,
        "lab_tests": lab_tests,
        "radiology_studies": radiology_studies,
        "procedures": procedures,
        "procedure_catalogs": procedure_catalog_list,
        "medications": medications,  # Changed from pharmacy_items to medications from inventory
        "can_check_in_orders": can_check_in_orders,
        "can_create_lab_orders": can_create_lab_orders,
        "can_create_radiology_orders": can_create_radiology_orders,
        "can_create_procedures": can_create_procedures,
        "can_create_pharmacy_sales": can_create_pharmacy_sales,
    }
    return templates.TemplateResponse("front_office/walk_in_orders.html", context)


@router.post("/walk-in-orders/lab/create", name="create_walk_in_lab_order", status_code=status.HTTP_302_FOUND)
def create_walk_in_lab_order(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Lab Staff"])),
    patient_id: Optional[int] = Form(None),
    walk_in_first_name: Optional[str] = Form(None),
    walk_in_last_name: Optional[str] = Form(None),
    walk_in_phone: Optional[str] = Form(None),
    test_name: str = Form(...),
    test_code: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
    priority: str = Form("routine"),
):
    """Create a walk-in lab order"""
    import traceback
    try:
        print(f"[DEBUG] create_walk_in_lab_order called with test_name={test_name}")
        patient = ensure_patient(db, patient_id, walk_in_first_name, walk_in_last_name, walk_in_phone)
        
        lab_order_data = LabOrderCreate(
            encounter_id=None,
            patient_id=patient.id,
            ordered_by_id=current_user.id,
            test_name=test_name,
            test_code=test_code if test_code else None,
            instructions=instructions if instructions else None,
            priority=priority,
            is_walk_in=True
        )
        
        new_order = encounter_crud.create_lab_order(db, lab_order_data)
        
        # Create charge for the lab order
        try:
            create_charge_for_lab_order(db, new_order, current_user.id, check_payment_required=False)
        except Exception as billing_error:
            import traceback
            print(f"Warning: Unable to create walk-in lab charge for order {new_order.id}: {billing_error}")
            print(traceback.format_exc())
            # Don't fail the order creation if charge creation fails - can be created manually later
        
        return RedirectResponse(
            url=str(request.url_for("walk_in_orders_dashboard")) + "?status=lab_order_created",
            status_code=status.HTTP_302_FOUND
        )
    except HTTPException as http_exc:
        print(f"[DEBUG] HTTPException in create_walk_in_lab_order: {http_exc.status_code} - {http_exc.detail}")
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Error creating walk-in lab order: {error_msg}")
        traceback.print_exc()
        try:
            redirect_url = str(request.url_for("walk_in_orders_dashboard")) + f"?error={error_msg[:200]}"
        except Exception as url_error:
            print(f"[ERROR] Failed to generate redirect URL: {url_error}")
            redirect_url = "/walk-in-orders?error=Failed to create lab order"
        return RedirectResponse(
            url=redirect_url,
            status_code=status.HTTP_302_FOUND
        )


@router.post("/walk-in-orders/radiology/create", name="create_walk_in_radiology_order", status_code=status.HTTP_302_FOUND)
def create_walk_in_radiology_order(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Radiology Staff"])),
    patient_id: Optional[int] = Form(None),
    walk_in_first_name: Optional[str] = Form(None),
    walk_in_last_name: Optional[str] = Form(None),
    walk_in_phone: Optional[str] = Form(None),
    study_type: str = Form(...),
    study_code: Optional[str] = Form(None),
    body_part: Optional[str] = Form(None),
    clinical_indication: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
    priority: str = Form("routine"),
):
    """Create a walk-in radiology order"""
    import traceback
    try:
        print(f"[DEBUG] create_walk_in_radiology_order called with study_type={study_type}")
        patient = ensure_patient(db, patient_id, walk_in_first_name, walk_in_last_name, walk_in_phone)
        
        radiology_order_data = RadiologyOrderCreate(
            encounter_id=None,
            patient_id=patient.id,
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
        
        # Create charge for the radiology order
        try:
            create_charge_for_radiology_order(db, new_order, current_user.id, check_payment_required=False)
        except Exception as billing_error:
            import traceback
            print(f"Warning: Unable to create walk-in radiology charge for order {new_order.id}: {billing_error}")
            print(traceback.format_exc())
            # Don't fail the order creation if charge creation fails - can be created manually later
        
        return RedirectResponse(
            url=str(request.url_for("walk_in_orders_dashboard")) + "?status=radiology_order_created",
            status_code=status.HTTP_302_FOUND
        )
    except HTTPException as http_exc:
        print(f"[DEBUG] HTTPException in create_walk_in_radiology_order: {http_exc.status_code} - {http_exc.detail}")
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Error creating walk-in radiology order: {error_msg}")
        traceback.print_exc()
        try:
            redirect_url = str(request.url_for("walk_in_orders_dashboard")) + f"?error={error_msg[:200]}"
        except Exception as url_error:
            print(f"[ERROR] Failed to generate redirect URL: {url_error}")
            redirect_url = "/walk-in-orders?error=Failed to create radiology order"
        return RedirectResponse(
            url=redirect_url,
            status_code=status.HTTP_302_FOUND
        )


@router.post("/walk-in-orders/pharmacy/create", name="create_walk_in_pharmacy_sale", status_code=status.HTTP_302_FOUND)
def create_walk_in_pharmacy_sale(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Pharmacy Staff"])),
    patient_id: Optional[int] = Form(None),
    walk_in_first_name: Optional[str] = Form(None),
    walk_in_last_name: Optional[str] = Form(None),
    walk_in_phone: Optional[str] = Form(None),
    medication_name: str = Form(...),
    dosage: str = Form(...),
    frequency: str = Form(...),
    duration: str = Form(...),
    quantity: int = Form(1),
    medication_code: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
):
    """Create a walk-in pharmacy sale (prescription without consultation)."""
    import traceback
    try:
        print(f"[DEBUG] create_walk_in_pharmacy_sale called with medication_name={medication_name}")
        patient = ensure_patient(db, patient_id, walk_in_first_name, walk_in_last_name, walk_in_phone)
        
        encounter_data = EncounterCreate(
            patient_id=patient.id,
            clinician_id=current_user.id,
            chief_complaint=f"Walk-in pharmacy sale: {medication_name}",
            status=EncounterStatus.IN_PROGRESS
        )
        encounter = encounter_crud.create_encounter(db, encounter_data)
        encounter_crud.update_encounter(
            db,
            encounter.id,
            EncounterUpdate(status=EncounterStatus.COMPLETED)
        )
        
        prescription_data = PrescriptionCreate(
            encounter_id=encounter.id,
            prescribed_by_id=current_user.id,
            medication_name=medication_name,
            medication_code=medication_code if medication_code else None,
            dosage=dosage,
            frequency=frequency,
            duration=duration,
            quantity=quantity,
            instructions=instructions if instructions else None,
            is_walk_in=True
        )
        
        new_prescription = encounter_crud.create_prescription(db, prescription_data)
        
        # Create charge for the prescription
        try:
            create_charge_for_prescription(db, new_prescription, current_user.id, check_payment_required=False)
        except Exception as billing_error:
            import traceback
            print(f"Warning: Unable to create walk-in pharmacy charge for prescription {new_prescription.id}: {billing_error}")
            print(traceback.format_exc())
            # Don't fail the prescription creation if charge creation fails - can be created manually later
        
        return RedirectResponse(
            url=str(request.url_for("walk_in_orders_dashboard")) + "?status=pharmacy_sale_created",
            status_code=status.HTTP_302_FOUND
        )
    except HTTPException as http_exc:
        print(f"[DEBUG] HTTPException in create_walk_in_pharmacy_sale: {http_exc.status_code} - {http_exc.detail}")
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Error creating walk-in pharmacy sale: {error_msg}")
        traceback.print_exc()
        # Ensure we can generate the redirect URL even if url_for fails
        try:
            redirect_url = str(request.url_for("walk_in_orders_dashboard")) + f"?error={error_msg[:200]}"
        except Exception as url_error:
            print(f"[ERROR] Failed to generate redirect URL: {url_error}")
            redirect_url = "/walk-in-orders?error=Failed to create pharmacy sale"
        return RedirectResponse(
            url=redirect_url,
            status_code=status.HTTP_302_FOUND
        )


@router.post("/walk-in-orders/procedure/create", name="create_walk_in_procedure", status_code=status.HTTP_302_FOUND)
def create_walk_in_procedure(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin"])),
    patient_id: Optional[int] = Form(None),
    walk_in_first_name: Optional[str] = Form(None),
    walk_in_last_name: Optional[str] = Form(None),
    walk_in_phone: Optional[str] = Form(None),
    procedure_name: str = Form(...),
    procedure_code: Optional[str] = Form(None),
    procedure_type: str = Form(...),
    procedure_catalog_id: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    indication: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
):
    """Create a walk-in procedure"""
    import traceback
    try:
        print(f"[DEBUG] create_walk_in_procedure called with procedure_name={procedure_name}")
        from app.models.procedure_models import ProcedureType
        
        patient = ensure_patient(db, patient_id, walk_in_first_name, walk_in_last_name, walk_in_phone)
        
        procedure_data = ProcedureCreate(
            patient_id=patient.id,
            encounter_id=None,
            ordered_by_id=current_user.id,
            procedure_name=procedure_name,
            procedure_code=procedure_code if procedure_code else None,
            procedure_catalog_id=procedure_catalog_id,
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
            url=str(request.url_for("walk_in_orders_dashboard")) + "?status=procedure_created",
            status_code=status.HTTP_302_FOUND
        )
    except HTTPException as http_exc:
        print(f"[DEBUG] HTTPException in create_walk_in_procedure: {http_exc.status_code} - {http_exc.detail}")
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Error creating walk-in procedure: {error_msg}")
        traceback.print_exc()
        try:
            redirect_url = str(request.url_for("walk_in_orders_dashboard")) + f"?error={error_msg[:200]}"
        except Exception as url_error:
            print(f"[ERROR] Failed to generate redirect URL: {url_error}")
            redirect_url = "/walk-in-orders?error=Failed to create procedure"
        return RedirectResponse(
            url=redirect_url,
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
        
        charge = (
            db.query(Charge)
            .options(joinedload(Charge.invoice))
            .filter(Charge.lab_order_id == order_id)
            .order_by(Charge.created_at.desc())
            .first()
        )
        if not charge or not charge.invoice:
            raise ValueError("No invoice found for this lab order. Please generate an invoice before checking in.")
        if charge.invoice.balance > 0:
            raise ValueError("Payment pending: collect payment and update the invoice before checking in.")
        
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
        
        charge = (
            db.query(Charge)
            .options(joinedload(Charge.invoice))
            .filter(Charge.radiology_order_id == order_id)
            .order_by(Charge.created_at.desc())
            .first()
        )
        if not charge or not charge.invoice:
            raise ValueError("No invoice found for this radiology order. Please generate an invoice before checking in.")
        if charge.invoice.balance > 0:
            raise ValueError("Payment pending: collect payment and update the invoice before checking in.")
        
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


@router.post("/walk-in-orders/pharmacy/{prescription_id}/check-in", name="check_in_walk_in_pharmacy_sale", status_code=status.HTTP_302_FOUND)
def check_in_walk_in_pharmacy_sale(
    request: Request,
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin"]))
):
    """Confirm payment for a walk-in pharmacy sale."""
    try:
        prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
        if not prescription:
            raise HTTPException(status_code=404, detail="Prescription not found")
        
        if not prescription.is_walk_in:
            raise ValueError("This is not a walk-in pharmacy sale")
        
        if prescription.checked_in_at:
            raise ValueError("This pharmacy sale has already been checked in")
        
        charge = (
            db.query(Charge)
            .options(joinedload(Charge.invoice))
            .filter(Charge.prescription_id == prescription_id)
            .order_by(Charge.created_at.desc())
            .first()
        )
        
        if not charge or not charge.invoice:
            raise ValueError("No invoice found for this pharmacy sale. Please create or refresh the invoice before check-in.")
        
        if charge.invoice.balance > 0:
            raise ValueError("Payment pending: please collect payment and update the invoice before checking in.")
        
        prescription.checked_in_at = datetime.now()
        prescription.checked_in_by_id = current_user.id
        if prescription.status == OrderStatus.PENDING.value:
            prescription.status = OrderStatus.ORDERED.value
        
        db.commit()
        
        return RedirectResponse(
            url="/walk-in-orders?status=pharmacy_sale_checked_in",
            status_code=status.HTTP_302_FOUND
        )
    except HTTPException:
        raise
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

