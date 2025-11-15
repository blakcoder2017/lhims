from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.supplier_models import Supplier
from app.crud import supplier_crud
from app.schemas.supplier_schemas import SupplierCreate

router = APIRouter(tags=["Suppliers"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/pharmacy/suppliers", name="suppliers_dashboard")
def suppliers_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"])),
    search: Optional[str] = Query(None)
):
    """Suppliers management dashboard"""
    suppliers = supplier_crud.get_suppliers(db, search=search, limit=100)
    
    context = {
        "request": request,
        "title": "Supplier Management",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "suppliers": suppliers,
        "search": search
    }
    return templates.TemplateResponse("inventory/suppliers_dashboard.html", context)


@router.get("/pharmacy/suppliers/{supplier_id}", name="view_supplier")
def view_supplier(
    request: Request,
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"]))
):
    """View supplier details"""
    from app.models.inventory_models import StockItem
    from sqlalchemy.orm import joinedload
    
    supplier = supplier_crud.get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Get stock items from this supplier with medication relationship
    stock_items = db.query(StockItem).options(
        joinedload(StockItem.medication)
    ).filter(
        StockItem.supplier_id == supplier_id,
        StockItem.is_active == True
    ).limit(50).all()
    
    context = {
        "request": request,
        "title": f"Supplier: {supplier.name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "supplier": supplier,
        "stock_items": stock_items
    }
    return templates.TemplateResponse("inventory/supplier_detail.html", context)


@router.post("/pharmacy/suppliers", name="create_supplier", status_code=302)
def create_supplier(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"])),
    name: str = Form(...),
    code: Optional[str] = Form(None),
    contact_person: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None)
):
    """Create a new supplier"""
    # Convert empty strings to None for optional fields
    supplier_data = SupplierCreate(
        name=name,
        code=code if code else None,
        contact_person=contact_person if contact_person else None,
        email=email if email and email.strip() else None,
        phone=phone if phone else None,
        address=address if address else None
    )
    
    supplier = supplier_crud.create_supplier(db, supplier_data)
    return RedirectResponse(url=f"/pharmacy/suppliers/{supplier.id}", status_code=302)

