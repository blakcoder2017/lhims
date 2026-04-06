"""
OPD/IPD Encounter Validation Service
Validates that encounters are properly linked to either OPD visits or IPD admissions.
"""
from sqlalchemy.orm import Session
from typing import Optional, Tuple
from app.models.opd_models import OPDVisit, OPDVisitStatus
from app.models.ipd_models import Admission, AdmissionStatus
from app.models.patient_models import Patient, PaymentMechanism


def validate_encounter_creation(
    db: Session,
    patient_id: int,
    opd_visit_id: Optional[int] = None,
    admission_id: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate that encounter can be created.
    
    Rules:
    1. Must have either opd_visit_id OR admission_id (not both, not neither)
    2. If OPD, verify payment (unless emergency/waived)
    3. If IPD, verify admission status
    
    Returns:
        (is_valid, error_message)
    """
    # Rule 1: Must have either opd_visit_id OR admission_id (not both, not neither)
    if not opd_visit_id and not admission_id:
        return False, "Encounter must be linked to either OPD visit or IPD admission"
    
    if opd_visit_id and admission_id:
        return False, "Encounter cannot be linked to both OPD visit and IPD admission"
    
    # Rule 2: If OPD, verify payment (unless emergency/waived)
    if opd_visit_id:
        opd_visit = db.query(OPDVisit).filter(
            OPDVisit.id == opd_visit_id,
            OPDVisit.is_active == True
        ).first()
        
        if not opd_visit:
            return False, f"OPD visit {opd_visit_id} not found"
        
        if opd_visit.status != OPDVisitStatus.ACTIVE:
            return False, f"OPD visit {opd_visit.opd_number} is not active"
        
        # Sync payment status (fixes cases where payment was made but status wasn't updated)
        from app.crud import opd_crud
        synced_visit = opd_crud.sync_opd_visit_payment_status(db, opd_visit_id)
        if synced_visit:
            opd_visit = synced_visit
        else:
            db.refresh(opd_visit)
        
        # OPD cash flow: do NOT require payment before encounter creation.
        # Payment is enforced later (e.g. before lab result entry, pharmacy dispense, radiology report).
        # We still sync payment status above so OPD visit shows "paid" when they have paid.
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return False, f"Patient {patient_id} not found"
        
        if patient.payment_mechanism is None or patient.payment_mechanism == PaymentMechanism.CASH:
            # Treat NULL payment_mechanism as cash
            # Optional: update OPD visit payment_status if we find paid invoices (no block)
            if opd_visit.payment_status not in ["paid", "waived", "emergency"]:
                from app.models.billing_models import Invoice, InvoiceStatus, Payment, PaymentStatus
                from decimal import Decimal
                from app.models.billing_models import Charge
                
                invoices_direct = db.query(Invoice).filter(
                    Invoice.opd_visit_id == opd_visit_id,
                    Invoice.is_active == True
                ).all()
                invoices_via_charges = db.query(Invoice).join(Charge).filter(
                    Charge.opd_visit_id == opd_visit_id,
                    Invoice.is_active == True
                ).distinct().all()
                all_invoice_ids = set()
                all_invoices = []
                for inv in invoices_direct + invoices_via_charges:
                    if inv.id not in all_invoice_ids:
                        all_invoice_ids.add(inv.id)
                        all_invoices.append(inv)
                
                for invoice in all_invoices:
                    if invoice.status == InvoiceStatus.PAID:
                        opd_visit.payment_status = "paid"
                        db.commit()
                        db.refresh(opd_visit)
                        break
                    if invoice.balance is not None and invoice.balance <= Decimal('0.00'):
                        opd_visit.payment_status = "paid"
                        db.commit()
                        db.refresh(opd_visit)
                        break
                    completed_payments = db.query(Payment).filter(
                        Payment.invoice_id == invoice.id,
                        Payment.status == PaymentStatus.COMPLETED,
                        Payment.is_active == True
                    ).all()
                    if completed_payments:
                        total_paid = sum(p.amount for p in completed_payments)
                        if invoice.total_amount and total_paid >= invoice.total_amount:
                            opd_visit.payment_status = "paid"
                            db.commit()
                            db.refresh(opd_visit)
                            break
                # Do not block encounter: allow creation regardless of payment status for OPD cash
    
    # Rule 3: If IPD, verify admission status
    if admission_id:
        admission = db.query(Admission).filter(
            Admission.id == admission_id,
            Admission.is_active == True
        ).first()
        
        if not admission:
            return False, f"Admission {admission_id} not found"
        
        if admission.status != AdmissionStatus.ADMITTED:
            return False, f"Patient must be admitted to create IPD encounter. Current status: {admission.status.value}"
        
        # Verify patient matches
        if admission.patient_id != patient_id:
            return False, "Admission patient_id does not match encounter patient_id"
    
    return True, None


def auto_link_opd_visit(
    db: Session,
    patient_id: int,
    appointment_id: Optional[int] = None
) -> Optional[int]:
    """
    Automatically find and link an active OPD visit for the patient.
    If no active visit exists, creates one automatically.
    Returns opd_visit_id if found or created, None otherwise.
    """
    from app.crud import opd_crud
    from app.schemas.opd_schemas import OPDVisitCreate
    from app.models.patient_models import Patient
    
    # Try to get active OPD visit
    active_visit = opd_crud.get_active_opd_visit_by_patient(db, patient_id)
    
    if active_visit:
        return active_visit.id
    
    # If no active visit and appointment_id is provided, check if appointment has an OPD visit
    if appointment_id:
        from app.models.scheduled_appointment_models import ScheduledAppointment
        appointment = db.query(ScheduledAppointment).filter(ScheduledAppointment.id == appointment_id).first()
        if appointment:
            # Check if there's an OPD visit linked to this appointment
            opd_visit = db.query(OPDVisit).filter(
                OPDVisit.appointment_id == appointment_id,
                OPDVisit.patient_id == patient_id,
                OPDVisit.is_active == True,
                OPDVisit.status == OPDVisitStatus.ACTIVE
            ).first()
            
            if opd_visit:
                return opd_visit.id
    
    # No active visit found - create one automatically
    try:
        # Get patient to determine payment status
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return None
        
        # Validate and sanitize appointment_id before using it
        valid_appointment_id = None
        if appointment_id:
            from app.models.scheduled_appointment_models import ScheduledAppointment
            appointment = db.query(ScheduledAppointment).filter(
                ScheduledAppointment.id == appointment_id,
                ScheduledAppointment.is_active == True,
            ).first()
            if appointment:
                valid_appointment_id = appointment_id
        
        # Determine visit_type and payment_status from appointment if provided
        visit_type = "walk_in"
        payment_status = "pending"
        if valid_appointment_id:
            from app.models.scheduled_appointment_models import ScheduledAppointment, AppointmentType
            appointment = db.query(ScheduledAppointment).filter(
                ScheduledAppointment.id == valid_appointment_id,
                ScheduledAppointment.is_active == True,
            ).first()
            if appointment:
                if (
                    getattr(appointment, "appointment_type", None) == AppointmentType.EMERGENCY
                    or (getattr(appointment, "department", None) or "").strip().lower() == "emergency"
                ):
                    visit_type = "emergency"
                    payment_status = "emergency"
        
        if visit_type != "emergency" and patient.payment_mechanism:
            if patient.payment_mechanism.value == "cash":
                payment_status = "pending"
            elif patient.payment_mechanism.value in ["nhis", "private_insurance"]:
                payment_status = "paid"  # Insurance patients don't need upfront payment
        
        # Create OPD visit with validated appointment_id
        opd_visit_data = OPDVisitCreate(
            appointment_id=valid_appointment_id,
            visit_type=visit_type,
            payment_status=payment_status
        )
        
        opd_visit = opd_crud.create_opd_visit(db, opd_visit_data, patient_id)
        
        # Note: Consultation charges are created at registration (front office), not during encounter creation
        # This ensures cash patients pay at registration before seeing a clinician
        
        return opd_visit.id
        
    except Exception as e:
        # If creation fails, return None (validation will catch this)
        print(f"Error auto-creating OPD visit: {e}")
        return None

