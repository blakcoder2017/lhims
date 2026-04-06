# 
import csv
import io
import json
import logging
from datetime import datetime, date

from fastapi import APIRouter, Request, Depends, status, Query
from typing import Optional, List
from fastapi.responses import RedirectResponse, StreamingResponse
from app.core.templates import templates
from app.core.deps import get_current_user, role_required
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.crud import patient_crud, encounter_crud, disease_crud 
from app.schemas.patient_schemas import Patient 
from app.models.user_models import User
from app.services import create_charge_for_consultation

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter()


def _safe_parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _build_differential_registry_rows(records):
    rows = []
    for encounter in records:
        payload = encounter_crud.load_differential_data(encounter)
        if not payload:
            continue
        suggestions = payload.get("suggestions", [])
        generated_at_dt = _safe_parse_datetime(payload.get("generated_at"))
        counts = {
            "total": len(suggestions),
            "working": sum(1 for s in suggestions if (s.get("status") or "").lower() == "working"),
            "ruled_out": sum(
                1 for s in suggestions if (s.get("status") or "").lower() in {"ruled_out", "ruled-out"}
            ),
        }
        counts["suggested"] = counts["total"] - counts["working"] - counts["ruled_out"]
        rows.append(
            {
                "encounter": encounter,
                "patient": encounter.patient,
                "clinician": encounter.clinician,
                "summary": (payload.get("clinical_summary") or "").strip(),
                "notes": payload.get("notes"),
                "generated_at": generated_at_dt,
                "generated_at_display": generated_at_dt.strftime("%Y-%m-%d %H:%M")
                if generated_at_dt
                else None,
                "counts": counts,
                "suggestions": suggestions,
                "top_suggestion": suggestions[0] if suggestions else None,
            }
        )
    return rows


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

