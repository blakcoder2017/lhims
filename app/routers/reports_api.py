"""
Reports API Routes

Routes for generating various reports including:
- Admission reports with PDF export
- Financial reports (pharmacy, radiology, lab breakdown)
- Patient demographics reports
"""
from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from urllib.parse import quote
from app.core.templates import templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import Optional, List
from datetime import datetime, date, timedelta
from decimal import Decimal
import json

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.crud import ipd_crud, patient_crud, billing_crud, drug_administration_crud, procedure_reports_crud, procedure_reports_crud
from app.models.ipd_models import Admission, AdmissionStatus, AdmissionNote, DischargeStatus
from app.models.billing_models import Invoice, Charge, ChargeType, Payment, PaymentStatus, InvoiceStatus
from app.models.patient_models import Patient, PaymentMechanism
from app.models.encounter_models import Encounter, EncounterStatus, LabOrder, RadiologyOrder, Prescription
from app.models.procedure_models import Procedure
from app.models.expense_models import Expense, ExpenseCategory, ExpenseStatus
from app.models.opd_models import OPDVisit, OPDVisitStatus
from app.models.disease_models import Disease, EncounterDisease
from app.models.pharmacy_models import PharmacyDispense, PharmacyDispenseItem
from app.models.department_models import Department
from app.crud import hospital_settings_crud, opd_crud, user_crud, service_pricing_crud
from app.models.user_models import User, Role

router = APIRouter(prefix="/reports", tags=["Reports"])

DEFAULT_CONSULTATION_FEE = Decimal('100.00')
# Register the age filter
from datetime import date
def calculate_age(dob):
    if not dob:
        return None
    if isinstance(dob, str):
        dob = date.fromisoformat(dob)
    today = date.today()
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age
templates.env.filters["age"] = calculate_age


@router.get("/", name="reports_dashboard")
def reports_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Management", "Doctor"]))
):
    """Reports dashboard - lists all available reports.
    Note: Financial reports section is restricted to Admin, Management, Finance in template."""
    context = {
        "request": request,
        "title": "Reports Dashboard",
        "current_user": current_user,
        "user_role": current_user.role.name
    }
    return templates.TemplateResponse("reports/dashboard.html", context)


@router.get("/admissions/{admission_id}/referral", name="referral_report")
def referral_report(
    request: Request,
    admission_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Nurse", "Front Office"])),
    receiving_hospital: Optional[str] = Query(None, description="Name of receiving hospital"),
    reason_for_referral: Optional[str] = Query(None, description="Reason for referral"),
    format: str = Query("html", regex="^(html|pdf)$")
):
    """
    Generate a referral report for patient transfer to another hospital.
    Can be regenerated as needed.
    """
    from app.services.referral_report_service import generate_referral_report
    
    try:
        report_data = generate_referral_report(
            db, 
            admission_id, 
            receiving_hospital=receiving_hospital,
            reason_for_referral=reason_for_referral
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    context = {
        "request": request,
        "title": f"Referral Report - {report_data['admission'].admission_number}",
        "current_user": current_user,
        **report_data
    }
    
    if format == "pdf":
        from app.utils.pdf_generator import generate_referral_report_pdf
        pdf_content = generate_referral_report_pdf(context)
        filename_safe = f"referral_report_{report_data['admission'].admission_number}.pdf"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename_safe}"}
        )
    
    return templates.TemplateResponse("reports/referral_report.html", context)


@router.get("/admissions/{admission_id}/report", name="admission_report")
def admission_report(
    request: Request,
    admission_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Nurse", "Front Office", "Finance"])),
    format: str = Query("html", regex="^(html|pdf)$")
):
    
    # Get admission with all related data
    admission = db.query(Admission).options(
        joinedload(Admission.patient),
        joinedload(Admission.ward),
        joinedload(Admission.bed),
        joinedload(Admission.admitted_by),
        joinedload(Admission.discharged_by),
        joinedload(Admission.encounters).joinedload(Encounter.clinician),
        joinedload(Admission.invoice)
    ).filter(Admission.id == admission_id).first()
    
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    
    # Get medication administrations
    administrations = drug_administration_crud.get_drug_administrations_by_admission(db, admission_id)
    
    # Get admission notes
    notes = db.query(AdmissionNote).filter(
        AdmissionNote.admission_id == admission_id,
        AdmissionNote.is_active == True
    ).order_by(AdmissionNote.created_at.desc()).all()
    
    # Get vitals from encounters
    from app.models.triage_models import TriageVitals
    vitals_records = []
    for encounter in admission.encounters:
        if encounter.patient_id:
            vitals = db.query(TriageVitals).filter(
                TriageVitals.patient_id == encounter.patient_id
            ).order_by(TriageVitals.recorded_at.desc()).limit(5).all()
            vitals_records.extend(vitals)
    
    # Get lab orders and results
    lab_orders = []
    from app.models.lab_template_models import LabTemplateVersion
    for encounter in admission.encounters:
        orders = db.query(LabOrder).options(
            joinedload(LabOrder.ordered_by),
            joinedload(LabOrder.result_entered_by),
            joinedload(LabOrder.verified_by),
            joinedload(LabOrder.authorized_by)
        ).filter(LabOrder.encounter_id == encounter.id).all()
        
        # Load schema_json for each order with template
        for order in orders:
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
        
        lab_orders.extend(orders)
    
    # Get prescriptions
    prescriptions = []
    for encounter in admission.encounters:
        prescriptions.extend(db.query(Prescription).filter(Prescription.encounter_id == encounter.id).all())
    
    # Get radiology orders
    radiology_orders = []
    for encounter in admission.encounters:
        radiology_orders.extend(db.query(RadiologyOrder).filter(RadiologyOrder.encounter_id == encounter.id).all())
    
    # Calculate length of stay
    # Convert datetime to date if needed
    admission_date = admission.admission_date.date() if isinstance(admission.admission_date, datetime) else admission.admission_date
    if admission.discharge_date:
        discharge_date = admission.discharge_date.date() if isinstance(admission.discharge_date, datetime) else admission.discharge_date
        los = (discharge_date - admission_date).days
    else:
        los = (date.today() - admission_date).days
    
    # Get hospital settings
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": f"Admission Report - {admission.admission_number}",
        "current_user": current_user,
        "admission": admission,
        "patient": admission.patient,  # Add patient to context for template
        "drug_administrations": administrations,
        "admission_notes": notes,
        "vitals": vitals_records[:10],  # Limit to 10 most recent
        "lab_orders": lab_orders,
        "radiology_orders": radiology_orders,
        "prescriptions": prescriptions,
        "final_diagnosis": admission.discharge_diagnosis,
        "length_of_stay": los,
        "hospital_settings": hospital_settings,
        "report_date": datetime.now()
    }
    
    if format == "pdf":
        from app.utils.pdf_generator import generate_admission_report_pdf
        pdf_content = generate_admission_report_pdf(context)
        filename_safe = f"admission_report_{admission.admission_number}.pdf"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename_safe}"}
        )
    
    return templates.TemplateResponse("reports/admission_report.html", context)


@router.get("/financial", name="financial_report")
def financial_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    service_type: Optional[str] = Query(None),
    payment_mechanism: Optional[str] = Query(None),
    format: str = Query("html", regex="^(html|pdf|excel)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Management"]))
):
    """Generate financial report with breakdown by service type."""
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today() - timedelta(days=30)  # Default: last 30 days
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Build query filters
    filters = [
        Invoice.is_active == True,
        func.date(Invoice.invoice_date) >= start,
        func.date(Invoice.invoice_date) <= end
    ]
    
    if payment_mechanism:
        filters.append(Invoice.payment_mechanism == payment_mechanism)
    
    # Get all invoices in date range with patient data
    invoices = db.query(Invoice).options(
        joinedload(Invoice.patient)
    ).filter(*filters).order_by(Invoice.invoice_date.desc()).all()
    
    # Get all charges for these invoices
    invoice_ids = [inv.id for inv in invoices]
    charges = db.query(Charge).filter(Charge.invoice_id.in_(invoice_ids)).all()
    
    # Get all payments
    payments = db.query(Payment).filter(
        Payment.invoice_id.in_(invoice_ids),
        Payment.is_active == True
    ).all()
    
    # Calculate totals
    total_revenue = sum([inv.total_amount for inv in invoices])
    total_paid = sum([p.amount for p in payments])
    total_outstanding = total_revenue - total_paid
    
    # Breakdown by service type
    service_breakdown = {}
    for charge in charges:
        if service_type and charge.charge_type.value != service_type:
            continue
        
        ct = charge.charge_type.value
        if ct not in service_breakdown:
            service_breakdown[ct] = {
                "count": 0,
                "total": Decimal('0.00'),
                "paid": Decimal('0.00')
            }
        
        service_breakdown[ct]["count"] += 1
        service_breakdown[ct]["total"] += charge.total_amount
        
        # Find payments for this charge's invoice
        invoice = next((inv for inv in invoices if inv.id == charge.invoice_id), None)
        if invoice:
            service_breakdown[ct]["paid"] += invoice.paid_amount or Decimal('0.00')
    
    # Breakdown by payment mechanism
    payment_breakdown = {}
    for invoice in invoices:
        pm = invoice.payment_mechanism.value if invoice.payment_mechanism else "unknown"
        if pm not in payment_breakdown:
            payment_breakdown[pm] = {
                "count": 0,
                "total": Decimal('0.00'),
                "paid": Decimal('0.00')
            }
        
        payment_breakdown[pm]["count"] += 1
        payment_breakdown[pm]["total"] += invoice.total_amount
        payment_breakdown[pm]["paid"] += invoice.paid_amount
    
    # Get detailed invoice data with patient and charge information
    invoices_detailed = []
    for invoice in invoices:
        invoice_charges = [c for c in charges if c.invoice_id == invoice.id]
        invoice_payments = [p for p in payments if p.invoice_id == invoice.id]
        invoices_detailed.append({
            "invoice": invoice,
            "charges": invoice_charges,
            "payments": invoice_payments,
            "patient": invoice.patient if hasattr(invoice, 'patient') else None
        })
    
    # Get hospital settings
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": "Financial Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "service_type": service_type,
        "payment_mechanism": payment_mechanism,
        "total_revenue": total_revenue,
        "total_paid": total_paid,
        "total_outstanding": total_outstanding,
        "service_breakdown": service_breakdown,
        "payment_breakdown": payment_breakdown,
        "invoices": invoices,  # All invoices for export
        "invoices_detailed": invoices_detailed,  # Detailed invoice data
        "charges": charges,  # All charges
        "payments": payments,  # All payments
        "hospital_settings": hospital_settings,
        "report_date": datetime.now()
    }
    
    if format == "pdf":
        from app.utils.pdf_generator import generate_financial_report_pdf
        pdf_content = generate_financial_report_pdf(context)
        filename_safe = f"financial_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.pdf"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename_safe}"
            }
        )
    elif format == "excel":
        from app.utils.excel_generator import generate_financial_report_excel
        excel_content = generate_financial_report_excel(context)
        filename_safe = f"financial_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.xlsx"
        return Response(
            content=excel_content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename_safe}"
            }
        )
    
    return templates.TemplateResponse("reports/financial_report.html", context)


@router.get("/financial/by-department", name="department_financial_report")
def department_financial_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    format: str = Query("html", regex="^(html|pdf|excel)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Management"]))
):
    """Generate financial report grouped by department.
    
    All charges (procedures, lab tests, radiology, etc.) are grouped by their
    associated department. For procedures, this uses the department from ProcedureCatalog
    by linking through procedures performed in encounters or by parsing procedure ID from description.
    """
    from app.models.procedure_catalog_models import ProcedureCatalog
    from app.models.procedure_models import Procedure
    import re
    
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today() - timedelta(days=30)  # Default: last 30 days
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Get all departments
    departments = db.query(Department).filter(Department.is_active == True).order_by(Department.name).all()
    
    # Build base filter for invoices
    invoice_filters = [
        Invoice.is_active == True,
        func.date(Invoice.invoice_date) >= start,
        func.date(Invoice.invoice_date) <= end
    ]
    
    # Get all invoices in date range
    invoices = db.query(Invoice).filter(*invoice_filters).all()
    invoice_ids = [inv.id for inv in invoices]
    
    if not invoice_ids:
        # No invoices in date range, return empty data
        department_data = {}
        total_revenue = Decimal('0.00')
        total_charges = 0
    else:
        # Get all charges for these invoices
        charges = db.query(Charge).filter(
            Charge.invoice_id.in_(invoice_ids),
            Charge.is_active == True
        ).all()
        
        # Build procedure_id to department mapping from procedure_catalog
        # First, get all procedures
        all_procedures = db.query(Procedure).filter(Procedure.is_active == True).all()
        procedure_to_dept = {}
        for proc in all_procedures:
            if proc.procedure_catalog_id:
                # Get department from procedure_catalog
                proc_catalog = db.query(ProcedureCatalog).filter(
                    ProcedureCatalog.id == proc.procedure_catalog_id
                ).first()
                if proc_catalog and proc_catalog.department_id:
                    procedure_to_dept[proc.id] = proc_catalog.department_id
        
        # Also build procedure_catalog_id to department mapping
        all_proc_catalogs = db.query(ProcedureCatalog).filter(
            ProcedureCatalog.department_id.isnot(None)
        ).all()
        proc_catalog_to_dept = {pc.id: pc.department_id for pc in all_proc_catalogs}
        
        # For each charge, determine its department
        charge_to_dept = {}
        for charge in charges:
            dept = None
            
            # 1. Check if charge has direct department_id
            if charge.department_id:
                dept = charge.department_id
            # 2. Check if charge has procedure_catalog_id
            elif charge.procedure_catalog_id and charge.procedure_catalog_id in proc_catalog_to_dept:
                dept = proc_catalog_to_dept[charge.procedure_catalog_id]
            # 3. For procedure charges, try to parse procedure number from description
            elif charge.charge_type and charge.charge_type.value == 'procedure':
                # Parse "Procedure #123: NAME" to get procedure ID
                match = re.search(r'#(\d+):', charge.description or '')
                if match:
                    proc_id = int(match.group(1))
                    if proc_id in procedure_to_dept:
                        dept = procedure_to_dept[proc_id]
            
            charge_to_dept[charge.id] = dept
        
        # Group charges by department
        department_data = {}
        for dept in departments:
            dept_charges = [c for c in charges if charge_to_dept.get(c.id) == dept.id]
            
            if dept_charges:
                # Group by charge type within department
                type_breakdown = {}
                for charge in dept_charges:
                    ct = charge.charge_type.value if charge.charge_type else "other"
                    if ct not in type_breakdown:
                        type_breakdown[ct] = {
                            "count": 0,
                            "total": Decimal('0.00')
                        }
                    type_breakdown[ct]["count"] += 1
                    type_breakdown[ct]["total"] += charge.total_amount or Decimal('0.00')
                
                dept_total = sum(c.total_amount or Decimal('0.00') for c in dept_charges)
                department_data[dept.id] = {
                    "name": dept.name,
                    "code": dept.code,
                    "charge_count": len(dept_charges),
                    "total_income": dept_total,
                    "type_breakdown": type_breakdown
                }
        
        # Also include charges without department (unassigned)
        unassigned_charges = [c for c in charges if charge_to_dept.get(c.id) is None]
        
        if unassigned_charges:
            unassigned_total = sum(c.total_amount or Decimal('0.00') for c in unassigned_charges)
            type_breakdown = {}
            for charge in unassigned_charges:
                ct = charge.charge_type.value if charge.charge_type else "other"
                if ct not in type_breakdown:
                    type_breakdown[ct] = {"count": 0, "total": Decimal('0.00')}
                type_breakdown[ct]["count"] += 1
                type_breakdown[ct]["total"] += charge.total_amount or Decimal('0.00')
            
            department_data[0] = {
                "name": "Unassigned",
                "code": None,
                "charge_count": len(unassigned_charges),
                "total_income": unassigned_total,
                "type_breakdown": type_breakdown
            }
        
        # Calculate grand totals
        total_revenue = sum(department_data[d]["total_income"] for d in department_data)
        total_charges = sum(department_data[d]["charge_count"] for d in department_data)
    
    # Get hospital settings
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": "Department Financial Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "department_id": department_id,
        "departments": departments,
        "department_data": department_data,
        "total_revenue": total_revenue,
        "total_charges": total_charges,
        "hospital_settings": hospital_settings,
        "report_date": datetime.now()
    }
    
    if format == "pdf":
        # PDF generation - can be implemented similarly to financial report
        pass
    elif format == "excel":
        # Excel generation - can be implemented similarly to financial report
        pass
    
    return templates.TemplateResponse("reports/department_financial_report.html", context)


