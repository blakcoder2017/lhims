# Feature Implementation Summary

## Completed Features ✅

### 1. Doctor's Dashboard - Current Admission Cases
**Status:** ✅ **COMPLETED**

- Added current admission cases to Doctor's Dashboard
- Displays: Admission number, Patient name, Ward, Bed, Admission date, Days stayed, Diagnosis, Status
- Links to admission detail and encounter pages
- Shows up to 10 admissions with link to view all

**Files Modified:**
- `app/routers/doctor_api.py`: Added current admissions query with stay days calculation
- `app/templates/doctor/dashboard.html`: Added "Current Admission Cases" section

---

### 2. Enhanced Discharge Form
**Status:** ✅ **COMPLETED**

- Added Discharge Status enum: Normal, Death, Referral
- Added discharge diagnosis field (auto-filled from encounter if available)
- Added discharge notes field for instructions and follow-up care
- Created separate discharge form page (`/ipd/admissions/{id}/discharge-form`)
- Updated discharge route to capture and save discharge information

**Files Modified:**
- `app/models/ipd_models.py`: Added `DischargeStatus` enum and fields (`discharge_status`, `discharge_diagnosis`, `discharge_notes`)
- `app/schemas/ipd_schemas.py`: Added discharge fields to `AdmissionUpdate` schema
- `app/routers/ipd_ui_routes.py`: Added `discharge_form` route and updated `discharge_admission` to capture discharge info
- `app/templates/ipd/discharge_form.html`: **NEW** - Discharge form with status, diagnosis, notes
- `app/templates/ipd/admission_detail.html`: Updated "Discharge Patient" button to link to discharge form

---

## Remaining Features 📋

### 3. Patient Information Editing
**Status:** ❌ **PENDING**

**Requirements:**
- Allow editing patient information (name, DOB, gender, contact info, insurance details)
- Accessible from patient records page
- Role-based access (Admin, Front Office)
- Audit trail for changes

**Implementation Needed:**
- Add `PatientUpdate` schema to `app/schemas/patient_schemas.py`
- Add `update_patient` function to `app/crud/patient_crud.py`
- Add GET/POST routes to `app/routers/patient_api.py` or `app/routers/patient_records_api.py`
- Create/edit template: `app/templates/clinical/edit_patient.html`
- Add "Edit Patient" button to `app/templates/clinical/patient_records.html`

---

### 4. Refund Functionality (Management Only)
**Status:** ❌ **PENDING**

**Requirements:**
- Refund payments (by Management/Admin only)
- Link refunds to original payment/invoice
- Track refund reason and approval
- Generate refund receipt

**Implementation Needed:**
- Add `Refund` model to `app/models/billing_models.py`
- Add `RefundStatus` enum (PENDING, APPROVED, REJECTED, PROCESSED)
- Add `create_refund`, `approve_refund`, `process_refund` functions to `app/crud/billing_crud.py`
- Add refund routes to `app/routers/billing_api.py`
- Create refund templates:
  - `app/templates/billing/create_refund.html`
  - `app/templates/billing/refunds_list.html`
  - `app/templates/billing/refund_detail.html`
- Add "Refunds" menu to sidebar (Management/Admin only)

---

### 5. Medical Report for Patient Transfers
**Status:** ❌ **PENDING**

**Requirements:**
- Generate medical report when patient is transferred to another facility
- Include: Patient demographics, Admission details, Diagnosis, Treatment summary, Vitals history, Medications, Lab/Radiology results
- Exportable as PDF
- Print-friendly format

**Implementation Needed:**
- Create `generate_transfer_medical_report` function in `app/services/report_service.py` (or new file)
- Add route `GET /ipd/admissions/{id}/transfer-medical-report` to `app/routers/ipd_ui_routes.py`
- Create template: `app/templates/reports/transfer_medical_report.html`
- Add "Generate Medical Report" button to transfer form
- Consider using `weasyprint` or `reportlab` for PDF generation

---

### 6. IPD Billing - Bed Fee (One-time vs Daily)
**Status:** ❌ **PENDING**

**Requirements:**
- Clarify bed fee billing logic:
  - **One-time fee**: Charge once when patient is admitted to bed
  - **Daily fee**: Charge per day for bed occupancy (current implementation)
- Add configuration option to choose between one-time or daily
- Update billing logic accordingly

**Current Implementation:**
- `app/services/ipd_billing_service.py`: Currently calculates bed charges as **daily charges** based on days stayed
- Bed has `charge_per_day` field

