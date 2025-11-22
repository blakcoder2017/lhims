"""
Procedure Reports CRUD Operations

Database operations for procedure reporting and analytics.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, extract
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.models.procedure_models import Procedure, ProcedureType, ProcedureStatus
from app.models.patient_models import Patient
from app.models.procedure_catalog_models import ProcedureCatalog
from app.utils.patient_utils import calculate_age


def get_procedure_statistics(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    procedure_type: Optional[ProcedureType] = None,
    procedure_category: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get comprehensive procedure statistics.
    Returns statistics grouped by gender, age groups, and procedure type.
    """
    # Base query
    query = db.query(Procedure).join(Patient).filter(
        Procedure.is_active == True,
        Procedure.status == ProcedureStatus.COMPLETED
    )
    
    # Apply date filters
    if start_date:
        query = query.filter(func.date(Procedure.scheduled_date) >= start_date)
    if end_date:
        query = query.filter(func.date(Procedure.scheduled_date) <= end_date)
    
    # Apply procedure type filter
    if procedure_type:
        query = query.filter(Procedure.procedure_type == procedure_type)
    
    # Apply procedure category filter (if we link to catalog)
    if procedure_category:
        # This would require joining with ProcedureCatalog
        # For now, we'll filter by procedure_name containing category
        query = query.filter(Procedure.procedure_name.ilike(f"%{procedure_category}%"))
    
    procedures = query.all()
    
    # Calculate statistics
    total_procedures = len(procedures)
    
    # Group by gender
    gender_stats = {}
    for procedure in procedures:
        gender = procedure.patient.gender or "Unknown"
        if gender not in gender_stats:
            gender_stats[gender] = {
                "count": 0,
                "procedures": []
            }
        gender_stats[gender]["count"] += 1
        gender_stats[gender]["procedures"].append(procedure)
    
    # Group by age groups
    age_groups = {
        "0-18": {"min": 0, "max": 18, "count": 0, "procedures": []},
        "19-35": {"min": 19, "max": 35, "count": 0, "procedures": []},
        "36-50": {"min": 36, "max": 50, "count": 0, "procedures": []},
        "51-65": {"min": 51, "max": 65, "count": 0, "procedures": []},
        "65+": {"min": 65, "max": 999, "count": 0, "procedures": []}
    }
    
    for procedure in procedures:
        age = calculate_age(procedure.patient.date_of_birth)
        for group_name, group_data in age_groups.items():
            if group_data["min"] <= age <= group_data["max"]:
                group_data["count"] += 1
                group_data["procedures"].append(procedure)
                break
    
    # Group by procedure type
    procedure_type_stats = {}
    for procedure in procedures:
        proc_type = procedure.procedure_type.value if procedure.procedure_type else "Unknown"
        if proc_type not in procedure_type_stats:
            procedure_type_stats[proc_type] = {
                "count": 0,
                "procedures": []
            }
        procedure_type_stats[proc_type]["count"] += 1
        procedure_type_stats[proc_type]["procedures"].append(procedure)
    
    # Group by procedure name (most common procedures)
    procedure_name_stats = {}
    for procedure in procedures:
        proc_name = procedure.procedure_name
        if proc_name not in procedure_name_stats:
            procedure_name_stats[proc_name] = {
                "count": 0,
                "procedures": []
            }
        procedure_name_stats[proc_name]["count"] += 1
        procedure_name_stats[proc_name]["procedures"].append(procedure)
    
    # Sort by count
    procedure_name_stats = dict(sorted(
        procedure_name_stats.items(),
        key=lambda x: x[1]["count"],
        reverse=True
    ))
    
    # Calculate average duration
    durations = [p.duration_minutes for p in procedures if p.duration_minutes]
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    # Calculate complications rate
    complications_count = sum(1 for p in procedures if p.complications)
    complications_rate = (complications_count / total_procedures * 100) if total_procedures > 0 else 0
    
    return {
        "total_procedures": total_procedures,
        "gender_stats": gender_stats,
        "age_group_stats": age_groups,
        "procedure_type_stats": procedure_type_stats,
        "procedure_name_stats": procedure_name_stats,
        "average_duration_minutes": avg_duration,
        "complications_count": complications_count,
        "complications_rate": complications_rate,
        "start_date": start_date,
        "end_date": end_date
    }


def get_procedure_report_by_gender_age_type(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """
    Get procedure report segregated by gender, age, and procedure type.
    Returns a detailed breakdown for reporting.
    """
    # Base query
    query = db.query(
        Procedure,
        Patient.gender,
        Patient.date_of_birth,
        Procedure.procedure_type,
        Procedure.procedure_name
    ).join(Patient).filter(
        Procedure.is_active == True,
        Procedure.status == ProcedureStatus.COMPLETED
    )
    
    # Apply date filters
    if start_date:
        query = query.filter(func.date(Procedure.scheduled_date) >= start_date)
    if end_date:
        query = query.filter(func.date(Procedure.scheduled_date) <= end_date)
    
    results = query.all()
    
    # Build detailed report
    report_data = []
    
    for procedure, gender, dob, proc_type, proc_name in results:
        age = calculate_age(dob)
        
        # Determine age group
        if age <= 18:
            age_group = "0-18"
        elif age <= 35:
            age_group = "19-35"
        elif age <= 50:
            age_group = "36-50"
        elif age <= 65:
            age_group = "51-65"
        else:
            age_group = "65+"
        
        report_data.append({
            "procedure_id": procedure.id,
            "procedure_number": procedure.procedure_number,
            "procedure_name": proc_name,
            "procedure_type": proc_type.value if proc_type else "Unknown",
            "patient_id": procedure.patient_id,
            "patient_name": f"{procedure.patient.first_name} {procedure.patient.last_name}",
            "gender": gender or "Unknown",
            "age": age,
            "age_group": age_group,
            "scheduled_date": procedure.scheduled_date,
            "duration_minutes": procedure.duration_minutes,
            "findings": procedure.findings,
            "complications": procedure.complications,
            "outcome": procedure.outcome,
            "performed_by": procedure.performed_by.full_name if procedure.performed_by else None
        })
    
    return report_data