@router.get("/patients/demographics", name="patient_demographics_report")
def patient_demographics_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: str = Query("html", regex="^(html|pdf|excel)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Management", "Doctor"]))
):
    """Generate patient demographics report."""
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today() - timedelta(days=365)  # Default: last year
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Get patients registered in date range
    patients = db.query(Patient).filter(
        Patient.is_active == True,
        func.date(Patient.created_at) >= start,
        func.date(Patient.created_at) <= end
    ).all()
    
    # Demographics breakdown
    total_patients = len(patients)
    
    # By gender
    gender_breakdown = {}
    for patient in patients:
        gender = patient.gender or "Unknown"
        gender_breakdown[gender] = gender_breakdown.get(gender, 0) + 1
    
    # By payment mechanism
    payment_breakdown = {}
    for patient in patients:
        pm = patient.payment_mechanism.value if patient.payment_mechanism else "unknown"
        payment_breakdown[pm] = payment_breakdown.get(pm, 0) + 1
    
    # By age groups
    from app.utils.patient_utils import calculate_age
    age_groups = {
        "0-5": 0,
        "6-12": 0,
        "13-18": 0,
        "19-35": 0,
        "36-50": 0,
        "51-65": 0,
        "65+": 0
    }
    
    for patient in patients:
        if not patient.date_of_birth:
            continue
        age_data = calculate_age(patient.date_of_birth)
        age = age_data.get("years", 0)  # Extract years from the dictionary
        if age <= 5:
            age_groups["0-5"] += 1
        elif age <= 12:
            age_groups["6-12"] += 1
        elif age <= 18:
            age_groups["13-18"] += 1
        elif age <= 35:
            age_groups["19-35"] += 1
        elif age <= 50:
            age_groups["36-50"] += 1
        elif age <= 65:
            age_groups["51-65"] += 1
        else:
            age_groups["65+"] += 1
    
    # Top conditions (from encounters)
    condition_counts = {}
    encounters = db.query(Encounter).filter(
        Encounter.patient_id.in_([p.id for p in patients]),
        Encounter.is_active == True
    ).all()
    
    for encounter in encounters:
        if encounter.primary_diagnosis_description:
            condition = encounter.primary_diagnosis_description
            condition_counts[condition] = condition_counts.get(condition, 0) + 1
    
    top_conditions = sorted(condition_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    context = {
        "request": request,
        "title": "Patient Demographics Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "total_patients": total_patients,
        "gender_breakdown": gender_breakdown,
        "payment_breakdown": payment_breakdown,
        "age_groups": age_groups,
        "top_conditions": top_conditions,
        "report_date": datetime.now()
    }
    
    if format == "pdf":
        from app.utils.pdf_generator import generate_demographics_report_pdf
        pdf_content = generate_demographics_report_pdf(context)
        filename_safe = f"demographics_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.pdf"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename_safe}"}
        )
    
    return templates.TemplateResponse("reports/patient_demographics_report.html", context)


@router.get("/income-statement", name="income_statement")
def income_statement(
    request: Request,
    period: Optional[str] = Query("custom", regex="^(day|month|year|custom)$"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: str = Query("html", regex="^(html|pdf|excel)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Management"]))
):
    """Generate Income Statement (Profit & Loss Statement) for a given period."""
    # Get hospital settings
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    # Determine date range based on period type
    today = date.today()
    if period == "day":
        start = today
        end = today
        period_label = f"{today.strftime('%B %d, %Y')}"
    elif period == "month":
        start = date(today.year, today.month, 1)
        end = today
        period_label = f"{today.strftime('%B %Y')}"
    elif period == "year":
        start = date(today.year, 1, 1)
        end = today
        period_label = f"{today.year}"
    else:  # custom
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start = date.today() - timedelta(days=30)
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end = date.today()
        period_label = f"{start.strftime('%B %d, %Y')} - {end.strftime('%B %d, %Y')}"
    
    # Calculate REVENUE from payments (actual cash received)
    # Revenue = sum of all payments made within the period
    payments = db.query(Payment).filter(
        func.date(Payment.payment_date) >= start,
        func.date(Payment.payment_date) <= end,
        Payment.status == PaymentStatus.COMPLETED.value,
        Payment.is_active == True
    ).all()
    
    total_revenue = sum([p.amount for p in payments])
    
    # Revenue breakdown by payment method
    revenue_by_method = {}
    for payment in payments:
        method = payment.payment_method.value if payment.payment_method else "unknown"
        if method not in revenue_by_method:
            revenue_by_method[method] = Decimal('0.00')
        revenue_by_method[method] += payment.amount
    
    # Revenue breakdown by service type (from charges on invoices that have payments)
    revenue_by_service = {}
    for payment in payments:
        invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id).first()
        if invoice:
            # Calculate payment ratio (if partial payment)
            payment_ratio = Decimal(payment.amount / invoice.total_amount) if invoice.total_amount > 0 else Decimal('1.0')
            
            # Get charges for this invoice
            charges = db.query(Charge).filter(Charge.invoice_id == invoice.id).all()
            for charge in charges:
                service_type = charge.charge_type.value
                if service_type not in revenue_by_service:
                    revenue_by_service[service_type] = Decimal('0.00')
                revenue_by_service[service_type] += charge.total_amount * payment_ratio
    
    # Calculate EXPENSES
    expenses = db.query(Expense).filter(
        func.date(Expense.expense_date) >= start,
        func.date(Expense.expense_date) <= end,
        Expense.status == ExpenseStatus.APPROVED.value,
        Expense.is_active == True
    ).all()
    
    total_expenses = sum([e.amount for e in expenses])
    
    # Expense breakdown by category
    expenses_by_category = {}
    for expense in expenses:
        category = expense.category.value if expense.category else "other"
        if category not in expenses_by_category:
            expenses_by_category[category] = Decimal('0.00')
        expenses_by_category[category] += expense.amount
    
    # Calculate NET INCOME
    net_income = total_revenue - total_expenses
    
    # Calculate profit margin
    profit_margin = (net_income / total_revenue * 100) if total_revenue > 0 else Decimal('0.00')
    
    period_label_safe = period_label.replace(" ", "_").replace(",", "").replace("-", "_")
    
    context = {
        "request": request,
        "title": "Income Statement (Profit & Loss)",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "period": period,
        "period_label": period_label,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "total_revenue": total_revenue,
        "revenue_by_method": revenue_by_method,
        "revenue_by_service": revenue_by_service,
        "total_expenses": total_expenses,
        "expenses_by_category": expenses_by_category,
        "net_income": net_income,
        "profit_margin": profit_margin,
        "hospital_settings": hospital_settings,
        "report_date": datetime.now()
    }
    
    if format == "pdf":
        from app.utils.pdf_generator import generate_income_statement_pdf
        pdf_content = generate_income_statement_pdf(context)
        filename = f"income_statement_{period_label_safe}.pdf"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    elif format == "excel":
        from app.utils.excel_generator import generate_income_statement_excel
        excel_content = generate_income_statement_excel(context)
        filename = f"income_statement_{period_label_safe}.xlsx"
        return Response(
            content=excel_content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    return templates.TemplateResponse("reports/income_statement.html", context)


@router.get("/opd/detailed", name="opd_detailed_report")
def opd_detailed_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    format: str = Query("html", regex="^(html|pdf|excel|csv)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Nurse", "Front Office", "Management"]))
):
    """Generate detailed OPD report with visit statistics and revenue."""
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today() - timedelta(days=30)  # Default: last 30 days
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Build query filters
    filters = [
        OPDVisit.is_active == True,
        func.date(OPDVisit.visit_date) >= start,
        func.date(OPDVisit.visit_date) <= end
    ]
    
    if status:
        filters.append(OPDVisit.status == OPDVisitStatus[status.upper()])
    
    # Get OPD visits
    visits = db.query(OPDVisit).options(
        joinedload(OPDVisit.patient),
        joinedload(OPDVisit.appointment)
    ).filter(*filters).order_by(OPDVisit.visit_date.desc()).all()
    
    # Calculate statistics
    total_visits = len(visits)
    active_visits = len([v for v in visits if v.status == OPDVisitStatus.ACTIVE])
    completed_visits = len([v for v in visits if v.status == OPDVisitStatus.COMPLETED])
    
    # Calculate revenue from charges linked to OPD visits
    total_revenue = Decimal('0.00')
    for visit in visits:
        # Get charges linked to this OPD visit
        charges = db.query(Charge).filter(
            Charge.opd_visit_id == visit.id
        ).all()
        total_revenue += sum([c.total_amount for c in charges])
    
    # Breakdown by visit type
    visit_type_breakdown = {}
    for visit in visits:
        vt = visit.visit_type or "unknown"
        visit_type_breakdown[vt] = visit_type_breakdown.get(vt, 0) + 1
    
    # Breakdown by payment status (with revenue)
    payment_breakdown = {}
    payment_status_breakdown = {}
    for visit in visits:
        ps = visit.payment_status or "unknown"
        payment_status_breakdown[ps] = payment_status_breakdown.get(ps, 0) + 1
        
        # Calculate revenue for this payment status
        if ps not in payment_breakdown:
            payment_breakdown[ps] = {"count": 0, "total": Decimal('0.00')}
        payment_breakdown[ps]["count"] += 1
        
        # Get charges for this visit
        visit_charges = db.query(Charge).filter(
            Charge.opd_visit_id == visit.id
        ).all()
        visit_revenue = sum([c.total_amount for c in visit_charges])
        payment_breakdown[ps]["total"] += visit_revenue

    # New vs Revisit: consultation revenue by visit type
    # follow_up = Revisit; routine, walk_in, emergency = New
    new_consultation_revenue = Decimal('0.00')
    revisit_consultation_revenue = Decimal('0.00')
    new_visit_count = 0
    revisit_visit_count = 0
    for visit in visits:
        consult_charges = db.query(Charge).filter(
            Charge.opd_visit_id == visit.id,
            Charge.charge_type == ChargeType.CONSULTATION
        ).all()
        consult_total = sum([c.total_amount for c in consult_charges])
        vt = (visit.visit_type or "").lower()
        if vt == "follow_up":
            revisit_consultation_revenue += consult_total
            revisit_visit_count += 1
        else:
            new_consultation_revenue += consult_total
            new_visit_count += 1

    consultation_breakdown = {
        "new": {"count": new_visit_count, "revenue": new_consultation_revenue},
        "revisit": {"count": revisit_visit_count, "revenue": revisit_consultation_revenue},
    }
    
    # Patient Demographics - Age and Gender Distribution
    patient_ids = list(set([v.patient_id for v in visits if v.patient_id]))
    patients = db.query(Patient).filter(Patient.id.in_(patient_ids)).all()
    
    # Gender breakdown
    gender_breakdown = {}
    for patient in patients:
        gender = patient.gender or "Unknown"
        gender_breakdown[gender] = gender_breakdown.get(gender, 0) + 1
    
    # Age groups
    from app.utils.patient_utils import calculate_age
    age_groups = {
        "0-5": 0,
        "6-12": 0,
        "13-18": 0,
        "19-35": 0,
        "36-50": 0,
        "51-65": 0,
        "65+": 0
    }
    
    for patient in patients:
        if not patient.date_of_birth:
            continue
        age_data = calculate_age(patient.date_of_birth)
        age = age_data.get("years", 0)
        if age <= 5:
            age_groups["0-5"] += 1
        elif age <= 12:
            age_groups["6-12"] += 1
        elif age <= 18:
            age_groups["13-18"] += 1
        elif age <= 35:
            age_groups["19-35"] += 1
        elif age <= 50:
            age_groups["36-50"] += 1
        elif age <= 65:
            age_groups["51-65"] += 1
        else:
            age_groups["65+"] += 1
    
    # Get hospital settings
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": "OPD Detailed Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "status": status,
        "visits": visits,
        "total_visits": total_visits,
        "active_visits": active_visits,
        "completed_visits": completed_visits,
        "total_revenue": total_revenue,
        "visit_type_breakdown": visit_type_breakdown,
        "payment_status_breakdown": payment_status_breakdown,
        "payment_breakdown": payment_breakdown,
        "consultation_breakdown": consultation_breakdown,
        "gender_breakdown": gender_breakdown,
        "age_groups": age_groups,
        "hospital_settings": hospital_settings,
        "report_date": datetime.now()
    }
    
    # Handle different formats
    if format == "pdf":
        from app.utils.pdf_generator import generate_opd_report_pdf
        pdf_content = generate_opd_report_pdf(context)
        filename_safe = f"opd_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.pdf"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename_safe}"}
        )
    elif format == "excel":
        from app.utils.excel_generator import generate_opd_report_excel
        excel_content = generate_opd_report_excel(context)
        filename_safe = f"opd_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.xlsx"
        return Response(
            content=excel_content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename_safe}"}
        )
    elif format == "csv":
        from app.utils.csv_generator import generate_opd_report_csv
        csv_content = generate_opd_report_csv(context)
        filename_safe = f"opd_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename_safe}"}
        )
    
    return templates.TemplateResponse("reports/opd_detailed_report.html", context)


@router.get("/ipd/detailed", name="ipd_detailed_report")
def ipd_detailed_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    format: str = Query("html", regex="^(html|pdf|excel|csv)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Nurse", "Management", "Finance"]))
):
    """Generate detailed IPD report with admission statistics, revenue, and demographics."""
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today() - timedelta(days=30)  # Default: last 30 days
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Build query filters
    filters = [
        Admission.is_active == True,
        func.date(Admission.admission_date) >= start,
        func.date(Admission.admission_date) <= end
    ]
    
    if status:
        try:
            status_enum = AdmissionStatus[status.upper()]
            filters.append(Admission.status == status_enum)
        except KeyError:
            pass  # Invalid status, ignore
    
    # Get admissions
    admissions = db.query(Admission).options(
        joinedload(Admission.patient),
        joinedload(Admission.ward),
        joinedload(Admission.bed),
        joinedload(Admission.invoice)
    ).filter(*filters).order_by(Admission.admission_date.desc()).all()
    
    # Calculate statistics
    total_admissions = len(admissions)
    active_admissions = len([a for a in admissions if a.status == AdmissionStatus.ADMITTED])
    discharged_admissions = len([a for a in admissions if a.status == AdmissionStatus.DISCHARGED])
    transferred_admissions = len([a for a in admissions if a.status == AdmissionStatus.TRANSFERRED])
    
    # Calculate length of stay statistics
    los_list = []
    total_los = 0
    for admission in admissions:
        # Convert datetime to date if needed
        admission_date = admission.admission_date.date() if isinstance(admission.admission_date, datetime) else admission.admission_date
        if admission.discharge_date:
            discharge_date = admission.discharge_date.date() if isinstance(admission.discharge_date, datetime) else admission.discharge_date
            los = (discharge_date - admission_date).days
        else:
            los = (date.today() - admission_date).days
        los_list.append(los)
        total_los += los
    
    avg_los = total_los / total_admissions if total_admissions > 0 else 0
    
    # Financial statistics
    total_revenue = sum([a.invoice.total_amount if a.invoice else Decimal('0.00') for a in admissions])
    total_encounters = sum([len(a.encounters) for a in admissions])
    
    # Breakdown by ward
    ward_breakdown = {}
    for admission in admissions:
        ward_name = admission.ward.name if admission.ward else "Unknown"
        if ward_name not in ward_breakdown:
            ward_breakdown[ward_name] = {"count": 0, "total_los": 0}
        ward_breakdown[ward_name]["count"] += 1
        # Convert datetime to date if needed
        admission_date = admission.admission_date.date() if isinstance(admission.admission_date, datetime) else admission.admission_date
        if admission.discharge_date:
            discharge_date = admission.discharge_date.date() if isinstance(admission.discharge_date, datetime) else admission.discharge_date
            los = (discharge_date - admission_date).days
        else:
            los = (date.today() - admission_date).days
        ward_breakdown[ward_name]["total_los"] += los
    
    # Breakdown by discharge status
    discharge_status_breakdown = {}
    for admission in admissions:
        if admission.discharge_status:
            ds = admission.discharge_status.value
            if ds not in discharge_status_breakdown:
                discharge_status_breakdown[ds] = 0
            discharge_status_breakdown[ds] += 1
    
    # Calculate LOS for each admission (for template display)
    admission_los = {}
    today = date.today()
    for admission in admissions:
        # Convert datetime to date if needed
        admission_date = admission.admission_date.date() if isinstance(admission.admission_date, datetime) else admission.admission_date
        if admission.discharge_date:
            discharge_date = admission.discharge_date.date() if isinstance(admission.discharge_date, datetime) else admission.discharge_date
            los = (discharge_date - admission_date).days
        else:
            los = (today - admission_date).days
        admission_los[admission.id] = los
    
    # Patient Demographics - Age and Gender Distribution
    patient_ids = list(set([a.patient_id for a in admissions if a.patient_id]))
    patients = db.query(Patient).filter(Patient.id.in_(patient_ids)).all()
    
    # Gender breakdown
    gender_breakdown = {}
    for patient in patients:
        gender = patient.gender or "Unknown"
        gender_breakdown[gender] = gender_breakdown.get(gender, 0) + 1
    
    # Age groups
    from app.utils.patient_utils import calculate_age
    age_groups = {
        "0-5": 0,
        "6-12": 0,
        "13-18": 0,
        "19-35": 0,
        "36-50": 0,
        "51-65": 0,
        "65+": 0
    }
    
    for patient in patients:
        if not patient.date_of_birth:
            continue
        age_data = calculate_age(patient.date_of_birth)
        age = age_data.get("years", 0)
        if age <= 5:
            age_groups["0-5"] += 1
        elif age <= 12:
            age_groups["6-12"] += 1
        elif age <= 18:
            age_groups["13-18"] += 1
        elif age <= 35:
            age_groups["19-35"] += 1
        elif age <= 50:
            age_groups["36-50"] += 1
        elif age <= 65:
            age_groups["51-65"] += 1
        else:
            age_groups["65+"] += 1
    
    # Get hospital settings
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": "IPD Detailed Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "status": status,
        "admissions": admissions,
        "admission_los": admission_los,
        "total_admissions": total_admissions,
        "active_admissions": active_admissions,
        "discharged_admissions": discharged_admissions,
        "transferred_admissions": transferred_admissions,
        "total_revenue": total_revenue,
        "total_encounters": total_encounters,
        "avg_los": avg_los,
        "los_list": los_list,
        "ward_breakdown": ward_breakdown,
        "discharge_status_breakdown": discharge_status_breakdown,
        "gender_breakdown": gender_breakdown,
        "age_groups": age_groups,
        "hospital_settings": hospital_settings,
        "report_date": datetime.now()
    }
    
    # Handle different formats
    if format == "pdf":
        from app.utils.pdf_generator import generate_ipd_report_pdf
        pdf_content = generate_ipd_report_pdf(context)
        filename_safe = f"ipd_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.pdf"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename_safe}"}
        )
    elif format == "excel":
        from app.utils.excel_generator import generate_ipd_report_excel
        excel_content = generate_ipd_report_excel(context)
        filename_safe = f"ipd_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.xlsx"
        return Response(
            content=excel_content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename_safe}"}
        )
    elif format == "csv":
        from app.utils.csv_generator import generate_ipd_report_csv
        csv_content = generate_ipd_report_csv(context)
        filename_safe = f"ipd_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename_safe}"}
        )
    
    return templates.TemplateResponse("reports/ipd_detailed_report.html", context)


