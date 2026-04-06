"""
Pharmacy Ghana-Ready API
- Formulary search for prescribing (MUST select formulation)
- Inventory, stock-in, dispense, FEFO
- Role-based pricing visibility
- Interaction check
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func
from typing import Optional, List

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.core.templates import templates
from app.models.pharmacy_models import (
    PharmacyDosageForm, PharmacyDrug, PharmacySupplier, PharmacyStore,
    PharmacyBatch, PharmacyStockLedger, PharmacyDispense, PharmacyDispenseItem,
    PharmacyDispenseAllocation, PharmacyDrugInteraction, PharmacyRolePolicy,
    PatientActiveMedication,
)
from app.models.encounter_models import Prescription, Encounter
from app.models.patient_models import Patient
from app.models.inventory_models import Medication, StockItem
from app.services.pharmacy_fefo import (
    get_available_batches_fefo,
    allocate_fefo,
    stock_in_create_batch,
    _append_ledger,
)
from app.schemas.pharmacy_schemas import DrugCreate, DrugUpdate

router = APIRouter(prefix="/pharmacy", tags=["Pharmacy Ghana"])


def _can_view_cost(db: Session, role_name: str) -> bool:
    p = db.query(PharmacyRolePolicy).filter(PharmacyRolePolicy.role_name == role_name).first()
    if p:
        return p.can_view_unit_cost
    return role_name and role_name.lower() == "admin"


# --- Formulary search (for prescribing) ---
@router.get("/formulary/search", name="pharmacy_formulary_search")
def formulary_search(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Search formulations: generic + strength + dosage form + route. Doctor MUST select one."""
    from datetime import datetime
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Formulary search called with q={q}")
    
    search = f"%{q.strip()}%"
    items = (
        db.query(PharmacyDrug)
        .options(joinedload(PharmacyDrug.dosage_form))
        .filter(
            PharmacyDrug.is_active == True,
            or_(
                PharmacyDrug.generic_name.ilike(search),
                PharmacyDrug.brand_name.ilike(search),
                PharmacyDrug.item_code.ilike(search),
            ),
        )
        .order_by(PharmacyDrug.generic_name, PharmacyDrug.strength_value)
        .limit(50)
        .all()
    )
    
    # Get active store
    store = db.query(PharmacyStore).filter(PharmacyStore.is_active == True).first()
    
    out = []
    for d in items:
        df = d.dosage_form.name if d.dosage_form else ""
        strength = f"{d.strength_value} {d.strength_unit or ''}" if d.strength_value else ""
        if d.concentration_value:
            strength = f"{d.concentration_value} {d.concentration_unit or ''}"
        label = f"{d.generic_name}"
        if strength:
            label += f" {strength}"
        label += f" {df}"
        if d.route:
            label += f" ({d.route})"
        
        # Get price and stock from pharmacy batches
        default_price = None
        available_stock = 0
        if store:
            # Get FEFO batch (earliest expiry first)
            batch = db.query(PharmacyBatch).filter(
                PharmacyBatch.store_id == store.id,
                PharmacyBatch.drug_id == d.id,
                PharmacyBatch.status == "ACTIVE",
                PharmacyBatch.expiry_date >= datetime.now().date(),
                PharmacyBatch.qty_on_hand > 0,
            ).order_by(PharmacyBatch.expiry_date.asc()).first()
            
            if batch and batch.selling_price:
                default_price = float(batch.selling_price)
            
            # Calculate total available stock
            batches = db.query(PharmacyBatch).filter(
                PharmacyBatch.store_id == store.id,
                PharmacyBatch.drug_id == d.id,
                PharmacyBatch.status == "ACTIVE",
                PharmacyBatch.expiry_date >= datetime.now().date(),
            ).all()
            available_stock = float(sum(b.qty_on_hand for b in batches if b.qty_on_hand > 0))
        
        out.append({
            "id": str(d.id),
            "item_code": d.item_code,
            "label": label,
            "generic_name": d.generic_name,
            "brand_name": d.brand_name,
            "dosage_form": df,
            "strength_value": float(d.strength_value) if d.strength_value else None,
            "strength_unit": d.strength_unit,
            "route": d.route,
            "concentration_value": float(d.concentration_value) if d.concentration_value else None,
            "concentration_unit": d.concentration_unit,
            "pack_size": d.pack_size,
            "is_controlled": d.is_controlled,
            "default_price": default_price,
            "available_stock": available_stock,
        })
    return JSONResponse(content=out)


@router.get("/formulary/{drug_id}", name="pharmacy_formulary_detail")
def formulary_detail(
    drug_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Pharmacy Staff"])),
):
    """Full formulation details."""
    d = db.query(PharmacyDrug).options(joinedload(PharmacyDrug.dosage_form)).filter(
        PharmacyDrug.id == drug_id,
        PharmacyDrug.is_active == True
    ).first()
    if not d:
        raise HTTPException(404, "Drug not found")
    df = d.dosage_form.name if d.dosage_form else ""
    return JSONResponse(content={
        "id": str(d.id),
        "item_code": d.item_code,
        "generic_name": d.generic_name,
        "brand_name": d.brand_name,
        "dosage_form": df,
        "dosage_form_id": str(d.dosage_form_id),
        "strength_value": float(d.strength_value) if d.strength_value else None,
        "strength_unit": d.strength_unit,
        "route": d.route,
        "concentration_value": float(d.concentration_value) if d.concentration_value else None,
        "concentration_unit": d.concentration_unit,
        "pack_size": d.pack_size,
        "is_controlled": d.is_controlled,
    })


# --- Interactions ---
@router.get("/interactions/check", name="pharmacy_interaction_check")
def interaction_check(
    patient_id: int = Query(...),
    drug_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Pharmacy Staff"])),
):
    """Check drug interactions against patient's active meds (from recent prescriptions)."""
    # Get patient's recent prescriptions with pharmacy_drug_id (via encounter)
    recent = (
        db.query(Prescription.pharmacy_drug_id)
        .join(Encounter, Prescription.encounter_id == Encounter.id)
        .filter(
            Encounter.patient_id == patient_id,
            Prescription.pharmacy_drug_id.isnot(None),
            Prescription.pharmacy_drug_id != drug_id,
        )
        .filter(Prescription.prescribed_at >= datetime.now() - timedelta(days=90))
        .distinct()
        .all()
    )
    other_ids = [r[0] for r in recent if r[0]]
    if not other_ids:
        return JSONResponse(content={"has_interactions": False, "interactions": []})
    # Check pharmacy_drug_interaction
    ints = (
        db.query(PharmacyDrugInteraction)
        .filter(
            PharmacyDrugInteraction.is_active == True,
            or_(
                and_(PharmacyDrugInteraction.drug_a_id == drug_id, PharmacyDrugInteraction.drug_b_id.in_(other_ids)),
                and_(PharmacyDrugInteraction.drug_b_id == drug_id, PharmacyDrugInteraction.drug_a_id.in_(other_ids)),
            ),
        )
        .all()
    )
    out = []
    for i in ints:
        out.append({
            "severity": i.severity,
            "description": i.description,
            "recommendation": i.recommendation,
        })
    return JSONResponse(content={"has_interactions": len(out) > 0, "interactions": out})


# --- Stock-in ---
@router.post("/stores/{store_id}/stock-in", name="pharmacy_stock_in")
def stock_in(
    store_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    drug_id: UUID = Query(...),
    batch_no: str = Query(...),
    expiry_date: date = Query(...),
    qty: float = Query(...),
    unit_cost: Optional[float] = Query(None),
    selling_price: Optional[float] = Query(None),
    supplier_id: Optional[UUID] = Query(None),
    invoice_ref: Optional[str] = Query(None),
):
    """Stock-in: creates/updates batch and ledger."""
    if qty <= 0:
        raise HTTPException(400, "qty must be positive")
    batch = stock_in_create_batch(
        db,
        drug_id=drug_id,
        store_id=store_id,
        batch_no=batch_no,
        expiry_date=expiry_date,
        qty=Decimal(str(qty)),
        unit_cost=Decimal(str(unit_cost)) if unit_cost else None,
        selling_price=Decimal(str(selling_price)) if selling_price else None,
        supplier_id=supplier_id,
        invoice_ref=invoice_ref,
        created_by_id=current_user.id,
    )
    db.commit()
    return JSONResponse(content={"batch_id": str(batch.id), "qty_on_hand": float(batch.qty_on_hand)})


