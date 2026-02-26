"""
PDF Generation Utilities

Utilities for generating PDF reports using reportlab or weasyprint.
"""
from typing import Dict, Any
from io import BytesIO
from datetime import datetime
from decimal import Decimal

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def generate_admission_report_pdf(context: Dict[str, Any]) -> bytes:
    """Generate PDF report for an admission."""
    if not REPORTLAB_AVAILABLE:
        # Fallback: return HTML as text
        return b"PDF generation requires reportlab. Install with: pip install reportlab"
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    story.append(Paragraph("ADMISSION REPORT", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    admission = context['admission']
    patient = context['patient']
    
    # Patient Information
    story.append(Paragraph("<b>Patient Information</b>", styles['Heading2']))
    patient_data = [
        ['Patient Name:', f"{patient.first_name} {patient.last_name}"],
        ['Patient Number:', patient.patient_number or 'N/A'],
        ['Date of Birth:', patient.date_of_birth.strftime('%Y-%m-%d')],
        ['Gender:', patient.gender],
        ['Phone:', patient.phone_number or 'N/A'],
    ]
    patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Admission Information
    story.append(Paragraph("<b>Admission Information</b>", styles['Heading2']))
    admission_data = [
        ['Admission Number:', admission.admission_number],
        ['Admission Date:', admission.admission_date.strftime('%Y-%m-%d %H:%M')],
        ['Discharge Date:', admission.discharge_date.strftime('%Y-%m-%d %H:%M') if admission.discharge_date else 'N/A'],
        ['Ward:', admission.ward.name],
        ['Bed:', admission.bed.bed_number],
        ['Status:', admission.status.value.title()],
        ['Length of Stay:', f"{context['length_of_stay']} days"],
    ]
    if admission.admission_reason:
        admission_data.append(['Reason:', admission.admission_reason])
    if admission.diagnosis:
        admission_data.append(['Diagnosis:', admission.diagnosis])
    
    admission_table = Table(admission_data, colWidths=[2*inch, 4*inch])
    admission_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(admission_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Footer
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_financial_report_pdf(context: Dict[str, Any]) -> bytes:
    """Generate detailed PDF report for financial report."""
    if not REPORTLAB_AVAILABLE:
        return b"PDF generation requires reportlab. Install with: pip install reportlab"
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Hospital header
    hospital_settings = context.get('hospital_settings')
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    if hospital_settings:
        story.append(Paragraph(hospital_settings.hospital_name or "Hospital", title_style))
        if hospital_settings.hospital_address:
            story.append(Paragraph(hospital_settings.hospital_address, styles['Normal']))
    else:
        story.append(Paragraph("HOSPITAL", title_style))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("FINANCIAL REPORT", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Period and summary
    story.append(Paragraph(f"<b>Period:</b> {context['start_date']} to {context['end_date']}", styles['Normal']))
    story.append(Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Summary Statistics
    story.append(Paragraph("<b>Summary Statistics</b>", styles['Heading2']))
    summary_data = [
        ['Total Revenue:', f"GHS {float(context.get('total_revenue', Decimal('0.00'))):,.2f}"],
        ['Total Paid:', f"GHS {float(context.get('total_paid', Decimal('0.00'))):,.2f}"],
        ['Outstanding Balance:', f"GHS {float(context.get('total_outstanding', Decimal('0.00'))):,.2f}"],
        ['Total Invoices:', str(len(context.get('invoices', [])))],
        ['Total Charges:', str(len(context.get('charges', [])))],
        ['Total Payments:', str(len(context.get('payments', [])))],
    ]
    summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Service Type Breakdown
    service_breakdown = context.get('service_breakdown', {})
    if service_breakdown:
        story.append(Paragraph("<b>Revenue by Service Type</b>", styles['Heading2']))
        service_data = [['Service Type', 'Count', 'Total Revenue (GHS)', 'Paid (GHS)', 'Outstanding (GHS)']]
        for service, data in sorted(service_breakdown.items(), key=lambda x: x[1]['total'], reverse=True):
            outstanding = data['total'] - data['paid']
            service_data.append([
                service.replace('_', ' ').title(),
                str(data['count']),
                f"{float(data['total']):,.2f}",
                f"{float(data['paid']):,.2f}",
                f"{float(outstanding):,.2f}"
            ])
        service_table = Table(service_data, colWidths=[2*inch, 0.8*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        service_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(service_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Payment Mechanism Breakdown
    payment_breakdown = context.get('payment_breakdown', {})
    if payment_breakdown:
        story.append(Paragraph("<b>Revenue by Payment Mechanism</b>", styles['Heading2']))
        payment_data = [['Payment Mechanism', 'Count', 'Total Revenue (GHS)', 'Paid (GHS)', 'Outstanding (GHS)']]
        for mechanism, data in sorted(payment_breakdown.items(), key=lambda x: x[1]['total'], reverse=True):
            outstanding = data['total'] - data['paid']
            payment_data.append([
                mechanism.replace('_', ' ').title(),
                str(data['count']),
                f"{float(data['total']):,.2f}",
                f"{float(data['paid']):,.2f}",
                f"{float(outstanding):,.2f}"
            ])
        payment_table = Table(payment_data, colWidths=[2*inch, 0.8*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(payment_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Detailed Invoices (first 100 for PDF)
    invoices_detailed = context.get('invoices_detailed', [])
    if invoices_detailed:
        story.append(Paragraph("<b>Detailed Invoices</b>", styles['Heading2']))
        invoice_data = [['Invoice #', 'Date', 'Patient', 'Patient #', 'Service Type', 'Total (GHS)', 'Paid (GHS)', 'Balance (GHS)', 'Status']]
        
        for inv_detail in invoices_detailed[:100]:  # Limit to first 100 for PDF
            invoice = inv_detail['invoice']
            patient = inv_detail.get('patient')
            patient_name = f"{patient.first_name} {patient.last_name}" if patient else "N/A"
            patient_number = patient.patient_number if patient else "N/A"
            
            # Get primary service type from charges
            charges = inv_detail.get('charges', [])
            service_types = [c.charge_type.value.replace('_', ' ').title() for c in charges[:2]]  # First 2 service types
            service_type_str = ', '.join(service_types) if service_types else 'N/A'
            if len(charges) > 2:
                service_type_str += f" (+{len(charges)-2} more)"
            
            invoice_date = invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else 'N/A'
            total = float(invoice.total_amount)
            paid = float(invoice.paid_amount or Decimal('0.00'))
            balance = float(invoice.balance or Decimal('0.00'))
            status = "Paid" if balance <= 0 else "Partial" if paid > 0 else "Unpaid"
            
            invoice_data.append([
                invoice.invoice_number or f"#{invoice.id}",
                invoice_date,
                patient_name[:25],  # Truncate long names
                patient_number[:15] if patient_number else 'N/A',
                service_type_str[:30],  # Truncate
                f"{total:,.2f}",
                f"{paid:,.2f}",
                f"{balance:,.2f}",
                status
            ])
        
        invoice_table = Table(invoice_data, colWidths=[0.8*inch, 0.7*inch, 1*inch, 0.8*inch, 1*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.6*inch])
        invoice_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (5, 0), (7, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(invoice_table)
        if len(invoices_detailed) > 100:
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph(f"<i>Note: Showing first 100 of {len(invoices_detailed)} invoices. Use Excel/CSV export for complete data.</i>", styles['Normal']))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Footer
    report_date = context.get('report_date', datetime.now())
    if isinstance(report_date, datetime):
        report_date_str = report_date.strftime('%Y-%m-%d %H:%M')
    else:
        report_date_str = str(report_date)
    
    current_user = context.get('current_user')
    generated_by = current_user.full_name if current_user and hasattr(current_user, 'full_name') else (current_user.username if current_user else 'LHIMS Administrator')
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceBefore=20
    )
    story.append(Paragraph(f"Report Generated: {report_date_str} | Generated by: {generated_by}", footer_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_demographics_report_pdf(context: Dict[str, Any]) -> bytes:
    """Generate PDF report for patient demographics."""
    if not REPORTLAB_AVAILABLE:
        return b"PDF generation requires reportlab. Install with: pip install reportlab"
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    story.append(Paragraph("Patient Demographics Report", title_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Dashboard header
    dashboard_style = ParagraphStyle(
        'Dashboard',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        alignment=TA_LEFT
    )
    story.append(Paragraph("Dashboard", dashboard_style))
    story.append(Paragraph("Demographics Report", dashboard_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Filters section
    story.append(Paragraph("<b>Filters</b>", styles['Heading3']))
    start_date = context.get('start_date', 'N/A')
    end_date = context.get('end_date', 'N/A')
    
    # Format dates to DD/MM/YYYY if they're in YYYY-MM-DD format
    def format_date(date_str):
        if date_str == 'N/A' or not date_str:
            return date_str
        try:
            # Try parsing YYYY-MM-DD format
            if '-' in date_str and len(date_str) == 10:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                return dt.strftime('%d/%m/%Y')
        except:
            pass
        return date_str
    
    story.append(Paragraph(f"Start Date: {format_date(start_date)}", styles['Normal']))
    story.append(Paragraph(f"End Date: {format_date(end_date)}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Total Patients
    total_patients = context.get('total_patients', 0)
    story.append(Paragraph(f"<b>{total_patients}</b>", styles['Heading2']))
    story.append(Paragraph("Total Patients", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Gender Distribution
    story.append(Paragraph("<b>Gender Distribution</b>", styles['Heading3']))
    gender_breakdown = context.get('gender_breakdown', {})
    gender_data = [['Gender', 'Count', 'Percentage']]
    
    for gender, count in gender_breakdown.items():
        percentage = (count / total_patients * 100) if total_patients > 0 else 0
        gender_data.append([
            gender or 'Unknown',
            str(count),
            f"{percentage:.1f}%"
        ])
    
    gender_table = Table(gender_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
    gender_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(gender_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Age Distribution
    story.append(Paragraph("<b>Age Distribution</b>", styles['Heading3']))
    age_groups = context.get('age_groups', {})
    age_data = [['Age Group', 'Count', 'Percentage']]
    
    for age_group, count in age_groups.items():
        percentage = (count / total_patients * 100) if total_patients > 0 else 0
        age_label = f"{age_group} years" if age_group != "65+" else "65+ years"
        age_data.append([
            age_label,
            str(count),
            f"{percentage:.1f}%"
        ])
    
    age_table = Table(age_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
    age_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(age_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Payment Mechanism Distribution
    story.append(Paragraph("<b>Payment Mechanism Distribution</b>", styles['Heading3']))
    payment_breakdown = context.get('payment_breakdown', {})
    payment_data = [['Payment Mechanism', 'Count', 'Percentage', 'Visual']]
    
    for mechanism, count in payment_breakdown.items():
        percentage = (count / total_patients * 100) if total_patients > 0 else 0
        bar_length = int(percentage / 2)
        visual_bar = '█' * bar_length if bar_length > 0 else ''
        # Format mechanism name
        mechanism_display = mechanism.replace('_', ' ').title()
        payment_data.append([
            mechanism_display,
            str(count),
            f"{percentage:.1f}%",
            visual_bar
        ])
    
    payment_table = Table(payment_data, colWidths=[2.5*inch, 1*inch, 1.5*inch, 2*inch])
    payment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(payment_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Footer
    report_date = context.get('report_date', datetime.now())
    if isinstance(report_date, datetime):
        report_date_str = report_date.strftime('%Y-%m-%d %H:%M')
    else:
        report_date_str = str(report_date)
    
    current_user = context.get('current_user')
    generated_by = current_user.full_name if current_user and hasattr(current_user, 'full_name') else (current_user.username if current_user else 'LHIMS Administrator')
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceBefore=20
    )
    story.append(Paragraph(f"Report Generated: {report_date_str} | Generated by: {generated_by}", footer_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_income_statement_pdf(context: Dict[str, Any]) -> bytes:
    """Generate PDF report for income statement."""
    if not REPORTLAB_AVAILABLE:
        return b"PDF generation requires reportlab. Install with: pip install reportlab"
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    hospital_settings = context.get('hospital_settings')
    if hospital_settings:
        story.append(Paragraph(hospital_settings.hospital_name or "Hospital", title_style))
        if hospital_settings.hospital_address:
            story.append(Paragraph(hospital_settings.hospital_address, styles['Normal']))
    else:
        story.append(Paragraph("HOSPITAL", title_style))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("INCOME STATEMENT (PROFIT & LOSS)", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Period
    period_label = context.get('period_label', '')
    story.append(Paragraph(f"<b>Period:</b> {period_label}", styles['Normal']))
    report_date = context.get('report_date', datetime.now())
    if isinstance(report_date, datetime):
        story.append(Paragraph(f"<b>Report Generated:</b> {report_date.strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Revenue Section
    story.append(Paragraph("<b><u>REVENUE</u></b>", styles['Heading2']))
    revenue_data = [['Description', 'Amount (GHS)']]
    revenue_by_service = context.get('revenue_by_service', {})
    for service_type, amount in revenue_by_service.items():
        revenue_data.append([
            service_type.replace('_', ' ').title(),
            f"{float(amount):.2f}"
        ])
    
    total_revenue = float(context.get('total_revenue', Decimal('0.00')))
    revenue_data.append(['<b>TOTAL REVENUE</b>', f"<b>{total_revenue:.2f}</b>"])
    
    revenue_table = Table(revenue_data, colWidths=[4*inch, 2*inch])
    revenue_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgreen),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(revenue_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Expenses Section
    story.append(Paragraph("<b><u>EXPENSES</u></b>", styles['Heading2']))
    expenses_data = [['Category', 'Amount (GHS)']]
    expenses_by_category = context.get('expenses_by_category', {})
    for category, amount in expenses_by_category.items():
        expenses_data.append([
            category.replace('_', ' ').title(),
            f"{float(amount):.2f}"
        ])
    
    total_expenses = float(context.get('total_expenses', Decimal('0.00')))
    expenses_data.append(['<b>TOTAL EXPENSES</b>', f"<b>{total_expenses:.2f}</b>"])
    
    expenses_table = Table(expenses_data, colWidths=[4*inch, 2*inch])
    expenses_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightcoral),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(expenses_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Net Income Section
    net_income = float(context.get('net_income', Decimal('0.00')))
    profit_margin = float(context.get('profit_margin', Decimal('0.00')))
    
    net_income_data = [
        ['<b>NET INCOME</b>', f"<b>{net_income:.2f}</b>"],
        ['<b>Profit Margin</b>', f"<b>{profit_margin:.2f}%</b>"]
    ]
    
    net_income_table = Table(net_income_data, colWidths=[4*inch, 2*inch])
    net_income_color = colors.lightgreen if net_income >= 0 else colors.lightcoral
    net_income_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 0), (-1, -1), net_income_color),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(net_income_table)
    
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_expense_report_pdf(context: Dict[str, Any]) -> bytes:
    """Generate PDF report for expenses."""
    if not REPORTLAB_AVAILABLE:
        return b"PDF generation requires reportlab. Install with: pip install reportlab"
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    story.append(Paragraph("EXPENSE REPORT", title_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(f"Period: {context['start_date']} to {context['end_date']}", styles['Normal']))
    story.append(Paragraph(f"Total Expenses: GHS {context['total_expenses']:.2f}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_opd_report_pdf(context: Dict[str, Any]) -> bytes:
    """Generate PDF report for OPD visits."""
    if not REPORTLAB_AVAILABLE:
        return b"PDF generation requires reportlab. Install with: pip install reportlab"
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Hospital header
    hospital_settings = context.get('hospital_settings')
    if hospital_settings:
        story.append(Paragraph(hospital_settings.hospital_name or "Hospital", title_style))
        if hospital_settings.hospital_address:
            story.append(Paragraph(hospital_settings.hospital_address, styles['Normal']))
    else:
        story.append(Paragraph("HOSPITAL", title_style))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("OPD DETAILED REPORT", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Period and summary
    story.append(Paragraph(f"<b>Period:</b> {context['start_date']} to {context['end_date']}", styles['Normal']))
    story.append(Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Summary statistics
    story.append(Paragraph("<b>Summary Statistics</b>", styles['Heading2']))
    summary_data = [
        ['Total Visits:', str(context.get('total_visits', 0))],
        ['Active Visits:', str(context.get('active_visits', 0))],
        ['Completed Visits:', str(context.get('completed_visits', 0))],
        ['Cancelled Visits:', str(context.get('cancelled_visits', 0))],
        ['Total Revenue:', f"GHS {float(context.get('total_revenue', Decimal('0.00'))):.2f}"],
        ['Total Encounters:', str(context.get('total_encounters', 0))],
    ]
    summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Payment breakdown
    payment_breakdown = context.get('payment_breakdown', {})
    if payment_breakdown:
        story.append(Paragraph("<b>Payment Breakdown</b>", styles['Heading2']))
        payment_data = [['Payment Status', 'Count', 'Total (GHS)']]
        for status, data in payment_breakdown.items():
            payment_data.append([
                status.title(),
                str(data.get('count', 0)),
                f"{float(data.get('total', Decimal('0.00'))):.2f}"
            ])
        payment_table = Table(payment_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(payment_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Patient Demographics - Gender Distribution
    gender_breakdown = context.get('gender_breakdown', {})
    if gender_breakdown:
        story.append(Paragraph("<b>Gender Distribution</b>", styles['Heading2']))
        total_patients = sum(gender_breakdown.values())
        gender_data = [['Gender', 'Count', 'Percentage']]
        for gender, count in gender_breakdown.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            gender_data.append([
                gender or 'Unknown',
                str(count),
                f"{percentage:.1f}%"
            ])
        gender_table = Table(gender_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        gender_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(gender_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Patient Demographics - Age Distribution
    age_groups = context.get('age_groups', {})
    if age_groups:
        story.append(Paragraph("<b>Age Distribution</b>", styles['Heading2']))
        total_patients = sum(age_groups.values())
        age_data = [['Age Group', 'Count', 'Percentage']]
        for age_group, count in age_groups.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            age_label = f"{age_group} years" if age_group != "65+" else "65+ years"
            age_data.append([
                age_label,
                str(count),
                f"{percentage:.1f}%"
            ])
        age_table = Table(age_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        age_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(age_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Detailed visits table
    visits = context.get('visits', [])
    if visits:
        story.append(Paragraph("<b>Detailed Visits</b>", styles['Heading2']))
        visits_data = [['OPD Number', 'Patient Name', 'Visit Date', 'Status', 'Payment Status', 'Visit Type', 'Total Charges', 'Encounters']]
        
        for visit in visits[:100]:  # Limit to first 100 for PDF
            patient_name = f"{visit.patient.first_name} {visit.patient.last_name}" if visit.patient else "N/A"
            visits_data.append([
                visit.opd_number,
                patient_name[:30],  # Truncate long names
                visit.visit_date.strftime('%Y-%m-%d') if visit.visit_date else 'N/A',
                visit.status.value.title() if hasattr(visit.status, 'value') else str(visit.status).title(),
                visit.payment_status.title() if visit.payment_status else 'N/A',
                visit.visit_type.title() if visit.visit_type else 'N/A',
                f"{float(visit.total_charges):.2f}",
                str(len(visit.encounters)) if visit.encounters else '0'
            ])
        
        visits_table = Table(visits_data, colWidths=[1*inch, 1.2*inch, 0.8*inch, 0.7*inch, 0.8*inch, 0.7*inch, 0.8*inch, 0.7*inch])
        visits_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (6, 0), (7, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(visits_table)
        if len(visits) > 100:
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph(f"<i>Note: Showing first 100 of {len(visits)} visits. Use Excel/CSV export for complete data.</i>", styles['Normal']))
    else:
        story.append(Paragraph("<i>No visits found for the selected criteria.</i>", styles['Normal']))
    
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_ipd_report_pdf(context: Dict[str, Any]) -> bytes:
    """Generate PDF report for IPD admissions."""
    if not REPORTLAB_AVAILABLE:
        return b"PDF generation requires reportlab. Install with: pip install reportlab"
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Hospital header
    hospital_settings = context.get('hospital_settings')
    if hospital_settings:
        story.append(Paragraph(hospital_settings.hospital_name or "Hospital", title_style))
        if hospital_settings.hospital_address:
            story.append(Paragraph(hospital_settings.hospital_address, styles['Normal']))
    else:
        story.append(Paragraph("HOSPITAL", title_style))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("IPD DETAILED REPORT", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Period and summary
    story.append(Paragraph(f"<b>Period:</b> {context['start_date']} to {context['end_date']}", styles['Normal']))
    story.append(Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Summary statistics
    story.append(Paragraph("<b>Summary Statistics</b>", styles['Heading2']))
    summary_data = [
        ['Total Admissions:', str(context.get('total_admissions', 0))],
        ['Active Admissions:', str(context.get('active_admissions', 0))],
        ['Discharged Admissions:', str(context.get('discharged_admissions', 0))],
        ['Transferred Admissions:', str(context.get('transferred_admissions', 0))],
        ['Average Length of Stay:', f"{context.get('avg_los', 0):.1f} days"],
        ['Total Revenue:', f"GHS {float(context.get('total_revenue', Decimal('0.00'))):.2f}"],
        ['Total Encounters:', str(context.get('total_encounters', 0))],
    ]
    summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Ward breakdown
    ward_breakdown = context.get('ward_breakdown', {})
    if ward_breakdown:
        story.append(Paragraph("<b>Ward Breakdown</b>", styles['Heading2']))
        ward_data = [['Ward', 'Count', 'Avg LOS (days)']]
        for ward_name, data in ward_breakdown.items():
            avg_los = data['total_los'] / data['count'] if data['count'] > 0 else 0
            ward_data.append([
                ward_name,
                str(data['count']),
                f"{avg_los:.1f}"
            ])
        ward_table = Table(ward_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
        ward_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(ward_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Patient Demographics - Gender Distribution
    gender_breakdown = context.get('gender_breakdown', {})
    if gender_breakdown:
        story.append(Paragraph("<b>Gender Distribution</b>", styles['Heading2']))
        total_patients = sum(gender_breakdown.values())
        gender_data = [['Gender', 'Count', 'Percentage']]
        for gender, count in gender_breakdown.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            gender_data.append([
                gender or 'Unknown',
                str(count),
                f"{percentage:.1f}%"
            ])
        gender_table = Table(gender_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        gender_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(gender_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Patient Demographics - Age Distribution
    age_groups = context.get('age_groups', {})
    if age_groups:
        story.append(Paragraph("<b>Age Distribution</b>", styles['Heading2']))
        total_patients = sum(age_groups.values())
        age_data = [['Age Group', 'Count', 'Percentage']]
        for age_group, count in age_groups.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            age_label = f"{age_group} years" if age_group != "65+" else "65+ years"
            age_data.append([
                age_label,
                str(count),
                f"{percentage:.1f}%"
            ])
        age_table = Table(age_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        age_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(age_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Detailed admissions table
    admissions = context.get('admissions', [])
    if admissions:
        story.append(Paragraph("<b>Detailed Admissions</b>", styles['Heading2']))
        admissions_data = [['Admission Number', 'Patient Name', 'Ward', 'Bed', 'Admission Date', 'Discharge Date', 'Status', 'LOS (days)', 'Revenue', 'Encounters']]
        
        report_date = context.get('report_date', datetime.now())
        if isinstance(report_date, datetime):
            report_date_obj = report_date.date()
        else:
            report_date_obj = datetime.now().date()
        
        for admission in admissions[:100]:  # Limit to first 100 for PDF
            patient_name = f"{admission.patient.first_name} {admission.patient.last_name}" if admission.patient else "N/A"
            ward_name = admission.ward.name if admission.ward else "N/A"
            bed_number = admission.bed.bed_number if admission.bed else "N/A"
            
            # Calculate LOS - convert datetime to date if needed
            admission_date = admission.admission_date.date() if isinstance(admission.admission_date, datetime) else admission.admission_date
            if admission.discharge_date:
                discharge_date = admission.discharge_date.date() if isinstance(admission.discharge_date, datetime) else admission.discharge_date
                los = (discharge_date - admission_date).days
            else:
                los = (report_date_obj - admission_date).days
            
            revenue = admission.invoice.total_amount if admission.invoice else Decimal('0.00')
            encounters_count = len(admission.encounters) if admission.encounters else 0
            
            admissions_data.append([
                admission.admission_number,
                patient_name[:25],  # Truncate long names
                ward_name[:20],
                bed_number[:15],
                admission.admission_date.strftime('%Y-%m-%d') if admission.admission_date else 'N/A',
                admission.discharge_date.strftime('%Y-%m-%d') if admission.discharge_date else 'N/A',
                admission.status.value.title() if hasattr(admission.status, 'value') else str(admission.status).title(),
                str(los),
                f"{float(revenue):.2f}",
                str(encounters_count)
            ])
        
        admissions_table = Table(admissions_data, colWidths=[1*inch, 1*inch, 0.7*inch, 0.6*inch, 0.7*inch, 0.7*inch, 0.6*inch, 0.5*inch, 0.6*inch, 0.5*inch])
        admissions_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (7, 0), (9, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(admissions_table)
        if len(admissions) > 100:
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph(f"<i>Note: Showing first 100 of {len(admissions)} admissions. Use Excel/CSV export for complete data.</i>", styles['Normal']))
    else:
        story.append(Paragraph("<i>No admissions found for the selected criteria.</i>", styles['Normal']))
    
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_disease_report_pdf(context: Dict[str, Any]) -> bytes:
    """Generate PDF report for disease encounter statistics."""
    if not REPORTLAB_AVAILABLE:
        return b"PDF generation requires reportlab. Install with: pip install reportlab"
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    story.append(Paragraph("DISEASE ENCOUNTER REPORT", title_style))
    story.append(Spacer(1, 0.2*inch))
    
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
    
    story.append(Paragraph(f"<b>Period:</b> {period_text}", styles['Normal']))
    if search:
        story.append(Paragraph(f"<b>Search:</b> {search}", styles['Normal']))
    story.append(Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Summary statistics
    totals = context.get('totals', {})
    story.append(Paragraph("<b>Summary Statistics</b>", styles['Heading2']))
    summary_data = [
        ['Total Encounter Diagnoses:', str(totals.get('encounters', 0))],
        ['Marked as Primary Diagnosis:', str(totals.get('primary', 0))],
        ['Unique Diseases:', str(totals.get('diseases', 0))],
    ]
    summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Patient Demographics - Gender Distribution
    gender_breakdown = context.get('gender_breakdown', {})
    if gender_breakdown:
        story.append(Paragraph("<b>Gender Distribution</b>", styles['Heading2']))
        total_patients = sum(gender_breakdown.values())
        gender_data = [['Gender', 'Count', 'Percentage']]
        for gender, count in gender_breakdown.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            gender_data.append([
                gender or 'Unknown',
                str(count),
                f"{percentage:.1f}%"
            ])
        gender_table = Table(gender_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        gender_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(gender_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Patient Demographics - Age Distribution
    age_groups = context.get('age_groups', {})
    if age_groups:
        story.append(Paragraph("<b>Age Distribution</b>", styles['Heading2']))
        total_patients = sum(age_groups.values())
        age_data = [['Age Group', 'Count', 'Percentage']]
        for age_group, count in age_groups.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            age_label = f"{age_group} years" if age_group != "65+" else "65+ years"
            age_data.append([
                age_label,
                str(count),
                f"{percentage:.1f}%"
            ])
        age_table = Table(age_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        age_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(age_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Disease breakdown table
    stats = context.get('stats', [])
    if stats:
        story.append(Paragraph("<b>Disease Encounter Breakdown</b>", styles['Heading2']))
        disease_data = [['Disease', 'Code', 'Total Encounters', 'Primary Count', 'Primary %', 'First Recorded', 'Last Recorded']]
        
        for item in stats:
            first_recorded = item.get('first_recorded')
            last_recorded = item.get('last_recorded')
            disease_data.append([
                item.get('name', 'N/A'),
                item.get('code', '—'),
                str(item.get('encounter_count', 0)),
                str(item.get('primary_count', 0)),
                f"{item.get('primary_ratio', 0):.1f}%",
                first_recorded.strftime('%Y-%m-%d') if first_recorded else 'N/A',
                last_recorded.strftime('%Y-%m-%d') if last_recorded else 'N/A'
            ])
        
        disease_table = Table(disease_data, colWidths=[1.5*inch, 0.8*inch, 1*inch, 1*inch, 0.8*inch, 1*inch, 1*inch])
        disease_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (4, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(disease_table)
    else:
        story.append(Paragraph("<i>No disease encounters found for the selected criteria.</i>", styles['Normal']))
    
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_dhims_disease_report_pdf(context: Dict[str, Any]) -> bytes:
    """Generate PDF report for DHIMS2 disease morbidity report."""
    if not REPORTLAB_AVAILABLE:
        return b"PDF generation requires reportlab. Install with: pip install reportlab"
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    # Title
    story.append(Paragraph("GHANA HEALTH SERVICE - DHIMS2 DISEASE MORBIDITY REPORT", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Period information
    filters = context.get('filters', {})
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    period = filters.get('period', '')
    
    period_text = "All Time"
    if start_date and end_date:
        period_text = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    elif period:
        period_text = f"Period: {period}"
    
    hospital_settings = context.get('hospital_settings', {})
    story.append(Paragraph(f"<b>Facility:</b> {hospital_settings.get('name', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"<b>Period:</b> {period_text}", styles['Normal']))
    story.append(Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Summary Statistics
    opd = context.get('opd', {})
    ipd = context.get('ipd', {})
    
    story.append(Paragraph("<b>SUMMARY STATISTICS</b>", styles['Heading2']))
    summary_data = [
        ['Category', 'OPD Cases', 'IPD Cases', 'Total'],
        ['Total Cases', str(opd.get('total_cases', 0)), str(ipd.get('total_cases', 0)), 
         str(opd.get('total_cases', 0) + ipd.get('total_cases', 0))],
        ['Male Cases', str(opd.get('male_cases', 0)), str(ipd.get('male_cases', 0)),
         str(opd.get('male_cases', 0) + ipd.get('male_cases', 0))],
        ['Female Cases', str(opd.get('female_cases', 0)), str(ipd.get('female_cases', 0)),
         str(opd.get('female_cases', 0) + ipd.get('female_cases', 0))],
        ['Unique Diseases', str(opd.get('unique_diseases', 0)), str(ipd.get('unique_diseases', 0)),
         str(opd.get('unique_diseases', 0) + ipd.get('unique_diseases', 0))],
    ]
    summary_table = Table(summary_data, colWidths=[1.8*inch, 1.3*inch, 1.3*inch, 1.3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Age Distribution
    story.append(Paragraph("<b>AGE DISTRIBUTION</b>", styles['Heading2']))
    age_groups = context.get('age_groups', [])
    opd_age = opd.get('age_summary', {})
    ipd_age = ipd.get('age_summary', {})
    
    age_data = [['Age Group', 'OPD', 'IPD', 'Total']]
    for ag in age_groups:
        opd_count = opd_age.get(ag, 0)
        ipd_count = ipd_age.get(ag, 0)
        age_label = ag.replace('_', ' ').upper() if ag != '65_plus' else '65+'
        age_data.append([age_label, str(opd_count), str(ipd_count), str(opd_count + ipd_count)])
    
    age_table = Table(age_data, colWidths=[1.8*inch, 1.3*inch, 1.3*inch, 1.3*inch])
    age_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    story.append(age_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Disease Category Breakdown
    category_breakdown = context.get('category_breakdown', [])
    if category_breakdown:
        story.append(Paragraph("<b>DISEASE CATEGORY BREAKDOWN</b>", styles['Heading2']))
        cat_data = [['Category', 'OPD', 'IPD', 'Total']]
        for cat in category_breakdown[:10]:
            cat_data.append([
                cat.get('name', 'Unknown').upper(),
                str(cat.get('opd', 0)),
                str(cat.get('ipd', 0)),
                str(cat.get('total', 0))
            ])
        
        cat_table = Table(cat_data, colWidths=[2*inch, 1.3*inch, 1.3*inch, 1.3*inch])
        cat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(cat_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Top Diseases
    top_diseases = context.get('top_diseases', [])
    if top_diseases:
        story.append(Paragraph("<b>TOP DISEASES</b>", styles['Heading2']))
        disease_data = [['Disease', 'OPD', 'IPD', 'Total']]
        for disease in top_diseases[:15]:
            disease_data.append([
                disease.get('name', 'Unknown')[:30],
                str(disease.get('opd', 0)),
                str(disease.get('ipd', 0)),
                str(disease.get('total', 0))
            ])
        
        disease_table = Table(disease_data, colWidths=[2.5*inch, 1*inch, 1*inch, 1*inch])
        disease_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(disease_table)
    
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_pharmacy_report_pdf(context: Dict[str, Any]) -> bytes:
    """Generate PDF report for pharmacy report."""
    if not REPORTLAB_AVAILABLE:
        return b"PDF generation requires reportlab. Install with: pip install reportlab"
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Hospital header
    hospital_settings = context.get('hospital_settings')
    if hospital_settings:
        story.append(Paragraph(hospital_settings.hospital_name or "Hospital", title_style))
        if hospital_settings.hospital_address:
            story.append(Paragraph(hospital_settings.hospital_address, styles['Normal']))
    else:
        story.append(Paragraph("HOSPITAL", title_style))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("PHARMACY REPORT", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Period and summary
    story.append(Paragraph(f"<b>Period:</b> {context['start_date']} to {context['end_date']}", styles['Normal']))
    report_date = context.get('report_date', datetime.now())
    if isinstance(report_date, datetime):
        story.append(Paragraph(f"<b>Report Generated:</b> {report_date.strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Summary statistics
    story.append(Paragraph("<b>Summary Statistics</b>", styles['Heading2']))
    summary_data = [
        ['Total Prescriptions:', str(context.get('total_prescriptions', 0))],
        ['Total Revenue:', f"GHS {float(context.get('total_revenue', Decimal('0.00'))):,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Top Medications
    top_medications = context.get('top_medications', [])
    if top_medications:
        story.append(Paragraph("<b>Top Prescribed Medications</b>", styles['Heading2']))
        med_data = [['Rank', 'Medication', 'Count']]
        for idx, (med, count) in enumerate(top_medications[:20], 1):
            med_data.append([str(idx), med[:40], str(count)])
        med_table = Table(med_data, colWidths=[0.5*inch, 4*inch, 1.5*inch])
        med_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(med_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Gender Distribution
    gender_breakdown = context.get('gender_breakdown', {})
    if gender_breakdown:
        story.append(Paragraph("<b>Gender Distribution</b>", styles['Heading2']))
        total_patients = sum(gender_breakdown.values())
        gender_data = [['Gender', 'Count', 'Percentage']]
        for gender, count in gender_breakdown.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            gender_data.append([gender or 'Unknown', str(count), f"{percentage:.1f}%"])
        gender_table = Table(gender_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
        gender_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(gender_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Age Distribution
    age_groups = context.get('age_groups', {})
    if age_groups:
        story.append(Paragraph("<b>Age Distribution</b>", styles['Heading2']))
        total_patients = sum(age_groups.values())
        age_data = [['Age Group', 'Count', 'Percentage']]
        for age_group, count in age_groups.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            age_label = f"{age_group} years" if age_group != "65+" else "65+ years"
            age_data.append([age_label, str(count), f"{percentage:.1f}%"])
        age_table = Table(age_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
        age_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(age_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Footer
    current_user = context.get('current_user')
    generated_by = current_user.full_name if current_user and hasattr(current_user, 'full_name') else (current_user.username if current_user else 'LHIMS Administrator')
    story.append(Paragraph(f"Report Generated: {report_date.strftime('%Y-%m-%d %H:%M')} | Generated by: {generated_by}", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_lab_report_pdf(context: Dict[str, Any]) -> bytes:
    """Generate PDF report for lab report."""
    if not REPORTLAB_AVAILABLE:
        return b"PDF generation requires reportlab. Install with: pip install reportlab"
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Hospital header
    hospital_settings = context.get('hospital_settings')
    if hospital_settings:
        story.append(Paragraph(hospital_settings.hospital_name or "Hospital", title_style))
        if hospital_settings.hospital_address:
            story.append(Paragraph(hospital_settings.hospital_address, styles['Normal']))
    else:
        story.append(Paragraph("HOSPITAL", title_style))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("LAB REPORT", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Period and summary
    story.append(Paragraph(f"<b>Period:</b> {context['start_date']} to {context['end_date']}", styles['Normal']))
    report_date = context.get('report_date', datetime.now())
    if isinstance(report_date, datetime):
        story.append(Paragraph(f"<b>Report Generated:</b> {report_date.strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Summary statistics
    story.append(Paragraph("<b>Summary Statistics</b>", styles['Heading2']))
    summary_data = [
        ['Total Orders:', str(context.get('total_orders', 0))],
        ['Total Revenue:', f"GHS {float(context.get('total_revenue', Decimal('0.00'))):,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Test Frequency
    test_counts = context.get('test_counts', {})
    if test_counts:
        story.append(Paragraph("<b>Test Frequency</b>", styles['Heading2']))
        test_data = [['Test Name', 'Count']]
        for test_name, count in sorted(test_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
            test_data.append([test_name[:40], str(count)])
        test_table = Table(test_data, colWidths=[4.5*inch, 1.5*inch])
        test_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(test_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Gender Distribution
    gender_breakdown = context.get('gender_breakdown', {})
    if gender_breakdown:
        story.append(Paragraph("<b>Gender Distribution</b>", styles['Heading2']))
        total_patients = sum(gender_breakdown.values())
        gender_data = [['Gender', 'Count', 'Percentage']]
        for gender, count in gender_breakdown.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            gender_data.append([gender or 'Unknown', str(count), f"{percentage:.1f}%"])
        gender_table = Table(gender_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
        gender_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(gender_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Age Distribution
    age_groups = context.get('age_groups', {})
    if age_groups:
        story.append(Paragraph("<b>Age Distribution</b>", styles['Heading2']))
        total_patients = sum(age_groups.values())
        age_data = [['Age Group', 'Count', 'Percentage']]
        for age_group, count in age_groups.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            age_label = f"{age_group} years" if age_group != "65+" else "65+ years"
            age_data.append([age_label, str(count), f"{percentage:.1f}%"])
        age_table = Table(age_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
        age_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(age_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Footer
    current_user = context.get('current_user')
    generated_by = current_user.full_name if current_user and hasattr(current_user, 'full_name') else (current_user.username if current_user else 'LHIMS Administrator')
    story.append(Paragraph(f"Report Generated: {report_date.strftime('%Y-%m-%d %H:%M')} | Generated by: {generated_by}", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_radiology_report_pdf(context: Dict[str, Any]) -> bytes:
    """Generate PDF report for radiology report."""
    if not REPORTLAB_AVAILABLE:
        return b"PDF generation requires reportlab. Install with: pip install reportlab"
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Hospital header
    hospital_settings = context.get('hospital_settings')
    if hospital_settings:
        story.append(Paragraph(hospital_settings.hospital_name or "Hospital", title_style))
        if hospital_settings.hospital_address:
            story.append(Paragraph(hospital_settings.hospital_address, styles['Normal']))
    else:
        story.append(Paragraph("HOSPITAL", title_style))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("RADIOLOGY REPORT", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Period and summary
    story.append(Paragraph(f"<b>Period:</b> {context['start_date']} to {context['end_date']}", styles['Normal']))
    report_date = context.get('report_date', datetime.now())
    if isinstance(report_date, datetime):
        story.append(Paragraph(f"<b>Report Generated:</b> {report_date.strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Summary statistics
    story.append(Paragraph("<b>Summary Statistics</b>", styles['Heading2']))
    summary_data = [
        ['Total Orders:', str(context.get('total_orders', 0))],
        ['Total Revenue:', f"GHS {float(context.get('total_revenue', Decimal('0.00'))):,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Study Type Frequency
    study_counts = context.get('study_counts', {})
    if study_counts:
        story.append(Paragraph("<b>Study Type Frequency</b>", styles['Heading2']))
        study_data = [['Study Type', 'Count']]
        for study_type, count in sorted(study_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
            study_data.append([study_type[:40], str(count)])
        study_table = Table(study_data, colWidths=[4.5*inch, 1.5*inch])
        study_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(study_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Gender Distribution
    gender_breakdown = context.get('gender_breakdown', {})
    if gender_breakdown:
        story.append(Paragraph("<b>Gender Distribution</b>", styles['Heading2']))
        total_patients = sum(gender_breakdown.values())
        gender_data = [['Gender', 'Count', 'Percentage']]
        for gender, count in gender_breakdown.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            gender_data.append([gender or 'Unknown', str(count), f"{percentage:.1f}%"])
        gender_table = Table(gender_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
        gender_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(gender_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Age Distribution
    age_groups = context.get('age_groups', {})
    if age_groups:
        story.append(Paragraph("<b>Age Distribution</b>", styles['Heading2']))
        total_patients = sum(age_groups.values())
        age_data = [['Age Group', 'Count', 'Percentage']]
        for age_group, count in age_groups.items():
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            age_label = f"{age_group} years" if age_group != "65+" else "65+ years"
            age_data.append([age_label, str(count), f"{percentage:.1f}%"])
        age_table = Table(age_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
        age_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(age_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Footer
    current_user = context.get('current_user')
    generated_by = current_user.full_name if current_user and hasattr(current_user, 'full_name') else (current_user.username if current_user else 'LHIMS Administrator')
    story.append(Paragraph(f"Report Generated: {report_date.strftime('%Y-%m-%d %H:%M')} | Generated by: {generated_by}", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def generate_transfer_medical_report_pdf(context: Dict[str, Any]) -> bytes:
    """Generate comprehensive medical report for patient transfer to external facility."""
    if not REPORTLAB_AVAILABLE:
        return b"PDF generation requires reportlab. Install with: pip install reportlab"
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Hospital header
    hospital_settings = context.get('hospital_settings')
    if hospital_settings:
        story.append(Paragraph(hospital_settings.hospital_name or "Hospital", title_style))
        if hospital_settings.hospital_address:
            story.append(Paragraph(hospital_settings.hospital_address, styles['Normal']))
    else:
        story.append(Paragraph("HOSPITAL", title_style))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("MEDICAL TRANSFER REPORT", title_style))
    story.append(Spacer(1, 0.3*inch))
    
    admission = context.get('admission')
    patient = admission.patient if admission else context.get('patient')
    
    # Patient Demographics
    story.append(Paragraph("<b>PATIENT DEMOGRAPHICS</b>", styles['Heading2']))
    patient_data = [
        ['Full Name:', f"{patient.first_name} {patient.last_name}"],
        ['Patient Number:', patient.patient_number or 'N/A'],
        ['Date of Birth:', patient.date_of_birth.strftime('%Y-%m-%d') if patient.date_of_birth else 'N/A'],
        ['Gender:', patient.gender or 'N/A'],
        ['Phone Number:', patient.phone_number or 'N/A'],
        ['Address:', patient.address or 'N/A'],
        ['National ID:', patient.national_id or 'N/A'],
    ]
    if patient.payment_mechanism:
        patient_data.append(['Payment Mechanism:', patient.payment_mechanism.value.replace('_', ' ').title()])
    if patient.nhis_number:
        patient_data.append(['NHIS Number:', patient.nhis_number])
    
    patient_table = Table(patient_data, colWidths=[2.5*inch, 3.5*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Admission Information
    story.append(Paragraph("<b>ADMISSION INFORMATION</b>", styles['Heading2']))
    admission_date = admission.admission_date.date() if isinstance(admission.admission_date, datetime) else admission.admission_date
    admission_data = [
        ['Admission Number:', admission.admission_number or f"#{admission.id}"],
        ['Admission Date:', admission.admission_date.strftime('%Y-%m-%d %H:%M') if admission.admission_date else 'N/A'],
        ['Ward:', admission.ward.name if admission.ward else 'N/A'],
        ['Bed:', admission.bed.bed_number if admission.bed else 'N/A'],
    ]
    if admission.admission_reason:
        admission_data.append(['Reason for Admission:', admission.admission_reason])
    if admission.diagnosis:
        admission_data.append(['Admission Diagnosis:', admission.diagnosis])
    if admission.discharge_date:
        discharge_date = admission.discharge_date.date() if isinstance(admission.discharge_date, datetime) else admission.discharge_date
        los = (discharge_date - admission_date).days
        admission_data.append(['Length of Stay:', f"{los} days"])
    else:
        los = (date.today() - admission_date).days
        admission_data.append(['Length of Stay (Current):', f"{los} days"])
    
    admission_table = Table(admission_data, colWidths=[2.5*inch, 3.5*inch])
    admission_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(admission_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Transfer Information
    transfer_info = context.get('transfer_info', {})
    if transfer_info:
        story.append(Paragraph("<b>TRANSFER INFORMATION</b>", styles['Heading2']))
        transfer_data = [
            ['Transfer Date:', datetime.now().strftime('%Y-%m-%d %H:%M')],
            ['Transfer Type:', 'External Transfer'],
        ]
        if transfer_info.get('external_hospital_name'):
            transfer_data.append(['Receiving Hospital:', transfer_info['external_hospital_name']])
        if transfer_info.get('external_hospital_address'):
            transfer_data.append(['Hospital Address:', transfer_info['external_hospital_address']])
        if transfer_info.get('external_hospital_contact'):
            transfer_data.append(['Contact Information:', transfer_info['external_hospital_contact']])
        if transfer_info.get('external_ward_department'):
            transfer_data.append(['Ward/Department:', transfer_info['external_ward_department']])
        if transfer_info.get('transfer_reason'):
            transfer_data.append(['Transfer Reason:', transfer_info['transfer_reason']])
        
        transfer_table = Table(transfer_data, colWidths=[2.5*inch, 3.5*inch])
        transfer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(transfer_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Clinical Encounters
    encounters = context.get('encounters', [])
    if encounters:
        story.append(Paragraph("<b>CLINICAL ENCOUNTERS</b>", styles['Heading2']))
        for idx, encounter in enumerate(encounters, 1):
            story.append(Paragraph(f"<b>Encounter #{idx} - {encounter.encounter_date.strftime('%Y-%m-%d %H:%M') if encounter.encounter_date else 'N/A'}</b>", styles['Heading3']))
            
            encounter_details = []
            if encounter.clinician:
                encounter_details.append(['Clinician:', f"{encounter.clinician.full_name or encounter.clinician.username}"])
            if encounter.chief_complaint:
                encounter_details.append(['Chief Complaint:', encounter.chief_complaint[:200]])
            if encounter.history_of_present_illness:
                encounter_details.append(['History of Present Illness:', encounter.history_of_present_illness[:300]])
            if encounter.past_medical_history:
                encounter_details.append(['Past Medical History:', encounter.past_medical_history[:300]])
            if encounter.allergies:
                encounter_details.append(['Allergies:', encounter.allergies])
            if encounter.medications:
                encounter_details.append(['Current Medications:', encounter.medications[:300]])
            if encounter.physical_examination:
                encounter_details.append(['Physical Examination:', encounter.physical_examination[:300]])
            if encounter.assessment:
                encounter_details.append(['Assessment:', encounter.assessment[:300]])
            if encounter.plan:
                encounter_details.append(['Treatment Plan:', encounter.plan[:300]])
            if encounter.primary_diagnosis_description:
                encounter_details.append(['Primary Diagnosis:', f"{encounter.primary_diagnosis_code or ''} - {encounter.primary_diagnosis_description}"])
            
            if encounter_details:
                enc_table = Table(encounter_details, colWidths=[2*inch, 4*inch])
                enc_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP')
                ]))
                story.append(enc_table)
            story.append(Spacer(1, 0.2*inch))
    
    # Lab Results
    lab_orders = context.get('lab_orders', [])
    if lab_orders:
        story.append(Paragraph("<b>LABORATORY RESULTS</b>", styles['Heading2']))
        lab_data = [['Test Name', 'Date', 'Result', 'Status']]
        for order in lab_orders:
            test_date = order.ordered_at.strftime('%Y-%m-%d') if order.ordered_at else 'N/A'
            result = order.result[:150] if order.result else 'Pending'
            lab_data.append([
                order.test_name or 'N/A',
                test_date,
                result,
                order.status.value.title() if order.status else 'N/A'
            ])
        
        lab_table = Table(lab_data, colWidths=[1.5*inch, 1*inch, 2.5*inch, 1*inch])
        lab_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(lab_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Radiology Reports
    radiology_orders = context.get('radiology_orders', [])
    if radiology_orders:
        story.append(Paragraph("<b>RADIOLOGY REPORTS</b>", styles['Heading2']))
        rad_data = [['Study Type', 'Date', 'Report', 'Status']]
        for order in radiology_orders:
            study_date = order.ordered_at.strftime('%Y-%m-%d') if order.ordered_at else 'N/A'
            report = order.report[:150] if order.report else 'Pending'
            rad_data.append([
                order.study_type or 'N/A',
                study_date,
                report,
                order.status.value.title() if order.status else 'N/A'
            ])
        
        rad_table = Table(rad_data, colWidths=[1.5*inch, 1*inch, 2.5*inch, 1*inch])
        rad_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(rad_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Prescriptions
    prescriptions = context.get('prescriptions', [])
    if prescriptions:
        story.append(Paragraph("<b>PRESCRIPTIONS</b>", styles['Heading2']))
        presc_data = [['Medication', 'Dosage', 'Frequency', 'Duration', 'Status']]
        for presc in prescriptions:
            presc_data.append([
                presc.medication_name or 'N/A',
                presc.dosage or 'N/A',
                presc.frequency or 'N/A',
                presc.duration or 'N/A',
                presc.status.value.title() if presc.status else 'N/A'
            ])
        
        presc_table = Table(presc_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 1.5*inch])
        presc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(presc_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Vital Signs
    vitals_records = context.get('vitals_records', [])
    if vitals_records:
        story.append(Paragraph("<b>VITAL SIGNS</b>", styles['Heading2']))
        vitals_data = [['Date/Time', 'Temp (°C)', 'BP', 'Pulse', 'RR', 'SpO2%', 'Weight (kg)']]
        for vital in vitals_records[:10]:  # Limit to 10 most recent
            recorded_at = vital.recorded_at.strftime('%Y-%m-%d %H:%M') if vital.recorded_at else 'N/A'
            bp = f"{vital.systolic_bp or ''}/{vital.diastolic_bp or ''}" if (vital.systolic_bp or vital.diastolic_bp) else (vital.blood_pressure or 'N/A')
            vitals_data.append([
                recorded_at,
                str(vital.temperature) if vital.temperature else 'N/A',
                bp,
                str(vital.pulse_rate) if vital.pulse_rate else 'N/A',
                str(vital.respiratory_rate) if vital.respiratory_rate else 'N/A',
                str(vital.oxygen_saturation) if vital.oxygen_saturation else 'N/A',
                str(vital.weight) if vital.weight else 'N/A'
            ])
        
        vitals_table = Table(vitals_data, colWidths=[1.2*inch, 0.8*inch, 0.8*inch, 0.7*inch, 0.7*inch, 0.8*inch, 0.9*inch])
        vitals_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(vitals_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Admission Notes
    notes = context.get('notes', [])
    if notes:
        story.append(Paragraph("<b>ADMISSION NOTES</b>", styles['Heading2']))
        for note in notes[:10]:  # Limit to 10 most recent
            note_date = note.created_at.strftime('%Y-%m-%d %H:%M') if note.created_at else 'N/A'
            note_author = note.created_by.full_name if note.created_by and hasattr(note.created_by, 'full_name') else (note.created_by.username if note.created_by else 'N/A')
            story.append(Paragraph(f"<b>{note_date} - {note_author}</b>", styles['Normal']))
            if note.note:
                story.append(Paragraph(note.note[:500], styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
        story.append(Spacer(1, 0.2*inch))
    
    # Footer
    story.append(Spacer(1, 0.3*inch))
    report_date = context.get('report_date', datetime.now())
    report_date_str = report_date.strftime('%Y-%m-%d %H:%M') if isinstance(report_date, datetime) else str(report_date)
    current_user = context.get('current_user')
    generated_by = current_user.full_name if current_user and hasattr(current_user, 'full_name') else (current_user.username if current_user else 'LHIMS Administrator')
    
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, textColor=colors.grey, alignment=TA_CENTER, spaceBefore=20)
    story.append(Paragraph(f"Report Generated: {report_date_str} | Generated by: {generated_by}", footer_style))
    
    if hospital_settings:
        story.append(Paragraph(f"Prepared by: {hospital_settings.hospital_name or 'Hospital'}", footer_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_lab_result_pdf(context: Dict[str, Any]) -> bytes:
    """Generate PDF report for a lab result."""
    if not REPORTLAB_AVAILABLE:
        return b"PDF generation requires reportlab. Install with: pip install reportlab"
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    lab_order = context['lab_order']
    patient = context['patient']
    result_json = context.get('result_json')
    schema_json = context.get('schema_json')
    flags_json = context.get('flags_json')
    ref_ranges = context.get('ref_ranges')
    
    # Hospital header
    hospital_settings = context.get('hospital_settings')
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    if hospital_settings:
        story.append(Paragraph(hospital_settings.hospital_name or "Laboratory Report", title_style))
    else:
        story.append(Paragraph("LABORATORY REPORT", title_style))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("LABORATORY TEST REPORT", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Patient Information
    story.append(Paragraph("<b>Patient Information</b>", styles['Heading2']))
    patient_data = [
        ['Patient Name:', f"{patient.first_name} {patient.last_name}"],
        ['Patient Number:', patient.patient_number or 'N/A'],
        ['Date of Birth:', patient.date_of_birth.strftime('%Y-%m-%d') if patient.date_of_birth else 'N/A'],
        ['Gender:', patient.gender or 'N/A'],
    ]
    patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Test Information
    story.append(Paragraph("<b>Test Information</b>", styles['Heading2']))
    test_data = [
        ['Test Name:', lab_order.test_name or 'N/A'],
        ['Test Code:', lab_order.test_code or 'N/A'],
        ['Collection Date:', lab_order.ordered_at.strftime('%Y-%m-%d') if lab_order.ordered_at else 'N/A'],
        ['Report Date:', lab_order.result_entered_at.strftime('%Y-%m-%d %H:%M') if lab_order.result_entered_at else 'N/A'],
        ['Status:', lab_order.result_status or 'N/A'],
    ]
    test_table = Table(test_data, colWidths=[2*inch, 4*inch])
    test_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(test_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Results
    if result_json and schema_json and flags_json:
        story.append(Paragraph("<b>Test Results</b>", styles['Heading2']))
        
        result_data = [['Test Parameter', 'Result', 'Flag', 'Reference Range']]
        
        # Get sections from schema layout
        sections = schema_json.get('layout', {}).get('sections', []) if isinstance(schema_json, dict) else []
        
        for section in sections:
            if section.get('title'):
                # Add section header row
                result_data.append([section['title'], '', '', ''])
            
            rows = section.get('rows', [])
            for row in rows:
                columns = row.get('columns', [])
                for col in columns:
                    items = col.get('items', [])
                    for fid in items:
                        if isinstance(schema_json, dict):
                            fld = schema_json.get('fields', {}).get(fid)
                        else:
                            fld = None
                        
                        if fld:
                            val = result_json.get(fld.get('code'))
                            if val is not None and val != '' and val != []:
                                flag_info = flags_json.get(fld.get('code')) if flags_json else None
                                flag = flag_info.get('flag') if flag_info else None
                                
                                # Format result value
                                if isinstance(val, list):
                                    val_str = ', '.join(map(str, val))
                                else:
                                    val_str = str(val)
                                
                                # Add unit if present
                                unit = fld.get('unit', '')
                                if unit and not isinstance(val, list):
                                    val_str = f"{val_str} {unit}"
                                
                                # Format flag
                                if flag == 'CRITICAL':
                                    flag_str = 'CRITICAL'
                                elif flag == 'H':
                                    flag_str = 'HIGH'
                                elif flag == 'L':
                                    flag_str = 'LOW'
                                else:
                                    flag_str = 'Normal'
                                
                                # Get reference range
                                ref_range = None
                                if ref_ranges:
                                    ref_range = ref_ranges.get(fld.get('code'))
                                
                                if ref_range:
                                    ref_str = f"{ref_range.get('low', '')} - {ref_range.get('high', '')}"
                                    if unit:
                                        ref_str = f"{ref_str} {unit}"
                                elif unit:
                                    ref_str = unit
                                else:
                                    ref_str = 'N/A'
                                
                                result_data.append([
                                    fld.get('label', ''),
                                    val_str,
                                    flag_str,
                                    ref_str
                                ])
        
        # Create table
        result_table = Table(result_data, colWidths=[2*inch, 1.5*inch, 0.8*inch, 1.7*inch])
        result_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (2, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(result_table)
        story.append(Spacer(1, 0.2*inch))
    
    # Comments
    if result_json and result_json.get('comment'):
        story.append(Paragraph("<b>Comments/Interpretation:</b>", styles['Heading3']))
        story.append(Paragraph(result_json.get('comment'), styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
    
    # Signatures
    story.append(Paragraph("<b>Signatures</b>", styles['Heading2']))
    signature_data = [
        ['Result Entered By:', lab_order.result_entered_by.full_name if lab_order.result_entered_by and hasattr(lab_order.result_entered_by, 'full_name') else 'N/A'],
        ['Verified By:', lab_order.verified_by.full_name if lab_order.verified_by and hasattr(lab_order.verified_by, 'full_name') else 'N/A'],
        ['Authorized By:', lab_order.authorized_by.full_name if lab_order.authorized_by and hasattr(lab_order.authorized_by, 'full_name') else 'N/A'],
    ]
    signature_table = Table(signature_data, colWidths=[2*inch, 4*inch])
    signature_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(signature_table)
    
    # Footer
    story.append(Spacer(1, 0.3*inch))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, textColor=colors.grey, alignment=TA_CENTER, spaceBefore=20)
    story.append(Paragraph("This is a computer-generated report. No signature required.", footer_style))
    story.append(Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", footer_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
