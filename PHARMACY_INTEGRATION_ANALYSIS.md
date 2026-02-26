# Pharmacy System Integration Analysis

## Executive Summary

This document provides a detailed analysis of the LHIMS pharmacy module, its architecture, and how it integrates with other modules in the system.

---

## 1. System Architecture Overview

### 1.1 Two Parallel Pharmacy Systems

The LHIMS contains **two parallel pharmacy systems**:

| System | Database Tables | Purpose |
|--------|-----------------|---------|
| **Legacy** | `medications`, `stock_items`, `inventory_transactions` | Original inventory-based system |
| **Ghana (New)** | `pharmacy_drug`, `pharmacy_batch`, `pharmacy_stock_ledger` | FEFO-based Ghana-compliant system |

### 1.2 Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Frontend**: Jinja2 Templates + AdminLTE

---

## 2. Database Integration Points

### 2.1 Core Pharmacy Models

```
pharmacy_dosage_form (UUID)
    ↓
pharmacy_drug (UUID) ──────► pharmacy_batch (UUID)
    ↓                           ↓
pharmacy_supplier (UUID)    pharmacy_stock_ledger (UUID)
    ↓
pharmacy_store (UUID)
```

### 2.2 Integration with Encounter/Clinical Module

**Model**: `Prescription` ([`app/models/encounter_models.py`](app/models/encounter_models.py:224))

```python
class Prescription:
    # Foreign Keys
    encounter_id = Column(Integer, ForeignKey("encounters.id"))
    prescribed_by_id = Column(Integer, ForeignKey("users.id"))
    medication_id = Column(Integer, ForeignKey("medications.id"))       # LEGACY
    pharmacy_drug_id = Column(UUID, ForeignKey("pharmacy_drug.id"))   # GHANA
    
    # Fields
    medication_name = Column(String)  # Free text (required)
    dosage = Column(String)          # e.g., "500mg"
    frequency = Column(String)       # e.g., "twice daily"
    duration = Column(String)        # e.g., "7 days"
    quantity = Column(Integer)       # Number of units
    
    # Status
    status = Column(ENUM)           # PENDING, IN_PROGRESS, COMPLETED, CANCELLED
    dispensed_by_id = Column(Integer, ForeignKey("users.id"))
    dispensed_at = Column(DateTime)
```

**Integration Flow**:
1. Doctor creates prescription during encounter → `Prescription` record created
2. Prescription linked to `Encounter` → Patient context maintained
3. Pharmacist views pending prescriptions → Filtered by `status = PENDING`
4. Dispensing updates status → `COMPLETED` with `dispensed_by_id`

### 2.3 Integration with Billing Module

**Model**: `Charge` ([`app/models/billing_models.py`](app/models/billing_models.py:156))

```python
class Charge:
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"))
    charge_type = Column(ENUM)  # ChargeType.PHARMACY
    amount = Column(Numeric)
    status = Column(ENUM)  # PENDING, PAID, WAIVED
```

**Payment Flow**:
```
Doctor creates Prescription
        ↓
Prescription appears in Pharmacy queue
        ↓
Cash Patient → Must pay at Front Office
        ↓
Charge created with charge_type = PHARMACY
        ↓
Payment verified before dispensing allowed
        ↓
Pharmacist can dispense
```

**Key Integration Points**:
- [`ancillary_services_api.py:dispense_prescription()`](app/routers/ancillary_services_api.py:1520) - Checks payment before dispensing
- [`payment_ui_routes.py:pay_pharmacy_page()`](app/routers/payment_ui_routes.py:822) - Payment processing for pharmacy

### 2.4 Integration with Inventory Module

**Legacy Integration**:
```python
# app/models/inventory_models.py
class InventoryTransaction:
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"))
    medication_id = Column(Integer, ForeignKey("medications.id"))
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"))
    transaction_type = Column(ENUM)  # SALE, PURCHASE, ADJUSTMENT
    quantity = Column(Integer)  # Negative for sales
```

