from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from app.core.templates import templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from typing import Optional, List
from decimal import Decimal

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.encounter_models import Prescription
from app.models.inventory_models import Medication, StockItem, InventoryTransaction, TransactionType, StockStatus
from datetime import datetime
from app.crud import inventory_crud
from app.schemas.inventory_schemas import (
    MedicationCreate, StockItemCreate, InventoryTransactionCreate,
    StockCheckRequest, DrugInteractionCheckRequest, FormularyCheckRequest
)

router = APIRouter(tags=["Inventory"])


# Medication Routes
@router.get("/pharmacy/inventory", name="inventory_dashboard")
def inventory_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"])),
    search: Optional[str] = Query(None),
    low_stock: Optional[bool] = Query(None),
    out_of_stock: Optional[bool] = Query(None),
    expired: Optional[bool] = Query(None)
):
    """Inventory dashboard"""
    from sqlalchemy import func, or_
    from app.models.inventory_models import StockItem, StockStatus
    
    # Get medications with stock summary
    query = db.query(Medication).filter(Medication.is_active == True)
    
    if search:
        query = query.filter(
            or_(
                Medication.name.ilike(f"%{search}%"),
                Medication.generic_name.ilike(f"%{search}%"),
                Medication.medication_code.ilike(f"%{search}%")
            )
        )
    
    medications = query.order_by(Medication.name).limit(200).all()
    
    # Calculate stock totals for each medication
    medication_stock = {}
    for med in medications:
        stock_items = inventory_crud.get_stock_items_by_medication(db, med.id)
        total_quantity = sum(item.quantity for item in stock_items if item.is_active)
        available_quantity = sum(item.available_quantity for item in stock_items if item.is_active)
        
        # Check for low stock
        is_low_stock = med.reorder_level and total_quantity <= med.reorder_level
        is_out_of_stock = total_quantity == 0
        has_expired = any(
            item.expiry_date and item.expiry_date < datetime.now() and item.quantity > 0
            for item in stock_items if item.is_active
        )
        
        medication_stock[med.id] = {
            "total_quantity": total_quantity,
            "available_quantity": available_quantity,
            "is_low_stock": is_low_stock,
            "is_out_of_stock": is_out_of_stock,
            "has_expired": has_expired,
            "stock_items": stock_items
        }
    
    # Apply filters
    if low_stock:
        medications = [m for m in medications if medication_stock[m.id]["is_low_stock"]]
    if out_of_stock:
        medications = [m for m in medications if medication_stock[m.id]["is_out_of_stock"]]
    if expired:
        medications = [m for m in medications if medication_stock[m.id]["has_expired"]]
    
    context = {
        "request": request,
        "title": "Pharmacy Inventory",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "medications": medications,
        "medication_stock": medication_stock,
        "search": search,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
        "expired": expired
    }
    return templates.TemplateResponse("inventory/dashboard.html", context)


@router.get("/pharmacy/inventory/medications/new", name="create_medication_page")
def create_medication_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"]))
):
    """Page for creating a new medication"""
    from app.crud import supplier_crud
    suppliers = supplier_crud.get_suppliers(db)
    
    context = {
        "request": request,
        "title": "Add New Medication",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "suppliers": suppliers
    }
    return templates.TemplateResponse("inventory/create_medication.html", context)


@router.get("/pharmacy/inventory/medications/{medication_id}/edit", name="edit_medication_page")
def edit_medication_page(
    request: Request,
    medication_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"]))
):
    """Page for editing a medication"""
    from app.crud import supplier_crud
    medication = inventory_crud.get_medication(db, medication_id)
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    suppliers = supplier_crud.get_suppliers(db)
    
    context = {
        "request": request,
        "title": f"Edit Medication: {medication.name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "medication": medication,
        "suppliers": suppliers
    }
    return templates.TemplateResponse("inventory/edit_medication.html", context)


@router.get("/pharmacy/inventory/medications/{medication_id}", name="view_medication")
def view_medication(
    request: Request,
    medication_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"]))
):
    """View medication details and stock"""
    medication = inventory_crud.get_medication(db, medication_id)
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    stock_items = inventory_crud.get_stock_items_by_medication(db, medication_id)
    transactions = inventory_crud.get_inventory_transactions(db, medication_id=medication_id, limit=50)
    
    # Stock check
    stock_check = inventory_crud.check_stock_availability(db, medication_id, 1)
    
    context = {
        "request": request,
        "title": f"Medication: {medication.name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "medication": medication,
        "stock_items": stock_items,
        "transactions": transactions,
        "stock_check": stock_check,
        "now": datetime.now()
    }
    return templates.TemplateResponse("inventory/medication_detail.html", context)


