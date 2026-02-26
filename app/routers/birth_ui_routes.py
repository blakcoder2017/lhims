"""
Birth / Delivery UI Routes

Birth records and delivery tracking.
"""
from fastapi import APIRouter, Request, Depends, Query, Form
from fastapi.responses import RedirectResponse, JSONResponse
from app.core.templates import templates
from starlette import status
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from datetime import date, time, datetime
from decimal import Decimal
import re

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.models.birth_models import (
    BirthRecord, DeliveryType, BirthOutcome, Gender,
    PlaceOfDelivery, StateOfPerineum, AnaesthesiaType, NumberOfBabiesType,
    BabyConditionAtDischarge, UterusCondition, BreastCondition, PerineumCondition,
    LochiaColour, LochiaOdour, EyeCareGiven, TimeOfDay, PlacentaStatus
)
from app.models.baby_discharge_models import BabyDischarge, BabyConditionAtDischarge as BabyCondEnum
from app.crud import birth_crud, patient_crud
from app.crud import baby_discharge_crud

router = APIRouter()


@router.get("/api/births/patients/search")
def search_patients_for_birth(
    query: str = Query(None, min_length=2, alias="q"),
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    JSON API endpoint for searching patients for birth record form.
    Searches by name, patient number, or phone number.
    """
    if not query:
        return JSONResponse(content=[])
    
    from app.models.patient_models import Patient
    from sqlalchemy import or_
    
    search_term = f"%{query.strip()}%"
    patients = db.query(Patient).filter(
        Patient.is_active == True
    ).filter(
        or_(
            Patient.first_name.ilike(search_term),
            Patient.last_name.ilike(search_term),
            Patient.patient_number.ilike(search_term),
            Patient.phone_number.ilike(search_term),
        )
    ).limit(limit).all()
    
    results = []
    for p in patients:
        results.append({
            "id": p.id,
            "patient_number": p.patient_number,
            "first_name": p.first_name,
            "last_name": p.last_name,
            "date_of_birth": p.date_of_birth.isoformat() if p.date_of_birth else None,
            "phone_number": p.phone_number,
        })
    
    return JSONResponse(content=results)


@router.get("/api/births/antenatal-visits/{patient_id}")
def get_patient_antenatal_visits(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    JSON API endpoint to get ANC visits for a patient.
    Used to link birth records to antenatal care history.
    """
    from app.models.antenatal_models import AntenatalVisit
    
    visits = db.query(AntenatalVisit).filter(
        AntenatalVisit.patient_id == patient_id,
        AntenatalVisit.is_active == True
    ).order_by(AntenatalVisit.visit_date.desc()).all()
    
    results = []
    for v in visits:
        results.append({
            "id": v.id,
            "visit_date": v.visit_date.isoformat() if v.visit_date else None,
            "visit_number": v.visit_number,
            "gestational_weeks": float(v.gestational_weeks) if v.gestational_weeks else None,
            "edd": v.edd.isoformat() if v.edd else None,
            "risk_factors": v.risk_factors,
            "complications": v.complications,
        })
    
    return JSONResponse(content=results)


@router.get("/births/dashboard", name="births_dashboard")
def births_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
):
    """Births dashboard with stats."""
    today = date.today()

    total_births = (
        db.query(BirthRecord).filter(BirthRecord.is_active == True).count()
    )
    births_today = (
        db.query(BirthRecord)
        .filter(BirthRecord.birth_date == today, BirthRecord.is_active == True)
        .count()
    )
    live_births_today = (
        db.query(BirthRecord)
        .filter(
            BirthRecord.birth_date == today,
            BirthRecord.birth_outcome == BirthOutcome.LIVE.value,
            BirthRecord.is_active == True,
        )
        .count()
    )

    recent_births, _ = birth_crud.get_birth_records(db, skip=0, limit=15)
    
    print(f"[BIRTH_DASHBOARD_DEBUG] total_births={total_births}, births_today={births_today}, recent_births_count={len(recent_births) if recent_births else 0}")
    if recent_births:
        for b in recent_births:
            print(f"[BIRTH_DASHBOARD_DEBUG] Birth record: id={b.id}, birth_number={b.birth_number}, mother_patient_id={b.mother_patient_id}, birth_date={b.birth_date}")

    context = {
        "request": request,
        "title": "Births / Delivery Dashboard",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "total_births": total_births,
        "births_today": births_today,
        "live_births_today": live_births_today,
        "recent_births": recent_births,
    }
    return templates.TemplateResponse("births/births_dashboard.html", context)


@router.get("/births", name="births_list")
def births_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
    mother_id: Optional[int] = Query(None),
    birth_outcome: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
):
    """List birth records."""
    records, total = birth_crud.get_birth_records(
        db, skip=0, limit=limit, mother_id=mother_id, birth_outcome=birth_outcome
    )
    context = {
        "request": request,
        "title": "Birth Records",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "birth_records": records,
        "total": total,
        "mother_id": mother_id,
        "birth_outcome_filter": birth_outcome,
    }
    return templates.TemplateResponse("births/births_list.html", context)


@router.get("/births/create/{mother_id}", name="birth_record_create_form")
def birth_record_create_form(
    request: Request,
    mother_id: int,
    admission_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
):
    """Form to create birth record with mother pre-selected."""
    mother = patient_crud.get_patient(db, mother_id)
    today = date.today()
    # Get mother's antenatal visits if she's selected
    antenatal_visits = []
    if mother_id:
        from app.crud import antenatal_crud
        antenatal_visits = antenatal_crud.get_antenatal_visits_by_patient(db, mother_id, limit=10)
    context = {
        "request": request,
        "title": "Record Birth / Delivery",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "mother": mother,
        "mother_id": mother_id,
        "admission_id": admission_id,
        "today": today.strftime("%Y-%m-%d"),
        "antenatal_visits": antenatal_visits,
        "delivery_types": [t.value for t in DeliveryType],
        "birth_outcomes": [o.value for o in BirthOutcome],
        "genders": [g.value for g in Gender],
        "place_of_delivery_options": [p.value for p in PlaceOfDelivery],
        "state_of_perineum_options": [s.value for s in StateOfPerineum],
        "anaesthesia_options": [a.value for a in AnaesthesiaType],
        "number_of_babies_options": [n.value for n in NumberOfBabiesType],
        "baby_condition_options": [b.value for b in BabyConditionAtDischarge],
        "uterus_condition_options": [u.value for u in UterusCondition],
        "breast_condition_options": [b.value for b in BreastCondition],
        "perineum_condition_options": [p.value for p in PerineumCondition],
        "lochia_colour_options": [l.value for l in LochiaColour],
        "lochia_odour_options": [l.value for l in LochiaOdour],
        "eye_care_options": [e.value for e in EyeCareGiven],
        "time_of_day_options": [t.value for t in TimeOfDay],
        "placenta_status_options": [p.value for p in PlacentaStatus],
    }
    return templates.TemplateResponse("births/birth_record_form.html", context)