**Ghana System Integration**:
```python
# app/models/pharmacy_models.py
class PharmacyStockLedger:
    # Immutable stock movement tracking
    drug_id = Column(UUID, ForeignKey("pharmacy_drug.id"))
    batch_id = Column(UUID, ForeignKey("pharmacy_batch.id"))
    movement_type = Column(String)  # STOCK_IN, DISPENSE, SALE, RETURN
    qty_in = Column(Numeric)
    qty_out = Column(Numeric)
    reference_type = Column(String)  # "PRESCRIPTION"
    reference_id = Column(UUID)
```

### 2.5 Integration with Drug Administration Module

**Model**: `DrugAdministration` ([`app/models/drug_administration_models.py`](app/models/drug_administration_models.py:36))

```python
class DrugAdministration:
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"))
    # Tracks actual administration to patient (for IPD)
```

---

## 3. API Integration Points

### 3.1 Pharmacy Routes

| Route | File | Integration |
|-------|------|-------------|
| `/pharmacy` | [`ancillary_services_api.py:1263`](app/routers/ancillary_services_api.py:1263) | Legacy prescription dashboard |
| `/pharmacy/ghana/prescriptions` | [`pharmacy_ghana_ui_routes.py`](app/routers/pharmacy_ghana_ui_routes.py) | Ghana prescription list |
| `/pharmacy/ghana/reports/stock-ledger` | [`pharmacy_ghana_ui_routes.py`](app/routers/pharmacy_ghana_ui_routes.py) | Stock ledger report |
| `/pharmacy/formulary/search` | [`pharmacy_ghana_api.py`](app/routers/pharmacy_ghana_api.py) | Drug lookup API |

### 3.2 Key Integration Functions

**1. Payment Verification** ([`app/utils/payment_verification.py`](app/utils/payment_verification.py))
```python
def is_cash_patient(db, patient_id) -> bool:
    """Determines if patient is cash-paying"""
    
def check_payment_required_and_paid(db, patient_id, service_type, ...) -> dict:
    """Checks if payment is required and if paid"""
```

**2. Charge Creation** ([`app/services/charge_automation.py`](app/services/charge_automation.py))
```python
def create_charge_for_prescription(db, prescription, user_id):
    """Creates billing charge for prescription"""
```

**3. Inventory Stock Check** ([`app/crud/inventory_crud.py`](app/crud/inventory_crud.py))
```python
def check_stock_availability(db, medication_id, quantity) -> dict:
    """Checks if medication is in stock"""
```

---

## 4. Sidebar Integration

### 4.1 Current Menu Structure

```
Pharmacy (PhIS)
├── Pending Prescriptions     → /pharmacy/ghana/prescriptions
├── Dashboard                 → /pharmacy/ghana
├── Drug Catalogue           → /pharmacy/ghana/drugs
├── Batch Management         → /pharmacy/ghana/stores/{id}/batches
├── Stores                   → /pharmacy/stores
├── Suppliers                → /pharmacy/suppliers
├── Formulary Rules          → /pharmacy/formulary
├── Drug Interactions        → /pharmacy/drug-interactions
└── Reports
    ├── Pharmacy Report       → /reports/pharmacy
    ├── Stock Ledger         → /pharmacy/ghana/reports/stock-ledger
    └── Profit & Margin       → /pharmacy/ghana/reports/profit-margin
```

### 4.2 Role-Based Access

| Role | Access Level |
|------|-------------|
| Admin | Full access |
| Pharmacy Staff | All pharmacy functions |
| Doctor | View prescriptions, prescribe |
| Clinician | View prescriptions, prescribe |
| Finance | Reports only |
| Nurse | Limited (drug administration) |

---

## 5. Data Flow Diagrams

### 5.1 Outpatient Prescription Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Doctor    │────►│  Encounter  │────►│  Prescription│
└─────────────┘     └─────────────┘     └─────────────┘
                                                │
                                                ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Front Office│◄───│   Billing   │◄───│  Payment    │
│  (Cash)     │     │   Charge    │     │  Verification│
└─────────────┘     └─────────────┘     └─────────────┘
                                                │
                                                ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Inventory  │◄───│  Dispense   │◄───│ Pharmacist  │
