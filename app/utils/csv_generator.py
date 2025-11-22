"""
CSV Generation Utilities

Utilities for generating CSV reports.
"""
from typing import Dict, Any, List
from io import StringIO
from datetime import datetime
from decimal import Decimal
import csv


def generate_opd_report_csv(context: Dict[str, Any]) -> str:
    """Generate CSV report for OPD visits."""
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["OPD DETAILED REPORT"])
    writer.writerow([f"Period: {context['start_date']} to {context['end_date']}"])
    writer.writerow([f"Generated: {context['report_date'].strftime('%Y-%m-%d %H:%M')}"])
    writer.writerow([])
    
    # Summary
    writer.writerow(["SUMMARY"])
    writer.writerow(["Total Visits", context['total_visits']])
    writer.writerow(["Active Visits", context['active_visits']])
    writer.writerow(["Completed Visits", context['completed_visits']])
    writer.writerow(["Cancelled Visits", context['cancelled_visits']])
    writer.writerow(["Total Revenue", f"GHS {context['total_revenue']:.2f}"])
    writer.writerow(["Total Encounters", context['total_encounters']])
    writer.writerow([])
    
    # Payment Breakdown
    writer.writerow(["PAYMENT BREAKDOWN"])
    writer.writerow(["Payment Status", "Count", "Total (GHS)"])
    for status, data in context['payment_breakdown'].items():
        writer.writerow([status.title(), data['count'], f"{data['total']:.2f}"])
    writer.writerow([])
    
    # Visit Type Breakdown
    writer.writerow(["VISIT TYPE BREAKDOWN"])
    writer.writerow(["Visit Type", "Count"])
    for vtype, count in context['visit_type_breakdown'].items():
        writer.writerow([vtype.title(), count])
    writer.writerow([])
    
    # Gender Distribution
    gender_breakdown = context.get('gender_breakdown', {})
    if gender_breakdown:
        writer.writerow(["GENDER DISTRIBUTION"])
        writer.writerow(["Gender", "Count", "Percentage"])
        total_patients = sum(gender_breakdown.values())
        for gender, count in gender_breakdown.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            writer.writerow([gender or 'Unknown', count, f"{percentage:.1f}%"])
        writer.writerow([])
    
    # Age Distribution
    age_groups = context.get('age_groups', {})
    if age_groups:
        writer.writerow(["AGE DISTRIBUTION"])
        writer.writerow(["Age Group", "Count", "Percentage"])
        total_patients = sum(age_groups.values())
        for age_group, count in age_groups.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            age_label = f"{age_group} years" if age_group != "65+" else "65+ years"
            writer.writerow([age_label, count, f"{percentage:.1f}%"])
        writer.writerow([])
    
    # Detailed Visits
    writer.writerow(["DETAILED VISITS"])
    writer.writerow([
        "OPD Number", "Patient Name", "Visit Date", "Status", 
        "Payment Status", "Visit Type", "Total Charges", "Encounters"
    ])
    for visit in context['visits']:
        writer.writerow([
            visit.opd_number,
            f"{visit.patient.first_name} {visit.patient.last_name}",
            visit.visit_date.strftime('%Y-%m-%d'),
            visit.status.value,
            visit.payment_status,
            visit.visit_type or "N/A",
            f"{visit.total_charges:.2f}",
            len(visit.encounters)
        ])
    
    return output.getvalue()


