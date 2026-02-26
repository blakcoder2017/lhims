"""
Lab Report PDF Generation Service

This module provides PDF report generation functionality for lab results.
"""
from io import BytesIO
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Image, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from sqlalchemy.orm import Session

from app.models.encounter_models import LabOrder
from app.models.lab_models import ReferenceRange, LabSample


class LabReportPDFGenerator:
    """Generate PDF reports for lab results."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='LabReportTitle',
            parent=self.styles['Title'],
            fontSize=18,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_CENTER
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='LabReportSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.gray,
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='LabReportSection',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2c3e50'),
            spaceBefore=15,
            spaceAfter=10,
            borderPadding=5
        ))
        
        # Result normal style
        self.styles.add(ParagraphStyle(
            name='LabResultNormal',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.black
        ))
        
        # Result abnormal style (High)
        self.styles.add(ParagraphStyle(
            name='LabResultHigh',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#e74c3c'),  # Red
            fontName='Helvetica-Bold'
        ))
        
        # Result abnormal style (Low)
        self.styles.add(ParagraphStyle(
            name='LabResultLow',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#3498db'),  # Blue
            fontName='Helvetica-Bold'
        ))
        
        # Critical style
        self.styles.add(ParagraphStyle(
            name='LabResultCritical',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.white,
            backColor=colors.HexColor('#e74c3c'),
            spaceBefore=3,
            spaceAfter=3,
            leftPadding=5,
            rightPadding=5
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='LabReportFooter',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.gray,
            alignment=TA_CENTER
        ))
    
    def generate_report(
        self,
        db: Session,
        lab_order: LabOrder,
        include_patient_info: bool = True,
        include_sample_info: bool = True,
        include_reference_ranges: bool = True
    ) -> bytes:
        """
        Generate a PDF report for a lab order.
        
        Args:
            db: Database session
            lab_order: The lab order to generate report for
            include_patient_info: Include patient information
            include_sample_info: Include sample information
            include_reference_ranges: Include reference ranges
            
        Returns:
            PDF bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        # Build the story
        story = []
        
        # Add header
        story.extend(self._build_header())
        
        # Add patient information
        if include_patient_info:
            story.extend(self._build_patient_section(db, lab_order))
        
        # Add sample information
        if include_sample_info:
            story.extend(self._build_sample_section(db, lab_order))
        
        # Add test information
        story.extend(self._build_test_section(lab_order))
        
        # Add results
        if lab_order.result_json:
            story.extend(self._build_results_section(
                db, lab_order, include_reference_ranges
            ))
        elif lab_order.result:
            story.extend(self._build_free_text_result_section(lab_order))
        
        # Add authorization info
        story.extend(self._build_authorization_section(lab_order))
        
        # Add footer
        story.extend(self._build_footer(lab_order))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _build_header(self) -> List:
        """Build the report header."""
        story = []
        
        # Hospital name (placeholder - can be fetched from settings)
        story.append(Paragraph(
            "LABORATORY SERVICES DEPARTMENT",
            self.styles['LabReportTitle']
        ))
        
        story.append(Paragraph(
            "Medical Laboratory Report",
            self.styles['LabReportSubtitle']
        ))
        
        # Add a horizontal line
        story.append(HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor('#3498db'),
            spaceBefore=10,
            spaceAfter=15
        ))
        
        return story
    
    def _build_patient_section(self, db: Session, lab_order: LabOrder) -> List:
        """Build patient information section."""
        story = []
        
        story.append(Paragraph("Patient Information", self.styles['LabReportSection']))
        
        # Get patient info
        patient = None
        if lab_order.encounter:
            patient = lab_order.encounter.patient
        elif lab_order.patient_id:
            from app.models.patient_models import Patient
            patient = db.query(Patient).filter(Patient.id == lab_order.patient_id).first()
        
        if patient:
            # Calculate age
            age = ""
            if patient.date_of_birth:
                today = datetime.now().date()
                age_years = today.year - patient.date_of_birth.year
                if (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day):
                    age_years -= 1
                age = f"{age_years} years"
            
            patient_data = [
                ['Name:', f"{patient.first_name} {patient.last_name}"],
                ['Patient ID:', str(patient.patient_id) if hasattr(patient, 'patient_id') else str(patient.id)],
                ['Age:', age],
                ['Gender:', patient.gender or 'N/A'],
                ['Contact:', patient.phone or 'N/A'],
            ]
            
            patient_table = Table(patient_data, colWidths=[50*mm, 120*mm])
            patient_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
                ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            story.append(patient_table)
            story.append(Spacer(1, 15))
        
        return story
    
    def _build_sample_section(self, db: Session, lab_order: LabOrder) -> List:
        """Build sample information section."""
        story = []
        
        # Get sample
        sample = db.query(LabSample).filter(
            LabSample.lab_order_id == lab_order.id,
            LabSample.is_active == True
        ).first()
        
        if sample:
            story.append(Paragraph("Sample Information", self.styles['LabReportSection']))
            
            sample_data = [
                ['Barcode:', sample.barcode],
                ['Specimen Type:', sample.sample_type or 'N/A'],
                ['Collection Date:', sample.collected_at.strftime('%Y-%m-%d %H:%M') if sample.collected_at else 'N/A'],
                ['Received Date:', sample.received_at.strftime('%Y-%m-%d %H:%M') if sample.received_at else 'N/A'],
                ['Status:', sample.status.capitalize() if sample.status else 'N/A'],
            ]
            
            sample_table = Table(sample_data, colWidths=[50*mm, 120*mm])
            sample_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
                ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            story.append(sample_table)
            story.append(Spacer(1, 15))
        
        return story
    
    def _build_test_section(self, lab_order: LabOrder) -> List:
        """Build test information section."""
        story = []
        
        story.append(Paragraph("Test Details", self.styles['LabReportSection']))
        
        # Order info
        order_data = [
            ['Test Name:', lab_order.test_name],
            ['Test Code:', lab_order.test_code or 'N/A'],
            ['Priority:', lab_order.priority.capitalize() if lab_order.priority else 'Routine'],
            ['Order Date:', lab_order.ordered_at.strftime('%Y-%m-%d %H:%M') if lab_order.ordered_at else 'N/A'],
            ['Completed Date:', lab_order.completed_at.strftime('%Y-%m-%d %H:%M') if lab_order.completed_at else 'N/A'],
        ]
        
        order_table = Table(order_data, colWidths=[50*mm, 120*mm])
        order_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        story.append(order_table)
        story.append(Spacer(1, 15))
        
        return story
    
    def _build_results_section(
        self,
        db: Session,
        lab_order: LabOrder,
        include_reference_ranges: bool
    ) -> List:
        """Build results section for structured results."""
        story = []
        
        story.append(Paragraph("Test Results", self.styles['LabReportSection']))
        
        result_json = lab_order.result_json or {}
        flags = lab_order.flags_json or {}
        
        # Get reference ranges if needed
        ref_ranges = {}
        if include_reference_ranges:
            ref_ranges = self._get_reference_ranges(db, lab_order.test_name)
        
        # Build results table
        table_data = [['Parameter', 'Result', 'Reference Range', 'Flag']]
        
        for field_code, value in result_json.items():
            # Get field label
            field_label = field_code.replace('_', ' ').title()
            
            # Get value
            result_value = str(value) if value is not None else 'N/A'
            
            # Get reference range
            ref_range = ref_ranges.get(field_code, {})
            ref_str = f"{ref_range.get('low', '-')} - {ref_range.get('high', '-')}" if ref_range else 'N/A'
            
            # Get flag
            flag_info = flags.get(field_code, {})
            flag = flag_info.get('flag', '')
            
            # Determine row style based on flag
            if flag == 'CRITICAL':
                row_style = [
                    ('TEXTCOLOR', (1, -1), (1, -1), colors.HexColor('#e74c3c')),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ffebee')),
                    ('FONTNAME', (1, -1), (1, -1), 'Helvetica-Bold'),
                ]
            elif flag == 'H':
                row_style = [
                    ('TEXTCOLOR', (1, -1), (1, -1), colors.HexColor('#e74c3c')),
                    ('FONTNAME', (1, -1), (1, -1), 'Helvetica-Bold'),
                ]
            elif flag == 'L':
                row_style = [
                    ('TEXTCOLOR', (1, -1), (1, -1), colors.HexColor('#3498db')),
                    ('FONTNAME', (1, -1), (1, -1), 'Helvetica-Bold'),
                ]
            else:
                row_style = []
            
            table_data.append([field_label, result_value, ref_str, flag])
        
        if len(table_data) > 1:
            # Create table
            results_table = Table(table_data, colWidths=[60*mm, 35*mm, 50*mm, 25*mm])
            results_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ecf0f1')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                ('ALIGN', (3, 0), (3, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            # Apply row styles
            for i in range(1, len(table_data)):
                flag = table_data[i][3]
                if flag == 'CRITICAL':
                    results_table.setStyle(TableStyle([
                        ('TEXTCOLOR', (1, i), (1, i), colors.HexColor('#e74c3c')),
                        ('BACKGROUND', (0, i), (-1, i), colors.HexColor('#ffebee')),
                        ('FONTNAME', (1, i), (1, i), 'Helvetica-Bold'),
                    ]))
                elif flag == 'H':
                    results_table.setStyle(TableStyle([
                        ('TEXTCOLOR', (1, i), (1, i), colors.HexColor('#e74c3c')),
                        ('FONTNAME', (1, i), (1, i), 'Helvetica-Bold'),
                    ]))
                elif flag == 'L':
                    results_table.setStyle(TableStyle([
                        ('TEXTCOLOR', (1, i), (1, i), colors.HexColor('#3498db')),
                        ('FONTNAME', (1, i), (1, i), 'Helvetica-Bold'),
                    ]))
            
            story.append(results_table)
        else:
            story.append(Paragraph("No results available", self.styles['LabResultNormal']))
        
        story.append(Spacer(1, 15))
        
        return story
    
    def _build_free_text_result_section(self, lab_order: LabOrder) -> List:
        """Build results section for free-text results."""
        story = []
        
        story.append(Paragraph("Test Results", self.styles['LabReportSection']))
        
        # Get validation status
        validation_status = ""
        if lab_order.result_status:
            validation_status = f" - {lab_order.result_status}"
        
        story.append(Paragraph(
            f"<b>Result:</b> {lab_order.result}",
            self.styles['LabResultNormal']
        ))
        
        story.append(Spacer(1, 15))
        
        return story
    
    def _build_authorization_section(self, lab_order: LabOrder) -> List:
        """Build authorization section."""
        story = []
        
        # Add authorization info if available
        if lab_order.authorized_by_id or lab_order.verified_by_id:
            story.append(Paragraph("Authorization", self.styles['LabReportSection']))
            
            auth_data = []
            
            if lab_order.verified_by_id:
                from app.models.user_models import User
                verifier = db.query(User).filter(User.id == lab_order.verified_by_id).first()
                if verifier:
                    auth_data.append([
                        'Verified By:',
                        f"{verifier.first_name} {verifier.last_name}",
                        lab_order.verified_at.strftime('%Y-%m-%d %H:%M') if lab_order.verified_at else ''
                    ])
            
            if lab_order.authorized_by_id:
                from app.models.user_models import User
                authorizer = db.query(User).filter(User.id == lab_order.authorized_by_id).first()
                if authorizer:
                    auth_data.append([
                        'Authorized By:',
                        f"{authorizer.first_name} {authorizer.last_name}",
                        lab_order.authorized_at.strftime('%Y-%m-%d %H:%M') if lab_order.authorized_at else ''
                    ])
            
            if auth_data:
                auth_table = Table(auth_data, colWidths=[40*mm, 60*mm, 50*mm])
                auth_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]))
                story.append(auth_table)
            
            story.append(Spacer(1, 15))
        
        return story
    
    def _build_footer(self, lab_order: LabOrder) -> List:
        """Build footer section."""
        story = []
        
        # Add disclaimer
        story.append(HRFlowable(
            width="100%",
            thickness=0.5,
            color=colors.gray,
            spaceBefore=10,
            spaceAfter=10
        ))
        
        story.append(Paragraph(
            "This report is electronically generated. Results relate only to the specimen tested. "
            "Please contact the laboratory for any queries or clarifications.",
            self.styles['LabReportFooter']
        ))
        
        story.append(Paragraph(
            f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Report ID: {lab_order.id}",
            self.styles['LabReportFooter']
        ))
        
        return story
    
    def _get_reference_ranges(
        self,
        db: Session,
        test_name: str
    ) -> Dict[str, Dict]:
        """Get reference ranges for a test."""
        ranges = db.query(ReferenceRange).filter(
            ReferenceRange.is_active == True,
            ReferenceRange.test_name.ilike(f"%{test_name}%")
        ).all()
        
        ref_ranges = {}
        for ref in ranges:
            # Store first matching range (could be enhanced for age/gender specific)
            if ref.test_code and ref.test_code not in ref_ranges:
                ref_ranges[ref.test_code] = {
                    'low': ref.normal_min,
                    'high': ref.normal_max,
                    'unit': ref.unit
                }
        
        return ref_ranges


# Helper function to generate lab report
def generate_lab_report_pdf(
    db: Session,
    lab_order_id: int,
    include_patient_info: bool = True,
    include_sample_info: bool = True,
    include_reference_ranges: bool = True
) -> Optional[bytes]:
    """
    Generate a PDF report for a lab order.
    
    Args:
        db: Database session
        lab_order_id: The lab order ID
        include_patient_info: Include patient information
        include_sample_info: Include sample information
        include_reference_ranges: Include reference ranges
        
    Returns:
        PDF bytes or None if order not found
    """
    lab_order = db.query(LabOrder).filter(LabOrder.id == lab_order_id).first()
    
    if not lab_order:
        return None
    
    generator = LabReportPDFGenerator()
    return generator.generate_report(
        db=db,
        lab_order=lab_order,
        include_patient_info=include_patient_info,
        include_sample_info=include_sample_info,
        include_reference_ranges=include_reference_ranges
    )