# New Reports - Pharmacy, Lab, Radiology, Procedure, IPD, Disease

@router.get("/reports/pharmacy", name="pharmacy_report")
def pharmacy_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: str = Query("html", regex="^(html|pdf|excel)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Management", "Pharmacy Staff"]))
):
    """Generate pharmacy report with revenue and frequently prescribed medications."""
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today() - timedelta(days=30)
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Get pharmacy charges (charges with charge_type = PHARMACY)
    charges = db.query(Charge).join(Invoice).filter(
        Charge.charge_type == ChargeType.PHARMACY,
        Invoice.is_active == True,
        func.date(Invoice.invoice_date) >= start,
        func.date(Invoice.invoice_date) <= end
    ).all()
    
    # Calculate total revenue
    total_revenue = sum([c.total_amount for c in charges])
    
    # Calculate actual profit from PharmacyDispenseItem records (Ghana FEFO system)
    total_cost = Decimal('0.00')
    total_profit = Decimal('0.00')
    
    # Get dispense items from Ghana pharmacy system in date range
    dispense_items = db.query(PharmacyDispenseItem).join(
        PharmacyDispense
    ).filter(
        func.date(PharmacyDispense.dispensed_at) >= start,
        func.date(PharmacyDispense.dispensed_at) <= end,
        PharmacyDispense.status == "DISPENSED"
    ).all()
    
    for item in dispense_items:
        item_cost = (item.unit_cost_snapshot or 0) * item.qty_dispensed
        total_cost += item_cost
        item_profit = (item.total_amount or 0) - item_cost
        total_profit += item_profit
    
    # Calculate profit margin
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0.00')
    
    # Get prescriptions in date range with encounter relationships
    prescriptions = db.query(Prescription).options(
        joinedload(Prescription.encounter)
    ).filter(
        func.date(Prescription.prescribed_at) >= start,
        func.date(Prescription.prescribed_at) <= end
    ).all()
    
    # Count frequently prescribed medications
    medication_counts = {}
    for prescription in prescriptions:
        med_name = prescription.medication_name
        if med_name:
            medication_counts[med_name] = medication_counts.get(med_name, 0) + 1
    
    # Sort by count and get top 20
    top_medications = sorted(medication_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    
    # Revenue by medication
    medication_revenue = {}
    for charge in charges:
        # Try to find prescription linked to this charge
        prescription = db.query(Prescription).filter(
            Prescription.id == charge.prescription_id
        ).first()
        
        if prescription:
            med_name = prescription.medication_name
            if med_name:
                if med_name not in medication_revenue:
                    medication_revenue[med_name] = Decimal('0.00')
                medication_revenue[med_name] += charge.total_amount
    
    # Patient Demographics - Age and Gender Distribution
    patient_ids = set()
    for prescription in prescriptions:
        if prescription.encounter and prescription.encounter.patient_id:
            patient_ids.add(prescription.encounter.patient_id)
    
    patients = db.query(Patient).filter(Patient.id.in_(list(patient_ids))).all() if patient_ids else []
    
    # Gender breakdown
    gender_breakdown = {}
    for patient in patients:
        gender = patient.gender or "Unknown"
        gender_breakdown[gender] = gender_breakdown.get(gender, 0) + 1
    
    # Age groups
    from app.utils.patient_utils import calculate_age
    age_groups = {
        "0-5": 0, "6-12": 0, "13-18": 0, "19-35": 0,
        "36-50": 0, "51-65": 0, "65+": 0
    }
    
    for patient in patients:
        if not patient.date_of_birth:
            continue
        age_data = calculate_age(patient.date_of_birth)
        age = age_data.get("years", 0)
        if age <= 5:
            age_groups["0-5"] += 1
        elif age <= 12:
            age_groups["6-12"] += 1
        elif age <= 18:
            age_groups["13-18"] += 1
        elif age <= 35:
            age_groups["19-35"] += 1
        elif age <= 50:
            age_groups["36-50"] += 1
        elif age <= 65:
            age_groups["51-65"] += 1
        else:
            age_groups["65+"] += 1
    
    # Get hospital settings
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": "Pharmacy Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "total_revenue": total_revenue,
        "total_prescriptions": len(prescriptions),
        "top_medications": top_medications,
        "medication_revenue": medication_revenue,
        "gender_breakdown": gender_breakdown,
        "age_groups": age_groups,
        "hospital_settings": hospital_settings,
        "report_date": datetime.now(),
        # Profit metrics from actual costs (Ghana FEFO system)
        "total_cost": total_cost,
        "total_profit": total_profit,
        "profit_margin": profit_margin
    }
    
    if format == "pdf":
        from app.utils.pdf_generator import generate_pharmacy_report_pdf
        pdf_content = generate_pharmacy_report_pdf(context)
        filename_safe = f"pharmacy_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.pdf"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename_safe}"
            }
        )
    elif format == "excel":
        from app.utils.excel_generator import generate_pharmacy_report_excel
        excel_content = generate_pharmacy_report_excel(context)
        filename_safe = f"pharmacy_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.xlsx"
        return Response(
            content=excel_content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename_safe}"
            }
        )
    
    return templates.TemplateResponse("reports/pharmacy_report.html", context)


@router.get("/reports/lab", name="lab_report")
def lab_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: str = Query("html", regex="^(html|pdf|excel)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Management", "Lab Staff"]))
):
    """Generate lab report with revenue."""
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today() - timedelta(days=30)
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Get lab charges
    charges = db.query(Charge).join(Invoice).filter(
        Charge.charge_type == ChargeType.LAB_TEST,
        Invoice.is_active == True,
        func.date(Invoice.invoice_date) >= start,
        func.date(Invoice.invoice_date) <= end
    ).all()
    
    # Calculate total revenue
    total_revenue = sum([c.total_amount for c in charges])
    
    # Get lab orders in date range with encounter relationships
    lab_orders = db.query(LabOrder).options(
        joinedload(LabOrder.encounter)
    ).filter(
        func.date(LabOrder.ordered_at) >= start,
        func.date(LabOrder.ordered_at) <= end
    ).all()
    
    # Count tests by name
    test_counts = {}
    for order in lab_orders:
        test_name = order.test_name
        if test_name:
            test_counts[test_name] = test_counts.get(test_name, 0) + 1
    
    # Revenue by test
    test_revenue = {}
    for charge in charges:
        lab_order = db.query(LabOrder).filter(
            LabOrder.id == charge.lab_order_id
        ).first()
        
        if lab_order:
            test_name = lab_order.test_name
            if test_name:
                if test_name not in test_revenue:
                    test_revenue[test_name] = Decimal('0.00')
                test_revenue[test_name] += charge.total_amount
    
    # Patient Demographics - Age and Gender Distribution
    patient_ids = set()
    for order in lab_orders:
        if order.encounter and order.encounter.patient_id:
            patient_ids.add(order.encounter.patient_id)
    
    patients = db.query(Patient).filter(Patient.id.in_(list(patient_ids))).all() if patient_ids else []
    
    # Gender breakdown
    gender_breakdown = {}
    for patient in patients:
        gender = patient.gender or "Unknown"
        gender_breakdown[gender] = gender_breakdown.get(gender, 0) + 1
    
    # Age groups
    from app.utils.patient_utils import calculate_age
    age_groups = {
        "0-5": 0, "6-12": 0, "13-18": 0, "19-35": 0,
        "36-50": 0, "51-65": 0, "65+": 0
    }
    
    for patient in patients:
        if not patient.date_of_birth:
            continue
        age_data = calculate_age(patient.date_of_birth)
        age = age_data.get("years", 0)
        if age <= 5:
            age_groups["0-5"] += 1
        elif age <= 12:
            age_groups["6-12"] += 1
        elif age <= 18:
            age_groups["13-18"] += 1
        elif age <= 35:
            age_groups["19-35"] += 1
        elif age <= 50:
            age_groups["36-50"] += 1
        elif age <= 65:
            age_groups["51-65"] += 1
        else:
            age_groups["65+"] += 1
    
    # Get hospital settings
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": "Lab Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "total_revenue": total_revenue,
        "total_orders": len(lab_orders),
        "test_counts": test_counts,
        "test_revenue": test_revenue,
        "gender_breakdown": gender_breakdown,
        "age_groups": age_groups,
        "hospital_settings": hospital_settings,
        "report_date": datetime.now()
    }
    
    if format == "pdf":
        from app.utils.pdf_generator import generate_lab_report_pdf
        pdf_content = generate_lab_report_pdf(context)
        filename_safe = f"lab_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.pdf"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename_safe}"
            }
        )
    elif format == "excel":
        from app.utils.excel_generator import generate_lab_report_excel
        excel_content = generate_lab_report_excel(context)
        filename_safe = f"lab_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.xlsx"
        return Response(
            content=excel_content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename_safe}"
            }
        )
    
    return templates.TemplateResponse("reports/lab_report.html", context)


@router.get("/reports/radiology", name="radiology_report")
def radiology_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: str = Query("html", regex="^(html|pdf|excel)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Management", "Radiology Staff"]))
):
    """Generate radiology report with revenue."""
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today() - timedelta(days=30)
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Get radiology charges
    charges = db.query(Charge).join(Invoice).filter(
        Charge.charge_type == ChargeType.RADIOLOGY,
        Invoice.is_active == True,
        func.date(Invoice.invoice_date) >= start,
        func.date(Invoice.invoice_date) <= end
    ).all()
    
    # Calculate total revenue
    total_revenue = sum([c.total_amount for c in charges])
    
    # Get radiology orders in date range with encounter relationships
    radiology_orders = db.query(RadiologyOrder).options(
        joinedload(RadiologyOrder.encounter)
    ).filter(
        func.date(RadiologyOrder.ordered_at) >= start,
        func.date(RadiologyOrder.ordered_at) <= end
    ).all()
    
    # Count studies by type
    study_counts = {}
    for order in radiology_orders:
        study_type = order.study_type
        if study_type:
            study_counts[study_type] = study_counts.get(study_type, 0) + 1
    
    # Revenue by study type
    study_revenue = {}
    for charge in charges:
        radiology_order = db.query(RadiologyOrder).filter(
            RadiologyOrder.id == charge.radiology_order_id
        ).first()
        
        if radiology_order:
            study_type = radiology_order.study_type
            if study_type:
                if study_type not in study_revenue:
                    study_revenue[study_type] = Decimal('0.00')
                study_revenue[study_type] += charge.total_amount
    
    # Patient Demographics - Age and Gender Distribution
    patient_ids = set()
    for order in radiology_orders:
        if order.encounter and order.encounter.patient_id:
            patient_ids.add(order.encounter.patient_id)
    
    patients = db.query(Patient).filter(Patient.id.in_(list(patient_ids))).all() if patient_ids else []
    
    # Gender breakdown
    gender_breakdown = {}
    for patient in patients:
        gender = patient.gender or "Unknown"
        gender_breakdown[gender] = gender_breakdown.get(gender, 0) + 1
    
    # Age groups
    from app.utils.patient_utils import calculate_age
    age_groups = {
        "0-5": 0, "6-12": 0, "13-18": 0, "19-35": 0,
        "36-50": 0, "51-65": 0, "65+": 0
    }
    
    for patient in patients:
        if not patient.date_of_birth:
            continue
        age_data = calculate_age(patient.date_of_birth)
        age = age_data.get("years", 0)
        if age <= 5:
            age_groups["0-5"] += 1
        elif age <= 12:
            age_groups["6-12"] += 1
        elif age <= 18:
            age_groups["13-18"] += 1
        elif age <= 35:
            age_groups["19-35"] += 1
        elif age <= 50:
            age_groups["36-50"] += 1
        elif age <= 65:
            age_groups["51-65"] += 1
        else:
            age_groups["65+"] += 1
    
    # Get hospital settings
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": "Radiology Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "total_revenue": total_revenue,
        "total_orders": len(radiology_orders),
        "study_counts": study_counts,
        "study_revenue": study_revenue,
        "gender_breakdown": gender_breakdown,
        "age_groups": age_groups,
        "hospital_settings": hospital_settings,
        "report_date": datetime.now()
    }
    
    if format == "pdf":
        from app.utils.pdf_generator import generate_radiology_report_pdf
        pdf_content = generate_radiology_report_pdf(context)
        filename_safe = f"radiology_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.pdf"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename_safe}"
            }
        )
    elif format == "excel":
        from app.utils.excel_generator import generate_radiology_report_excel
        excel_content = generate_radiology_report_excel(context)
        filename_safe = f"radiology_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.xlsx"
        return Response(
            content=excel_content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename_safe}"
            }
        )
    
    return templates.TemplateResponse("reports/radiology_report.html", context)


@router.get("/procedures", name="procedure_report")
def procedure_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: str = Query("html", regex="^(html|pdf|excel)$"),
    procedure_type: Optional[str] = Query(None),
    procedure_category: Optional[str] = Query(None),
    report_format: str = Query("summary", regex="^(summary|detailed)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Management", "Doctor"]))
):
    """Generate comprehensive procedure report with gender, age, and type segregation."""
    from app.models.procedure_models import ProcedureType
    
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today() - timedelta(days=30)
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Parse procedure type
    proc_type_enum = None
    if procedure_type:
        try:
            proc_type_enum = ProcedureType(procedure_type)
        except ValueError:
            pass
    
    # Get comprehensive statistics
    statistics = procedure_reports_crud.get_procedure_statistics(
        db,
        start_date=start,
        end_date=end,
        procedure_type=proc_type_enum,
        procedure_category=procedure_category
    )
    
    # Get detailed report data if requested
    detailed_report = None
    if report_format == "detailed":
        detailed_report = procedure_reports_crud.get_procedure_report_by_gender_age_type(
            db,
            start_date=start,
            end_date=end
        )
    
    # Get procedure charges for revenue calculation
    charges = db.query(Charge).join(Invoice).filter(
        Charge.charge_type == ChargeType.PROCEDURE,
        Invoice.is_active == True,
        func.date(Invoice.invoice_date) >= start,
        func.date(Invoice.invoice_date) <= end
    ).all()
    
    # Calculate total revenue
    total_revenue = sum([c.total_amount for c in charges])
    
    # Revenue by procedure
    procedure_revenue = {}
    for charge in charges:
        # Try to match by description pattern
        if "Procedure #" in charge.description:
            # Extract procedure name from description
            proc_name = charge.description.split(":")[-1].strip() if ":" in charge.description else charge.description
            if proc_name:
                if proc_name not in procedure_revenue:
                    procedure_revenue[proc_name] = Decimal('0.00')
                procedure_revenue[proc_name] += charge.total_amount
    
    # Get hospital settings
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": "Procedure Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "procedure_type_filter": procedure_type,
        "procedure_category_filter": procedure_category,
        "report_format": report_format,
        "statistics": statistics,
        "detailed_report": detailed_report,
        "total_procedures": statistics.get("total_procedures", 0),
        "total_revenue": total_revenue,
        "procedure_revenue": procedure_revenue,
        "procedure_types": [pt.value for pt in ProcedureType],
        "hospital_settings": hospital_settings,
        "report_date": datetime.now()
    }
    
    if format == "pdf":
        # PDF generation (to be implemented)
        pass
    elif format == "excel":
        # Excel generation (to be implemented)
        pass
    
    return templates.TemplateResponse("reports/procedure_report.html", context)