@router.post("/pharmacy/inventory/medications", name="create_medication", status_code=302)
def create_medication(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"])),
    name: str = Form(...),
    generic_name: Optional[str] = Form(None),
    brand_name: Optional[str] = Form(None),
    medication_code: Optional[str] = Form(None),
    dosage_form: Optional[str] = Form(None),
    strength: Optional[str] = Form(None),
    unit: Optional[str] = Form(None),
    is_nhis_covered: bool = Form(False),
    nhis_code: Optional[str] = Form(None),
    is_formulary: bool = Form(True),
    unit_cost: Optional[str] = Form(None),
    unit_price: Optional[str] = Form(None),
    reorder_level: Optional[int] = Form(None),
    reorder_quantity: Optional[int] = Form(None)
):
    """Create a new medication"""
    try:
        medication_data = MedicationCreate(
            name=name,
            generic_name=generic_name,
            brand_name=brand_name,
            medication_code=medication_code if medication_code else None,
            dosage_form=dosage_form,
            strength=strength,
            unit=unit,
            is_nhis_covered=is_nhis_covered,
            nhis_code=nhis_code,
            is_formulary=is_formulary,
            unit_cost=Decimal(unit_cost) if unit_cost else None,
            unit_price=Decimal(unit_price) if unit_price else None,
            reorder_level=reorder_level,
            reorder_quantity=reorder_quantity
        )
        
        medication = inventory_crud.create_medication(db, medication_data)
        return RedirectResponse(
            url=f"/pharmacy/inventory/medications/{medication.id}?status=created",
            status_code=302
        )
    except Exception as e:
        from app.crud import supplier_crud
        suppliers = supplier_crud.get_suppliers(db)
        context = {
            "request": request,
            "title": "Add New Medication",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "suppliers": suppliers,
            "error": f"Error creating medication: {str(e)}"
        }
        return templates.TemplateResponse("inventory/create_medication.html", context)


@router.post("/pharmacy/inventory/medications/{medication_id}/edit", name="update_medication", status_code=302)
def update_medication(
    request: Request,
    medication_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"])),
    name: Optional[str] = Form(None),
    generic_name: Optional[str] = Form(None),
    brand_name: Optional[str] = Form(None),
    medication_code: Optional[str] = Form(None),
    dosage_form: Optional[str] = Form(None),
    strength: Optional[str] = Form(None),
    unit: Optional[str] = Form(None),
    is_nhis_covered: Optional[bool] = Form(None),
    nhis_code: Optional[str] = Form(None),
    is_formulary: Optional[bool] = Form(None),
    unit_cost: Optional[str] = Form(None),
    unit_price: Optional[str] = Form(None),
    reorder_level: Optional[int] = Form(None),
    reorder_quantity: Optional[int] = Form(None)
):
    """Update a medication"""
    from app.schemas.inventory_schemas import MedicationUpdate
    
    medication = inventory_crud.get_medication(db, medication_id)
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    try:
        update_data = {}
        if name is not None:
            update_data['name'] = name
        if generic_name is not None:
            update_data['generic_name'] = generic_name
        if brand_name is not None:
            update_data['brand_name'] = brand_name
        if medication_code is not None:
            update_data['medication_code'] = medication_code
        if dosage_form is not None:
            update_data['dosage_form'] = dosage_form
        if strength is not None:
            update_data['strength'] = strength
        if unit is not None:
            update_data['unit'] = unit
        if is_nhis_covered is not None:
            update_data['is_nhis_covered'] = is_nhis_covered
        if nhis_code is not None:
            update_data['nhis_code'] = nhis_code
        if is_formulary is not None:
            update_data['is_formulary'] = is_formulary
        if unit_cost is not None:
            update_data['unit_cost'] = Decimal(unit_cost) if unit_cost else None
        if unit_price is not None:
            update_data['unit_price'] = Decimal(unit_price) if unit_price else None
        if reorder_level is not None:
            update_data['reorder_level'] = reorder_level
        if reorder_quantity is not None:
            update_data['reorder_quantity'] = reorder_quantity
        
        medication_update = MedicationUpdate(**update_data)
        inventory_crud.update_medication(db, medication_id, medication_update)
        
        return RedirectResponse(
            url=f"/pharmacy/inventory/medications/{medication_id}?status=updated",
            status_code=302
        )
    except Exception as e:
        from app.crud import supplier_crud
        suppliers = supplier_crud.get_suppliers(db)
        context = {
            "request": request,
            "title": f"Edit Medication: {medication.name}",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "medication": medication,
            "suppliers": suppliers,
            "error": f"Error updating medication: {str(e)}"
        }
        return templates.TemplateResponse("inventory/edit_medication.html", context)


