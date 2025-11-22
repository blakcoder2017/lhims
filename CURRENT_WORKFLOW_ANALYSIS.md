# Current Workflow Analysis

## 📋 **CURRENT FLOW (Before OPD/IPD Integration)**

### **For New Patients:**

```
1. Patient Arrives
   ↓
2. Front Office: Register Patient
   - Enter demographics
   - Select payment mechanism (Cash/NHIS/Private Insurance)
   - System generates patient_number (DGMS000001)
   - Auto-redirects to Triage page
   ↓
3. Front Office/Nurse: Record Vital Signs
   - Enter temperature, BP, pulse, SpO2, weight, height
   - System calculates BMI
   - Click "Save Vital Signs"
   - Redirects to Patient Records page
   ↓
4. Front Office: Create Appointment (Optional)
   - Select department, appointment type
   - Assign clinician (optional)
   - Status: "Scheduled"
   ↓
5. Front Office: Check-In Patient
   - Click "Check In" button
   - Status changes to "Checked In"
   - Patient appears in doctor queue
   ↓
6. Doctor: Create Encounter
   - From queue or patient search
   - Click "New Encounter"
   - System checks:
     ✓ Vitals recorded (today)
     ✓ Patient checked in
     ✓ Payment made (for cash patients)
   - Fill encounter form:
     * Chief Complaint
     * HPI, PMH, Allergies, Medications
     * Physical Examination
     * Assessment & Diagnoses
     * Treatment Plan
   - Click "Save Encounter"
   ↓
7. Doctor: Place Orders
   - Lab Orders
   - Radiology Orders
   - Prescriptions
   ↓
8. Ancillary Staff: Fulfill Orders
   - Lab: Enter results
   - Pharmacy: Dispense medications
   - Radiology: Complete studies
   ↓
9. Doctor: Complete Encounter
   - Review all documentation
   - Click "Complete Encounter"
   - System auto-generates charges
   ↓
10. Finance: Generate Invoice & Process Payment
    - Charges aggregated automatically
    - Process payment
    - Generate receipt
```

### **For Returning Patients:**

```
1. Front Office: Search Patient
   - Search by name, National ID, or phone
   - Select patient from results
   ↓
2. Front Office: Start New Visit (Current Implementation)
   - Click "Start New Visit" button
   - System creates NEW consultation charge
   - Redirects to Triage page with ?new_visit=true
   ↓
3. Front Office/Nurse: Record Vital Signs
   - Enter vitals for this visit
   - Save vitals
   ↓
4. Front Office: Create Appointment & Check-In
   - Create appointment
   - Check in patient
   ↓
5. Doctor: Create Encounter
   - Same as new patient flow
   - System verifies payment for THIS visit
   ↓
6-10. Same as new patient (Orders → Fulfillment → Complete → Billing)
```

---

## 🔄 **CURRENT SYSTEM CHARACTERISTICS**

### **What Works Now:**

1. ✅ **Patient Registration**
   - New patient registration
   - Returning patient search
   - Payment mechanism selection

2. ✅ **Triage & Vital Signs**
   - Record vitals
   - BMI calculation
   - Triage level assignment

3. ✅ **Appointment Management**
   - Create appointments
   - Check-in functionality
   - Queue management

4. ✅ **Encounter Creation**
   - Full clinical documentation
   - Diagnosis selection (multi-select)
   - Order placement (Lab/Radiology/Prescriptions)

5. ✅ **Payment Verification**
   - Checks if consultation fee paid (cash patients)
   - Creates charges automatically
   - Links charges to encounters

6. ✅ **Billing**
   - Auto-generates charges
   - Aggregates charges per encounter
   - Invoice generation

### **Current Limitations:**

1. ❌ **No OPD Visit Tracking**
   - No `opd_number` for outpatient visits
   - Cannot track multiple visits per day
   - No visit-level billing aggregation

2. ❌ **No Clear OPD/IPD Separation**
   - Encounters don't distinguish OPD vs IPD
   - Billing not separated by visit type
   - Reporting doesn't separate OPD/IPD

3. ❌ **Visit Continuity**
   - No way to link multiple encounters to same visit
   - Each encounter is standalone
   - Difficult to track visit-to-visit history

4. ❌ **Billing Aggregation**
   - Charges linked to encounters only
   - No visit-level billing summary
   - Cannot see "total for this visit"

---

## 🆕 **NEW FLOW (After OPD/IPD Integration)**

### **For New Patients (OPD):**

```
1. Patient Arrives
   ↓
2. Front Office: Register Patient
   - Enter demographics
   - Select payment mechanism
   - System generates patient_number
   ↓
3. Front Office: Start OPD Visit ⭐ NEW
   - Click "Start New Visit" button
   - System creates OPDVisit record
   - Generates opd_number (OPD-2024-0001)
   - Creates consultation charge (if cash)
   - Links charge to OPD visit
   - Redirects to Triage page
   ↓
4. Front Office/Nurse: Record Vital Signs
   - Enter vitals
   - Save vitals
   ↓
5. Front Office: Create Appointment & Check-In
   - Create appointment (optional)
   - Check in patient
   ↓
6. Doctor: Create Encounter ⭐ UPDATED
   - System auto-links to active OPD visit
   - OR doctor selects OPD visit
   - Validation ensures:
     ✓ OPD visit exists and is active
     ✓ Payment verified (cash patients)
   - Fill encounter form
   - Encounter linked to opd_visit_id
   ↓
7. Doctor: Place Orders
   - Orders can link to OPD visit (optional)
   - Orders still link to encounter (required)
   ↓
8. Ancillary Staff: Fulfill Orders
   - Same as before
   ↓
9. Doctor: Complete Encounter
   - Complete encounter
   - Charges aggregated under OPD visit
   ↓
10. Finance: Generate Invoice
    - Invoice linked to OPD visit
    - All charges for visit aggregated
    - Process payment
    ↓
11. Front Office: Complete OPD Visit ⭐ NEW
    - Mark OPD visit as "completed"
    - Visit closed
```

