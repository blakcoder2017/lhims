"""
Pharmacy Ghana-Ready UI Routes
- Drug catalogue (formulations)
- Batch management, stock-in
- Dashboard (low stock, near expiry, expired)
- Controlled register report
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from typing import Optional

from app.db.database import get_db
from app.core.deps import role_required
from app.core.templates import templates
from app.models.pharmacy_models import (
    PharmacyDosageForm, PharmacyDrug, PharmacySupplier, PharmacyStore,
    PharmacyBatch, PharmacyRolePolicy, PharmacyDispense, PharmacyDispenseItem,
    PharmacyDispenseAllocation,
)
from app.models.encounter_models import OrderStatus
from app.models.billing_models import Invoice, InvoiceStatus, Charge, ChargeType

router = APIRouter(tags=["Pharmacy Ghana UI"])


def _can_view_cost(db: Session, role_name: str) -> bool:
    p = db.query(PharmacyRolePolicy).filter(PharmacyRolePolicy.role_name == role_name).first()
    if p:
        return p.can_view_unit_cost
    return role_name and role_name.lower() == "admin"


@router.get("/pharmacy/ghana", name="pharmacy_ghana_dashboard")
def pharmacy_ghana_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Ghana pharmacy dashboard: low stock, near expiry, expired."""
    today = date.today()
    cutoff_90 = today + timedelta(days=90)
    
    batches = db.query(PharmacyBatch).options(
        joinedload(PharmacyBatch.drug),
        joinedload(PharmacyBatch.store),
    ).filter(
        PharmacyBatch.status == "ACTIVE",
        PharmacyBatch.qty_on_hand > 0,
    ).all()
    
    near_expiry = [b for b in batches if today <= b.expiry_date <= cutoff_90]
    expired = [b for b in batches if b.expiry_date < today]
    low_stock = []
    for b in batches:
        if b.drug and b.drug.reorder_level and b.qty_on_hand <= b.drug.reorder_level:
            low_stock.append(b)
    
    stores = db.query(PharmacyStore).all()
    drugs_count = db.query(PharmacyDrug).filter(PharmacyDrug.is_active == True).count()
    
    context = {
        "request": request,
        "title": "Pharmacy Ghana - Dashboard",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "near_expiry": sorted(near_expiry, key=lambda x: x.expiry_date)[:50],
        "expired": sorted(expired, key=lambda x: x.expiry_date)[:30],
        "low_stock": low_stock[:50],
        "stores": stores,
        "drugs_count": drugs_count,
        "can_view_cost": _can_view_cost(db, current_user.role.name),
        "hospital_settings": hospital_settings_crud.get_hospital_settings(db),
    }
    return templates.TemplateResponse("pharmacy_ghana/dashboard.html", context)


@router.get("/pharmacy/ghana/drugs", name="pharmacy_ghana_drugs")
def pharmacy_ghana_drugs(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    search: Optional[str] = Query(None),
):
    """Drug catalogue (formulations)."""
    q = db.query(PharmacyDrug).options(joinedload(PharmacyDrug.dosage_form)).filter(
        PharmacyDrug.is_active == True
    )
    if search:
        s = f"%{search}%"
        q = q.filter(
            or_(
                PharmacyDrug.generic_name.ilike(s),
                PharmacyDrug.brand_name.ilike(s),
                PharmacyDrug.item_code.ilike(s),
            )
        )
    drugs = q.order_by(PharmacyDrug.generic_name).limit(200).all()
    
    context = {
        "request": request,
        "title": "Pharmacy Drug Catalogue",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "drugs": drugs,
        "search": search,
        "can_view_cost": _can_view_cost(db, current_user.role.name),
    }
    return templates.TemplateResponse("pharmacy_ghana/drugs_list.html", context)


@router.get("/pharmacy/ghana/stores/{store_id}/batches", name="pharmacy_ghana_batches")
def pharmacy_ghana_batches(
    request: Request,
    store_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    drug_id: Optional[str] = Query(None),
):
    """Batch management for a store. Stock-in form with summary dashboard."""
    today = date.today()
    cutoff_90 = today + timedelta(days=90)
    
    # Handle 'default' or empty store_id by getting the first store
    if store_id == 'default' or not store_id:
        store = db.query(PharmacyStore).first()
        if not store:
            raise HTTPException(404, "No pharmacy store found. Please create a store first.")
        store_uuid = store.id
    else:
        try:
            store_uuid = UUID(store_id)
        except ValueError:
            raise HTTPException(400, "Invalid store ID format")
        store = db.query(PharmacyStore).filter(PharmacyStore.id == store_uuid).first()
    
    if not store:
        raise HTTPException(404, "Store not found")
    
    # Base query for batches
    q = db.query(PharmacyBatch).options(
        joinedload(PharmacyBatch.drug),
        joinedload(PharmacyBatch.supplier),
    ).filter(PharmacyBatch.store_id == store_uuid)
    
    if drug_id:
        try:
            q = q.filter(PharmacyBatch.drug_id == UUID(drug_id))
        except ValueError:
            pass
    
    batches = q.order_by(PharmacyBatch.expiry_date).all()
    
    # Calculate summary statistics
    total_batches = len(batches)
    total_stock_value = sum(float(b.qty_on_hand * (b.selling_price or 0)) for b in batches if b.selling_price)
    expired_count = sum(1 for b in batches if b.expiry_date and b.expiry_date < today and b.qty_on_hand > 0)
    near_expiry_count = sum(1 for b in batches if b.expiry_date and today <= b.expiry_date <= cutoff_90 and b.qty_on_hand > 0)
    low_stock_count = 0
    for b in batches:
        if b.drug and b.drug.reorder_level and b.qty_on_hand <= b.drug.reorder_level:
            low_stock_count += 1
    
    # Summary dict for template
    summary = {
        "total_batches": total_batches,
        "total_stock_value": round(total_stock_value, 2),
        "expired_count": expired_count,
        "near_expiry_count": near_expiry_count,
        "low_stock_count": low_stock_count,
    }
    
    drugs = db.query(PharmacyDrug).options(joinedload(PharmacyDrug.dosage_form)).filter(
        PharmacyDrug.is_active == True
    ).order_by(PharmacyDrug.generic_name).all()
    suppliers = db.query(PharmacySupplier).all()
    
    context = {
        "request": request,
        "title": f"Batches - {store.name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "store": store,
        "batches": batches,
        "drugs": drugs,
        "suppliers": suppliers,
        "drug_id": drug_id,
        "can_view_cost": _can_view_cost(db, current_user.role.name),
        "today": today,
        "today_plus_90": cutoff_90,
        "summary": summary,
    }
    return templates.TemplateResponse("pharmacy_ghana/batches.html", context)


@router.get("/pharmacy/ghana/reports/near-expiry", name="pharmacy_ghana_near_expiry")
def pharmacy_ghana_near_expiry(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    days: int = Query(90, ge=1),
    store_id: Optional[str] = Query(None),
):
    """Near-expiry report."""
    today = date.today()
    cutoff = today + timedelta(days=days)
    q = db.query(PharmacyBatch).options(
        joinedload(PharmacyBatch.drug),
        joinedload(PharmacyBatch.store),
    ).filter(
        PharmacyBatch.status == "ACTIVE",
        PharmacyBatch.expiry_date <= cutoff,
        PharmacyBatch.expiry_date >= today,
        PharmacyBatch.qty_on_hand > 0,
    ).order_by(PharmacyBatch.expiry_date)
    
    if store_id and store_id.strip():
        try:
            q = q.filter(PharmacyBatch.store_id == UUID(store_id))
        except (ValueError, TypeError):
            pass
    
    batches = q.all()
    stores = db.query(PharmacyStore).all()
    
    from app.crud import hospital_settings_crud
    
    context = {
        "request": request,
        "title": f"Near Expiry (within {days} days)",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "batches": batches,
        "stores": stores,
        "days": days,
        "store_id": store_id,
        "hospital_settings": hospital_settings_crud.get_hospital_settings(db),
    }
    return templates.TemplateResponse("pharmacy_ghana/near_expiry.html", context)


@router.get("/pharmacy/ghana/reports/controlled-register", name="pharmacy_ghana_controlled_register")
def pharmacy_ghana_controlled_register(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
):
    """Controlled drugs register report."""
    from app.models.pharmacy_models import PharmacyDispense, PharmacyDispenseItem
    from app.models.patient_models import Patient
    
    f = date.today() - timedelta(days=30) if not from_date else date.fromisoformat(from_date)
    t = date.today() if not to_date else date.fromisoformat(to_date)
    
    items = (
        db.query(PharmacyDispenseItem, PharmacyDispense, PharmacyDrug, Patient)
        .join(PharmacyDispense, PharmacyDispenseItem.dispense_id == PharmacyDispense.id)
        .join(PharmacyDrug, PharmacyDispenseItem.drug_id == PharmacyDrug.id)
        .join(Patient, PharmacyDispense.patient_id == Patient.id)
        .filter(
            PharmacyDrug.is_controlled == True,
            PharmacyDispense.status == "DISPENSED",
            func.date(PharmacyDispense.dispensed_at) >= f,
            func.date(PharmacyDispense.dispensed_at) <= t,
        )
        .order_by(PharmacyDispense.dispensed_at)
        .all()
    )
    
    from app.crud import hospital_settings_crud
    
    context = {
        "request": request,
        "title": "Controlled Drugs Register",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "items": items,
        "from_date": f,
        "to_date": t,
        "hospital_settings": hospital_settings_crud.get_hospital_settings(db),
    }
    return templates.TemplateResponse("pharmacy_ghana/controlled_register.html", context)


# --- Drug Management UI ---
@router.get("/pharmacy/drugs", name="pharmacy_drugs")
def pharmacy_drugs(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    search: Optional[str] = Query(None),
):
    """Drug catalogue (formulations) list page."""
    q = db.query(PharmacyDrug).options(joinedload(PharmacyDrug.dosage_form)).filter(
        PharmacyDrug.is_active == True
    )
    if search:
        s = f"%{search}%"
        q = q.filter(
            or_(
                PharmacyDrug.generic_name.ilike(s),
                PharmacyDrug.brand_name.ilike(s),
                PharmacyDrug.item_code.ilike(s),
            )
        )
    drugs = q.order_by(PharmacyDrug.generic_name).limit(200).all()
    
    # Build display labels
    for d in drugs:
        strength = f"{d.strength_value} {d.strength_unit or ''}" if d.strength_value else ""
        if d.concentration_value:
            strength = f"{d.concentration_value} {d.concentration_unit or ''}"
        d._display_label = f"{d.generic_name} {strength} {d.dosage_form.name if d.dosage_form else ''}"
        if d.route:
            d._display_label += f" ({d.route})"
    
    context = {
        "request": request,
        "title": "Pharmacy Drug Catalogue",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "drugs": drugs,
        "search": search,
        "can_view_cost": _can_view_cost(db, current_user.role.name),
    }
    return templates.TemplateResponse("pharmacy_ghana/drugs_list.html", context)


