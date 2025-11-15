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
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Optional, List
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.crud import ipd_crud, patient_crud, billing_crud, drug_administration_crud
from app.models.ipd_models import Admission, AdmissionStatus, AdmissionNote
from app.models.billing_models import Invoice, Charge, ChargeType, Payment, PaymentStatus
from app.models.patient_models import Patient, PaymentMechanism
from app.models.encounter_models import Encounter, LabOrder, RadiologyOrder, Prescription
from app.models.expense_models import Expense, ExpenseCategory, ExpenseStatus
from app.crud import hospital_settings_crud

router = APIRouter(prefix="/reports", tags=["Reports"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", name="reports_dashboard")
def reports_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Management", "Doctor"]))
):
    """Reports dashboard - lists all available reports."""
    context = {
        "request": request,
        "title": "Reports Dashboard",
        "current_user": current_user,
        "user_role": current_user.role.name
    }
    return templates.TemplateResponse("reports/dashboard.html", context)


@router.get("/admissions/{admission_id}/report", name="admission_report")
def admission_report(
    request: Request,
    admission_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Nurse", "Front Office", "Finance"])),
    format: str = Query("html", regex="^(html|pdf)$")
):
    """Generate admission report for a specific admission."""
    admission = ipd_crud.get_admission(db, admission_id)
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    
    patient = admission.patient
    
    # Get encounters during admission
    encounters = []
    if admission.encounter_id:
        encounters = db.query(Encounter).filter(
            Encounter.id == admission.encounter_id,
            Encounter.is_active == True
        ).all()
    else:
        # Get encounters during admission period
        encounters = db.query(Encounter).filter(
            Encounter.patient_id == patient.id,
            Encounter.encounter_date >= admission.admission_date,
            Encounter.is_active == True
        ).all()
        if admission.discharge_date:
            encounters = [e for e in encounters if e.encounter_date <= admission.discharge_date]
    
    # Get vitals during admission
    from app.models.triage_models import TriageVitals
    vitals = db.query(TriageVitals).filter(
        TriageVitals.patient_id == patient.id,
        TriageVitals.recorded_at >= admission.admission_date
    ).all()
    if admission.discharge_date:
        vitals = [v for v in vitals if v.recorded_at <= admission.discharge_date]
    
    # Get lab orders during admission
    lab_orders = []
    radiology_orders = []
    prescriptions = []
    for encounter in encounters:
        lab_orders.extend(db.query(LabOrder).filter(LabOrder.encounter_id == encounter.id).all())
        radiology_orders.extend(db.query(RadiologyOrder).filter(RadiologyOrder.encounter_id == encounter.id).all())
        prescriptions.extend(db.query(Prescription).filter(Prescription.encounter_id == encounter.id).all())
    
    # Get invoices related to admission
    invoices = db.query(Invoice).filter(
        Invoice.patient_id == patient.id,
        Invoice.invoice_date >= admission.admission_date
    ).all()
    if admission.discharge_date:
        invoices = [inv for inv in invoices if inv.invoice_date <= admission.discharge_date]
    
    # Calculate length of stay
    discharge_date = admission.discharge_date or datetime.now()
    length_of_stay = (discharge_date - admission.admission_date).days
    
    # Get drug administrations
    drug_administrations = drug_administration_crud.get_drug_administrations_by_admission(db, admission.id)

    # Get admission notes (both nurses and doctors)
    admission_notes = db.query(AdmissionNote).filter(
        AdmissionNote.admission_id == admission.id,
        AdmissionNote.is_active == True
    ).order_by(AdmissionNote.created_at.desc()).all()

    context = {
        "request": request,
        "title": f"Admission Report: {admission.admission_number}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "admission": admission,
        "patient": patient,
        "encounters": encounters,
        "vitals": vitals,
        "lab_orders": lab_orders,
        "radiology_orders": radiology_orders,
        "prescriptions": prescriptions,
        "drug_administrations": drug_administrations,
        "admission_notes": admission_notes,
        "invoices": invoices,
        "length_of_stay": length_of_stay,
        "report_date": datetime.now()
    }
    
    if format == "pdf":
        # Generate PDF (will implement PDF generation utility)
        from app.utils.pdf_generator import generate_admission_report_pdf
        pdf_content = generate_admission_report_pdf(context)
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=admission_report_{admission.admission_number}.pdf"
            }
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
    
    # Get all invoices in date range
    invoices = db.query(Invoice).filter(*filters).all()
    
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
        service_type = charge.charge_type.value
        if service_type not in service_breakdown:
            service_breakdown[service_type] = {
                "count": 0,
                "total": Decimal('0.00'),
                "paid": Decimal('0.00')
            }
        
        service_breakdown[service_type]["count"] += 1
        service_breakdown[service_type]["total"] += charge.total_amount
        
        # Find payments for this charge's invoice
        invoice_payments = [p for p in payments if p.invoice_id == charge.invoice_id]
        if invoice_payments:
            # Proportionally allocate payments
            invoice = next((inv for inv in invoices if inv.id == charge.invoice_id), None)
            if invoice and invoice.total_amount > 0:
                payment_ratio = sum([p.amount for p in invoice_payments]) / invoice.total_amount
                service_breakdown[service_type]["paid"] += charge.total_amount * payment_ratio
    
    # Filter by service type if specified
    if service_type:
        service_breakdown = {k: v for k, v in service_breakdown.items() if k == service_type}
    
    # Breakdown by payment mechanism
    payment_breakdown = {}
    for invoice in invoices:
        pm = invoice.payment_mechanism or "unknown"
        if pm not in payment_breakdown:
            payment_breakdown[pm] = {
                "count": 0,
                "total": Decimal('0.00'),
                "paid": Decimal('0.00')
            }
        payment_breakdown[pm]["count"] += 1
        payment_breakdown[pm]["total"] += invoice.total_amount
        payment_breakdown[pm]["paid"] += invoice.paid_amount
    
    context = {
        "request": request,
        "title": "Financial Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start,
        "end_date": end,
        "service_type": service_type,
        "payment_mechanism": payment_mechanism,
        "total_revenue": total_revenue,
        "total_paid": total_paid,
        "total_outstanding": total_outstanding,
        "service_breakdown": service_breakdown,
        "payment_breakdown": payment_breakdown,
        "invoices": invoices[:100],  # Limit for display
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
        # Excel export (to be implemented)
        pass
    
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
        age_dict = calculate_age(patient.date_of_birth)
        age = age_dict['years']  # Get years as integer
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
    
    # Common conditions (from encounters)
    conditions = {}
    encounters = db.query(Encounter).filter(
        Encounter.patient_id.in_([p.id for p in patients]),
        Encounter.is_active == True
    ).all()
    
    for encounter in encounters:
        if encounter.primary_diagnosis_description:
            condition = encounter.primary_diagnosis_description
            conditions[condition] = conditions.get(condition, 0) + 1
    
    # Top conditions
    top_conditions = sorted(conditions.items(), key=lambda x: x[1], reverse=True)[:10]
    
    context = {
        "request": request,
        "title": "Patient Demographics Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "start_date": start,
        "end_date": end,
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
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=patient_demographics_{start}_{end}.pdf"
            }
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
    elif period == "month":
        start = today.replace(day=1)
        end = today
    elif period == "year":
        start = today.replace(month=1, day=1)
        end = today
    else:  # custom
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start = today - timedelta(days=30)  # Default: last 30 days
        
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end = today
    
    # Calculate REVENUE from payments (actual cash received)
    # Revenue = sum of all payments made within the period
    payments = db.query(Payment).filter(
        Payment.is_active == True,
        func.date(Payment.payment_date) >= start,
        func.date(Payment.payment_date) <= end,
        Payment.status == PaymentStatus.COMPLETED.value  # Only count completed payments
    ).all()
    
    total_revenue = sum([p.amount for p in payments])
    
    # Revenue breakdown by payment method
    revenue_by_method = {}
    for payment in payments:
        method = payment.payment_method.value if hasattr(payment.payment_method, 'value') else str(payment.payment_method)
        if method not in revenue_by_method:
            revenue_by_method[method] = Decimal('0.00')
        revenue_by_method[method] += payment.amount
    
    # Revenue breakdown by service type (from charges on invoices that have payments)
    payment_invoice_ids = [p.invoice_id for p in payments]
    charges = db.query(Charge).filter(
        Charge.invoice_id.in_(payment_invoice_ids)
    ).all()
    
    revenue_by_service = {}
    for charge in charges:
        # Find corresponding payment for this invoice
        invoice_payments = [p for p in payments if p.invoice_id == charge.invoice_id]
        if invoice_payments:
            # Get the invoice to calculate payment ratio
            invoice = db.query(Invoice).filter(Invoice.id == charge.invoice_id).first()
            if invoice and invoice.total_amount > 0:
                total_paid_for_invoice = sum([p.amount for p in invoice_payments])
                payment_ratio = total_paid_for_invoice / invoice.total_amount
                service_type = charge.charge_type.value
                if service_type not in revenue_by_service:
                    revenue_by_service[service_type] = Decimal('0.00')
                revenue_by_service[service_type] += charge.total_amount * payment_ratio
    
    # Calculate EXPENSES from Expense model
    expenses = db.query(Expense).filter(
        Expense.is_active == True,
        func.date(Expense.expense_date) >= start,
        func.date(Expense.expense_date) <= end,
        Expense.status.in_([ExpenseStatus.APPROVED.value, ExpenseStatus.PAID.value])  # Only count approved/paid expenses
    ).all()
    
    total_expenses = sum([e.amount for e in expenses])
    
    # Expense breakdown by category
    expenses_by_category = {}
    for expense in expenses:
        category = expense.category.value if hasattr(expense.category, 'value') else str(expense.category)
        if category not in expenses_by_category:
            expenses_by_category[category] = Decimal('0.00')
        expenses_by_category[category] += expense.amount
    
    # Calculate NET INCOME
    net_income = total_revenue - total_expenses
    
    # Calculate profit margin
    profit_margin = (net_income / total_revenue * 100) if total_revenue > 0 else Decimal('0.00')
    
    context = {
        "request": request,
        "title": "Income Statement (Profit & Loss)",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "hospital_settings": hospital_settings,
        "period": period,
        "start_date": start,
        "end_date": end,
        "total_revenue": total_revenue,
        "revenue_by_method": revenue_by_method,
        "revenue_by_service": revenue_by_service,
        "total_expenses": total_expenses,
        "expenses_by_category": expenses_by_category,
        "net_income": net_income,
        "profit_margin": profit_margin,
        "report_date": datetime.now(),
        "period_label": _get_period_label(period, start, end)
    }
    
    if format == "pdf":
        from app.utils.pdf_generator import generate_income_statement_pdf
        pdf_content = generate_income_statement_pdf(context)
        period_label_safe = _get_period_label(period, start, end).replace(" ", "_").replace("/", "-")
        filename = f"income_statement_{period_label_safe}.pdf"
        
        def generate():
            yield pdf_content
        
        return StreamingResponse(
            generate(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    elif format == "excel":
        from app.utils.excel_generator import generate_income_statement_excel
        excel_content = generate_income_statement_excel(context)
        period_label_safe = _get_period_label(period, start, end).replace(" ", "_").replace("/", "-")
        filename = f"income_statement_{period_label_safe}.xlsx"
        
        def generate():
            yield excel_content
        
        return StreamingResponse(
            generate(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    
    return templates.TemplateResponse("reports/income_statement.html", context)


def _get_period_label(period: str, start: date, end: date) -> str:
    """Generate a human-readable period label."""
    if period == "day":
        return start.strftime("%B %d, %Y")
    elif period == "month":
        return start.strftime("%B %Y")
    elif period == "year":
        return start.strftime("%Y")
    else:  # custom
        return f"{start.strftime('%B %d, %Y')} to {end.strftime('%B %d, %Y')}"