│  Update     │     │  Process    │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 5.2 Stock Movement Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Stock-In    │────►│  Pharmacy   │────►│  Pharmacy   │
│ (Purchase)  │     │  Batch      │     │  Stock Ledger│
└─────────────┘     └─────────────┘     └─────────────┘
                                                │
                     ┌─────────────┐             │
                     │  Prescription│◄───────────┘
                     │  Fulfillment│
                     └─────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Pharmacy   │   │  Pharmacy   │   │  Inventory  │
│  Dispense    │   │  Dispense   │   │  Transaction│
│  Allocation  │   │  Item       │   │  (Legacy)   │
└─────────────┘   └─────────────┘   └─────────────┘
```

---

## 6. Key Integration APIs

### 6.1 Prescribing (Doctor)

```python
# app/routers/encounter_api.py
POST /api/v1/encounters/{id}/prescriptions
Body: {
    "medication_name": "Paracetamol",
    "pharmacy_drug_id": "uuid",  # NEW - Ghana system
    "medication_id": 1,           # LEGACY - old system
    "dosage": "500mg",
    "frequency": "three times daily",
    "duration": "5 days",
    "quantity": 15,
    "instructions": "Take with food"
}
```

### 6.2 Dispensing (Pharmacist)

```python
# app/routers/pharmacy_ghana_ui_routes.py
POST /pharmacy/ghana/prescriptions/{id}/dispense
Body: {
    "batch_id": "uuid",
    "qty_dispensed": 15,
    "selling_price": 5.00,
    "payment_type": "CASH",
    "dispense_instructions": "Take as directed"
}
```

### 6.3 Stock Ledger Query

```python
# app/routers/pharmacy_ghana_api.py
GET /api/v1/pharmacy/stock-ledger?drug_id={id}&from_date={date}
Response: {
    "entries": [...],
    "running_balance": 150,
    "total_qty_in": 200,
    "total_qty_out": 50
}
```

---

## 7. Integration Challenges & Solutions

### 7.1 Dual Prescription System

**Problem**: Both `medication_id` (legacy) and `pharmacy_drug_id` (Ghana) can be set

**Solution**: 
- Make `pharmacy_drug_id` preferred for new prescriptions
- Migration script maps legacy to new system
- Display shows "Formulary Drug" vs "Free Text" badge

### 7.2 Payment Integration

**Problem**: Must verify payment before allowing dispensing

**Solution**:
1. Check if patient is cash-paying using `is_cash_patient()`
2. Look for unpaid `Charge` with `charge_type = PHARMACY`
3. Block dispensing if balance > 0

### 7.3 Stock Availability

**Problem**: Must check stock in both legacy and Ghana systems

**Solution**:
```python
if prescription.pharmacy_drug_id:
    # Use Ghana system
    batches = db.query(PharmacyBatch).filter(
        drug_id=prescription.pharmacy_drug_id,
        qty_on_hand >= required_qty
    ).order_by(expiry_date).all()
else:
    # Fallback to legacy
    stock_check = inventory_crud.check_stock_availability(...)
```

---

## 8. Database Schema Summary

### Tables Created for Ghana System

| Table | Purpose |
|-------|---------|
| `pharmacy_dosage_form` | Master list of dosage forms |
| `pharmacy_supplier` | Supplier records |
| `pharmacy_store` | Store/location records |
| `pharmacy_drug` | Drug formulations (generic + strength + form + route) |
| `pharmacy_batch` | Batch tracking with expiry |
| `pharmacy_stock_ledger` | Immutable stock movements |
| `pharmacy_dispense` | Dispense transactions |
| `pharmacy_dispense_item` | Items in each dispense |
| `pharmacy_dispense_allocation` | FEFO batch allocation |
| `pharmacy_drug_interaction` | Drug interaction database |
| `pharmacy_role_policy` | Role-based pricing visibility |
| `patient_active_medication` | Patient's current medications |

---

## 9. Conclusion

The pharmacy module is deeply integrated with:

1. **Encounter Module** - Prescriptions linked to patient encounters
2. **Billing Module** - Payment verification before dispensing
3. **Inventory Module** - Stock tracking (both legacy and new)
4. **Drug Administration** - Tracking medication given to patients
5. **Reports Module** - Financial and stock reports

The dual-system architecture allows for gradual migration from legacy to Ghana-compliant pharmacy while maintaining backward compatibility.