@router.get("/ipd/comprehensive", name="ipd_comprehensive_report")
def ipd_comprehensive_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: str = Query("html", regex="^(html|pdf|excel)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Management", "Doctor"]))
):
    """Generate comprehensive IPD report with disease, financial, and demographics data."""
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today() - timedelta(days=30)
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Get discharged admissions - filter by discharge_date for morbidity reporting
    # Get discharged admissions - filter by discharge_date for morbidity reporting
    # Include any admission that has a discharge_date (regardless of status)
    admissions = db.query(Admission).options(
        joinedload(Admission.patient),
        joinedload(Admission.ward),
        joinedload(Admission.bed),
        joinedload(Admission.invoice),
        joinedload(Admission.encounters)
    ).filter(
        Admission.is_active == True,
        Admission.discharge_date.isnot(None),  # Must have been discharged
        func.date(Admission.discharge_date) >= start,  # Filter by discharge date
        func.date(Admission.discharge_date) <= end
    ).all()
    
    # Financial Report
    total_revenue = sum([a.invoice.total_amount if a.invoice else Decimal('0.00') for a in admissions])
    total_paid = sum([a.invoice.paid_amount if a.invoice else Decimal('0.00') for a in admissions])
    total_outstanding = total_revenue - total_paid
    
    # Helper function to match disease names
    def match_disease_by_name(disease_name: str, db_session):
        """
        Try to match a free-text disease name to an existing Disease record.
        Returns (disease_id, disease_name, disease_code) or (None, original_name, None) if no match.
        """
        if not disease_name or not disease_name.strip():
            return None, None, None
        
        # Clean up the disease name
        clean_name = disease_name.strip()
        
        # Try exact match first (case-insensitive)
        existing = db_session.query(Disease).filter(
            func.lower(Disease.name) == clean_name.lower()
        ).first()
        
        if existing:
            return existing.id, existing.name, existing.code
        
        # Try partial match (disease name contains the search term)
        existing = db_session.query(Disease).filter(
            Disease.name.ilike(f"%{clean_name}%")
        ).first()
        
        if existing:
            return existing.id, existing.name, existing.code
        
        # No match found - return None to indicate custom/unmatched diagnosis
        return None, clean_name, None
    
    # Disease Report - Get diseases from discharge_diagnosis (final diagnosis from discharge form)
    # This is the PRIMARY source for IPD morbidity reporting
    disease_counts = {}
    disease_revenue = {}
    
    # First, count diseases from discharge_diagnosis field (the final diagnosis)
    for admission in admissions:
        patient = admission.patient
        
        # Process discharge diagnosis - this is the FINAL diagnosis from discharge form
        if admission.discharge_diagnosis and admission.discharge_diagnosis.strip():
            # Split by comma to handle multiple diagnoses (e.g., "Malaria, Typhoid Fever")
            diagnosis_parts = [d.strip() for d in admission.discharge_diagnosis.split(',') if d.strip()]
            
            for diagnosis_text in diagnosis_parts:
                # Try to match to disease database
                disease_id, matched_name, code = match_disease_by_name(diagnosis_text, db)
                
                # Use matched name or original text
                disease_name = matched_name if matched_name else diagnosis_text
                
                disease_counts[disease_name] = disease_counts.get(disease_name, 0) + 1
                
                # Calculate revenue for this disease (from admission invoice)
                if admission.invoice:
                    if disease_name not in disease_revenue:
                        disease_revenue[disease_name] = Decimal('0.00')
                    disease_revenue[disease_name] += admission.invoice.total_amount / max(len(diagnosis_parts), 1)
    
    # Also include diseases from encounter_diseases table as supplementary data
    for admission in admissions:
        for encounter in admission.encounters:
            # Get diseases from encounter
            encounter_diseases = db.query(EncounterDisease).filter(
                EncounterDisease.encounter_id == encounter.id
            ).all()
            
            for enc_disease in encounter_diseases:
                disease = db.query(Disease).filter(Disease.id == enc_disease.disease_id).first()
                if disease:
                    disease_name = disease.name
                    # Add to counts (could be duplicate with discharge_diagnosis, but that's acceptable for now)
                    disease_counts[disease_name] = disease_counts.get(disease_name, 0) + 1
                    
                    # Calculate revenue for this disease (from admission invoice)
                    if admission.invoice:
                        if disease_name not in disease_revenue:
                            disease_revenue[disease_name] = Decimal('0.00')
                        # Distribute revenue proportionally (simplified)
                        disease_revenue[disease_name] += admission.invoice.total_amount / max(len(encounter_diseases), 1)
            
            # Also check primary diagnosis from encounter (as supplementary)
            if encounter.primary_diagnosis_description:
                diag = encounter.primary_diagnosis_description
                disease_counts[diag] = disease_counts.get(diag, 0) + 1
                if admission.invoice:
                    if diag not in disease_revenue:
                        disease_revenue[diag] = Decimal('0.00')
                    disease_revenue[diag] += admission.invoice.total_amount
    
    # Patient Demographics
    patient_ids = list(set([a.patient_id for a in admissions]))
    patients = db.query(Patient).filter(Patient.id.in_(patient_ids)).all()
    
    # Gender breakdown
    gender_breakdown = {}
    for patient in patients:
        gender = patient.gender or "Unknown"
        gender_breakdown[gender] = gender_breakdown.get(gender, 0) + 1
    
    # Age groups
    from app.utils.patient_utils import calculate_age
    age_groups = {
        "0-5": 0, "6-12": 0, "13-18": 0, "19-35": 0,
        "36-50": 0, "51-65": 0, "65+": 0
    }
    
    for patient in patients:
        if not patient.date_of_birth:
            continue
        age_data = calculate_age(patient.date_of_birth)
        age = age_data.get("years", 0)  # Extract years from the dictionary
        if age <= 5:
            age_groups["0-5"] += 1
        elif age <= 12:
            age_groups["6-12"] += 1
        elif age <= 18:
            age_groups["13-18"] += 1
        elif age <= 35:
            age_groups["19-35"] += 1
        elif age <= 50:
            age_groups["36-50"] += 1
        elif age <= 65:
            age_groups["51-65"] += 1
        else:
            age_groups["65+"] += 1
    
    # Top diseases
    top_diseases = sorted(disease_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    
    # Get hospital settings
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": "IPD Comprehensive Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "total_admissions": len(admissions),
        "total_revenue": total_revenue,
        "total_paid": total_paid,
        "total_outstanding": total_outstanding,
        "disease_counts": disease_counts,
        "disease_revenue": disease_revenue,
        "top_diseases": top_diseases,
        "gender_breakdown": gender_breakdown,
        "age_groups": age_groups,
        "hospital_settings": hospital_settings,
        "report_date": datetime.now()
    }
    
    if format == "pdf":
        # PDF generation (to be implemented)
        pass
    elif format == "excel":
        # Excel generation (to be implemented)
        pass
    
    return templates.TemplateResponse("reports/ipd_comprehensive_report.html", context)


@router.get("/diseases", name="disease_report")
def disease_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: str = Query("html", regex="^(html|pdf|excel)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Management", "Doctor"]))
):
    """Generate disease report based on diseases form/database."""
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today() - timedelta(days=365)  # Default: last year
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Get all encounters in date range
    encounters = db.query(Encounter).filter(
        Encounter.is_active == True,
        func.date(Encounter.encounter_date) >= start,
        func.date(Encounter.encounter_date) <= end
    ).all()
    
    # Count diseases from encounter_diseases table
    disease_counts = {}
    disease_patients = {}  # Track unique patients per disease
    
    for encounter in encounters:
        # Get diseases linked to this encounter
        encounter_diseases = db.query(EncounterDisease).filter(
            EncounterDisease.encounter_id == encounter.id
        ).all()
        
        for enc_disease in encounter_diseases:
            disease = db.query(Disease).filter(Disease.id == enc_disease.disease_id).first()
            if disease:
                disease_name = disease.name
                disease_counts[disease_name] = disease_counts.get(disease_name, 0) + 1
                
                # Track unique patients
                if disease_name not in disease_patients:
                    disease_patients[disease_name] = set()
                disease_patients[disease_name].add(encounter.patient_id)
        
        # Also count primary diagnosis
        if encounter.primary_diagnosis_description:
            diag = encounter.primary_diagnosis_description
            disease_counts[diag] = disease_counts.get(diag, 0) + 1
            if diag not in disease_patients:
                disease_patients[diag] = set()
            disease_patients[diag].add(encounter.patient_id)
    
    # Convert patient sets to counts
    disease_patient_counts = {k: len(v) for k, v in disease_patients.items()}
    
    # Sort by count
    top_diseases = sorted(disease_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Patient Demographics - Age and Gender Distribution
    patient_ids = list(set([e.patient_id for e in encounters if e.patient_id]))
    patients = db.query(Patient).filter(Patient.id.in_(patient_ids)).all()
    
    # Gender breakdown
    gender_breakdown = {}
    for patient in patients:
        gender = patient.gender or "Unknown"
        gender_breakdown[gender] = gender_breakdown.get(gender, 0) + 1
    
    # Age groups
    from app.utils.patient_utils import calculate_age
    age_groups = {
        "0-5": 0,
        "6-12": 0,
        "13-18": 0,
        "19-35": 0,
        "36-50": 0,
        "51-65": 0,
        "65+": 0
    }
    
    for patient in patients:
        if not patient.date_of_birth:
            continue
        age_data = calculate_age(patient.date_of_birth)
        age = age_data.get("years", 0)
        if age <= 5:
            age_groups["0-5"] += 1
        elif age <= 12:
            age_groups["6-12"] += 1
        elif age <= 18:
            age_groups["13-18"] += 1
        elif age <= 35:
            age_groups["19-35"] += 1
        elif age <= 50:
            age_groups["36-50"] += 1
        elif age <= 65:
            age_groups["51-65"] += 1
        else:
            age_groups["65+"] += 1
    
    # Get all diseases from database for reference
    all_diseases = db.query(Disease).filter(Disease.is_active == True).all()
    
    # Get hospital settings
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": "Disease Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "disease_counts": disease_counts,
        "disease_patient_counts": disease_patient_counts,
        "top_diseases": top_diseases,
        "all_diseases": all_diseases,
        "total_encounters": len(encounters),
        "gender_breakdown": gender_breakdown,
        "age_groups": age_groups,
        "hospital_settings": hospital_settings,
        "report_date": datetime.now()
    }
    
    if format == "pdf":
        from app.utils.pdf_generator import generate_disease_report_pdf
        # Update context for PDF generator (it expects different structure)
        pdf_context = {
            "filters": {
                "start_date": start,
                "end_date": end
            },
            "totals": {
                "encounters": len(encounters),
                "primary": sum([1 for e in encounters if e.primary_diagnosis_description]),
                "diseases": len(disease_counts)
            },
            "stats": [
                {
                    "name": disease,
                    "code": "",
                    "encounter_count": count,
                    "primary_count": 0,
                    "primary_ratio": 0.0,
                    "first_recorded": None,
                    "last_recorded": None
                }
                for disease, count in top_diseases[:50]
            ],
            "gender_breakdown": gender_breakdown,
            "age_groups": age_groups,
            "report_date": datetime.now()
        }
        pdf_content = generate_disease_report_pdf(pdf_context)
        filename_safe = f"disease_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.pdf"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename_safe}"
            }
        )
    elif format == "excel":
        from app.utils.excel_generator import generate_disease_report_excel
        excel_content = generate_disease_report_excel(context)
        filename_safe = f"disease_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.xlsx"
        return Response(
            content=excel_content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename_safe}"
            }
        )
    
    return templates.TemplateResponse("reports/disease_report.html", context)


@router.get("/doctor", name="doctor_report")
def doctor_report(
    request: Request,
    doctor_id: Optional[int] = Query(None, description="Doctor/Clinician ID"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: str = Query("html", regex="^(html|pdf|excel)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Management", "Doctor"]))
):
    """
    Doctor Report: How many patients a doctor saw within a period, and calculated payment.
    Payment = consultation_fee × patient_count (e.g. 300 cedis × 5 patients = 1,500 cedis).
    """
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today() - timedelta(days=30)

    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()

    # Get doctors and clinicians (users who can document encounters)
    doctor_role = db.query(Role).filter(Role.name == "Doctor").first()
    clinician_role = db.query(Role).filter(Role.name == "Clinician").first()
    doctor_ids = []
    if doctor_role:
        doctor_ids.extend([u.id for u in db.query(User).filter(User.role_id == doctor_role.id, User.is_active == True).all()])
    if clinician_role:
        doctor_ids.extend([u.id for u in db.query(User).filter(User.role_id == clinician_role.id, User.is_active == True).all()])
    doctor_ids = list(set(doctor_ids))

    clinicians = db.query(User).options(joinedload(User.role)).filter(
        User.id.in_(doctor_ids),
        User.is_active == True
    ).order_by(User.full_name.asc()).all()

    # Get consultation fee from service pricing
    consultation_fee = service_pricing_crud.get_default_price_for_service(db, "Consultation", "consultation")
    if consultation_fee is None:
        consultation_fee = DEFAULT_CONSULTATION_FEE

    report_data = None
    selected_doctor = None

    if doctor_id:
        selected_doctor = db.query(User).options(joinedload(User.role)).filter(User.id == doctor_id).first()
        if selected_doctor:
            # Count encounters by this clinician (exclude cancelled)
            encounter_count = db.query(func.count(Encounter.id)).filter(
                Encounter.clinician_id == doctor_id,
                Encounter.is_active == True,
                Encounter.status != EncounterStatus.CANCELLED,
                func.date(Encounter.encounter_date) >= start,
                func.date(Encounter.encounter_date) <= end
            ).scalar() or 0

            total_amount = consultation_fee * encounter_count

            report_data = {
                "doctor": selected_doctor,
                "patient_count": encounter_count,
                "consultation_fee": consultation_fee,
                "total_amount": total_amount,
                "encounters": db.query(Encounter)
                    .options(
                        joinedload(Encounter.patient),
                        joinedload(Encounter.clinician)
                    )
                    .filter(
                        Encounter.clinician_id == doctor_id,
                        Encounter.is_active == True,
                        Encounter.status != EncounterStatus.CANCELLED,
                        func.date(Encounter.encounter_date) >= start,
                        func.date(Encounter.encounter_date) <= end
                    )
                    .order_by(Encounter.encounter_date.desc())
                    .limit(100)
                    .all()
            }

    context = {
        "request": request,
        "title": "Doctor Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "clinicians": clinicians,
        "doctor_id": doctor_id,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "consultation_fee": consultation_fee,
        "report_data": report_data,
        "selected_doctor": selected_doctor,
    }

    if format == "pdf" and report_data:
        try:
            from app.utils.pdf_generator import generate_doctor_report_pdf
            pdf_content = generate_doctor_report_pdf(context)
            doc_name = (selected_doctor.full_name or selected_doctor.username or "doctor").replace(" ", "_")
            filename_safe = f"doctor_report_{doc_name}_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.pdf"
            return Response(
                content=pdf_content,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename_safe}"}
            )
        except (ImportError, AttributeError):
            pass  # Fall through to HTML
    elif format == "excel" and report_data:
        try:
            from app.utils.excel_generator import generate_doctor_report_excel
            excel_content = generate_doctor_report_excel(context)
            doc_name = (selected_doctor.full_name or selected_doctor.username or "doctor").replace(" ", "_")
            filename_safe = f"doctor_report_{doc_name}_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.xlsx"
            return Response(
                content=excel_content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename_safe}"}
            )
        except (ImportError, AttributeError):
            pass  # Fall through to HTML

    return templates.TemplateResponse("reports/doctor_report.html", context)


@router.get("/antenatal-births", name="antenatal_births_report")
def antenatal_births_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Management", "Doctor", "Midwife", "Nurse"]))
):
    """Antenatal visits and birth records report."""
    from app.models.antenatal_models import AntenatalVisit
    from app.models.birth_models import BirthRecord, BirthOutcome, DeliveryType

    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today() - timedelta(days=90)

    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()

    # Antenatal visits
    antenatal_visits = db.query(AntenatalVisit).filter(
        AntenatalVisit.is_active == True,
        func.date(AntenatalVisit.visit_date) >= start,
        func.date(AntenatalVisit.visit_date) <= end
    ).all()

    # Birth records
    birth_records = db.query(BirthRecord).filter(
        BirthRecord.is_active == True,
        BirthRecord.birth_date >= start,
        BirthRecord.birth_date <= end
    ).all()

    # ANC stats
    total_anc_visits = len(antenatal_visits)
    unique_patients_anc = len(set(v.patient_id for v in antenatal_visits))
    anc_by_month = {}
    for v in antenatal_visits:
        key = v.visit_date.strftime("%Y-%m") if v.visit_date else "unknown"
        anc_by_month[key] = anc_by_month.get(key, 0) + 1

    # Birth stats
    total_births = len(birth_records)
    live_births = len([b for b in birth_records if (b.birth_outcome or "").lower() == BirthOutcome.LIVE.value])
    stillbirths = len([b for b in birth_records if (b.birth_outcome or "").lower() == BirthOutcome.STILLBIRTH.value])
    delivery_type_breakdown = {}
    for b in birth_records:
        dt = (b.delivery_type or "unknown").replace("_", " ").title()
        delivery_type_breakdown[dt] = delivery_type_breakdown.get(dt, 0) + 1

    hospital_settings = hospital_settings_crud.get_hospital_settings(db)

    context = {
        "request": request,
        "title": "Antenatal & Births Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "total_anc_visits": total_anc_visits,
        "unique_patients_anc": unique_patients_anc,
        "anc_by_month": dict(sorted(anc_by_month.items())),
        "total_births": total_births,
        "live_births": live_births,
        "stillbirths": stillbirths,
        "delivery_type_breakdown": delivery_type_breakdown,
        "antenatal_visits": antenatal_visits[:200],
        "birth_records": birth_records[:200],
        "hospital_settings": hospital_settings,
        "report_date": datetime.now()
    }
    return templates.TemplateResponse("reports/antenatal_births_report.html", context)


