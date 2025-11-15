"""
Excel Generation Utilities

Utilities for generating Excel reports using openpyxl.
"""
from typing import Dict, Any
from io import BytesIO
from datetime import datetime
from decimal import Decimal

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


def generate_income_statement_excel(context: Dict[str, Any]) -> bytes:
    """Generate Excel report for income statement."""
    if not OPENPYXL_AVAILABLE:
        # Return a simple CSV as fallback
        return _generate_income_statement_csv(context).encode('utf-8')
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Income Statement"
    
    # Style definitions
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    title_font = Font(bold=True, size=16)
    subtitle_font = Font(bold=True, size=12)
    total_fill_green = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    total_fill_red = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    total_font = Font(bold=True, size=11)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    row = 1
    
    # Hospital header
    hospital_settings = context.get('hospital_settings')
    if hospital_settings:
        ws.merge_cells(f'A{row}:B{row}')
        cell = ws.cell(row=row, column=1, value=hospital_settings.hospital_name or "Hospital")
        cell.font = title_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        row += 1
        
        if hospital_settings.hospital_address:
            ws.merge_cells(f'A{row}:B{row}')
            cell = ws.cell(row=row, column=1, value=hospital_settings.hospital_address)
            cell.alignment = Alignment(horizontal='center', vertical='center')
            row += 1
    
    row += 1
    
    # Title
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws.cell(row=row, column=1, value="INCOME STATEMENT (PROFIT & LOSS)")
    cell.font = title_font
    cell.alignment = Alignment(horizontal='center', vertical='center')
    row += 1
    
    # Period
    period_label = context.get('period_label', '')
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws.cell(row=row, column=1, value=f"Period: {period_label}")
    cell.alignment = Alignment(horizontal='center', vertical='center')
    row += 1
    
    # Report date
    report_date = context.get('report_date', datetime.now())
    if isinstance(report_date, datetime):
        ws.merge_cells(f'A{row}:B{row}')
        cell = ws.cell(row=row, column=1, value=f"Report Generated: {report_date.strftime('%B %d, %Y at %I:%M %p')}")
        cell.alignment = Alignment(horizontal='center', vertical='center')
        row += 1
    
    row += 1
    
    # Revenue Section
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws.cell(row=row, column=1, value="REVENUE")
    cell.font = subtitle_font
    cell.fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    row += 1
    
    # Revenue header
    ws.cell(row=row, column=1, value="Description").font = header_font
    ws.cell(row=row, column=1).fill = header_fill
    ws.cell(row=row, column=1).alignment = Alignment(horizontal='left', vertical='center')
    ws.cell(row=row, column=1).border = border
    ws.cell(row=row, column=2, value="Amount (GHS)").font = header_font
    ws.cell(row=row, column=2).fill = header_fill
    ws.cell(row=row, column=2).alignment = Alignment(horizontal='right', vertical='center')
    ws.cell(row=row, column=2).border = border
    row += 1
    
    # Revenue rows
    revenue_by_service = context.get('revenue_by_service', {})
    revenue_start_row = row
    for service_type, amount in revenue_by_service.items():
        ws.cell(row=row, column=1, value=service_type.replace('_', ' ').title())
        ws.cell(row=row, column=1).border = border
        ws.cell(row=row, column=2, value=float(amount))
        ws.cell(row=row, column=2).number_format = '#,##0.00'
        ws.cell(row=row, column=2).alignment = Alignment(horizontal='right', vertical='center')
        ws.cell(row=row, column=2).border = border
        row += 1
    
    # Total Revenue
    total_revenue = float(context.get('total_revenue', Decimal('0.00')))
    ws.cell(row=row, column=1, value="TOTAL REVENUE").font = total_font
    ws.cell(row=row, column=1).fill = total_fill_green
    ws.cell(row=row, column=1).border = border
    ws.cell(row=row, column=2, value=total_revenue).font = total_font
    ws.cell(row=row, column=2).number_format = '#,##0.00'
    ws.cell(row=row, column=2).fill = total_fill_green
    ws.cell(row=row, column=2).alignment = Alignment(horizontal='right', vertical='center')
    ws.cell(row=row, column=2).border = border
    row += 2
    
    # Expenses Section
    ws.merge_cells(f'A{row}:B{row}')
    cell = ws.cell(row=row, column=1, value="EXPENSES")
    cell.font = subtitle_font
    cell.fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    row += 1
    
    # Expenses header
    ws.cell(row=row, column=1, value="Category").font = header_font
    ws.cell(row=row, column=1).fill = header_fill
    ws.cell(row=row, column=1).alignment = Alignment(horizontal='left', vertical='center')
    ws.cell(row=row, column=1).border = border
    ws.cell(row=row, column=2, value="Amount (GHS)").font = header_font
    ws.cell(row=row, column=2).fill = header_fill
    ws.cell(row=row, column=2).alignment = Alignment(horizontal='right', vertical='center')
    ws.cell(row=row, column=2).border = border
    row += 1
    
    # Expenses rows
    expenses_by_category = context.get('expenses_by_category', {})
    for category, amount in expenses_by_category.items():
        ws.cell(row=row, column=1, value=category.replace('_', ' ').title())
        ws.cell(row=row, column=1).border = border
        ws.cell(row=row, column=2, value=float(amount))
        ws.cell(row=row, column=2).number_format = '#,##0.00'
        ws.cell(row=row, column=2).alignment = Alignment(horizontal='right', vertical='center')
        ws.cell(row=row, column=2).border = border
        row += 1
    
    # Total Expenses
    total_expenses = float(context.get('total_expenses', Decimal('0.00')))
    ws.cell(row=row, column=1, value="TOTAL EXPENSES").font = total_font
    ws.cell(row=row, column=1).fill = total_fill_red
    ws.cell(row=row, column=1).border = border
    ws.cell(row=row, column=2, value=total_expenses).font = total_font
    ws.cell(row=row, column=2).number_format = '#,##0.00'
    ws.cell(row=row, column=2).fill = total_fill_red
    ws.cell(row=row, column=2).alignment = Alignment(horizontal='right', vertical='center')
    ws.cell(row=row, column=2).border = border
    row += 2
    
    # Net Income Section
    net_income = float(context.get('net_income', Decimal('0.00')))
    profit_margin = float(context.get('profit_margin', Decimal('0.00')))
    
    net_income_fill = total_fill_green if net_income >= 0 else total_fill_red
    
    ws.cell(row=row, column=1, value="NET INCOME (PROFIT/LOSS)").font = Font(bold=True, size=12)
    ws.cell(row=row, column=1).fill = net_income_fill
    ws.cell(row=row, column=1).border = border
    ws.cell(row=row, column=2, value=net_income).font = Font(bold=True, size=12)
    ws.cell(row=row, column=2).number_format = '#,##0.00'
    ws.cell(row=row, column=2).fill = net_income_fill
    ws.cell(row=row, column=2).alignment = Alignment(horizontal='right', vertical='center')
    ws.cell(row=row, column=2).border = border
    row += 1
    
    ws.cell(row=row, column=1, value="Profit Margin").font = total_font
    ws.cell(row=row, column=1).fill = net_income_fill
    ws.cell(row=row, column=1).border = border
    ws.cell(row=row, column=2, value=f"{profit_margin:.2f}%").font = total_font
    ws.cell(row=row, column=2).fill = net_income_fill
    ws.cell(row=row, column=2).alignment = Alignment(horizontal='right', vertical='center')
    ws.cell(row=row, column=2).border = border
    row += 2
    
    # Revenue by Payment Method
    revenue_by_method = context.get('revenue_by_method', {})
    if revenue_by_method:
        ws.merge_cells(f'A{row}:C{row}')
        cell = ws.cell(row=row, column=1, value="Revenue by Payment Method")
        cell.font = subtitle_font
        cell.fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
        row += 1
        
        # Header
        ws.cell(row=row, column=1, value="Payment Method").font = header_font
        ws.cell(row=row, column=1).fill = header_fill
        ws.cell(row=row, column=1).alignment = Alignment(horizontal='left', vertical='center')
        ws.cell(row=row, column=1).border = border
        ws.cell(row=row, column=2, value="Amount (GHS)").font = header_font
        ws.cell(row=row, column=2).fill = header_fill
        ws.cell(row=row, column=2).alignment = Alignment(horizontal='right', vertical='center')
        ws.cell(row=row, column=2).border = border
        ws.cell(row=row, column=3, value="Percentage").font = header_font
        ws.cell(row=row, column=3).fill = header_fill
        ws.cell(row=row, column=3).alignment = Alignment(horizontal='right', vertical='center')
        ws.cell(row=row, column=3).border = border
        row += 1
        
        # Data rows
        for method, amount in revenue_by_method.items():
            percentage = (float(amount) / total_revenue * 100) if total_revenue > 0 else 0
            ws.cell(row=row, column=1, value=method.replace('_', ' ').title())
            ws.cell(row=row, column=1).border = border
            ws.cell(row=row, column=2, value=float(amount))
            ws.cell(row=row, column=2).number_format = '#,##0.00'
            ws.cell(row=row, column=2).alignment = Alignment(horizontal='right', vertical='center')
            ws.cell(row=row, column=2).border = border
            ws.cell(row=row, column=3, value=f"{percentage:.2f}%")
            ws.cell(row=row, column=3).alignment = Alignment(horizontal='right', vertical='center')
            ws.cell(row=row, column=3).border = border
            row += 1
    
    # Set column widths
    ws.column_dimensions['A'].width = 40
    ws.column_dimensions['B'].width = 20
    if revenue_by_method:
        ws.column_dimensions['C'].width = 15
    
    # Footer
    row += 1
    ws.cell(row=row, column=1, value=f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Save to bytes
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def _generate_income_statement_csv(context: Dict[str, Any]) -> str:
    """Fallback CSV generation if openpyxl is not available."""
    lines = []
    
    hospital_settings = context.get('hospital_settings')
    if hospital_settings:
        lines.append(hospital_settings.hospital_name or "Hospital")
        if hospital_settings.hospital_address:
            lines.append(hospital_settings.hospital_address)
    
    lines.append("INCOME STATEMENT (PROFIT & LOSS)")
    lines.append(f"Period: {context.get('period_label', '')}")
    
    report_date = context.get('report_date', datetime.now())
    if isinstance(report_date, datetime):
        lines.append(f"Report Generated: {report_date.strftime('%B %d, %Y at %I:%M %p')}")
    
    lines.append("")
    lines.append("REVENUE")
    lines.append("Description,Amount (GHS)")
    
    revenue_by_service = context.get('revenue_by_service', {})
    for service_type, amount in revenue_by_service.items():
        lines.append(f"{service_type.replace('_', ' ').title()},{float(amount):.2f}")
    
    total_revenue = float(context.get('total_revenue', Decimal('0.00')))
    lines.append(f"TOTAL REVENUE,{total_revenue:.2f}")
    lines.append("")
    
    lines.append("EXPENSES")
    lines.append("Category,Amount (GHS)")
    
    expenses_by_category = context.get('expenses_by_category', {})
    for category, amount in expenses_by_category.items():
        lines.append(f"{category.replace('_', ' ').title()},{float(amount):.2f}")
    
    total_expenses = float(context.get('total_expenses', Decimal('0.00')))
    lines.append(f"TOTAL EXPENSES,{total_expenses:.2f}")
    lines.append("")
    
    net_income = float(context.get('net_income', Decimal('0.00')))
    profit_margin = float(context.get('profit_margin', Decimal('0.00')))
    lines.append(f"NET INCOME (PROFIT/LOSS),{net_income:.2f}")
    lines.append(f"Profit Margin,{profit_margin:.2f}%")
    
    revenue_by_method = context.get('revenue_by_method', {})
    if revenue_by_method:
        lines.append("")
        lines.append("Revenue by Payment Method")
        lines.append("Payment Method,Amount (GHS),Percentage")
        for method, amount in revenue_by_method.items():
            percentage = (float(amount) / total_revenue * 100) if total_revenue > 0 else 0
            lines.append(f"{method.replace('_', ' ').title()},{float(amount):.2f},{percentage:.2f}%")
    
    return "\n".join(lines)

