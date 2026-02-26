# Pharmacy Module Analysis: Current State, Gaps & Migration Plan

## 1. CURRENT STATE MAP

### 1.1 Database Tables/Models

#### Legacy System (app/models/inventory_models.py)
| Table | Purpose | PK Type | Key Fields |
|-------|---------|---------|------------|
| `medications` | Master drug catalog | Integer | name, generic_name, brand_name, dosage_form, strength, unit_cost, unit_price, is_controlled |
| `stock_items` | Batch tracking | Integer | medication_id, batch_number, expiry_date, quantity, available_quantity, purchase_price |
| `inventory_transactions` | Stock movements | Integer | medication_id, stock_item_id, transaction_type, quantity, unit_cost |

#### Ghana Pharmacy System (app/models/pharmacy_models.py)
| Table | Purpose | PK Type | Key Fields |
|-------|---------|---------|------------|
| `pharmacy_dosage_form` | Dosage form catalog | UUID | name |
| `pharmacy_supplier` | Supplier catalog | UUID | name, phone, email, address |
| `pharmacy_store` | Store locations | UUID | name, facility_id |
| `pharmacy_drug` | **Formulation** = generic + strength + dosage form + route | UUID | item_code, generic_name, brand_name, dosage_form_id, strength_value, route, is_controlled |
| `pharmacy_batch` | **Batch with expiry tracking** | UUID | drug_id, store_id, batch_no, expiry_date, unit_cost, selling_price, qty_on_hand, qty_reserved, status |
| `pharmacy_stock_ledger` | **Immutable stock ledger** | UUID | store_id, drug_id, batch_id, movement_type, qty_in, qty_out, unit_cost_snapshot |
| `pharmacy_dispense` | Dispense transaction | UUID | patient_id, encounter_id, status, dispensed_by_id |
| `pharmacy_dispense_item` | Items in dispense | UUID | dispense_id, drug_id, qty_dispensed, unit_selling_price |
| `pharmacy_dispense_allocation` | **FEFO batch allocation** | UUID | dispense_item_id, batch_id, qty_allocated |
| `pharmacy_drug_interaction` | Drug interactions | UUID | drug_a_id, drug_b_id, severity, description, recommendation |
| `pharmacy_role_policy` | **Role-based pricing visibility** | UUID | role_name, can_view_unit_cost, can_view_margin, can_edit_selling_price |
| `patient_active_medication` | Patient active meds | UUID | patient_id, drug_id, start_date, status |

#### Prescription (app/models/encounter_models.py)
| Field | Type | Purpose |
|-------|------|---------|
| `pharmacy_drug_id` | UUID (FK) | **NEW** - Ghana formulation reference |
| `medication_id` | Integer (FK) | **LEGACY** - old inventory medication |
| `medication_name` | String | **FREE-TEXT** - drug name (required) |

### 1.2 API Routes & Services

#### API Routers
| File | Purpose |
|------|---------|
| `app/routers/pharmacy_ghana_api.py` | Formulary search, interactions, stock-in, reports |
| `app/routers/pharmacy_ghana_ui_routes.py` | Dashboard, drugs list, batches, reports UI |
| `app/routers/inventory_api.py` | Legacy inventory management |

#### Services
| File | Purpose |
|------|---------|
| `app/services/pharmacy_fefo.py` | FEFO allocation, stock-in with ledger, batch management |

#### Key API Endpoints (pharmacy_ghana_api.py)
- `GET /pharmacy/formulary/search` - Search formulations
- `GET /pharmacy/formulary/{drug_id}` - Get formulation details
- `GET /pharmacy/interactions/check` - Check drug interactions
- `POST /pharmacy/stores/{store_id}/stock-in` - Stock-in with batch creation
- `GET /pharmacy/reports/near-expiry` - Near-expiry report
- `GET /pharmacy/reports/controlled-register` - Controlled drugs register

### 1.3 UI Templates (Jinja2)

| Path | Purpose |
|------|---------|
| `app/templates/pharmacy_ghana/dashboard.html` | Pharmacy dashboard (low stock, near expiry, expired) |
| `app/templates/pharmacy_ghana/drugs_list.html` | Drug catalogue/formulary |
| `app/templates/pharmacy_ghana/batches.html` | Batch management & stock-in |
| `app/templates/pharmacy_ghana/near_expiry.html` | Near-expiry report |
| `app/templates/pharmacy_ghana/controlled_register.html` | Controlled drugs register |
| `app/templates/inventory/prescription_check.html` | Legacy prescription check |
| `app/templates/ancillary/prescription_detail.html` | Prescription detail with dispensing |

### 1.4 Roles/Permissions Implementation

#### Pharmacy-Specific (PharmacyRolePolicy)
- `can_view_unit_cost` - View cost price
- `can_view_margin` - View profit margins
- `can_edit_selling_price` - Modify selling price
- `can_adjust_stock` - Adjust stock quantities
- `can_approve_adjustment` - Approve stock adjustments
- `can_dispense_controlled` - Dispense controlled drugs

#### General Role System (role_permissions_api.py)
- Uses `Role` and `Permission` models
- Grouped by module in admin UI
- Admin can assign permissions to roles

---

## 2. GAP LIST

### 2.1 Feature Availability Matrix