@router.post("/pharmacy/inventory/medications/{medication_id}/delete", name="delete_medication", status_code=302)
def delete_medication(
    request: Request,
    medication_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Soft delete a medication"""
    medication = inventory_crud.get_medication(db, medication_id)
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    # Soft delete
    medication.is_active = False
    db.commit()
    
    return RedirectResponse(
        url=f"/pharmacy/inventory?status=deleted",
        status_code=302
    )


@router.get("/pharmacy/inventory/medications/{medication_id}/add-stock", name="add_stock_page")
def add_stock_page(
    request: Request,
    medication_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"]))
):
    """Page for adding stock to a medication"""
    from app.crud import supplier_crud
    medication = inventory_crud.get_medication(db, medication_id)
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    suppliers = supplier_crud.get_suppliers(db)
    
    context = {
        "request": request,
        "title": f"Add Stock: {medication.name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "medication": medication,
        "suppliers": suppliers
    }
    return templates.TemplateResponse("inventory/add_stock.html", context)


@router.post("/pharmacy/inventory/stock-items", name="create_stock_item", status_code=302)
def create_stock_item(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"])),
    medication_id: int = Form(...),
    batch_number: Optional[str] = Form(None),
    quantity: int = Form(...),
    expiry_date: Optional[str] = Form(None),
    manufacturing_date: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    supplier_id: Optional[int] = Form(None),
    supplier: Optional[str] = Form(None),
    purchase_price: Optional[str] = Form(None),
    purchase_date: Optional[str] = Form(None)
):
    """Add stock to inventory"""
    from datetime import datetime
    
    try:
        stock_data = StockItemCreate(
            medication_id=medication_id,
            batch_number=batch_number,
            quantity=quantity,
            expiry_date=datetime.fromisoformat(expiry_date) if expiry_date else None,
            manufacturing_date=datetime.fromisoformat(manufacturing_date) if manufacturing_date else None,
            location=location,
            supplier_id=supplier_id,
            supplier=supplier,
            purchase_price=Decimal(purchase_price) if purchase_price else None,
            purchase_date=datetime.fromisoformat(purchase_date) if purchase_date else None
        )
        
        stock_item = inventory_crud.create_stock_item(db, stock_data)
        
        # Create purchase transaction
        transaction_data = InventoryTransactionCreate(
            medication_id=medication_id,
            stock_item_id=stock_item.id,
            transaction_type=TransactionType.PURCHASE,
            quantity=quantity,
            unit_cost=Decimal(purchase_price) if purchase_price else None,
            notes=f"Stock added: Batch {batch_number or 'N/A'}"
        )
        inventory_crud.create_inventory_transaction(db, transaction_data, current_user.id)
        
        return RedirectResponse(
            url=f"/pharmacy/inventory/medications/{medication_id}?status=stock_added",
            status_code=302
        )
    except Exception as e:
        from app.crud import supplier_crud
        medication = inventory_crud.get_medication(db, medication_id)
        suppliers = supplier_crud.get_suppliers(db)
        context = {
            "request": request,
            "title": f"Add Stock: {medication.name if medication else 'Unknown'}",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "medication": medication,
            "suppliers": suppliers,
            "error": f"Error adding stock: {str(e)}"
        }
        return templates.TemplateResponse("inventory/add_stock.html", context)


@router.post("/pharmacy/inventory/stock-items/{stock_item_id}/adjust", name="adjust_stock", status_code=302)
def adjust_stock(
    request: Request,
    stock_item_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"])),
    adjustment_quantity: int = Form(...),
    adjustment_type: str = Form(...),
    notes: Optional[str] = Form(None)
):
    """Adjust stock quantity (add or remove)"""
    stock_item = inventory_crud.get_stock_item(db, stock_item_id)
    if not stock_item:
        raise HTTPException(status_code=404, detail="Stock item not found")
    
    try:
        # Determine transaction type
        if adjustment_type == "add":
            transaction_type = TransactionType.ADJUSTMENT
            quantity_change = abs(adjustment_quantity)
            stock_item.quantity += quantity_change
            stock_item.available_quantity += quantity_change
        elif adjustment_type == "remove":
            transaction_type = TransactionType.ADJUSTMENT
            quantity_change = -abs(adjustment_quantity)
            if stock_item.quantity < abs(quantity_change):
                raise ValueError("Insufficient stock for adjustment")
            stock_item.quantity += quantity_change
            stock_item.available_quantity += quantity_change
        elif adjustment_type == "expiry":
            transaction_type = TransactionType.EXPIRY
            quantity_change = -abs(adjustment_quantity)
            if stock_item.quantity < abs(quantity_change):
                raise ValueError("Insufficient stock for expiry adjustment")
            stock_item.quantity += quantity_change
            stock_item.available_quantity += quantity_change
        elif adjustment_type == "damage":
            transaction_type = TransactionType.DAMAGE
            quantity_change = -abs(adjustment_quantity)
            if stock_item.quantity < abs(quantity_change):
                raise ValueError("Insufficient stock for damage adjustment")
            stock_item.quantity += quantity_change
            stock_item.available_quantity += quantity_change
        else:
            raise ValueError("Invalid adjustment type")
        
        db.commit()
        
        # Create transaction record
        transaction_data = InventoryTransactionCreate(
            medication_id=stock_item.medication_id,
            stock_item_id=stock_item_id,
            transaction_type=transaction_type,
            quantity=quantity_change,
            notes=notes or f"Stock adjustment: {adjustment_type}"
        )
        inventory_crud.create_inventory_transaction(db, transaction_data, current_user.id)
        
        return RedirectResponse(
            url=f"/pharmacy/inventory/medications/{stock_item.medication_id}?status=stock_adjusted",
            status_code=302
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/pharmacy/inventory/medications/{stock_item.medication_id}?error={str(e)}",
            status_code=302
        )


# Stock Check API
@router.get("/api/v1/inventory/medications/search", name="search_medications")
def search_medications_api(
    search: Optional[str] = Query(None, min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Search medications from inventory for autocomplete"""
    from fastapi.responses import JSONResponse
    
    # If no search term, return empty results
    if not search or len(search.strip()) < 1:
        return JSONResponse(content={"medications": []})
    
    medications = inventory_crud.get_medications(db, search=search, limit=limit)
    
    results = []
    for med in medications:
        # Check stock availability
        try:
            stock_check = inventory_crud.check_stock_availability(db, med.id, 1)
            in_stock = stock_check.is_available if stock_check else False
            available_quantity = stock_check.available_quantity if stock_check else 0
        except Exception:
            # If stock check fails, assume not in stock
            in_stock = False
            available_quantity = 0
        
        results.append({
            "id": med.id,
            "name": med.name,
            "generic_name": med.generic_name,
            "brand_name": med.brand_name,
            "medication_code": med.medication_code,
            "strength": med.strength,
            "dosage_form": med.dosage_form,
            "unit": med.unit,
            "unit_price": float(med.unit_price) if med.unit_price else None,
            "in_stock": in_stock,
            "available_quantity": available_quantity
        })
    
    return JSONResponse(content={"medications": results})


@router.get("/api/v1/inventory/check-stock/{medication_id}", name="api_check_stock")
def api_check_stock(
    medication_id: int,
    required_quantity: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """API endpoint to check stock availability"""
    try:
        stock_check = inventory_crud.check_stock_availability(db, medication_id, required_quantity)
        return stock_check
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Formulary Check API
@router.get("/api/v1/inventory/check-formulary/{medication_id}", name="api_check_formulary")
def api_check_formulary(
    medication_id: int,
    patient_nhis_number: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """API endpoint to check formulary compliance"""
    try:
        formulary_check = inventory_crud.check_formulary_compliance(db, medication_id, patient_nhis_number)
        return formulary_check
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Drug Interaction Check API
@router.post("/api/v1/inventory/check-interactions", name="api_check_interactions")
def api_check_interactions(
    request: DrugInteractionCheckRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """API endpoint to check drug interactions"""
    interaction_check = inventory_crud.check_drug_interactions(db, request.medication_ids)
    return interaction_check


# Integrate with prescription dispensing
@router.post("/pharmacy/prescriptions/{prescription_id}/check-availability", name="check_prescription_availability")
def check_prescription_availability(
    request: Request,
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"]))
):
    """Check if prescription medication is available"""
    from app.crud import encounter_crud
    
    prescription = encounter_crud.get_prescription(db, prescription_id)
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Try to find medication by name or code
    medication = None
    if prescription.medication_code:
        medication = inventory_crud.get_medication_by_code(db, prescription.medication_code)
    
    if not medication:
        # Search by name
        medications = inventory_crud.get_medications(db, search=prescription.medication_name, limit=1)
        if medications:
            medication = medications[0]
    
    context = {
        "request": request,
        "title": "Check Prescription Availability",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "prescription": prescription,
        "medication": medication
    }
    
    if medication:
        stock_check = inventory_crud.check_stock_availability(db, medication.id, prescription.quantity or 1)
        context["stock_check"] = stock_check
        
        # Check formulary
        patient = prescription.encounter.patient
        formulary_check = inventory_crud.check_formulary_compliance(
            db, medication.id, patient.nhis_number
        )
        context["formulary_check"] = formulary_check
    
    return templates.TemplateResponse("inventory/prescription_check.html", context)