@router.get("/appointments", name="appointment_report")
def appointment_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Management", "Front Office", "Doctor"]))
):
    """Appointment report: scheduled vs walk-in, no-shows."""
    from app.models.scheduled_appointment_models import ScheduledAppointment, AppointmentStatus, AppointmentType

    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today() - timedelta(days=30)

    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()

    appointments = db.query(ScheduledAppointment).options(
        joinedload(ScheduledAppointment.patient),
        joinedload(ScheduledAppointment.assigned_doctor)
    ).filter(
        ScheduledAppointment.is_active == True,
        func.date(ScheduledAppointment.scheduled_date) >= start,
        func.date(ScheduledAppointment.scheduled_date) <= end
    ).order_by(ScheduledAppointment.scheduled_date.desc()).all()

    def _status_val(a):
        return a.status.value if hasattr(a.status, "value") else str(a.status)

    def _type_val(a):
        return a.appointment_type.value if a.appointment_type and hasattr(a.appointment_type, "value") else str(a.appointment_type or "")

    total = len(appointments)
    walk_in_count = len([a for a in appointments if _type_val(a) == "walk_in"])
    scheduled_count = total - walk_in_count
    no_show_count = len([a for a in appointments if _status_val(a) == "no_show"])
    completed_count = len([a for a in appointments if _status_val(a) == "completed"])
    cancelled_count = len([a for a in appointments if _status_val(a) == "cancelled"])
    checked_in_count = len([a for a in appointments if _status_val(a) in ("checked_in", "in_progress")])

    by_status = {}
    for a in appointments:
        s = _status_val(a)
        by_status[s] = by_status.get(s, 0) + 1

    by_type = {}
    for a in appointments:
        t = _type_val(a)
        by_type[t] = by_type.get(t, 0) + 1

    by_department = {}
    for a in appointments:
        d = a.department or "Unspecified"
        by_department[d] = by_department.get(d, 0) + 1

    hospital_settings = hospital_settings_crud.get_hospital_settings(db)

    context = {
        "request": request,
        "title": "Appointment Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "total": total,
        "walk_in_count": walk_in_count,
        "scheduled_count": total - walk_in_count,
        "no_show_count": no_show_count,
        "completed_count": completed_count,
        "cancelled_count": cancelled_count,
        "checked_in_count": checked_in_count,
        "by_status": by_status,
        "by_type": by_type,
        "by_department": by_department,
        "appointments": appointments[:300],
        "hospital_settings": hospital_settings,
        "report_date": datetime.now()
    }
    return templates.TemplateResponse("reports/appointment_report.html", context)


# ==================== DHIMS2-STYLE REPORTS ====================

@router.get("/dhims/opd", name="dhims_opd_report")
def dhims_opd_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    format: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Nurse", "Front Office", "Management", "DHIMS2Preparer"]))
):
    """
    DHIMS2-style OPD Report for Ghana Health Service reporting.
    
    Includes:
    - Total OPD attendances
    - New cases vs revisits
    - Gender breakdown
    - Age group breakdown (Under 5, 5+)
    - Payment mechanism (NHIS, Cash)
    - Referrals in/out
    - Disease morbidity
    """
    from app.models.encounter_models import Encounter
    from app.models.disease_models import Disease, EncounterDisease
    
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today().replace(day=1)  # First day of current month
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Quick date filters
    period = request.query_params.get('period')
    if period:
        today = date.today()
        if period == 'this_month':
            start = today.replace(day=1)
            end = today
        elif period == 'last_month':
            first_day_this_month = today.replace(day=1)
            last_day_last_month = first_day_this_month - timedelta(days=1)
            start = last_day_last_month.replace(day=1)
            end = last_day_last_month
        elif period == 'this_quarter':
            quarter = (today.month - 1) // 3
            start = date(today.year, quarter * 3 + 1, 1)
            end = today
        elif period == 'this_year':
            start = date(today.year, 1, 1)
            end = today
    
    # Get all OPD visits in period
    visits = db.query(OPDVisit).options(
        joinedload(OPDVisit.patient)
    ).filter(
        OPDVisit.is_active == True,
        func.date(OPDVisit.visit_date) >= start,
        func.date(OPDVisit.visit_date) <= end
    ).all()
    
    total_visits = len(visits)
    
    # Get patient data for demographics
    patient_ids = list(set([v.patient_id for v in visits if v.patient_id]))
    patients = db.query(Patient).filter(Patient.id.in_(patient_ids)).all() if patient_ids else []
    patient_map = {p.id: p for p in patients}
    
    # Gender breakdown
    male_count = 0
    female_count = 0
    for visit in visits:
        patient = patient_map.get(visit.patient_id)
        if patient:
            if patient.gender == "male":
                male_count += 1
            elif patient.gender == "female":
                female_count += 1
    
    # Age groups - Under 5, 5+
    under_5_count = 0
    over_5_count = 0
    for patient in patients:
        if patient.date_of_birth:
            age = calculate_age(patient.date_of_birth)
            if age is not None:
                if age < 5:
                    under_5_count += 1
                else:
                    over_5_count += 1
    
    # New cases vs Revisits (based on visit_type)
    new_cases = 0
    revisits = 0
    for visit in visits:
        vt = (visit.visit_type or "").lower()
        if vt in ["follow_up", "revisit"]:
            revisits += 1
        else:
            new_cases += 1
    
    # Payment mechanism breakdown
    nhis_count = 0
    cash_count = 0
    for visit in visits:
        ps = (visit.payment_status or "").lower()
        if ps == "paid":
            # Check if NHIS - would need insurance info
            cash_count += 1
        elif ps in ["pending", "waived"]:
            cash_count += 1
    
    # Visit type breakdown
    emergency_count = 0
    routine_count = 0
    for visit in visits:
        vt = (visit.visit_type or "").lower()
        if vt == "emergency":
            emergency_count += 1
        else:
            routine_count += 1
    
    # Get encounters for diagnosis information
    encounter_count = db.query(Encounter).filter(
        Encounter.opd_visit_id.in_([v.id for v in visits])
    ).count() if visits else 0
    
    # === REFERRALS ===
    # Note: Referral tracking requires a Referral model which is not currently implemented
    # Setting placeholder values - can be extended when Referral model is added
    referrals_in = 0
    referrals_out = 0
    
    # === DISEASE MORBIDITY ===
    # Get diseases from encounters linked to OPD visits
    visit_ids = [v.id for v in visits]
    disease_counts = {}
    
    if visit_ids:
        # Query using the Disease relationship to get the name
        diseases = db.query(
            Disease.name,
            func.count(EncounterDisease.id).label('count')
        ).join(
            Disease, Disease.id == EncounterDisease.disease_id
        ).join(
            Encounter, Encounter.id == EncounterDisease.encounter_id
        ).filter(
            Encounter.opd_visit_id.in_(visit_ids)
        ).group_by(
            Disease.name
        ).all()
        
        for disease in diseases:
            if disease.name:
                disease_counts[disease.name] = disease.count
    
    # Top 10 diseases
    top_diseases = sorted(disease_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": "DHIMS2 OPD Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "period": period,
        "total_visits": total_visits,
        "male_count": male_count,
        "female_count": female_count,
        "under_5_count": under_5_count,
        "over_5_count": over_5_count,
        "new_cases": new_cases,
        "revisits": revisits,
        "emergency_count": emergency_count,
        "routine_count": routine_count,
        "nhis_count": nhis_count,
        "cash_count": cash_count,
        "encounter_count": encounter_count,
        "referrals_in": referrals_in,
        "referrals_out": referrals_out,
        "disease_counts": disease_counts,
        "top_diseases": top_diseases,
        "hospital_settings": hospital_settings,
        "report_date": datetime.now()
    }
    return templates.TemplateResponse("reports/dhims_opd_report.html", context)


@router.get("/dhims/ipd", name="dhims_ipd_report")
def dhims_ipd_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    format: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Nurse", "Management", "DHIMS2Preparer"]))
):
    """
    DHIMS2-style IPD Report for Ghana Health Service reporting.
    
    Includes:
    - Total admissions
    - Total discharges
    - Deaths (by timing)
    - Transfers
    - Bed occupancy
    - Average length of stay
    - Disease morbidity
    """
    from app.models.ipd_models import Admission, AdmissionStatus, DischargeStatus
    from app.models.encounter_models import Encounter
    from app.models.disease_models import Disease, EncounterDisease
    
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today().replace(day=1)
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Quick date filters
    period = request.query_params.get('period')
    if period:
        today = date.today()
        if period == 'this_month':
            start = today.replace(day=1)
            end = today
        elif period == 'last_month':
            first_day_this_month = today.replace(day=1)
            last_day_last_month = first_day_this_month - timedelta(days=1)
            start = last_day_last_month.replace(day=1)
            end = last_day_last_month
        elif period == 'this_quarter':
            quarter = (today.month - 1) // 3
            start = date(today.year, quarter * 3 + 1, 1)
            end = today
        elif period == 'this_year':
            start = date(today.year, 1, 1)
            end = today
    
    # Get all admissions in period
    admissions = db.query(Admission).options(
        joinedload(Admission.patient),
        joinedload(Admission.ward)
    ).filter(
        Admission.is_active == True,
        func.date(Admission.admission_date) >= start,
        func.date(Admission.admission_date) <= end
    ).all()
    
    total_admissions = len(admissions)
    
    # Discharge outcomes
    discharges_normal = 0
    discharges_death = 0
    discharges_transfer = 0
    discharges_absconded = 0
    
    for adm in admissions:
        if adm.status == AdmissionStatus.DISCHARGED:
            if adm.discharge_status == DischargeStatus.NORMAL:
                discharges_normal += 1
            elif adm.discharge_status == DischargeStatus.DEATH:
                discharges_death += 1
            elif adm.discharge_status == DischargeStatus.REFERRAL:
                discharges_transfer += 1
        elif adm.status == AdmissionStatus.ABSCONDED:
            discharges_absconded += 1
    
    total_discharges = discharges_normal + discharges_death + discharges_transfer + discharges_absconded
    
    # Deaths by timing (24h, 48h+)
    deaths_under_24h = 0
    deaths_24_48h = 0
    deaths_over_48h = 0
    
    for adm in admissions:
        if adm.discharge_status == DischargeStatus.DEATH and adm.discharge_date:
            if adm.admission_date and adm.discharge_date:
                hours = (adm.discharge_date - adm.admission_date).total_seconds() / 3600
                if hours < 24:
                    deaths_under_24h += 1
                elif hours < 48:
                    deaths_24_48h += 1
                else:
                    deaths_over_48h += 1
    
    # Current inpatients
    current_inpatients = len([a for a in admissions if a.status == AdmissionStatus.ADMITTED])
    
    # Average length of stay
    total_stay_days = 0
    stay_count = 0
    for adm in admissions:
        if adm.admission_date and adm.discharge_date:
            days = (adm.discharge_date - adm.admission_date).days
            if days > 0:
                total_stay_days += days
                stay_count += 1
    
    avg_length_stay = round(total_stay_days / stay_count, 1) if stay_count > 0 else 0
    
    # Ward breakdown
    ward_admissions = {}
    for adm in admissions:
        ward_name = adm.ward.name if adm.ward else "Unknown"
        ward_admissions[ward_name] = ward_admissions.get(ward_name, 0) + 1
    
    # Gender breakdown
    male_count = 0
    female_count = 0
    for adm in admissions:
        if adm.patient:
            if adm.patient.gender == "male":
                male_count += 1
            elif adm.patient.gender == "female":
                female_count += 1
    
    # === DISEASE MORBIDITY ===
    # Get diseases from encounters linked to IPD admissions
    admission_ids = [a.id for a in admissions]
    disease_counts = {}
    
    if admission_ids:
        # Query using the Disease relationship to get the name
        diseases = db.query(
            Disease.name,
            func.count(EncounterDisease.id).label('count')
        ).join(
            Disease, Disease.id == EncounterDisease.disease_id
        ).join(
            Encounter, Encounter.id == EncounterDisease.encounter_id
        ).filter(
            Encounter.admission_id.in_(admission_ids)
        ).group_by(
            Disease.name
        ).all()
        
        for disease in diseases:
            if disease.name:
                disease_counts[disease.name] = disease.count
    
    # Top 10 diseases
    top_diseases = sorted(disease_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": "DHIMS2 IPD Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "period": period,
        "total_admissions": total_admissions,
        "total_discharges": total_discharges,
        "discharges_normal": discharges_normal,
        "discharges_death": discharges_death,
        "discharges_transfer": discharges_transfer,
        "discharges_absconded": discharges_absconded,
        "deaths_under_24h": deaths_under_24h,
        "deaths_24_48h": deaths_24_48h,
        "deaths_over_48h": deaths_over_48h,
        "current_inpatients": current_inpatients,
        "avg_length_stay": avg_length_stay,
        "ward_admissions": ward_admissions,
        "male_count": male_count,
        "female_count": female_count,
        "disease_counts": disease_counts,
        "top_diseases": top_diseases,
        "hospital_settings": hospital_settings,
        "report_date": datetime.now()
    }
    return templates.TemplateResponse("reports/dhims_ipd_report.html", context)


@router.get("/dhims/lab", name="dhims_lab_report")
def dhims_lab_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    format: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Lab Staff", "Management", "DHIMS2Preparer"]))
):
    """
    DHIMS2-style Lab Report for Ghana Health Service reporting.
    
    Includes:
    - Total tests conducted
    - Tests by category (Hematology, Chemistry, Microbiology, etc.)
    - Tests by outcome (Normal, Abnormal, Critical)
    - Rejection rates
    """
    from app.models.lab_models import LabSample, SampleStatus
    from app.models.lab_catalog_models import LabTest
    
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today().replace(day=1)
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Quick date filters
    period = request.query_params.get('period')
    if period:
        today = date.today()
        if period == 'this_month':
            start = today.replace(day=1)
            end = today
        elif period == 'last_month':
            first_day_this_month = today.replace(day=1)
            last_day_last_month = first_day_this_month - timedelta(days=1)
            start = last_day_last_month.replace(day=1)
            end = last_day_last_month
        elif period == 'this_quarter':
            quarter = (today.month - 1) // 3
            start = date(today.year, quarter * 3 + 1, 1)
            end = today
        elif period == 'this_year':
            start = date(today.year, 1, 1)
            end = today
    
    # Get all lab samples in period
    samples = db.query(LabSample).options(
        joinedload(LabSample.lab_order)
    ).filter(
        LabSample.is_active == True,
        func.date(LabSample.created_at) >= start,
        func.date(LabSample.created_at) <= end
    ).all()
    
    total_samples = len(samples)
    
    # Status breakdown
    samples_collected = len([s for s in samples if s.status == SampleStatus.COLLECTED])
    samples_received = len([s for s in samples if s.status == SampleStatus.RECEIVED])
    samples_processing = len([s for s in samples if s.status == SampleStatus.PROCESSING])
    samples_completed = len([s for s in samples if s.status == SampleStatus.COMPLETED])
    samples_rejected = len([s for s in samples if s.status == SampleStatus.REJECTED])
    
    rejection_rate = round((samples_rejected / total_samples * 100), 1) if total_samples > 0 else 0
    
    # Sample type breakdown
    sample_type_breakdown = {}
    for sample in samples:
        st = sample.sample_type or "Unknown"
        sample_type_breakdown[st] = sample_type_breakdown.get(st, 0) + 1
    
    # Get lab orders for test information
    lab_orders = db.query(LabOrder).filter(
        func.date(LabOrder.created_at) >= start,
        func.date(LabOrder.created_at) <= end
    ).all() if start and end else []
    
    total_orders = len(lab_orders)
    
    # Test category breakdown (based on lab test catalog)
    test_categories = {}
    completed_orders = [o for o in lab_orders if o.status and o.status.value == "completed"]
    pending_orders = [o for o in lab_orders if o.status and o.status.value in ["pending", "approved"]]
    cancelled_orders = [o for o in lab_orders if o.status and o.status.value == "cancelled"]
    
    # Get unique tests performed
    test_count_by_name = {}
    for order in completed_orders:
        if order.lab_test:
            test_name = order.lab_test.test_name
            test_category = order.lab_test.test_category or "Other"
            test_count_by_name[test_name] = test_count_by_name.get(test_name, 0) + 1
            test_categories[test_category] = test_categories.get(test_category, 0) + 1
    
    # Top tests
    top_tests = sorted(test_count_by_name.items(), key=lambda x: x[1], reverse=True)[:10]
    
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": "DHIMS2 Lab Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "period": period,
        "total_samples": total_samples,
        "total_orders": total_orders,
        "samples_collected": samples_collected,
        "samples_received": samples_received,
        "samples_processing": samples_processing,
        "samples_completed": samples_completed,
        "samples_rejected": samples_rejected,
        "rejection_rate": rejection_rate,
        "sample_type_breakdown": sample_type_breakdown,
        "test_categories": test_categories,
        "completed_orders": len(completed_orders),
        "pending_orders": len(pending_orders),
        "cancelled_orders": len(cancelled_orders),
        "top_tests": top_tests,
        "hospital_settings": hospital_settings,
        "report_date": datetime.now()
    }
    return templates.TemplateResponse("reports/dhims_lab_report.html", context)


# Cache for MCH report data
from functools import lru_cache
from typing import Optional, Dict, Any
import json


