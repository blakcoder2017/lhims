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
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import Optional, List
from datetime import datetime, date, timedelta
from decimal import Decimal
import json

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.crud import ipd_crud, patient_crud, billing_crud, drug_administration_crud, procedure_reports_crud, procedure_reports_crud
from app.models.ipd_models import Admission, AdmissionStatus, AdmissionNote
from app.models.billing_models import Invoice, Charge, ChargeType, Payment, PaymentStatus
from app.models.patient_models import Patient, PaymentMechanism
from app.models.encounter_models import Encounter, EncounterStatus, LabOrder, RadiologyOrder, Prescription
from app.models.procedure_models import Procedure
from app.models.expense_models import Expense, ExpenseCategory, ExpenseStatus
from app.models.opd_models import OPDVisit, OPDVisitStatus
from app.models.disease_models import Disease, EncounterDisease
from app.crud import hospital_settings_crud, opd_crud, user_crud, service_pricing_crud
from app.models.user_models import User, Role

router = APIRouter(prefix="/reports", tags=["Reports"])

DEFAULT_CONSULTATION_FEE = Decimal('100.00')
templates = Jinja2Templates(directory="app/templates")


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
    for encounter in admission.encounters:
        lab_orders.extend(db.query(LabOrder).filter(LabOrder.encounter_id == encounter.id).all())
    
    # Get prescriptions
    prescriptions = []
    for encounter in admission.encounters:
        prescriptions.extend(db.query(Prescription).filter(Prescription.encounter_id == encounter.id).all())
    
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
        "administrations": administrations,
        "notes": notes,
        "vitals_records": vitals_records[:10],  # Limit to 10 most recent
        "lab_orders": lab_orders,
        "prescriptions": prescriptions,
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

@router.get("/pharmacy", name="pharmacy_report")
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
        "report_date": datetime.now()
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


@router.get("/lab", name="lab_report")
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


@router.get("/radiology", name="radiology_report")
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
    
    # Get admissions
    admissions = db.query(Admission).options(
        joinedload(Admission.patient),
        joinedload(Admission.ward),
        joinedload(Admission.bed),
        joinedload(Admission.invoice),
        joinedload(Admission.encounters)
    ).filter(
        Admission.is_active == True,
        func.date(Admission.admission_date) >= start,
        func.date(Admission.admission_date) <= end
    ).all()
    
    # Financial Report
    total_revenue = sum([a.invoice.total_amount if a.invoice else Decimal('0.00') for a in admissions])
    total_paid = sum([a.invoice.paid_amount if a.invoice else Decimal('0.00') for a in admissions])
    total_outstanding = total_revenue - total_paid
    
    # Disease Report - Get diseases from encounters
    disease_counts = {}
    disease_revenue = {}
    
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
                    disease_counts[disease_name] = disease_counts.get(disease_name, 0) + 1
                    
                    # Calculate revenue for this disease (from admission invoice)
                    if admission.invoice:
                        if disease_name not in disease_revenue:
                            disease_revenue[disease_name] = Decimal('0.00')
                        # Distribute revenue proportionally (simplified)
                        disease_revenue[disease_name] += admission.invoice.total_amount / max(len(encounter_diseases), 1)
            
            # Also check primary diagnosis
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