def generate_ipd_report_csv(context: Dict[str, Any]) -> str:
    """Generate CSV report for IPD admissions."""
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["IPD DETAILED REPORT"])
    writer.writerow([f"Period: {context['start_date']} to {context['end_date']}"])
    writer.writerow([f"Generated: {context['report_date'].strftime('%Y-%m-%d %H:%M')}"])
    writer.writerow([])
    
    # Summary
    writer.writerow(["SUMMARY"])
    writer.writerow(["Total Admissions", context['total_admissions']])
    writer.writerow(["Active Admissions", context['active_admissions']])
    writer.writerow(["Discharged Admissions", context['discharged_admissions']])
    writer.writerow(["Transferred Admissions", context['transferred_admissions']])
    writer.writerow(["Average Length of Stay", f"{context['avg_los']:.1f} days"])
    writer.writerow(["Total Revenue", f"GHS {context['total_revenue']:.2f}"])
    writer.writerow(["Total Encounters", context['total_encounters']])
    writer.writerow([])
    
    # Ward Breakdown
    writer.writerow(["WARD BREAKDOWN"])
    writer.writerow(["Ward", "Count", "Avg LOS"])
    for ward, data in context['ward_breakdown'].items():
        avg_los = data['total_los'] / data['count'] if data['count'] > 0 else 0
        writer.writerow([ward, data['count'], f"{avg_los:.1f}"])
    writer.writerow([])
    
    # Discharge Status Breakdown
    if context['discharge_status_breakdown']:
        writer.writerow(["DISCHARGE STATUS BREAKDOWN"])
        writer.writerow(["Status", "Count"])
        for status, count in context['discharge_status_breakdown'].items():
            writer.writerow([status.title(), count])
        writer.writerow([])
    
    # Gender Distribution
    gender_breakdown = context.get('gender_breakdown', {})
    if gender_breakdown:
        writer.writerow(["GENDER DISTRIBUTION"])
        writer.writerow(["Gender", "Count", "Percentage"])
        total_patients = sum(gender_breakdown.values())
        for gender, count in gender_breakdown.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            writer.writerow([gender or 'Unknown', count, f"{percentage:.1f}%"])
        writer.writerow([])
    
    # Age Distribution
    age_groups = context.get('age_groups', {})
    if age_groups:
        writer.writerow(["AGE DISTRIBUTION"])
        writer.writerow(["Age Group", "Count", "Percentage"])
        total_patients = sum(age_groups.values())
        for age_group, count in age_groups.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            age_label = f"{age_group} years" if age_group != "65+" else "65+ years"
            writer.writerow([age_label, count, f"{percentage:.1f}%"])
        writer.writerow([])
    
    # Detailed Admissions
    writer.writerow(["DETAILED ADMISSIONS"])
    writer.writerow([
        "Admission Number", "Patient Name", "Ward", "Bed", 
        "Admission Date", "Discharge Date", "Status", "LOS (days)", "Revenue"
    ])
    for admission in context['admissions']:
        if admission.discharge_date:
            los = (admission.discharge_date - admission.admission_date).days
        else:
            los = (datetime.now().date() - admission.admission_date).days
        
        revenue = admission.invoice.total_amount if admission.invoice else Decimal('0.00')
        writer.writerow([
            admission.admission_number,
            f"{admission.patient.first_name} {admission.patient.last_name}",
            admission.ward.name if admission.ward else "N/A",
            admission.bed.bed_number if admission.bed else "N/A",
            admission.admission_date.strftime('%Y-%m-%d'),
            admission.discharge_date.strftime('%Y-%m-%d') if admission.discharge_date else "N/A",
            admission.status.value,
            los,
            f"{revenue:.2f}"
        ])
    
    return output.getvalue()


