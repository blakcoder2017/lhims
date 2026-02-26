"""
CRUD operations for Baby Discharge Summary
Handles individual baby discharge records for multiple births
"""
from datetime import date
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.baby_discharge_models import BabyDischarge


def create_baby_discharge(
    db: Session,
    birth_record_id: int,
    discharge_date: Optional[date] = None,
    heart_rate: Optional[int] = None,
    respiratory_rate: Optional[int] = None,
    temperature: Optional[float] = None,
    weight_at_discharge: Optional[float] = None,
    breastfeeding_initiated: Optional[bool] = None,
    suckling_established: Optional[bool] = None,
    meconium_passed: Optional[bool] = None,
    urine_passed: Optional[bool] = None,
    eye_care_given: Optional[str] = None,
    cord_care_date: Optional[date] = None,
    vitamin_k_date: Optional[date] = None,
    bcg_date: Optional[date] = None,
    hepatitis_b_date: Optional[date] = None,
    oral_polio_date: Optional[date] = None,
    condition: Optional[str] = None,
    abnormal_specify: Optional[str] = None,
    referred_to: Optional[str] = None,
    notes: Optional[str] = None,
    recorded_by_id: Optional[int] = None,
) -> BabyDischarge:
    """Create a new baby discharge summary."""
    baby_discharge = BabyDischarge(
        birth_record_id=birth_record_id,
        discharge_date=discharge_date,
        heart_rate=heart_rate,
        respiratory_rate=respiratory_rate,
        temperature=temperature,
        weight_at_discharge=weight_at_discharge,
        breastfeeding_initiated=breastfeeding_initiated,
        suckling_established=suckling_established,
        meconium_passed=meconium_passed,
        urine_passed=urine_passed,
        eye_care_given=eye_care_given,
        cord_care_date=cord_care_date,
        vitamin_k_date=vitamin_k_date,
        bcg_date=bcg_date,
        hepatitis_b_date=hepatitis_b_date,
        oral_polio_date=oral_polio_date,
        condition=condition,
        abnormal_specify=abnormal_specify,
        referred_to=referred_to,
        notes=notes,
        recorded_by_id=recorded_by_id,
        created_at=date.today()
    )
    db.add(baby_discharge)
    db.commit()
    db.refresh(baby_discharge)
    return baby_discharge


def get_baby_discharge_by_birth_record(
    db: Session, 
    birth_record_id: int
) -> Optional[BabyDischarge]:
    """Get baby discharge summary by birth record ID."""
    return db.query(BabyDischarge).filter(
        BabyDischarge.birth_record_id == birth_record_id
    ).first()


def update_baby_discharge(
    db: Session,
    baby_discharge: BabyDischarge,
    discharge_date: Optional[date] = None,
    heart_rate: Optional[int] = None,
    respiratory_rate: Optional[int] = None,
    temperature: Optional[float] = None,
    weight_at_discharge: Optional[float] = None,
    breastfeeding_initiated: Optional[bool] = None,
    suckling_established: Optional[bool] = None,
    meconium_passed: Optional[bool] = None,
    urine_passed: Optional[bool] = None,
    eye_care_given: Optional[str] = None,
    cord_care_date: Optional[date] = None,
    vitamin_k_date: Optional[date] = None,
    bcg_date: Optional[date] = None,
    hepatitis_b_date: Optional[date] = None,
    oral_polio_date: Optional[date] = None,
    condition: Optional[str] = None,
    abnormal_specify: Optional[str] = None,
    referred_to: Optional[str] = None,
    notes: Optional[str] = None,
) -> BabyDischarge:
    """Update baby discharge summary."""
    if discharge_date is not None:
        baby_discharge.discharge_date = discharge_date
    if heart_rate is not None:
        baby_discharge.heart_rate = heart_rate
    if respiratory_rate is not None:
        baby_discharge.respiratory_rate = respiratory_rate
    if temperature is not None:
        baby_discharge.temperature = temperature
    if weight_at_discharge is not None:
        baby_discharge.weight_at_discharge = weight_at_discharge
    if breastfeeding_initiated is not None:
        baby_discharge.breastfeeding_initiated = breastfeeding_initiated
    if suckling_established is not None:
        baby_discharge.suckling_established = suckling_established
    if meconium_passed is not None:
        baby_discharge.meconium_passed = meconium_passed
    if urine_passed is not None:
        baby_discharge.urine_passed = urine_passed
    if eye_care_given is not None:
        baby_discharge.eye_care_given = eye_care_given
    if cord_care_date is not None:
        baby_discharge.cord_care_date = cord_care_date
    if vitamin_k_date is not None:
        baby_discharge.vitamin_k_date = vitamin_k_date
    if bcg_date is not None:
        baby_discharge.bcg_date = bcg_date
    if hepatitis_b_date is not None:
        baby_discharge.hepatitis_b_date = hepatitis_b_date
    if oral_polio_date is not None:
        baby_discharge.oral_polio_date = oral_polio_date
    if condition is not None:
        baby_discharge.condition = condition
    if abnormal_specify is not None:
        baby_discharge.abnormal_specify = abnormal_specify
    if referred_to is not None:
        baby_discharge.referred_to = referred_to
    if notes is not None:
        baby_discharge.notes = notes
    
    baby_discharge.updated_at = date.today()
    db.commit()
    db.refresh(baby_discharge)
    return baby_discharge