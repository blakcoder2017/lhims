"""
Referral Report Service
Generates and sends referral reports for patient transfers to other hospitals
"""
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional
from app.models.ipd_models import Admission, DischargeStatus
from app.models.patient_models import Patient
from app.models.encounter_models import Encounter, LabOrder, RadiologyOrder, Prescription
from app.models.triage_models import TriageVitals
from app.crud import hospital_settings_crud


def generate_referral_report(
    db: Session,
    admission_id: int,
    receiving_hospital: Optional[str] = None,
    reason_for_referral: Optional[str] = None
) -> dict:
    """
    Generate a referral report for a patient transfer.
    
    Args:
        db: Database session
        admission_id: Admission ID to generate report for
        receiving_hospital: Name of receiving hospital
        reason_for_referral: Reason for referral
    
    Returns:
        dict with report data
    """
    from sqlalchemy.orm import joinedload
    
    # Get admission with all related data
    admission = db.query(Admission).options(
        joinedload(Admission.patient),
        joinedload(Admission.ward),
        joinedload(Admission.bed),
        joinedload(Admission.admitted_by),
        joinedload(Admission.encounters).joinedload(Encounter.clinician)
    ).filter(Admission.id == admission_id).first()
    
    if not admission:
        raise ValueError("Admission not found")
    
    # Get hospital settings
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    # Get all encounters for this admission
    encounters = admission.encounters
    
    # Collect all clinical data
    lab_orders = []
    radiology_orders = []
    prescriptions = []
    vitals_records = []
    
    for encounter in encounters:
        # Lab orders
        lab_orders.extend(db.query(LabOrder).filter(LabOrder.encounter_id == encounter.id).all())
        
        # Radiology orders
        radiology_orders.extend(db.query(RadiologyOrder).filter(RadiologyOrder.encounter_id == encounter.id).all())
        
        # Prescriptions
        prescriptions.extend(db.query(Prescription).filter(Prescription.encounter_id == encounter.id).all())
        
        # Vitals
        if encounter.patient_id:
            vitals = db.query(TriageVitals).filter(
                TriageVitals.patient_id == encounter.patient_id
            ).order_by(TriageVitals.recorded_at.desc()).limit(10).all()
            vitals_records.extend(vitals)
    
    # Get admission notes
    from app.models.ipd_models import AdmissionNote
    admission_notes = db.query(AdmissionNote).filter(
        AdmissionNote.admission_id == admission_id,
        AdmissionNote.is_active == True
    ).order_by(AdmissionNote.created_at.desc()).all()
    
    # Calculate length of stay
    admission_date = admission.admission_date.date() if isinstance(admission.admission_date, datetime) else admission.admission_date
    if admission.discharge_date:
        discharge_date = admission.discharge_date.date() if isinstance(admission.discharge_date, datetime) else admission.discharge_date
        length_of_stay = (discharge_date - admission_date).days
    else:
        from datetime import date
        length_of_stay = (date.today() - admission_date).days
    
    # Build report
    report_data = {
        "admission": admission,
        "patient": admission.patient,
        "hospital_settings": hospital_settings,
        "receiving_hospital": receiving_hospital,
        "reason_for_referral": reason_for_referral,
        "encounters": encounters,
        "lab_orders": lab_orders,
        "radiology_orders": radiology_orders,
        "prescriptions": prescriptions,
        "vitals_records": vitals_records[:10],  # Limit to 10 most recent
        "admission_notes": admission_notes,
        "length_of_stay": length_of_stay,
        "report_date": datetime.now(),
        "report_type": "referral"
    }
    
    return report_data


def regenerate_referral_report(
    db: Session,
    admission_id: int,
    receiving_hospital: Optional[str] = None,
    reason_for_referral: Optional[str] = None
) -> dict:
    """
    Regenerate a referral report for a patient transfer.
    This is useful when a patient is transferred and the report needs to be regenerated.
    
    Args:
        db: Database session
        admission_id: Admission ID to regenerate report for
        receiving_hospital: Name of receiving hospital
        reason_for_referral: Reason for referral
    
    Returns:
        dict with report data
    """
    return generate_referral_report(db, admission_id, receiving_hospital, reason_for_referral)
