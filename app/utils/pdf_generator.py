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
    """Generate PDF report for financial data."""
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
    story.append(Paragraph("FINANCIAL REPORT", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Date Range
    start_date = context.get('start_date')
    end_date = context.get('end_date')
    if start_date and end_date:
        start_str = start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date)
        end_str = end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date)
        story.append(Paragraph(
            f"Period: {start_str} to {end_str}",
            styles['Normal']
        ))
    story.append(Spacer(1, 0.2*inch))
    
    # Summary
    story.append(Paragraph("<b>Summary</b>", styles['Heading2']))
    total_revenue = float(context.get('total_revenue', Decimal('0.00')))
    total_paid = float(context.get('total_paid', Decimal('0.00')))
    total_outstanding = float(context.get('total_outstanding', Decimal('0.00')))
    
    summary_data = [
        ['Total Revenue:', f"GHS {total_revenue:.2f}"],
        ['Total Paid:', f"GHS {total_paid:.2f}"],
        ['Outstanding:', f"GHS {total_outstanding:.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Service Breakdown
    service_breakdown = context.get('service_breakdown', {})
    if service_breakdown:
        story.append(Paragraph("<b>Breakdown by Service Type</b>", styles['Heading2']))
        service_data = [['Service Type', 'Count', 'Total Amount', 'Paid', 'Outstanding']]
        for service_type, data in service_breakdown.items():
            total_amt = float(data.get('total', Decimal('0.00')))
            paid_amt = float(data.get('paid', Decimal('0.00')))
            outstanding = total_amt - paid_amt
            service_data.append([
                service_type.replace('_', ' ').title(),
                str(data.get('count', 0)),
                f"GHS {total_amt:.2f}",
                f"GHS {paid_amt:.2f}",
                f"GHS {outstanding:.2f}"
            ])
        
        service_table = Table(service_data, colWidths=[1.5*inch, 0.8*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        service_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(service_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Footer
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    
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
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    story.append(Paragraph("PATIENT DEMOGRAPHICS REPORT", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Summary
    story.append(Paragraph(f"<b>Total Patients:</b> {context['total_patients']}", styles['Heading2']))
    story.append(Paragraph(
        f"Period: {context['start_date']} to {context['end_date']}",
        styles['Normal']
    ))
    story.append(Spacer(1, 0.3*inch))
    
    # Gender Breakdown
    if context['gender_breakdown']:
        story.append(Paragraph("<b>Gender Distribution</b>", styles['Heading2']))
        gender_data = [['Gender', 'Count', 'Percentage']]
        for gender, count in context['gender_breakdown'].items():
            percentage = (count / context['total_patients'] * 100) if context['total_patients'] > 0 else 0
            gender_data.append([gender, str(count), f"{percentage:.1f}%"])
        
        gender_table = Table(gender_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        gender_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(gender_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Age Groups
    if context['age_groups']:
        story.append(Paragraph("<b>Age Distribution</b>", styles['Heading2']))
        age_data = [['Age Group', 'Count', 'Percentage']]
        for age_group, count in context['age_groups'].items():
            percentage = (count / context['total_patients'] * 100) if context['total_patients'] > 0 else 0
            age_data.append([age_group, str(count), f"{percentage:.1f}%"])
        
        age_table = Table(age_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        age_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(age_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Footer
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    
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
        ['<b>NET INCOME (PROFIT/LOSS)</b>', f"<b>{net_income:.2f}</b>"],
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
    
    # Revenue by Payment Method
    revenue_by_method = context.get('revenue_by_method', {})
    if revenue_by_method:
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("<b>Revenue by Payment Method</b>", styles['Heading3']))
        method_data = [['Payment Method', 'Amount (GHS)', 'Percentage']]
        for method, amount in revenue_by_method.items():
            percentage = (float(amount) / total_revenue * 100) if total_revenue > 0 else 0
            method_data.append([
                method.replace('_', ' ').title(),
                f"{float(amount):.2f}",
                f"{percentage:.2f}%"
            ])
        
        method_table = Table(method_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        method_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(method_table)
    
    # Footer
    story.append(Spacer(1, 0.5*inch))
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
    
    # Title
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
    
    # Date Range
    start_date = context.get('start_date')
    end_date = context.get('end_date')
    if start_date and end_date:
        story.append(Paragraph(
            f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            styles['Normal']
        ))
    story.append(Spacer(1, 0.2*inch))
    
    # Statistics Summary
    statistics = context.get('statistics', {})
    story.append(Paragraph("<b>Summary</b>", styles['Heading2']))
    summary_data = [
        ['Total Expenses:', f"GHS {float(statistics.get('total_expenses', Decimal('0.00'))):.2f}"],
        ['Total Records:', str(statistics.get('total_count', 0))],
    ]
    
    status_breakdown = statistics.get('status_breakdown', {})
    if status_breakdown:
        pending_count = status_breakdown.get('pending', {}).get('count', 0)
        paid_count = status_breakdown.get('paid', {}).get('count', 0)
        summary_data.append(['Pending:', str(pending_count)])
        summary_data.append(['Paid:', str(paid_count)])
    
    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Category Breakdown
    category_breakdown = statistics.get('category_breakdown', {})
    if category_breakdown:
        story.append(Paragraph("<b>Expenses by Category</b>", styles['Heading2']))
        category_data = [['Category', 'Amount (GHS)']]
        for category, amount in category_breakdown.items():
            category_data.append([
                category.replace('_', ' ').title(),
                f"{float(amount):.2f}"
            ])
        
        category_table = Table(category_data, colWidths=[3*inch, 2*inch])
        category_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(category_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Expenses List (limited to first 50)
    expenses = context.get('expenses', [])
    if expenses:
        story.append(Paragraph("<b>Expense Details</b>", styles['Heading2']))
        expense_data = [['Date', 'Description', 'Category', 'Amount', 'Status']]
        for expense in expenses[:50]:  # Limit to first 50
            expense_date = expense.expense_date.strftime('%Y-%m-%d') if hasattr(expense.expense_date, 'strftime') else str(expense.expense_date)
            description = (expense.description or 'N/A')[:30]  # Truncate long descriptions
            category = expense.category.value if hasattr(expense.category, 'value') else str(expense.category)
            amount = f"{float(expense.amount):.2f}"
            status = expense.status.value if hasattr(expense.status, 'value') else str(expense.status)
            
            expense_data.append([
                expense_date,
                description,
                category.replace('_', ' ').title(),
                amount,
                status.title()
            ])
        
        expense_table = Table(expense_data, colWidths=[1*inch, 2*inch, 1*inch, 1*inch, 0.8*inch])
        expense_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(expense_table)
        
        if len(expenses) > 50:
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph(f"<i>Showing first 50 of {len(expenses)} expenses</i>", styles['Normal']))
        
        story.append(Spacer(1, 0.3*inch))
    
    # Footer
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
