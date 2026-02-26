# Pharmacy Module - Quick Admin Guide

This guide covers the core pharmacy workflows in the LHIMS system.

## 1. Master Data Setup

### Creating Dosage Forms
1. Navigate to Pharmacy → Formulations → Dosage Forms
2. Add common forms: Tablet, Capsule, Syrup, Injection, IV infusion, etc.

### Creating Formulations (Drugs)
1. Navigate to Pharmacy → Formulations → Drugs
2. Create each formulation with:
   - **Item Code**: Unique identifier (e.g., AMX500CAP)
   - **Generic Name**: Active ingredient (e.g., Amoxicillin)
   - **Brand Name**: Optional trade name
   - **Dosage Form**: Select from dropdown
   - **Strength**: Value + unit (e.g., 500 mg)
   - **Route**: PO, IV, IM, etc.
   - **Controlled**: Mark if requires special handling

### Creating Stores
1. Navigate to Pharmacy → Settings → Stores
2. Add locations: Main Pharmacy, Ward Store, OPD Dispensary

### Creating Suppliers
1. Navigate to Pharmacy → Settings → Suppliers
2. Add supplier details for stock intake

## 2. Receiving Stock

### Stock-In Process
1. Navigate to Pharmacy → Stock-In
2. Select store and supplier
3. Search for drug/formulation
4. Enter:
   - Batch number
   - Expiry date
   - Quantity received
   - Unit cost (hidden from regular staff)
   - Selling price
5. Submit - creates batch and ledger entry

### Key Concepts
- **Batches**: Each stock intake creates a batch with unique number and expiry
- **FEFO**: First Expiry First Out - system allocates from earliest expiry
- **Ledger**: Immutable record of all stock movements

## 3. Prescribing (Clinical)

### Doctor Workflow
1. Open patient encounter (OPD or IPD)
2. Navigate to Prescriptions section
3. Click "Add Prescription"
4. **Search formulary**: Type drug name, select from dropdown
   - Must select specific formulation (no free text)
   - Shows strength, dosage form, route
5. Enter:
   - Dosage (e.g., 500mg)
   - Frequency (e.g., twice daily)
   - Duration (e.g., 7 days)
   - Quantity (optional)
   - Instructions (optional)
6. Submit - validates drug interactions
7. If interactions detected:
   - CONTRAINDICATED: Blocked
   - MAJOR: Warning with confirmation
   - MODERATE/MINOR: Info only

### Interaction Checking
- Checks patient's prescriptions (last 90 days)
- Blocks contraindicated combinations
- Warns on major interactions
- Reference data seeded for Ghana-relevant drugs

## 4. Dispensing (Pharmacy)

### Pharmacist Workflow
1. Navigate to Pharmacy → Dispense
2. Enter patient ID to load pending prescriptions
3. For each prescription:
   - Verify prescription details
   - Check stock availability
4. Add items to dispense
5. Click "Allocate" - FEFO assigns batches
6. Review allocated batches
7. Click "Finalize" - stock deducted, receipt printed

### Key Features
- **FEFO Allocation**: Automatically selects earliest expiry batches
- **Stock Validation**: Prevents dispensing more than available
- **Controlled Drugs**: Requires special permission
- **Interaction Check**: Final check before dispensing

## 5. Returns & Write-Offs

### Patient Returns
1. Locate original dispense
2. Click "Return" to restock
3. Stock returned to inventory (new batch or existing)
4. Ledger entry: RETURN

### Write-Offs (Expired/Damaged)
1. Navigate to Pharmacy → Write-Off
2. Select batch
3. Choose type: EXPIRED or DAMAGED
4. Enter quantity and reason
5. **Approval Required**:
   - Admin/Head of Pharmacy: Auto-approved
   - Regular Staff: Requires approved_by user ID
6. Ledger entry: WRITEOFF_EXPIRED or WRITEOFF_DAMAGED

## 6. Reports

### Available Reports
1. **Near-Expiry**: Batches expiring within N days
   - Path: `/pharmacy/ghana/reports/near-expiry`
   - Filter by store, days
   
2. **Stock Ledger**: Full movement history
   - Path: `/pharmacy/ghana/reports/stock-ledger`
   - Filter by store, drug, date range, movement type
   - Shows running balance per drug

3. **Controlled Register**: Dispensing of controlled drugs
   - Path: `/pharmacy/ghana/reports/controlled-register`
   - Filter by date range, store

4. **Pharmacy Revenue**: Financial summary
   - Path: `/reports/pharmacy`
   - Revenue, frequently prescribed drugs

## 7. Role Permissions

### Configure in Pharmacy → Settings → Role Policies

| Role | View Cost | Edit Price | Adjust Stock | Approve | Dispense Controlled |
|------|-----------|------------|--------------|---------|---------------------|
| Admin | ✓ | ✓ | ✓ | ✓ | ✓ |
| Head of Pharmacy | ✓ | ✓ | ✓ | ✓ | ✓ |
| Pharmacy Staff | ✗ | ✗ | ✗ | ✗ | ✗ |
| Doctor | - | - | - | - | - |

## 8. Database Schema

### Key Tables
- `pharmacy_dosage_form` - Dosage forms
- `pharmacy_drug` - Formulations
- `pharmacy_batch` - Stock batches
- `pharmacy_stock_ledger` - Movement history (immutable)
- `pharmacy_dispense` - Dispense transactions
- `pharmacy_dispense_item` - Items in each dispense
- `pharmacy_dispense_allocation` - Batch allocations
- `pharmacy_drug_interaction` - Interaction rules
- `pharmacy_role_policy` - Role permissions

### Movement Types (Ledger)
- STOCK_IN - Received from supplier
- DISPENSE - Patient dispense
- RETURN - Patient return
- WRITEOFF_EXPIRED - Expired stock
- WRITEOFF_DAMAGED - Damaged stock
- ADJUSTMENT - Manual adjustment

## 9. Seeding Initial Data

Run the seed script to populate initial data:
```bash
python scripts/seed_pharmacy_ghana.py
```

This creates:
- Standard dosage forms
- Default store and supplier
- Sample formulations (15 drugs)
- Drug interactions (12 pairs)
- Role policies
