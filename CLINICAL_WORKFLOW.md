# 🏥 Clinical Workflow Guide - When Doctors See Patients

## Overview

This document explains the complete workflow from patient arrival to doctor consultation, including when and how doctors access patient information.

---

## 📋 Complete Patient Journey

### Step 1: Patient Arrival & Registration
**Role:** Front Office Staff  
**Action:** Register new patient or search existing patient

1. Navigate to **Front Office → Patient Registration**
2. Enter patient demographics (name, DOB, gender, National ID, contact)
3. Complete financial screening (Cash, NHIS, Private Insurance)
4. Click **"Register Patient"**
5. **→ Auto-redirects to Triage page**

---

### Step 2: Triage & Vital Signs
**Role:** Front Office Staff or Nurse  
**Action:** Record vital signs

1. After registration, you're automatically on the Triage page
2. Enter vital signs:
   - Temperature (°C)
   - Blood Pressure (mmHg)
   - Notes (optional)
3. Click **"Save Vital Signs"**
4. **→ Redirects to Patient Records page**

---

### Step 3: Appointment Scheduling
**Role:** Front Office Staff  
**Action:** Create appointment for patient

1. From Patient Records or Queue page
2. Navigate to **Front Office → Appointment & Queue**
3. Click **"Create Appointment"** or use the appointment form
4. Fill in:
   - Patient
   - Department
   - Appointment Type (Walk-In, Scheduled, Emergency, Follow-Up)
   - Scheduled Date & Time
   - Chief Complaint
   - Priority (1-10)
   - Assigned Clinician (optional)
5. Click **"Create Appointment"**
6. **→ Appointment appears in queue with status "Scheduled"**

---

### Step 4: Check-In
**Role:** Front Office Staff  
**Action:** Check patient in when they arrive

1. Navigate to **Front Office → Appointment & Queue**
2. Find the patient's appointment in the queue
3. Click **"Check In"** button
4. **→ Appointment status changes to "Checked In"**
5. **→ Patient is now visible to doctors in the queue**

---

### Step 5: Doctor Sees Patient Information ⭐
**Role:** Clinician (Doctor/Nurse)  
**Action:** Access patient information and start encounter

#### Option A: From Appointments Queue
1. Navigate to **Appointments** (in sidebar for Clinicians)
2. View today's appointments
3. Find patient with status "Checked In" or "In Progress"
4. Click **"View"** button
5. **→ Opens Patient Records page**

#### Option B: From Pending Encounters
1. Navigate to **Clinical Services → Pending Encounters**
2. View all in-progress encounters for today
3. Click **"View/Edit"** on an encounter
4. **→ Opens Encounter page with full patient information**

#### Option C: Direct Patient Search
1. Navigate to **Clinical Services → Patient EHR Search**
2. Search by name, National ID, or phone number
3. Click on patient from results
4. Click **"View Records"**
5. **→ Opens Patient Records page with complete history**

---

### Step 6: Clinical Encounter Documentation
**Role:** Clinician (Doctor)  
**Action:** Document encounter and create orders

#### 6.1 View Patient Information
When you open a patient record, you see:
- **Demographics:** Name, age, gender, contact info
- **Medical History:** All previous encounters
- **Vital Signs History:** All recorded vital signs
- **Timeline:** Combined chronological view
- **Current Appointment:** If patient has an active appointment

#### 6.2 Create New Encounter
1. From Patient Records page, click **"New Encounter"**
2. Or navigate directly: `/patients/{patient_id}/encounters/new`
3. Fill in encounter details:
   - **Chief Complaint:** Patient's main reason for visit
   - **History of Present Illness (HPI):** Detailed history
   - **Past Medical History:** Previous conditions
   - **Allergies:** Known allergies
   - **Current Medications:** Current medications
   - **Physical Examination:** Examination findings
   - **Assessment:** Clinical assessment/diagnosis
   - **Plan:** Treatment plan
   - **Primary Diagnosis:** ICD-10 code and description
   - **Secondary Diagnoses:** Additional diagnoses (optional)

#### 6.3 Add Orders
From the Encounter page, you can add:

**Lab Orders:**
- Click **"Add Lab Order"** in Lab Orders section
- Enter test name, type, priority, clinical indication
- Click **"Create Lab Order"**
- **→ Order appears in Lab dashboard (visible to Lab Staff and Clinicians)**

**Radiology Orders:**
- Click **"Add Radiology Order"** in Radiology Orders section
- Enter study type, body part, priority, clinical indication
- Click **"Create Radiology Order"**
- **→ Order appears in Radiology dashboard**

**Prescriptions:**
- Click **"Add Prescription"** in Prescriptions section
- Enter medication name, dosage, frequency, duration, quantity
- System checks for drug interactions automatically
- Click **"Create Prescription"**
- **→ Prescription appears in Pharmacy dashboard (visible to Pharmacy Staff and Clinicians)**

#### 6.4 Complete Encounter
1. Review all documentation
2. Ensure all orders are placed
3. Click **"Complete Encounter"**
4. **→ Encounter status changes to "Completed"**
5. **→ Charges are automatically created for billing**

---

### Step 7: Order Fulfillment

#### Lab Orders
**Role:** Lab Staff  
**Action:** Process lab orders and enter results