@router.get("/births/create", name="birth_record_create")
def birth_record_create_form_no_mother(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
):
    """Form to create birth record without pre-selected mother."""
    today = date.today()
    context = {
        "request": request,
        "title": "Record Birth / Delivery",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "mother": None,
        "mother_id": None,
        "today": today.strftime("%Y-%m-%d"),
        "antenatal_visits": [],
        "delivery_types": [t.value for t in DeliveryType],
        "birth_outcomes": [o.value for o in BirthOutcome],
        "genders": [g.value for g in Gender],
        "place_of_delivery_options": [p.value for p in PlaceOfDelivery],
        "state_of_perineum_options": [s.value for s in StateOfPerineum],
        "anaesthesia_options": [a.value for a in AnaesthesiaType],
        "number_of_babies_options": [n.value for n in NumberOfBabiesType],
        "baby_condition_options": [b.value for b in BabyConditionAtDischarge],
        "uterus_condition_options": [u.value for u in UterusCondition],
        "breast_condition_options": [b.value for b in BreastCondition],
        "perineum_condition_options": [p.value for p in PerineumCondition],
        "lochia_colour_options": [l.value for l in LochiaColour],
        "lochia_odour_options": [l.value for l in LochiaOdour],
        "eye_care_options": [e.value for e in EyeCareGiven],
        "time_of_day_options": [t.value for t in TimeOfDay],
        "placenta_status_options": [p.value for p in PlacentaStatus],
    }
    return templates.TemplateResponse("births/birth_record_form.html", context)