def generate_disease_report_csv(context: Dict[str, Any]) -> str:
    """Generate CSV report for disease encounter statistics."""
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["DISEASE ENCOUNTER REPORT"])
    
    # Period information
    filters = context.get('filters', {})
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    search = filters.get('search', '')
    
    period_text = "All Time"
    if start_date and end_date:
        period_text = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    elif start_date:
        period_text = f"From {start_date.strftime('%Y-%m-%d')}"
    elif end_date:
        period_text = f"Until {end_date.strftime('%Y-%m-%d')}"
    
    writer.writerow([f"Period: {period_text}"])
    if search:
        writer.writerow([f"Search: {search}"])
    writer.writerow([f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"])
    writer.writerow([])
    
    # Summary statistics
    totals = context.get('totals', {})
    writer.writerow(["SUMMARY STATISTICS"])
    writer.writerow(["Total Encounter Diagnoses", totals.get('encounters', 0)])
    writer.writerow(["Marked as Primary Diagnosis", totals.get('primary', 0)])
    writer.writerow(["Unique Diseases", totals.get('diseases', 0)])
    writer.writerow([])
    
    # Gender Distribution
    gender_breakdown = context.get('gender_breakdown', {})
    if gender_breakdown:
        writer.writerow(["GENDER DISTRIBUTION"])
        writer.writerow(["Gender", "Count", "Percentage"])
        total_patients = sum(gender_breakdown.values())
        for gender, count in gender_breakdown.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            writer.writerow([gender or 'Unknown', count, f"{percentage:.1f}%"])
        writer.writerow([])
    
    # Age Distribution
    age_groups = context.get('age_groups', {})
    if age_groups:
        writer.writerow(["AGE DISTRIBUTION"])
        writer.writerow(["Age Group", "Count", "Percentage"])
        total_patients = sum(age_groups.values())
        for age_group, count in age_groups.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            age_label = f"{age_group} years" if age_group != "65+" else "65+ years"
            writer.writerow([age_label, count, f"{percentage:.1f}%"])
        writer.writerow([])
    
    # Disease breakdown
    stats = context.get('stats', [])
    if stats:
        writer.writerow(["DISEASE BREAKDOWN"])
        writer.writerow([
            "Disease", "Code", "Total Encounters", "Primary Count", 
            "Primary %", "First Recorded", "Last Recorded"
        ])
        
        for item in stats:
            first_recorded = item.get('first_recorded')
            last_recorded = item.get('last_recorded')
            writer.writerow([
                item.get('name', 'N/A'),
                item.get('code', '—'),
                item.get('encounter_count', 0),
                item.get('primary_count', 0),
                f"{item.get('primary_ratio', 0):.1f}%",
                first_recorded.strftime('%Y-%m-%d') if first_recorded else 'N/A',
                last_recorded.strftime('%Y-%m-%d') if last_recorded else 'N/A'
            ])
    
    return output.getvalue()


def generate_financial_report_csv(context: Dict[str, Any]) -> str:
    """Generate detailed CSV report for financial report."""
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    hospital_settings = context.get('hospital_settings')
    if hospital_settings:
        writer.writerow([hospital_settings.hospital_name or "Hospital"])
        if hospital_settings.hospital_address:
            writer.writerow([hospital_settings.hospital_address])
    else:
        writer.writerow(["HOSPITAL"])
    
    writer.writerow(["FINANCIAL REPORT"])
    writer.writerow([])
    
    # Period
    writer.writerow(["Period:", f"{context['start_date']} to {context['end_date']}"])
    report_date = context.get('report_date', datetime.now())
    if isinstance(report_date, datetime):
        report_date_str = report_date.strftime('%Y-%m-%d %H:%M')
    else:
        report_date_str = str(report_date)
    writer.writerow(["Report Generated:", report_date_str])
    writer.writerow([])
    
    # Summary Statistics
    writer.writerow(["SUMMARY STATISTICS"])
    writer.writerow(["Total Revenue", f"GHS {float(context.get('total_revenue', Decimal('0.00'))):,.2f}"])
    writer.writerow(["Total Paid", f"GHS {float(context.get('total_paid', Decimal('0.00'))):,.2f}"])
    writer.writerow(["Outstanding Balance", f"GHS {float(context.get('total_outstanding', Decimal('0.00'))):,.2f}"])
    writer.writerow(["Total Invoices", len(context.get('invoices', []))])
    writer.writerow(["Total Charges", len(context.get('charges', []))])
    writer.writerow(["Total Payments", len(context.get('payments', []))])
    writer.writerow([])
    
    # Service Type Breakdown
    service_breakdown = context.get('service_breakdown', {})
    if service_breakdown:
        writer.writerow(["REVENUE BY SERVICE TYPE"])
        writer.writerow(["Service Type", "Count", "Total Revenue (GHS)", "Paid (GHS)", "Outstanding (GHS)"])
        for service, data in sorted(service_breakdown.items(), key=lambda x: x[1]['total'], reverse=True):
            outstanding = data['total'] - data['paid']
            writer.writerow([
                service.replace('_', ' ').title(),
                data['count'],
                f"{float(data['total']):,.2f}",
                f"{float(data['paid']):,.2f}",
                f"{float(outstanding):,.2f}"
            ])
        writer.writerow([])
    
    # Payment Mechanism Breakdown
    payment_breakdown = context.get('payment_breakdown', {})
    if payment_breakdown:
        writer.writerow(["REVENUE BY PAYMENT MECHANISM"])
        writer.writerow(["Payment Mechanism", "Count", "Total Revenue (GHS)", "Paid (GHS)", "Outstanding (GHS)"])
        for mechanism, data in sorted(payment_breakdown.items(), key=lambda x: x[1]['total'], reverse=True):
            outstanding = data['total'] - data['paid']
            writer.writerow([
                mechanism.replace('_', ' ').title(),
                data['count'],
                f"{float(data['total']):,.2f}",
                f"{float(data['paid']):,.2f}",
                f"{float(outstanding):,.2f}"
            ])
        writer.writerow([])
    
    # Detailed Invoices
    invoices_detailed = context.get('invoices_detailed', [])
    if invoices_detailed:
        writer.writerow(["DETAILED INVOICES"])
        writer.writerow([
            "Invoice #", "Date", "Patient Name", "Patient #", "Service Types", 
            "Total (GHS)", "Paid (GHS)", "Balance (GHS)", "Status"
        ])
        for inv_detail in invoices_detailed:
            invoice = inv_detail['invoice']
            patient = inv_detail.get('patient')
            patient_name = f"{patient.first_name} {patient.last_name}" if patient else "N/A"
            patient_number = patient.patient_number if patient else "N/A"
            
            # Get service types from charges
            charges = inv_detail.get('charges', [])
            service_types = [c.charge_type.value.replace('_', ' ').title() for c in charges]
            service_type_str = ', '.join(service_types) if service_types else 'N/A'
            
            invoice_date = invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else 'N/A'
            total = float(invoice.total_amount)
            paid = float(invoice.paid_amount or Decimal('0.00'))
            balance = float(invoice.balance or Decimal('0.00'))
            status = "Paid" if balance <= 0 else "Partial" if paid > 0 else "Unpaid"
            
            writer.writerow([
                invoice.invoice_number or f"#{invoice.id}",
                invoice_date,
                patient_name,
                patient_number,
                service_type_str,
                f"{total:,.2f}",
                f"{paid:,.2f}",
                f"{balance:,.2f}",
                status
            ])
    
    return output.getvalue()


def generate_pharmacy_report_csv(context: Dict[str, Any]) -> str:
    """Generate CSV report for pharmacy report."""
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    hospital_settings = context.get('hospital_settings')
    if hospital_settings:
        writer.writerow([hospital_settings.hospital_name or "Hospital"])
        if hospital_settings.hospital_address:
            writer.writerow([hospital_settings.hospital_address])
    else:
        writer.writerow(["HOSPITAL"])
    
    writer.writerow(["PHARMACY REPORT"])
    writer.writerow([])
    
    # Period
    writer.writerow(["Period:", f"{context['start_date']} to {context['end_date']}"])
    report_date = context.get('report_date', datetime.now())
    if isinstance(report_date, datetime):
        report_date_str = report_date.strftime('%Y-%m-%d %H:%M')
    else:
        report_date_str = str(report_date)
    writer.writerow(["Report Generated:", report_date_str])
    writer.writerow([])
    
    # Summary
    writer.writerow(["Total Prescriptions", context.get('total_prescriptions', 0)])
    writer.writerow(["Total Revenue", f"GHS {float(context.get('total_revenue', Decimal('0.00'))):,.2f}"])
    writer.writerow([])
    
    # Top Medications
    top_medications = context.get('top_medications', [])
    if top_medications:
        writer.writerow(["TOP PRESCRIBED MEDICATIONS"])
        writer.writerow(["Rank", "Medication", "Count"])
        for idx, (med, count) in enumerate(top_medications[:20], 1):
            writer.writerow([idx, med, count])
        writer.writerow([])
    
    # Gender Distribution
    gender_breakdown = context.get('gender_breakdown', {})
    if gender_breakdown:
        writer.writerow(["GENDER DISTRIBUTION"])
        writer.writerow(["Gender", "Count", "Percentage"])
        total_patients = sum(gender_breakdown.values())
        for gender, count in gender_breakdown.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            writer.writerow([gender or 'Unknown', count, f"{percentage:.1f}%"])
        writer.writerow([])
    
    # Age Distribution
    age_groups = context.get('age_groups', {})
    if age_groups:
        writer.writerow(["AGE DISTRIBUTION"])
        writer.writerow(["Age Group", "Count", "Percentage"])
        total_patients = sum(age_groups.values())
        for age_group, count in age_groups.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            age_label = f"{age_group} years" if age_group != "65+" else "65+ years"
            writer.writerow([age_label, count, f"{percentage:.1f}%"])
        writer.writerow([])
    
    return output.getvalue()


def generate_lab_report_csv(context: Dict[str, Any]) -> str:
    """Generate CSV report for lab report."""
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    hospital_settings = context.get('hospital_settings')
    if hospital_settings:
        writer.writerow([hospital_settings.hospital_name or "Hospital"])
        if hospital_settings.hospital_address:
            writer.writerow([hospital_settings.hospital_address])
    else:
        writer.writerow(["HOSPITAL"])
    
    writer.writerow(["LAB REPORT"])
    writer.writerow([])
    
    # Period
    writer.writerow(["Period:", f"{context['start_date']} to {context['end_date']}"])
    report_date = context.get('report_date', datetime.now())
    if isinstance(report_date, datetime):
        report_date_str = report_date.strftime('%Y-%m-%d %H:%M')
    else:
        report_date_str = str(report_date)
    writer.writerow(["Report Generated:", report_date_str])
    writer.writerow([])
    
    # Summary
    writer.writerow(["Total Orders", context.get('total_orders', 0)])
    writer.writerow(["Total Revenue", f"GHS {float(context.get('total_revenue', Decimal('0.00'))):,.2f}"])
    writer.writerow([])
    
    # Test Frequency
    test_counts = context.get('test_counts', {})
    if test_counts:
        writer.writerow(["TEST FREQUENCY"])
        writer.writerow(["Test Name", "Count"])
        for test_name, count in sorted(test_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
            writer.writerow([test_name, count])
        writer.writerow([])
    
    # Gender Distribution
    gender_breakdown = context.get('gender_breakdown', {})
    if gender_breakdown:
        writer.writerow(["GENDER DISTRIBUTION"])
        writer.writerow(["Gender", "Count", "Percentage"])
        total_patients = sum(gender_breakdown.values())
        for gender, count in gender_breakdown.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            writer.writerow([gender or 'Unknown', count, f"{percentage:.1f}%"])
        writer.writerow([])
    
    # Age Distribution
    age_groups = context.get('age_groups', {})
    if age_groups:
        writer.writerow(["AGE DISTRIBUTION"])
        writer.writerow(["Age Group", "Count", "Percentage"])
        total_patients = sum(age_groups.values())
        for age_group, count in age_groups.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            age_label = f"{age_group} years" if age_group != "65+" else "65+ years"
            writer.writerow([age_label, count, f"{percentage:.1f}%"])
        writer.writerow([])
    
    return output.getvalue()


def generate_radiology_report_csv(context: Dict[str, Any]) -> str:
    """Generate CSV report for radiology report."""
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    hospital_settings = context.get('hospital_settings')
    if hospital_settings:
        writer.writerow([hospital_settings.hospital_name or "Hospital"])
        if hospital_settings.hospital_address:
            writer.writerow([hospital_settings.hospital_address])
    else:
        writer.writerow(["HOSPITAL"])
    
    writer.writerow(["RADIOLOGY REPORT"])
    writer.writerow([])
    
    # Period
    writer.writerow(["Period:", f"{context['start_date']} to {context['end_date']}"])
    report_date = context.get('report_date', datetime.now())
    if isinstance(report_date, datetime):
        report_date_str = report_date.strftime('%Y-%m-%d %H:%M')
    else:
        report_date_str = str(report_date)
    writer.writerow(["Report Generated:", report_date_str])
    writer.writerow([])
    
    # Summary
    writer.writerow(["Total Orders", context.get('total_orders', 0)])
    writer.writerow(["Total Revenue", f"GHS {float(context.get('total_revenue', Decimal('0.00'))):,.2f}"])
    writer.writerow([])
    
    # Study Type Frequency
    study_counts = context.get('study_counts', {})
    if study_counts:
        writer.writerow(["STUDY TYPE FREQUENCY"])
        writer.writerow(["Study Type", "Count"])
        for study_type, count in sorted(study_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
            writer.writerow([study_type, count])
        writer.writerow([])
    
    # Gender Distribution
    gender_breakdown = context.get('gender_breakdown', {})
    if gender_breakdown:
        writer.writerow(["GENDER DISTRIBUTION"])
        writer.writerow(["Gender", "Count", "Percentage"])
        total_patients = sum(gender_breakdown.values())
        for gender, count in gender_breakdown.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            writer.writerow([gender or 'Unknown', count, f"{percentage:.1f}%"])
        writer.writerow([])
    
    # Age Distribution
    age_groups = context.get('age_groups', {})
    if age_groups:
        writer.writerow(["AGE DISTRIBUTION"])
        writer.writerow(["Age Group", "Count", "Percentage"])
        total_patients = sum(age_groups.values())
        for age_group, count in age_groups.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            age_label = f"{age_group} years" if age_group != "65+" else "65+ years"
            writer.writerow([age_label, count, f"{percentage:.1f}%"])
        writer.writerow([])
    
    return output.getvalue()