| Feature | Status | Implementation Details |
|---------|--------|------------------------|
| **Batch/Expiry Tracking** | ✅ EXISTS | `PharmacyBatch` has batch_no, expiry_date, status |
| **FEFO Allocation** | ✅ EXISTS | `pharmacy_fefo.py` with `get_available_batches_fefo()`, `allocate_fefo()` |
| **Stock Ledger** | ✅ EXISTS | `PharmacyStockLedger` - immutable, tracks qty_in/qty_out per batch |
| **Prescribing uses drug_id** | ⚠️ PARTIAL | `Prescription.pharmacy_drug_id` exists BUT `medication_name` (free-text) is still required |
| **Dosage Forms** | ✅ EXISTS | `PharmacyDosageForm` table exists with relationship to drugs |
| **Drug Interactions** | ✅ EXISTS | `PharmacyDrugInteraction` with severity, description, recommendation |
| **Pricing Visibility** | ⚠️ PARTIAL | `PharmacyRolePolicy` table exists BUT: <br>- No admin UI to manage policies<br>- Only basic `_can_view_cost()` function<br>- No margin/profit display |

### 2.2 Specific Gaps

| Gap | Severity | Details |
|-----|----------|---------|
| **Dispensing Workflow UI** | HIGH | No complete UI for creating `PharmacyDispense` with items and FEFO allocation |
| **Pricing Policy Admin UI** | MEDIUM | `PharmacyRolePolicy` exists but no CRUD UI at `/admin` |
| **Dual Prescription System** | HIGH | Both `pharmacy_drug_id` AND `medication_name` required; no migration of legacy data |
| **Legacy Data Migration** | HIGH | No migration path from `medications` → `pharmacy_drug`, `stock_items` → `pharmacy_batch` |
| **Walk-in/OTC Sales** | MEDIUM | `Prescription.is_walk_in` exists but no dedicated UI flow |
| **Stock Adjustment Approvals** | LOW | Policy field exists but no workflow implementation |

---

## 3. PROPOSED MIGRATION PLAN

### Phase 1: Foundation (Weeks 1-2)
**Objective:** Enable dual-write mode, prepare data migration path

1. **Add migration fields to Prescription**
   - Make `pharmacy_drug_id` nullable (currently NOT NULL in schema comment but verify)
   - Keep `medication_name` for legacy displays

2. **Create data migration scripts**
   ```sql
   -- Migration: medications → pharmacy_drug
   INSERT INTO pharmacy_drug (id, item_code, generic_name, brand_name, 
       dosage_form_id, strength_value, strength_unit, route, 
       is_active, created_at)
   SELECT 
       gen_random_uuid() as id,
       medication_code as item_code,
       COALESCE(generic_name, name) as generic_name,
       brand_name,
       (SELECT id FROM pharmacy_dosage_form WHERE name ILIKE CONCAT('%', dosage_form, '%') LIMIT 1) as dosage_form_id,
       -- Parse strength_value from 'strength' field
       ... 
   FROM medications;
   ```

3. **Seed dosage forms** if empty
   - Tablet, Capsule, Syrup, Injection, Cream, etc.

### Phase 2: Core Features (Weeks 3-4)
**Objective:** Complete dispensing workflow, add missing UIs

1. **Build Dispensing UI** (`/pharmacy/ghana/dispense/{prescription_id}`)
   - Show prescription details
   - FEFO batch selection (auto-allocate)
   - Manual batch override option
   - Calculate total, apply insurance/cash
   - Create `PharmacyDispense` + `PharmacyDispenseItem` + `PharmacyDispenseAllocation`

2. **Build Pricing Policy Admin UI**
   - `/admin/pharmacy/roles/policies`
   - CRUD for `PharmacyRolePolicy`
   - Toggle switches for each permission

3. **Update Formulary Search**
   - Make it mandatory for new prescriptions
   - Show warnings if drug not in formulary

### Phase 3: Legacy Deprecation (Weeks 5-6)
**Objective:** Switch to new system, archive legacy

1. **Update prescriptions to use pharmacy_drug_id**
   - Batch update: `UPDATE prescriptions SET pharmacy_drug_id = (SELECT id FROM pharmacy_drug WHERE ...) WHERE medication_name = ...`

2. **Add read-only flag to legacy inventory**
   - Keep `medications` table but mark as "archived"
   - Redirect legacy UI to new pharmacy UI

3. **Final validation**
   - All new prescriptions use `pharmacy_drug_id`
   - Stock movements use `PharmacyStockLedger`
   - Cost prices hidden from non-admin roles

### Phase 4: Reports & Audit (Weeks 7-8)
**Objective:** Complete reporting, ensure auditability

1. **Stock Ledger Reports**
   - By drug, by store, by date range
   - Running balance calculation

2. **Profit/Margin Reports**
   - Only visible to roles with `can_view_margin`

3. **Controlled Drugs Audit Trail**
   - Complete the register with running balances

---

## 4. BACKWARD COMPATIBILITY NOTES

| Item | Strategy |
|------|----------|
| Existing prescriptions | Keep as-is; read `medication_name` for display |
| Existing stock items | Keep in sync until migration complete |
| Billing integration | `PharmacyDispense` links to encounter/invoice |
| Insurance claims | Use `payment_type` field on dispense |
| Reports | Union queries across both systems during transition |

---

## 5. FILE PATHS REFERENCE

### Models
- `app/models/pharmacy_models.py` - Ghana pharmacy models
- `app/models/inventory_models.py` - Legacy inventory models  
- `app/models/encounter_models.py` - Prescription model

### Routers
- `app/routers/pharmacy_ghana_api.py` - API endpoints
- `app/routers/pharmacy_ghana_ui_routes.py` - UI routes
- `app/routers/inventory_api.py` - Legacy routes

### Services
- `app/services/pharmacy_fefo.py` - FEFO logic

### Templates
- `app/templates/pharmacy_ghana/*.html` - Ghana pharmacy
- `app/templates/inventory/*.html` - Legacy inventory
- `app/templates/ancillary/prescription_detail.html` - Prescription

### Permissions
- `app/routers/role_permissions_api.py` - Role management
- `app/models/pharmacy_models.py:PharmacyRolePolicy` - Pharmacy policies
