"""
Expense CRUD Operations

Database operations for expense management.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal

from app.models.expense_models import Expense, ExpenseCategory, ExpenseStatus
from app.schemas.expense_schemas import ExpenseCreate, ExpenseUpdate


def generate_expense_number(db: Session) -> str:
    """Generate a unique expense number."""
    # Get the count of expenses today
    today = date.today()
    count = db.query(Expense).filter(
        func.date(Expense.created_at) == today
    ).count()
    
    # Format: EXP-YYYYMMDD-XXX
    return f"EXP-{today.strftime('%Y%m%d')}-{str(count + 1).zfill(3)}"


def create_expense(db: Session, expense: ExpenseCreate, created_by_id: int) -> Expense:
    """Create a new expense."""
    expense_number = generate_expense_number(db)
    
    db_expense = Expense(
        expense_number=expense_number,
        description=expense.description,
        category=expense.category,
        amount=expense.amount,
        currency=expense.currency,
        vendor_name=expense.vendor_name,
        vendor_contact=expense.vendor_contact,
        invoice_number=expense.invoice_number,
        status=expense.status,
        payment_method=expense.payment_method,
        payment_date=expense.payment_date,
        payment_reference=expense.payment_reference,
        expense_date=expense.expense_date,
        due_date=expense.due_date,
        notes=expense.notes,
        receipt_path=expense.receipt_path,
        department=expense.department,
        created_by_id=created_by_id,
        is_active=True
    )
    
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense


def get_expense(db: Session, expense_id: int) -> Optional[Expense]:
    """Get an expense by ID."""
    return db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.is_active == True
    ).first()


def get_expenses(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    category: Optional[ExpenseCategory] = None,
    status: Optional[ExpenseStatus] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    department: Optional[str] = None
) -> tuple[List[Expense], int]:
    """Get expenses with filtering and pagination."""
    query = db.query(Expense).filter(Expense.is_active == True)
    
    if category:
        query = query.filter(Expense.category == category)
    
    if status:
        query = query.filter(Expense.status == status)
    
    if start_date:
        query = query.filter(func.date(Expense.expense_date) >= start_date)
    
    if end_date:
        query = query.filter(func.date(Expense.expense_date) <= end_date)
    
    if department:
        query = query.filter(Expense.department == department)
    
    total_count = query.count()
    expenses = query.order_by(Expense.expense_date.desc()).offset(skip).limit(limit).all()
    
    return expenses, total_count


def update_expense(db: Session, expense_id: int, expense_update: ExpenseUpdate) -> Optional[Expense]:
    """Update an expense."""
    db_expense = get_expense(db, expense_id)
    if not db_expense:
        return None
    
    update_data = expense_update.model_dump(exclude_unset=True)
    
    # Handle approval
    if "status" in update_data and update_data["status"] == ExpenseStatus.APPROVED:
        if not db_expense.approved_at:
            update_data["approved_at"] = datetime.now()
    
    for field, value in update_data.items():
        setattr(db_expense, field, value)
    
    db.commit()
    db.refresh(db_expense)
    return db_expense


def delete_expense(db: Session, expense_id: int) -> bool:
    """Soft delete an expense."""
    db_expense = get_expense(db, expense_id)
    if not db_expense:
        return False
    
    db_expense.is_active = False
    db.commit()
    return True


def get_expense_statistics(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> dict:
    """Get expense statistics."""
    query = db.query(Expense).filter(Expense.is_active == True)
    
    if start_date:
        query = query.filter(func.date(Expense.expense_date) >= start_date)
    
    if end_date:
        query = query.filter(func.date(Expense.expense_date) <= end_date)
    
    expenses = query.all()
    
    total_expenses = sum([exp.amount for exp in expenses])
    
    # Breakdown by category
    category_breakdown = {}
    for expense in expenses:
        category = expense.category.value
        if category not in category_breakdown:
            category_breakdown[category] = Decimal('0.00')
        category_breakdown[category] += expense.amount
    
    # Breakdown by status
    status_breakdown = {}
    for expense in expenses:
        status = expense.status.value
        if status not in status_breakdown:
            status_breakdown[status] = {"count": 0, "amount": Decimal('0.00')}
        status_breakdown[status]["count"] += 1
        status_breakdown[status]["amount"] += expense.amount
    
    return {
        "total_expenses": total_expenses,
        "total_count": len(expenses),
        "category_breakdown": category_breakdown,
        "status_breakdown": status_breakdown
    }