# --- Reports ---
@router.post("/stores/{store_id}/batches/{batch_id}/adjust", name="pharmacy_batch_adjust")
def adjust_batch_stock(
    store_id: UUID,
    batch_id: UUID,
    adjustment_qty: float = Form(...),
    reason: str = Form(...),  # DAMAGED, EXPIRED, RETURNED, CORRECTION, THEFT
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """
    Adjust batch stock with reason codes.
    Positive adjustment_qty adds stock, negative removes stock.
    Reasons: DAMAGED, EXPIRED, RETURNED, CORRECTION, THEFT, OTHER
    """
    valid_reasons = ["DAMAGED", "EXPIRED", "RETURNED", "CORRECTION", "THEFT", "OTHER"]
    if reason.upper() not in valid_reasons:
        raise HTTPException(400, f"Invalid reason. Must be one of: {', '.join(valid_reasons)}")
    
    batch = db.query(PharmacyBatch).filter(
        PharmacyBatch.id == batch_id,
        PharmacyBatch.store_id == store_id,
    ).first()
    
    if not batch:
        raise HTTPException(404, "Batch not found")
    
    adjustment = Decimal(str(adjustment_qty))
    old_qty = batch.qty_on_hand
    
    # Apply adjustment
    new_qty = old_qty + adjustment
    if new_qty < 0:
        raise HTTPException(400, f"Cannot reduce stock below zero. Current: {old_qty}, Requested: {adjustment}")
    
    batch.qty_on_hand = new_qty
    
    # Update status based on quantity
    if new_qty <= 0:
        batch.status = "DEPLETED"
    elif batch.expiry_date and batch.expiry_date < date.today():
        batch.status = "EXPIRED"
    else:
        batch.status = "ACTIVE"
    
    # Create ledger entry
    movement_type = f"ADJUST_{reason.upper()}"
    _append_ledger(
        db=db,
        store_id=store_id,
        drug_id=batch.drug_id,
        batch_id=batch_id,
        movement_type=movement_type,
        qty_in=adjustment if adjustment > 0 else Decimal("0"),
        qty_out=abs(adjustment) if adjustment < 0 else Decimal("0"),
        unit_cost_snapshot=batch.unit_cost,
        selling_price_snapshot=batch.selling_price,
        reference_type="ADJUSTMENT",
        reference_id=None,
        note=note or f"Stock adjustment: {reason}",
        created_by_id=current_user.id,
    )
    
    db.commit()
    return JSONResponse(content={
        "success": True,
        "batch_id": str(batch_id),
        "old_qty": float(old_qty),
        "adjustment": float(adjustment),
        "new_qty": float(new_qty),
        "reason": reason.upper(),
        "status": batch.status,
    })


# --- Bulk Import/Export ---
@router.post("/stores/{store_id}/batches/bulk-import-json", name="pharmacy_batch_bulk_import_json")
def bulk_import_batches_json(
    store_id: UUID,
    batches_data: List[dict],
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """
    Bulk import batches from JSON array.
    Expected format:
    [
      {"drug_code": "...", "batch_no": "...", "expiry_date": "YYYY-MM-DD", "qty": 100, "unit_cost": 10.00, "selling_price": 15.00, "supplier_name": "..."}
    ]
    """
    from uuid import uuid4
    
    store = db.query(PharmacyStore).filter(PharmacyStore.id == store_id).first()
    if not store:
        raise HTTPException(404, "Store not found")
    
    results = {"success": [], "errors": []}
    
    for idx, item in enumerate(batches_data):
        try:
            # Find drug by code or name
            drug = None
            if "drug_id" in item:
                drug = db.query(PharmacyDrug).filter(PharmacyDrug.id == UUID(item["drug_id"])).first()
            elif "drug_code" in item:
                drug = db.query(PharmacyDrug).filter(PharmacyDrug.item_code == item["drug_code"]).first()
            elif "generic_name" in item:
                drug = db.query(PharmacyDrug).filter(
                    PharmacyDrug.generic_name.ilike(item["generic_name"])
                ).first()
            
            if not drug:
                results["errors"].append({"index": idx, "error": f"Drug not found: {item.get('drug_code') or item.get('generic_name')}"})
                continue
            
            # Find or create supplier
            supplier = None
            if item.get("supplier_name"):
                supplier = db.query(PharmacySupplier).filter(
                    PharmacySupplier.name.ilike(item["supplier_name"])
                ).first()
            
            # Check if batch exists
            batch = db.query(PharmacyBatch).filter(
                PharmacyBatch.store_id == store_id,
                PharmacyBatch.drug_id == drug.id,
                PharmacyBatch.batch_no == item.get("batch_no"),
            ).first()
            
            if batch:
                # Update existing batch
                batch.qty_on_hand = (batch.qty_on_hand or Decimal("0")) + Decimal(str(item.get("qty", 0)))
                if item.get("unit_cost"):
                    batch.unit_cost = Decimal(str(item["unit_cost"]))
                if item.get("selling_price"):
                    batch.selling_price = Decimal(str(item["selling_price"]))
            else:
                # Create new batch
                batch = PharmacyBatch(
                    id=uuid4(),
                    store_id=store_id,
                    drug_id=drug.id,
                    batch_no=item.get("batch_no", f"BATCH-{idx+1}"),
                    expiry_date=date.fromisoformat(item["expiry_date"]) if item.get("expiry_date") else None,
                    qty_on_hand=Decimal(str(item.get("qty", 0))),
                    unit_cost=Decimal(str(item["unit_cost"])) if item.get("unit_cost") else None,
                    selling_price=Decimal(str(item["selling_price"])) if item.get("selling_price") else None,
                    supplier_id=supplier.id if supplier else None,
                    status="ACTIVE",
                    created_by_id=current_user.id,
                )
                db.add(batch)
            
            # Create ledger entry
            _append_ledger(
                db=db,
                store_id=store_id,
                drug_id=drug.id,
                batch_id=batch.id if batch.id else None,
                movement_type="STOCK_IN",
                qty_in=Decimal(str(item.get("qty", 0))),
                qty_out=Decimal("0"),
                unit_cost_snapshot=Decimal(str(item["unit_cost"])) if item.get("unit_cost") else None,
                selling_price_snapshot=Decimal(str(item["selling_price"])) if item.get("selling_price") else None,
                reference_type="BULK_IMPORT",
                reference_id=None,
                note=f"Bulk import: {item.get('batch_no')}",
                created_by_id=current_user.id,
            )
            
            results["success"].append({"index": idx, "batch_no": item.get("batch_no"), "drug": drug.generic_name})
            
        except Exception as e:
            results["errors"].append({"index": idx, "error": str(e)})
    
    db.commit()
    return JSONResponse(content=results)


@router.get("/stores/{store_id}/batches/export", name="pharmacy_batch_export")
def export_batches_csv(
    store_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Export batches to CSV format."""
    import csv
    from io import StringIO
    from fastapi.responses import StreamingResponse
    
    batches = db.query(PharmacyBatch).options(
        joinedload(PharmacyBatch.drug),
        joinedload(PharmacyBatch.supplier),
    ).filter(PharmacyBatch.store_id == store_id).order_by(PharmacyBatch.expiry_date).all()
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "drug_code", "generic_name", "batch_no", "expiry_date", 
        "qty_on_hand", "unit_cost", "selling_price", "supplier_name", "status"
    ])
    
    # Data
    for b in batches:
        writer.writerow([
            b.drug.item_code if b.drug else "",
            b.drug.generic_name if b.drug else "",
            b.batch_no,
            str(b.expiry_date) if b.expiry_date else "",
            float(b.qty_on_hand) if b.qty_on_hand else 0,
            float(b.unit_cost) if b.unit_cost else "",
            float(b.selling_price) if b.selling_price else "",
            b.supplier.name if b.supplier else "",
            b.status,
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=batches_{store_id}.csv"}
    )


@router.get("/reports/near-expiry", name="pharmacy_report_near_expiry")
def report_near_expiry(
    days: int = Query(90, ge=1),
    store_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Batches expiring within N days."""
    cutoff = date.today() + timedelta(days=days)
    q = db.query(PharmacyBatch).options(
        joinedload(PharmacyBatch.drug),
        joinedload(PharmacyBatch.store),
    ).filter(
        PharmacyBatch.status == "ACTIVE",
        PharmacyBatch.expiry_date <= cutoff,
        PharmacyBatch.expiry_date >= date.today(),
        PharmacyBatch.qty_on_hand > 0,
    )
    if store_id:
        q = q.filter(PharmacyBatch.store_id == store_id)
    batches = q.order_by(PharmacyBatch.expiry_date).all()
    out = []
    for b in batches:
        out.append({
            "batch_id": str(b.id),
            "drug": b.drug.generic_name if b.drug else "",
            "batch_no": b.batch_no,
            "expiry_date": str(b.expiry_date),
            "qty_on_hand": float(b.qty_on_hand),
        })
    return JSONResponse(content=out)


@router.get("/reports/stock-ledger", name="pharmacy_report_stock_ledger")
def report_stock_ledger(
    from_date: date = Query(...),
    to_date: date = Query(...),
    store_id: Optional[UUID] = Query(None),
    drug_id: Optional[UUID] = Query(None),
    movement_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Stock ledger report with filters: store, date range, drug, movement type."""
    q = db.query(PharmacyStockLedger).options(
        joinedload(PharmacyStockLedger.drug),
        joinedload(PharmacyStockLedger.store),
    ).filter(
        PharmacyStockLedger.created_at >= datetime.combine(from_date, datetime.min.time()),
        PharmacyStockLedger.created_at <= datetime.combine(to_date, datetime.max.time()),
    )
    if store_id:
        q = q.filter(PharmacyStockLedger.store_id == store_id)
    if drug_id:
        q = q.filter(PharmacyStockLedger.drug_id == drug_id)
    if movement_type:
        q = q.filter(PharmacyStockLedger.movement_type == movement_type)
    
    entries = q.order_by(PharmacyStockLedger.created_at).all()
    
    # Calculate running balance per drug
    balances = {}
    out = []
    for entry in entries:
        drug_id_str = str(entry.drug_id)
        if drug_id_str not in balances:
            balances[drug_id_str] = 0
        
        qty_in = float(entry.qty_in) if entry.qty_in else 0
        qty_out = float(entry.qty_out) if entry.qty_out else 0
        balances[drug_id_str] += qty_in - qty_out
        
        out.append({
            "date": entry.created_at.strftime("%Y-%m-%d %H:%M") if entry.created_at else "",
            "drug": entry.drug.generic_name if entry.drug else "",
            "store": entry.store.name if entry.store else "",
            "movement_type": entry.movement_type,
            "qty_in": qty_in,
            "qty_out": qty_out,
            "running_balance": balances[drug_id_str],
            "reference": f"{entry.reference_type}:{entry.reference_id}" if entry.reference_type else "",
            "note": entry.note,
        })
    return JSONResponse(content=out)


@router.get("/stores/{store_id}/batches/{batch_id}/history", name="pharmacy_batch_history")
def get_batch_history(
    store_id: UUID,
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Get stock movement history for a specific batch."""
    entries = db.query(PharmacyStockLedger).filter(
        PharmacyStockLedger.batch_id == batch_id,
        PharmacyStockLedger.store_id == store_id,
    ).order_by(PharmacyStockLedger.created_at.desc()).limit(50).all()
    
    out = []
    for e in entries:
        out.append({
            "date": e.created_at.strftime("%Y-%m-%d %H:%M") if e.created_at else "",
            "movement_type": e.movement_type,
            "qty_in": float(e.qty_in) if e.qty_in else 0,
            "qty_out": float(e.qty_out) if e.qty_out else 0,
            "reference": f"{e.reference_type}:{e.reference_id}" if e.reference_type else "",
            "note": e.note,
        })
    return JSONResponse(content=out)


@router.get("/reports/controlled-register", name="pharmacy_report_controlled_register")
def report_controlled_register(
    from_date: date = Query(...),
    to_date: date = Query(...),
    store_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Controlled drugs register: dispenses of controlled drugs with running balance."""
    from sqlalchemy import func
    # Get pharmacy_dispense items for controlled drugs
    q = (
        db.query(PharmacyDispenseItem, PharmacyDispense, PharmacyDrug)
        .join(PharmacyDispense, PharmacyDispenseItem.dispense_id == PharmacyDispense.id)
        .join(PharmacyDrug, PharmacyDispenseItem.drug_id == PharmacyDrug.id)
        .filter(
            PharmacyDrug.is_controlled == True,
            PharmacyDispense.status == "DISPENSED",
            PharmacyDispense.dispensed_at >= datetime.combine(from_date, datetime.min.time()),
            PharmacyDispense.dispensed_at <= datetime.combine(to_date, datetime.max.time()),
        )
        .order_by(PharmacyDispense.dispensed_at)
    )
    if store_id:
        # Filter by store if dispense has store context (we'd need store_id on dispense - skip for now)
        pass
    items = q.all()
    out = []
    for di, disp, drug in items:
        out.append({
            "date": str(disp.dispensed_at.date()) if disp.dispensed_at else "",
            "patient_id": disp.patient_id,
            "drug": drug.generic_name,
            "qty_dispensed": float(di.qty_dispensed) if di.qty_dispensed else 0,
            "dispensed_by": disp.dispensed_by_id,
        })
    return JSONResponse(content=out)



# --- Drug CRUD API ---
@router.get("/drugs", name="pharmacy_drugs_list")
def drugs_list_api(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
):
    """List all drugs with optional search, including price and stock info."""
    from datetime import date
    from sqlalchemy import func
    
    # Get active store
    store = db.query(PharmacyStore).filter(PharmacyStore.is_active == True).first()
    
    q = db.query(PharmacyDrug).options(joinedload(PharmacyDrug.dosage_form))
    if search:
        s = f"%{search}%"
        q = q.filter(
            or_(
                PharmacyDrug.generic_name.ilike(s),
                PharmacyDrug.brand_name.ilike(s),
                PharmacyDrug.item_code.ilike(s),
            )
        )
    q = q.filter(PharmacyDrug.is_active == True)
    total = q.count()
    drugs = q.order_by(PharmacyDrug.generic_name).offset((page - 1) * limit).limit(limit).all()
    
    out = []
    for d in drugs:
        df = d.dosage_form.name if d.dosage_form else ""
        strength = f"{d.strength_value} {d.strength_unit or ''}" if d.strength_value else ""
        if d.concentration_value:
            strength = f"{d.concentration_value} {d.concentration_unit or ''}"
        label = f"{d.generic_name}"
        if strength:
            label += f" {strength}"
        label += f" {df}"
        if d.route:
            label += f" ({d.route})"
        
        # Get stock and price info from pharmacy batches
        default_price = None
        available_stock = 0
        if store:
            # Get FEFO batch (earliest expiry first)
            batch = db.query(PharmacyBatch).filter(
                PharmacyBatch.store_id == store.id,
                PharmacyBatch.drug_id == d.id,
                PharmacyBatch.status == "ACTIVE",
                PharmacyBatch.expiry_date >= date.today(),
                PharmacyBatch.qty_on_hand > 0,
            ).order_by(PharmacyBatch.expiry_date.asc()).first()
            
            if batch and batch.selling_price:
                default_price = float(batch.selling_price)
            
            # Calculate total available stock
            batches = db.query(PharmacyBatch).filter(
                PharmacyBatch.store_id == store.id,
                PharmacyBatch.drug_id == d.id,
                PharmacyBatch.status == "ACTIVE",
                PharmacyBatch.expiry_date >= date.today(),
            ).all()
            available_stock = float(sum(b.qty_on_hand for b in batches if b.qty_on_hand > 0))
        
        out.append({
            "id": str(d.id),
            "item_code": d.item_code,
            "generic_name": d.generic_name,
            "brand_name": d.brand_name,
            "dosage_form": df,
            "dosage_form_id": str(d.dosage_form_id),
            "strength_value": float(d.strength_value) if d.strength_value else None,
            "strength_unit": d.strength_unit,
            "route": d.route,
            "concentration_value": float(d.concentration_value) if d.concentration_value else None,
            "concentration_unit": d.concentration_unit,
            "pack_size": d.pack_size,
            "reorder_level": float(d.reorder_level) if d.reorder_level else None,
            "reorder_qty": float(d.reorder_qty) if d.reorder_qty else None,
            "is_controlled": d.is_controlled,
            "label": label,
            "default_price": default_price,
            "available_stock": available_stock,
        })
    return JSONResponse(content={"total": total, "page": page, "limit": limit, "drugs": out})


@router.post("/drugs", name="pharmacy_drug_create", status_code=201)
async def drug_create_api(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Create a new drug/formulation. Accepts JSON or form data."""
    from decimal import Decimal
    
    # Check content type to determine how to parse the request
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        # Parse JSON body
        body = await request.json()
        drug_data = DrugCreate(**body)
        item_code = drug_data.item_code
        generic_name = drug_data.generic_name
        brand_name = drug_data.brand_name
        dosage_form_id = drug_data.dosage_form_id
        strength_value = drug_data.strength_value
        strength_unit = drug_data.strength_unit
        route = drug_data.route
        concentration_value = drug_data.concentration_value
        concentration_unit = drug_data.concentration_unit
        pack_size = drug_data.pack_size
        reorder_level = drug_data.reorder_level
        reorder_qty = drug_data.reorder_qty
        is_controlled = drug_data.is_controlled
        notes = drug_data.notes
    else:
        # Parse form data
        form_data = await request.form()
        item_code = form_data.get("item_code")
        generic_name = form_data.get("generic_name")
        brand_name = form_data.get("brand_name") or None
        dosage_form_id_str = form_data.get("dosage_form_id")
        strength_value_str = form_data.get("strength_value")
        strength_unit = form_data.get("strength_unit") or None
        route = form_data.get("route") or None
        concentration_value_str = form_data.get("concentration_value")
        concentration_unit = form_data.get("concentration_unit") or None
        pack_size_str = form_data.get("pack_size")
        reorder_level_str = form_data.get("reorder_level")
        reorder_qty_str = form_data.get("reorder_qty")
        is_controlled = form_data.get("is_controlled") == "on"
        notes = form_data.get("notes") or None
        
        # Convert string values
        try:
            dosage_form_id = UUID(dosage_form_id_str)
        except (ValueError, TypeError):
            raise HTTPException(400, "Invalid dosage_form_id")
        
        strength_value = Decimal(str(strength_value_str)) if strength_value_str else None
        concentration_value = Decimal(str(concentration_value_str)) if concentration_value_str else None
        pack_size = int(pack_size_str) if pack_size_str else None
        reorder_level = Decimal(str(reorder_level_str)) if reorder_level_str else None
        reorder_qty = Decimal(str(reorder_qty_str)) if reorder_qty_str else None
    
    # Check for required fields
    if not item_code:
        raise HTTPException(400, "item_code is required")
    if not generic_name:
        raise HTTPException(400, "generic_name is required")
    if not dosage_form_id:
        raise HTTPException(400, "dosage_form_id is required")
    
    existing = db.query(PharmacyDrug).filter(PharmacyDrug.item_code == item_code).first()
    if existing:
        raise HTTPException(400, f"Item code '{item_code}' already exists")
    df = db.query(PharmacyDosageForm).filter(PharmacyDosageForm.id == dosage_form_id).first()
    if not df:
        raise HTTPException(400, "Invalid dosage_form_id")
    drug = PharmacyDrug(
        item_code=item_code,
        generic_name=generic_name,
        brand_name=brand_name,
        dosage_form_id=dosage_form_id,
        strength_value=strength_value,
        strength_unit=strength_unit,
        route=route,
        concentration_value=concentration_value,
        concentration_unit=concentration_unit,
        pack_size=pack_size,
        reorder_level=reorder_level,
        reorder_qty=reorder_qty,
        is_controlled=is_controlled,
        notes=notes,
        is_active=True,
    )
    db.add(drug)
    db.commit()
    db.refresh(drug)
    return JSONResponse(content={"id": str(drug.id), "message": "Drug created successfully"})


@router.put("/drugs/{drug_id}", name="pharmacy_drug_update")
async def drug_update_api(
    drug_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Update a drug/formulation. Accepts JSON or form data."""
    from decimal import Decimal
    
    drug = db.query(PharmacyDrug).filter(PharmacyDrug.id == drug_id).first()
    if not drug:
        raise HTTPException(404, "Drug not found")
    
    # Check content type to determine how to parse the request
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        # Parse JSON body
        body = await request.json()
        drug_data = DrugUpdate(**body)
        item_code = drug_data.item_code
        generic_name = drug_data.generic_name
        brand_name = drug_data.brand_name
        dosage_form_id = drug_data.dosage_form_id
        strength_value = drug_data.strength_value
        strength_unit = drug_data.strength_unit
        route = drug_data.route
        concentration_value = drug_data.concentration_value
        concentration_unit = drug_data.concentration_unit
        pack_size = drug_data.pack_size
        reorder_level = drug_data.reorder_level
        reorder_qty = drug_data.reorder_qty
        is_controlled = drug_data.is_controlled
        notes = drug_data.notes
        is_active = drug_data.is_active
    else:
        # Parse form data
        form_data = await request.form()
        item_code = form_data.get("item_code")
        generic_name = form_data.get("generic_name")
        brand_name = form_data.get("brand_name")
        dosage_form_id_str = form_data.get("dosage_form_id")
        strength_value_str = form_data.get("strength_value")
        strength_unit = form_data.get("strength_unit")
        route = form_data.get("route")
        concentration_value_str = form_data.get("concentration_value")
        concentration_unit = form_data.get("concentration_unit")
        pack_size_str = form_data.get("pack_size")
        reorder_level_str = form_data.get("reorder_level")
        reorder_qty_str = form_data.get("reorder_qty")
        is_controlled_str = form_data.get("is_controlled")
        notes = form_data.get("notes")
        is_active_str = form_data.get("is_active")
        
        # Convert string values
        if dosage_form_id_str:
            try:
                dosage_form_id = UUID(dosage_form_id_str)
            except (ValueError, TypeError):
                raise HTTPException(400, "Invalid dosage_form_id")
        else:
            dosage_form_id = None
        
        strength_value = Decimal(str(strength_value_str)) if strength_value_str else None
        concentration_value = Decimal(str(concentration_value_str)) if concentration_value_str else None
        pack_size = int(pack_size_str) if pack_size_str else None
        reorder_level = Decimal(str(reorder_level_str)) if reorder_level_str else None
        reorder_qty = Decimal(str(reorder_qty_str)) if reorder_qty_str else None
        is_controlled = is_controlled_str == "on" if is_controlled_str else None
        is_active = is_active_str == "on" if is_active_str else None
    
    # Update drug fields
    if item_code is not None and item_code != drug.item_code:
        existing = db.query(PharmacyDrug).filter(PharmacyDrug.item_code == item_code, PharmacyDrug.id != drug_id).first()
        if existing:
            raise HTTPException(400, f"Item code '{item_code}' already exists")
        drug.item_code = item_code
    if generic_name is not None:
        drug.generic_name = generic_name
    if brand_name is not None:
        drug.brand_name = brand_name
    if dosage_form_id is not None:
        df = db.query(PharmacyDosageForm).filter(PharmacyDosageForm.id == dosage_form_id).first()
        if not df:
            raise HTTPException(400, "Invalid dosage_form_id")
        drug.dosage_form_id = dosage_form_id
    if strength_value is not None:
        drug.strength_value = strength_value
    if strength_unit is not None:
        drug.strength_unit = strength_unit
    if route is not None:
        drug.route = route
    if concentration_value is not None:
        drug.concentration_value = concentration_value
    if concentration_unit is not None:
        drug.concentration_unit = concentration_unit
    if pack_size is not None:
        drug.pack_size = pack_size
    if reorder_level is not None:
        drug.reorder_level = reorder_level
    if reorder_qty is not None:
        drug.reorder_qty = reorder_qty
    if is_controlled is not None:
        drug.is_controlled = is_controlled
    if notes is not None:
        drug.notes = notes
    if is_active is not None:
        drug.is_active = is_active
    db.commit()
    return JSONResponse(content={"id": str(drug.id), "message": "Drug updated successfully"})


@router.delete("/drugs/{drug_id}", name="pharmacy_drug_delete")
def drug_delete_api(
    drug_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
):
    """Soft delete a drug (set is_active=False)."""
    drug = db.query(PharmacyDrug).filter(PharmacyDrug.id == drug_id).first()
    if not drug:
        raise HTTPException(404, "Drug not found")
    drug.is_active = False
    db.commit()
    return JSONResponse(content={"id": str(drug.id), "message": "Drug deleted successfully"})



# --- Dispensing API ---
from datetime import datetime, date
from uuid import UUID


@router.post("/dispense", name="pharmacy_dispense_create")
def create_dispense(
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    patient_id: int = Query(...),
    encounter_id: Optional[int] = Query(None),
    prescriber_id: Optional[int] = Query(None),
    payment_type: Optional[str] = Query(None),
):
    """Create a new dispense draft."""
    # Verify patient exists
    from app.models.patient_models import Patient
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")
    
    dispense = PharmacyDispense(
        patient_id=patient_id,
        encounter_id=encounter_id,
        prescriber_id=prescriber_id,
        status="DRAFT",
        payment_type=payment_type,
    )
    db.add(dispense)
    db.commit()
    db.refresh(dispense)
    return JSONResponse(content={"id": str(dispense.id), "status": dispense.status})


@router.get("/dispense/{dispense_id}", name="pharmacy_dispense_detail")
def get_dispense(
    dispense_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Get dispense details with items and allocations."""
    from app.models.patient_models import Patient
    from sqlalchemy.orm import joinedload
    
    dispense = db.query(PharmacyDispense).options(
        joinedload(PharmacyDispense.patient),
        joinedload(PharmacyDispense.items).joinedload(PharmacyDispenseItem.drug),
        joinedload(PharmacyDispense.items).joinedload(PharmacyDispenseItem.allocations).joinedload(PharmacyDispenseAllocation.batch),
    ).filter(PharmacyDispense.id == dispense_id).first()
    
    if not dispense:
        raise HTTPException(404, "Dispense not found")
    
    items_out = []
    for item in dispense.items:
        item_dict = {
            "id": str(item.id),
            "drug_id": str(item.drug_id),
            "drug_name": item.drug.generic_name if item.drug else "",
            "dosage_instructions": item.dosage_instructions,
            "qty_prescribed": float(item.qty_prescribed) if item.qty_prescribed else None,
            "qty_dispensed": float(item.qty_dispensed),
            "unit_selling_price": float(item.unit_selling_price) if item.unit_selling_price else None,
            "total_amount": float(item.total_amount) if item.total_amount else None,
            "allocations": [
                {
                    "batch_id": str(a.batch_id),
                    "batch_no": a.batch.batch_no if a.batch else "",
                    "expiry_date": str(a.batch.expiry_date) if a.batch and a.batch.expiry_date else "",
                    "qty_allocated": float(a.qty_allocated),
                }
                for a in item.allocations
            ]
        }
        items_out.append(item_dict)
    
    return JSONResponse(content={
        "id": str(dispense.id),
        "patient_id": dispense.patient_id,
        "status": dispense.status,
        "payment_type": dispense.payment_type,
        "items": items_out,
    })


@router.post("/dispense/{dispense_id}/items", name="pharmacy_dispense_add_item")
def add_dispense_item(
    dispense_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    drug_id: UUID = Query(...),
    qty_dispensed: float = Query(...),
    dosage_instructions: Optional[str] = Query(None),
    qty_prescribed: Optional[float] = Query(None),
    check_interactions: bool = Query(True),
):
    """Add an item to the dispense."""
    from app.models.patient_models import Patient
    
    # Verify dispense exists and is draft
    dispense = db.query(PharmacyDispense).filter(
        PharmacyDispense.id == dispense_id,
        PharmacyDispense.status == "DRAFT"
    ).first()
    if not dispense:
        raise HTTPException(400, "Dispense not found or not in DRAFT status")
    
    # Verify drug exists
    drug = db.query(PharmacyDrug).filter(PharmacyDrug.id == drug_id).first()
    if not drug:
        raise HTTPException(404, "Drug not found")
    
    # Check controlled drug permission
    if drug.is_controlled:
        policy = db.query(PharmacyRolePolicy).filter(
            PharmacyRolePolicy.role_name == current_user.role.name
        ).first()
        if not policy or not policy.can_dispense_controlled:
            raise HTTPException(403, "You don't have permission to dispense controlled drugs")
    
    # Check drug interactions (if enabled)
    interaction_warnings = []
    if check_interactions and dispense.patient_id:
        # Get patient's current drugs (from this dispense + recent prescriptions)
        other_drug_ids = set()
        
        # Add drugs already in this dispense
        for item in dispense.items:
            if item.drug_id != drug_id:
                other_drug_ids.add(item.drug_id)
        
        # Add recent prescriptions
        from app.models.encounter_models import Prescription, Encounter
        recent = db.query(Prescription.pharmacy_drug_id).join(
            Encounter, Prescription.encounter_id == Encounter.id
        ).filter(
            Encounter.patient_id == dispense.patient_id,
            Prescription.pharmacy_drug_id.isnot(None),
            Prescription.pharmacy_drug_id != drug_id,
            Prescription.prescribed_at >= datetime.now() - timedelta(days=90)
        ).distinct().all()
        
        for r in recent:
            if r[0]:
                other_drug_ids.add(UUID(r[0]))
        
        # Check interactions
        if other_drug_ids:
            ints = db.query(PharmacyDrugInteraction).filter(
                PharmacyDrugInteraction.is_active == True,
                or_(
                    and_(PharmacyDrugInteraction.drug_a_id == drug_id, PharmacyDrugInteraction.drug_b_id.in_(other_drug_ids)),
                    and_(PharmacyDrugInteraction.drug_b_id == drug_id, PharmacyDrugInteraction.drug_a_id.in_(other_drug_ids)),
                ),
            ).all()
            
            for i in ints:
                # Find the other drug name
                other_id = i.drug_b_id if i.drug_a_id == drug_id else i.drug_a_id
                other_drug = db.query(PharmacyDrug).filter(PharmacyDrug.id == other_id).first()
                other_name = other_drug.generic_name if other_drug else "Unknown"
                
                interaction_warnings.append({
                    "severity": i.severity,
                    "drug": other_name,
                    "description": i.description,
                    "recommendation": i.recommendation,
                })
    
    # Get current selling price from active batch
    batch = db.query(PharmacyBatch).filter(
        PharmacyBatch.drug_id == drug_id,
        PharmacyBatch.status == "ACTIVE",
        PharmacyBatch.expiry_date >= date.today(),
        PharmacyBatch.qty_on_hand > 0,
    ).order_by(PharmacyBatch.expiry_date.asc()).first()
    
    unit_price = float(batch.selling_price) if batch and batch.selling_price else 0
    total = unit_price * qty_dispensed
    
    item = PharmacyDispenseItem(
        dispense_id=dispense_id,
        drug_id=drug_id,
        qty_dispensed=Decimal(str(qty_dispensed)),
        dosage_instructions=dosage_instructions,
        qty_prescribed=Decimal(str(qty_prescribed)) if qty_prescribed else None,
        unit_selling_price=Decimal(str(unit_price)),
        total_amount=Decimal(str(total)),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    
    response = {
        "id": str(item.id),
        "drug_id": str(drug_id),
        "qty_dispensed": qty_dispensed,
    }
    
    # Include interaction warnings in response
    if interaction_warnings:
        response["interaction_warnings"] = interaction_warnings
        response["has_interactions"] = True
    else:
        response["has_interactions"] = False
    
    return JSONResponse(content=response)


@router.post("/dispense/{dispense_id}/allocate", name="pharmacy_dispense_allocate")
def allocate_dispense_items(
    dispense_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Allocate batches to all items using FEFO."""
    from app.services.pharmacy_fefo import allocate_batches_fefo
    
    dispense = db.query(PharmacyDispense).filter(
        PharmacyDispense.id == dispense_id,
        PharmacyDispense.status == "DRAFT"
    ).first()
    if not dispense:
        raise HTTPException(400, "Dispense not found or not in DRAFT status")
    
    # Get store (default to first store)
    store = db.query(PharmacyStore).first()
    if not store:
        raise HTTPException(400, "No pharmacy store configured")
    
    results = []
    for item in dispense.items:
        if item.allocations:  # Already allocated
            continue
        
        # Check for expired/near-expiry batches
        result = allocate_batches_fefo(db, store.id, item.drug_id, item.qty_dispensed)
        
        if not result["success"]:
            return JSONResponse(content={
                "success": False,
                "error": f"Drug {item.drug.generic_name}: {result['error']}"
            }, status_code=400)
        
        # Check for near-expiry warning (within 30 days)
        near_expiry_warnings = []
        for alloc in result["allocations"]:
            batch = db.query(PharmacyBatch).filter(PharmacyBatch.id == UUID(alloc["batch_id"])).first()
            if batch and batch.expiry_date:
                days_until = (batch.expiry_date - date.today()).days
                if days_until <= 30:
                    near_expiry_warnings.append(f"Batch {batch.batch_no} expires in {days_until} days")
        
        results.append({
            "item_id": str(item.id),
            "allocations": result["allocations"],
            "near_expiry_warnings": near_expiry_warnings,
        })
    
    return JSONResponse(content={
        "success": True,
        "results": results,
    })


@router.post("/dispense/{dispense_id}/finalize", name="pharmacy_dispense_finalize")
def finalize_dispense(
    dispense_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    override_interactions: bool = Query(False),
    interaction_override_reason: Optional[str] = Query(None),
):
    """Finalize dispense: create allocations, deduct stock, append ledger.
    
    If override_interactions=True, allows MAJOR interactions with reason stored.
    CONTRAINDICATED interactions always require override.
    """
    from app.services.pharmacy_fefo import allocate_batches_fefo
    from uuid import UUID
    
    dispense = db.query(PharmacyDispense).filter(
        PharmacyDispense.id == dispense_id,
        PharmacyDispense.status == "DRAFT"
    ).first()
    if not dispense:
        raise HTTPException(400, "Dispense not found or not in DRAFT status")
    
    # Check drug interactions before finalizing
    if dispense.patient_id and dispense.items:
        drug_ids_in_dispense = [item.drug_id for item in dispense.items]
        
        # Get recent prescriptions for the patient
        from app.models.encounter_models import Prescription, Encounter
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
                # pharmacy_drug_id is already a UUID, use directly
                other_drug_ids.add(r[0])
        
        # Check all interactions
        all_interactions = []
        for item in dispense.items:
            if other_drug_ids:
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
                        "description": i.description,
                        "recommendation": i.recommendation,
                    })
        
        # Check for CONTRAINDICATED interactions
        contraindicated = [i for i in all_interactions if i["severity"] == "CONTRAINDICATED"]
        if contraindicated and not override_interactions:
            raise HTTPException(400, {
                "detail": "CONTRAINDICATED drug interaction detected. Cannot finalize dispense.",
                "interactions": contraindicated,
            })
        
        # Check for MAJOR interactions
        major = [i for i in all_interactions if i["severity"] == "MAJOR"]
        if major and not override_interactions:
            raise HTTPException(400, {
                "detail": "MAJOR drug interaction detected. Use override_interactions=true with reason to proceed.",
                "interactions": major,
            })
        
        # Store interaction override info if overridden
        if override_interactions and (contraindicated or major):
            if not interaction_override_reason:
                raise HTTPException(400, "Override reason required when bypassing interaction warnings")
            # Store in notes field or create a new field
            existing_notes = dispense.notes or ""
            override_note = f"[INTERACTION OVERRIDE] {interaction_override_reason}"
            dispense.notes = f"{existing_notes}\n{override_note}" if existing_notes else override_note
    
    # Get store
    store = db.query(PharmacyStore).first()
    if not store:
        raise HTTPException(400, "No pharmacy store configured")
    
    # Process each item
    for item in dispense.items:
        if item.allocations:  # Already allocated
            continue
        
        # Allocate using FEFO
        result = allocate_batches_fefo(db, store.id, item.drug_id, item.qty_dispensed)
        
        if not result["success"]:
            db.rollback()
            raise HTTPException(400, f"Insufficient stock for {item.drug.generic_name}: {result['error']}")
        
        # Block if any allocation uses expired batch
        for alloc in result["allocations"]:
            batch = db.query(PharmacyBatch).filter(PharmacyBatch.id == UUID(alloc["batch_id"])).first()
            if batch and batch.expiry_date and batch.expiry_date < date.today():
                db.rollback()
                raise HTTPException(400, f"Cannot use expired batch {batch.batch_no}")
        
        # Create allocations and deduct stock
        for alloc in result["allocations"]:
            batch = db.query(PharmacyBatch).filter(PharmacyBatch.id == UUID(alloc["batch_id"])).first()
            
            # Prevent negative stock
            if batch.qty_on_hand < Decimal(str(alloc["qty_allocated"])):
                db.rollback()
                raise HTTPException(400, f"Insufficient stock for batch {batch.batch_no}")
            
            # Deduct from batch
            batch.qty_on_hand = batch.qty_on_hand - Decimal(str(alloc["qty_allocated"]))
            
            # Create allocation record
            allocation = PharmacyDispenseAllocation(
                dispense_item_id=item.id,
                batch_id=UUID(alloc["batch_id"]),
                qty_allocated=Decimal(str(alloc["qty_allocated"])),
            )
            db.add(allocation)
            
            # Append ledger
            from app.services.pharmacy_fefo import _append_ledger
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
    
    return JSONResponse(content={
        "success": True,
        "dispense_id": str(dispense_id),
        "status": dispense.status,
    })


# --- Dispense All for Patient ---
@router.post("/dispense/patient/{patient_id}", name="pharmacy_dispense_patient_all")
def dispense_all_for_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    encounter_id: Optional[int] = Query(None),
    prescriber_id: Optional[int] = Query(None),
    payment_type: Optional[str] = Query(None),
):
    """Create a new dispense with ALL pending prescriptions for a patient.
    
    This endpoint loads all pending prescriptions for a patient and creates
    a single dispense record with all medications.
    """
    from app.models.patient_models import Patient
    from app.models.encounter_models import Prescription, Encounter, OrderStatus
    
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")
    
    # Get pending prescriptions for this patient
    query = db.query(Prescription).join(Encounter).filter(
        Encounter.patient_id == patient_id,
        Prescription.status == OrderStatus.PENDING.value
    )
    
    # Optionally filter by encounter
    if encounter_id:
        query = query.filter(Prescription.encounter_id == encounter_id)
    
    # Only include prescriptions with pharmacy_drug_id (Ghana pharmacy)
    prescriptions = query.filter(
        Prescription.pharmacy_drug_id.isnot(None)
    ).all()
    
    if not prescriptions:
        raise HTTPException(400, "No pending prescriptions found for this patient")
    
    # Create a new dispense
    dispense = PharmacyDispense(
        patient_id=patient_id,
        encounter_id=encounter_id,
        prescriber_id=prescriber_id,
        status="DRAFT",
        payment_type=payment_type,
    )
    db.add(dispense)
    db.flush()  # Get the dispense ID
    
    # Add all prescriptions as dispense items
    items_added = []
    from datetime import date
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
        items_added.append({
            "prescription_id": prescription.id,
            "drug_id": str(prescription.pharmacy_drug_id),
            "qty": qty_to_dispense
        })
    
    db.commit()
    db.refresh(dispense)
    
    return JSONResponse(content={
        "id": str(dispense.id),
        "status": dispense.status,
        "patient_id": patient_id,
        "items_count": len(items_added),
        "items": items_added,
    })


# --- Returns & Write-offs ---
@router.post("/dispense/{dispense_id}/return", name="pharmacy_dispense_return")
def return_dispense(
    dispense_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Return a dispensed item to stock (patient returned medication)."""
    from app.services.pharmacy_fefo import _append_ledger
    
    dispense = db.query(PharmacyDispense).filter(
        PharmacyDispense.id == dispense_id,
        PharmacyDispense.status == "DISPENSED"
    ).first()
    if not dispense:
        raise HTTPException(400, "Dispense not found or not in DISPENSED status")
    
    # Get store
    store = db.query(PharmacyStore).first()
    if not store:
        raise HTTPException(400, "No pharmacy store configured")
    
    # Return each item to stock
    for item in dispense.items:
        # Find active batch for this drug
        batch = db.query(PharmacyBatch).filter(
            PharmacyBatch.drug_id == item.drug_id,
            PharmacyBatch.status == "ACTIVE",
            PharmacyBatch.expiry_date >= date.today(),
        ).order_by(PharmacyBatch.expiry_date.asc()).first()
        
        if batch:
            # Add back to existing batch
            batch.qty_on_hand = batch.qty_on_hand + item.qty_dispensed
        else:
            # Create new batch for returned stock
            batch = PharmacyBatch(
                drug_id=item.drug_id,
                store_id=store.id,
                batch_no=f"RETURN-{date.today().strftime('%Y%m%d')}",
                expiry_date=date.today() + timedelta(days=365),  # Default 1 year
                qty_on_hand=item.qty_dispensed,
                qty_reserved=0,
                status="ACTIVE",
                unit_cost=item.unit_selling_price,
                selling_price=item.unit_selling_price,
            )
            db.add(batch)
            db.flush()
        
        # Append ledger entry
        _append_ledger(
            db,
            store_id=store.id,
            drug_id=item.drug_id,
            batch_id=batch.id,
            movement_type="RETURN",
            qty_in=item.qty_dispensed,
            unit_cost_snapshot=batch.unit_cost,
            selling_price_snapshot=item.unit_selling_price,
            reference_type="DISPENSE_RETURN",
            reference_id=dispense_id,
            created_by_id=current_user.id,
        )
    
    # Update dispense status
    dispense.status = "RETURNED"
    dispense.notes = (dispense.notes or "") + "\n[RETURNED]"
    
    db.commit()
    
    return JSONResponse(content={
        "success": True,
        "dispense_id": str(dispense_id),
        "status": dispense.status,
    })


@router.post("/batch/{batch_id}/writeoff", name="pharmacy_batch_writeoff")
def writeoff_batch(
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    reason: str = Query(...),
    writeoff_type: str = Query(...),  # EXPIRED, DAMAGED
    qty: Optional[float] = Query(None),  # If null, write off all
    approved_by: Optional[int] = Query(None),  # Required for writeoffs (role policy check done via permission)
):
    """Write off batch quantity (expiry or damage). Requires approval check."""
    from app.services.pharmacy_fefo import _append_ledger
    
    # Check approval permission (Admin or Head of Pharmacy can approve)
    policy = db.query(PharmacyRolePolicy).filter(
        PharmacyRolePolicy.role_name == current_user.role.name
    ).first()
    
    if not policy or not policy.can_approve_adjustment:
        # Require explicit approval from another user
        if not approved_by:
            raise HTTPException(400, "Write-off requires approval. Provide approved_by user ID.")
    
    batch = db.query(PharmacyBatch).filter(PharmacyBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch not found")
    
    # Determine quantity to write off
    writeoff_qty = Decimal(str(qty)) if qty else batch.qty_on_hand
    if writeoff_qty > batch.qty_on_hand:
        raise HTTPException(400, "Write-off quantity exceeds available stock")
    
    # Get store
    store = db.query(PharmacyStore).filter(PharmacyStore.id == batch.store_id).first()
    
    # Deduct from batch
    batch.qty_on_hand = batch.qty_on_hand - writeoff_qty
    
    if batch.qty_on_hand <= 0:
        batch.status = "DEPLETED"
    
    # Append ledger entry
    _append_ledger(
        db,
        store_id=batch.store_id,
        drug_id=batch.drug_id,
        batch_id=batch.id,
        movement_type=f"WRITEOFF_{writeoff_type}",
        qty_out=writeoff_qty,
        unit_cost_snapshot=batch.unit_cost,
        reference_type="WRITEOFF",
        note=f"{writeoff_type}: {reason}",
        created_by_id=current_user.id,
    )
    
    db.commit()
    
    return JSONResponse(content={
        "success": True,
        "batch_id": str(batch_id),
        "writeoff_qty": float(writeoff_qty),
        "remaining_qty": float(batch.qty_on_hand),
    })
    
    # Process each item
    for item in dispense.items:
        if item.allocations:  # Already allocated
            continue
        
        # Allocate using FEFO
        result = allocate_batches_fefo(db, store.id, item.drug_id, item.qty_dispensed)
        
        if not result["success"]:
            db.rollback()
            raise HTTPException(400, f"Insufficient stock for {item.drug.generic_name}: {result['error']}")
        
        # Block if any allocation uses expired batch
        for alloc in result["allocations"]:
            batch = db.query(PharmacyBatch).filter(PharmacyBatch.id == UUID(alloc["batch_id"])).first()
            if batch and batch.expiry_date and batch.expiry_date < date.today():
                db.rollback()
                raise HTTPException(400, f"Cannot use expired batch {batch.batch_no}")
        
        # Create allocations and deduct stock
        for alloc in result["allocations"]:
            batch = db.query(PharmacyBatch).filter(PharmacyBatch.id == UUID(alloc["batch_id"])).first()
            
            # Deduct from batch
            batch.qty_on_hand = batch.qty_on_hand - Decimal(str(alloc["qty_allocated"]))
            
            # Create allocation record
            allocation = PharmacyDispenseAllocation(
                dispense_item_id=item.id,
                batch_id=UUID(alloc["batch_id"]),
                qty_allocated=Decimal(str(alloc["qty_allocated"])),
            )
            db.add(allocation)
            
            # Append ledger
            from app.services.pharmacy_fefo import _append_ledger
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
    
    return JSONResponse(content={
        "success": True,
        "dispense_id": str(dispense_id),
        "status": "DISPENSED",
    })


@router.get("/dispense/{dispense_id}/slip", name="pharmacy_dispense_slip")
def get_dispense_slip(
    request: Request,
    dispense_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Generate dispense slip for printing."""
    from app.models.patient_models import Patient
    from sqlalchemy.orm import joinedload
    
    dispense = db.query(PharmacyDispense).options(
        joinedload(PharmacyDispense.patient),
        joinedload(PharmacyDispense.items).joinedload(PharmacyDispenseItem.drug).joinedload(PharmacyDrug.dosage_form),
        joinedload(PharmacyDispense.items).joinedload(PharmacyDispenseItem.allocations).joinedload(PharmacyDispenseAllocation.batch),
    ).filter(PharmacyDispense.id == dispense_id).first()
    
    if not dispense:
        raise HTTPException(404, "Dispense not found")
    
    context = {
        "request": request,
        "title": f"Dispense Slip #{dispense.id}",
        "dispense": dispense,
        "patient": dispense.patient,
    }
    return templates.TemplateResponse("pharmacy_ghana/dispense_slip.html", context)


# ========================================================
# BATCH ACTIONS API
# ========================================================

@router.put("/stores/{store_id}/batches/{batch_id}", name="pharmacy_batch_update")
def update_batch(
    store_id: UUID,
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    batch_no: Optional[str] = Form(None),
    expiry_date: Optional[date] = Form(None),
    unit_cost: Optional[float] = Form(None),
    selling_price: Optional[float] = Form(None),
    qty_on_hand: Optional[float] = Form(None),
    supplier_id: Optional[str] = Form(None),
    invoice_ref: Optional[str] = Form(None),
):
    """Update batch details."""
    batch = db.query(PharmacyBatch).filter(
        PharmacyBatch.id == batch_id,
        PharmacyBatch.store_id == store_id
    ).first()
    
    if not batch:
        raise HTTPException(404, "Batch not found")
    
    if batch_no is not None:
        batch.batch_no = batch_no
    if expiry_date is not None:
        batch.expiry_date = expiry_date
    if unit_cost is not None:
        batch.unit_cost = Decimal(str(unit_cost))
    if selling_price is not None:
        batch.selling_price = Decimal(str(selling_price))
    if qty_on_hand is not None:
        batch.qty_on_hand = Decimal(str(qty_on_hand))
    if invoice_ref is not None:
        batch.invoice_ref = invoice_ref
    if supplier_id is not None:
        try:
            batch.supplier_id = UUID(supplier_id)
        except ValueError:
            pass
    
    # Update audit fields
    batch.updated_at = datetime.now()
    batch.updated_by_id = current_user.id
    
    db.commit()
    db.refresh(batch)
    
    return {"success": True, "message": "Batch updated successfully", "batch_id": str(batch.id)}


@router.post("/stores/{store_id}/batches/{batch_id}/status", name="pharmacy_batch_update_status")
def update_batch_status(
    store_id: UUID,
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    status: str = Form(...),
    notes: Optional[str] = Form(None),
):
    """Update batch status (DAMAGED, RETURNED, QUARANTINE, ACTIVE)."""
    valid_statuses = ["ACTIVE", "DAMAGED", "RETURNED", "QUARANTINE", "EXPIRED", "DEPLETED"]
    if status.upper() not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    batch = db.query(PharmacyBatch).filter(
        PharmacyBatch.id == batch_id,
        PharmacyBatch.store_id == store_id
    ).first()
    
    if not batch:
        raise HTTPException(404, "Batch not found")
    
    old_status = batch.status
    batch.status = status.upper()
    batch.updated_at = datetime.now()
    batch.updated_by_id = current_user.id
    
    # Create stock ledger entry for status change
    ledger = PharmacyStockLedger(
        store_id=store_id,
        drug_id=batch.drug_id,
        batch_id=batch_id,
        movement_type=f"STATUS_{status.upper()}",
        qty_in=0,
        qty_out=0,
        note=f"Status changed from {old_status} to {status.upper()}. Notes: {notes or 'N/A'}",
        created_by_id=current_user.id,
    )
    db.add(ledger)
    db.commit()
    
    return {"success": True, "message": f"Batch status updated to {status}", "batch_id": str(batch.id)}


@router.post("/stores/{store_id}/batches/bulk-status", name="pharmacy_batch_bulk_update_status")
def update_batches_status_bulk(
    store_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    batch_ids: List[str] = Form(...),
    status: str = Form(...),
    notes: Optional[str] = Form(None),
):
    """Update status for multiple batches at once."""
    valid_statuses = ["ACTIVE", "DAMAGED", "RETURNED", "QUARANTINE", "EXPIRED", "DEPLETED"]
    if status.upper() not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    if not batch_ids:
        raise HTTPException(400, "No batch IDs provided")
    
    updated_count = 0
    errors = []
    
    for batch_id_str in batch_ids:
        try:
            batch_id = UUID(batch_id_str)
        except ValueError:
            errors.append(f"Invalid batch ID: {batch_id_str}")
            continue
        
        batch = db.query(PharmacyBatch).filter(
            PharmacyBatch.id == batch_id,
            PharmacyBatch.store_id == store_id
        ).first()
        
        if not batch:
            errors.append(f"Batch not found: {batch_id_str}")
            continue
        
        old_status = batch.status
        batch.status = status.upper()
        batch.updated_at = datetime.now()
        batch.updated_by_id = current_user.id
        
        # Create stock ledger entry for status change
        ledger = PharmacyStockLedger(
            store_id=store_id,
            drug_id=batch.drug_id,
            batch_id=batch_id,
            movement_type=f"STATUS_{status.upper()}",
            qty_in=0,
            qty_out=0,
            note=f"Bulk status change from {old_status} to {status.upper()}. Notes: {notes or 'N/A'}",
            created_by_id=current_user.id,
        )
        db.add(ledger)
        updated_count += 1
    
    db.commit()
    
    return {
        "success": True, 
        "message": f"Updated {updated_count} batch(es) to {status}",
        "updated_count": updated_count,
        "errors": errors if errors else None
    }


@router.post("/stores/{store_id}/batches/{batch_id}/transfer", name="pharmacy_batch_transfer")
def transfer_batch(
    store_id: UUID,
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    target_store_id: str = Form(...),
    transfer_qty: float = Form(...),
    notes: Optional[str] = Form(None),
):
    """Transfer batch quantity to another store."""
    batch = db.query(PharmacyBatch).filter(
        PharmacyBatch.id == batch_id,
        PharmacyBatch.store_id == store_id
    ).first()
    
    if not batch:
        raise HTTPException(404, "Source batch not found")
    
    if transfer_qty > float(batch.qty_on_hand):
        raise HTTPException(400, "Transfer quantity exceeds available quantity")
    
    try:
        target_uuid = UUID(target_store_id)
    except ValueError:
        raise HTTPException(400, "Invalid target store ID")
    
    target_store = db.query(PharmacyStore).filter(PharmacyStore.id == target_uuid).first()
    if not target_store:
        raise HTTPException(404, "Target store not found")
    
    # Create ledger entry for source batch
    ledger_out = PharmacyStockLedger(
        store_id=store_id,
        drug_id=batch.drug_id,
        batch_id=batch_id,
        movement_type="TRANSFER_OUT",
        qty_in=0,
        qty_out=transfer_qty,
        reference_type="Store",
        reference_id=target_uuid,
        note=f"Transferred to {target_store.name}. Notes: {notes or 'N/A'}",
        created_by_id=current_user.id,
    )
    db.add(ledger_out)
    
    # Deduct from source batch
    batch.qty_on_hand -= Decimal(str(transfer_qty))
    batch.updated_at = datetime.now()
    batch.updated_by_id = current_user.id
    
    # Check if target batch exists
    target_batch = db.query(PharmacyBatch).filter(
        PharmacyBatch.drug_id == batch.drug_id,
        PharmacyBatch.store_id == target_uuid,
        PharmacyBatch.batch_no == batch.batch_no,
        PharmacyBatch.expiry_date == batch.expiry_date,
    ).first()
    
    if target_batch:
        # Add to existing batch
        target_batch.qty_on_hand += Decimal(str(transfer_qty))
        target_batch.updated_at = datetime.now()
        target_batch.updated_by_id = current_user.id
        new_batch_id = target_batch.id
    else:
        # Create new batch in target store
        new_batch = PharmacyBatch(
            drug_id=batch.drug_id,
            store_id=target_uuid,
            batch_no=batch.batch_no,
            expiry_date=batch.expiry_date,
            unit_cost=batch.unit_cost,
            selling_price=batch.selling_price,
            qty_on_hand=transfer_qty,
            supplier_id=batch.supplier_id,
            status="ACTIVE",
        )
        db.add(new_batch)
        db.flush()
        new_batch_id = new_batch.id
    
    # Create ledger entry for target batch
    ledger_in = PharmacyStockLedger(
        store_id=target_uuid,
        drug_id=batch.drug_id,
        batch_id=new_batch_id,
        movement_type="TRANSFER_IN",
        qty_in=transfer_qty,
        qty_out=0,
        reference_type="Store",
        reference_id=store_id,
        note=f"Received from {store_id}. Notes: {notes or 'N/A'}",
        created_by_id=current_user.id,
    )
    db.add(ledger_in)
    
    db.commit()
    
    return {"success": True, "message": f"Transferred {transfer_qty} units to {target_store.name}"}


@router.get("/stores/{store_id}/batches/{batch_id}/label", name="pharmacy_batch_label")
def print_batch_label(
    store_id: UUID,
    batch_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
):
    """Generate batch label for printing."""
    batch = db.query(PharmacyBatch).options(
        joinedload(PharmacyBatch.drug),
        joinedload(PharmacyBatch.store),
        joinedload(PharmacyBatch.supplier),
    ).filter(
        PharmacyBatch.id == batch_id,
        PharmacyBatch.store_id == store_id
    ).first()
    
    if not batch:
        raise HTTPException(404, "Batch not found")
    
    context = {
        "request": request,
        "title": f"Batch Label - {batch.batch_no}",
        "batch": batch,
        "drug": batch.drug,
        "store": batch.store,
        "now": datetime.now(),
        "today": date.today(),
        "timedelta": timedelta,
    }
    return templates.TemplateResponse("pharmacy_ghana/batch_label.html", context)


@router.get("/stores/{store_id}/batches", name="pharmacy_batches_list_paginated")
def list_batches_paginated(
    store_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin", "Pharmacy Staff"])),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    drug_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """List batches with pagination and filters."""
    q = db.query(PharmacyBatch).options(
        joinedload(PharmacyBatch.drug),
        joinedload(PharmacyBatch.supplier),
    ).filter(PharmacyBatch.store_id == store_id)
    
    if drug_id:
        try:
            q = q.filter(PharmacyBatch.drug_id == UUID(drug_id))
        except ValueError:
            pass
    
    if status:
        q = q.filter(PharmacyBatch.status == status.upper())
    
    if search:
        s = f"%{search}%"
        q = q.filter(
            or_(
                PharmacyBatch.batch_no.ilike(s),
                PharmacyBatch.drug.has(PharmacyDrug.generic_name.ilike(s)),
            )
        )
    
    total = q.count()
    batches = q.order_by(PharmacyBatch.expiry_date).offset((page - 1) * limit).limit(limit).all()
    
    out = []
    for b in batches:
        out.append({
            "id": str(b.id),
            "batch_no": b.batch_no,
            "expiry_date": str(b.expiry_date) if b.expiry_date else None,
            "qty_on_hand": float(b.qty_on_hand) if b.qty_on_hand else 0,
            "unit_cost": float(b.unit_cost) if b.unit_cost else None,
            "selling_price": float(b.selling_price) if b.selling_price else None,
            "status": b.status,
            "drug": {
                "id": str(b.drug.id),
                "generic_name": b.drug.generic_name,
                "brand_name": b.drug.brand_name,
            } if b.drug else None,
            "updated_at": b.updated_at.isoformat() if b.updated_at else None,
            "updated_by": b.updated_by.username if b.updated_by else None,
        })
    
    return {"total": total, "page": page, "limit": limit, "batches": out}

