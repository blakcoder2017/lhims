from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Numeric, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql
from app.db.database import Base
import enum
from decimal import Decimal
from datetime import date


class StockStatus(str, enum.Enum):
    """Stock status enumeration"""
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    EXPIRED = "expired"
    DISCONTINUED = "discontinued"


class TransactionType(str, enum.Enum):
    """Inventory transaction type enumeration"""
    PURCHASE = "purchase"
    SALE = "sale"
    ADJUSTMENT = "adjustment"
    RETURN = "return"
    EXPIRY = "expiry"
    DAMAGE = "damage"
    TRANSFER = "transfer"


class Medication(Base):
    """
    SQLAlchemy Model for medication/drug catalog.
    Master list of all medications available in the pharmacy.
    """
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    
    # Medication Details
    name = Column(String(255), nullable=False, index=True)  # Medication name
    generic_name = Column(String(255), nullable=True)  # Generic name
    brand_name = Column(String(255), nullable=True)  # Brand name
    medication_code = Column(String(50), unique=True, nullable=True, index=True)  # NDC code or internal code
    dosage_form = Column(String(100), nullable=True)  # e.g., "Tablet", "Capsule", "Syrup"
    strength = Column(String(100), nullable=True)  # e.g., "500mg", "10ml"
    unit = Column(String(50), nullable=True)  # e.g., "tablet", "bottle", "vial"
    
    # Formulary Information
    is_nhis_covered = Column(Boolean, default=False)  # NHIS coverage status
    nhis_code = Column(String(50), nullable=True)  # NHIS medication code
    is_formulary = Column(Boolean, default=True)  # Is it in the formulary
    
    # Pricing
    unit_cost = Column(Numeric(10, 2), nullable=True)  # Cost per unit
    unit_price = Column(Numeric(10, 2), nullable=True)  # Selling price per unit
    
    # Stock Settings
    reorder_level = Column(Integer, nullable=True, default=10)  # Minimum stock level
    reorder_quantity = Column(Integer, nullable=True, default=50)  # Quantity to reorder
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    stock_items = relationship("StockItem", back_populates="medication")
    transactions = relationship("InventoryTransaction", back_populates="medication")
    
    def __repr__(self):
        return f"<Medication(id={self.id}, name='{self.name}')>"


class StockItem(Base):
    """
    SQLAlchemy Model for individual stock items (batches).
    Tracks specific batches with expiry dates and batch numbers.
    """
    __tablename__ = "stock_items"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    medication_id = Column(Integer, ForeignKey("medications.id"), nullable=False)
    
    # Batch Information
    batch_number = Column(String(100), nullable=True, index=True)  # Batch/lot number
    expiry_date = Column(DateTime, nullable=True)  # Expiry date
    manufacturing_date = Column(DateTime, nullable=True)  # Manufacturing date
    
    # Stock Information
    quantity = Column(Integer, nullable=False, default=0)  # Current quantity
    reserved_quantity = Column(Integer, nullable=False, default=0)  # Reserved for pending prescriptions
    available_quantity = Column(Integer, nullable=False, default=0)  # Available quantity (quantity - reserved)
    status = Column(postgresql.ENUM(StockStatus, values_callable=lambda x: [e.value for e in x], name='stockstatus', create_type=False), nullable=False, default=StockStatus.IN_STOCK)
    
    # Location
    location = Column(String(100), nullable=True)  # Storage location (shelf, room, etc.)
    
    # Supplier Information
    supplier = Column(String(255), nullable=True)  # Supplier name (legacy)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)  # Link to supplier
    purchase_date = Column(DateTime, nullable=True)  # Date purchased
    purchase_price = Column(Numeric(10, 2), nullable=True)  # Purchase price per unit
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    medication = relationship("Medication", back_populates="stock_items")
    transactions = relationship("InventoryTransaction", back_populates="stock_item")
    supplier_obj = relationship("Supplier", back_populates="stock_items")
    
    def __repr__(self):
        return f"<StockItem(id={self.id}, medication_id={self.medication_id}, quantity={self.quantity}, batch={self.batch_number})>"


class InventoryTransaction(Base):
    """
    SQLAlchemy Model for inventory transactions.
    Tracks all stock movements (purchases, sales, adjustments, etc.).
    """
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    medication_id = Column(Integer, ForeignKey("medications.id"), nullable=False)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)  # Optional: specific batch
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=True)  # If related to prescription
    performed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who performed the transaction
    
    # Transaction Details
    transaction_type = Column(postgresql.ENUM(TransactionType, values_callable=lambda x: [e.value for e in x], name='transactiontype', create_type=False), nullable=False)
    quantity = Column(Integer, nullable=False)  # Quantity change (positive for additions, negative for deductions)
    unit_cost = Column(Numeric(10, 2), nullable=True)  # Cost per unit at time of transaction
    total_cost = Column(Numeric(10, 2), nullable=True)  # Total cost
    
    # Reference Information
    reference_number = Column(String(100), nullable=True)  # Invoice number, receipt number, etc.
    notes = Column(Text, nullable=True)  # Additional notes
    
    # Transaction Date
    transaction_date = Column(DateTime, nullable=False, server_default=func.now())
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    medication = relationship("Medication", back_populates="transactions")
    stock_item = relationship("StockItem", back_populates="transactions")
    prescription = relationship("Prescription")
    performed_by = relationship("User", foreign_keys=[performed_by_id])
    
    def __repr__(self):
        return f"<InventoryTransaction(id={self.id}, type={self.transaction_type.value}, quantity={self.quantity})>"


class FormularyRule(Base):
    """
    SQLAlchemy Model for formulary rules and compliance checks.
    Defines rules for medication prescribing and dispensing.
    """
    __tablename__ = "formulary_rules"

    id = Column(Integer, primary_key=True, index=True)
    
    # Rule Details
    rule_name = Column(String(255), nullable=False)  # Name of the rule
    rule_type = Column(String(100), nullable=False)  # e.g., "nhis_coverage", "restriction", "substitution"
    description = Column(Text, nullable=True)  # Rule description
    
    # Medication Association
    medication_id = Column(Integer, ForeignKey("medications.id"), nullable=True)  # Specific medication
    medication_category = Column(String(100), nullable=True)  # Medication category
    
    # Rule Conditions
    condition = Column(Text, nullable=True)  # JSON or text condition
    is_active = Column(Boolean, default=True)  # Is rule active
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    medication = relationship("Medication")
    
    def __repr__(self):
        return f"<FormularyRule(id={self.id}, rule_name='{self.rule_name}')>"


class DrugInteraction(Base):
    """
    SQLAlchemy Model for drug interaction database.
    Stores known drug interactions and their severity.
    """
    __tablename__ = "drug_interactions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Medication Pair
    medication1_id = Column(Integer, ForeignKey("medications.id"), nullable=False)
    medication2_id = Column(Integer, ForeignKey("medications.id"), nullable=False)
    
    # Interaction Details
    interaction_type = Column(String(100), nullable=False)  # e.g., "contraindication", "warning", "precaution"
    severity = Column(String(50), nullable=False)  # e.g., "severe", "moderate", "mild"
    description = Column(Text, nullable=False)  # Description of the interaction
    clinical_significance = Column(Text, nullable=True)  # Clinical significance
    management = Column(Text, nullable=True)  # How to manage the interaction
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    medication1 = relationship("Medication", foreign_keys=[medication1_id])
    medication2 = relationship("Medication", foreign_keys=[medication2_id])
    
    def __repr__(self):
        return f"<DrugInteraction(id={self.id}, med1={self.medication1_id}, med2={self.medication2_id}, severity={self.severity})>"