def _get_mch_report_data(
    db: Session,
    start: date,
    end: date
) -> Dict[str, Any]:
    """
    Optimized MCH report data retrieval using database aggregations.
    This function is cached for performance.
    """
    from app.models.antenatal_models import AntenatalVisit
    from app.models.birth_models import BirthRecord, BirthOutcome, DeliveryType
    from sqlalchemy import func, case, cast, Integer
    
    # ANC Visits - Optimized aggregation queries
    # Total ANC visits
    total_anc_visits = db.query(func.count(AntenatalVisit.id)).filter(
        AntenatalVisit.is_active == True,
        func.date(AntenatalVisit.visit_date) >= start,
        func.date(AntenatalVisit.visit_date) <= end
    ).scalar() or 0
    
    # Unique ANC patients
    unique_anc_patients = db.query(
        func.count(func.distinct(AntenatalVisit.patient_id))
    ).filter(
        AntenatalVisit.is_active == True,
        func.date(AntenatalVisit.visit_date) >= start,
        func.date(AntenatalVisit.visit_date) <= end
    ).scalar() or 0
    
    # ANC Visit Numbers using CASE for efficient counting
    anc_visit_counts = db.query(
        func.sum(case((AntenatalVisit.visit_number == 1, 1), else_=0)),
        func.sum(case((AntenatalVisit.visit_number == 2, 1), else_=0)),
        func.sum(case((AntenatalVisit.visit_number == 3, 1), else_=0)),
        func.sum(case((AntenatalVisit.visit_number == 4, 1), else_=0)),
        func.sum(case((AntenatalVisit.visit_number >= 5, 1), else_=0))
    ).filter(
        AntenatalVisit.is_active == True,
        func.date(AntenatalVisit.visit_date) >= start,
        func.date(AntenatalVisit.visit_date) <= end
    ).first()
    
    anc1_visits = anc_visit_counts[0] or 0
    anc2_visits = anc_visit_counts[1] or 0
    anc3_visits = anc_visit_counts[2] or 0
    anc4_visits = anc_visit_counts[3] or 0
    anc5_plus_visits = anc_visit_counts[4] or 0
    
    # ANC Lab tests - Now uses actual model fields
    lab_test_result = db.query(
        func.sum(case((AntenatalVisit.hiv_tested == True, 1), else_=0)),
        func.sum(case((AntenatalVisit.syphilis_tested == True, 1), else_=0)),
        func.sum(case((AntenatalVisit.hepatitis_b_tested == True, 1), else_=0)),
        func.sum(case((AntenatalVisit.hepatitis_c_tested == True, 1), else_=0)),
        func.sum(case((AntenatalVisit.urinalysis_done == True, 1), else_=0)),
        # Positive results
        func.sum(case((AntenatalVisit.hiv_result == 'Positive', 1), else_=0)),
        func.sum(case((AntenatalVisit.syphilis_result == 'Positive', 1), else_=0)),
        func.sum(case((AntenatalVisit.hepatitis_b_result == 'Positive', 1), else_=0))
    ).filter(
        AntenatalVisit.is_active == True,
        func.date(AntenatalVisit.visit_date) >= start,
        func.date(AntenatalVisit.visit_date) <= end
    ).first()
    
    anc_hiv_tested = lab_test_result[0] or 0
    anc_syphilis_tested = lab_test_result[1] or 0
    anc_hepatitis_b_tested = lab_test_result[2] or 0
    anc_hepatitis_c_tested = lab_test_result[3] or 0
    anc_urinalysis_done = lab_test_result[4] or 0
    anc_hiv_positive = lab_test_result[5] or 0
    anc_syphilis_positive = lab_test_result[6] or 0
    anc_hepatitis_b_positive = lab_test_result[7] or 0
    
    # ANC by month
    anc_by_month_raw = db.query(
        func.to_char(AntenatalVisit.visit_date, 'YYYY-MM').label('month'),
        func.count(AntenatalVisit.id).label('count')
    ).filter(
        AntenatalVisit.is_active == True,
        func.date(AntenatalVisit.visit_date) >= start,
        func.date(AntenatalVisit.visit_date) <= end
    ).group_by(func.to_char(AntenatalVisit.visit_date, 'YYYY-MM')).all()
    
    anc_by_month = {row.month: row.count for row in anc_by_month_raw}
    
    # Birth Records - Optimized aggregation queries
    total_births = db.query(func.count(BirthRecord.id)).filter(
        BirthRecord.is_active == True,
        BirthRecord.birth_date >= start,
        BirthRecord.birth_date <= end
    ).scalar() or 0
    
    # Birth outcomes using CASE
    birth_outcome_result = db.query(
        func.sum(case((func.lower(BirthRecord.birth_outcome) == BirthOutcome.LIVE.value, 1), else_=0)),
        func.sum(case((func.lower(BirthRecord.birth_outcome) == BirthOutcome.STILLBIRTH.value, 1), else_=0)),
        func.sum(case((func.lower(BirthRecord.birth_outcome) == 'still_birth', 1), else_=0))
    ).filter(
        BirthRecord.is_active == True,
        BirthRecord.birth_date >= start,
        BirthRecord.birth_date <= end
    ).first()
    
    live_births = (birth_outcome_result[0] or 0)
    stillbirths = (birth_outcome_result[1] or 0) + (birth_outcome_result[2] or 0)
    
    # Delivery types
    delivery_type_result = db.query(
        func.sum(case((func.lower(BirthRecord.delivery_type) == DeliveryType.VAGINAL.value, 1), else_=0)),
        func.sum(case((func.lower(BirthRecord.delivery_type) == DeliveryType.CAESAREAN.value, 1), else_=0)),
        func.sum(case((func.lower(BirthRecord.delivery_type) == DeliveryType.ASSISTED.value, 1), else_=0)),
        func.sum(case((func.lower(BirthRecord.delivery_type) == 'normal', 1), else_=0))
    ).filter(
        BirthRecord.is_active == True,
        BirthRecord.birth_date >= start,
        BirthRecord.birth_date <= end
    ).first()
    
    vaginal_delivery = (delivery_type_result[0] or 0) + (delivery_type_result[3] or 0)
    cesarean_delivery = delivery_type_result[1] or 0
    assisted_delivery = delivery_type_result[2] or 0
    
    # Birth weight
    birth_weight_result = db.query(
        func.sum(case((BirthRecord.weight_kg < 2.5, 1), else_=0)),
        func.sum(case((BirthRecord.weight_kg < 1.5, 1), else_=0)),
        func.sum(case((BirthRecord.weight_kg >= 2.5, 1), else_=0)),
        func.sum(case((BirthRecord.weight_kg == None, 1), else_=0))
    ).filter(
        BirthRecord.is_active == True,
        BirthRecord.birth_date >= start,
        BirthRecord.birth_date <= end
    ).first()
    
    low_birth_weight = birth_weight_result[0] or 0
    very_low_birth_weight = birth_weight_result[1] or 0
    normal_birth_weight = birth_weight_result[2] or 0
    unknown_weight = birth_weight_result[3] or 0
    
    # Newborn care
    newborn_care_result = db.query(
        func.sum(case((BirthRecord.bcg_vaccine == True, 1), else_=0)),
        func.sum(case((BirthRecord.polio_vaccine == True, 1), else_=0)),
        func.sum(case((BirthRecord.vitamin_k_administered == True, 1), else_=0)),
        func.sum(case((BirthRecord.skin_to_skin == True, 1), else_=0)),
        func.sum(case((BirthRecord.breastfeeding_initiated_1hr == True, 1), else_=0))
    ).filter(
        BirthRecord.is_active == True,
        BirthRecord.birth_date >= start,
        BirthRecord.birth_date <= end
    ).first()
    
    bcg_vaccinated = newborn_care_result[0] or 0
    polio_vaccinated = newborn_care_result[1] or 0
    vitamin_k_given = newborn_care_result[2] or 0
    skin_to_skin = newborn_care_result[3] or 0
    early_breastfeeding = newborn_care_result[4] or 0
    
    # Birth attendant
    attendant_result = db.query(
        func.sum(case((BirthRecord.attendant_category == 'doctor', 1), else_=0)),
        func.sum(case((BirthRecord.attendant_category == 'midwife', 1), else_=0)),
        func.sum(case((BirthRecord.attendant_category == 'nurse', 1), else_=0)),
        func.sum(case((BirthRecord.attendant_category == 'tba', 1), else_=0)),
        func.sum(case((BirthRecord.attendant_category == 'cho', 1), else_=0))
    ).filter(
        BirthRecord.is_active == True,
        BirthRecord.birth_date >= start,
        BirthRecord.birth_date <= end
    ).first()
    
    births_by_doctor = attendant_result[0] or 0
    births_by_midwife = attendant_result[1] or 0
    births_by_nurse = attendant_result[2] or 0
    births_by_tba = attendant_result[3] or 0
    births_by_cho = attendant_result[4] or 0
    
    # Gestational age
    gestational_result = db.query(
        func.sum(case((BirthRecord.gestational_age_weeks < 37, 1), else_=0)),
        func.sum(case((BirthRecord.gestational_age_weeks >= 37, 1), else_=0))
    ).filter(
        BirthRecord.is_active == True,
        BirthRecord.birth_date >= start,
        BirthRecord.birth_date <= end,
        BirthRecord.gestational_age_weeks != None
    ).first()
    
    preterm_births = gestational_result[0] or 0
    term_births = gestational_result[1] or 0
    
    # PNC visits
    pnc_result = db.query(
        func.sum(case((BirthRecord.pnc1_date != None, 1), else_=0)),
        func.sum(case((BirthRecord.pnc2_date != None, 1), else_=0)),
        func.sum(case((BirthRecord.pnc3_date != None, 1), else_=0))
    ).filter(
        BirthRecord.is_active == True,
        BirthRecord.birth_date >= start,
        BirthRecord.birth_date <= end
    ).first()
    
    pnc1_visits = pnc_result[0] or 0
    pnc2_visits = pnc_result[1] or 0
    pnc3_visits = pnc_result[2] or 0
    
    # Births by month
    births_by_month_raw = db.query(
        func.to_char(BirthRecord.birth_date, 'YYYY-MM').label('month'),
        func.count(BirthRecord.id).label('count')
    ).filter(
        BirthRecord.is_active == True,
        BirthRecord.birth_date >= start,
        BirthRecord.birth_date <= end
    ).group_by(func.to_char(BirthRecord.birth_date, 'YYYY-MM')).all()
    
    births_by_month = {row.month: row.count for row in births_by_month_raw}
    
    # Year-over-year comparison (same period last year)
    start_last_year = start.replace(year=start.year - 1)
    end_last_year = end.replace(year=end.year - 1)
    
    last_year_births = db.query(func.count(BirthRecord.id)).filter(
        BirthRecord.is_active == True,
        BirthRecord.birth_date >= start_last_year,
        BirthRecord.birth_date <= end_last_year
    ).scalar() or 0
    
    last_year_anc = db.query(func.count(AntenatalVisit.id)).filter(
        AntenatalVisit.is_active == True,
        func.date(AntenatalVisit.visit_date) >= start_last_year,
        func.date(AntenatalVisit.visit_date) <= end_last_year
    ).scalar() or 0
    
    return {
        # ANC Summary
        "total_anc_visits": total_anc_visits,
        "unique_anc_patients": unique_anc_patients,
        "anc1_visits": anc1_visits,
        "anc2_visits": anc2_visits,
        "anc3_visits": anc3_visits,
        "anc4_visits": anc4_visits,
        "anc5_plus_visits": anc5_plus_visits,
        # ANC Lab Tests
        "anc_hiv_tested": anc_hiv_tested,
        "anc_hiv_positive": anc_hiv_positive,
        "anc_syphilis_tested": anc_syphilis_tested,
        "anc_syphilis_positive": anc_syphilis_positive,
        "anc_hepatitis_b_tested": anc_hepatitis_b_tested,
        "anc_hepatitis_b_positive": anc_hepatitis_b_positive,
        "anc_hepatitis_c_tested": anc_hepatitis_c_tested,
        "anc_urinalysis_done": anc_urinalysis_done,
        # Birth Summary
        "total_births": total_births,
        "live_births": live_births,
        "stillbirths": stillbirths,
        "vaginal_delivery": vaginal_delivery,
        "cesarean_delivery": cesarean_delivery,
        "assisted_delivery": assisted_delivery,
        # Birth Weight
        "low_birth_weight": low_birth_weight,
        "very_low_birth_weight": very_low_birth_weight,
        "normal_birth_weight": normal_birth_weight,
        "unknown_weight": unknown_weight,
        # Newborn Care
        "bcg_vaccinated": bcg_vaccinated,
        "polio_vaccinated": polio_vaccinated,
        "vitamin_k_given": vitamin_k_given,
        "skin_to_skin": skin_to_skin,
        "early_breastfeeding": early_breastfeeding,
        # Birth Attendant
        "births_by_doctor": births_by_doctor,
        "births_by_midwife": births_by_midwife,
        "births_by_nurse": births_by_nurse,
        "births_by_tba": births_by_tba,
        "births_by_cho": births_by_cho,
        # Gestational Age
        "preterm_births": preterm_births,
        "term_births": term_births,
        # PNC
        "pnc1_visits": pnc1_visits,
        "pnc2_visits": pnc2_visits,
        "pnc3_visits": pnc3_visits,
        # Time series
        "anc_by_month": anc_by_month,
        "births_by_month": births_by_month,
        # Year-over-year
        "last_year_births": last_year_births,
        "last_year_anc": last_year_anc
    }


@router.get("/dhims/mch", name="dhims_mch_report")
def dhims_mch_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    format: Optional[str] = Query(None, regex="html|json|csv|dhims2"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Midwife", "Nurse", "Management", "DHIMS2Preparer"]))
):
    """
    DHIMS2-style Maternal & Child Health Report for Ghana Health Service reporting.
    
    Includes:
    - ANC: Total visits, ANC1-4, ANC5+, unique patients
    - ANC Lab Tests: HIV, Syphilis, Hepatitis B/C (with test results)
    - Delivery: Total births, Live/Stillbirth, Delivery type
    - Newborn: Birth weight, BCG, Vitamin K, Skin-to-skin, Early breastfeeding
    - PNC: Postnatal care visits (PNC1, PNC2, PNC3)
    - Year-over-year comparison
    
    Export formats:
    - html: Default HTML template
    - json: JSON for API integration
    - csv: CSV for spreadsheet analysis
    - dhims2: DHIMS2-compatible JSON format
    
    Query parameters:
    - start_date: Start date (YYYY-MM-DD), defaults to first day of current month
    - end_date: End date (YYYY-MM-DD), defaults to today
    - format: Output format (html|json|csv|dhims2)
    """
    from app.models.antenatal_models import AntenatalVisit
    from app.models.birth_models import BirthRecord
    
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today().replace(day=1)
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Get hospital settings
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    # Get report data (uses optimized queries)
    report_data = _get_mch_report_data(db, start, end)
    
    # Handle export formats
    if format == "json":
        return {
            "status": "success",
            "report_type": "dhims_mch",
            "period": {
                "start": start.strftime("%Y-%m-%d"),
                "end": end.strftime("%Y-%m-%d")
            },
            "generated_at": datetime.now().isoformat(),
            "data": report_data
        }
    
    elif format == "csv":
        # Generate CSV response
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(["Indicator", "Value"])
        
        # Data rows
        for key, value in report_data.items():
            if not isinstance(value, dict):
                writer.writerow([key, value])
            else:
                for sub_key, sub_value in value.items():
                    writer.writerow([f"{key}.{sub_key}", sub_value])
        
        output.seek(0)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=mch_report_{start}_{end}.csv"}
        )
    
    elif format == "dhims2":
        # DHIMS2-compatible format
        dhims2_data = {
            "org_unit": hospital_settings.hospital_name if hospital_settings else "Unknown",
            "period": start.strftime("%Y%m"),
            "data": {
                "ANC_Total": report_data["total_anc_visits"],
                "ANC_Clients": report_data["unique_anc_patients"],
                "ANC1": report_data["anc1_visits"],
                "ANC2": report_data["anc2_visits"],
                "ANC3": report_data["anc3_visits"],
                "ANC4": report_data["anc4_visits"],
                "ANC5plus": report_data["anc5_plus_visits"],
                "HIV_Tested": report_data["anc_hiv_tested"],
                "HIV_Positive": report_data["anc_hiv_positive"],
                "Syphilis_Tested": report_data["anc_syphilis_tested"],
                "Syphilis_Positive": report_data["anc_syphilis_positive"],
                "HepatitisB_Tested": report_data["anc_hepatitis_b_tested"],
                "HepatitisB_Positive": report_data["anc_hepatitis_b_positive"],
                "Deliveries_Total": report_data["total_births"],
                "Live_Births": report_data["live_births"],
                "Still_Births": report_data["stillbirths"],
                "Normal_Delivery": report_data["vaginal_delivery"],
                "Caesarean_Section": report_data["cesarean_delivery"],
                "Low_Birth_Weight": report_data["low_birth_weight"],
                "Very_Low_Birth_Weight": report_data["very_low_birth_weight"],
                "BCG_Vaccinated": report_data["bcg_vaccinated"],
                "Vitamin_K_Given": report_data["vitamin_k_given"],
                "Skin_to_Skin": report_data["skin_to_skin"],
                "Early_Breastfeeding": report_data["early_breastfeeding"],
                "PNC1": report_data["pnc1_visits"],
                "PNC2": report_data["pnc2_visits"],
                "PNC3": report_data["pnc3_visits"],
                "Preterm_Births": report_data["preterm_births"],
                "Term_Births": report_data["term_births"],
                "Births_by_Doctor": report_data["births_by_doctor"],
                "Births_by_Midwife": report_data["births_by_midwife"],
                "Births_by_Nurse": report_data["births_by_nurse"],
                "Births_by_TBA": report_data["births_by_tba"]
            },
            "trends": {
                "anc_by_month": report_data["anc_by_month"],
                "births_by_month": report_data["births_by_month"]
            },
            "year_over_year": {
                "previous_period_births": report_data["last_year_births"],
                "previous_period_anc": report_data["last_year_anc"]
            }
        }
        return dhims2_data
    
    # Default: HTML template
    context = {
        "request": request,
        "title": "DHIMS2 Maternal & Child Health Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        **report_data,
        "hospital_settings": hospital_settings,
        "report_date": datetime.now()
    }
    return templates.TemplateResponse("reports/dhims_mch_report.html", context)
# ==================== DHIMS2 DISEASE REPORT ====================

