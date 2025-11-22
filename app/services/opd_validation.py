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
        
        # Sync payment status before checking (fixes cases where payment was made but status wasn't updated)
        from app.crud import opd_crud
        synced_visit = opd_crud.sync_opd_visit_payment_status(db, opd_visit_id)
        if synced_visit:
            opd_visit = synced_visit  # Use the synced version
        else:
            db.refresh(opd_visit)  # Refresh if sync didn't return updated visit
        
        # Check payment for cash patients
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return False, f"Patient {patient_id} not found"
        
        if patient.payment_mechanism == PaymentMechanism.CASH:
            # Double-check payment status by looking at invoices directly if status is still pending
            if opd_visit.payment_status not in ["paid", "waived", "emergency"]:
                # Final check: verify payment status by checking invoices directly
                from app.models.billing_models import Invoice, InvoiceStatus, Payment, PaymentStatus
                from decimal import Decimal
                
                # Check if there are any paid invoices linked to this OPD visit
                # Method 1: Direct link via invoice.opd_visit_id
                invoices_direct = db.query(Invoice).filter(
                    Invoice.opd_visit_id == opd_visit_id,
                    Invoice.is_active == True
                ).all()
                
                # Method 2: Link via charges (for invoices created before opd_visit_id was added to invoices)
                from app.models.billing_models import Charge
                invoices_via_charges = db.query(Invoice).join(Charge).filter(
                    Charge.opd_visit_id == opd_visit_id,
                    Invoice.is_active == True
                ).distinct().all()
                
                # Combine both lists (remove duplicates by ID)
                all_invoice_ids = set()
                all_invoices = []
                for inv in invoices_direct + invoices_via_charges:
                    if inv.id not in all_invoice_ids:
                        all_invoice_ids.add(inv.id)
                        all_invoices.append(inv)
                
                payment_found = False
                for invoice in all_invoices:
                    # Check if invoice is paid (most reliable)
                    if invoice.status == InvoiceStatus.PAID:
                        # Invoice is paid, update OPD visit status and allow
                        opd_visit.payment_status = "paid"
                        db.commit()
                        db.refresh(opd_visit)
                        payment_found = True
                        break
                    
                    # Check balance
                    if invoice.balance is not None and invoice.balance <= Decimal('0.00'):
                        # Invoice balance is zero or negative, update status
                        opd_visit.payment_status = "paid"
                        db.commit()
                        db.refresh(opd_visit)
                        payment_found = True
                        break
                    
                    # Check payments directly (most comprehensive)
                    completed_payments = db.query(Payment).filter(
                        Payment.invoice_id == invoice.id,
                        Payment.status == PaymentStatus.COMPLETED,
                        Payment.is_active == True
                    ).all()
                    if completed_payments:
                        total_paid = sum(p.amount for p in completed_payments)
                        if invoice.total_amount and total_paid >= invoice.total_amount:
                            # Payments cover full amount, update status and allow
                            opd_visit.payment_status = "paid"
                            db.commit()
                            db.refresh(opd_visit)
                            payment_found = True
                            break
                
                # Re-check after potential update
                if not payment_found and opd_visit.payment_status not in ["paid", "waived", "emergency"]:
                    return False, f"Payment required for OPD visit {opd_visit.opd_number}. Current status: {opd_visit.payment_status}"
    
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
        from app.models.appointment_models import Appointment
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
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
        
        # Determine payment status based on patient's payment mechanism
        payment_status = "pending"
        visit_type = "walk_in"
        
        if patient.payment_mechanism:
            if patient.payment_mechanism.value == "cash":
                payment_status = "pending"
            elif patient.payment_mechanism.value in ["nhis", "private_insurance"]:
                payment_status = "paid"  # Insurance patients don't need upfront payment
        
        # Create OPD visit
        opd_visit_data = OPDVisitCreate(
            appointment_id=appointment_id,
            visit_type=visit_type,
            payment_status=payment_status
        )
        
        opd_visit = opd_crud.create_opd_visit(db, opd_visit_data, patient_id)
        
        # For cash patients, create consultation charge if not already created
        if patient.payment_mechanism and patient.payment_mechanism.value == "cash":
            from app.services.charge_automation import create_charge_for_consultation
            try:
                create_charge_for_consultation(
                    db, 
                    patient_id, 
                    None,  # created_by_id - will be set by the service
                    encounter_id=None,
                    opd_visit_id=opd_visit.id
                )
                opd_crud.mark_consultation_charge_created(db, opd_visit.id)
            except Exception as e:
                # Log error but don't fail the visit creation
                print(f"Error creating consultation charge during auto-link: {e}")
        
        return opd_visit.id
        
    except Exception as e:
        # If creation fails, return None (validation will catch this)
        print(f"Error auto-creating OPD visit: {e}")
        return None