@router.get("/", name="dashboard")
# Protected by get_current_user, which raises 401 if unauthenticated.
async def dashboard(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Renders the main dashboard page with real-time metrics and statistics.
    If unauthenticated, a 401 is raised, and main.py redirects to /login.
    """
    from sqlalchemy import func, and_, extract
    from datetime import datetime, timedelta
    from decimal import Decimal
    from app.models.patient_models import Patient
    from app.models.scheduled_appointment_models import Appointment, AppointmentStatus
    from app.models.encounter_models import Encounter, EncounterStatus, LabOrder, RadiologyOrder, Prescription, OrderStatus
    from app.models.billing_models import Invoice, Payment, InvoiceStatus, PaymentStatus
    from app.models.inventory_models import StockItem, StockStatus
    from app.models.lab_models import LabSample, SampleStatus
    
    # Date ranges
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)
    this_month_start = datetime.now().replace(day=1).date()
    
    # Patient Statistics
    total_patients = db.query(func.count(Patient.id)).filter(Patient.is_active == True).scalar() or 0
    new_patients_today = db.query(func.count(Patient.id)).filter(
        func.date(Patient.created_at) == today,
        Patient.is_active == True
    ).scalar() or 0
    new_patients_month = db.query(func.count(Patient.id)).filter(
        Patient.created_at >= this_month_start,
        Patient.is_active == True
    ).scalar() or 0
    
    # Appointment Statistics
    total_appointments_today = db.query(func.count(Appointment.id)).filter(
        Appointment.scheduled_date == today,
        Appointment.is_active == True
    ).scalar() or 0
    pending_appointments = db.query(func.count(Appointment.id)).filter(
        Appointment.status == AppointmentStatus.SCHEDULED.value,
        Appointment.is_active == True
    ).scalar() or 0
    
    # Encounter Statistics
    total_encounters_today = db.query(func.count(Encounter.id)).filter(
        func.date(Encounter.encounter_date) == today,
        Encounter.is_active == True
    ).scalar() or 0
    pending_encounters = db.query(func.count(Encounter.id)).filter(
        Encounter.status == EncounterStatus.IN_PROGRESS.value,
        Encounter.is_active == True
    ).scalar() or 0
    
    # Order Statistics
    pending_lab_orders = db.query(func.count(LabOrder.id)).filter(
        LabOrder.status == OrderStatus.PENDING.value
    ).scalar() or 0
    pending_radiology_orders = db.query(func.count(RadiologyOrder.id)).filter(
        RadiologyOrder.status == OrderStatus.PENDING.value
    ).scalar() or 0
    pending_prescriptions = db.query(func.count(Prescription.id)).filter(
        Prescription.status == OrderStatus.PENDING.value
    ).scalar() or 0
    
    # Financial Statistics
    revenue_today = db.query(func.sum(Payment.amount)).filter(
        func.date(Payment.payment_date) == today,
        Payment.status == PaymentStatus.COMPLETED.value,
        Payment.is_active == True
    ).scalar() or Decimal('0.00')
    
    revenue_month = db.query(func.sum(Payment.amount)).filter(
        Payment.payment_date >= this_month_start,
        Payment.status == PaymentStatus.COMPLETED.value,
        Payment.is_active == True
    ).scalar() or Decimal('0.00')
    
    outstanding_invoices = db.query(func.count(Invoice.id)).filter(
        Invoice.balance > 0,
        Invoice.is_active == True
    ).scalar() or 0
    
    total_outstanding = db.query(func.sum(Invoice.balance)).filter(
        Invoice.balance > 0,
        Invoice.is_active == True
    ).scalar() or Decimal('0.00')
    
    # Inventory Statistics
    low_stock_items = db.query(func.count(StockItem.id)).filter(
        StockItem.status == StockStatus.LOW_STOCK.value,
        StockItem.is_active == True
    ).scalar() or 0
    
    out_of_stock_items = db.query(func.count(StockItem.id)).filter(
        StockItem.status == StockStatus.OUT_OF_STOCK.value,
        StockItem.is_active == True
    ).scalar() or 0
    
    expired_items = db.query(func.count(StockItem.id)).filter(
        StockItem.status == StockStatus.EXPIRED.value,
        StockItem.is_active == True
    ).scalar() or 0
    
    # Lab Sample Statistics - Only count COLLECTED samples as pending (not RECEIVED)
    pending_samples = db.query(func.count(LabSample.id)).filter(
        LabSample.status == SampleStatus.COLLECTED.value,
        LabSample.is_active == True
    ).scalar() or 0
    
    # IPD Statistics
    from app.models.ipd_models import Ward, Bed, Admission, WardStatus, BedStatus, AdmissionStatus
    
    # Total beds and occupancy
    # Count only active beds (exclude maintenance beds from total)
    total_beds = db.query(func.count(Bed.id)).filter(
        Bed.is_active == True,
        Bed.status != BedStatus.MAINTENANCE.value
    ).scalar() or 0
    occupied_beds = db.query(func.count(Bed.id)).filter(
        Bed.status == BedStatus.OCCUPIED.value,
        Bed.is_active == True
    ).scalar() or 0
    # Available beds = beds with status AVAILABLE (not occupied, reserved, or maintenance)
    available_beds = db.query(func.count(Bed.id)).filter(
        Bed.status == BedStatus.AVAILABLE.value,
        Bed.is_active == True
    ).scalar() or 0
    reserved_beds = db.query(func.count(Bed.id)).filter(
        Bed.status == BedStatus.RESERVED.value,
        Bed.is_active == True
    ).scalar() or 0
    bed_occupancy_percentage = (occupied_beds / total_beds * 100) if total_beds > 0 else 0
    
    # Ward statistics
    total_wards = db.query(func.count(Ward.id)).filter(Ward.is_active == True).scalar() or 0
    active_wards = db.query(func.count(Ward.id)).filter(
        Ward.status == WardStatus.ACTIVE.value,
        Ward.is_active == True
    ).scalar() or 0
    
    # Admission statistics
    current_admissions = db.query(func.count(Admission.id)).filter(
        Admission.status == AdmissionStatus.ADMITTED.value,
        Admission.is_active == True
    ).scalar() or 0
    admissions_today = db.query(func.count(Admission.id)).filter(
        func.date(Admission.admission_date) == today,
        Admission.is_active == True
    ).scalar() or 0
    discharges_today = db.query(func.count(Admission.id)).filter(
        func.date(Admission.discharge_date) == today,
        Admission.status == AdmissionStatus.DISCHARGED.value,
        Admission.is_active == True
    ).scalar() or 0
    
    context = {
        "request": request,
        "title": "Dashboard",
        "current_user": current_user,
        "user_role": current_user.role.name,
        # Patient stats
        "total_patients": total_patients,
        "new_patients_today": new_patients_today,
        "new_patients_month": new_patients_month,
        # Appointment stats
        "total_appointments_today": total_appointments_today,
        "pending_appointments": pending_appointments,
        # Encounter stats
        "total_encounters_today": total_encounters_today,
        "pending_encounters": pending_encounters,
        # Order stats
        "pending_lab_orders": pending_lab_orders,
        "pending_radiology_orders": pending_radiology_orders,
        "pending_prescriptions": pending_prescriptions,
        # Financial stats
        "revenue_today": float(revenue_today),
        "revenue_month": float(revenue_month),
        "outstanding_invoices": outstanding_invoices,
        "total_outstanding": float(total_outstanding),
        # Inventory stats
        "low_stock_items": low_stock_items,
        "out_of_stock_items": out_of_stock_items,
        "expired_items": expired_items,
        # Lab stats
        "pending_samples": pending_samples,
        # IPD stats
        "total_beds": total_beds,
        "occupied_beds": occupied_beds,
        "available_beds": available_beds,
        "reserved_beds": reserved_beds,
        "bed_occupancy_percentage": round(bed_occupancy_percentage, 1),
        "total_wards": total_wards,
        "active_wards": active_wards,
        "current_admissions": current_admissions,
        "admissions_today": admissions_today,
        "discharges_today": discharges_today
    }
    return templates.TemplateResponse("index.html", context)

@router.get("/patients/register", name="register_patient")
def get_patient_registration_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Front Office", "Nurse", "Finance", "Admin"])) 
):
    """Unified registration/check-in: new patient or start visit for existing patient."""
    from app.crud import insurance_provider_crud, department_crud, hospital_settings_crud, service_pricing_crud
    
    # Get active insurance providers for dropdown
    insurance_providers = insurance_provider_crud.get_insurance_providers(db, active_only=True)
    # Get active departments for clinical routing
    departments, _ = department_crud.get_departments(db, limit=100, active_only=True)
    # Get consultation service pricing for the pricing dropdown - filter by charge_type=opd
    consultation_pricing = service_pricing_crud.get_service_pricing_by_charge_type(db, "opd")
    # Get hospital settings including insurance configuration
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    # Determine which payment mechanisms are enabled
    nhis_enabled = hospital_settings.nhis_enabled if hospital_settings else True
    private_insurance_enabled = hospital_settings.private_insurance_enabled if hospital_settings else True
    
    context = {
        "request": request,
        "title": "Patient Registration",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "insurance_providers": insurance_providers,
        "departments": departments,
        "consultation_pricing": consultation_pricing,
        "nhis_enabled": nhis_enabled,
        "private_insurance_enabled": private_insurance_enabled
    }
    return templates.TemplateResponse("front_office/register_patient.html", context)


@router.get("/patients/{patient_id}/registration-success", name="registration_success")
def registration_success_page(
    request: Request,
    patient_id: int,
    service_pricing_id: int = Query(..., description="Service pricing ID for consultation fee"),
    department: Optional[str] = Query(None, description="Department for clinical routing"),
    from_registration: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Front Office", "Nurse", "Admin"])),
):
    """After registration: show patient ID and number for writing on paper, then collect payment (cash only)."""
    patient_data = patient_crud.get_patient(db, patient_id=patient_id)
    if not patient_data:
        return RedirectResponse(url="/patients/register", status_code=status.HTTP_302_FOUND)
    from urllib.parse import quote
    from app.crud import service_pricing_crud
    from decimal import Decimal
    
    # Get service pricing to determine the consultation fee
    service_pricing_obj = service_pricing_crud.get_service_pricing(db, service_pricing_id)
    if service_pricing_obj:
        consultation_fee = Decimal(str(service_pricing_obj.unit_price))
        service_name = service_pricing_obj.service_name
    else:
        from app.services.charge_automation import DEFAULT_CONSULTATION_FEE
        consultation_fee = DEFAULT_CONSULTATION_FEE
        service_name = "Consultation Fee"
    
    # Use department for clinical routing if provided
    department_clean = (department or "").strip() or "General Medicine"
    
    pay_url = f"/patients/{patient_id}/pay/consultation?service_pricing_id={service_pricing_id}&return_to=dashboard&from_registration=1&new_visit=true"
    if department:
        pay_url += f"&department={quote(department)}"
    
    context = {
        "request": request,
        "title": "Patient registered",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient_data,
        "department": department_clean,
        "service_pricing_id": service_pricing_id,
        "service_name": service_name,
        "consultation_fee": float(consultation_fee) if consultation_fee else None,
        "pay_url": pay_url,
    }
    return templates.TemplateResponse("front_office/registration_success.html", context)


# NEW: Triage Page Route
@router.get("/patients/{patient_id}/triage", name="patient_triage")
def get_patient_triage_page(
    request: Request,
    patient_id: int,
    new_visit: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    # FIX: Dependency syntax is now simplified
    current_user = Depends(role_required(["Front Office", "Nurse", "Doctor", "Clinician", "Admin"])) 
):
    """
    Renders the Patient Triage page.
    For returning patients (new_visit=true), ensures a new consultation charge is created for this visit.
    """
    from app.utils.payment_verification import (
        check_payment_required_and_paid,
        is_cash_patient,
        is_patient_admitted,
        has_paid_for_service
    )
    from app.models.billing_models import ChargeType, InvoiceStatus
    from datetime import datetime, timedelta, date
    from sqlalchemy import func
    from decimal import Decimal
    
    # Fetch Patient Details
    patient_data = patient_crud.get_patient(db, patient_id=patient_id)
    if not patient_data:
        # Redirect to dashboard if patient not found
        return RedirectResponse(url=request.url_for("dashboard"), status_code=status.HTTP_302_FOUND)
    
    # Ensure OPD visit exists when landing with appointment_id (e.g. emergency registration)
    # so the visit appears on Emergency/OPD dashboards and has correct visit_type from appointment
    appointment_id_param = request.query_params.get("appointment_id")
    if appointment_id_param:
        try:
            aid = int(appointment_id_param)
            from app.crud import opd_crud
            from app.services.opd_validation import auto_link_opd_visit
            if not opd_crud.get_active_opd_visit_by_patient(db, patient_id):
                auto_link_opd_visit(db, patient_id, aid)
        except (ValueError, TypeError):
            pass
    
    # Check if this is a new visit (returning patient) vs appointment
    # Initialize is_new_visit from explicit parameter
    is_new_visit = new_visit and new_visit.lower() == 'true'
    
    # If accessing from patient list without appointment_id, check if it's a returning patient
    appointment_id = request.query_params.get("appointment_id")
    is_coming_from_list = not appointment_id and not is_new_visit
    
    # Front office check: Determine if this is a new visit or appointment
    # If appointment_id exists, it's an appointment (not a new visit)
    # If no appointment_id and patient has previous encounters, it's a new visit
    is_appointment = bool(appointment_id)
    if not is_appointment and not is_new_visit:
        # Check if patient has previous encounters/appointments
        from app.models.encounter_models import Encounter
        from app.models.scheduled_appointment_models import Appointment
        has_previous_encounters = db.query(Encounter).filter(
            Encounter.patient_id == patient_id,
            Encounter.is_active == True
        ).count() > 0
        has_previous_appointments = db.query(Appointment).filter(
            Appointment.patient_id == patient_id,
            Appointment.is_active == True
        ).count() > 0
        
        if has_previous_encounters or has_previous_appointments:
            is_new_visit = True
    
    # For returning cash patients accessing from patient list, automatically treat as new visit
    # This ensures each visit requires a new consultation fee payment, even on the same day
    if is_coming_from_list and is_cash_patient(db, patient_id):
        # Check if patient has a completed encounter today
        from app.models.encounter_models import Encounter, EncounterStatus
        from sqlalchemy import func
        from datetime import date
        
        today = date.today()
        completed_encounters_today = db.query(Encounter).filter(
            Encounter.patient_id == patient_id,
            Encounter.status == EncounterStatus.COMPLETED.value,
            Encounter.is_active == True,
            func.date(Encounter.encounter_date) == today
        ).count()
        
        # If there's a completed encounter today, this is a new visit requiring new payment
        if completed_encounters_today > 0:
            is_new_visit = True
    
    # Check if payment was just completed or vitals were saved (from redirect)
    status_param = request.query_params.get('status')
    payment_success = status_param == 'payment_success'
    vitals_saved = status_param == 'vitals_saved'
    
    # If vitals were saved, payment must have been made, so check for it
    needs_payment_check = payment_success or vitals_saved
    
    # Check payment requirement for cash patients
    # Consultation fee now covers both vitals and encounter
    payment_required = False
    payment_paid = True
    charge = None
    invoice = None
    
    # For new visits, check for TODAY's consultation payment only
    # For returning patients, we need a NEW consultation charge for THIS visit
    if is_cash_patient(db, patient_id):
        # If payment was just completed or vitals were saved, force a fresh check
        if needs_payment_check:
            # Re-check payment status after successful payment or vitals saved
            # Check for any consultation invoices with payments
            from datetime import timedelta
            from app.models.billing_models import Charge, Invoice, Payment, PaymentStatus, InvoiceStatus
            
            # Look for any consultation charges, then check if they have payments
            recent_charges = db.query(Charge).join(Invoice).filter(
                Invoice.patient_id == patient_id,
                Charge.charge_type == ChargeType.CONSULTATION,
                Charge.encounter_id.is_(None),
                Invoice.is_active == True
            ).order_by(Charge.created_at.desc()).limit(5).all()
            
            recent_paid_charge = None
            has_paid = False
            for ch in recent_charges:
                # Check all payments on this invoice (not just recent ones)
                # If vitals were saved, payment must have been made, so check all payments
                all_payments = db.query(Payment).filter(
                    Payment.invoice_id == ch.invoice_id,
                    Payment.status == PaymentStatus.COMPLETED,
                    Payment.is_active == True
                ).all()
                
                if all_payments:
                    total_paid_all = sum(p.amount for p in all_payments)
                    
                    if total_paid_all >= ch.total_amount:
                        recent_paid_charge = ch
                        has_paid = True
                        break
            
            if recent_paid_charge:
                charge = recent_paid_charge
                invoice = recent_paid_charge.invoice
            else:
                # Fallback: check for today's charges using the standard method
                has_paid, charge, invoice = has_paid_for_service(
                    db, patient_id, ChargeType.CONSULTATION,
                    encounter_id=None,
                    check_today_only=True
                )
            
            payment_required = True
            payment_paid = has_paid
        else:
            # For new visits (returning patients), ALWAYS create a NEW charge for THIS visit
            completed_encounters_today = 0  # Default value for else branch
            if is_new_visit:
                try:
                    from app.services.charge_automation import create_charge_for_consultation
                    from app.models.encounter_models import Encounter, EncounterStatus
                    from sqlalchemy import func
                    from datetime import date
                    
                    logger.debug(f"[CHARGE_DBG] Patient {patient_id}: is_new_visit={is_new_visit}, is_cash_patient=True")
                    
                    # Get the opd_visit_id from query params if available
                    opd_visit_id_param = request.query_params.get("opd_visit_id")
                    opd_visit_id = int(opd_visit_id_param) if opd_visit_id_param else None
                    
                    # Check if there's a completed encounter today
                    today = date.today()
                    completed_encounters_today = db.query(Encounter).filter(
                        Encounter.patient_id == patient_id,
                        Encounter.status == EncounterStatus.COMPLETED.value,
                        Encounter.is_active == True,
                        func.date(Encounter.encounter_date) == today
                    ).count()
                    logger.debug(f"[CHARGE_DBG] Patient {patient_id}: completed_encounters_today={completed_encounters_today}")
                    
                    # FIX: First check if there's already a consultation charge for this encounter
                    # This prevents duplicates by reusing existing charges
                    from app.models.billing_models import Charge, Invoice
                    existing_encounter_charge = db.query(Charge).join(Invoice).filter(
                        Invoice.patient_id == patient_id,
                        Charge.charge_type == ChargeType.CONSULTATION,
                        Invoice.is_active == True
                    )
                    
                    # Check by opd_visit_id or encounter_id
                    if opd_visit_id:
                        existing_encounter_charge = existing_encounter_charge.filter(
                            (Charge.opd_visit_id == opd_visit_id) | 
                            (Charge.encounter_id.is_(None) & (Invoice.opd_visit_id == opd_visit_id))
                        )
                    
                    existing_encounter_charge = existing_encounter_charge.order_by(Charge.created_at.desc()).first()
                    
                    logger.debug(f"[CHARGE_DBG] Patient {patient_id}: existing_encounter_charge={'Found ID ' + str(existing_encounter_charge.id) if existing_encounter_charge else 'None'}")
                    
                    # If there's an existing charge for this encounter, use it
                    if existing_encounter_charge:
                        charge = existing_encounter_charge
                        invoice = existing_encounter_charge.invoice
                        payment_paid = (invoice.balance <= Decimal('0')) or (invoice.status == InvoiceStatus.PAID)
                        logger.info(f"[CHARGE_DBG] Patient {patient_id}: Reusing existing encounter charge {existing_encounter_charge.id}")
                    else:
                        # No existing charge for this encounter - create a new one using create_charge_for_consultation
                        # This function has proper duplicate checking
                        logger.info(f"[CHARGE_DBG] Patient {patient_id}: No existing charge for encounter, creating new one via create_charge_for_consultation")
                        charge = create_charge_for_consultation(
                            db, patient_id, current_user.id, 
                            encounter_id=None, 
                            opd_visit_id=opd_visit_id
                        )
                        if charge:
                            invoice = charge.invoice
                            payment_paid = False  # New charge is unpaid
                        else:
                            payment_paid = False
                    
                    payment_required = True
                except Exception as billing_error:
                    print(f"Warning: Unable to create consultation charge for patient {patient_id}: {billing_error}")
                    import traceback
                    traceback.print_exc()
                    # Fallback: check for any existing charge
                    has_paid, charge, invoice = has_paid_for_service(
                        db, patient_id, ChargeType.CONSULTATION,
                        encounter_id=None,
                        check_today_only=False
                    )
                    payment_required = True
                    payment_paid = has_paid
                else:
                    logger.debug(f"[CHARGE_DBG] Patient {patient_id}: is_new_visit={is_new_visit}, completed_encounters_today={completed_encounters_today}")
                    
                    # If there's a completed encounter today, this is a new visit requiring new payment
                    if completed_encounters_today > 0:
                        # Treat as new visit - create new charge
                        try:
                            from app.services.charge_automation import create_charge_for_consultation
                            logger.info(f"[CHARGE_DBG] Patient {patient_id}: Completed encounter today, creating new charge via create_charge_for_consultation")
                            # Get opd_visit_id for consistency
                            opd_visit_id_param = request.query_params.get("opd_visit_id")
                            opd_visit_id = int(opd_visit_id_param) if opd_visit_id_param else None
                            charge = create_charge_for_consultation(db, patient_id, current_user.id, encounter_id=None, opd_visit_id=opd_visit_id)
                            if charge:
                                invoice = charge.invoice
                                payment_paid = (invoice.balance <= Decimal('0')) or (invoice.status == InvoiceStatus.PAID)
                                logger.info(f"[CHARGE_DBG] Patient {patient_id}: Created charge {charge.id} via completed_encounters path")
                            else:
                                payment_paid = False
                            payment_required = True
                        except Exception as billing_error:
                            print(f"Warning: Unable to create consultation charge for patient {patient_id}: {billing_error}")
                            payment_required = True
                            payment_paid = False
                    else:
                        # No completed encounter today - check for today's consultation payment
                        has_paid, charge, invoice = has_paid_for_service(
                            db, patient_id, ChargeType.CONSULTATION,
                            encounter_id=None,
                            check_today_only=True  # Only check for today's charges
                        )
                        
                        logger.debug(f"[CHARGE_DBG] Patient {patient_id}: has_paid={has_paid}, charge={'Found ID ' + str(charge.id) if charge else 'None'}")
                        
                        payment_required = True
                        payment_paid = has_paid
                        
                        # If no charge exists for today, create one
                        if not charge:
                            try:
                                from app.services.charge_automation import create_charge_for_consultation
                                logger.info(f"[CHARGE_DBG] Patient {patient_id}: No existing charge today, creating new one")
                                charge = create_charge_for_consultation(db, patient_id, current_user.id, encounter_id=None)
                                if charge:
                                    invoice = charge.invoice
                                    logger.info(f"[CHARGE_DBG] Patient {patient_id}: Created charge {charge.id} via no_existing_charge path")
                                payment_paid = False
                            except Exception as billing_error:
                                print(f"Warning: Unable to seed consultation charge for patient {patient_id}: {billing_error}")
    else:
        # For insurance patients (NHIS or Private Insurance), create consultation charge and add to their bill
        if is_new_visit:
            try:
                from app.services.charge_automation import create_charge_for_consultation
                # Create consultation charge - it will be added to their insurance claim
                charge = create_charge_for_consultation(db, patient_id, current_user.id, encounter_id=None)
                if charge:
                    invoice = charge.invoice
                    # For insurance patients, payment is not required upfront
                    payment_required = False
                    payment_paid = True  # Consider it "paid" since it goes to insurance
            except Exception as billing_error:
                print(f"Warning: Unable to create consultation charge for insurance patient {patient_id}: {billing_error}")
    
    # Triage page: Do NOT require payment before recording vitals for any cash patient.
    # OPD cash: pay later before check-in. IPD cash: vitals are for monitoring (same as from_admission in API).
    if is_cash_patient(db, patient_id):
        payment_required = False
        
    # Get doctors on duty for appointment assignment
    from app.crud import ipd_crud
    doctors_on_duty = ipd_crud.get_doctors_on_duty(db)
    
    # Get all clinicians for manual assignment
    from app.models.user_models import User
    from sqlalchemy.orm import joinedload
    try:
        from app.models.role_models import Role
        clinicians = db.query(User).options(joinedload(User.role)).join(Role).filter(Role.name.in_(["Clinician", "Admin"])).all()
    except Exception as e:
        # Fallback: get all users and filter by role name in Python
        all_users = db.query(User).options(joinedload(User.role)).all()
        clinicians = [u for u in all_users if u.role and u.role.name in ["Clinician", "Admin"]]
    
    # Check if patient has recent vitals (within last hour) to show check-in button
    from app.models.triage_models import TriageVitals
    from datetime import timedelta
    recent_vitals_raw = db.query(TriageVitals).filter(
        TriageVitals.patient_id == patient_id
    ).order_by(TriageVitals.recorded_at.desc()).first()
    
    has_recent_vitals = False
    recent_vitals = None
    has_previous_vitals = False
    if recent_vitals_raw:
        has_previous_vitals = True
        time_diff = datetime.now() - recent_vitals_raw.recorded_at
        has_recent_vitals = time_diff < timedelta(hours=1)
        # Only pre-populate form when vitals were recorded in last 15 min (same session).
        # For revisit/follow-up, nurse must enter NEW vitals - do not show old values.
        if time_diff < timedelta(minutes=15):
            recent_vitals = recent_vitals_raw
    
    # Check if patient is already checked in (has appointment with checked_in status)
    from app.models.scheduled_appointment_models import Appointment, AppointmentStatus
    checked_in_appointment = db.query(Appointment).filter(
        Appointment.patient_id == patient_id,
        Appointment.status == AppointmentStatus.CHECKED_IN,
        Appointment.is_active == True,
        func.date(Appointment.scheduled_date) == datetime.now().date()
    ).first()
    
    # Determine if patient is cash (for template to check check-in requirements)
    is_cash_patient_flag = is_cash_patient(db, patient_id)
    
    context = {
        "request": request,
        "title": f"Triage - {patient_data.first_name} {patient_data.last_name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient_data,
        "doctors_on_duty": doctors_on_duty,
        "clinicians": clinicians,
        "payment_required": payment_required,
        "payment_paid": payment_paid,
        "is_cash_patient": is_cash_patient_flag,
        "charge": charge,
        "invoice": invoice,
        "has_recent_vitals": has_recent_vitals,
        "recent_vitals": recent_vitals,
        "has_previous_vitals": has_previous_vitals,
        "checked_in_appointment": checked_in_appointment,
        "from_admission": request.query_params.get("from_admission"),  # IPD: redirect back to admission after recording
    }
    return templates.TemplateResponse("front_office/triage_page.html", context)


# Clinical Encounter Routes
@router.get("/patients/{patient_id}/encounters/new", name="new_encounter")
def get_new_encounter_page(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Clinician", "Admin"]))
):
    """
    Renders the page for creating a new clinical encounter.
    Only doctors/clinicians (and admins) can create encounters. Front desk and nurses should check in patients to the doctor's queue instead.
    """
    from app.crud import patient_crud, appointment_crud, disease_crud
    from app.utils.payment_verification import (
        check_payment_required_and_paid,
        is_cash_patient,
        requires_payment_before_service,
        has_paid_for_service
    )
    from app.models.billing_models import ChargeType
    from app.models.scheduled_appointment_models import AppointmentStatus
    
    # Fetch Patient Details
    patient_data = patient_crud.get_patient(db, patient_id=patient_id)
    if not patient_data:
        return RedirectResponse(url=request.url_for("dashboard"), status_code=status.HTTP_302_FOUND)
    
    # Fetch appointment if provided in query params
    appointment_data = None
    appointment_id = request.query_params.get("appointment_id")
    if appointment_id:
        try:
            appointment_data = appointment_crud.get_appointment(db, int(appointment_id))
        except (ValueError, TypeError):
            pass
    
    # Get admission_id from query params (for IPD encounters)
    admission_id = request.query_params.get("admission_id")
    if admission_id:
        try:
            admission_id = int(admission_id)
        except (ValueError, TypeError):
            admission_id = None
    
    # For IPD encounters, skip triage/payment verification - IPD patients don't need these
    is_ipd_encounter = admission_id is not None
    
    checked_in_statuses = {AppointmentStatus.CHECKED_IN, AppointmentStatus.IN_PROGRESS}
    active_appointment = None
    
    if not is_ipd_encounter:
        # Verify complete workflow: vitals + check-in + payment (for OPD encounters only)
        from app.utils.payment_verification import verify_encounter_workflow
        
        workflow_complete, missing_step, vitals_record, appointment_record, payment_info = verify_encounter_workflow(
            db, patient_id, check_vitals=True, check_checkin=True, check_payment=True
        )
        
        if not workflow_complete:
            triage_url = request.url_for("patient_triage", patient_id=patient_id)
            status_param = "checkin_required"
            if missing_step == "vitals":
                status_param = "vitals_required"
            elif missing_step == "payment":
                status_param = "payment_required"
            return RedirectResponse(
                url=f"{triage_url}?status={status_param}",
                status_code=status.HTTP_302_FOUND
            )
        
        # Use the verified appointment record
        appointment_data = appointment_record or appointment_data
        
        # Extract payment info from workflow verification
        payment_paid, charge, invoice = payment_info if payment_info else (True, None, None)
        payment_required = not payment_paid and is_cash_patient(db, patient_id)
    else:
        # IPD encounter - no payment/triage required
        payment_paid = True
        charge = None
        invoice = None
        payment_required = False

    # Load diseases for dropdowns
    try:
        all_diseases = disease_crud.get_diseases(db, skip=0, limit=10000)  # Increased limit
        if all_diseases is None:
            all_diseases = []
        
        # Filter out diseases with empty/null names, IDs, or None values
        diseases = [
            d for d in all_diseases 
            if d is not None 
            and hasattr(d, 'id') 
            and d.id is not None 
            and hasattr(d, 'name') 
            and d.name is not None 
            and str(d.name).strip() != ''
        ]
    except Exception as e:
        print(f"Error loading diseases: {e}")
        diseases = []
    
    # Get active OPD visit if any (kept for opd_visit_id hidden input if needed by encounter create)
    from app.crud import opd_crud
    active_opd_visit = opd_crud.get_active_opd_visit_by_patient(db, patient_id)
    
    # Get recent vitals for display (last 2 days, up to 10 records)
    from app.models.triage_models import TriageVitals
    from datetime import timedelta
    from sqlalchemy.orm import joinedload
    yesterday = date.today() - timedelta(days=1)
    recent_vitals_list = db.query(TriageVitals).options(
        joinedload(TriageVitals.recorded_by)
    ).filter(
        TriageVitals.patient_id == patient_id,
        TriageVitals.recorded_at >= datetime.combine(yesterday, datetime.min.time())
    ).order_by(TriageVitals.recorded_at.desc()).limit(10).all()
    
    # Get OPD visit ID from query params if provided
    opd_visit_id = request.query_params.get("opd_visit_id")
    if opd_visit_id:
        try:
            opd_visit = opd_crud.get_opd_visit(db, int(opd_visit_id))
            if opd_visit and opd_visit.patient_id == patient_id:
                active_opd_visit = opd_visit
        except (ValueError, TypeError):
            pass
    
    # Get queue_entry_id from query params if provided
    queue_entry_id = request.query_params.get("queue_entry_id")
    
    # Sync payment status for active OPD visit (fixes cases where payment was made before auto-update was added)
    if active_opd_visit:
        opd_crud.sync_opd_visit_payment_status(db, active_opd_visit.id)
        # Refresh the visit to get updated status
        db.refresh(active_opd_visit)

    context = {
        "request": request,
        "title": f"New Encounter - {patient_data.first_name} {patient_data.last_name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient_data,
        "appointment": appointment_data,
        "queue_entry_id": queue_entry_id,
        "admission_id": admission_id,
        "active_opd_visit": active_opd_visit,
        "recent_vitals": recent_vitals_list,
        "payment_required": payment_required,
        "payment_paid": payment_paid,
        "charge": charge,
        "invoice": invoice,
        "diseases": diseases or [],  # Ensure it's always a list
        "has_checked_in_appointment": appointment_data is not None
    }
    return templates.TemplateResponse("clinical/new_encounter.html", context)


@router.get("/encounters/today", name="pending_encounters")
def get_pending_encounters_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"])),
    search: Optional[str] = Query(None)
):
    """
    Renders a page showing pending (in-progress) encounters for today and previous days with search functionality.
    """
    from app.crud import appointment_crud
    from app.models.encounter_models import Encounter, EncounterStatus
    from app.models.patient_models import Patient
    from sqlalchemy.orm import joinedload
    from sqlalchemy import or_, func, String
    from datetime import datetime, date, timedelta
    
    # Get today's date
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Base query for in-progress encounters from today with eager loading
    query_today = db.query(Encounter).options(
        joinedload(Encounter.patient),
        joinedload(Encounter.clinician),
        joinedload(Encounter.appointment)
    ).filter(
        Encounter.status.in_([EncounterStatus.IN_PROGRESS.value, EncounterStatus.DETAINED.value]),
        Encounter.is_active == True,
        Encounter.encounter_date >= today_start,
        Encounter.encounter_date < today_end
    )
    
    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        # Join with Patient table for search
        query_today = query_today.join(Patient, Encounter.patient_id == Patient.id).filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                func.concat(Patient.first_name, " ", Patient.last_name).ilike(search_term),
                Patient.patient_number.ilike(search_term),
                Patient.national_id.ilike(search_term),
                Patient.phone_number.ilike(search_term),
                func.cast(Patient.id, String).ilike(search_term),
                func.cast(Encounter.id, String).ilike(search_term),  # Search by encounter ID
                Encounter.chief_complaint.ilike(search_term)
            )
        )
    
    encounters_today = query_today.order_by(Encounter.encounter_date.desc()).all()
    
    # Get unfulfilled encounters from previous days (last 7 days)
    start_date = today_start - timedelta(days=7)
    query_previous = db.query(Encounter).options(
        joinedload(Encounter.patient),
        joinedload(Encounter.clinician),
        joinedload(Encounter.appointment)
    ).filter(
        Encounter.status.in_([EncounterStatus.IN_PROGRESS.value, EncounterStatus.DETAINED.value]),
        Encounter.is_active == True,
        Encounter.encounter_date >= start_date,
        Encounter.encounter_date < today_start
    )
    
    # Apply search filter to previous days' encounters if provided
    if search:
        search_term = f"%{search}%"
        query_previous = query_previous.join(Patient, Encounter.patient_id == Patient.id).filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                func.concat(Patient.first_name, " ", Patient.last_name).ilike(search_term),
                Patient.patient_number.ilike(search_term),
                Patient.national_id.ilike(search_term),
                Patient.phone_number.ilike(search_term),
                func.cast(Patient.id, String).ilike(search_term),
                func.cast(Encounter.id, String).ilike(search_term),
                Encounter.chief_complaint.ilike(search_term)
            )
        )
    
    encounters_previous = query_previous.order_by(Encounter.encounter_date.asc()).all()
    
    # Calculate wait times for today's encounters
    encounters_today_with_wait = []
    for encounter in encounters_today:
        # Use encounter_date or started_at for wait time calculation
        start_time = encounter.started_at or encounter.encounter_date
        if start_time:
            wait_time = datetime.now() - start_time
            wait_time_str = appointment_crud.format_wait_time(wait_time)
        else:
            wait_time = None
            wait_time_str = "N/A"
        encounters_today_with_wait.append({
            "encounter": encounter,
            "wait_time": wait_time,
            "wait_time_str": wait_time_str
        })
    
    # Calculate wait times for previous days' encounters
    encounters_previous_with_wait = []
    for encounter in encounters_previous:
        start_time = encounter.started_at or encounter.encounter_date
        if start_time:
            wait_time = datetime.now() - start_time
            wait_time_str = appointment_crud.format_wait_time(wait_time)
        else:
            wait_time = None
            wait_time_str = "N/A"
        encounters_previous_with_wait.append({
            "encounter": encounter,
            "wait_time": wait_time,
            "wait_time_str": wait_time_str
        })
    
    context = {
        "request": request,
        "title": "Pending Encounters",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "encounters_today": encounters_today_with_wait,
        "encounters_previous": encounters_previous_with_wait,
        "today": today,
        "search_query": search or ""
    }
    return templates.TemplateResponse("clinical/pending_encounters.html", context)


@router.get("/encounters/{encounter_id}", name="view_encounter")
def get_encounter_page(
    request: Request,
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    """
    Renders the page for viewing/editing a clinical encounter.
    """
    from app.crud import encounter_crud
    from app.utils.patient_utils import calculate_age
    
    # Fetch Encounter with orders
    encounter_data = encounter_crud.get_encounter_with_orders(db, encounter_id)
    if not encounter_data:
        return RedirectResponse(url=request.url_for("dashboard"), status_code=status.HTTP_302_FOUND)
    
    # Load schema_json for each lab order with template
    from app.models.lab_template_models import LabTemplateVersion
    for order in (encounter_data.lab_orders or []):
        if order.template_id and order.template_version_used:
            version = db.query(LabTemplateVersion).filter(
                LabTemplateVersion.template_id == order.template_id,
                LabTemplateVersion.version == order.template_version_used,
                LabTemplateVersion.status == 'PUBLISHED'
            ).first()
            if version:
                order._schema_json = version.schema_json
            else:
                order._schema_json = None
        else:
            order._schema_json = None
    
    # Calculate patient age
    patient_age = calculate_age(encounter_data.patient.date_of_birth)
    
    # Check for pending orders
    from app.models.encounter_models import LabOrder, RadiologyOrder, OrderStatus
    pending_lab_orders = [order for order in (encounter_data.lab_orders or []) 
                         if order.status in [OrderStatus.PENDING, OrderStatus.ORDERED, OrderStatus.IN_PROGRESS]]
    pending_radiology_orders = [order for order in (encounter_data.radiology_orders or []) 
                              if order.status in [OrderStatus.PENDING, OrderStatus.ORDERED, OrderStatus.IN_PROGRESS]]
    
    # Get service pricing dropdowns
    from app.crud import service_pricing_crud
    from app.models.procedure_catalog_models import ProcedureCatalog
    procedure_catalogs = db.query(ProcedureCatalog).filter(
        ProcedureCatalog.is_active == True
    ).order_by(ProcedureCatalog.procedure_name).all()
    # Create a list of dicts with id and name for the dropdown
    procedure_catalog_list = [{"id": p.id, "name": p.procedure_name, "cash_price": float(p.cash_price) if p.cash_price else 0} for p in procedure_catalogs]
    procedure_pricing = service_pricing_crud.get_service_pricing_by_charge_type(db, "procedure")
    procedure_names = [p.service_name for p in procedure_pricing if p.is_active]
    lab_service_pricing = service_pricing_crud.get_service_pricing_by_charge_type(db, "lab_test")
    radiology_service_pricing = service_pricing_crud.get_service_pricing_by_charge_type(db, "radiology")
    antenatal_service_pricing = service_pricing_crud.get_service_pricing_by_charge_type(db, "antenatal")
    
    # Get Lab Test Catalog for order selection
    from app.models.lab_catalog_models import LabTest
    lab_tests = db.query(LabTest).filter(LabTest.is_active == True).order_by(LabTest.test_name).all()
    
    # Get existing procedures for this encounter
    from app.crud import procedure_crud
    procedures, _ = procedure_crud.get_procedures(db, encounter_id=encounter_id, limit=100)
    
    # Check if patient is currently admitted
    from app.crud import ipd_crud
    from app.models.ipd_models import AdmissionStatus
    current_admission = ipd_crud.get_current_admission(db, encounter_data.patient_id)
    is_admitted = current_admission is not None and current_admission.status == AdmissionStatus.ADMITTED
    
    # List antenatal charges already applied to this encounter
    from app.models.billing_models import Charge, ChargeType
    antenatal_charges = db.query(Charge).filter(
        Charge.encounter_id == encounter_id,
        Charge.charge_type == ChargeType.ANTENATAL
    ).order_by(Charge.created_at.desc()).all()

    # Parse secondary diagnosis codes from JSON
    secondary_diagnoses = []
    if encounter_data.secondary_diagnosis_codes:
        try:
            secondary_diagnoses = json.loads(encounter_data.secondary_diagnosis_codes)
        except (json.JSONDecodeError, TypeError):
            # If parsing fails, treat as plain text
            secondary_diagnoses = [{"description": encounter_data.secondary_diagnosis_codes}]
    
    # Get encounter diseases from encounter_diseases table
    from app.crud import disease_crud
    from app.models.disease_models import EncounterDisease
    from sqlalchemy.orm import joinedload
    
    # Load encounter diseases with disease relationship
    encounter_diseases_list = db.query(EncounterDisease).options(
        joinedload(EncounterDisease.disease)
    ).filter(EncounterDisease.encounter_id == encounter_id).all()
    
    # Format encounter diseases for display
    formatted_diagnoses = []
    for enc_disease in encounter_diseases_list:
        if enc_disease.disease_id and enc_disease.disease:
            # Disease from database
            diagnosis_info = {
                "id": enc_disease.disease.id,
                "name": enc_disease.disease.name,
                "code": enc_disease.disease.code,
                "is_primary": enc_disease.is_primary,
                "custom_name": None
            }
        elif enc_disease.custom_name:
            # Custom disease
            diagnosis_info = {
                "id": None,
                "name": enc_disease.custom_name,
                "code": None,
                "is_primary": enc_disease.is_primary,
                "custom_name": enc_disease.custom_name
            }
        else:
            # Skip if neither disease nor custom_name
            continue
        formatted_diagnoses.append(diagnosis_info)
    
    # Sort: primary first, then by name
    formatted_diagnoses.sort(key=lambda x: (not x["is_primary"], x["name"] or ""))
    
    from datetime import timedelta
    from app.models.triage_models import TriageVitals
    
    # Get hospital settings for print header
    from app.crud import hospital_settings_crud
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    # Get addendums for this encounter
    from app.crud import encounter_crud
    addendums = encounter_crud.get_addendums_by_encounter(db, encounter_id)
    
    # Recent/visit vitals for this patient (for doctor to see on encounter page)
    yesterday = date.today() - timedelta(days=1)
    recent_vitals = db.query(TriageVitals).filter(
        TriageVitals.patient_id == encounter_data.patient_id,
        TriageVitals.recorded_at >= datetime.combine(yesterday, datetime.min.time())
    ).order_by(TriageVitals.recorded_at.desc()).limit(10).all()
    
    # Load diseases for diagnosis selection in edit form
    try:
        all_diseases = disease_crud.get_diseases(db, skip=0, limit=10000)
        if all_diseases is None:
            all_diseases = []
        diseases_list = [
            d for d in all_diseases
            if d is not None
        ]
    except Exception as e:
        print(f"Error loading diseases: {e}")
        diseases_list = []
    
    context = {
        "request": request,
        "title": f"Encounter #{encounter_id}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "encounter": encounter_data,
        "patient": encounter_data.patient,
        "patient_age": patient_age,
        "pending_lab_orders": pending_lab_orders,
        "pending_radiology_orders": pending_radiology_orders,
        "has_pending_orders": len(pending_lab_orders) > 0 or len(pending_radiology_orders) > 0,
        "procedure_names": procedure_names,
        "procedure_catalogs": procedure_catalog_list,
        "procedures": procedures,
        "lab_services": lab_service_pricing,
        "lab_tests": lab_tests,  # Lab Test Catalog for order selection
        "radiology_services": radiology_service_pricing,
        "antenatal_services": antenatal_service_pricing,
        "antenatal_charges": antenatal_charges,
        "is_admitted": is_admitted,
        "current_admission": current_admission,
        "secondary_diagnoses": secondary_diagnoses,
        "encounter_diseases": formatted_diagnoses,
        "diseases": diseases_list,
        "date": date,
        "timedelta": timedelta,
        "hospital_settings": hospital_settings,
        "datetime": datetime,
        "current_time": datetime.utcnow(),
        "recent_vitals": recent_vitals,
        "addendums": addendums,
    }
    return templates.TemplateResponse("clinical/view_encounter.html", context)


@router.get("/encounters/{encounter_id}/print", name="print_encounter")
def print_encounter_page(
    request: Request,
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    """
    Dedicated print-friendly view for clinical encounters.
    Returns a clean HTML page optimized for printing.
    """
    from app.utils.patient_utils import calculate_age
    from app.crud import hospital_settings_crud
    from datetime import datetime
    
    # Fetch Encounter with orders
    encounter_data = encounter_crud.get_encounter_with_orders(db, encounter_id)
    if not encounter_data:
        return RedirectResponse(url=request.url_for("dashboard"), status_code=status.HTTP_302_FOUND)
    
    # Calculate patient age
    patient_age = calculate_age(encounter_data.patient.date_of_birth)
    
    # Check for pending orders
    from app.models.encounter_models import LabOrder, RadiologyOrder, OrderStatus
    pending_lab_orders = [order for order in (encounter_data.lab_orders or []) 
                         if order.status in [OrderStatus.PENDING, OrderStatus.ORDERED, OrderStatus.IN_PROGRESS]]
    pending_radiology_orders = [order for order in (encounter_data.radiology_orders or []) 
                               if order.status in [OrderStatus.PENDING, OrderStatus.ORDERED, OrderStatus.IN_PROGRESS]]
    
    # Get existing procedures for this encounter
    from app.crud import procedure_crud
    procedures, _ = procedure_crud.get_procedures(db, encounter_id=encounter_id, limit=100)
    
    # Check if patient is currently admitted
    from app.crud import ipd_crud
    from app.models.ipd_models import AdmissionStatus
    current_admission = ipd_crud.get_current_admission(db, encounter_data.patient_id)
    is_admitted = current_admission is not None and current_admission.status == AdmissionStatus.ADMITTED
    
    # Parse secondary diagnosis codes from JSON
    secondary_diagnoses = []
    if encounter_data.secondary_diagnosis_codes:
        try:
            secondary_diagnoses = json.loads(encounter_data.secondary_diagnosis_codes)
        except (json.JSONDecodeError, TypeError):
            secondary_diagnoses = [{"description": encounter_data.secondary_diagnosis_codes}]
    
    # Get encounter diseases
    from app.crud import disease_crud
    from app.models.disease_models import EncounterDisease
    from sqlalchemy.orm import joinedload
    
    encounter_diseases_list = db.query(EncounterDisease).options(
        joinedload(EncounterDisease.disease)
    ).filter(EncounterDisease.encounter_id == encounter_id).all()
    
    formatted_diagnoses = []
    for enc_disease in encounter_diseases_list:
        if enc_disease.disease_id and enc_disease.disease:
            diagnosis_info = {
                "id": enc_disease.disease.id,
                "name": enc_disease.disease.name,
                "code": enc_disease.disease.code,
                "is_primary": enc_disease.is_primary,
                "custom_name": None
            }
        elif enc_disease.custom_name:
            diagnosis_info = {
                "id": None,
                "name": enc_disease.custom_name,
                "code": None,
                "is_primary": enc_disease.is_primary,
                "custom_name": enc_disease.custom_name
            }
        else:
            continue
        formatted_diagnoses.append(diagnosis_info)
    
    formatted_diagnoses.sort(key=lambda x: (not x["is_primary"], x["name"] or ""))
    
    # Get hospital settings
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": f"Encounter #{encounter_id} - Print",
        "encounter": encounter_data,
        "patient": encounter_data.patient,
        "patient_age": patient_age,
        "pending_lab_orders": pending_lab_orders,
        "pending_radiology_orders": pending_radiology_orders,
        "has_pending_orders": len(pending_lab_orders) > 0 or len(pending_radiology_orders) > 0,
        "procedures": procedures,
        "is_admitted": is_admitted,
        "current_admission": current_admission,
        "secondary_diagnoses": secondary_diagnoses,
        "encounter_diseases": formatted_diagnoses,
        "hospital_settings": hospital_settings,
        "datetime": datetime
    }
    return templates.TemplateResponse("clinical/print_encounter.html", context)


@router.get("/encounters/{encounter_id}/differentials/report", name="view_differential_report")
def view_differential_report(
    request: Request,
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    from app.utils.patient_utils import calculate_age

    encounter = encounter_crud.get_encounter_with_orders(db, encounter_id)
    if not encounter:
        return RedirectResponse(url=request.url_for("dashboard"), status_code=status.HTTP_302_FOUND)
    
    differential_data = encounter_crud.load_differential_data(encounter)
    if not differential_data:
        return RedirectResponse(
            url=request.url_for("view_encounter", encounter_id=encounter_id),
            status_code=status.HTTP_302_FOUND
        )
    
    suggestions = differential_data.get("suggestions", [])
    generated_at = _safe_parse_datetime(differential_data.get("generated_at"))
    patient_age = (
        calculate_age(encounter.patient.date_of_birth)
        if getattr(encounter.patient, "date_of_birth", None)
        else None
    )
    stats = {
        "total": len(suggestions),
        "working": sum(1 for s in suggestions if (s.get("status") or "").lower() == "working"),
        "ruled_out": sum(
            1 for s in suggestions if (s.get("status") or "").lower() in {"ruled_out", "ruled-out"}
        ),
    }
    stats["suggested"] = stats["total"] - stats["working"] - stats["ruled_out"]
    
    context = {
        "request": request,
        "title": f"Encounter #{encounter_id} Differential Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "encounter": encounter,
        "patient": encounter.patient,
        "clinician": encounter.clinician,
        "differential": differential_data,
        "generated_at": generated_at,
        "generated_at_display": generated_at.strftime("%Y-%m-%d %H:%M") if generated_at else None,
        "suggestions": suggestions,
        "stats": stats,
        "patient_age": patient_age,
    }
    return templates.TemplateResponse("clinical/differential_report.html", context)


@router.get("/encounters/differentials", name="differential_registry")
def differential_registry_page(
    request: Request,
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    records = encounter_crud.get_encounters_with_differentials(db, limit=limit)
    differential_entries = _build_differential_registry_rows(records)
    context = {
        "request": request,
        "title": "G-STG Differential Registry",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "differential_entries": differential_entries,
        "limit": limit,
    }
    return templates.TemplateResponse("clinical/differential_registry.html", context)


@router.get("/encounters/differentials/export", name="differential_registry_export")
def export_differential_registry(
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    records = encounter_crud.get_encounters_with_differentials(db, limit=limit)
    entries = _build_differential_registry_rows(records)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Encounter ID",
        "Patient Name",
        "Patient ID",
        "Clinician",
        "Generated At",
        "Summary",
        "Working Dx Count",
        "Rule Out Count",
        "Suggested Count",
        "Notes",
        "Diagnoses (status)"
    ])
    for entry in entries:
        clinician = entry.get("clinician")
        clinician_name = (
            (clinician.full_name or clinician.username)
            if clinician
            else "N/A"
        )
        statuses = [
            f"{suggestion.get('diagnosis')} ({suggestion.get('status', 'suggested')})"
            for suggestion in entry.get("suggestions", [])
        ]
        writer.writerow([
            entry["encounter"].id,
            f"{entry['patient'].first_name} {entry['patient'].last_name}",
            entry["patient"].id,
            clinician_name,
            entry.get("generated_at_display") or "",
            entry.get("summary", "").replace("\n", " "),
            entry["counts"]["working"],
            entry["counts"]["ruled_out"],
            entry["counts"]["suggested"],
            (entry.get("notes") or "").replace("\n", " "),
            "; ".join(statuses),
        ])
    
    output.seek(0)
    filename = f"gstg_differentials_{datetime.utcnow():%Y%m%d_%H%M}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/diseases", name="disease_report")
def disease_report_page(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=10, le=500),
    format: str = Query("html", regex="^(html|pdf|excel|csv)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Clinician", "Management", "Nurse"]))
):
    from fastapi.responses import Response
    
    start_date_parsed = _parse_date(start_date)
    end_date_parsed = _parse_date(end_date)
    
    start_dt = datetime.combine(start_date_parsed, datetime.min.time()) if start_date_parsed else None
    end_dt = datetime.combine(end_date_parsed, datetime.max.time()) if end_date_parsed else None
    
    stats = disease_crud.get_disease_encounter_stats(
        db,
        start_date=start_dt,
        end_date=end_dt,
        search=search,
        limit=limit
    )
    totals = {
        "diseases": len(stats),
        "encounters": sum(item["encounter_count"] for item in stats),
        "primary": sum(item["primary_count"] for item in stats),
    }
    for item in stats:
        item["primary_ratio"] = (
            round((item["primary_count"] / item["encounter_count"]) * 100, 1)
            if item["encounter_count"]
            else 0
        )
    
    context = {
        "request": request,
        "title": "Disease Encounter Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "stats": stats,
        "totals": totals,
        "filters": {
            "start_date": start_date_parsed,
            "end_date": end_date_parsed,
            "search": search or "",
            "limit": limit
        },
        "start_date": start_date,
        "end_date": end_date,
        "search": search,
        "limit": limit,
        "report_date": datetime.now()  # Add report_date for template
    }
    
    # Handle different formats
    if format == "pdf":
        from app.utils.pdf_generator import generate_disease_report_pdf
        pdf_content = generate_disease_report_pdf(context)
        start_str = start_date_parsed.strftime("%Y-%m-%d") if start_date_parsed else "all"
        end_str = end_date_parsed.strftime("%Y-%m-%d") if end_date_parsed else "all"
        filename = f"disease_report_{start_str}_{end_str}.pdf"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    elif format == "excel":
        from app.utils.excel_generator import generate_disease_report_excel
        excel_content = generate_disease_report_excel(context)
        start_str = start_date_parsed.strftime("%Y-%m-%d") if start_date_parsed else "all"
        end_str = end_date_parsed.strftime("%Y-%m-%d") if end_date_parsed else "all"
        filename = f"disease_report_{start_str}_{end_str}.xlsx"
        return Response(
            content=excel_content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    elif format == "csv":
        from app.utils.csv_generator import generate_disease_report_csv
        csv_content = generate_disease_report_csv(context)
        start_str = start_date_parsed.strftime("%Y-%m-%d") if start_date_parsed else "all"
        end_str = end_date_parsed.strftime("%Y-%m-%d") if end_date_parsed else "all"
        filename = f"disease_report_{start_str}_{end_str}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    
    return templates.TemplateResponse("reports/disease_report.html", context)