### **For Returning Patients (OPD):**

```
1. Front Office: Search Patient
   - Find existing patient
   ↓
2. Front Office: Start New OPD Visit ⭐ NEW
   - Click "Start New Visit"
   - System creates NEW OPDVisit
   - Generates NEW opd_number (OPD-2024-0002)
   - Creates NEW consultation charge
   - Links to patient_number
   - Redirects to Triage
   ↓
3-11. Same as new patient flow
```

### **For IPD (Inpatient):**

```
1. Patient Arrives (or from OPD)
   ↓
2. Doctor/Nurse: Admit Patient
   - Select ward and bed
   - System creates Admission record
   - Generates admission_number
   - Creates deposit charge (if cash)
   ↓
3. Nurse: Initial Assessment
   - Record vitals
   - Admission note
   ↓
4. Doctor: Create Encounter ⭐ UPDATED
   - System links to admission_id
   - Validation ensures:
     ✓ Admission exists and status = "admitted"
   - Fill encounter form
   - Encounter linked to admission_id
   ↓
5. Daily Monitoring
   - Multiple encounters per admission
   - Each linked to same admission_id
   ↓
6. Orders & Billing
   - Orders link to admission
   - Charges aggregated per admission
   ↓
7. Doctor: Discharge Patient
   - Generate discharge summary
   - Final billing calculated
   - Admission status = "discharged"
```

---

## 🔀 **KEY DIFFERENCES: Current vs New**

| Aspect | Current Flow | New Flow (OPD/IPD) |
|--------|-------------|-------------------|
| **Visit Tracking** | ❌ No visit tracking | ✅ OPD visits tracked with `opd_number` |
| **Encounter Linkage** | Links to `appointment_id` only | Links to `opd_visit_id` OR `admission_id` |
| **Billing Aggregation** | Per encounter | Per OPD visit or IPD admission |
| **Payment Verification** | Checks recent charges | Checks OPD visit payment status |
| **Visit History** | Encounter history only | OPD visit history + encounter history |
| **Multiple Visits/Day** | ❌ Not supported | ✅ Each visit has unique `opd_number` |
| **Returning Patient** | Creates new charge | Creates new OPD visit + charge |
| **IPD Support** | Basic admission tracking | Full IPD workflow with admission linking |

---

## 📊 **CURRENT STATE SUMMARY**

### **✅ What's Implemented (Backend):**

1. ✅ OPD Visit model and database structure
2. ✅ OPD CRUD operations
3. ✅ OPD API endpoints
4. ✅ Encounter validation (requires OPD/IPD link)
5. ✅ Auto-linking OPD visits from appointments
6. ✅ Billing models updated (ready for OPD/IPD links)

### **⏳ What's Pending (UI/Integration):**

1. ⏳ "Start New Visit" UI button and route
2. ⏳ Patient records page showing OPD visits
3. ⏳ Encounter form auto-populating `opd_visit_id`
4. ⏳ OPD visit completion workflow
5. ⏳ Data migration for existing encounters
6. ⏳ Reporting with OPD/IPD separation

---

## 🎯 **CURRENT WORKFLOW STATUS**

### **Working Right Now:**

- ✅ Patient registration
- ✅ Triage and vital signs
- ✅ Appointment creation and check-in
- ✅ Encounter creation (with payment verification)
- ✅ Order placement
- ✅ Billing and invoicing

### **Not Yet Integrated:**

- ❌ OPD visit creation in UI
- ❌ OPD visit display in patient records
- ❌ Encounter form showing OPD context
- ❌ Visit-level billing aggregation
- ❌ OPD/IPD reporting

---

## 🚀 **MIGRATION PATH**

### **Current System:**
- Encounters exist without OPD/IPD links
- Billing works at encounter level
- No visit tracking

### **After Migration:**
- New encounters require OPD/IPD link
- Existing encounters can be migrated retroactively
- Billing aggregates at visit level
- Full visit history tracking

### **Backward Compatibility:**
- Existing encounters remain valid (nullable fields)
- Gradual migration possible
- No breaking changes to current workflow

---

## 📝 **NEXT STEPS TO COMPLETE INTEGRATION**

1. **Run Database Migration**
   ```bash
   alembic upgrade head
   ```

2. **Create "Start New Visit" UI**
   - Add button to patient records page
   - Create route to create OPD visit
   - Redirect to triage with OPD visit context

3. **Update Encounter Form**
   - Auto-detect active OPD visit
   - Pre-populate `opd_visit_id`
   - Show OPD visit context

4. **Update Patient Records**
   - Display OPD visit history
   - Show active OPD visit
   - Link encounters to visits

5. **Data Migration**
   - Migrate existing encounters
   - Create OPD visits retroactively
   - Link encounters to visits

---

**Last Updated:** 2025-01-15  
**Status:** Backend Complete, UI Integration Pending