@router.post("/births/create", name="birth_record_create_submit")
async def birth_record_create_submit(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
):
    """Create birth record(s) - handles single or multiple babies."""
    try:
        # Parse form data manually to handle baby array
        form_data = await request.form()
        
        # Extract common fields
        mother_patient_id = int(form_data.get("mother_patient_id"))
        mother_nhis_number = form_data.get("mother_nhis_number") or None
        
        # ANC Visit Link
        antenatal_visit_id = form_data.get("antenatal_visit_id")
        antenatal_visit_id_val = None
        if antenatal_visit_id and antenatal_visit_id.strip():
            try:
                antenatal_visit_id_val = int(antenatal_visit_id)
            except ValueError:
                pass
        
        father_name = form_data.get("father_name") or None
        father_contact = form_data.get("father_contact") or None
        referred_from = form_data.get("referred_from") or None
        referred_to = form_data.get("referred_to") or None
        birth_date = date.fromisoformat(form_data.get("birth_date"))
        
        birth_time = form_data.get("birth_time")
        birth_time_obj = None
        if birth_time:
            try:
                parts = birth_time.split(":")
                birth_time_obj = time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
            except (ValueError, IndexError):
                pass
        
        delivery_type = form_data.get("delivery_type", "vaginal")
        birth_outcome = form_data.get("birth_outcome", "live")
        
        # Common fields
        facility_name = form_data.get("facility_name") or None
        district = form_data.get("district") or None
        region = form_data.get("region") or None
        attendant_name = form_data.get("attendant_name") or None
        attendant_category = form_data.get("attendant_category") or None
        attendant_registration_number = form_data.get("attendant_registration_number") or None
        baby_address = form_data.get("baby_address") or None
        birth_number = form_data.get("birth_number") or None
        birth_notification_number = form_data.get("birth_notification_number") or None
        
        # Number of babies (for multiples)
        number_of_babies_str = form_data.get("number_of_babies")
        number_of_babies_val = None
        if number_of_babies_str:
            try:
                number_of_babies_val = int(number_of_babies_str)
            except ValueError:
                pass
        birth_certificate_status = form_data.get("birth_certificate_status", "pending")
        birth_certificate_number = form_data.get("birth_certificate_number") or None
        birth_certificate_date = form_data.get("birth_certificate_date")
        birth_cert_date_obj = None
        if birth_certificate_date:
            try:
                birth_cert_date_obj = date.fromisoformat(birth_certificate_date)
            except ValueError:
                pass
        
        discharge_date = form_data.get("discharge_date")
        discharge_date_obj = None
        if discharge_date:
            try:
                discharge_date_obj = date.fromisoformat(discharge_date)
            except ValueError:
                pass
        
        mother_discharge_condition = form_data.get("mother_discharge_condition") or None
        baby_discharge_condition = form_data.get("baby_discharge_condition") or None
        follow_up_date = form_data.get("follow_up_date")
        follow_up_date_obj = None
        if follow_up_date:
            try:
                follow_up_date_obj = date.fromisoformat(follow_up_date)
            except ValueError:
                pass
        
        gravida_str = form_data.get("gravida") or None
        para_str = form_data.get("para") or None
        complications = form_data.get("complications") or None
        notes = form_data.get("notes") or None
        
        # New labour & delivery fields (GHS)
        referral_reason = form_data.get("referral_reason") or None
        
        # Weeks of pregnancy (GHS new)
        weeks_of_pregnancy_str = form_data.get("weeks_of_pregnancy")
        weeks_of_pregnancy_val = None
        if weeks_of_pregnancy_str:
            try:
                weeks_of_pregnancy_val = int(weeks_of_pregnancy_str)
            except:
                pass
        
        # Time of delivery AM/PM (GHS new)
        time_of_delivery_am_pm = form_data.get("time_of_delivery_am_pm") or None
        
        # Time of placenta delivery AM/PM (GHS new)
        time_of_placenta_delivery_am_pm = form_data.get("time_of_placenta_delivery_am_pm") or None
        
        # Duration of labour (GHS - existing hours + new minutes)
        duration_of_labour_hours = form_data.get("duration_of_labour_hours")
        duration_labour_val = None
        if duration_of_labour_hours:
            try:
                duration_labour_val = Decimal(str(duration_of_labour_hours))
            except:
                pass
        
        duration_labour_minutes_str = form_data.get("duration_labour_minutes")
        duration_labour_minutes_val = None
        if duration_labour_minutes_str:
            try:
                duration_labour_minutes_val = int(duration_labour_minutes_str)
            except:
                pass
        
        # Indication for Vacuum / Caesarean Section (GHS new)
        indication_for_vacuum_cs = form_data.get("indication_for_vacuum_cs") or None
        
        # Anaesthesia (GHS new)
        anaesthesia = form_data.get("anaesthesia") or None
        
        partograph_used = form_data.get("partograph_used") in ['true', True]
        placenta_delivered = form_data.get("placenta_delivered") or None
        estimated_blood_loss_ml = form_data.get("estimated_blood_loss_ml")
        ebl_val = None
        if estimated_blood_loss_ml:
            try:
                ebl_val = int(estimated_blood_loss_ml)
            except:
                pass
        
        # Blood transfusion (GHS new)
        blood_transfusion = form_data.get("blood_transfusion") in ['true', True, 'on']
        
        # Manual removal of placenta (GHS new)
        manual_removal_placenta = form_data.get("manual_removal_placenta") in ['true', True, 'on']
        
        # State of perineum (GHS new)
        state_of_perineum = form_data.get("state_of_perineum") or None
        
        # Labour & delivery complications (GHS new)
        labour_delivery_complications = form_data.get("labour_delivery_complications") or None
        
        # Place of delivery (GHS new)
        place_of_delivery = form_data.get("place_of_delivery") or None
        
        # Breastfeeding started within 30 minutes (GHS new)
        breastfeeding_30min = form_data.get("breastfeeding_30min") in ['true', True, 'on']
        
        # Skin to skin reason (GHS new)
        skin_to_skin_reason = form_data.get("skin_to_skin_reason") or None
        
        # Medications
        uterotonic_drug = form_data.get("uterotonic_drug") or None
        other_medications = form_data.get("other_medications") or None
        
        # Mother's health
        tetanus_status = form_data.get("tetanus_status") or None
        iptp_doses = form_data.get("iptp_doses")
        iptp_val = None
        if iptp_doses:
            try:
                iptp_val = int(iptp_doses)
            except:
                pass
        
        # === BABY DISCHARGE SUMMARY (GHS NEW) ===
        discharge_date_baby_str = form_data.get("discharge_date_baby")
        discharge_date_baby_obj = None
        if discharge_date_baby_str:
            try:
                discharge_date_baby_obj = date.fromisoformat(discharge_date_baby_str)
            except:
                pass
        
        discharge_heart_rate_str = form_data.get("discharge_heart_rate")
        discharge_heart_rate_val = None
        if discharge_heart_rate_str:
            try:
                discharge_heart_rate_val = int(discharge_heart_rate_str)
            except:
                pass
        
        discharge_respiratory_rate_str = form_data.get("discharge_respiratory_rate")
        discharge_respiratory_rate_val = None
        if discharge_respiratory_rate_str:
            try:
                discharge_respiratory_rate_val = int(discharge_respiratory_rate_str)
            except:
                pass
        
        discharge_temperature_str = form_data.get("discharge_temperature")
        discharge_temperature_val = None
        if discharge_temperature_str:
            try:
                discharge_temperature_val = Decimal(str(discharge_temperature_str))
            except:
                pass
        
        discharge_weight_str = form_data.get("discharge_weight")
        discharge_weight_val = None
        if discharge_weight_str:
            try:
                discharge_weight_val = Decimal(str(discharge_weight_str))
            except:
                pass
        
        # Feeding status at discharge
        breastfeeding_initiated_discharge = form_data.get("breastfeeding_initiated_discharge") in ['true', True, 'on']
        baby_suckling_established = form_data.get("baby_suckling_established") in ['true', True, 'on']
        meconium_passed = form_data.get("meconium_passed") in ['true', True, 'on']
        urine_passed = form_data.get("urine_passed") in ['true', True, 'on']
        
        # Eye care
        eye_care_given = form_data.get("eye_care_given") or None
        
        # Immunisation dates
        cord_care_date_str = form_data.get("cord_care_date")
        cord_care_date_obj = None
        if cord_care_date_str:
            try:
                cord_care_date_obj = date.fromisoformat(cord_care_date_str)
            except:
                pass
        
        vitamin_k_date_str = form_data.get("vitamin_k_date")
        vitamin_k_date_obj = None
        if vitamin_k_date_str:
            try:
                vitamin_k_date_obj = date.fromisoformat(vitamin_k_date_str)
            except:
                pass
        
        bcg_date_str = form_data.get("bcg_date")
        bcg_date_obj = None
        if bcg_date_str:
            try:
                bcg_date_obj = date.fromisoformat(bcg_date_str)
            except:
                pass
        
        hepatitis_b_date_str = form_data.get("hepatitis_b_date")
        hepatitis_b_date_obj = None
        if hepatitis_b_date_str:
            try:
                hepatitis_b_date_obj = date.fromisoformat(hepatitis_b_date_str)
            except:
                pass
        
        oral_polio_date_str = form_data.get("oral_polio_date")
        oral_polio_date_obj = None
        if oral_polio_date_str:
            try:
                oral_polio_date_obj = date.fromisoformat(oral_polio_date_str)
            except:
                pass
        
        # Baby's condition at discharge
        baby_condition_at_discharge = form_data.get("baby_condition_at_discharge") or None
        baby_condition_abnormal_specify = form_data.get("baby_condition_abnormal_specify") or None
        
        # === MOTHER'S CONDITION AT DISCHARGE (GHS NEW) ===
        discharge_date_mother_str = form_data.get("discharge_date_mother")
        discharge_date_mother_obj = None
        if discharge_date_mother_str:
            try:
                discharge_date_mother_obj = date.fromisoformat(discharge_date_mother_str)
            except:
                pass
        
        discharge_mother_bp = form_data.get("discharge_mother_bp") or None
        
        discharge_mother_pulse_str = form_data.get("discharge_mother_pulse")
        discharge_mother_pulse_val = None
        if discharge_mother_pulse_str:
            try:
                discharge_mother_pulse_val = int(discharge_mother_pulse_str)
            except:
                pass
        
        discharge_mother_temperature_str = form_data.get("discharge_mother_temperature")
        discharge_mother_temperature_val = None
        if discharge_mother_temperature_str:
            try:
                discharge_mother_temperature_val = Decimal(str(discharge_mother_temperature_str))
            except:
                pass
        
        discharge_uterus_condition = form_data.get("discharge_uterus_condition") or None
        
        discharge_fundal_height_str = form_data.get("discharge_fundal_height")
        discharge_fundal_height_val = None
        if discharge_fundal_height_str:
            try:
                discharge_fundal_height_val = Decimal(str(discharge_fundal_height_str))
            except:
                pass
        
        discharge_lochia_colour = form_data.get("discharge_lochia_colour") or None
        discharge_lochia_odour = form_data.get("discharge_lochia_odour") or None
        discharge_perineum_condition = form_data.get("discharge_perineum_condition") or None
        discharge_breast_condition = form_data.get("discharge_breast_condition") or None
        
        # === POSTNATAL CARE (PNC) PLAN (GHS NEW) ===
        next_visit_date_str = form_data.get("next_visit_date")
        next_visit_date_obj = None
        if next_visit_date_str:
            try:
                next_visit_date_obj = date.fromisoformat(next_visit_date_str)
            except:
                pass
        
        pnc1_date_str = form_data.get("pnc1_date")
        pnc1_date_obj = None
        if pnc1_date_str:
            try:
                pnc1_date_obj = date.fromisoformat(pnc1_date_str)
            except:
                pass
        
        pnc2_date_str = form_data.get("pnc2_date")
        pnc2_date_obj = None
        if pnc2_date_str:
            try:
                pnc2_date_obj = date.fromisoformat(pnc2_date_str)
            except:
                pass
        
        pnc3_date_str = form_data.get("pnc3_date")
        pnc3_date_obj = None
        if pnc3_date_str:
            try:
                pnc3_date_obj = date.fromisoformat(pnc3_date_str)
            except:
                pass
        
        # Stillbirth details
        fetal_death_date_str = form_data.get("fetal_death_date")
        fetal_death_date_obj = None
        if fetal_death_date_str:
            try:
                fetal_death_date_obj = date.fromisoformat(fetal_death_date_str)
            except ValueError:
                pass
        
        fetal_death_time_str = form_data.get("fetal_death_time")
        fetal_death_time_obj = None
        if fetal_death_time_str:
            try:
                parts = fetal_death_time_str.split(":")
                fetal_death_time_obj = time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
            except (ValueError, IndexError):
                pass
        
        # Convert gravida and para
        gravida = None
        if gravida_str is not None and gravida_str.strip():
            try:
                gravida = int(gravida_str.strip())
            except ValueError:
                pass
        
        para = None
        if para_str is not None and para_str.strip():
            try:
                para = int(para_str.strip())
            except ValueError:
                pass
        
        # Parse babies array - collect all baby data
        babies_data = []
        for key in form_data.keys():
            if key.startswith("babies["):
                # Extract baby index
                import re
                match = re.match(r'babies\[(\d+)\](.*)', key)
                if match:
                    idx = int(match.group(1))
                    field_name = match.group(2).lstrip('.')  # Remove leading dot
                    value = form_data.get(key)
                    
                    while len(babies_data) <= idx:
                        babies_data.append({})
                    babies_data[idx][field_name] = value
        
        # If no babies data, create at least one record
        if not babies_data:
            babies_data = [{}]
        
        created_records = []
        
        # Create a birth record for each baby
        for idx, baby in enumerate(babies_data):
            # Parse baby fields
            baby_name = baby.get("baby_name") or None
            gender = baby.get("gender") or None
            
            weight_kg = baby.get("weight_kg")
            weight_kg_val = None
            if weight_kg:
                try:
                    weight_kg_val = Decimal(str(weight_kg))
                except:
                    pass
            
            length_cm = baby.get("length_cm")
            length_cm_val = None
            if length_cm:
                try:
                    length_cm_val = Decimal(str(length_cm))
                except:
                    pass
            
            head_circ = baby.get("head_circumference_cm")
            head_circ_val = None
            if head_circ:
                try:
                    head_circ_val = Decimal(str(head_circ))
                except:
                    pass
            
            gest_age = baby.get("gestational_age_weeks")
            gest_age_val = None
            if gest_age:
                try:
                    gest_age_val = int(gest_age)
                except:
                    pass
            
            # Boolean fields
            lbw = baby.get("low_birth_weight") in ['true', True]
            vlbw = baby.get("very_low_birth_weight") in ['true', True]
            resus = baby.get("resuscitation_required") in ['true', True]
            vit_k = baby.get("vitamin_k_administered") in ['true', True, 'on']
            bcg = baby.get("bcg_vaccine") in ['true', True, 'on']
            polio = baby.get("polio_vaccine") in ['true', True, 'on']
            eye = baby.get("eye_prophylaxis") in ['true', True, 'on']
            bf_1hr = baby.get("breastfeeding_initiated_1hr") in ['true', True]
            nicu = baby.get("nicu_admission") in ['true', True]
            skin_to_skin_baby = baby.get("skin_to_skin") in ['true', True]
            kangaroo_care_baby = baby.get("kangaroo_care") in ['true', True]
            
            # Baby complications (GHS new)
            baby_complications = baby.get("baby_complications") or None
            
            # Referred to facility (GHS new)
            referred_to_facility_baby = baby.get("referred_to_facility") or None
            
            # Number of babies type (GHS new)
            number_of_babies_type = baby.get("number_of_babies_type") or None
            
            apgar_1min = baby.get("apgar_1min")
            apgar_1_val = None
            if apgar_1min:
                try:
                    apgar_1_val = int(apgar_1min)
                except:
                    pass
            
            apgar_5min = baby.get("apgar_5min")
            apgar_5_val = None
            if apgar_5min:
                try:
                    apgar_5_val = int(apgar_5min)
                except:
                    pass
            
            apgar_10min = baby.get("apgar_10min")
            apgar_10_val = None
            if apgar_10min:
                try:
                    apgar_10_val = int(apgar_10min)
                except:
                    pass
            
            birth_defects = baby.get("birth_defects") or None
            
            # New fields for baby
            birth_order_baby = baby.get("birth_order")
            birth_order_val = None
            if birth_order_baby:
                try:
                    birth_order_val = int(birth_order_baby)
                except:
                    pass
            
            resuscitation_type = baby.get("resuscitation_type") or None
            
            # Create birth record for this baby
            record = birth_crud.create_birth_record(
                db,
                mother_patient_id=mother_patient_id,
                mother_nhis_number=mother_nhis_number,
                antenatal_visit_id=antenatal_visit_id_val if idx == 0 else None,  # Link to ANC visit (first baby only)
                father_name=father_name,
                father_contact=father_contact,
                referred_from=referred_from,
                referred_to=referred_to if idx == 0 else None,
                referral_reason=referral_reason if idx == 0 else None,
                birth_date=birth_date,
                birth_time=birth_time_obj,
                
                # === DELIVERY OUTCOME (GHS) ===
                weeks_of_pregnancy=weeks_of_pregnancy_val if idx == 0 else None,
                time_of_delivery_am_pm=time_of_delivery_am_pm if idx == 0 else None,
                time_of_placenta_delivery_am_pm=time_of_placenta_delivery_am_pm if idx == 0 else None,
                duration_of_labour_hours=duration_labour_val if idx == 0 else None,
                duration_labour_minutes=duration_labour_minutes_val if idx == 0 else None,
                delivery_type=delivery_type,
                indication_for_vacuum_cs=indication_for_vacuum_cs if idx == 0 else None,
                anaesthesia=anaesthesia if idx == 0 else None,
                estimated_blood_loss_ml=ebl_val if idx == 0 else None,
                blood_transfusion=blood_transfusion if idx == 0 else None,
                placenta_delivered=placenta_delivered if idx == 0 else None,
                manual_removal_placenta=manual_removal_placenta if idx == 0 else None,
                state_of_perineum=state_of_perineum if idx == 0 else None,
                labour_delivery_complications=labour_delivery_complications if idx == 0 else None,
                place_of_delivery=place_of_delivery if idx == 0 else None,
                partograph_used=partograph_used if idx == 0 else False,
                birth_outcome=birth_outcome,
                
                # Breastfeeding
                breastfeeding_30min=breastfeeding_30min if idx == 0 else None,
                skin_to_skin=skin_to_skin_baby,
                skin_to_skin_reason=skin_to_skin_reason if idx == 0 else None,
                
                baby_name=baby_name,
                gender=gender,
                weight_kg=weight_kg_val,
                length_cm=length_cm_val,
                head_circumference_cm=head_circ_val,
                number_of_babies=len(babies_data),
                number_of_babies_type=number_of_babies_type,
                birth_order=idx + 1 if len(babies_data) > 1 else None,
                gestational_age_weeks=gest_age_val,
                low_birth_weight=lbw,
                very_low_birth_weight=vlbw,
                apgar_1min=apgar_1_val,
                apgar_5min=apgar_5_val,
                apgar_10min=apgar_10_val,
                resuscitation_required=resus,
                resuscitation_type=resuscitation_type,
                birth_defects=birth_defects,
                baby_complications=baby_complications,
                referred_to_facility=referred_to_facility_baby,
                
                vitamin_k_administered=vit_k,
                bcg_vaccine=bcg,
                polio_vaccine=polio,
                eye_prophylaxis=eye,
                breastfeeding_initiated_1hr=bf_1hr,
                nicu_admission=nicu,
                kangaroo_care=kangaroo_care_baby,
                
                facility_name=facility_name,
                district=district,
                region=region,
                attendant_name=attendant_name,
                attendant_category=attendant_category,
                attendant_registration_number=attendant_registration_number,
                baby_address=baby_address,
                birth_number=birth_number if idx == 0 else None,
                birth_notification_number=birth_notification_number if idx == 0 else None,
                birth_certificate_status=birth_certificate_status if idx == 0 else None,
                birth_certificate_number=birth_certificate_number if idx == 0 else None,
                birth_certificate_date=birth_cert_date_obj if idx == 0 else None,
                discharge_date=discharge_date_obj if idx == 0 else None,
                mother_discharge_condition=mother_discharge_condition if idx == 0 else None,
                baby_discharge_condition=baby_discharge_condition if idx == 0 else None,
                follow_up_date=follow_up_date_obj if idx == 0 else None,
                gravida=gravida,
                para=para,
                complications=complications if idx == 0 else None,
                notes=notes if idx == 0 else None,
                
                # === BABY DISCHARGE SUMMARY (GHS) ===
                discharge_date_baby=discharge_date_baby_obj if idx == 0 else None,
                discharge_heart_rate=discharge_heart_rate_val if idx == 0 else None,
                discharge_respiratory_rate=discharge_respiratory_rate_val if idx == 0 else None,
                discharge_temperature=discharge_temperature_val if idx == 0 else None,
                discharge_weight=discharge_weight_val if idx == 0 else None,
                breastfeeding_initiated_discharge=breastfeeding_initiated_discharge if idx == 0 else None,
                baby_suckling_established=baby_suckling_established if idx == 0 else None,
                meconium_passed=meconium_passed if idx == 0 else None,
                urine_passed=urine_passed if idx == 0 else None,
                eye_care_given=eye_care_given if idx == 0 else None,
                cord_care_date=cord_care_date_obj if idx == 0 else None,
                vitamin_k_date=vitamin_k_date_obj if idx == 0 else None,
                bcg_date=bcg_date_obj if idx == 0 else None,
                hepatitis_b_date=hepatitis_b_date_obj if idx == 0 else None,
                oral_polio_date=oral_polio_date_obj if idx == 0 else None,
                baby_condition_at_discharge=baby_condition_at_discharge if idx == 0 else None,
                baby_condition_abnormal_specify=baby_condition_abnormal_specify if idx == 0 else None,
                
                # === MOTHER'S CONDITION AT DISCHARGE (GHS) ===
                discharge_date_mother=discharge_date_mother_obj if idx == 0 else None,
                discharge_mother_bp=discharge_mother_bp if idx == 0 else None,
                discharge_mother_pulse=discharge_mother_pulse_val if idx == 0 else None,
                discharge_mother_temperature=discharge_mother_temperature_val if idx == 0 else None,
                discharge_uterus_condition=discharge_uterus_condition if idx == 0 else None,
                discharge_fundal_height=discharge_fundal_height_val if idx == 0 else None,
                discharge_lochia_colour=discharge_lochia_colour if idx == 0 else None,
                discharge_lochia_odour=discharge_lochia_odour if idx == 0 else None,
                discharge_perineum_condition=discharge_perineum_condition if idx == 0 else None,
                discharge_breast_condition=discharge_breast_condition if idx == 0 else None,
                
                # === POSTNATAL CARE (PNC) PLAN (GHS) ===
                next_visit_date=next_visit_date_obj if idx == 0 else None,
                pnc1_date=pnc1_date_obj if idx == 0 else None,
                pnc2_date=pnc2_date_obj if idx == 0 else None,
                pnc3_date=pnc3_date_obj if idx == 0 else None,
                
                # Medications
                uterotonic_drug=uterotonic_drug if idx == 0 else None,
                other_medications=other_medications if idx == 0 else None,
                # Mother's Health
                tetanus_status=tetanus_status if idx == 0 else None,
                iptp_doses=iptp_val if idx == 0 else None,
                # Stillbirth Details
                fetal_death_date=fetal_death_date_obj if idx == 0 else None,
                fetal_death_time=fetal_death_time_obj if idx == 0 else None,
                delivered_by_id=current_user.id,
            )
            db.commit()
            created_records.append(record)
        
        # Redirect to the first birth record detail page
        if created_records:
            redirect_url = str(request.url_for("birth_record_detail", record_id=created_records[0].id)) + f"?status=created&total_babies={len(created_records)}"
        else:
            redirect_url = str(request.url_for("births_dashboard")) + "?status=birth_recorded"
        
        return RedirectResponse(
            url=redirect_url,
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        # Redirect back to form with error
        mother_id = (await request.form()).get("mother_patient_id", 0)
        error_url = str(request.url_for("birth_record_create_form", mother_id=int(mother_id) if mother_id else 0)) + f"?error={str(e)}"
        return RedirectResponse(
            url=error_url,
            status_code=status.HTTP_302_FOUND,
        )


@router.get("/births/{record_id}", name="birth_record_detail")
def birth_record_detail(
    request: Request,
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
    status: Optional[str] = Query(default=None),
):
    """View birth record detail."""
    record = birth_crud.get_birth_record(db, record_id)
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Birth record not found")
    
    # Get mother's antenatal visits
    antenatal_visits = []
    if record.mother_patient_id:
        from app.crud import antenatal_crud
        antenatal_visits = antenatal_crud.get_antenatal_visits_by_patient(db, record.mother_patient_id, limit=10)
    
    # Get all baby records for this mother (for navigation in case of multiples)
    sibling_records = []
    if record.number_of_babies and record.number_of_babies > 1:
        sibling_records = birth_crud.get_birth_records_by_mother(db, record.mother_patient_id)
    
    # Get baby discharge summary for this baby
    baby_discharge = None
    if hasattr(record, 'baby_discharge'):
        baby_discharge = record.baby_discharge
    else:
        baby_discharge = baby_discharge_crud.get_baby_discharge_by_birth_record(db, record.id)
    
    context = {
        "request": request,
        "title": f"Birth Record – {record.birth_number or 'N/A'}",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "record": record,
        "antenatal_visits": antenatal_visits,
        "sibling_records": sibling_records,
        "status": status,
        "baby_discharge": baby_discharge,
    }
    return templates.TemplateResponse("births/birth_record_detail.html", context)


# ============== Baby Discharge Summary API ==============
@router.post("/api/births/{record_id}/baby-discharge", name="baby_discharge_save")
async def save_baby_discharge(
    record_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
):
    """Save or update baby discharge summary for a specific birth record."""
    try:
        form_data = await request.form()
        
        # Parse discharge date
        discharge_date_str = form_data.get("discharge_date")
        discharge_date_obj = None
        if discharge_date_str:
            try:
                discharge_date_obj = date.fromisoformat(discharge_date_str)
            except ValueError:
                pass
        
        # Parse vitals
        heart_rate = None
        hr_str = form_data.get("heart_rate")
        if hr_str:
            try:
                heart_rate = int(hr_str)
            except ValueError:
                pass
        
        respiratory_rate = None
        rr_str = form_data.get("respiratory_rate")
        if rr_str:
            try:
                respiratory_rate = int(rr_str)
            except ValueError:
                pass
        
        temperature = None
        temp_str = form_data.get("temperature")
        if temp_str:
            try:
                temperature = Decimal(str(temp_str))
            except ValueError:
                pass
        
        weight = None
        weight_str = form_data.get("weight_at_discharge")
        if weight_str:
            try:
                weight = Decimal(str(weight_str))
            except ValueError:
                pass
        
        # Boolean fields
        breastfeeding = form_data.get("breastfeeding_initiated") in ['true', 'on', True]
        suckling = form_data.get("suckling_established") in ['true', 'on', True]
        meconium = form_data.get("meconium_passed") in ['true', 'on', True]
        urine = form_data.get("urine_passed") in ['true', 'on', True]
        
        # Parse date fields
        def parse_date(field_name):
            d = form_data.get(field_name)
            if d:
                try:
                    return date.fromisoformat(d)
                except:
                    return None
            return None
        
        # Check if discharge record exists
        existing = baby_discharge_crud.get_baby_discharge_by_birth_record(db, record_id)
        
        if existing:
            # Update existing
            baby_discharge_crud.update_baby_discharge(
                db, existing,
                discharge_date=discharge_date_obj,
                heart_rate=heart_rate,
                respiratory_rate=respiratory_rate,
                temperature=temperature,
                weight_at_discharge=weight,
                breastfeeding_initiated=breastfeeding,
                suckling_established=suckling,
                meconium_passed=meconium,
                urine_passed=urine,
                eye_care_given=form_data.get("eye_care_given"),
                cord_care_date=parse_date("cord_care_date"),
                vitamin_k_date=parse_date("vitamin_k_date"),
                bcg_date=parse_date("bcg_date"),
                hepatitis_b_date=parse_date("hepatitis_b_date"),
                oral_polio_date=parse_date("oral_polio_date"),
                condition=form_data.get("condition"),
                abnormal_specify=form_data.get("abnormal_specify"),
                referred_to=form_data.get("referred_to"),
                notes=form_data.get("notes"),
            )
            db.commit()
            return {"success": True, "message": "Baby discharge summary updated"}
        else:
            # Create new
            baby_discharge_crud.create_baby_discharge(
                db,
                birth_record_id=record_id,
                discharge_date=discharge_date_obj,
                heart_rate=heart_rate,
                respiratory_rate=respiratory_rate,
                temperature=temperature,
                weight_at_discharge=weight,
                breastfeeding_initiated=breastfeeding,
                suckling_established=suckling,
                meconium_passed=meconium,
                urine_passed=urine,
                eye_care_given=form_data.get("eye_care_given"),
                cord_care_date=parse_date("cord_care_date"),
                vitamin_k_date=parse_date("vitamin_k_date"),
                bcg_date=parse_date("bcg_date"),
                hepatitis_b_date=parse_date("hepatitis_b_date"),
                oral_polio_date=parse_date("oral_polio_date"),
                condition=form_data.get("condition"),
                abnormal_specify=form_data.get("abnormal_specify"),
                referred_to=form_data.get("referred_to"),
                notes=form_data.get("notes"),
                recorded_by_id=current_user.id,
            )
            return {"success": True, "message": "Baby discharge summary created"}
            
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


# ============== DHIMS2 Export ==============
@router.get("/api/births/dhims2-export", name="birth_dhims2_export")
async def export_births_for_dhims2(
    start_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "HIO"])),
):
    """
    Export birth records in DHIMS2 format for reporting.
    
    Returns birth records mapped to DHIMS2 data elements for the specified period.
    """
    from app.integrations.dhims2.birth_mapper import BirthRecordMapper
    
    try:
        # Parse dates
        start = None
        end = None
        
        if start_date:
            try:
                start = date.fromisoformat(start_date)
            except ValueError:
                return JSONResponse(status_code=400, content={"error": "Invalid start_date format. Use YYYY-MM-DD"})
        
        if end_date:
            try:
                end = date.fromisoformat(end_date)
            except ValueError:
                return JSONResponse(status_code=400, content={"error": "Invalid end_date format. Use YYYY-MM-DD"})
        
        # Query birth records
        query = db.query(BirthRecord)
        
        if start:
            query = query.filter(BirthRecord.birth_date >= start)
        if end:
            query = query.filter(BirthRecord.birth_date <= end)
        
        birth_records = query.all()
        
        # Map to DHIMS2 format
        dhims2_data = []
        for record in birth_records:
            # Get baby discharge if exists
            baby_discharge = baby_discharge_crud.get_baby_discharge_by_birth_record(db, record.id)
            
            mapped = BirthRecordMapper.map_birth_record_to_dhims2(record, baby_discharge)
            mapped["birth_record_id"] = record.id
            mapped["birth_number"] = record.birth_number
            dhims2_data.append(mapped)
        
        # Get summary statistics
        summary = BirthRecordMapper.get_maternal_health_summary(birth_records)
        
        return {
            "success": True,
            "period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "total_records": len(birth_records),
            "summary": summary,
            "records": dhims2_data
        }
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============== Birth DHIMS Report Page ==============
@router.get("/reports/births/dhims", name="birth_dhims_report")
async def birth_dhims_report_page(
    request: Request,
    start_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(None, description="End date (YYYY-MM-DD)"),
    period: str = Query(None, description="Quick period filter"),
    format: str = Query(None, regex="html|pdf|excel|dhims2|csv"),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "HIO"])),
):
    """
    Display Birth & Delivery DHIMS Report page.
    
    Supports:
    - Quick period filters: this_month, last_month, this_quarter, this_year
    - Export formats: html (default), pdf, excel
    """
    from datetime import timedelta
    from app.crud import baby_discharge_crud
    from app.crud import hospital_settings_crud
    
    # Handle quick period filters
    today = date.today()
    if period == "this_month":
        start_date = date(today.year, today.month, 1).isoformat()
        end_date = today.isoformat()
    elif period == "last_month":
        first_day_this_month = date(today.year, today.month, 1)
        last_month_end = first_day_this_month - timedelta(days=1)
        start_date = date(last_month_end.year, last_month_end.month, 1).isoformat()
        end_date = last_month_end.isoformat()
    elif period == "this_quarter":
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        start_date = date(today.year, quarter_start_month, 1).isoformat()
        end_date = today.isoformat()
    elif period == "this_year":
        start_date = date(today.year, 1, 1).isoformat()
        end_date = today.isoformat()
    else:
        # Default to current month if no dates provided
        if not start_date:
            start_date = date(today.year, today.month, 1).isoformat()
        if not end_date:
            end_date = today.isoformat()
    
    # Get hospital settings for header
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    report_data = None
    
    if start_date and end_date:
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
            
            # Query birth records
            birth_records = db.query(BirthRecord).filter(
                BirthRecord.birth_date >= start,
                BirthRecord.birth_date <= end,
                BirthRecord.is_active == True
            ).all()
            
            # Build summary with all DHIMS2 indicators
            summary = {
                "total_deliveries": len(birth_records),
                "live_births": 0,
                "stillbirths": 0,
                "normal_delivery": 0,
                "vacuum_delivery": 0,
                "caesarean_section": 0,
                "low_birth_weight": 0,
                "very_low_birth_weight": 0,
                "blood_transfusion": 0,
                "manual_removal_placenta": 0,
                "bcg_given": 0,
                "vitamin_k_given": 0,
                "pnc_48hrs": 0,
                "pnc_6days": 0,
                "pnc_6weeks": 0,
                # New fields
                "facility_delivery": 0,
                "community_delivery": 0,
                "births_by_doctor": 0,
                "births_by_midwife": 0,
                "births_by_nurse": 0,
                "teenage_delivery": 0,
                "skin_to_skin": 0,
                "early_breastfeeding": 0,
                "preterm_births": 0,
                "term_births": 0,
                "multiple_births": 0,
                # Child sex statistics
                "male_babies": 0,
                "female_babies": 0,
            }
            
            # Build individual records list
            records = []
            for record in birth_records:
                # Count outcomes
                if record.birth_outcome:
                    if record.birth_outcome.lower() == "live":
                        summary["live_births"] += 1
                    elif record.birth_outcome.lower() == "stillbirth":
                        summary["stillbirths"] += 1
                
                # Count delivery types
                if record.delivery_type:
                    dt = record.delivery_type.lower()
                    if dt in ["vaginal", "normal"]:
                        summary["normal_delivery"] += 1
                    elif dt == "vacuum":
                        summary["vacuum_delivery"] += 1
                    elif dt == "caesarean":
                        summary["caesarean_section"] += 1
                
                # Count birth weight categories
                if record.weight_kg:
                    weight = float(record.weight_kg)
                    if weight < 1.5:
                        summary["very_low_birth_weight"] += 1
                        summary["low_birth_weight"] += 1
                    elif weight < 2.5:
                        summary["low_birth_weight"] += 1
                
                # Count blood transfusion
                if record.blood_transfusion:
                    summary["blood_transfusion"] += 1
                
                # Count manual removal
                if record.manual_removal_placenta:
                    summary["manual_removal_placenta"] += 1
                
                # Count immunisations
                if record.bcg_vaccine:
                    summary["bcg_given"] += 1
                if record.vitamin_k_administered:
                    summary["vitamin_k_given"] += 1
                
                # Count PNC
                if record.pnc1_date:
                    summary["pnc_48hrs"] += 1
                if record.pnc2_date:
                    summary["pnc_6days"] += 1
                if record.pnc3_date:
                    summary["pnc_6weeks"] += 1
                
                # Count place of delivery
                if record.place_of_delivery:
                    place = record.place_of_delivery.lower()
                    if "facility" in place or "hospital" in place or "health" in place:
                        summary["facility_delivery"] += 1
                    else:
                        summary["community_delivery"] += 1
                else:
                    # Default to facility if not specified
                    summary["facility_delivery"] += 1
                
                # Count birth attendant
                if record.attendant_category:
                    att = record.attendant_category.lower()
                    if "doctor" in att:
                        summary["births_by_doctor"] += 1
                    elif "midwife" in att:
                        summary["births_by_midwife"] += 1
                    elif "nurse" in att:
                        summary["births_by_nurse"] += 1
                
                # Count skin-to-skin
                if record.skin_to_skin:
                    summary["skin_to_skin"] += 1
                
                # Count early breastfeeding
                if record.breastfeeding_initiated_1hr or record.breastfeeding_30min:
                    summary["early_breastfeeding"] += 1
                
                # Count gestational age
                if record.gestational_age_weeks:
                    if record.gestational_age_weeks < 37:
                        summary["preterm_births"] += 1
                    elif record.gestational_age_weeks >= 37:
                        summary["term_births"] += 1
                
                # Count multiple births
                if record.number_of_babies and record.number_of_babies > 1:
                    summary["multiple_births"] += 1
                
                # Count child sex (male/female)
                if record.gender:
                    gender = record.gender.lower()
                    if gender == "male" or gender == "m":
                        summary["male_babies"] += 1
                    elif gender == "female" or gender == "f":
                        summary["female_babies"] += 1
                
                # Get mother name and age
                mother_name = ""
                mother_age = None
                if record.mother:
                    mother_name = f"{record.mother.first_name} {record.mother.last_name}"
                    if record.mother.date_of_birth:
                        mother_age = (today - record.mother.date_of_birth).days // 365
                        # Count teenage delivery (<18 years)
                        if mother_age and mother_age < 18:
                            summary["teenage_delivery"] += 1
                
                records.append({
                    "birth_date": record.birth_date.strftime("%Y-%m-%d") if record.birth_date else "",
                    "mother_name": mother_name,
                    "mother_age": mother_age,
                    "birth_outcome": record.birth_outcome or "",
                    "delivery_type": record.delivery_type or "",
                    "gender": record.gender or "",
                    "weight_kg": str(record.weight_kg) if record.weight_kg else "",
                    "bcg_vaccine": record.bcg_vaccine or False,
                    "pnc1_date": record.pnc1_date.strftime("%Y-%m-%d") if record.pnc1_date else None,
                    "place_of_delivery": record.place_of_delivery or "Facility",
                    "gestational_age": record.gestational_age_weeks,
                })
            
            # Calculate rates
            live_births = summary["live_births"] if summary["live_births"] > 0 else 1
            total_deliveries = summary["total_deliveries"] if summary["total_deliveries"] > 0 else 1
            
            summary["institutional_delivery_rate"] = round((summary["facility_delivery"] / total_deliveries) * 100, 1)
            summary["low_birth_weight_rate"] = round((summary["low_birth_weight"] / live_births) * 100, 1)
            summary["pnc_coverage_rate"] = round((summary["pnc_48hrs"] / live_births) * 100, 1)
            skilled_attendants = summary["births_by_doctor"] + summary["births_by_midwife"] + summary["births_by_nurse"]
            summary["skilled_birth_attendant_rate"] = round((skilled_attendants / total_deliveries) * 100, 1)
            
            report_data = {
                "summary": summary,
                "records": records,
                "start_date": start_date,
                "end_date": end_date,
            }
            
            # Handle export formats
            if format == "json":
                return {
                    "status": "success",
                    "report_type": "birth_dhims",
                    "period": {
                        "start": start_date,
                        "end": end_date
                    },
                    "generated_at": datetime.now().isoformat(),
                    "data": report_data
                }
            
            elif format == "csv":
                import csv
                import io
                from fastapi.responses import Response
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Header
                writer.writerow(["Indicator", "Value"])
                
                # Summary data
                for key, value in summary.items():
                    writer.writerow([key, value])
                
                output.seek(0)
                return Response(
                    content=output.getvalue(),
                    media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=birth_dhims_report_{start_date}_{end_date}.csv"}
                )
            
            elif format == "dhims2":
                # DHIMS2-compatible format
                return {
                    "org_unit": hospital_settings.hospital_name if hospital_settings else "Unknown",
                    "period": start.strftime("%Y%m"),
                    "data": {
                        "Total_Deliveries": summary["total_deliveries"],
                        "Live_Births": summary["live_births"],
                        "Still_Births": summary["stillbirths"],
                        "Normal_Delivery": summary["normal_delivery"],
                        "Vacuum_Delivery": summary["vacuum_delivery"],
                        "Caesarean_Section": summary["caesarean_section"],
                        "Low_Birth_Weight": summary["low_birth_weight"],
                        "Very_Low_Birth_Weight": summary["very_low_birth_weight"],
                        "Blood_Transfusion": summary["blood_transfusion"],
                        "Manual_Removal_Placenta": summary["manual_removal_placenta"],
                        "BCG_Vaccinated": summary["bcg_given"],
                        "Vitamin_K_Given": summary["vitamin_k_given"],
                        "PNC_48hrs": summary["pnc_48hrs"],
                        "PNC_6days": summary["pnc_6days"],
                        "PNC_6weeks": summary["pnc_6weeks"],
                        "Facility_Delivery": summary["facility_delivery"],
                        "Community_Delivery": summary["community_delivery"],
                        "Births_by_Doctor": summary["births_by_doctor"],
                        "Births_by_Midwife": summary["births_by_midwife"],
                        "Births_by_Nurse": summary["births_by_nurse"],
                        "Teenage_Delivery": summary["teenage_delivery"],
                        "Skin_to_Skin": summary["skin_to_skin"],
                        "Early_Breastfeeding": summary["early_breastfeeding"],
                        "Preterm_Births": summary["preterm_births"],
                        "Term_Births": summary["term_births"],
                        "Multiple_Births": summary["multiple_births"],
                        "Male_Babies": summary["male_babies"],
                        "Female_Babies": summary["female_babies"],
                        "Institutional_Delivery_Rate": summary["institutional_delivery_rate"],
                        "Low_Birth_Weight_Rate": summary["low_birth_weight_rate"],
                        "PNC_Coverage_Rate": summary["pnc_coverage_rate"],
                        "Skilled_Birth_Attendant_Rate": summary["skilled_birth_attendant_rate"],
                    }
                }
            
        except Exception as e:
            print(f"Error generating report: {e}")
    
    context = {
        "request": request,
        "title": "Birth & Delivery Report (DHIMS2)",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "start_date": start_date,
        "end_date": end_date,
        "period": period,
        "report_data": report_data,
        "hospital_settings": hospital_settings,
        "report_date": datetime.now(),
    }
    return templates.TemplateResponse("reports/birth_dhims_report.html", context)


