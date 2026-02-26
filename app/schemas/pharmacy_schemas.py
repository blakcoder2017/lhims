"""
Pharmacy Ghana-Ready Schemas
- Request/Response schemas for API endpoints
"""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, Field


# --- Dosage Forms ---
class DosageFormBase(BaseModel):
    name: str = Field(..., max_length=100)


class DosageFormCreate(DosageFormBase):
    pass


class DosageFormResponse(DosageFormBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# --- Suppliers ---
class SupplierBase(BaseModel):
    name: str = Field(..., max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(SupplierBase):
    pass


class SupplierResponse(SupplierBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# --- Stores ---
class StoreBase(BaseModel):
    name: str = Field(..., max_length=255)
    facility_id: Optional[int] = None


class StoreCreate(StoreBase):
    pass


class StoreUpdate(StoreBase):
    pass


class StoreResponse(StoreBase):
    id: UUID
    created_at: datetime
    # Computed fields for UI
    batches_count: Optional[int] = None
    total_stock_value: Optional[float] = None

    class Config:
        from_attributes = True


# --- Drugs/Formulations ---
class DrugBase(BaseModel):
    item_code: str = Field(..., max_length=50)
    generic_name: str = Field(..., max_length=255)
    brand_name: Optional[str] = Field(None, max_length=255)
    dosage_form_id: UUID
    strength_value: Optional[Decimal] = Field(None, decimal_places=6)
    strength_unit: Optional[str] = Field(None, max_length=50)
    route: Optional[str] = Field(None, max_length=50)
    concentration_value: Optional[Decimal] = Field(None, decimal_places=6)
    concentration_unit: Optional[str] = Field(None, max_length=100)
    pack_size: Optional[int] = None
    reorder_level: Optional[Decimal] = Field(None, decimal_places=6)
    reorder_qty: Optional[Decimal] = Field(None, decimal_places=6)
    is_controlled: bool = False
    is_active: bool = True
    notes: Optional[str] = None


class DrugCreate(DrugBase):
    pass


class DrugUpdate(BaseModel):
    """Schema for updating a drug - all fields optional for partial updates"""
    item_code: Optional[str] = Field(None, max_length=50)
    generic_name: Optional[str] = Field(None, max_length=255)
    brand_name: Optional[str] = Field(None, max_length=255)
    dosage_form_id: Optional[UUID] = None
    strength_value: Optional[Decimal] = Field(None, decimal_places=6)
    strength_unit: Optional[str] = Field(None, max_length=50)
    route: Optional[str] = Field(None, max_length=50)
    concentration_value: Optional[Decimal] = Field(None, decimal_places=6)
    concentration_unit: Optional[str] = Field(None, max_length=100)
    pack_size: Optional[int] = None
    reorder_level: Optional[Decimal] = Field(None, decimal_places=6)
    reorder_qty: Optional[Decimal] = Field(None, decimal_places=6)
    is_controlled: Optional[bool] = False
    is_active: Optional[bool] = True
    notes: Optional[str] = None


class DrugResponse(DrugBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Computed
    dosage_form_name: Optional[str] = None
    total_stock: Optional[float] = None
    available_batches: Optional[int] = None

    class Config:
        from_attributes = True


class DrugListItem(BaseModel):
    """Simplified drug for list views"""
    id: UUID
    item_code: str
    generic_name: str
    brand_name: Optional[str]
    dosage_form_name: str
    strength_value: Optional[float]
    strength_unit: Optional[str]
    route: Optional[str]
    is_controlled: bool
    is_active: bool
    total_stock: Optional[float] = 0

    class Config:
        from_attributes = True


# --- Batches ---
class BatchBase(BaseModel):
    drug_id: UUID
    store_id: UUID
    batch_no: str = Field(..., max_length=100)
    expiry_date: date
    received_date: Optional[date] = None
    unit_cost: Optional[Decimal] = Field(None, decimal_places=6)
    selling_price: Optional[Decimal] = Field(None, decimal_places=6)
    qty_on_hand: Decimal = Field(0, decimal_places=6)
    qty_reserved: Decimal = Field(0, decimal_places=6)
    status: str = "ACTIVE"
    supplier_id: Optional[UUID] = None
    invoice_ref: Optional[str] = Field(None, max_length=255)


class BatchCreate(BatchBase):
    qty: Optional[Decimal] = None  # For stock-in convenience


class BatchUpdate(BaseModel):
    unit_cost: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    status: Optional[str] = None


class BatchResponse(BatchBase):
    id: UUID
    created_at: datetime
    # Computed
    drug_name: Optional[str] = None
    store_name: Optional[str] = None
    supplier_name: Optional[str] = None
    is_near_expiry: Optional[bool] = False
    days_to_expiry: Optional[int] = None

    class Config:
        from_attributes = True


class BatchListItem(BaseModel):
    """Simplified batch for list views"""
    id: UUID
    batch_no: str
    expiry_date: date
    qty_on_hand: float
    status: str
    drug_name: str
    store_name: str
    is_near_expiry: bool = False

    class Config:
        from_attributes = True


# --- Stock Ledger ---
class StockLedgerBase(BaseModel):
    store_id: UUID
    drug_id: UUID
    batch_id: Optional[UUID] = None
    movement_type: str
    qty_in: Decimal = 0
    qty_out: Decimal = 0
    unit_cost_snapshot: Optional[Decimal] = None
    selling_price_snapshot: Optional[Decimal] = None
    reference_type: Optional[str] = None
    reference_id: Optional[UUID] = None
    note: Optional[str] = None


class StockLedgerResponse(StockLedgerBase):
    id: UUID
    created_by_id: Optional[int] = None
    created_at: datetime
    # Computed
    drug_name: Optional[str] = None
    batch_no: Optional[str] = None
    store_name: Optional[str] = None

    class Config:
        from_attributes = True


# --- Dispense ---
class DispenseItemBase(BaseModel):
    drug_id: UUID
    dosage_instructions: Optional[str] = None
    qty_prescribed: Optional[Decimal] = None
    qty_dispensed: Decimal
    unit_selling_price: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None


class DispenseItemCreate(DispenseItemBase):
    pass


class DispenseItemResponse(DispenseItemBase):
    id: UUID
    created_at: datetime
    # Computed
    drug_name: Optional[str] = None
    allocations: Optional[List] = None

    class Config:
        from_attributes = True


class DispenseBase(BaseModel):
    patient_id: int
    encounter_id: Optional[int] = None
    prescriber_id: Optional[int] = None
    payment_type: Optional[str] = None
    notes: Optional[str] = None


class DispenseCreate(DispenseBase):
    items: List[DispenseItemCreate] = []


class DispenseUpdate(BaseModel):
    status: Optional[str] = None
    payment_type: Optional[str] = None
    notes: Optional[str] = None


class DispenseResponse(DispenseBase):
    id: UUID
    status: str
    dispensed_by_id: Optional[int] = None
    dispensed_at: Optional[datetime] = None
    created_at: datetime
    # Computed
    patient_name: Optional[str] = None
    items: List[DispenseItemResponse] = []
    total_amount: Optional[float] = None

    class Config:
        from_attributes = True


class DispenseListItem(BaseModel):
    """Simplified dispense for list views"""
    id: UUID
    patient_id: int
    patient_name: Optional[str] = None
    status: str
    payment_type: Optional[str]
    dispensed_at: Optional[datetime]
    created_at: datetime
    items_count: int = 0
    total_amount: Optional[float] = 0

    class Config:
        from_attributes = True


# --- Dispense Allocation ---
class AllocationResponse(BaseModel):
    id: UUID
    batch_id: UUID
    batch_no: Optional[str] = None
    expiry_date: Optional[date] = None
    qty_allocated: float

    class Config:
        from_attributes = True


# --- Stock Adjustment ---
class StockAdjustmentBase(BaseModel):
    drug_id: UUID
    store_id: UUID
    adjustment_type: str  # ADD, REMOVE, WRITE_OFF
    quantity: Decimal
    reason: str
    batch_no: Optional[str] = None
    expiry_date: Optional[date] = None


class StockAdjustmentCreate(StockAdjustmentBase):
    unit_cost: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None


class StockAdjustmentResponse(StockAdjustmentBase):
    id: UUID
    created_by_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Store Transfer ---
class TransferBase(BaseModel):
    from_store_id: UUID
    to_store_id: UUID
    drug_id: UUID
    quantity: Decimal
    batch_no: Optional[str] = None


class TransferCreate(TransferBase):
    pass


class TransferResponse(TransferBase):
    id: UUID
    created_by_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Drug Interaction ---
class InteractionBase(BaseModel):
    drug_a_id: UUID
    drug_b_id: UUID
    severity: str  # MINOR, MODERATE, MAJOR, CONTRAINDICATED
    description: Optional[str] = None
    recommendation: Optional[str] = None
    reference: Optional[str] = None
    is_active: bool = True


class InteractionCreate(InteractionBase):
    pass


class InteractionUpdate(InteractionBase):
    pass


class InteractionResponse(InteractionBase):
    id: UUID
    created_at: datetime
    drug_a_name: Optional[str] = None
    drug_b_name: Optional[str] = None

    class Config:
        from_attributes = True


# --- Role Policy ---
class RolePolicyBase(BaseModel):
    role_name: str = Field(..., max_length=100)
    can_view_unit_cost: bool = False
    can_view_margin: bool = False
    can_edit_selling_price: bool = False
    can_adjust_stock: bool = False
    can_approve_adjustment: bool = False
    can_dispense_controlled: bool = False


class RolePolicyCreate(RolePolicyBase):
    pass


class RolePolicyUpdate(RolePolicyBase):
    pass


class RolePolicyResponse(RolePolicyBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# --- Reports ---
class NearExpiryReportItem(BaseModel):
    batch_id: UUID
    drug_name: str
    batch_no: str
    expiry_date: date
    qty_on_hand: float
    days_to_expiry: int
    store_name: str

    class Config:
        from_attributes = True


class StockLedgerReportItem(BaseModel):
    date: datetime
    drug_name: str
    batch_no: Optional[str]
    movement_type: str
    qty_in: float
    qty_out: float
    balance: float
    reference: Optional[str]
    note: Optional[str]

    class Config:
        from_attributes = True


class ControlledRegisterItem(BaseModel):
    date: date
    patient_id: int
    patient_name: str
    drug_name: str
    qty_dispensed: float
    dispensed_by: Optional[str]
    prescriber: Optional[str]

    class Config:
        from_attributes = True


# --- Formulary Search Result ---
class FormularySearchResult(BaseModel):
    id: UUID
    item_code: str
    label: str  # Display string: "Amoxicillin 500mg Capsule (PO)"
    generic_name: str
    brand_name: Optional[str]
    dosage_form: str
    strength_value: Optional[float]
    strength_unit: Optional[str]
    route: Optional[str]
    concentration_value: Optional[float]
    concentration_unit: Optional[str]
    pack_size: Optional[int]
    is_controlled: bool
    # Stock info (optional)
    total_stock: Optional[float] = None
    available_stores: Optional[List[str]] = None

    class Config:
        from_attributes = True


# --- Interaction Check Result ---
class InteractionCheckResult(BaseModel):
    has_interactions: bool
    interactions: List[dict]
    # Blocked if contraindicated
    blocked: bool = False

    class Config:
        from_attributes = True


# --- Prescription for Dispensing ---
class PrescriptionForDispense(BaseModel):
    prescription_id: int
    drug_id: UUID
    drug_name: str
    dosage: str
    frequency: str
    duration: str
    quantity: Optional[int] = None
    status: str
    prescribed_by: str

    class Config:
        from_attributes = True