1. Navigate to **Ancillary Services → Laboratory (LIS)**
2. View pending lab orders
3. Click on an order to view details
4. Create sample record (optional)
5. Enter test results
6. Click **"Save Result"**
7. **→ Order status changes to "Completed"**
8. **→ Charge is automatically created**
9. **→ Clinician can now view results in Lab dashboard**

**Clinician View:**
- Navigate to **Ancillary Services → Laboratory (LIS)**
- View all lab orders (pending and completed)
- Click on an order to view details
- **Can view results but cannot enter them** (only Lab Staff can enter results)

#### Prescriptions
**Role:** Pharmacy Staff  
**Action:** Dispense medications

1. Navigate to **Ancillary Services → Pharmacy (PhIS)**
2. View pending prescriptions
3. Click on a prescription to view details
4. System checks:
   - Drug interactions
   - Formulary compliance
   - Stock availability
5. Click **"Dispense Medication"**
6. Enter batch number, expiry date, quantity
7. Click **"Confirm Dispensing"**
8. **→ Prescription status changes to "Dispensed"**
9. **→ Inventory is automatically updated**
10. **→ Charge is automatically created**

**Clinician View:**
- Navigate to **Ancillary Services → Pharmacy (PhIS)**
- View all prescriptions (pending and dispensed)
- Click on a prescription to view details
- **Can view prescription status but cannot dispense** (only Pharmacy Staff can dispense)

---

### Step 8: Billing & Payment
**Role:** Finance Staff or Front Office  
**Action:** Generate invoice and process payment

1. Navigate to **Finance & Reports → Billing & Payments**
2. Create new invoice or view existing
3. Link to encounter (charges are auto-added)
4. Review all charges
5. Process payment
6. **→ Invoice status updates**
7. **→ Receipt generated**

---

## 🔑 Key Points: When Doctors See Patients

### ✅ Doctors Can See Patient Information:

1. **After Check-In:**
   - Patient appears in Appointments queue
   - Status: "Checked In" or "In Progress"
   - Doctor can click "View" to see patient records

2. **From Pending Encounters:**
   - All in-progress encounters for today
   - Direct access to encounter documentation
   - Full patient information available

3. **From Patient Search:**
   - Search by name, ID, or phone
   - View complete medical history
   - Create new encounter if needed

4. **From Order Dashboards:**
   - Lab dashboard: View pending/completed lab orders
   - Pharmacy dashboard: View pending/dispensed prescriptions
   - Radiology dashboard: View radiology orders

### ❌ Doctors Cannot:

- Register new patients (Front Office only)
- Check patients in (Front Office only)
- Enter lab results (Lab Staff only)
- Dispense medications (Pharmacy Staff only)
- Process payments (Finance/Front Office only)

### ✅ Doctors Can:

- View all patient medical records
- Create clinical encounters
- Place orders (Lab, Radiology, Prescriptions)
- View order status and results
- Document diagnoses and treatment plans
- Complete encounters

---

## 📊 Workflow Summary

```
Patient Arrives
    ↓
Front Office: Register Patient
    ↓
Front Office: Record Vital Signs (Triage)
    ↓
Front Office: Create Appointment
    ↓
Front Office: Check-In Patient ⭐ (Patient now visible to doctor)
    ↓
Doctor: View Patient from Queue or Search
    ↓
Doctor: Create Encounter & Document
    ↓
Doctor: Place Orders (Lab/Radiology/Prescriptions)
    ↓
Lab/Pharmacy Staff: Fulfill Orders
    ↓
Doctor: View Results (from dashboards)
    ↓
Doctor: Complete Encounter
    ↓
Finance: Generate Invoice & Process Payment
    ↓
Patient Discharged
```

---

## 🎯 Quick Reference

| Action | Who Can Do It | Where to Find It |
|--------|--------------|------------------|
| Register Patient | Front Office | Front Office → Patient Registration |
| Record Vitals | Front Office, Nurse | Front Office → Triage & Vitals |
| Create Appointment | Front Office | Front Office → Appointment & Queue |
| Check-In Patient | Front Office | Front Office → Appointment & Queue → Check In |
| View Appointments | Front Office, Clinician | Appointments (in sidebar) |
| View Patient Records | All Clinical Staff | Clinical Services → Patient EHR Search |
| Create Encounter | Clinician | Patient Records → New Encounter |
| Place Lab Order | Clinician | Encounter → Add Lab Order |
| View Lab Orders | Clinician, Lab Staff | Ancillary Services → Laboratory (LIS) |
| Enter Lab Results | Lab Staff Only | Lab Order Detail → Enter Result |
| Place Prescription | Clinician | Encounter → Add Prescription |
| View Prescriptions | Clinician, Pharmacy Staff | Ancillary Services → Pharmacy (PhIS) |
| Dispense Medication | Pharmacy Staff Only | Prescription Detail → Dispense |
| Generate Invoice | Finance, Front Office | Finance & Reports → Billing & Payments |

---

## 💡 Tips for Doctors

1. **Always check the queue first** - Patients who are checked in will appear there
2. **Use Patient Search** - For returning patients or to view complete history
3. **Check Pending Encounters** - See all your in-progress encounters for today
4. **Monitor Order Status** - Check Lab and Pharmacy dashboards to see when results are ready
5. **Complete encounters promptly** - This triggers billing and closes the visit

---

**Last Updated:** 2025-01-XX  
**Version:** 1.0