# ============== DHIMS2 Auto-Sync ==============
@router.post("/api/births/sync-dhims2", name="birth_dhims2_auto_sync")
async def trigger_birth_dhims2_sync(
    request: Request,
    days_back: int = Form(7, description="Days to look back for records"),
    limit: int = Form(100, description="Maximum records to sync"),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
):
    """
    Trigger manual sync of birth records to DHIMS2.
    Can also be called via cron job for automatic daily sync.
    """
    from app.services.birth_dhims2_sync import sync_birth_records_to_dhims2
    
    try:
        result = sync_birth_records_to_dhims2(db, days_back=days_back, limit=limit)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/api/births/sync-status", name="birth_dhims2_sync_status")
async def get_birth_dhims2_sync_status(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
):
    """
    Get the status of the DHIMS2 birth sync cron job.
    """
    from app.services.birth_dhims2_sync import get_cron_job_status
    
    try:
        status = get_cron_job_status()
        return JSONResponse(content=status)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post("/api/births/sync-install", name="birth_dhims2_sync_install")
async def install_birth_dhims2_sync_cron(
    request: Request,
    hour: int = Form(6, ge=0, le=23, description="Hour of day (0-23) to run sync"),
    minute: int = Form(0, ge=0, le=59, description="Minute (0-59) to run sync"),
    current_user: User = Depends(role_required(["Admin"])),
):
    """
    Install automatic birth sync cron job.
    """
    from app.services.birth_dhims2_sync import install_cron_job
    
    try:
        success, message = install_cron_job(hour=hour, minute=minute)
        return JSONResponse(content={"success": success, "message": message})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/api/births/sync-remove", name="birth_dhims2_sync_remove")
async def remove_birth_dhims2_sync_cron(
    request: Request,
    current_user: User = Depends(role_required(["Admin"])),
):
    """
    Remove automatic birth sync cron job.
    """
    from app.services.birth_dhims2_sync import remove_cron_job
    
    try:
        success, message = remove_cron_job()
        return JSONResponse(content={"success": success, "message": message})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )
