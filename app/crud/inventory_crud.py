from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

from app.models.inventory_models import (
    Medication, StockItem, InventoryTransaction, FormularyRule, DrugInteraction,
    StockStatus, TransactionType
)
from app.schemas.inventory_schemas import (
    MedicationCreate, MedicationUpdate,
    StockItemCreate, StockItemUpdate,
    InventoryTransactionCreate,
    FormularyRuleCreate, FormularyRuleUpdate,
    DrugInteractionCreate, DrugInteractionUpdate,
    StockCheckResponse, DrugInteractionCheckResponse, FormularyCheckResponse
)


# Medication CRUD
def create_medication(db: Session, medication: MedicationCreate) -> Medication:
    """Create a new medication"""
    db_medication = Medication(**medication.dict())
    db.add(db_medication)
    db.commit()
    db.refresh(db_medication)
    return db_medication


def get_medication(db: Session, medication_id: int) -> Optional[Medication]:
    """Get a medication by ID"""
    return db.query(Medication).filter(
        Medication.id == medication_id,
        Medication.is_active == True
    ).first()


def get_medication_by_code(db: Session, medication_code: str) -> Optional[Medication]:
    """Get a medication by code"""
    return db.query(Medication).filter(
        Medication.medication_code == medication_code,
        Medication.is_active == True
    ).first()


def get_medications(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None) -> List[Medication]:
    """Get all medications with optional search"""
    query = db.query(Medication).filter(Medication.is_active == True)
    
    if search:
        query = query.filter(
            or_(
                Medication.name.ilike(f"%{search}%"),
                Medication.generic_name.ilike(f"%{search}%"),
                Medication.brand_name.ilike(f"%{search}%"),
                Medication.medication_code.ilike(f"%{search}%")
            )
        )
    
    return query.order_by(Medication.name).offset(skip).limit(limit).all()


def update_medication(db: Session, medication_id: int, medication_update: MedicationUpdate) -> Optional[Medication]:
    """Update a medication"""
    db_medication = db.query(Medication).filter(Medication.id == medication_id).first()
    if not db_medication:
        return None
    
    update_data = medication_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_medication, field, value)
    
    db.commit()
    db.refresh(db_medication)
    return db_medication


def delete_medication(db: Session, medication_id: int) -> bool:
    """Soft delete a medication"""
    db_medication = db.query(Medication).filter(Medication.id == medication_id).first()
    if not db_medication:
        return False
    
    db_medication.is_active = False
    db.commit()
    return True


# Stock Item CRUD
def create_stock_item(db: Session, stock_item: StockItemCreate) -> StockItem:
    """Create a new stock item"""
    stock_dict = stock_item.dict()
    # Ensure reserved_quantity is set (default to 0 if not provided)
    if 'reserved_quantity' not in stock_dict or stock_dict.get('reserved_quantity') is None:
        stock_dict['reserved_quantity'] = 0
    
    db_stock_item = StockItem(**stock_dict)
    # Calculate available quantity
    db_stock_item.available_quantity = db_stock_item.quantity - db_stock_item.reserved_quantity
    
    # Update status based on quantity and expiry
    _update_stock_status(db_stock_item)
    
    db.add(db_stock_item)
    db.commit()
    db.refresh(db_stock_item)
    return db_stock_item


def _update_stock_status(stock_item: StockItem):
    """Update stock status based on quantity and expiry"""
    if stock_item.expiry_date and stock_item.expiry_date < datetime.now():
        stock_item.status = StockStatus.EXPIRED.value
    elif stock_item.available_quantity <= 0:
        stock_item.status = StockStatus.OUT_OF_STOCK.value
    elif stock_item.medication and stock_item.medication.reorder_level:
        if stock_item.available_quantity <= stock_item.medication.reorder_level:
            stock_item.status = StockStatus.LOW_STOCK.value
        else:
            stock_item.status = StockStatus.IN_STOCK.value
    else:
        stock_item.status = StockStatus.IN_STOCK.value


def get_stock_item(db: Session, stock_item_id: int) -> Optional[StockItem]:
    """Get a stock item by ID"""
    return db.query(StockItem).options(
        joinedload(StockItem.medication)
    ).filter(
        StockItem.id == stock_item_id,
        StockItem.is_active == True
    ).first()


def get_stock_items_by_medication(db: Session, medication_id: int) -> List[StockItem]:
    """Get all stock items for a medication"""
    return db.query(StockItem).options(
        joinedload(StockItem.medication)
    ).filter(
        StockItem.medication_id == medication_id,
        StockItem.is_active == True
    ).order_by(StockItem.expiry_date.asc() if StockItem.expiry_date else StockItem.created_at.desc()).all()


