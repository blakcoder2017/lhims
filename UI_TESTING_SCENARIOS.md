# LHIMS UI Testing Scenarios - Real Life Simulation

**Date**: February 8, 2026  
**Purpose**: Comprehensive UI testing with real-life scenarios  
**Status**: 🚀 **Ready for Testing**  
**Application**: http://localhost:8000

## 👥 Test Accounts Setup

### ✅ **Administrator Account**
```
Username: admin
Password: Admin123
Role: Admin
Access: All modules and functions
```

### ✅ **Doctor Account**
```
Username: doctor1
Password: Doctor123
Role: Doctor
Access: Clinical modules, patient records, prescriptions, procedures
```

### ✅ **Nurse Account**
```
Username: nurse1
Password: Nurse123
Role: Nurse
Access: Patient care, vitals, triage, medication administration
```

### ✅ **Front Office Account**
```
Username: frontdesk1
Password: Front123
Role: Front Office
Access: Patient registration, appointments, billing
```

### ✅ **Midwife Account**
```
Username: midwife1
Password: Midwife123
Role: Midwife
Access: Antenatal care, maternity, patient records
```

### ✅ **Lab Technician Account**
```
Username: labtech1
Password: Lab123
Role: Lab Technician
Access: Lab orders, sample processing, results entry
```

### ✅ **Pharmacist Account**
```
Username: pharm1
Password: Pharm123
Role: Pharmacist
Access: Pharmacy, prescriptions, drug dispensing
```

## 🏥 Real-Life Testing Scenarios

### ✅ **Scenario 1: Patient Registration & OPD Visit**

#### **Step 1: Front Office Registration**
1. **Login**: `frontdesk1` / `Front123`
2. **Navigate**: Patients → New Patient Registration
3. **Create Patient**:
   ```
   First Name: Ama
   Last Name: Mensah
   Date of Birth: 1990-05-15
   Gender: Female
   Phone: 0201234567
   Address: Accra, Ghana
   Payment Mechanism: NHIS
   NHIS Number: NHIS123456789
   ```
4. **Expected Result**: Patient created successfully, patient number generated

#### **Step 2: Appointment Booking**
1. **Navigate**: Appointments → Book Appointment
2. **Select Patient**: Ama Mensah
3. **Department**: General Practice
4. **Date**: Today
5. **Expected Result**: Appointment created successfully

#### **Step 3: Patient Check-in**
1. **Navigate**: Queue → OPD Queue
2. **Find Patient**: Ama Mensah
3. **Check-in**: Click check-in button
4. **Expected Result**: Patient moves to triage queue

#### **Step 4: Triage**
1. **Login**: `nurse1` / `Nurse123`
2. **Navigate**: Triage → Triage Queue
3. **Select Patient**: Ama Mensah
4. **Record Vitals**:
   ```
   BP: 120/80
   Temperature: 36.5
   Pulse: 72
   Respiratory Rate: 16
   Oxygen Saturation: 98%
   Weight: 65kg
   Height: 165cm
   ```
5. **Expected Result**: Vitals saved, patient moves to doctor queue

#### **Step 5: Doctor Consultation**
1. **Login**: `doctor1` / `Doctor123`
2. **Navigate**: Clinical → Doctor Queue
3. **Select Patient**: Ama Mensah
4. **Create Encounter**:
   ```
   Chief Complaint: Headache and fever
   History: Patient has been experiencing headache for 3 days
   Diagnosis: Malaria (uncomplicated)
   Treatment: Antimalarial medication
   ```
5. **Expected Result**: Encounter created, treatment plan documented

#### **Step 6: Prescription**
1. **Within Encounter**: Add Prescription
2. **Medication**: Artemether/Lumefantrine
3. **Dosage**: 4 tablets twice daily for 3 days
4. **Expected Result**: Prescription created successfully

#### **Step 7: Lab Order**
1. **Within Encounter**: Order Lab Test
2. **Test**: Full Blood Count (FBC)
3. **Priority**: Routine
4. **Expected Result**: Lab order created

#### **Step 8: Billing**
1. **Navigate**: Billing → Create Invoice
2. **Select Patient**: Ama Mensah
3. **Add Charges**:
   ```
   Consultation: 50 GHS
   Lab Test: 30 GHS
   Medication: 45 GHS
   ```
4. **Expected Result**: Invoice created with total 125 GHS