@router.get("/dhims/disease", name="dhims_disease_report")
def dhims_disease_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    format: str = Query("html", regex="^(html|pdf|excel)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Nurse", "Management", "DHIMS2Preparer"]))
):
    """
    DHIMS2-style Disease Report for Ghana Health Service reporting.
    
    Includes OPD and IPD morbidity broken down by:
    - Gender (Male/Female)
    - Age groups (Under 5, 5-14, 15-24, 25-34, 35-44, 45-54, 55-64, 65+)
    - Disease categories (Infectious, NCDs, Maternal, etc.)
    """
    from app.models.encounter_models import Encounter
    from app.models.ipd_models import Admission
    
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today().replace(day=1)  # First day of current month
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Quick period filters
    if period:
        today = date.today()
        if period == 'this_month':
            start = today.replace(day=1)
            end = today
        elif period == 'last_month':
            first_day_this_month = today.replace(day=1)
            last_day_last_month = first_day_this_month - timedelta(days=1)
            start = last_day_last_month.replace(day=1)
            end = last_day_last_month
        elif period == 'this_quarter':
            quarter = (today.month - 1) // 3
            start = date(today.year, quarter * 3 + 1, 1)
            end = today
        elif period == 'this_year':
            start = date(today.year, 1, 1)
            end = today
    
    # Define age groups
    age_groups = [
        ("under_5", 0, 4),
        ("5_14", 5, 14),
        ("15_24", 15, 24),
        ("25_34", 25, 34),
        ("35_44", 35, 44),
        ("45_54", 45, 54),
        ("55_64", 55, 64),
        ("65_plus", 65, 200)
    ]
    
    def get_age_group(dob):
        """Return age group key based on date of birth."""
        if not dob:
            return "unknown"
        if isinstance(dob, str):
            try:
                dob = date.fromisoformat(dob)
            except:
                return "unknown"
        age = calculate_age(dob)
        if age is None:
            return "unknown"
        for key, min_age, max_age in age_groups:
            if min_age <= age <= max_age:
                return key
        return "unknown"
    
    def get_gender_key(gender):
        """Normalize gender to standard keys."""
        if not gender:
            return "unknown"
        g = str(gender).lower()
        if g in ["male", "m"]:
            return "male"
        elif g in ["female", "f"]:
            return "female"
        return "unknown"
    
    def match_disease_by_name(disease_name: str, db_session: Session) -> tuple:
        """
        Try to match a free-text disease name to an existing Disease record.
        Returns (disease_id, disease_name, disease_code) or (None, original_name, None) if no match.
        """
        if not disease_name or not disease_name.strip():
            return None, None, None
        
        # Clean up the disease name
        clean_name = disease_name.strip()
        
        # Try exact match first (case-insensitive)
        existing = db_session.query(Disease).filter(
            func.lower(Disease.name) == clean_name.lower()
        ).first()
        
        if existing:
            return existing.id, existing.name, existing.code
        
        # Try partial match (disease name contains the search term)
        existing = db_session.query(Disease).filter(
            Disease.name.ilike(f"%{clean_name}%")
        ).first()
        
        if existing:
            return existing.id, existing.name, existing.code
        
        # No match found - return None to indicate custom/unmatched diagnosis
        return None, clean_name, None
    
    # ==================== OPD DISEASE MORBIDITY ====================
    
    # Get all OPD visits in period
    opd_visits = db.query(OPDVisit).options(
        joinedload(OPDVisit.patient),
        joinedload(OPDVisit.encounters)
    ).filter(
        OPDVisit.is_active == True,
        func.date(OPDVisit.visit_date) >= start,
        func.date(OPDVisit.visit_date) <= end
    ).all()
    
    opd_visit_ids = [v.id for v in opd_visits]
    opd_patient_map = {v.id: v.patient for v in opd_visits if v.patient}
    # Also build a patient_id -> patient map for encounters
    patient_map = {v.patient_id: v.patient for v in opd_visits if v.patient}
    
    # Get OPD encounters - use both query and relationship
    opd_encounters = []
    for visit in opd_visits:
        if visit.encounters:
            opd_encounters.extend(visit.encounters)
    
    # If no encounters from relationship, try the query method
    if not opd_encounters and opd_visit_ids:
        opd_encounters = db.query(Encounter).filter(
            Encounter.opd_visit_id.in_(opd_visit_ids)
        ).all()
    
    opd_encounter_ids = [e.id for e in opd_encounters]
    
    # Get diseases for OPD encounters
    opd_diseases = db.query(EncounterDisease).filter(
        EncounterDisease.encounter_id.in_(opd_encounter_ids)
    ).all() if opd_encounter_ids else []
    
    # If still no encounter diseases, try to get diagnosis from encounter directly
    for encounter in opd_encounters:
        if encounter.primary_diagnosis_description and encounter.primary_diagnosis_description.strip():
            # Create a pseudo EncounterDisease from encounter diagnosis
            disease_id, matched_name, code = match_disease_by_name(encounter.primary_diagnosis_description, db)
            if disease_id:
                key = f"disease_{disease_id}"
            else:
                key = f"custom_{matched_name}"
            
            # This will be added to opd_diseases processing below
            # For now, we'll handle it in the main loop
    
    # Build disease data structure: {disease_id: {name, gender: {male, female}, age_group: {}}}
    opd_disease_data = {}
    
    # First, process EncounterDisease records
    for enc_disease in opd_diseases:
        # Find the encounter in the list
        encounter = next((e for e in opd_encounters if e.id == enc_disease.encounter_id), None)
        if not encounter or not encounter.patient_id:
            continue
        
        # Use patient_map keyed by patient_id
        patient = patient_map.get(encounter.patient_id)
        if not patient:
            continue
        
        disease_name = enc_disease.disease.name if enc_disease.disease else (enc_disease.custom_name or "Unknown")
        disease_id = enc_disease.disease_id
        
        # Use consistent key format with IPD: disease_{id} or custom_{name}
        if disease_id:
            key = f"disease_{disease_id}"
        else:
            key = f"custom_{disease_name}"
        
        if key not in opd_disease_data:
            opd_disease_data[key] = {
                "name": disease_name,
                "code": enc_disease.disease.code if enc_disease.disease else None,
                "disease_id": disease_id,
                "total": 0,
                "male": 0,
                "female": 0,
                "unknown_gender": 0,
                "age_groups": {ag[0]: 0 for ag in age_groups},
                "unknown_age": 0
            }
        
        gender_key = get_gender_key(patient.gender)
        age_group_key = get_age_group(patient.date_of_birth)
        
        opd_disease_data[key]["total"] += 1
        opd_disease_data[key][gender_key] += 1
        
        if age_group_key in opd_disease_data[key]["age_groups"]:
            opd_disease_data[key]["age_groups"][age_group_key] += 1
        else:
            opd_disease_data[key]["unknown_age"] += 1
    
    # Also process encounters that have direct diagnosis (primary_diagnosis_description field)
    # This is a fallback for when there are no EncounterDisease records
    for encounter in opd_encounters:
        if not encounter.primary_diagnosis_description or not encounter.primary_diagnosis_description.strip():
            continue
        if not encounter.patient_id:
            continue
        
        # Use patient_map keyed by patient_id
        patient = patient_map.get(encounter.patient_id)
        if not patient:
            continue
        
        # Match the diagnosis to a disease
        disease_id, matched_name, code = match_disease_by_name(encounter.primary_diagnosis_description, db)
        
        if disease_id:
            key = f"disease_{disease_id}"
        else:
            key = f"custom_{matched_name}"
        
        if key not in opd_disease_data:
            opd_disease_data[key] = {
                "name": matched_name,
                "code": code,
                "disease_id": disease_id,
                "total": 0,
                "male": 0,
                "female": 0,
                "unknown_gender": 0,
                "age_groups": {ag[0]: 0 for ag in age_groups},
                "unknown_age": 0
            }
        
        gender_key = get_gender_key(patient.gender)
        age_group_key = get_age_group(patient.date_of_birth)
        
        opd_disease_data[key]["total"] += 1
        opd_disease_data[key][gender_key] += 1
        
        if age_group_key in opd_disease_data[key]["age_groups"]:
            opd_disease_data[key]["age_groups"][age_group_key] += 1
        else:
            opd_disease_data[key]["unknown_age"] += 1
    
    # Sort by total cases
    opd_disease_list = sorted(opd_disease_data.values(), key=lambda x: x["total"], reverse=True)
    
    # ==================== IPD DISEASE MORBIDITY ====================
    
    # Get all IPD admissions in period (including those that span the period)
    # Also get admissions that were discharged in the period
    ipd_admissions = db.query(Admission).options(
        joinedload(Admission.patient),
        joinedload(Admission.encounters)
    ).filter(
        Admission.is_active == True,
        or_(
            # Admitted in the period
            and_(
                func.date(Admission.admission_date) >= start,
                func.date(Admission.admission_date) <= end
            ),
            # Discharged in the period
            and_(
                Admission.discharge_date != None,
                func.date(Admission.discharge_date) >= start,
                func.date(Admission.discharge_date) <= end
            ),
            # Still admitted and admission was before period end
            and_(
                Admission.discharge_date == None,
                func.date(Admission.admission_date) <= end
            )
        )
    ).all()
    
    ipd_admission_ids = [a.id for a in ipd_admissions]
    
    # Get encounters from IPD admissions
    ipd_encounters = []
    for admission in ipd_admissions:
        if admission.encounters:
            ipd_encounters.extend(admission.encounters)
    
    # Also include encounters that happened during IPD admission periods
    # (even if linked to OPD visits instead of directly to admission)
    ipd_patient_ids = [a.patient_id for a in ipd_admissions if a.patient_id]
    if ipd_patient_ids:
        # Find all encounters for these patients during their admission periods
        for admission in ipd_admissions:
            if not admission.patient_id:
                continue
            
            # Determine admission period
            period_start = admission.admission_date
            period_end = admission.discharge_date if admission.discharge_date else datetime.now()
            
            # Find OPD encounters for this patient during the admission period
            # These should count as IPD encounters
            opd_encounters_during_ipd = db.query(Encounter).options(
                joinedload(Encounter.patient)
            ).filter(
                Encounter.patient_id == admission.patient_id,
                Encounter.opd_visit_id != None,
                Encounter.encounter_date >= period_start,
                Encounter.encounter_date <= period_end,
                Encounter.is_active == True
            ).all()
            
            # Add these to ipd_encounters (avoiding duplicates)
            existing_ids = set(e.id for e in ipd_encounters)
            for enc in opd_encounters_during_ipd:
                if enc.id not in existing_ids:
                    ipd_encounters.append(enc)
                    existing_ids.add(enc.id)
    
    ipd_encounter_ids = [e.id for e in ipd_encounters]
    
    # Get diseases for IPD encounters
    ipd_diseases = db.query(EncounterDisease).filter(
        EncounterDisease.encounter_id.in_(ipd_encounter_ids)
    ).all() if ipd_encounter_ids else []
    
    # ==================== INCLUDE ADMISSION DIAGNOSIS DATA ====================
    # Also include diagnoses from Admission.diagnosis and discharge_diagnosis fields
    # These are free-text fields that may contain diagnoses not recorded in EncounterDisease
    # (match_disease_by_name function is defined earlier in the code)
    
    # Process admission diagnoses and discharge diagnoses
    admission_diagnosis_data = {}
    discharge_diagnosis_data = {}
    ipd_disease_data = {}
    
    for admission in ipd_admissions:
        patient = admission.patient
        if not patient:
            continue
        
        # Process admission diagnosis
        if admission.diagnosis and admission.diagnosis.strip():
            # Split by comma to handle multiple diagnoses (e.g., "Malaria, Typhoid Fever")
            diagnosis_parts = [d.strip() for d in admission.diagnosis.split(',') if d.strip()]
            
            for diagnosis_text in diagnosis_parts:
                disease_id, matched_name, code = match_disease_by_name(diagnosis_text, db)
                
                if disease_id:
                    # Use matched disease
                    key = f"disease_{disease_id}"
                else:
                    # Use custom name as key (prefixed to distinguish)
                    key = f"custom_{matched_name}"
                
                if key not in admission_diagnosis_data:
                    admission_diagnosis_data[key] = {
                        "name": matched_name,
                        "code": code,
                        "disease_id": disease_id,  # None for custom
                        "total": 0,
                        "male": 0,
                        "female": 0,
                        "unknown_gender": 0,
                        "age_groups": {ag[0]: 0 for ag in age_groups},
                        "unknown_age": 0
                    }
                
                gender_key = get_gender_key(patient.gender)
                age_group_key = get_age_group(patient.date_of_birth)
                
                admission_diagnosis_data[key]["total"] += 1
                admission_diagnosis_data[key][gender_key] += 1
                
                if age_group_key in admission_diagnosis_data[key]["age_groups"]:
                    admission_diagnosis_data[key]["age_groups"][age_group_key] += 1
                else:
                    admission_diagnosis_data[key]["unknown_age"] += 1
        
        # Process discharge diagnosis
        if admission.discharge_diagnosis and admission.discharge_diagnosis.strip():
            # Split by comma to handle multiple diagnoses (e.g., "Malaria, Typhoid Fever")
            diagnosis_parts = [d.strip() for d in admission.discharge_diagnosis.split(',') if d.strip()]
            
            for diagnosis_text in diagnosis_parts:
                disease_id, matched_name, code = match_disease_by_name(diagnosis_text, db)
                
                if disease_id:
                    key = f"disease_{disease_id}"
                else:
                    key = f"custom_{matched_name}"
                
                if key not in discharge_diagnosis_data:
                    discharge_diagnosis_data[key] = {
                        "name": matched_name,
                        "code": code,
                        "disease_id": disease_id,
                        "total": 0,
                        "male": 0,
                        "female": 0,
                        "unknown_gender": 0,
                        "age_groups": {ag[0]: 0 for ag in age_groups},
                        "unknown_age": 0
                    }
                
                gender_key = get_gender_key(patient.gender)
                age_group_key = get_age_group(patient.date_of_birth)
                
                discharge_diagnosis_data[key]["total"] += 1
                discharge_diagnosis_data[key][gender_key] += 1
                
                if age_group_key in discharge_diagnosis_data[key]["age_groups"]:
                    discharge_diagnosis_data[key]["age_groups"][age_group_key] += 1
                else:
                    discharge_diagnosis_data[key]["unknown_age"] += 1
    
    # Merge admission diagnoses into IPD disease data
    # Use discharge diagnosis if available, otherwise use admission diagnosis
    for key, data in discharge_diagnosis_data.items():
        if key not in ipd_disease_data:
            ipd_disease_data[key] = data
        else:
            # Already exists - skip (discharge diagnosis already counted)
            pass
    
    # Add admission diagnoses for diseases not in discharge diagnosis
    for key, data in admission_diagnosis_data.items():
        if key not in ipd_disease_data:
            ipd_disease_data[key] = data
    
    # Build disease data structure for IPD from encounter diseases
    # ONLY add encounter diseases if they don't already exist from discharge/admission diagnosis
    # (This prevents duplicate counting - discharge diagnosis is the authoritative source)
    
    for enc_disease in ipd_diseases:
        encounter = next((e for e in ipd_encounters if e.id == enc_disease.encounter_id), None)
        if not encounter or not encounter.patient_id:
            continue
        
        # Find the admission for this encounter by matching patient and date
        # (encounters may be linked to OPD visits but still count as IPD if during admission)
        admission = None
        for a in ipd_admissions:
            if a.patient_id == encounter.patient_id:
                # Check if encounter falls within admission period
                enc_date = encounter.encounter_date
                if a.admission_date and enc_date:
                    period_start = a.admission_date
                    period_end = a.discharge_date if a.discharge_date else datetime.now()
                    if period_start <= enc_date <= period_end:
                        admission = a
                        break
        
        if not admission or not admission.patient:
            continue
        
        patient = admission.patient
        disease_name = enc_disease.disease.name if enc_disease.disease else (enc_disease.custom_name or "Unknown")
        disease_id = enc_disease.disease_id
        
        # Use same key format as admission/discharge diagnoses
        if disease_id:
            key = f"disease_{disease_id}"
        else:
            key = f"custom_{disease_name}"
        
        # Only add if NOT already in ipd_disease_data (avoid duplicates from discharge/admission diagnosis)
        if key not in ipd_disease_data:
            ipd_disease_data[key] = {
                "name": disease_name,
                "code": enc_disease.disease.code if enc_disease.disease else None,
                "disease_id": disease_id,
                "total": 0,
                "male": 0,
                "female": 0,
                "unknown_gender": 0,
                "age_groups": {ag[0]: 0 for ag in age_groups},
                "unknown_age": 0
            }
            
            gender_key = get_gender_key(patient.gender)
            age_group_key = get_age_group(patient.date_of_birth)
            
            ipd_disease_data[key]["total"] += 1
            ipd_disease_data[key][gender_key] += 1
            
            if age_group_key in ipd_disease_data[key]["age_groups"]:
                ipd_disease_data[key]["age_groups"][age_group_key] += 1
            else:
                ipd_disease_data[key]["unknown_age"] += 1
    
    # Also process IPD encounters that have direct diagnosis (primary_diagnosis_description field)
    # This is a fallback for when there are no EncounterDisease records
    # Only add if NOT already in ipd_disease_data (avoid duplicates from discharge/admission diagnosis)
    for encounter in ipd_encounters:
        if not encounter.primary_diagnosis_description or not encounter.primary_diagnosis_description.strip():
            continue
        if not encounter.patient_id:
            continue
        
        # Find the admission for this encounter
        admission = next((a for a in ipd_admissions if encounter in a.encounters), None)
        if not admission or not admission.patient:
            continue
        
        patient = admission.patient
        
        # Match the diagnosis to a disease
        disease_id, matched_name, code = match_disease_by_name(encounter.primary_diagnosis_description, db)
        
        if disease_id:
            key = f"disease_{disease_id}"
        else:
            key = f"custom_{matched_name}"
        
        # Only add if NOT already in ipd_disease_data (avoid duplicates from discharge/admission diagnosis)
        if key not in ipd_disease_data:
            ipd_disease_data[key] = {
                "name": matched_name,
                "code": code,
                "disease_id": disease_id,
                "total": 0,
                "male": 0,
                "female": 0,
                "unknown_gender": 0,
                "age_groups": {ag[0]: 0 for ag in age_groups},
                "unknown_age": 0
            }
            
            gender_key = get_gender_key(patient.gender)
            age_group_key = get_age_group(patient.date_of_birth)
            
            ipd_disease_data[key]["total"] += 1
            ipd_disease_data[key][gender_key] += 1
            
            if age_group_key in ipd_disease_data[key]["age_groups"]:
                ipd_disease_data[key]["age_groups"][age_group_key] += 1
            else:
                ipd_disease_data[key]["unknown_age"] += 1
    
    # Sort by total cases
    ipd_disease_list = sorted(ipd_disease_data.values(), key=lambda x: x["total"], reverse=True)
    
    # ==================== SUMMARY STATISTICS ====================
    
    # OPD Summary
    opd_total_cases = sum(d["total"] for d in opd_disease_data.values())
    opd_male_cases = sum(d["male"] for d in opd_disease_data.values())
    opd_female_cases = sum(d["female"] for d in opd_disease_data.values())
    
    opd_age_summary = {}
    for ag_key, _, _ in age_groups:
        opd_age_summary[ag_key] = sum(d["age_groups"].get(ag_key, 0) for d in opd_disease_data.values())
    
    # IPD Summary
    ipd_total_cases = sum(d["total"] for d in ipd_disease_data.values())
    ipd_male_cases = sum(d["male"] for d in ipd_disease_data.values())
    ipd_female_cases = sum(d["female"] for d in ipd_disease_data.values())
    
    ipd_age_summary = {}
    for ag_key, _, _ in age_groups:
        ipd_age_summary[ag_key] = sum(d["age_groups"].get(ag_key, 0) for d in ipd_disease_data.values())
    
    # Top diseases (combined OPD + IPD)
    combined_disease_data = {}
    for d in opd_disease_data.values():
        key = d["name"]
        if key not in combined_disease_data:
            combined_disease_data[key] = {"name": key, "opd": 0, "ipd": 0, "total": 0}
        combined_disease_data[key]["opd"] = d["total"]
        combined_disease_data[key]["total"] += d["total"]
    
    for d in ipd_disease_data.values():
        key = d["name"]
        if key not in combined_disease_data:
            combined_disease_data[key] = {"name": key, "opd": 0, "ipd": 0, "total": 0}
        combined_disease_data[key]["ipd"] = d["total"]
        combined_disease_data[key]["total"] += d["total"]
    
    top_diseases = sorted(combined_disease_data.values(), key=lambda x: x["total"], reverse=True)[:15]
    
    # ==================== DISEASE CATEGORY BREAKDOWN ====================
    
    # Get disease categories with counts
    # Need to normalize keys - OPD uses integer disease_id, IPD uses "disease_{id}" format
    all_disease_ids = set()
    
    # Extract integer disease IDs from OPD (string format "disease_{id}")
    for k in opd_disease_data.keys():
        if isinstance(k, int):
            all_disease_ids.add(k)
        elif isinstance(k, str) and k.startswith("disease_"):
            try:
                all_disease_ids.add(int(k.split("_")[1]))
            except:
                pass
    
    # Extract integer disease IDs from IPD (string format "disease_{id}")
    for k in ipd_disease_data.keys():
        if isinstance(k, int):
            all_disease_ids.add(k)
        elif isinstance(k, str) and k.startswith("disease_"):
            try:
                all_disease_ids.add(int(k.split("_")[1]))
            except:
                pass
    
    category_breakdown = {}
    
    for disease_id in all_disease_ids:
        disease = db.query(Disease).filter(Disease.id == disease_id).first()
        if disease:
            category = disease.category.value if hasattr(disease.category, 'value') else disease.category
            if category not in category_breakdown:
                category_breakdown[category] = {
                    "name": category.upper(),
                    "opd": 0,
                    "ipd": 0,
                    "total": 0
                }
            
            # Check OPD data (string keys "disease_{id}")
            opd_key = f"disease_{disease_id}"
            if opd_key in opd_disease_data:
                category_breakdown[category]["opd"] += opd_disease_data[opd_key]["total"]
            # Check IPD data (string keys "disease_{id}")
            ipd_key = f"disease_{disease_id}"
            if ipd_key in ipd_disease_data:
                category_breakdown[category]["ipd"] += ipd_disease_data[ipd_key]["total"]
            category_breakdown[category]["total"] = category_breakdown[category]["opd"] + category_breakdown[category]["ipd"]
    
    category_list = sorted(category_breakdown.values(), key=lambda x: x["total"], reverse=True)
    
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": "DHIMS2 Disease Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start_date if start_date else start.strftime("%Y-%m-%d"),
        "end_date": end_date if end_date else end.strftime("%Y-%m-%d"),
        "period": period,
        # OPD Data
        "opd_diseases": opd_disease_list[:50],
        "opd_total_cases": opd_total_cases,
        "opd_male_cases": opd_male_cases,
        "opd_female_cases": opd_female_cases,
        "opd_age_summary": opd_age_summary,
        "opd_unique_diseases": len(opd_disease_data),
        # IPD Data
        "ipd_diseases": ipd_disease_list[:50],
        "ipd_total_cases": ipd_total_cases,
        "ipd_male_cases": ipd_male_cases,
        "ipd_female_cases": ipd_female_cases,
        "ipd_age_summary": ipd_age_summary,
        "ipd_unique_diseases": len(ipd_disease_data),
        # Combined
        "top_diseases": top_diseases,
        "total_disease_cases": opd_total_cases + ipd_total_cases,
        "age_groups": [ag[0] for ag in age_groups],
        "hospital_settings": hospital_settings,
        "report_date": datetime.now(),
        # Category breakdown
        "category_breakdown": category_list
    }
    
    # Export handling
    if format == "pdf":
        from app.utils.pdf_generator import generate_dhims_disease_report_pdf
        pdf_context = {
            "filters": {
                "start_date": start,
                "end_date": end,
                "period": period
            },
            "opd": {
                "diseases": opd_disease_list[:50],
                "total_cases": opd_total_cases,
                "male_cases": opd_male_cases,
                "female_cases": opd_female_cases,
                "age_summary": opd_age_summary,
                "unique_diseases": len(opd_disease_data)
            },
            "ipd": {
                "diseases": ipd_disease_list[:50],
                "total_cases": ipd_total_cases,
                "male_cases": ipd_male_cases,
                "female_cases": ipd_female_cases,
                "age_summary": ipd_age_summary,
                "unique_diseases": len(ipd_disease_data)
            },
            "top_diseases": top_diseases,
            "category_breakdown": category_list,
            "age_groups": [ag[0] for ag in age_groups],
            "hospital_settings": hospital_settings,
            "report_date": datetime.now()
        }
        pdf_content = generate_dhims_disease_report_pdf(pdf_context)
        filename_safe = f"dhims2_disease_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.pdf"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename_safe}"
            }
        )
    elif format == "excel":
        from app.utils.excel_generator import generate_dhims_disease_report_excel
        excel_content = generate_dhims_disease_report_excel(context)
        filename_safe = f"dhims2_disease_report_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.xlsx"
        return Response(
            content=excel_content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename_safe}"
            }
        )
    
    return templates.TemplateResponse("reports/dhims_disease_report.html", context)