def get_low_stock_items(db: Session) -> List[StockItem]:
    """Get all low stock items"""
    return db.query(StockItem).options(
        joinedload(StockItem.medication)
    ).filter(
        and_(
            StockItem.is_active == True,
            StockItem.status == StockStatus.LOW_STOCK.value
        )
    ).all()


def get_expired_stock_items(db: Session) -> List[StockItem]:
    """Get all expired stock items"""
    return db.query(StockItem).options(
        joinedload(StockItem.medication)
    ).filter(
        and_(
            StockItem.is_active == True,
            StockItem.status == StockStatus.EXPIRED.value
        )
    ).all()


def update_stock_item(db: Session, stock_item_id: int, stock_item_update: StockItemUpdate) -> Optional[StockItem]:
    """Update a stock item"""
    db_stock_item = db.query(StockItem).filter(StockItem.id == stock_item_id).first()
    if not db_stock_item:
        return None
    
    update_data = stock_item_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_stock_item, field, value)
    
    # Ensure reserved_quantity is not None (default to 0)
    if db_stock_item.reserved_quantity is None:
        db_stock_item.reserved_quantity = 0
    
    # Recalculate available quantity
    db_stock_item.available_quantity = db_stock_item.quantity - db_stock_item.reserved_quantity
    _update_stock_status(db_stock_item)
    
    db.commit()
    db.refresh(db_stock_item)
    return db_stock_item


def check_stock_availability(db: Session, medication_id: int, required_quantity: int) -> StockCheckResponse:
    """Check if medication is available in required quantity"""
    medication = get_medication(db, medication_id)
    if not medication:
        raise ValueError("Medication not found")
    
    stock_items = get_stock_items_by_medication(db, medication_id)
    
    total_quantity = sum([item.quantity for item in stock_items])
    total_available = sum([item.available_quantity for item in stock_items])
    total_reserved = sum([item.reserved_quantity for item in stock_items])
    
    # Filter out expired items
    valid_stock_items = [item for item in stock_items if item.status != StockStatus.EXPIRED.value]
    valid_available = sum([item.available_quantity for item in valid_stock_items])
    
    is_available = valid_available >= required_quantity
    low_stock = medication.reorder_level and valid_available <= medication.reorder_level
    out_of_stock = valid_available == 0
    
    return StockCheckResponse(
        medication_id=medication_id,
        medication_name=medication.name,
        available_quantity=valid_available,
        total_quantity=total_quantity,
        reserved_quantity=total_reserved,
        is_available=is_available,
        stock_items=valid_stock_items,
        low_stock=low_stock,
        out_of_stock=out_of_stock
    )


def reserve_stock(db: Session, stock_item_id: int, quantity: int) -> bool:
    """Reserve stock for a prescription"""
    db_stock_item = db.query(StockItem).filter(StockItem.id == stock_item_id).first()
    if not db_stock_item:
        return False
    
    if db_stock_item.available_quantity < quantity:
        return False
    
    db_stock_item.reserved_quantity += quantity
    db_stock_item.available_quantity = db_stock_item.quantity - db_stock_item.reserved_quantity
    _update_stock_status(db_stock_item)
    
    db.commit()
    return True


def release_stock_reservation(db: Session, stock_item_id: int, quantity: int) -> bool:
    """Release reserved stock"""
    db_stock_item = db.query(StockItem).filter(StockItem.id == stock_item_id).first()
    if not db_stock_item:
        return False
    
    db_stock_item.reserved_quantity = max(0, db_stock_item.reserved_quantity - quantity)
    db_stock_item.available_quantity = db_stock_item.quantity - db_stock_item.reserved_quantity
    _update_stock_status(db_stock_item)
    
    db.commit()
    return True


