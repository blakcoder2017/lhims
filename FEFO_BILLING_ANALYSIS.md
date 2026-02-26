# FEFO Pharmacy + Billing + Finance Integration Analysis

## Current State Assessment

### ✅ What's Already Implemented

#### 1. FEFO (First Expiry First Out) System
**Location**: [`app/services/pharmacy_fefo.py`](app/services/pharmacy_fefo.py)

| Function | Purpose |
|----------|---------|
| `get_available_batches_fefo()` | Get batches sorted by expiry date |
| `allocate_batches_fefo()` | Allocate qty from earliest expiry batches |
| `allocate_fefo()` | Full allocation with ledger + batch updates |
| `stock_in_create_batch()` | Stock-in with automatic ledger entry |

**FEFO Logic**:
```python
# Sort by expiry_date ASC, received_date ASC
batches = query.order_by(
    PharmacyBatch.expiry_date.asc(),
    PharmacyBatch.received_date.asc()
).all()
```

#### 2. Stock Ledger (Immutable)
**Location**: [`app/models/pharmacy_models.py:90`](app/models/pharmacy_models.py:90)

Tracks all movements:
- `STOCK_IN` - Purchases
- `DISPENSE` - Patient dispensing
- `SALE` - Direct sales
- `RETURN` - Patient returns
- `ADJUSTMENT` - Stock corrections

Each entry stores:
- `unit_cost_snapshot` - Cost at time of transaction
- `selling_price_snapshot` - Price at time of transaction
- `reference_type`, `reference_id` - Links to source

#### 3. Batch Tracking
**Location**: [`app/models/pharmacy_models.py:68`](app/models/pharmacy_models.py:68)

```python
class PharmacyBatch:
    batch_no = Column(String)
    expiry_date = Column(Date)
    qty_on_hand = Column(Numeric)
    qty_reserved = Column(Numeric)
    unit_cost = Column(Numeric)      # Purchase cost
    selling_price = Column(Numeric)   # Selling price
    status = Column(String)          # ACTIVE, QUARANTINED, EXPIRED, DEPLETED
```

---

### ❌ Gaps in Integration

#### 1. **Missing: Invoice Link**
**Current State**: `PharmacyDispense` has NO `invoice_id` field

```python
# Current - Missing!
class PharmacyDispense:
    patient_id = Column(Integer)
    encounter_id = Column(Integer)  
    # ❌ NO invoice_id!
    payment_type = Column(String)  # CASH, INSURANCE, WARD_CHARGE, FREE
```

**Impact**: Cannot track which invoice payment was received against

#### 2. **Missing: Prescription Link in PharmacyDispense**
**Current State**: Dispensing creates new `PharmacyDispense` but doesn't link back to `Prescription`

```python
# Current - Missing!
class PharmacyDispense:
    # ❌ NO prescription_id!
    patient_id = Column(Integer)
    encounter_id = Column(Integer)
```

**Impact**: Cannot trace which prescription was fulfilled

#### 3. **Billing Integration is One-Way**
- ✅ Payment check BEFORE dispensing (blocks if unpaid)
- ❌ No automatic invoice creation AFTER dispensing
- ❌ No link to `Invoice` or `Charge` records

#### 4. **Finance Reports Need Cost Margins**
- ✅ Stock ledger has `unit_cost_snapshot`
- ❌ Profit report calculates approximate 25% margin (hardcoded)
- ❌ No actual cost tracking per transaction

---

## Integration Flow Required

### Current Flow (Broken)
```
Doctor creates Prescription
        ↓
Prescription in Pharmacy queue
        ↓
Cash patient → Front Office payment
        ↓
Charge created (legacy system)
        ↓
Pharmacist dispenses → PharmacyDispense created
        ↓
        ❌ NO INVOICE LINK
        ❌ NO PRESCRIPTION LINK
```

### Required Flow
```
Doctor creates Prescription (with pharmacy_drug_id)
        ↓
Prescription in Pharmacy queue
        ↓
Cash patient → Front Office payment
        ↓
Charge created with charge_type = PHARMACY
        ↓
Invoice created
        ↓
Pharmacist dispenses
        ├─→ PharmacyDispense created (linked to prescription_id)
        ├─→ FEFO allocation (PharmacyDispenseAllocation)
        ├─→ Stock ledger updated
        └─→ invoice_id linked to PharmacyDispense
        ↓
Finance can track: Cost → Revenue → Profit
```

---

## Data Model Gaps

### Gap 1: Add prescription_id to PharmacyDispense
```python
# NEED TO ADD:
class PharmacyDispense(Base):
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
```

### Gap 2: Better Cost Tracking in Dispense
```python
# NEED TO TRACK:
class PharmacyDispenseItem(Base):
    unit_cost_snapshot = Column(Numeric)  # Actual cost from batch
    margin_calculated = Column(Numeric) # Revenue - Cost
```

---

## Report Capabilities

### ✅ Available Reports

| Report | Location | Fields |
|--------|----------|--------|
| Stock Ledger | `/pharmacy/ghana/reports/stock-ledger` | All movements with running balance |
| Controlled Drugs | `/pharmacy/ghana/reports/controlled-register` | Controlled dispenses |
| Near Expiry | `/pharmacy/ghana/reports/near-expiry` | Batches expiring soon |
| Profit Margin | `/pharmacy/ghana/reports/profit-margin` | Revenue (hardcoded 25% margin) |

### ❌ Missing Reports

1. **Cost of Goods Sold (COGS)** - Actual cost of items dispensed
2. **Gross Profit Report** - Revenue - Actual cost (not estimated)
3. **Batch Profitability** - Which batches are most profitable
4. **Inventory Valuation** - Current stock value at cost

---

## Recommendations

### Priority 1: Fix Data Model
1. Add `prescription_id` to `PharmacyDispense`
2. Add `invoice_id` to `PharmacyDispense`  
3. Add `unit_cost_snapshot` to `PharmacyDispenseItem`

### Priority 2: Fix Dispensing Flow
1. Link `PharmacyDispense` to `Prescription` on create
2. Create Invoice automatically after successful dispense
3. Update `Charge` status to PAID after dispense

### Priority 3: Finance Reports
1. Calculate actual margin using `unit_cost_snapshot`
2. Create COGS report
3. Create inventory valuation report

---

## Files to Modify

| File | Change |
|------|--------|
| `app/models/pharmacy_models.py` | Add prescription_id, invoice_id fields |
| `app/routers/pharmacy_ghana_ui_routes.py` | Link dispense to prescription/invoice |
| `app/services/pharmacy_fefo.py` | Return cost info for profit calc |

---

## Summary

| Feature | Status | Notes |
|---------|--------|-------|
| FEFO Allocation | ✅ Complete | Working correctly |
| Stock Ledger | ✅ Complete | Immutable, tracks all movements |
| Batch Tracking | ✅ Complete | Expiry, quantities tracked |
| Prescription Link | ❌ Missing | Need to add prescription_id |
| Invoice Link | ❌ Missing | Need to add invoice_id |
| Cost Tracking | ⚠️ Partial | unit_cost stored but not used in reports |
| Finance Integration | ❌ Incomplete | Need bidirectional link |
