"""
Pharmacy FEFO (First Expiry First Out) allocation and ledger.
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.pharmacy_models import (
    PharmacyBatch, PharmacyStockLedger, PharmacyDrug, PharmacyStore,
    PharmacyDispenseItem, PharmacyDispenseAllocation
)


def get_available_batches_fefo(
    db: Session,
    store_id,
    drug_id,
    qty_needed: Decimal,
    exclude_expired: bool = True,
    near_expiry_days: int = 90,
) -> List[Tuple[PharmacyBatch, Decimal]]:
    """
    Get batches sorted by FEFO (expiry ASC, received_date ASC).
    Returns list of (batch, qty_to_take) until qty_needed is fulfilled.
    Excludes expired; optionally warns on near-expiry.
    """
    today = date.today()
    q = db.query(PharmacyBatch).filter(
        PharmacyBatch.store_id == store_id,
        PharmacyBatch.drug_id == drug_id,
        PharmacyBatch.status == "ACTIVE",
        PharmacyBatch.qty_on_hand > 0,
    )
    if exclude_expired:
        q = q.filter(PharmacyBatch.expiry_date >= today)
    batches = q.order_by(PharmacyBatch.expiry_date.asc()).all()
    result = []
    remaining = Decimal(str(qty_needed))
    for b in batches:
        if remaining <= 0:
            break
        avail = b.qty_on_hand - b.qty_reserved
        if avail <= 0:
            continue
        take = min(avail, remaining)
        result.append((b, take))
        remaining -= take
    return result


def allocate_batches_fefo(
    db: Session,
    store_id,
    drug_id,
    qty_needed: Decimal,
) -> dict:
    """
    Reusable FEFO allocation service.
    
    Rules:
    - Only batches where status=ACTIVE, expiry_date >= today, (qty_on_hand - qty_reserved) > 0
    - Sort by expiry_date ASC then received_date ASC
    - Allocate quantities until qty_needed met
    - If insufficient -> return error with shortage amount
    - Never allocate expired batches
    
    Returns:
    {
        "success": True/False,
        "allocations": [{batch_id, qty_allocated, expiry_date, batch_no}],
        "error": None or "Insufficient stock: need X, available Y"
    }
    """
    from datetime import date
    today = date.today()
    
    # Query available batches (ACTIVE, not expired, has stock)
    batches = db.query(PharmacyBatch).filter(
        PharmacyBatch.store_id == store_id,
        PharmacyBatch.drug_id == drug_id,
        PharmacyBatch.status == "ACTIVE",
        PharmacyBatch.expiry_date >= today,  # Never allocate expired
    ).order_by(
        PharmacyBatch.expiry_date.asc(),
        PharmacyBatch.received_date.asc(),
    ).all()
    
    # Calculate total available
    total_available = Decimal("0")
    eligible_batches = []
    for b in batches:
        available = b.qty_on_hand - b.qty_reserved
        if available > 0:
            eligible_batches.append(b)
            total_available += available
    
    # Check if sufficient
    if total_available < qty_needed:
        return {
            "success": False,
            "allocations": [],
            "error": f"Insufficient stock: need {qty_needed}, available {total_available}"
        }
    
    # Allocate from earliest expiry first
    allocations = []
    remaining = Decimal(str(qty_needed))
    
    for batch in eligible_batches:
        if remaining <= 0:
            break
        available = batch.qty_on_hand - batch.qty_reserved
        qty_to_allocate = min(available, remaining)
        
        allocations.append({
            "batch_id": str(batch.id),
            "qty_allocated": float(qty_to_allocate),
            "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None,
            "batch_no": batch.batch_no,
        })
        
        remaining -= qty_to_allocate
    
    return {
        "success": True,
        "allocations": allocations,
        "error": None
    }


def allocate_fefo(
    db: Session,
    dispense_item_id,
    drug_id,
    store_id,
    qty: Decimal,
    unit_selling_price: Optional[Decimal] = None,
    created_by_id: Optional[int] = None,
) -> Tuple[bool, str, List]:
    """
    Allocate qty from batches (FEFO), create PharmacyDispenseAllocation records,
    update batch qty_on_hand, append to ledger.
    Returns (success, error_message, allocations).
    """
    allocations_data = get_available_batches_fefo(db, store_id, drug_id, qty)
    if not allocations_data:
        return False, "Insufficient stock or all batches expired", []
    total_alloc = sum(a[1] for a in allocations_data)
    if total_alloc < qty:
        return False, f"Insufficient stock: need {qty}, available {total_alloc}", []

    from app.models.pharmacy_models import PharmacyDispenseAllocation
    from uuid import uuid4

    created = []
    remaining = qty
    for batch, take in allocations_data:
        if remaining <= 0:
            break
        actual_take = min(take, remaining)
        batch.qty_on_hand = batch.qty_on_hand - actual_take
        db.flush()

        alloc = PharmacyDispenseAllocation(
            dispense_item_id=dispense_item_id,
            batch_id=batch.id,
            qty_allocated=actual_take,
        )
        db.add(alloc)
        db.flush()
        created.append(alloc)

        _append_ledger(
            db,
            store_id=store_id,
            drug_id=drug_id,
            batch_id=batch.id,
            movement_type="DISPENSE",
            qty_out=actual_take,
            unit_cost_snapshot=batch.unit_cost,
            selling_price_snapshot=unit_selling_price or batch.selling_price,
            reference_type="DISPENSE",
            reference_id=dispense_item_id,
            created_by_id=created_by_id,
        )
        remaining -= actual_take
    return True, "", created


def _append_ledger(
    db: Session,
    store_id,
    drug_id,
    batch_id,
    movement_type: str,
    qty_in: Decimal = 0,
    qty_out: Decimal = 0,
    unit_cost_snapshot=None,
    selling_price_snapshot=None,
    reference_type=None,
    reference_id=None,
    note=None,
    created_by_id=None,
):
    from app.models.pharmacy_models import PharmacyStockLedger
    row = PharmacyStockLedger(
        store_id=store_id,
        drug_id=drug_id,
        batch_id=batch_id,
        movement_type=movement_type,
        qty_in=qty_in,
        qty_out=qty_out,
        unit_cost_snapshot=unit_cost_snapshot,
        selling_price_snapshot=selling_price_snapshot,
        reference_type=reference_type,
        reference_id=reference_id,
        note=note,
        created_by_id=created_by_id,
    )
    db.add(row)


def stock_in_create_batch(
    db: Session,
    drug_id,
    store_id,
    batch_no: str,
    expiry_date: date,
    qty: Decimal,
    unit_cost: Optional[Decimal] = None,
    selling_price: Optional[Decimal] = None,
    supplier_id=None,
    invoice_ref=None,
    received_date: Optional[date] = None,
    created_by_id=None,
) -> PharmacyBatch:
    """Create or update batch on stock-in; append ledger."""
    today = date.today() if hasattr(date, 'today') else date.today()
    received = received_date or today
    existing = db.query(PharmacyBatch).filter(
        PharmacyBatch.store_id == store_id,
        PharmacyBatch.drug_id == drug_id,
        PharmacyBatch.batch_no == batch_no,
        PharmacyBatch.expiry_date == expiry_date,
    ).first()
    if existing:
        existing.qty_on_hand = existing.qty_on_hand + qty
        if unit_cost is not None:
            existing.unit_cost = unit_cost
        if selling_price is not None:
            existing.selling_price = selling_price
        batch = existing
    else:
        batch = PharmacyBatch(
            drug_id=drug_id,
            store_id=store_id,
            batch_no=batch_no,
            expiry_date=expiry_date,
            received_date=received,
            unit_cost=unit_cost,
            selling_price=selling_price,
            qty_on_hand=qty,
            qty_reserved=0,
            status="ACTIVE",
            supplier_id=supplier_id,
            invoice_ref=invoice_ref,
        )
        db.add(batch)
        db.flush()
    _append_ledger(
        db,
        store_id=store_id,
        drug_id=drug_id,
        batch_id=batch.id,
        movement_type="STOCK_IN",
        qty_in=qty,
        unit_cost_snapshot=unit_cost,
        selling_price_snapshot=selling_price,
        reference_type="PURCHASE",
        note=invoice_ref or f"Stock-in batch {batch_no}",
        created_by_id=created_by_id,
    )
    return batch
