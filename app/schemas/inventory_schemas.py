from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from app.models.inventory_models import StockStatus, TransactionType


# Medication Schemas
class MedicationBase(BaseModel):
    name: str = Field(..., max_length=255)
    generic_name: Optional[str] = None
    brand_name: Optional[str] = None
    medication_code: Optional[str] = Field(None, max_length=50)
    dosage_form: Optional[str] = Field(None, max_length=100)
    strength: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, max_length=50)
    is_nhis_covered: bool = False
    nhis_code: Optional[str] = Field(None, max_length=50)
    is_formulary: bool = True
    unit_cost: Optional[Decimal] = Field(None, ge=0)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    reorder_level: Optional[int] = Field(None, ge=0)
    reorder_quantity: Optional[int] = Field(None, ge=0)


class MedicationCreate(MedicationBase):
    pass


class MedicationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    generic_name: Optional[str] = None
    brand_name: Optional[str] = None
    medication_code: Optional[str] = Field(None, max_length=50)
    dosage_form: Optional[str] = Field(None, max_length=100)
    strength: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, max_length=50)
    is_nhis_covered: Optional[bool] = None
    nhis_code: Optional[str] = Field(None, max_length=50)
    is_formulary: Optional[bool] = None
    unit_cost: Optional[Decimal] = Field(None, ge=0)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    reorder_level: Optional[int] = Field(None, ge=0)
    reorder_quantity: Optional[int] = Field(None, ge=0)


class MedicationRead(MedicationBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Stock Item Schemas
class StockItemBase(BaseModel):
    medication_id: int
    batch_number: Optional[str] = Field(None, max_length=100)
    expiry_date: Optional[datetime] = None
    manufacturing_date: Optional[datetime] = None
    quantity: int = Field(default=0, ge=0)
    location: Optional[str] = Field(None, max_length=100)
    supplier: Optional[str] = Field(None, max_length=255)
    supplier_id: Optional[int] = None
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[Decimal] = Field(None, ge=0)


class StockItemCreate(StockItemBase):
    pass


class StockItemUpdate(BaseModel):
    batch_number: Optional[str] = Field(None, max_length=100)
    expiry_date: Optional[datetime] = None
    quantity: Optional[int] = Field(None, ge=0)
    location: Optional[str] = Field(None, max_length=100)
    supplier: Optional[str] = Field(None, max_length=255)


class StockItemRead(StockItemBase):
    id: int
    reserved_quantity: int
    available_quantity: int
    status: StockStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    medication: Optional[MedicationRead] = None

    class Config:
        from_attributes = True


# Inventory Transaction Schemas
class InventoryTransactionBase(BaseModel):
    medication_id: int
    stock_item_id: Optional[int] = None
    prescription_id: Optional[int] = None
    transaction_type: TransactionType
    quantity: int
    unit_cost: Optional[Decimal] = Field(None, ge=0)
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class InventoryTransactionCreate(InventoryTransactionBase):
    pass


class InventoryTransactionRead(InventoryTransactionBase):
    id: int
    total_cost: Optional[Decimal] = None
    transaction_date: datetime
    performed_by_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Formulary Rule Schemas
class FormularyRuleBase(BaseModel):
    rule_name: str = Field(..., max_length=255)
    rule_type: str = Field(..., max_length=100)
    description: Optional[str] = None
    medication_id: Optional[int] = None
    medication_category: Optional[str] = Field(None, max_length=100)
    condition: Optional[str] = None
    is_active: bool = True


class FormularyRuleCreate(FormularyRuleBase):
    pass


class FormularyRuleUpdate(BaseModel):
    rule_name: Optional[str] = Field(None, max_length=255)
    rule_type: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    condition: Optional[str] = None
    is_active: Optional[bool] = None


class FormularyRuleRead(FormularyRuleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Drug Interaction Schemas
class DrugInteractionBase(BaseModel):
    medication1_id: int
    medication2_id: int
    interaction_type: str = Field(..., max_length=100)
    severity: str = Field(..., max_length=50)
    description: str
    clinical_significance: Optional[str] = None
    management: Optional[str] = None


class DrugInteractionCreate(DrugInteractionBase):
    pass


class DrugInteractionUpdate(BaseModel):
    interaction_type: Optional[str] = Field(None, max_length=100)
    severity: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    clinical_significance: Optional[str] = None
    management: Optional[str] = None


class DrugInteractionRead(DrugInteractionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Stock Check Schemas
class StockCheckRequest(BaseModel):
    medication_id: int
    required_quantity: int = Field(..., gt=0)


class StockCheckResponse(BaseModel):
    medication_id: int
    medication_name: str
    available_quantity: int
    total_quantity: int
    reserved_quantity: int
    is_available: bool
    stock_items: List[StockItemRead] = []
    low_stock: bool
    out_of_stock: bool


# Drug Interaction Check Schemas
class DrugInteractionCheckRequest(BaseModel):
    medication_ids: List[int] = Field(..., min_items=2)


class DrugInteractionCheckResponse(BaseModel):
    has_interactions: bool
    interactions: List[DrugInteractionRead] = []


# Formulary Check Schemas
class FormularyCheckRequest(BaseModel):
    medication_id: int
    patient_nhis_number: Optional[str] = None


class FormularyCheckResponse(BaseModel):
    medication_id: int
    medication_name: str
    is_formulary: bool
    is_nhis_covered: bool
    compliance_status: str
    rules: List[FormularyRuleRead] = []
    warnings: List[str] = []