### ✅ **Scenario 2: Maternity Care Workflow**

#### **Step 1: Antenatal Registration**
1. **Login**: `midwife1` / `Midwife123`
2. **Navigate**: Maternity → Antenatal → New Antenatal Visit
3. **Select Patient**: Ama Mensah (or create pregnant patient)
4. **Record Antenatal Visit**:
   ```
   Visit Number: 1
   LMP: 2024-12-01
   EDD: 2025-09-08
   Gestational Age: 12 weeks
   Blood Pressure: 110/70
   Weight: 68kg
   Fundal Height: 12cm
   Fetal Heart Rate: 150 bpm
   ```
4. **Expected Result**: Antenatal visit recorded

#### **Step 2: Subsequent Antenatal Visits**
1. **Navigate**: Maternity → Antenatal Visits
2. **Select Patient**: Ama Mensah
3. **Create Follow-up Visit**:
   ```
   Visit Number: 2
   Gestational Age: 16 weeks
   Blood Pressure: 112/72
   Weight: 69kg
   Fundal Height: 16cm
   Fetal Heart Rate: 148 bpm
   ```
4. **Expected Result**: Follow-up visit recorded

#### **Step 3: Delivery Record**
1. **Navigate**: Maternity → Record Birth
2. **Select Mother**: Ama Mensah
3. **Record Delivery**:
   ```
   Delivery Date: 2025-09-08
   Delivery Type: Normal Vaginal Delivery
   Baby Name: Kofi Mensah
   Birth Weight: 3.2kg
   Apgar Score: 9/10
   Complications: None
   ```
4. **Expected Result**: Birth record created successfully

### ✅ **Scenario 3: Emergency Patient Workflow**

#### **Step 1: Emergency Registration**
1. **Login**: `frontdesk1` / `Front123`
2. **Navigate**: Emergency → Quick Registration
3. **Minimal Registration**:
   ```
   First Name: John (Emergency)
   Last Name: Doe
   Phone: 0234567890
   Chief Complaint: Chest pain
   ```
4. **Expected Result**: Emergency patient registered quickly

#### **Step 2: Emergency Triage**
1. **Login**: `nurse1` / `Nurse123`
2. **Navigate**: Emergency → Emergency Triage
3. **Assess Patient**:
   ```
   Triage Category: Emergency (Red)
   BP: 160/100
   Heart Rate: 110
   Oxygen Saturation: 92%
   Pain Scale: 8/10
   ```
4. **Expected Result**: Patient marked as emergency, immediate doctor notification

#### **Step 3: Emergency Treatment**
1. **Login**: `doctor1` / `Doctor123`
2. **Navigate**: Emergency → Emergency Cases
3. **Stabilize Patient**:
   ```
   Assessment: Acute myocardial infarction suspected
   Immediate Treatment: Aspirin, Nitroglycerin
   Plan: ECG, Cardiac enzymes, ICU admission
   ```
4. **Expected Result**: Emergency treatment documented

### ✅ **Scenario 4: Laboratory Workflow**

#### **Step 1: Lab Order Processing**
1. **Login**: `labtech1` / `Lab123`
2. **Navigate**: Laboratory → Lab Orders
3. **Find Order**: Ama Mensah - FBC
4. **Sample Collection**:
   ```
   Sample Type: Blood
   Collection Method: Venipuncture
   Collection Time: Now
   Barcode Generated: LAB-20250208-001
   ```
5. **Expected Result**: Sample collected and barcode generated

#### **Step 2: Sample Processing**
1. **Navigate**: Laboratory → Sample Processing
2. **Scan Barcode**: LAB-20250208-001
3. **Process Sample**:
   ```
   Status: Processing
   Machine: Hematology Analyzer
   Started At: Now
   ```
4. **Expected Result**: Sample processing started

#### **Step 3: Result Entry**
1. **Navigate**: Laboratory → Result Entry
2. **Find Sample**: LAB-20250208-001
3. **Enter Results**:
   ```
   WBC: 6.5 x10^9/L
   RBC: 4.2 x10^12/L
   Hemoglobin: 12.5 g/dL
   Platelets: 250 x10^9/L
   Normal Range: All within normal limits
   ```
4. **Expected Result**: Results saved, order marked as completed

### ✅ **Scenario 5: Pharmacy Workflow**