# Inventory Transaction CRUD
def create_inventory_transaction(db: Session, transaction: InventoryTransactionCreate, performed_by_id: int) -> InventoryTransaction:
    """Create an inventory transaction"""
    db_transaction = InventoryTransaction(
        **transaction.dict(),
        performed_by_id=performed_by_id
    )
    
    # Calculate total cost
    if db_transaction.unit_cost:
        db_transaction.total_cost = db_transaction.unit_cost * abs(db_transaction.quantity)
    
    db.add(db_transaction)
    
    # Update stock item if specified
    if db_transaction.stock_item_id:
        db_stock_item = db.query(StockItem).filter(StockItem.id == db_transaction.stock_item_id).first()
        if db_stock_item:
            if db_transaction.transaction_type in [TransactionType.PURCHASE.value, TransactionType.RETURN.value, TransactionType.ADJUSTMENT.value]:
                # Increase quantity
                db_stock_item.quantity += abs(db_transaction.quantity)
            elif db_transaction.transaction_type in [TransactionType.SALE.value, TransactionType.EXPIRY.value, TransactionType.DAMAGE.value]:
                # Decrease quantity
                db_stock_item.quantity = max(0, db_stock_item.quantity - abs(db_transaction.quantity))
            
            db_stock_item.available_quantity = db_stock_item.quantity - db_stock_item.reserved_quantity
            _update_stock_status(db_stock_item)
    
    db.commit()
    db.refresh(db_transaction)
    return db_transaction


def get_inventory_transactions(db: Session, medication_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[InventoryTransaction]:
    """Get inventory transactions"""
    query = db.query(InventoryTransaction).options(
        joinedload(InventoryTransaction.medication),
        joinedload(InventoryTransaction.performed_by)
    )
    
    if medication_id:
        query = query.filter(InventoryTransaction.medication_id == medication_id)
    
    return query.order_by(InventoryTransaction.transaction_date.desc()).offset(skip).limit(limit).all()


# Formulary Rule CRUD
def create_formulary_rule(db: Session, rule: FormularyRuleCreate) -> FormularyRule:
    """Create a formulary rule"""
    db_rule = FormularyRule(**rule.dict())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule


def get_formulary_rules(db: Session, medication_id: Optional[int] = None) -> List[FormularyRule]:
    """Get formulary rules"""
    query = db.query(FormularyRule).filter(FormularyRule.is_active == True)
    
    if medication_id:
        query = query.filter(
            or_(
                FormularyRule.medication_id == medication_id,
                FormularyRule.medication_id.is_(None)
            )
        )
    
    return query.all()


def check_formulary_compliance(db: Session, medication_id: int, patient_nhis_number: Optional[str] = None) -> FormularyCheckResponse:
    """Check formulary compliance for a medication"""
    medication = get_medication(db, medication_id)
    if not medication:
        raise ValueError("Medication not found")
    
    rules = get_formulary_rules(db, medication_id)
    warnings = []
    
    # Check NHIS coverage
    if patient_nhis_number and not medication.is_nhis_covered:
        warnings.append("Medication is not covered by NHIS")
    
    # Check if in formulary
    if not medication.is_formulary:
        warnings.append("Medication is not in the formulary")
    
    compliance_status = "compliant"
    if warnings:
        compliance_status = "non_compliant"
    elif not medication.is_formulary:
        compliance_status = "warning"
    
    return FormularyCheckResponse(
        medication_id=medication_id,
        medication_name=medication.name,
        is_formulary=medication.is_formulary,
        is_nhis_covered=medication.is_nhis_covered,
        compliance_status=compliance_status,
        rules=rules,
        warnings=warnings
    )


# Drug Interaction CRUD
def create_drug_interaction(db: Session, interaction: DrugInteractionCreate) -> DrugInteraction:
    """Create a drug interaction"""
    db_interaction = DrugInteraction(**interaction.dict())
    db.add(db_interaction)
    db.commit()
    db.refresh(db_interaction)
    return db_interaction


def check_drug_interactions(db: Session, medication_ids: List[int]) -> DrugInteractionCheckResponse:
    """Check for drug interactions between medications"""
    if len(medication_ids) < 2:
        return DrugInteractionCheckResponse(has_interactions=False, interactions=[])
    
    # Find all interactions between the medications
    interactions = db.query(DrugInteraction).filter(
        or_(
            and_(
                DrugInteraction.medication1_id.in_(medication_ids),
                DrugInteraction.medication2_id.in_(medication_ids)
            )
        )
    ).all()
    
    # Filter to only include interactions between the provided medications
    relevant_interactions = []
    for interaction in interactions:
        if interaction.medication1_id in medication_ids and interaction.medication2_id in medication_ids:
            relevant_interactions.append(interaction)
    
    return DrugInteractionCheckResponse(
        has_interactions=len(relevant_interactions) > 0,
        interactions=relevant_interactions
    )


def get_drug_interactions_by_medication(db: Session, medication_id: int) -> List[DrugInteraction]:
    """Get all drug interactions for a medication"""
    return db.query(DrugInteraction).filter(
        or_(
            DrugInteraction.medication1_id == medication_id,
            DrugInteraction.medication2_id == medication_id
        )
    ).all()

