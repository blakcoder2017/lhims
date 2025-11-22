from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.supplier_models import Supplier
from app.crud import supplier_crud
from app.schemas.supplier_schemas import SupplierCreate, SupplierUpdate
from fastapi import status

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
    return RedirectResponse(
        url=str(request.url_for("suppliers_dashboard")) + f"?status=supplier_created&supplier_id={supplier.id}",
        status_code=status.HTTP_302_FOUND
    )


@router.post("/pharmacy/suppliers/{supplier_id}/update", name="update_supplier", status_code=302)
def update_supplier(
    request: Request,
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"])),
    name: str = Form(...),
    code: Optional[str] = Form(None),
    contact_person: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    mobile: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    tax_id: Optional[str] = Form(None),
    registration_number: Optional[str] = Form(None),
    payment_terms: Optional[str] = Form(None),
    credit_limit: Optional[str] = Form(None)
):
    """Update an existing supplier"""
    supplier = supplier_crud.get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    try:
        # Convert empty strings to None for optional fields
        from decimal import Decimal
        
        credit_limit_decimal = None
        if credit_limit and credit_limit.strip():
            try:
                credit_limit_decimal = Decimal(credit_limit.strip())
            except:
                credit_limit_decimal = None
        
        supplier_update = SupplierUpdate(
            name=name,
            code=code if code and code.strip() else None,
            contact_person=contact_person if contact_person and contact_person.strip() else None,
            email=email if email and email.strip() else None,
            phone=phone if phone and phone.strip() else None,
            mobile=mobile if mobile and mobile.strip() else None,
            address=address if address and address.strip() else None,
            city=city if city and city.strip() else None,
            country=country if country and country.strip() else None,
            tax_id=tax_id if tax_id and tax_id.strip() else None,
            registration_number=registration_number if registration_number and registration_number.strip() else None,
            payment_terms=payment_terms if payment_terms and payment_terms.strip() else None,
            credit_limit=credit_limit_decimal
        )
        
        updated_supplier = supplier_crud.update_supplier(db, supplier_id, supplier_update)
        if not updated_supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        
        return RedirectResponse(
            url=str(request.url_for("view_supplier", supplier_id=supplier_id)) + "?status=updated",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("view_supplier", supplier_id=supplier_id)) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/pharmacy/suppliers/{supplier_id}/delete", name="delete_supplier", status_code=302)
def delete_supplier(
    request: Request,
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"]))
):
    """Delete (soft delete) a supplier"""
    supplier = supplier_crud.get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Check if supplier has active stock items
    from app.models.inventory_models import StockItem
    active_stock_items = db.query(StockItem).filter(
        StockItem.supplier_id == supplier_id,
        StockItem.is_active == True
    ).count()
    
    if active_stock_items > 0:
        return RedirectResponse(
            url=str(request.url_for("suppliers_dashboard")) + f"?error=Cannot delete supplier. It has {active_stock_items} active stock item(s). Please remove or transfer stock items first.",
            status_code=status.HTTP_302_FOUND
        )
    
    # Soft delete the supplier
    success = supplier_crud.delete_supplier(db, supplier_id)
    if not success:
        return RedirectResponse(
            url=str(request.url_for("suppliers_dashboard")) + "?error=Failed to delete supplier",
            status_code=status.HTTP_302_FOUND
        )
    
    return RedirectResponse(
        url=str(request.url_for("suppliers_dashboard")) + f"?status=supplier_deleted&supplier_id={supplier_id}",
        status_code=status.HTTP_302_FOUND
    )