#### **Step 1: Prescription Processing**
1. **Login**: `pharm1` / `Pharm123`
2. **Navigate**: Pharmacy → Prescriptions
3. **Find Prescription**: Ama Mensah - Antimalarial
4. **Verify Prescription**:
   ```
   Medication: Artemether/Lumefantrine
   Dosage: 4 tablets twice daily
   Duration: 3 days
   Prescribed By: doctor1
   ```
5. **Expected Result**: Prescription verified

#### **Step 2: Medication Dispensing**
1. **Process Dispensing**:
   ```
   Quantity Dispensed: 24 tablets
   Batch Number: MAL001
   Expiry Date: 2026-12-31
   Dispensed By: pharm1
   Patient Instructions: Take with food
   ```
2. **Expected Result**: Medication dispensed, prescription marked as completed

#### **Step 3: Stock Update**
1. **Navigate**: Pharmacy → Inventory
2. **Update Stock**:
   ```
   Medication: Artemether/Lumefantrine
   Previous Stock: 100 tablets
   Dispensed: 24 tablets
   New Stock: 76 tablets
   ```
3. **Expected Result**: Inventory updated automatically

### ✅ **Scenario 6: Inpatient Admission**

#### **Step 1: Admission Order**
1. **Login**: `doctor1` / `Doctor123`
2. **Navigate**: IPD → Admit Patient
3. **Select Patient**: John Doe (Emergency)
4. **Admission Details**:
   ```
   Admission Type: Emergency
   Ward: Emergency Ward
   Bed: E-001
   Diagnosis: Acute MI
   Admitting Doctor: doctor1
   ```
5. **Expected Result**: Patient admitted successfully

#### **Step 2: Nursing Care**
1. **Login**: `nurse1` / `Nurse123`
2. **Navigate**: IPD → Patient Care
3. **Select Patient**: John Doe
4. **Record Nursing Care**:
   ```
   Vital Signs Monitoring: Every 2 hours
   Medication Administration: As prescribed
   IV Fluids: Normal Saline 500ml
   Patient Condition: Stable
   ```
5. **Expected Result**: Nursing care documented

#### **Step 3: Discharge Planning**
1. **Navigate**: IPD → Discharge Planning
2. **Discharge Summary**:
   ```
   Discharge Date: Tomorrow
   Condition: Improved
   Discharge Medications: Continue cardiac meds
   Follow-up: Cardiology clinic in 1 week
   ```
3. **Expected Result**: Discharge planned

### ✅ **Scenario 7: Procedure Management**

#### **Step 1: Procedure Scheduling**
1. **Login**: `doctor1` / `Doctor123`
2. **Navigate**: Procedures → Schedule Procedure
3. **Select Patient**: Ama Mensah
4. **Procedure Details**:
   ```
   Procedure: Appendectomy
   Type: Surgical
   Scheduled Date: Tomorrow
   Location: Operating Room 1
   Anesthesia: General
   Surgeon: doctor1
   ```
5. **Expected Result**: Procedure scheduled

#### **Step 2: Pre-operative Assessment**
1. **Navigate**: Procedures → Pre-op Assessment
2. **Assessment**:
   ```
   ASA Classification: ASA 1
   Airway: Mallampati 1
   Allergies: None
   Consent: Signed
   ```
3. **Expected Result**: Pre-op assessment completed

#### **Step 3: Procedure Documentation**
1. **Post-procedure Documentation**:
   ```
   Start Time: 10:00 AM
   End Time: 11:30 AM
   Findings: Acute appendicitis
   Complications: None
   Outcome: Successful
   ```
2. **Expected Result**: Procedure documented as completed

## 🔍 Pages to Test

### ✅ **Authentication Pages**
- [ ] Login Page (`/login`)
- [ ] Logout Functionality
- [ ] Password Reset (if available)

### ✅ **Dashboard Pages**
- [ ] Admin Dashboard (`/admin/dashboard`)
- [ ] Doctor Dashboard (`/doctor/dashboard`)
- [ ] Nurse Dashboard (`/nurse/dashboard`)
- [ ] Front Office Dashboard (`/front_office/dashboard`)
- [ ] Midwife Dashboard (`/midwife/dashboard`)
- [ ] Lab Dashboard (`/lab/dashboard`)
- [ ] Pharmacy Dashboard (`/pharmacy/dashboard`)