**Implementation Needed:**
- Add `billing_type` enum (ONE_TIME, DAILY) to `Bed` model or create `BedBillingConfig` table
- Update `calculate_ward_bed_charges` in `app/services/ipd_billing_service.py` to handle both types
- If one-time: Charge once on admission (in `create_admission` route)
- If daily: Continue current logic (charge per day on discharge/preparation)

---

### 7. Insurance Price List
**Status:** ❌ **PENDING**

**Requirements:**
- Manage insurance price lists (NHIS, Private Insurance)
- Different prices for same service based on insurance provider
- Link services to insurance-specific prices
- Use insurance price list when creating charges for insurance patients

**Implementation Needed:**
- Create `InsurancePriceList` model in `app/models/billing_models.py`:
  - Fields: `insurance_provider`, `service_type`, `service_code`, `price`, `effective_date`, `expiry_date`
- Create CRUD functions in `app/crud/billing_crud.py`:
  - `create_insurance_price`, `get_insurance_price`, `get_insurance_prices_by_provider`, `update_insurance_price`
- Create routes in `app/routers/billing_api.py`:
  - `GET /billing/insurance-prices` - List all insurance prices
  - `GET /billing/insurance-prices/{provider}` - Prices for specific provider
  - `POST /billing/insurance-prices` - Create/Update price
  - `GET /billing/insurance-prices/manage` - UI for managing prices
- Create template: `app/templates/billing/insurance_prices.html`
- Update charge creation logic to use insurance prices:
  - In `app/services/charge_automation.py`: Check if patient has insurance, use insurance price if available
- Add "Insurance Price Lists" menu to sidebar (Finance/Admin)

---

## Database Migrations Required 📦

1. **Discharge Status Fields** (for Admission model):
   ```sql
   CREATE TYPE dischargestatus AS ENUM ('normal', 'death', 'referral');
   ALTER TABLE admissions ADD COLUMN discharge_status dischargestatus;
   ALTER TABLE admissions ADD COLUMN discharge_diagnosis TEXT;
   ALTER TABLE admissions ADD COLUMN discharge_notes TEXT;
   ```

2. **Refund Model** (if implemented):
   ```sql
   CREATE TABLE refunds (
       id SERIAL PRIMARY KEY,
       payment_id INTEGER REFERENCES payments(id),
       invoice_id INTEGER REFERENCES invoices(id),
       amount NUMERIC(10, 2) NOT NULL,
       reason TEXT,
       status refundstatus NOT NULL,
       requested_by_id INTEGER REFERENCES users(id),
       approved_by_id INTEGER REFERENCES users(id),
       processed_by_id INTEGER REFERENCES users(id),
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP,
       is_active BOOLEAN DEFAULT TRUE
   );
   ```

3. **Insurance Price List** (if implemented):
   ```sql
   CREATE TABLE insurance_price_lists (
       id SERIAL PRIMARY KEY,
       insurance_provider VARCHAR(100) NOT NULL,
       service_type VARCHAR(50) NOT NULL,
       service_code VARCHAR(50),
       price NUMERIC(10, 2) NOT NULL,
       effective_date DATE NOT NULL,
       expiry_date DATE,
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP,
       is_active BOOLEAN DEFAULT TRUE
   );
   ```

4. **Bed Billing Type** (if implemented):
   ```sql
   ALTER TABLE beds ADD COLUMN billing_type VARCHAR(20) DEFAULT 'daily';
   -- or create separate billing_config table
   ```

---

## Next Steps 🚀

### Priority 1 (Critical):
1. ✅ **Doctor's Dashboard - Current Admissions** - DONE
2. ✅ **Enhanced Discharge Form** - DONE
3. ⏳ **Patient Information Editing** - Should be quick to implement

### Priority 2 (Important):
4. ⏳ **IPD Billing - Bed Fee Clarification** - Need user clarification on one-time vs daily
5. ⏳ **Medical Report for Transfers** - Important for patient care continuity

### Priority 3 (Nice to have):
6. ⏳ **Refund Functionality** - Management/Admin feature
7. ⏳ **Insurance Price List** - Billing optimization

---

## Notes 📝

- **IPD Billing Days Calculation**: The system already automatically calculates days stayed. Current implementation in `app/services/ipd_billing_service.py` calculates days from admission date to discharge date (or current date if still admitted).
- **Bed Fee**: Currently implemented as daily charges. Need user clarification on whether bed fee should be:
  - **One-time**: Charge once when admitted (simpler, but less accurate for longer stays)
  - **Daily**: Charge per day (current implementation, more accurate for billing)
- **Medical Report**: Should be comprehensive and include all relevant clinical information for continuity of care at receiving facility.

