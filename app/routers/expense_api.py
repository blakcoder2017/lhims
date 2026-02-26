"""
Expense API Routes

Routes for expense management including CRUD operations and reporting.
"""
from fastapi import APIRouter, Depends, Request, Query, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from app.core.templates import templates
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.crud import expense_crud
from app.schemas.expense_schemas import ExpenseCreate, ExpenseUpdate, Expense
from app.models.expense_models import ExpenseCategory, ExpenseStatus

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get("/", name="expenses_list")
def expenses_list(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Management"]))
):
    """List all expenses with filtering and pagination."""
    skip = (page - 1) * per_page
    
    # Parse dates
    start = None
    end = None
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    # Parse category and status
    expense_category = None
    if category:
        try:
            expense_category = ExpenseCategory(category)
        except ValueError:
            pass
    
    expense_status = None
    if status:
        try:
            expense_status = ExpenseStatus(status)
        except ValueError:
            pass
    
    expenses, total_count = expense_crud.get_expenses(
        db, skip=skip, limit=per_page,
        category=expense_category,
        status=expense_status,
        start_date=start,
        end_date=end,
        department=department
    )
    
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    # Get statistics
    stats = expense_crud.get_expense_statistics(db, start_date=start, end_date=end)
    
    context = {
        "request": request,
        "title": "Expenses Management",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "expenses": expenses,
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages,
        "category_filter": category,
        "status_filter": status,
        "start_date": start_date,
        "end_date": end_date,
        "department_filter": department,
        "categories": [cat.value for cat in ExpenseCategory],
        "statuses": [stat.value for stat in ExpenseStatus],
        "statistics": stats
    }
    return templates.TemplateResponse("expenses/expenses_list.html", context)


@router.get("/create", name="expense_create_form")
def expense_create_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance"]))
):
    """Form to create a new expense."""
    context = {
        "request": request,
        "title": "Create Expense",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "categories": [cat.value for cat in ExpenseCategory],
        "statuses": [stat.value for stat in ExpenseStatus],
        "today": date.today().strftime('%Y-%m-%d')
    }
    return templates.TemplateResponse("expenses/expense_form.html", context)


@router.post("/create", name="create_expense", status_code=302)
def create_expense(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance"])),
    description: str = Form(...),
    category: str = Form(...),
    amount: str = Form(...),
    currency: str = Form("GHS"),
    vendor_name: Optional[str] = Form(None),
    vendor_contact: Optional[str] = Form(None),
    invoice_number: Optional[str] = Form(None),
    status: str = Form("pending"),
    payment_method: Optional[str] = Form(None),
    expense_date: Optional[str] = Form(None),
    due_date: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    notes: Optional[str] = Form(None)
):
    """Create a new expense."""
    try:
        amount_decimal = Decimal(amount)
        expense_category = ExpenseCategory(category)
        expense_status = ExpenseStatus(status)
        
        expense_date_obj = datetime.now()
        if expense_date:
            expense_date_obj = datetime.strptime(expense_date, "%Y-%m-%d")
        
        due_date_obj = None
        if due_date:
            due_date_obj = datetime.strptime(due_date, "%Y-%m-%d")
        
        expense_data = ExpenseCreate(
            description=description,
            category=expense_category,
            amount=amount_decimal,
            currency=currency,
            vendor_name=vendor_name,
            vendor_contact=vendor_contact,
            invoice_number=invoice_number,
            status=expense_status,
            payment_method=payment_method,
            expense_date=expense_date_obj,
            due_date=due_date_obj,
            department=department,
            notes=notes
        )
        
        expense = expense_crud.create_expense(db, expense_data, current_user.id)
        
        return RedirectResponse(
            url=request.url_for("expense_detail", expense_id=expense.id),
            status_code=302
        )
    except Exception as e:
        return RedirectResponse(
            url=request.url_for("expense_create_form") + f"?error={str(e)}",
            status_code=302
        )


@router.get("/report", name="expense_report")
def expense_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    format: str = Query("html", regex="^(html|pdf)$"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Management"]))
):
    """Generate expense report."""
    # Parse dates
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = date.today() - timedelta(days=30)
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = date.today()
    
    # Get expenses
    expense_category = None
    if category:
        try:
            expense_category = ExpenseCategory(category)
        except ValueError:
            pass
    
    expenses, total_count = expense_crud.get_expenses(
        db, skip=0, limit=10000,
        category=expense_category,
        start_date=start,
        end_date=end
    )
    
    # Get statistics
    stats = expense_crud.get_expense_statistics(db, start_date=start, end_date=end)
    
    context = {
        "request": request,
        "title": "Expense Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "expenses": expenses,
        "start_date": start,
        "end_date": end,
        "category": category,
        "statistics": stats,
        "report_date": datetime.now()
    }
    
    if format == "pdf":
        from app.utils.pdf_generator import generate_expense_report_pdf
        pdf_content = generate_expense_report_pdf(context)
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=expense_report_{start}_{end}.pdf"
            }
        )
    
    return templates.TemplateResponse("expenses/expense_report.html", context)


@router.get("/{expense_id}", name="expense_detail")
def expense_detail(
    request: Request,
    expense_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Management"]))
):
    """View expense details."""
    expense = expense_crud.get_expense(db, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    context = {
        "request": request,
        "title": f"Expense: {expense.expense_number}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "expense": expense
    }
    return templates.TemplateResponse("expenses/expense_detail.html", context)


@router.get("/{expense_id}/edit", name="expense_edit_form")
def expense_edit_form(
    request: Request,
    expense_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance"]))
):
    """Form to edit an expense."""
    expense = expense_crud.get_expense(db, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    context = {
        "request": request,
        "title": f"Edit Expense: {expense.expense_number}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "expense": expense,
        "categories": [cat.value for cat in ExpenseCategory],
        "statuses": [stat.value for stat in ExpenseStatus],
        "today": date.today().strftime('%Y-%m-%d')
    }
    return templates.TemplateResponse("expenses/expense_form.html", context)


@router.post("/{expense_id}/update", name="update_expense", status_code=302)
def update_expense(
    request: Request,
    expense_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance"])),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    amount: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    approved: Optional[str] = Form(None),
    payment_method: Optional[str] = Form(None),
    payment_date: Optional[str] = Form(None),
    payment_reference: Optional[str] = Form(None),
    notes: Optional[str] = Form(None)
):
    """Update an expense."""
    try:
        update_data = {}
        
        if description:
            update_data["description"] = description
        if category:
            update_data["category"] = ExpenseCategory(category)
        if amount:
            update_data["amount"] = Decimal(amount)
        if status:
            update_data["status"] = ExpenseStatus(status)
        if approved == "yes" and current_user.role.name == "Admin":
            update_data["status"] = ExpenseStatus.APPROVED
            update_data["approved_by_id"] = current_user.id
        if payment_method:
            update_data["payment_method"] = payment_method
        if payment_date:
            update_data["payment_date"] = datetime.strptime(payment_date, "%Y-%m-%d")
        if payment_reference:
            update_data["payment_reference"] = payment_reference
        if notes is not None:
            update_data["notes"] = notes
        
        expense_update = ExpenseUpdate(**update_data)
        expense = expense_crud.update_expense(db, expense_id, expense_update)
        
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        return RedirectResponse(
            url=request.url_for("expense_detail", expense_id=expense_id),
            status_code=302
        )
    except Exception as e:
        return RedirectResponse(
            url=request.url_for("expense_edit_form", expense_id=expense_id) + f"?error={str(e)}",
            status_code=302
        )