### ✅ **Patient Management Pages**
- [ ] Patient Registration (`/patients/register`)
- [ ] Patient Search (`/patients/search`)
- [ ] Patient Records (`/patients/{id}/records`)
- [ ] Patient Edit (`/patients/{id}/edit`)
- [ ] OPD Queue (`/queue/opd`)
- [ ] Emergency Queue (`/queue/emergency`)

### ✅ **Clinical Pages**
- [ ] Appointments (`/appointments`)
- [ ] Triage (`/triage`)
- [ ] Doctor Queue (`/doctor/queue`)
- [ ] Encounters (`/encounters`)
- [ ] Prescriptions (`/prescriptions`)
- [ ] Procedures (`/procedures`)

### ✅ **Maternity Pages**
- [ ] Antenatal Dashboard (`/midwife/antenatal/dashboard`)
- [ ] Antenatal Visits (`/midwife/antenatal/visits`)
- [ ] New Antenatal Visit (`/midwife/antenatal/new`)
- [ ] Maternity Ward (`/births/dashboard`)
- [ ] Birth Records (`/births/list`)
- [ ] Record Birth (`/births/create`)

### ✅ **Laboratory Pages**
- [ ] Lab Orders (`/lab/orders`)
- [ ] Sample Processing (`/lab/samples`)
- [ ] Result Entry (`/lab/results`)
- [ ] Lab Reports (`/lab/reports`)

### ✅ **Pharmacy Pages**
- [ ] Prescriptions (`/pharmacy/prescriptions`)
- [ ] Medication Dispensing (`/pharmacy/dispense`)
- [ ] Inventory (`/pharmacy/inventory`)
- [ ] Stock Management (`/pharmacy/stock`)

### ✅ **Billing Pages**
- [ ] Invoices (`/billing/invoices`)
- [ ] Payments (`/billing/payments`)
- [ ] NHIS Claims (`/billing/nhis`)
- [ ] Financial Reports (`/billing/reports`)

### ✅ **IPD Pages**
- [ ] Admissions (`/ipd/admissions`)
- [ ] Ward Management (`/ipd/wards`)
- [ ] Bed Management (`/ipd/beds`)
- [ ] Discharge (`/ipd/discharge`)

### ✅ **Radiology Pages**
- [ ] Radiology Orders (`/radiology/orders`)
- [ ] Image Management (`/radiology/images`)
- [ ] Reports (`/radiology/reports`)

## 🎯 Testing Checklist

### ✅ **Functional Testing**
- [ ] All login credentials work
- [ ] Role-based access control works
- [ ] All forms submit successfully
- [ ] Data saves correctly
- [ ] Search functions work
- [ ] Filters work properly
- [ ] Pagination works
- [ ] Export functions work

### ✅ **Data Integrity Testing**
- [ ] Patient records update correctly
- [ ] Lab orders link to patients
- [ ] Prescriptions link to encounters
- [ ] Billing links to services
- [ ] Maternity records link to mothers
- [ ] Timeline shows all events

### ✅ **Workflow Testing**
- [ ] Complete OPD workflow works
- [ ] Complete emergency workflow works
- [ ] Complete maternity workflow works
- [ ] Complete lab workflow works
- [ ] Complete pharmacy workflow works
- [ ] Complete IPD workflow works

### ✅ **UI/UX Testing**
- [ ] Pages load quickly
- [ ] Navigation is intuitive
- [ ] Forms are user-friendly
- [ ] Error messages are clear
- [ ] Success messages appear
- [ ] Responsive design works
- [ ] Print functions work

## 🚀 Getting Started

### ✅ **Step 1: Start Application**
```bash
cd /Users/macbookpro/Documents/seproject/python_projects/lhims
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### ✅ **Step 2: Access Application**
Open browser: http://localhost:8000

### ✅ **Step 3: Test Scenarios**
1. **Start with Scenario 1** (Patient Registration & OPD Visit)
2. **Progress through each scenario**
3. **Document any issues found**
4. **Test all user roles**
5. **Verify all pages work**

### ✅ **Step 4: Report Issues**
Document any issues found:
- Page not loading
- Form not submitting
- Data not saving
- Access denied errors
- UI/UX problems

---

**Status**: 🚀 **Ready for Comprehensive Testing**

All test accounts are set up and scenarios are documented. Start testing with the provided real-life scenarios to ensure the LHIMS system works perfectly!

---

*Testing Guide Created: February 8, 2026*  
*Application: http://localhost:8000*  
*Status: Ready for Testing*