@router.get("/pharmacy/drugs/new", name="pharmacy_drug_new")
def pharmacy_drug_new(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Create new drug page."""
    dosage_forms = db.query(PharmacyDosageForm).order_by(PharmacyDosageForm.name).all()
    
    context = {
        "request": request,
        "title": "Add New Drug",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "dosage_forms": dosage_forms,
    }
    return templates.TemplateResponse("pharmacy_ghana/drug_form.html", context)


@router.post("/pharmacy/drugs/new", name="pharmacy_drug_create")
async def pharmacy_drug_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Create new drug action."""
    from decimal import Decimal
    from fastapi import Form
    form_data = await request.form()
    
    item_code = form_data.get("item_code")
    generic_name = form_data.get("generic_name")
    brand_name = form_data.get("brand_name") or None
    dosage_form_id = form_data.get("dosage_form_id")
    strength_value = form_data.get("strength_value") or None
    strength_unit = form_data.get("strength_unit") or None
    route = form_data.get("route") or None
    concentration_value = form_data.get("concentration_value") or None
    concentration_unit = form_data.get("concentration_unit") or None
    pack_size = form_data.get("pack_size") or None
    reorder_level = form_data.get("reorder_level") or None
    reorder_qty = form_data.get("reorder_qty") or None
    is_controlled = form_data.get("is_controlled") == "on"
    notes = form_data.get("notes") or None
    
    # Check unique item_code
    existing = db.query(PharmacyDrug).filter(PharmacyDrug.item_code == item_code).first()
    if existing:
        dosage_forms = db.query(PharmacyDosageForm).order_by(PharmacyDosageForm.name).all()
        context = {
            "request": request,
            "title": "Add New Drug",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "dosage_forms": dosage_forms,
            "error": f"Item code '{item_code}' already exists",
        }
        return templates.TemplateResponse("pharmacy_ghana/drug_form.html", context)
    
    # Verify dosage_form
    from uuid import UUID
    try:
        df_id = UUID(dosage_form_id)
    except ValueError:
        dosage_forms = db.query(PharmacyDosageForm).order_by(PharmacyDosageForm.name).all()
        context = {
            "request": request,
            "title": "Add New Drug",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "dosage_forms": dosage_forms,
            "error": "Invalid dosage form selected",
        }
        return templates.TemplateResponse("pharmacy_ghana/drug_form.html", context)
    
    drug = PharmacyDrug(
        item_code=item_code,
        generic_name=generic_name,
        brand_name=brand_name,
        dosage_form_id=df_id,
        strength_value=Decimal(str(strength_value)) if strength_value else None,
        strength_unit=strength_unit,
        route=route,
        concentration_value=Decimal(str(concentration_value)) if concentration_value else None,
        concentration_unit=concentration_unit,
        pack_size=int(pack_size) if pack_size else None,
        reorder_level=Decimal(str(reorder_level)) if reorder_level else None,
        reorder_qty=Decimal(str(reorder_qty)) if reorder_qty else None,
        is_controlled=is_controlled,
        notes=notes,
        is_active=True,
    )
    db.add(drug)
    db.commit()
    
    return RedirectResponse(url="/pharmacy/drugs?status=created", status_code=302)


@router.get("/pharmacy/drugs/{drug_id}/edit", name="pharmacy_drug_edit")
def pharmacy_drug_edit(
    request: Request,
    drug_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Edit drug page."""
    from uuid import UUID
    try:
        drug_uuid = UUID(drug_id)
    except ValueError:
        raise HTTPException(400, "Invalid drug ID")
    
    drug = db.query(PharmacyDrug).options(joinedload(PharmacyDrug.dosage_form)).filter(
        PharmacyDrug.id == drug_uuid
    ).first()
    if not drug:
        raise HTTPException(404, "Drug not found")
    
    dosage_forms = db.query(PharmacyDosageForm).order_by(PharmacyDosageForm.name).all()
    
    context = {
        "request": request,
        "title": f"Edit Drug: {drug.generic_name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "drug": drug,
        "dosage_forms": dosage_forms,
    }
    return templates.TemplateResponse("pharmacy_ghana/drug_form.html", context)


@router.post("/pharmacy/drugs/{drug_id}/edit", name="pharmacy_drug_update_ui")
async def pharmacy_drug_update(
    request: Request,
    drug_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Update drug action."""
    from decimal import Decimal
    from uuid import UUID
    
    try:
        drug_uuid = UUID(drug_id)
    except ValueError:
        raise HTTPException(400, "Invalid drug ID")
    
    drug = db.query(PharmacyDrug).filter(PharmacyDrug.id == drug_uuid).first()
    if not drug:
        raise HTTPException(404, "Drug not found")
    
    form_data = await request.form()
    
    item_code = form_data.get("item_code")
    generic_name = form_data.get("generic_name")
    brand_name = form_data.get("brand_name") or None
    dosage_form_id = form_data.get("dosage_form_id")
    strength_value = form_data.get("strength_value") or None
    strength_unit = form_data.get("strength_unit") or None
    route = form_data.get("route") or None
    concentration_value = form_data.get("concentration_value") or None
    concentration_unit = form_data.get("concentration_unit") or None
    pack_size = form_data.get("pack_size") or None
    reorder_level = form_data.get("reorder_level") or None
    reorder_qty = form_data.get("reorder_qty") or None
    is_controlled = form_data.get("is_controlled") == "on"
    notes = form_data.get("notes") or None
    
    # Check unique item_code
    if item_code != drug.item_code:
        existing = db.query(PharmacyDrug).filter(PharmacyDrug.item_code == item_code, PharmacyDrug.id != drug_uuid).first()
        if existing:
            dosage_forms = db.query(PharmacyDosageForm).order_by(PharmacyDosageForm.name).all()
            drug = db.query(PharmacyDrug).options(joinedload(PharmacyDrug.dosage_form)).filter(
                PharmacyDrug.id == drug_uuid
            ).first()
            context = {
                "request": request,
                "title": f"Edit Drug: {drug.generic_name if drug else generic_name}",
                "current_user": current_user,
                "user_role": current_user.role.name,
                "drug": drug,
                "dosage_forms": dosage_forms,
                "error": f"Item code '{item_code}' already exists",
            }
            return templates.TemplateResponse("pharmacy_ghana/drug_form.html", context)
        drug.item_code = item_code
    
    drug.generic_name = generic_name
    drug.brand_name = brand_name
    
    if dosage_form_id:
        try:
            df_id = UUID(dosage_form_id)
            drug.dosage_form_id = df_id
        except ValueError:
            pass
    
    drug.strength_value = Decimal(str(strength_value)) if strength_value else None
    drug.strength_unit = strength_unit
    drug.route = route
    drug.concentration_value = Decimal(str(concentration_value)) if concentration_value else None
    drug.concentration_unit = concentration_unit
    drug.pack_size = int(pack_size) if pack_size else None
    drug.reorder_level = Decimal(str(reorder_level)) if reorder_level else None
    drug.reorder_qty = Decimal(str(reorder_qty)) if reorder_qty else None
    drug.is_controlled = is_controlled
    drug.notes = notes
    
    db.commit()
    
    return RedirectResponse(url="/pharmacy/drugs?status=updated", status_code=302)


# --- Store Management UI ---
@router.get("/pharmacy/stores", name="pharmacy_stores")
def pharmacy_stores(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Store list page."""
    stores = db.query(PharmacyStore).order_by(PharmacyStore.name).all()
    
    context = {
        "request": request,
        "title": "Pharmacy Stores",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "stores": stores,
    }
    return templates.TemplateResponse("pharmacy_ghana/stores_list.html", context)


@router.post("/pharmacy/stores", name="pharmacy_store_create")
async def pharmacy_store_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Create new store."""
    form_data = await request.form()
    
    name = form_data.get("name")
    facility_id = form_data.get("facility_id") or None
    
    if not name:
        stores = db.query(PharmacyStore).order_by(PharmacyStore.name).all()
        context = {
            "request": request,
            "title": "Pharmacy Stores",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "stores": stores,
            "error": "Store name is required",
        }
        return templates.TemplateResponse("pharmacy_ghana/stores_list.html", context)
    
    store = PharmacyStore(
        name=name,
        facility_id=int(facility_id) if facility_id else None,
    )
    db.add(store)
    db.commit()
    
    return RedirectResponse(url="/pharmacy/stores?status=created", status_code=302)


# --- Supplier Management UI ---
@router.get("/pharmacy/suppliers", name="pharmacy_suppliers")
def pharmacy_suppliers(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Supplier list page."""
    suppliers = db.query(PharmacySupplier).order_by(PharmacySupplier.name).all()
    
    context = {
        "request": request,
        "title": "Pharmacy Suppliers",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "suppliers": suppliers,
    }
    return templates.TemplateResponse("pharmacy_ghana/suppliers_list.html", context)


@router.post("/pharmacy/suppliers", name="pharmacy_supplier_create")
async def pharmacy_supplier_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Create new supplier."""
    form_data = await request.form()
    
    name = form_data.get("name")
    phone = form_data.get("phone") or None
    email = form_data.get("email") or None
    address = form_data.get("address") or None
    
    if not name:
        suppliers = db.query(PharmacySupplier).order_by(PharmacySupplier.name).all()
        context = {
            "request": request,
            "title": "Pharmacy Suppliers",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "suppliers": suppliers,
            "error": "Supplier name is required",
        }
        return templates.TemplateResponse("pharmacy_ghana/suppliers_list.html", context)
    
    supplier = PharmacySupplier(
        name=name,
        phone=phone,
        email=email,
        address=address,
    )
    db.add(supplier)
    db.commit()
    
    return RedirectResponse(url="/pharmacy/suppliers?status=created", status_code=302)


# --- Dispense UI ---
@router.get("/pharmacy/dispense/new", name="pharmacy_dispense_new")
def pharmacy_dispense_new(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    patient_id: Optional[int] = Query(None),
):
    """New dispense page."""
    from app.models.patient_models import Patient
    
    patient = None
    dispense = None
    
    if patient_id:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if patient:
            # Check for existing draft or create new
            dispense = db.query(PharmacyDispense).filter(
                PharmacyDispense.patient_id == patient_id,
                PharmacyDispense.status == "DRAFT"
            ).first()
    
    context = {
        "request": request,
        "title": "New Dispense",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient_id": patient_id,
        "patient": patient,
        "dispense": dispense,
    }
    return templates.TemplateResponse("pharmacy_ghana/dispense_new.html", context)


# --- Dispense Create & Add Item (UI Form Handlers) ---
@router.post("/pharmacy/dispense/new", name="pharmacy_dispense_create_ui")
async def pharmacy_dispense_create_ui(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Create new dispense from UI."""
    from app.models.patient_models import Patient
    from fastapi import Form
    
    form_data = await request.form()
    patient_id = form_data.get("patient_id")
    payment_type = form_data.get("payment_type") or "CASH"
    
    if not patient_id:
        return RedirectResponse(url="/pharmacy/dispense/new?error=Patient+required", status_code=302)
    
    try:
        patient_id = int(patient_id)
    except ValueError:
        return RedirectResponse(url="/pharmacy/dispense/new?error=Invalid+patient+ID", status_code=302)
    
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return RedirectResponse(url="/pharmacy/dispense/new?error=Patient+not+found", status_code=302)
    
    # Create new dispense
    dispense = PharmacyDispense(
        patient_id=patient_id,
        status="DRAFT",
        payment_type=payment_type,
    )
    db.add(dispense)
    db.commit()
    db.refresh(dispense)
    
    return RedirectResponse(url=f"/pharmacy/dispense/{dispense.id}", status_code=302)


@router.post("/pharmacy/dispense/{dispense_id}/finalize", name="pharmacy_dispense_finalize_ui")
async def pharmacy_dispense_finalize_ui(
    request: Request,
    dispense_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """
    UI endpoint to finalize a dispense and redirect to prescriptions page.
    This wraps the API finalize logic and provides a redirect response.
    """
    from uuid import UUID
    from datetime import date, datetime, timedelta
    from app.models.pharmacy_models import (
        PharmacyDispense, PharmacyDispenseItem, PharmacyDispenseAllocation,
        PharmacyBatch, PharmacyStore, PharmacyDrugInteraction
    )
    from app.services.pharmacy_fefo import allocate_batches_fefo, _append_ledger
    
    try:
        dispense_uuid = UUID(dispense_id)
    except ValueError:
        return RedirectResponse(url=f"/pharmacy/ghana/prescriptions?error=Invalid+dispense+ID", status_code=302)
    
    # Get the dispense
    dispense = db.query(PharmacyDispense).filter(
        PharmacyDispense.id == dispense_uuid,
        PharmacyDispense.status == "DRAFT"
    ).first()
    
    if not dispense:
        return RedirectResponse(url=f"/pharmacy/ghana/prescriptions?error=Dispense+not+found+or+already+finalized", status_code=302)
    
    # Check payment verification before finalizing dispense
    if dispense.patient_id:
        from app.utils.payment_verification import requires_payment_before_service
        from app.models.billing_models import Charge, Invoice, ChargeType
        
        payment_required = requires_payment_before_service(db, dispense.patient_id, ChargeType.PHARMACY)
        
        if payment_required:
            # For OPD cash patients, check if there's an unpaid charge for any prescription in this dispense
            prescription_ids = [item.prescription_id for item in dispense.items if item.prescription_id]
            if prescription_ids:
                charges = db.query(Charge).filter(
                    Charge.prescription_id.in_(prescription_ids),
                    Charge.charge_type == ChargeType.PHARMACY
                ).all()
                
                # Block if payment required but no charges exist
                if not charges:
                    return RedirectResponse(
                        url=f"/pharmacy/ghana/prescriptions?error=Payment+required+-+No+charges+found.+Please+visit+billing+first.",
                        status_code=302
                    )
                
                # Check for unpaid balance
                unpaid_balance = 0
                for charge in charges:
                    if charge.invoice_id:
                        invoice = db.query(Invoice).filter(Invoice.id == charge.invoice_id).first()
                        if invoice and invoice.balance > 0:
                            unpaid_balance += float(invoice.balance)
                
                if unpaid_balance > 0:
                    return RedirectResponse(
                        url=f"/pharmacy/ghana/prescriptions?error=Payment+required+-+Unpaid+balance+GHS+{unpaid_balance}",
                        status_code=302
                    )
    
    # Check for drug interactions (same logic as API)
    if dispense.patient_id and dispense.items:
        from app.models.encounter_models import Prescription, Encounter
        drug_ids_in_dispense = [item.drug_id for item in dispense.items]
        
        recent = db.query(Prescription.pharmacy_drug_id).join(
            Encounter, Prescription.encounter_id == Encounter.id
        ).filter(
            Encounter.patient_id == dispense.patient_id,
            Prescription.pharmacy_drug_id.isnot(None),
            Prescription.prescribed_at >= datetime.now() - timedelta(days=90)
        ).distinct().all()
        
        other_drug_ids = set()
        for r in recent:
            if r[0]:
                other_drug_ids.add(r[0])
        
        all_interactions = []
        for item in dispense.items:
            if other_drug_ids:
                from sqlalchemy import or_, and_
                ints = db.query(PharmacyDrugInteraction).filter(
                    PharmacyDrugInteraction.is_active == True,
                    or_(
                        and_(PharmacyDrugInteraction.drug_a_id == item.drug_id, PharmacyDrugInteraction.drug_b_id.in_(other_drug_ids)),
                        and_(PharmacyDrugInteraction.drug_b_id == item.drug_id, PharmacyDrugInteraction.drug_a_id.in_(other_drug_ids)),
                    ),
                ).all()
                
                for i in ints:
                    other_id = i.drug_b_id if i.drug_a_id == item.drug_id else i.drug_a_id
                    other_drug = db.query(PharmacyDrug).filter(PharmacyDrug.id == other_id).first()
                    all_interactions.append({
                        "severity": i.severity,
                        "drug_a": item.drug.generic_name if item.drug else "Unknown",
                        "drug_b": other_drug.generic_name if other_drug else "Unknown",
                    })
        
        # Check for CONTRAINDICATED interactions - redirect with error
        contraindicated = [i for i in all_interactions if i["severity"] == "CONTRAINDICATED"]
        if contraindicated:
            return RedirectResponse(url=f"/pharmacy/dispense/{dispense_id}?error=CONTRAINDICATED+drug+interaction+detected", status_code=302)
    
    # Get store
    store = db.query(PharmacyStore).first()
    if not store:
        return RedirectResponse(url=f"/pharmacy/dispense/{dispense_id}?error=No+pharmacy+store+configured", status_code=302)
    
    # Process each item (allocate stock)
    for item in dispense.items:
        if item.allocations:  # Already allocated
            continue
        
        result = allocate_batches_fefo(db, store.id, item.drug_id, item.qty_dispensed)
        
        if not result["success"]:
            db.rollback()
            return RedirectResponse(url=f"/pharmacy/dispense/{dispense_id}?error=Insufficient+stock+for+{item.drug.generic_name if item.drug else 'drug'}", status_code=302)
        
        # Check for expired batches
        for alloc in result["allocations"]:
            batch = db.query(PharmacyBatch).filter(PharmacyBatch.id == UUID(alloc["batch_id"])).first()
            if batch and batch.expiry_date and batch.expiry_date < date.today():
                db.rollback()
                return RedirectResponse(url=f"/pharmacy/dispense/{dispense_id}?error=Cannot+use+expired+batch", status_code=302)
        
        # Create allocations and deduct stock
        for alloc in result["allocations"]:
            batch = db.query(PharmacyBatch).filter(PharmacyBatch.id == UUID(alloc["batch_id"])).first()
            
            if batch.qty_on_hand < Decimal(str(alloc["qty_allocated"])):
                db.rollback()
                return RedirectResponse(url=f"/pharmacy/dispense/{dispense_id}?error=Insufficient+stock+for+batch", status_code=302)
            
            batch.qty_on_hand = batch.qty_on_hand - Decimal(str(alloc["qty_allocated"]))
            
            allocation = PharmacyDispenseAllocation(
                dispense_item_id=item.id,
                batch_id=UUID(alloc["batch_id"]),
                qty_allocated=Decimal(str(alloc["qty_allocated"])),
            )
            db.add(allocation)
            
            _append_ledger(
                db,
                store_id=store.id,
                drug_id=item.drug_id,
                batch_id=UUID(alloc["batch_id"]),
                movement_type="DISPENSE",
                qty_out=Decimal(str(alloc["qty_allocated"])),
                unit_cost_snapshot=batch.unit_cost,
                selling_price_snapshot=item.unit_selling_price,
                reference_type="DISPENSE",
                reference_id=item.id,
                created_by_id=current_user.id,
            )
    
    # Update dispense status
    dispense.status = "DISPENSED"
    dispense.dispensed_by_id = current_user.id
    dispense.dispensed_at = datetime.now()
    
    # Update prescription status to COMPLETED for all prescriptions linked to this encounter
    from app.models.encounter_models import Prescription, OrderStatus
    if dispense.encounter_id:
        # Get all pending prescriptions for this encounter that have pharmacy drugs
        prescriptions_to_update = db.query(Prescription).filter(
            Prescription.encounter_id == dispense.encounter_id,
            Prescription.status == OrderStatus.PENDING.value,
            Prescription.pharmacy_drug_id.isnot(None)
        ).all()
    elif dispense.patient_id:
        # Fallback: get all pending prescriptions for this patient that have pharmacy drugs
        prescriptions_to_update = db.query(Prescription).join(Encounter).filter(
            Encounter.patient_id == dispense.patient_id,
            Prescription.status == OrderStatus.PENDING.value,
            Prescription.pharmacy_drug_id.isnot(None)
        ).all()
    else:
        prescriptions_to_update = []
        
    for prescription in prescriptions_to_update:
        prescription.status = OrderStatus.COMPLETED
    
    db.commit()
    
    # Redirect to prescriptions page (orders)
    return RedirectResponse(url="/pharmacy/ghana/prescriptions?status=dispense_finalized", status_code=302)


@router.get("/pharmacy/dispense/{dispense_id}", name="pharmacy_dispense_edit")
def pharmacy_dispense_edit(
    request: Request,
    dispense_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Edit dispense page."""
    from uuid import UUID
    from app.models.patient_models import Patient
    from sqlalchemy.orm import joinedload
    
    try:
        dispense_uuid = UUID(dispense_id)
    except ValueError:
        raise HTTPException(400, "Invalid dispense ID")
    
    dispense = db.query(PharmacyDispense).options(
        joinedload(PharmacyDispense.patient),
        joinedload(PharmacyDispense.items).joinedload(PharmacyDispenseItem.drug),
        joinedload(PharmacyDispense.items).joinedload(PharmacyDispenseItem.allocations).joinedload(PharmacyDispenseAllocation.batch),
    ).filter(PharmacyDispense.id == dispense_uuid).first()
    
    if not dispense:
        raise HTTPException(404, "Dispense not found")
    
    # Get available drugs for adding
    drugs = db.query(PharmacyDrug).filter(PharmacyDrug.is_active == True).order_by(PharmacyDrug.generic_name).limit(100).all()
    
    context = {
        "request": request,
        "title": f"Edit Dispense #{dispense.id}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "dispense": dispense,
        "drugs": drugs,
    }
    return templates.TemplateResponse("pharmacy_ghana/dispense_edit.html", context)


@router.post("/pharmacy/dispense/{dispense_id}/items", name="pharmacy_dispense_add_item_ui")
async def pharmacy_dispense_add_item_ui(
    request: Request,
    dispense_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Add item to dispense from UI."""
    from uuid import UUID
    from decimal import Decimal
    
    try:
        dispense_uuid = UUID(dispense_id)
    except ValueError:
        raise HTTPException(400, "Invalid dispense ID")
    
    dispense = db.query(PharmacyDispense).filter(
        PharmacyDispense.id == dispense_uuid,
        PharmacyDispense.status == "DRAFT"
    ).first()
    if not dispense:
        raise HTTPException(400, "Dispense not found or not in DRAFT status")
    
    form_data = await request.form()
    drug_id = form_data.get("drug_id")
    qty_dispensed = form_data.get("qty_dispensed")
    dosage_instructions = form_data.get("dosage_instructions") or None
    
    if not drug_id or not qty_dispensed:
        return RedirectResponse(url=f"/pharmacy/dispense/{dispense_id}?error=Drug+and+quantity+required", status_code=302)
    
    try:
        drug_uuid = UUID(drug_id)
        qty = Decimal(str(qty_dispensed))
    except ValueError:
        return RedirectResponse(url=f"/pharmacy/dispense/{dispense_id}?error=Invalid+input", status_code=302)
    
    drug = db.query(PharmacyDrug).filter(PharmacyDrug.id == drug_uuid).first()
    if not drug:
        return RedirectResponse(url=f"/pharmacy/dispense/{dispense_id}?error=Drug+not+found", status_code=302)
    
    # Get current price
    batch = db.query(PharmacyBatch).filter(
        PharmacyBatch.drug_id == drug_uuid,
        PharmacyBatch.status == "ACTIVE",
        PharmacyBatch.expiry_date >= date.today(),
        PharmacyBatch.qty_on_hand > 0,
    ).order_by(PharmacyBatch.expiry_date.asc()).first()
    
    unit_price = float(batch.selling_price) if batch and batch.selling_price else 0
    total = unit_price * float(qty)
    
    item = PharmacyDispenseItem(
        dispense_id=dispense_uuid,
        drug_id=drug_uuid,
        qty_dispensed=qty,
        dosage_instructions=dosage_instructions,
        unit_selling_price=Decimal(str(unit_price)),
        total_amount=Decimal(str(total)),
    )
    db.add(item)
    db.commit()
    
    return RedirectResponse(url=f"/pharmacy/dispense/{dispense_id}?status=item_added", status_code=302)


# =======================================================
# PHASE 2: Prescription-Based Dispensing (NEW)
# =======================================================

@router.get("/pharmacy/ghana/prescriptions/by-patient/{patient_id}", name="dispense_patient_prescriptions")
def dispense_patient_prescriptions(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    encounter_id: Optional[int] = Query(None),
):
    """Dispense all pending prescriptions for a patient at once."""
    from app.models.encounter_models import Prescription, Encounter, OrderStatus
    from app.models.patient_models import Patient
    from app.models.pharmacy_models import (
        PharmacyDrug, PharmacyBatch, PharmacyDispense, PharmacyDispenseItem,
        PharmacyDrugInteraction, PharmacyDispenseAllocation
    )
    from app.crud import inventory_crud
    from app.utils.payment_verification import is_cash_patient, check_payment_required_and_paid, requires_payment_before_service, is_patient_admitted
    from app.models.billing_models import Charge, ChargeType, Invoice
    from sqlalchemy import or_, and_
    from sqlalchemy.orm import joinedload
    
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get pending prescriptions for this patient
    query = db.query(Prescription).options(
        joinedload(Prescription.encounter).joinedload(Encounter.patient),
        joinedload(Prescription.prescribed_by),
        joinedload(Prescription.pharmacy_drug).joinedload(PharmacyDrug.dosage_form)
    ).join(Encounter).filter(
        Encounter.patient_id == patient_id,
        Prescription.status == OrderStatus.PENDING.value,
        Prescription.pharmacy_drug_id.isnot(None)
    )
    
    if encounter_id:
        query = query.filter(Prescription.encounter_id == encounter_id)
    
    prescriptions = query.order_by(Prescription.prescribed_at.desc()).all()
    
    if not prescriptions:
        raise HTTPException(status_code=404, detail="No pending prescriptions found for this patient")
    
    # Get FEFO batches and stock info for each prescription
    prescriptions_with_stock = []
    all_drug_ids = []
    
    for prescription in prescriptions:
        if prescription.pharmacy_drug_id:
            fefo_batches = db.query(PharmacyBatch).filter(
                PharmacyBatch.drug_id == prescription.pharmacy_drug_id,
                PharmacyBatch.status == "ACTIVE",
                PharmacyBatch.expiry_date >= date.today(),
                PharmacyBatch.qty_on_hand > 0
            ).order_by(PharmacyBatch.expiry_date.asc()).all()
            
            default_price = fefo_batches[0].selling_price if fefo_batches else None
            stock_check = {"available": float(sum(b.qty_on_hand for b in fefo_batches))} if fefo_batches else {"available": 0}
            
            prescriptions_with_stock.append({
                "prescription": prescription,
                "fefo_batches": fefo_batches,
                "default_price": float(default_price) if default_price else 0,
                "stock_check": stock_check,
            })
            all_drug_ids.append(prescription.pharmacy_drug_id)
    
    # Check drug interactions between all drugs in prescriptions
    drug_interactions = []
    if len(all_drug_ids) > 1:
        interactions = db.query(PharmacyDrugInteraction).filter(
            or_(
                and_(PharmacyDrugInteraction.drug_a_id.in_(all_drug_ids),
                     PharmacyDrugInteraction.drug_b_id.in_(all_drug_ids)),
                and_(PharmacyDrugInteraction.drug_b_id.in_(all_drug_ids),
                     PharmacyDrugInteraction.drug_a_id.in_(all_drug_ids))
            ),
            PharmacyDrugInteraction.is_active == True
        ).all()
        
        for inter in interactions:
            drug_a = db.query(PharmacyDrug).filter(PharmacyDrug.id == inter.drug_a_id).first()
            drug_b = db.query(PharmacyDrug).filter(PharmacyDrug.id == inter.drug_b_id).first()
            drug_interactions.append({
                "severity": inter.severity,
                "drug_a": drug_a.generic_name if drug_a else "Unknown",
                "drug_b": drug_b.generic_name if drug_b else "Unknown",
                "description": inter.description,
                "recommendation": inter.recommendation
            })
    
    # Check payment status
    is_admitted = is_patient_admitted(db, patient_id)
    payment_required = requires_payment_before_service(db, patient_id, ChargeType.PHARMACY)
    payment_notice = None
    
    if payment_required and is_admitted:
        payment_notice = "IPD Patient - Payment at Discharge"
    elif payment_required and not is_admitted:
        payment_notice = "Payment Required Before Dispense"
    else:
        payment_notice = "No Payment Required"
    
    context = {
        "request": request,
        "title": f"Dispense All Prescriptions - {patient.first_name} {patient.last_name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient,
        "prescriptions_with_stock": prescriptions_with_stock,
        "drug_interactions": drug_interactions,
        "encounter_id": encounter_id,
        "payment_required": payment_required,
        "payment_notice": payment_notice,
        "is_admitted": is_admitted,
    }
    return templates.TemplateResponse("pharmacy_ghana/dispense_patient_prescriptions.html", context)


@router.post("/pharmacy/ghana/prescriptions/by-patient/{patient_id}/create-dispense", name="create_dispense_for_patient")
async def create_dispense_for_patient(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """
    Create a new dispense with selected prescriptions for a patient.
    
    This endpoint:
    1. Reads pharmacy-entered quantities from the form
    2. Updates each prescription with pharmacy's quantity
    3. Creates billing charges for each prescription (BEFORE payment)
    4. Creates the dispense record
    
    This ensures pharmacy controls the quantities while billing is calculated correctly.
    """
    from app.models.encounter_models import Prescription, Encounter, OrderStatus
    from app.models.patient_models import Patient
    from app.models.pharmacy_models import (
        PharmacyDrug, PharmacyBatch, PharmacyDispense, PharmacyDispenseItem,
    )
    from app.models.billing_models import Charge, ChargeType, Invoice
    from app.services.charge_automation import create_charge_for_prescription
    from decimal import Decimal
    from datetime import date
    
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # ============================================================
    # Read ALL form data at once (before extracting individual fields)
    # ============================================================
    form_data = await request.form()
    
    # Parse prescription IDs from form (checkboxes with same name create multiple entries)
    selected_ids = []
    # Get all values for prescription_ids (there may be multiple checkboxes)
    prescription_ids_list = form_data.getlist("prescription_ids")
    for pid in prescription_ids_list:
        try:
            selected_ids.append(int(pid.strip()))
        except ValueError:
            pass
    
    # Also check for comma-separated format as fallback
    prescription_ids_str = form_data.get("prescription_ids", "")
    if prescription_ids_str and not selected_ids:
        for pid in prescription_ids_str.split(','):
            try:
                selected_ids.append(int(pid.strip()))
            except ValueError:
                pass
    
    # Parse encounter_id from form
    encounter_id_str = form_data.get("encounter_id", "")
    encounter_id = None
    if encounter_id_str:
        try:
            encounter_id = int(encounter_id_str)
        except ValueError:
            pass
    
    # Parse pharmacy-entered quantities from form
    pharmacy_quantities = {}
    for key, value in form_data.items():
        if key.startswith('qty_'):
            try:
                pres_id = int(key.replace('qty_', ''))
                # Handle empty string or None as 1, otherwise parse the int
                if value and str(value).strip():
                    qty = int(str(value).strip())
                    if qty > 0:
                        pharmacy_quantities[pres_id] = qty
            except (ValueError, TypeError):
                pass
    
    # ============================================================
    # Get the prescriptions from database
    # ============================================================
    if selected_ids:
        prescriptions = db.query(Prescription).filter(
            Prescription.id.in_(selected_ids),
            Prescription.status == OrderStatus.PENDING.value
        ).all()
    else:
        # If no selection, get all pending prescriptions for this patient
        query = db.query(Prescription).join(Encounter).filter(
            Encounter.patient_id == patient_id,
            Prescription.status == OrderStatus.PENDING.value,
            Prescription.pharmacy_drug_id.isnot(None)
        )
        if encounter_id:
            query = query.filter(Prescription.encounter_id == encounter_id)
        prescriptions = query.all()
    
    if not prescriptions:
        raise HTTPException(status_code=404, detail="No pending prescriptions found for the patient")
    
    # Update prescriptions with pharmacy's quantities and create billing
    for prescription in prescriptions:
        # Use pharmacy's quantity if entered, otherwise use prescription quantity
        qty = pharmacy_quantities.get(prescription.id, prescription.quantity or 1)
        
        # Update prescription with pharmacy's quantity
        prescription.quantity = qty
        
        # Flush to ensure prescription quantity is persisted before creating billing
        db.flush()
        
        # Get unit price from FEFO batch
        unit_price = None
        if prescription.pharmacy_drug_id:
            fefo_batch = db.query(PharmacyBatch).filter(
                PharmacyBatch.drug_id == prescription.pharmacy_drug_id,
                PharmacyBatch.status == "ACTIVE",
                PharmacyBatch.expiry_date >= date.today(),
                PharmacyBatch.qty_on_hand > 0
            ).order_by(PharmacyBatch.expiry_date.asc()).first()
            if fefo_batch:
                unit_price = fefo_batch.selling_price
        
        if not unit_price:
            from app.services.charge_automation import get_medication_price
            unit_price = get_medication_price(db, prescription)
        
        if not unit_price:
            unit_price = 0
        
        # Create or update billing charge with pharmacy's quantity
        existing_charge = db.query(Charge).filter(
            Charge.prescription_id == prescription.id,
            Charge.charge_type == ChargeType.PHARMACY
        ).first()
        
        if existing_charge:
            # Update existing charge with new quantity
            existing_charge.quantity = qty
            existing_charge.unit_price = unit_price
            existing_charge.total_amount = qty * unit_price
            existing_charge.description = f"Medication: {prescription.medication_name} ({qty} units @ GHS {float(unit_price)})"
            
            # Recalculate totals
            subtotal = existing_charge.total_amount - existing_charge.discount
            tax_amount = subtotal * (existing_charge.tax_rate / Decimal('100')) if existing_charge.tax_rate else Decimal('0')
            existing_charge.tax_amount = tax_amount
            existing_charge.total_amount = subtotal + tax_amount
            
            # Update invoice totals if invoice exists
            if existing_charge.invoice_id:
                invoice = db.query(Invoice).filter(Invoice.id == existing_charge.invoice_id).first()
                if invoice:
                    # Recalculate entire invoice
                    all_charges = db.query(Charge).filter(Charge.invoice_id == invoice.id).all()
                    invoice.subtotal = sum(float(c.total_amount) for c in all_charges)
                    invoice.tax_amount = sum(float(c.tax_amount) for c in all_charges)
                    invoice.total_amount = invoice.subtotal - float(invoice.discount_amount) + invoice.tax_amount
                    invoice.balance = invoice.total_amount - float(invoice.paid_amount)
        else:
            # Create new billing charge
            charge = Charge(
                encounter_id=prescription.encounter_id,
                prescription_id=prescription.id,
                charge_type=ChargeType.PHARMACY,
                quantity=qty,
                unit_price=unit_price,
                total_amount=Decimal(str(qty * unit_price)),
                tax_rate=Decimal('0'),
                tax_amount=Decimal('0'),
                description=f"Medication: {prescription.medication_name} ({qty} units @ GHS {float(unit_price)})",
            )
            db.add(charge)
    
    db.commit()
    
    # PAYMENT VERIFICATION: Check if payment is required for this patient
    from app.utils.payment_verification import requires_payment_before_service, is_patient_admitted
    
    is_admitted = is_patient_admitted(db, patient_id)
    payment_required = requires_payment_before_service(db, patient_id, ChargeType.PHARMACY)
    
    if payment_required and not is_admitted:
        # For OPD cash patients, check if there's an unpaid invoice
        # Get all prescriptions for this patient that have charges
        prescription_ids_list = [p.id for p in prescriptions]
        charges = db.query(Charge).filter(
            Charge.prescription_id.in_(prescription_ids_list),
            Charge.charge_type == ChargeType.PHARMACY
        ).all()
        
        # Block if payment required but no charges exist
        if not charges:
            return RedirectResponse(
                url=f"/pharmacy/ghana/prescriptions/by-patient/{patient_id}?error=Payment+required+-+No+charges+found.+Please+visit+billing+first.",
                status_code=302
            )
        
        unpaid_balance = 0
        for charge in charges:
            if charge.invoice_id:
                invoice = db.query(Invoice).filter(Invoice.id == charge.invoice_id).first()
                if invoice and invoice.status.value not in ['paid', 'PAID']:
                    unpaid_balance += float(invoice.balance) if invoice.balance else 0
        
        if unpaid_balance > 0:
            return RedirectResponse(
                url=f"/pharmacy/ghana/prescriptions/by-patient/{patient_id}?error=Payment+required+-+Unpaid+balance+GHS+{unpaid_balance}",
                status_code=302
            )
    
    # Create a new dispense
    dispense = PharmacyDispense(
        patient_id=patient_id,
        encounter_id=encounter_id,
        status="DRAFT",
    )
    db.add(dispense)
    db.flush()
    
    # Add all prescriptions as dispense items
    for prescription in prescriptions:
        # Get current selling price from active batch
        batch = db.query(PharmacyBatch).filter(
            PharmacyBatch.drug_id == prescription.pharmacy_drug_id,
            PharmacyBatch.status == "ACTIVE",
            PharmacyBatch.expiry_date >= date.today(),
            PharmacyBatch.qty_on_hand > 0,
        ).order_by(PharmacyBatch.expiry_date.asc()).first()
        
        unit_price = float(batch.selling_price) if batch and batch.selling_price else 0
        qty_to_dispense = float(prescription.quantity) if prescription.quantity else 1
        total = unit_price * qty_to_dispense
        
        item = PharmacyDispenseItem(
            dispense_id=dispense.id,
            drug_id=prescription.pharmacy_drug_id,
            qty_dispensed=Decimal(str(qty_to_dispense)),
            dosage_instructions=prescription.instructions,
            qty_prescribed=Decimal(str(prescription.quantity)) if prescription.quantity else None,
            unit_selling_price=Decimal(str(unit_price)),
            total_amount=Decimal(str(total)),
        )
        db.add(item)
    
    db.commit()
    db.refresh(dispense)
    
    # Redirect to the dispense detail page
    return RedirectResponse(url=f"/pharmacy/dispense/{dispense.id}", status_code=302)


@router.get("/pharmacy/ghana/prescriptions", name="pending_prescriptions")
def pending_prescriptions(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    status_filter: Optional[str] = Query(None),
    patient_id: Optional[int] = Query(None),
    patient_number: Optional[str] = Query(None),
    encounter_id: Optional[str] = Query(None),
):
    """List pending prescriptions for dispensing."""
    from app.models.encounter_models import Prescription, Encounter, OrderStatus
    from app.models.patient_models import Patient
    
    # Use outerjoin to include walk-in prescriptions (encounter_id = None)
    # Join Patient via both paths: directly (walk-in) and through encounter (regular)
    query = db.query(Prescription).outerjoin(
        Encounter, Prescription.encounter_id == Encounter.id
    ).outerjoin(
        Patient, Patient.id == Prescription.patient_id  # Direct patient link for walk-in
    )
    
    # Filter by patient_number if provided (e.g., DGMS000019)
    if patient_number and patient_number.strip():
        query = query.filter(Patient.patient_number.ilike(f"%{patient_number.strip()}%"))
    
    # Filter by patient id if provided - handle both walk-in and regular prescriptions
    if patient_id:
        # For walk-in: check Prescription.patient_id, for regular: check Encounter.patient_id
        from sqlalchemy import or_
        query = query.filter(
            or_(
                Prescription.patient_id == patient_id,
                Encounter.patient_id == patient_id
            )
        )
    
    # Filter by encounter if provided (handle empty string)
    if encounter_id and encounter_id.strip():
        try:
            encounter_id_int = int(encounter_id.strip())
            query = query.filter(Prescription.encounter_id == encounter_id_int)
        except ValueError:
            pass
    
    if status_filter and status_filter.lower() != "all":
        # Normalize to lowercase to match database enum values
        status_filter = status_filter.lower()
        # Validate that status_filter is a valid OrderStatus value
        valid_statuses = [s.value for s in OrderStatus]
        if status_filter not in valid_statuses:
            # If invalid status, show pending by default
            status_filter = OrderStatus.PENDING.value
        query = query.filter(Prescription.status == status_filter)
    elif not status_filter:
        # Default: show pending
        query = query.filter(Prescription.status == OrderStatus.PENDING.value)
    # If status_filter is "all", show all prescriptions without filtering by status
    
    prescriptions = query.order_by(Prescription.prescribed_at.desc()).limit(100).all()
    
    context = {
        "request": request,
        "title": "Pending Prescriptions",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "prescriptions": prescriptions,
        "status_filter": status_filter,
        "patient_id": patient_id,
        "patient_number": patient_number,
        "encounter_id": encounter_id,
    }
    return templates.TemplateResponse("pharmacy_ghana/pending_prescriptions.html", context)


@router.get("/pharmacy/ghana/prescriptions/{prescription_id}", name="dispense_prescription_page")
def dispense_prescription_page(
    request: Request,
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Dispense prescription page with FEFO batch selection."""
    from app.models.encounter_models import Prescription, Encounter
    from app.models.patient_models import Patient
    from app.models.pharmacy_models import (
        PharmacyDrug, PharmacyBatch, PharmacyDispense, PharmacyDispenseItem,
        PharmacyDrugInteraction
    )
    from app.crud import inventory_crud
    from app.utils.payment_verification import is_cash_patient, check_payment_required_and_paid, requires_payment_before_service, is_patient_admitted
    from app.models.billing_models import Charge, ChargeType, Invoice, InvoiceStatus
    from sqlalchemy import or_, and_
    from sqlalchemy.orm import joinedload
    from datetime import date
    
    # Get prescription with relationships
    prescription = db.query(Prescription).options(
        joinedload(Prescription.encounter).joinedload(Encounter.patient),
        joinedload(Prescription.prescribed_by),
        joinedload(Prescription.pharmacy_drug),
    ).filter(Prescription.id == prescription_id).first()
    
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    patient = prescription.encounter.patient if prescription.encounter else None
    
    # Get FEFO batches for the drug
    fefo_batches = []
    stock_check = {"available": 0}
    default_price = None
    
    if prescription.pharmacy_drug_id:
        fefo_batches = db.query(PharmacyBatch).filter(
            PharmacyBatch.drug_id == prescription.pharmacy_drug_id,
            PharmacyBatch.status == "ACTIVE",
            PharmacyBatch.expiry_date >= date.today(),
            PharmacyBatch.qty_on_hand > 0
        ).order_by(PharmacyBatch.expiry_date.asc()).all()
        
        stock_check = {"available": float(sum(b.qty_on_hand for b in fefo_batches))}
        default_price = fefo_batches[0].selling_price if fefo_batches else None
    
    # Check drug interactions
    drug_interactions = []
    if prescription.pharmacy_drug_id:
        interactions = db.query(PharmacyDrugInteraction).filter(
            or_(
                PharmacyDrugInteraction.drug_a_id == prescription.pharmacy_drug_id,
                PharmacyDrugInteraction.drug_b_id == prescription.pharmacy_drug_id
            ),
            PharmacyDrugInteraction.is_active == True
        ).all()
        
        for inter in interactions:
            other_drug = None
            if inter.drug_a_id == prescription.pharmacy_drug_id:
                other_drug = db.query(PharmacyDrug).filter(PharmacyDrug.id == inter.drug_b_id).first()
            else:
                other_drug = db.query(PharmacyDrug).filter(PharmacyDrug.id == inter.drug_a_id).first()
            
            if other_drug:
                drug_interactions.append({
                    "severity": inter.severity,
                    "other_drug": other_drug.generic_name,
                    "description": inter.description,
                    "recommendation": inter.recommendation
                })
    
    # Check payment status - use requires_payment_before_service to properly handle IPD patients
    payment_required = False
    payment_paid = False
    payment_notice = None
    unpaid_invoice = None
    is_admitted = False
    
    if patient:
        # Check if patient is admitted (IPD)
        is_admitted = is_patient_admitted(db, patient.id)
        
        # Check if payment is required before service using the full logic
        payment_required = requires_payment_before_service(
            db, patient.id, ChargeType.PHARMACY
        )
        
        if payment_required:
            # For OPD cash patients, check if the charge has been paid
            charge = db.query(Charge).filter(
                Charge.prescription_id == prescription_id,
                Charge.charge_type == ChargeType.PHARMACY
            ).first()
            
            if charge:
                invoice = db.query(Invoice).filter(Invoice.id == charge.invoice_id).first()
                if invoice:
                    payment_paid = invoice.status == InvoiceStatus.PAID
                    if not payment_paid:
                        unpaid_invoice = invoice
                        if is_admitted:
                            payment_notice = f"IPD Patient - Charges accumulate for discharge: GHS {invoice.balance}"
                        else:
                            payment_notice = f"Payment Required: GHS {invoice.balance}"
                    else:
                        if is_admitted:
                            payment_notice = "IPD Patient - Payment at Discharge"
                        else:
                            payment_notice = "Payment Completed"
    
    # Get other active prescriptions
    other_active_prescriptions = []
    if patient:
        other_active_prescriptions = db.query(Prescription).join(Encounter).filter(
            Encounter.patient_id == patient.id,
            Prescription.id != prescription_id,
            Prescription.status.in_([OrderStatus.PENDING, OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED])
        ).limit(10).all()
    
    # Check if user can edit price
    can_edit_price = _can_view_cost(db, current_user.role.name)
    
    context = {
        "request": request,
        "title": f"Dispense Prescription #{prescription_id}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "prescription": prescription,
        "patient": patient,
        "fefo_batches": fefo_batches,
        "stock_check": stock_check,
        "default_price": default_price,
        "drug_interactions": drug_interactions,
        "payment_required": payment_required,
        "payment_paid": payment_paid,
        "payment_notice": payment_notice,
        "unpaid_invoice": unpaid_invoice,
        "other_active_prescriptions": other_active_prescriptions,
        "can_edit_price": can_edit_price,
        "is_admitted": is_admitted,
    }
    return templates.TemplateResponse("pharmacy_ghana/prescription_dispense.html", context)


@router.post("/pharmacy/ghana/prescriptions/{prescription_id}/set-quantity", name="set_prescription_quantity")
async def set_prescription_quantity(
    request: Request,
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    quantity: int = Form(...),
    batch_id: str = Form(None),
):
    """
    Pharmacy sets the quantity to dispense BEFORE patient goes to pay.
    This creates/updates the billing charge with pharmacy's quantity.
    
    Workflow:
    1. Doctor creates prescription (quantity optional)
    2. Pharmacy reviews and inputs quantity to dispense
    3. Billing charge is created/updated with pharmacy's quantity
    4. Patient goes to pay at front desk
    5. Pharmacy verifies payment and dispenses
    """
    from app.models.encounter_models import Prescription, Encounter, OrderStatus
    from app.models.pharmacy_models import PharmacyDrug, PharmacyBatch
    from app.models.billing_models import Charge, ChargeType, Invoice
    from app.services.charge_automation import create_charge_for_prescription
    from uuid import UUID
    from decimal import Decimal
    
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Check if already dispensed
    if prescription.status == OrderStatus.COMPLETED:
        return RedirectResponse(
            url=f"/pharmacy/ghana/prescriptions/{prescription_id}?error=Already+dispensed",
            status_code=302
        )
    
    # Get the unit price from batch if specified, otherwise from FEFO
    unit_price = None
    if prescription.pharmacy_drug_id:
        if batch_id:
            try:
                batch = db.query(PharmacyBatch).filter(
                    PharmacyBatch.id == UUID(batch_id)
                ).first()
                if batch:
                    unit_price = batch.selling_price
            except ValueError:
                pass
        
        if not unit_price:
            # Get FEFO batch for price
            fefo_batch = db.query(PharmacyBatch).filter(
                PharmacyBatch.drug_id == prescription.pharmacy_drug_id,
                PharmacyBatch.status == "ACTIVE",
                PharmacyBatch.expiry_date >= date.today(),
                PharmacyBatch.qty_on_hand > 0
            ).order_by(PharmacyBatch.expiry_date.asc()).first()
            if fefo_batch:
                unit_price = fefo_batch.selling_price
    
    if not unit_price:
        # Fallback to getting price from service pricing
        from app.services.charge_automation import get_medication_price
        unit_price = get_medication_price(db, prescription)
    
    # Update prescription with pharmacy's quantity
    prescription.quantity = quantity
    db.commit()
    
    # Create or update billing charge with pharmacy's quantity
    existing_charge = db.query(Charge).filter(
        Charge.prescription_id == prescription_id,
        Charge.charge_type == ChargeType.PHARMACY
    ).first()
    
    if existing_charge:
        # Update existing charge with new quantity and price
        # Store old values for invoice recalculation
        old_subtotal = existing_charge.unit_price * existing_charge.quantity - existing_charge.discount
        old_tax = existing_charge.tax_amount
        
        existing_charge.quantity = quantity
        existing_charge.unit_price = unit_price
        # Calculate total with tax - ensure proper Decimal conversion
        qty_decimal = Decimal(str(quantity))
        unit_price_decimal = Decimal(str(unit_price)) if unit_price else Decimal('0')
        subtotal = qty_decimal * unit_price_decimal - existing_charge.discount
        tax_amount = subtotal * (existing_charge.tax_rate / Decimal('100'))
        existing_charge.tax_amount = tax_amount
        existing_charge.total_amount = subtotal + tax_amount
        existing_charge.description = f"Medication: {prescription.medication_name} ({quantity} units @ GHS {float(unit_price)})"
        
        # Recalculate invoice totals
        invoice = db.query(Invoice).filter(Invoice.id == existing_charge.invoice_id).first()
        if invoice:
            invoice.subtotal = invoice.subtotal - old_subtotal + subtotal
            invoice.tax_amount = invoice.tax_amount - old_tax + tax_amount
            invoice.total_amount = invoice.subtotal - invoice.discount_amount + invoice.tax_amount
            invoice.balance = invoice.total_amount - invoice.paid_amount
        
        db.commit()
    else:
        # Create new charge
        charge = create_charge_for_prescription(
            db=db,
            prescription=prescription,
            created_by_id=current_user.id,
            check_payment_required=True
        )
        if charge:
            # Override with pharmacy's quantity and price
            # Store old values for invoice recalculation
            old_subtotal = charge.unit_price * charge.quantity - charge.discount
            old_tax = charge.tax_amount
            
            charge.quantity = quantity
            charge.unit_price = unit_price
            # Calculate total with tax - ensure proper Decimal conversion
            qty_decimal = Decimal(str(quantity))
            unit_price_decimal = Decimal(str(unit_price)) if unit_price else Decimal('0')
            subtotal = qty_decimal * unit_price_decimal - charge.discount
            tax_amount = subtotal * (charge.tax_rate / Decimal('100'))
            charge.tax_amount = tax_amount
            charge.total_amount = subtotal + tax_amount
            charge.description = f"Medication: {prescription.medication_name} ({quantity} units @ GHS {float(unit_price)})"
            
            # Recalculate invoice totals
            invoice = db.query(Invoice).filter(Invoice.id == charge.invoice_id).first()
            if invoice:
                invoice.subtotal = invoice.subtotal - old_subtotal + subtotal
                invoice.tax_amount = invoice.tax_amount - old_tax + tax_amount
                invoice.total_amount = invoice.subtotal - invoice.discount_amount + invoice.tax_amount
                invoice.balance = invoice.total_amount - invoice.paid_amount
            
            db.commit()
    
    return RedirectResponse(
        url=f"/pharmacy/ghana/prescriptions/{prescription_id}?status=quantity_set&qty={quantity}",
        status_code=302
    )


@router.get("/pharmacy/ghana/prescriptions/{prescription_id}", name="dispense_prescription_page")
def dispense_prescription_page(
    request: Request,
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Dispense prescription page with FEFO batch selection."""
    from app.models.encounter_models import Prescription, Encounter
    from app.models.patient_models import Patient
    from app.models.pharmacy_models import (
        PharmacyDrug, PharmacyBatch, PharmacyDispense, PharmacyDispenseItem,
        PharmacyDrugInteraction
    )
    from app.crud import inventory_crud
    from app.utils.payment_verification import is_cash_patient, check_payment_required_and_paid, requires_payment_before_service, is_patient_admitted
    from app.models.billing_models import Charge, ChargeType, Invoice
    from sqlalchemy import or_, and_
    
    # Get prescription with relationships
    prescription = db.query(Prescription).options(
        joinedload(Prescription.encounter).joinedload(Encounter.patient),
        joinedload(Prescription.prescribed_by),
        joinedload(Prescription.pharmacy_drug).joinedload(PharmacyDrug.dosage_form)
    ).filter(Prescription.id == prescription_id).first()
    
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    patient = prescription.encounter.patient if prescription.encounter else None
    
    # Get FEFO batches for this drug
    fefo_batches = []
    stock_check = None
    default_price = None
    
    if prescription.pharmacy_drug_id:
        # Use Ghana pharmacy system
        fefo_batches = db.query(PharmacyBatch).filter(
            PharmacyBatch.drug_id == prescription.pharmacy_drug_id,
            PharmacyBatch.status == "ACTIVE",
            PharmacyBatch.expiry_date >= date.today(),
            PharmacyBatch.qty_on_hand > 0
        ).order_by(PharmacyBatch.expiry_date.asc()).all()
        
        if fefo_batches:
            default_price = fefo_batches[0].selling_price
            stock_check = {"available": float(sum(b.qty_on_hand for b in fefo_batches))}
        else:
            stock_check = {"available": 0}
    elif prescription.medication_id:
        # Fallback to legacy inventory
        from app.models.inventory_models import Medication
        medication = db.query(Medication).filter(Medication.id == prescription.medication_id).first()
        if medication:
            stock_check = inventory_crud.check_stock_availability(
                db, medication.id, prescription.quantity or 1
            )
            # Convert StockCheckResponse to dict for template compatibility
            if stock_check:
                stock_check = {"available": stock_check.available_quantity}
    
    # Check drug interactions
    drug_interactions = []
    if prescription.pharmacy_drug_id and patient:
        # Get other active prescriptions for this patient
        other_prescriptions = db.query(Prescription).join(Encounter).filter(
            Encounter.patient_id == patient.id,
            Prescription.id != prescription_id,
            Prescription.status.in_([OrderStatus.PENDING, OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED])
        ).all()
        
        other_drug_ids = []
        for op in other_prescriptions:
            if op.pharmacy_drug_id:
                other_drug_ids.append(op.pharmacy_drug_id)
        
        if other_drug_ids:
            interactions = db.query(PharmacyDrugInteraction).filter(
                or_(
                    and_(PharmacyDrugInteraction.drug_a_id == prescription.pharmacy_drug_id,
                         PharmacyDrugInteraction.drug_b_id.in_(other_drug_ids)),
                    and_(PharmacyDrugInteraction.drug_b_id == prescription.pharmacy_drug_id,
                         PharmacyDrugInteraction.drug_a_id.in_(other_drug_ids))
                ),
                PharmacyDrugInteraction.is_active == True
            ).all()
            
            for inter in interactions:
                other_drug = None
                if inter.drug_a_id == prescription.pharmacy_drug_id:
                    other_drug = db.query(PharmacyDrug).filter(PharmacyDrug.id == inter.drug_b_id).first()
                else:
                    other_drug = db.query(PharmacyDrug).filter(PharmacyDrug.id == inter.drug_a_id).first()
                
                if other_drug:
                    drug_interactions.append({
                        "severity": inter.severity,
                        "other_drug": other_drug.generic_name,
                        "description": inter.description,
                        "recommendation": inter.recommendation
                    })
    
    # Check payment status - use requires_payment_before_service to properly handle IPD patients
    # Rules:
    # - OPD Cash patients: Pay at billing before dispense
    # - IPD Cash patients: Pay at discharge (don't require payment before dispense)
    # - NHIS (OPD/IPD): Accumulate for claims (don't require payment)
    payment_required = False
    payment_paid = False
    payment_notice = None
    unpaid_invoice = None
    is_admitted = False
    
    if patient:
        # Check if patient is admitted (IPD)
        is_admitted = is_patient_admitted(db, patient.id)
        
        # Check if payment is required before service using the full logic
        payment_required = requires_payment_before_service(
            db, patient.id, ChargeType.PHARMACY
        )
        
        if payment_required:
            # For OPD cash patients, check if the charge has been paid
            charge = db.query(Charge).filter(
                Charge.prescription_id == prescription_id,
                Charge.charge_type == ChargeType.PHARMACY
            ).first()
            
            if charge:
                invoice = db.query(Invoice).filter(Invoice.id == charge.invoice_id).first()
                if invoice:
                    payment_paid = invoice.status == InvoiceStatus.PAID
                    if not payment_paid:
                        unpaid_invoice = invoice
                        if is_admitted:
                            payment_notice = f"IPD Patient - Charges accumulate for discharge: GHS {invoice.balance}"
                        else:
                            payment_notice = f"Payment Required: GHS {invoice.balance}"
                    else:
                        if is_admitted:
                            payment_notice = "IPD Patient - Payment at Discharge"
                        else:
                            payment_notice = "Payment Completed"
    
    # Get other active prescriptions
    other_active_prescriptions = []
    if patient:
        other_active_prescriptions = db.query(Prescription).join(Encounter).filter(
            Encounter.patient_id == patient.id,
            Prescription.id != prescription_id,
            Prescription.status.in_([OrderStatus.PENDING, OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED])
        ).limit(10).all()
    
    # Check if user can edit price
    can_edit_price = _can_view_cost(db, current_user.role.name)
    
    context = {
        "request": request,
        "title": f"Dispense Prescription #{prescription_id}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "prescription": prescription,
        "patient": patient,
        "fefo_batches": fefo_batches,
        "stock_check": stock_check,
        "default_price": default_price,
        "drug_interactions": drug_interactions,
        "payment_required": payment_required,
        "payment_paid": payment_paid,
        "payment_notice": payment_notice,
        "unpaid_invoice": unpaid_invoice,
        "other_active_prescriptions": other_active_prescriptions,
        "can_edit_price": can_edit_price,
        "is_admitted": is_admitted,
    }
    return templates.TemplateResponse("pharmacy_ghana/prescription_dispense.html", context)


@router.post("/pharmacy/ghana/prescriptions/{prescription_id}/dispense", name="dispense_prescription_ghana")
async def dispense_prescription_ghana(
    request: Request,
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    batch_id: str = Form(None),
    qty_dispensed: int = Form(1),
    selling_price: float = Form(None),
    dispense_instructions: str = Form(None),
    payment_type: str = Form("CASH"),
):
    """Process dispensing of a prescription using Ghana pharmacy system."""
    from app.models.encounter_models import Prescription, Encounter, OrderStatus
    from app.models.pharmacy_models import (
        PharmacyDrug, PharmacyBatch, PharmacyDispense, PharmacyDispenseItem,
        PharmacyDispenseAllocation, PharmacyStockLedger
    )
    from uuid import UUID
    
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Check current status
    if prescription.status == OrderStatus.COMPLETED:
        return RedirectResponse(
            url=f"/pharmacy/ghana/prescriptions/{prescription_id}?error=Already+dispensed",
            status_code=302
        )
    
    patient_id = prescription.encounter.patient_id if prescription.encounter else prescription.patient_id
    
    # Check payment status before dispensing - use same logic as GET page
    # This prevents direct POST attacks bypassing the UI payment check
    from app.utils.payment_verification import requires_payment_before_service, is_patient_admitted
    from app.models.billing_models import Charge, Invoice, ChargeType
    
    payment_required = requires_payment_before_service(db, patient_id, ChargeType.PHARMACY)
    
    if payment_required:
        # For OPD cash patients, verify payment has been made
        charge = db.query(Charge).filter(
            Charge.prescription_id == prescription_id,
            Charge.charge_type == ChargeType.PHARMACY
        ).first()
        
        # Block if payment required but no charge exists
        if not charge:
            return RedirectResponse(
                url=f"/pharmacy/ghana/prescriptions/{prescription_id}?error=Payment+required+-+No+charge+found.+Please+visit+billing+first.",
                status_code=302
            )
        
        if charge:
            invoice = db.query(Invoice).filter(Invoice.id == charge.invoice_id).first()
            if invoice and invoice.balance > 0:
                return RedirectResponse(
                    url=f"/pharmacy/ghana/prescriptions/{prescription_id}?error=Payment+required+-+balance+GHS+{str(invoice.balance)}",
                    status_code=302
                )
    
    # Find the invoice linked to this prescription (if any)
    invoice_id = None
    charge = db.query(Charge).filter(
        Charge.prescription_id == prescription_id,
        Charge.charge_type == ChargeType.PHARMACY
    ).first()
    if charge and charge.invoice_id:
        invoice_id = charge.invoice_id
    
    # Handle dispensing with Ghana pharmacy system
    if prescription.pharmacy_drug_id:
        # Create dispense record
        dispense = PharmacyDispense(
            patient_id=patient_id,
            encounter_id=prescription.encounter_id,
            prescription_id=prescription_id,  # Link to prescription
            invoice_id=invoice_id,  # Link to invoice
            prescriber_id=prescription.prescribed_by_id,
            status="DISPENSED",
            dispensed_by_id=current_user.id,
            dispensed_at=datetime.now(),
            payment_type=payment_type,
            notes=dispense_instructions
        )
        db.add(dispense)
        db.flush()
        
        # Get the batch
        batch = None
        if batch_id:
            try:
                batch = db.query(PharmacyBatch).filter(
                    PharmacyBatch.id == UUID(batch_id)
                ).first()
            except ValueError:
                pass
        
        # If no batch specified, get FEFO batch
        if not batch:
            batch = db.query(PharmacyBatch).filter(
                PharmacyBatch.drug_id == prescription.pharmacy_drug_id,
                PharmacyBatch.status == "ACTIVE",
                PharmacyBatch.expiry_date >= date.today(),
                PharmacyBatch.qty_on_hand >= qty_dispensed
            ).order_by(PharmacyBatch.expiry_date.asc()).first()
        
        if not batch:
            return RedirectResponse(
                url=f"/pharmacy/ghana/prescriptions/{prescription_id}?error=No+available+batch",
                status_code=302
            )
        
        # Calculate total
        unit_price = selling_price if selling_price else batch.selling_price
        total = unit_price * qty_dispensed
        
        # Calculate cost and margin
        unit_cost = batch.unit_cost or 0
        total_cost = unit_cost * qty_dispensed
        margin = float(total) - float(total_cost)
        
        # Create dispense item
        item = PharmacyDispenseItem(
            dispense_id=dispense.id,
            drug_id=prescription.pharmacy_drug_id,
            dosage_instructions=dispense_instructions or prescription.instructions,
            qty_prescribed=prescription.quantity,
            qty_dispensed=qty_dispensed,
            unit_selling_price=unit_price,
            unit_cost_snapshot=unit_cost,  # Actual cost from batch
            total_amount=total,
            total_cost=total_cost,  # For profit calculation
            margin=margin
        )
        db.add(item)
        db.flush()
        
        # Create FEFO allocation
        allocation = PharmacyDispenseAllocation(
            dispense_item_id=item.id,
            batch_id=batch.id,
            qty_allocated=qty_dispensed
        )
        db.add(allocation)
        
        # Update batch quantities
        batch.qty_on_hand -= qty_dispensed
        
        # Create stock ledger entry
        ledger = PharmacyStockLedger(
            store_id=batch.store_id,
            drug_id=prescription.pharmacy_drug_id,
            batch_id=batch.id,
            movement_type="DISPENSE",
            qty_in=0,
            qty_out=qty_dispensed,
            unit_cost_snapshot=batch.unit_cost,
            selling_price_snapshot=unit_price,
            reference_type="PRESCRIPTION",
            reference_id=dispense.id,
            note=f"Dispensed for prescription #{prescription_id}",
            created_by_id=current_user.id
        )
        db.add(ledger)
    else:
        # Fallback to legacy inventory system
        from app.crud import inventory_crud
        
        if prescription.medication_id:
            inventory_crud.record_sale(
                db,
                medication_id=prescription.medication_id,
                quantity=qty_dispensed,
                prescription_id=prescription_id,
                transaction_type="SALE",
                notes=f"Dispensed for prescription #{prescription_id}"
            )
    
    # Update prescription status
    prescription.status = OrderStatus.COMPLETED
    prescription.dispensed_by_id = current_user.id
    prescription.dispensed_at = datetime.now()
    
    # Note: Billing was already handled when pharmacy set the quantity
    # No reconciliation needed - billing matches what pharmacy decided
    
    db.commit()
    
    return RedirectResponse(
        url=f"/pharmacy/ghana/prescriptions/{prescription_id}?status=dispensed",
        status_code=302
    )


@router.post("/pharmacy/ghana/prescriptions/{prescription_id}/cancel", name="cancel_prescription_ghana")
async def cancel_prescription_ghana(
    request: Request,
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    reason: str = Form(...),
):
    """Cancel a prescription."""
    from app.models.encounter_models import Prescription, OrderStatus
    
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    if prescription.status == OrderStatus.COMPLETED:
        return RedirectResponse(
            url=f"/pharmacy/ghana/prescriptions/{prescription_id}?error=Cannot+cancel+completed+prescription",
            status_code=302
        )
    
    # Update status
    prescription.status = OrderStatus.CANCELLED
    
    # Add cancellation note
    current_notes = prescription.instructions or ""
    cancellation_note = f"\n\n[CANCELLED by {current_user.full_name or current_user.username} on {datetime.now().strftime('%Y-%m-%d %H:%M')}: {reason}]"
    prescription.instructions = current_notes + cancellation_note
    
    db.commit()
    
    return RedirectResponse(
        url=f"/pharmacy/ghana/prescriptions/{prescription_id}?status=cancelled",
        status_code=302
    )


@router.get("/pharmacy/ghana/prescriptions/{prescription_id}/print", name="print_dispense_receipt")
def print_dispense_receipt(
    request: Request,
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Print dispense receipt."""
    from app.models.encounter_models import Prescription, Encounter
    from app.models.patient_models import Patient
    from app.models.pharmacy_models import PharmacyDispense, PharmacyDispenseItem
    
    prescription = db.query(Prescription).options(
        joinedload(Prescription.encounter).joinedload(Encounter.patient),
        joinedload(Prescription.prescribed_by),
        joinedload(Prescription.dispensed_by)
    ).filter(Prescription.id == prescription_id).first()
    
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    patient = prescription.encounter.patient if prescription.encounter else None
    
    # Get dispense records
    dispenses = db.query(PharmacyDispense).filter(
        PharmacyDispense.prescription_id == prescription_id
    ).all()
    
    context = {
        "request": request,
        "title": f"Dispense Receipt #{prescription_id}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "prescription": prescription,
        "patient": patient,
        "dispenses": dispenses,
    }
    return templates.TemplateResponse("pharmacy_ghana/dispense_receipt.html", context)


@router.get("/pharmacy/pending", name="all_pending_prescriptions")
def all_pending_prescriptions(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Redirect to Ghana pharmacy prescriptions list."""
    return RedirectResponse(url="/pharmacy/ghana/prescriptions", status_code=302)


# =======================================================
# PHASE 4: Stock Ledger Reports
# =======================================================

@router.get("/pharmacy/ghana/reports/stock-ledger", name="pharmacy_stock_ledger_report")
def pharmacy_stock_ledger_report(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff", "Finance", "Management"])),
    drug_id: Optional[str] = Query(None),
    store_id: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    movement_type: Optional[str] = Query(None),
):
    """Stock Ledger Report with running balances."""
    from app.models.pharmacy_models import (
        PharmacyStockLedger, PharmacyDrug, PharmacyStore, PharmacyBatch
    )
    from sqlalchemy import func
    from uuid import UUID
    
    selected_drug_id = None
    selected_store_id = None
    
    query = db.query(PharmacyStockLedger).options(
        joinedload(PharmacyStockLedger.drug),
        joinedload(PharmacyStockLedger.store),
        joinedload(PharmacyStockLedger.batch)
    )
    
    if drug_id:
        try:
            selected_drug_id = UUID(drug_id)
            query = query.filter(PharmacyStockLedger.drug_id == selected_drug_id)
        except ValueError:
            pass
    
    if store_id:
        try:
            selected_store_id = UUID(store_id)
            query = query.filter(PharmacyStockLedger.store_id == selected_store_id)
        except ValueError:
            pass
    
    if from_date:
        try:
            f = datetime.strptime(from_date, '%Y-%m-%d')
            query = query.filter(func.date(PharmacyStockLedger.created_at) >= f)
        except ValueError:
            pass
    
    if to_date:
        try:
            t = datetime.strptime(to_date, '%Y-%m-%d')
            query = query.filter(func.date(PharmacyStockLedger.created_at) <= t)
        except ValueError:
            pass
    
    if movement_type:
        query = query.filter(PharmacyStockLedger.movement_type == movement_type)
    
    ledger_entries = query.order_by(PharmacyStockLedger.created_at.desc()).limit(500).all()
    
    running_balances = {}
    for entry in reversed(ledger_entries):
        key = (entry.drug_id, entry.store_id)
        current = running_balances.get(key, 0)
        running_balances[key] = current + (entry.qty_in or 0) - (entry.qty_out or 0)
        entry.running_balance = running_balances[key]
    
    total_transactions = len(ledger_entries)
    total_qty_in = float(sum(e.qty_in for e in ledger_entries if e.qty_in))
    total_qty_out = float(sum(e.qty_out for e in ledger_entries if e.qty_out))
    total_value = float(sum(
        (e.selling_price_snapshot or 0) * (e.qty_out or 0) 
        for e in ledger_entries if e.qty_out
    ))
    
    drugs = db.query(PharmacyDrug).filter(PharmacyDrug.is_active == True).order_by(PharmacyDrug.generic_name).all()
    stores = db.query(PharmacyStore).order_by(PharmacyStore.name).all()
    
    from app.crud import hospital_settings_crud
    
    context = {
        "request": request,
        "title": "Stock Ledger Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "ledger_entries": ledger_entries,
        "drugs": drugs,
        "stores": stores,
        "selected_drug_id": drug_id,
        "selected_store_id": store_id,
        "from_date": from_date,
        "to_date": to_date,
        "movement_type": movement_type,
        "total_transactions": total_transactions,
        "total_qty_in": total_qty_in,
        "total_qty_out": total_qty_out,
        "total_value": round(total_value, 2),
        "hospital_settings": hospital_settings_crud.get_hospital_settings(db),
    }
    return templates.TemplateResponse("pharmacy_ghana/stock_ledger_report.html", context)


@router.get("/pharmacy/ghana/reports/profit-margin", name="pharmacy_profit_report")
def pharmacy_profit_report(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Finance", "Management"])),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
):
    """Profit and Margin Report - Only visible to roles with can_view_margin."""
    from app.models.pharmacy_models import (
        PharmacyStockLedger, PharmacyDispense, PharmacyDispenseItem, PharmacyRolePolicy
    )
    from sqlalchemy import func
    
    policy = db.query(PharmacyRolePolicy).filter(
        PharmacyRolePolicy.role_name == current_user.role.name
    ).first()
    
    if not policy or not policy.can_view_margin:
        raise HTTPException(status_code=403, detail="You don't have permission to view profit reports")
    
    query = db.query(PharmacyDispenseItem, PharmacyDispense).join(
        PharmacyDispense, PharmacyDispenseItem.dispense_id == PharmacyDispense.id
    )
    
    if from_date:
        try:
            f = datetime.strptime(from_date, '%Y-%m-%d')
            query = query.filter(func.date(PharmacyDispense.dispensed_at) >= f)
        except ValueError:
            pass
    
    if to_date:
        try:
            t = datetime.strptime(to_date, '%Y-%m-%d')
            query = query.filter(func.date(PharmacyDispense.dispensed_at) <= t)
        except ValueError:
            pass
    
    items = query.all()
    
    total_revenue = float(sum(i.total_amount for i, d in items if i.total_amount))
    profit = total_revenue * 0.25  # Approximate 25% margin
    margin = 25.0
    
    from app.crud import hospital_settings_crud
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": "Profit & Margin Report",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "items": items,
        "from_date": from_date,
        "to_date": to_date,
        "total_revenue": total_revenue,
        "total_cost": total_revenue - profit,
        "profit": profit,
        "margin": margin,
        "hospital_settings": hospital_settings,
    }
    return templates.TemplateResponse("pharmacy_ghana/profit_report.html", context)