# ============================================
# NEW FINANCIAL REPORTS
# ============================================

@router.get("/financial/daily-cash-flow", name="daily_cash_flow_report")
def daily_cash_flow_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: str = Query("html", regex="^(html|excel)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Front Office"]))
):
    """
    Daily Cash Flow Report - Shows daily collections and payments.
    """
    from app.models.billing_models import Payment, PaymentStatus
    from app.models.expense_models import Expense, ExpenseStatus
    
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today() - timedelta(days=30)
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Get all payments in date range
    payments = db.query(Payment).filter(
        func.date(Payment.payment_date) >= start,
        func.date(Payment.payment_date) <= end,
        Payment.status == PaymentStatus.COMPLETED.value,
        Payment.is_active == True
    ).options(
        joinedload(Payment.patient),
        joinedload(Payment.invoice)
    ).order_by(Payment.payment_date.desc()).all()
    
    # Get all expenses in date range
    expenses = db.query(Expense).filter(
        func.date(Expense.expense_date) >= start,
        func.date(Expense.expense_date) <= end,
        Expense.status == ExpenseStatus.APPROVED.value,
        Expense.is_active == True
    ).order_by(Expense.expense_date.desc()).all()
    
    # Group by date
    daily_data = {}
    current = start
    while current <= end:
        daily_data[current] = {
            "date": current,
            "collections": Decimal('0.00'),
            "refunds": Decimal('0.00'),
            "expenses": Decimal('0.00'),
            "net_flow": Decimal('0.00'),
            "payment_count": 0,
            "by_method": {}
        }
        current += timedelta(days=1)
    
    # Process payments
    for payment in payments:
        payment_date = payment.payment_date.date()
        if payment_date in daily_data:
            method = payment.payment_method.value if payment.payment_method else "unknown"
            
            # Check if refund
            if payment.amount < 0:
                daily_data[payment_date]["refunds"] += abs(payment.amount)
            else:
                daily_data[payment_date]["collections"] += payment.amount
                daily_data[payment_date]["payment_count"] += 1
                
                if method not in daily_data[payment_date]["by_method"]:
                    daily_data[payment_date]["by_method"][method] = Decimal('0.00')
                daily_data[payment_date]["by_method"][method] += payment.amount
    
    # Process expenses
    for expense in expenses:
        expense_date = expense.expense_date.date()
        if expense_date in daily_data:
            daily_data[expense_date]["expenses"] += expense.amount
    
    # Calculate net flow
    for daily in daily_data.values():
        daily["net_flow"] = daily["collections"] - daily["refunds"] - daily["expenses"]
    
    # Calculate totals
    total_collections = sum(d["collections"] for d in daily_data.values())
    total_refunds = sum(d["refunds"] for d in daily_data.values())
    total_expenses = sum(d["expenses"] for d in daily_data.values())
    total_net_flow = total_collections - total_refunds - total_expenses
    
    context = {
        "request": request,
        "title": "Daily Cash Flow Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "daily_data": list(daily_data.values()),
        "total_collections": total_collections,
        "total_refunds": total_refunds,
        "total_expenses": total_expenses,
        "total_net_flow": total_net_flow,
        "report_date": datetime.now()
    }
    
    return templates.TemplateResponse("reports/daily_cash_flow.html", context)


@router.get("/financial/debtors-aging", name="debtors_aging_report")
def debtors_aging_report(
    request: Request,
    as_of_date: Optional[str] = Query(None),
    format: str = Query("html", regex="^(html|excel)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Management"]))
):
    """
    Debtors Aging Report - Shows outstanding invoices by age (current, 30, 60, 90+ days).
    """
    from app.models.patient_models import Patient
    
    # Parse as-of date
    if as_of_date:
        as_of = datetime.strptime(as_of_date, "%Y-%m-%d").date()
    else:
        as_of = date.today()
    
    # Get all active invoices with outstanding balance
    invoices = db.query(Invoice).options(
        joinedload(Invoice.patient)
    ).filter(
        Invoice.is_active == True,
        Invoice.balance > 0,
        Invoice.status.in_([InvoiceStatus.PENDING.value, InvoiceStatus.PARTIALLY_PAID.value])
    ).order_by(Invoice.invoice_date.asc()).all()
    
    # Age buckets
    aging_buckets = {
        "current": {"label": "Current (0-30 days)", "min_days": 0, "max_days": 30, "invoices": [], "total": Decimal('0.00')},
        "aging_30": {"label": "31-60 days", "min_days": 31, "max_days": 60, "invoices": [], "total": Decimal('0.00')},
        "aging_60": {"label": "61-90 days", "min_days": 61, "max_days": 90, "invoices": [], "total": Decimal('0.00')},
        "aging_90": {"label": "90+ days", "min_days": 91, "max_days": 9999, "invoices": [], "total": Decimal('0.00')}
    }
    
    # Patient-level aging
    patient_aging = {}
    
    for invoice in invoices:
        # Calculate age in days
        invoice_date = invoice.invoice_date.date() if isinstance(invoice.invoice_date, datetime) else invoice.invoice_date
        age_days = (as_of - invoice_date).days
        
        # Determine bucket
        bucket_key = "current"
        if age_days > 90:
            bucket_key = "aging_90"
        elif age_days > 60:
            bucket_key = "aging_60"
        elif age_days > 30:
            bucket_key = "aging_30"
        
        invoice_data = {
            "invoice": invoice,
            "patient": invoice.patient,
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date,
            "due_date": invoice.due_date,
            "age_days": age_days,
            "total_amount": invoice.total_amount,
            "paid_amount": invoice.paid_amount,
            "balance": invoice.balance,
            "status": invoice.status
        }
        
        aging_buckets[bucket_key]["invoices"].append(invoice_data)
        aging_buckets[bucket_key]["total"] += invoice.balance
        
        # Patient-level aggregation
        patient_id = invoice.patient_id
        if patient_id not in patient_aging:
            patient_aging[patient_id] = {
                "patient": invoice.patient,
                "total_balance": Decimal('0.00'),
                "oldest_invoice": invoice.invoice_date,
                "invoice_count": 0
            }
        patient_aging[patient_id]["total_balance"] += invoice.balance
        patient_aging[patient_id]["invoice_count"] += 1
        if invoice.invoice_date < patient_aging[patient_id]["oldest_invoice"]:
            patient_aging[patient_id]["oldest_invoice"] = invoice.invoice_date
    
    # Calculate grand total
    grand_total = sum(bucket["total"] for bucket in aging_buckets.values())
    total_patients = len(patient_aging)
    
    context = {
        "request": request,
        "title": "Debtors Aging Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "as_of_date": as_of.strftime("%Y-%m-%d"),
        "aging_buckets": aging_buckets,
        "patient_aging": list(patient_aging.values()),
        "grand_total": grand_total,
        "total_patients": total_patients,
        "report_date": datetime.now()
    }
    
    return templates.TemplateResponse("reports/debtors_aging.html", context)


@router.get("/financial/refund-analysis", name="refund_analysis_report")
def refund_analysis_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: str = Query("html", regex="^(html|excel)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance"]))
):
    """
    Refund Analysis Report - Shows refund trends and reasons.
    """
    from app.models.billing_models import Refund, RefundStatus
    
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today() - timedelta(days=90)
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Get all refunds in date range
    refunds = db.query(Refund).options(
        joinedload(Refund.patient),
        joinedload(Refund.invoice),
        joinedload(Refund.payment)
    ).filter(
        Refund.is_active == True,
        func.date(Refund.created_at) >= start,
        func.date(Refund.created_at) <= end
    ).order_by(Refund.created_at.desc()).all()
    
    # Analysis by status
    status_breakdown = {}
    for status in RefundStatus:
        status_breakdown[status.value] = {"count": 0, "total": Decimal('0.00')}
    
    # Analysis by reason (keywords)
    reason_analysis = {}
    
    # Monthly trend
    monthly_trend = {}
    
    for refund in refunds:
        status = refund.status.value
        if status not in status_breakdown:
            status_breakdown[status] = {"count": 0, "total": Decimal('0.00')}
        status_breakdown[status]["count"] += 1
        status_breakdown[status]["total"] += refund.amount
        
        # Reason analysis
        if refund.reason:
            reason_key = refund.reason[:50]  # Use first 50 chars as key
            if reason_key not in reason_analysis:
                reason_analysis[reason_key] = {"count": 0, "total": Decimal('0.00')}
            reason_analysis[reason_key]["count"] += 1
            reason_analysis[reason_key]["total"] += refund.amount
        
        # Monthly trend
        refund_month = refund.created_at.strftime("%Y-%m")
        if refund_month not in monthly_trend:
            monthly_trend[refund_month] = {"count": 0, "total": Decimal('0.00')}
        monthly_trend[refund_month]["count"] += 1
        monthly_trend[refund_month]["total"] += refund.amount
    
    # Calculate totals
    total_refunds = sum(r.amount for r in refunds)
    total_count = len(refunds)
    avg_refund = total_refunds / total_count if total_count > 0 else Decimal('0.00')
    
    # Sort reason analysis by total
    top_reasons = sorted(reason_analysis.items(), key=lambda x: x[1]["total"], reverse=True)[:10]
    
    # Sort monthly trend
    sorted_months = sorted(monthly_trend.items())
    
    context = {
        "request": request,
        "title": "Refund Analysis Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "refunds": refunds,
        "status_breakdown": status_breakdown,
        "reason_analysis": reason_analysis,
        "top_reasons": top_reasons,
        "monthly_trend": sorted_months,
        "total_refunds": total_refunds,
        "total_count": total_count,
        "avg_refund": avg_refund,
        "report_date": datetime.now()
    }
    
    return templates.TemplateResponse("reports/refund_analysis.html", context)
