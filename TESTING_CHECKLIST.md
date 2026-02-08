# LHIMS UI Testing Checklist - Live Testing Session

**Date**: February 8, 2026  
**Session**: Live UI Testing  
**Application**: http://localhost:8000  
**Status**: 🧪 **In Progress**

## 🎯 **Testing Order & Progress**

### ✅ **Phase 1: Authentication & Basic Access**
- [ ] **Admin Login**: admin / Admin123
- [ ] **Doctor Login**: doctor1 / Doctor123  
- [ ] **Nurse Login**: nurse1 / Nurse123
- [ ] **Front Office Login**: frontdesk1 / Front123
- [ ] **Midwife Login**: midwife1 / Midwife123
- [ ] **Lab Tech Login**: labtech1 / Lab123
- [ ] **Pharmacist Login**: pharm1 / Pharm123

### ✅ **Phase 2: Patient Registration Workflow**
- [ ] **Front Office**: Register new patient
- [ ] **Patient Search**: Find existing patients
- [ ] **Appointment Booking**: Schedule appointments
- [ ] **Queue Management**: Check-in patients

### ✅ **Phase 3: Clinical Workflows**
- [ ] **Triage**: Record vitals
- [ ] **Doctor Consultation**: Create encounters
- [ ] **Prescriptions**: Order medications
- [ ] **Lab Orders**: Request tests
- [ ] **Procedures**: Schedule procedures

### ✅ **Phase 4: Maternity Care**
- [ ] **Antenatal Visits**: Record pregnancy care
- [ ] **Birth Records**: Document deliveries
- [ ] **Maternity Dashboard**: View maternity stats

### ✅ **Phase 5: Ancillary Services**
- [ ] **Laboratory**: Process samples and results
- [ ] **Pharmacy**: Dispense medications
- [ ] **Radiology**: Manage imaging studies
- [ ] **Billing**: Create invoices and payments

### ✅ **Phase 6: Inpatient Care**
- [ ] **Admissions**: Admit patients
- [ ] **Ward Management**: Manage beds
- [ ] **Nursing Care**: Document care
- [ ] **Discharge**: Process discharges

## 🧪 **Current Testing Session**

### 📋 **Test Scenario 1: Patient Registration & OPD Visit**

#### **Step 1: Front Office Login**
1. **Open Browser**: http://localhost:8000
2. **Login**: frontdesk1 / Front123
3. **Expected**: Successful login to Front Office dashboard
4. **Actual**: [To be filled during testing]

#### **Step 2: Patient Registration**
1. **Navigate**: Patients → New Patient Registration
2. **Fill Form**:
   ```
   First Name: Test
   Last Name: Patient
   Date of Birth: 1990-01-01
   Gender: Female
   Phone: 0200000000
   Address: Test Address, Accra
   Payment Mechanism: NHIS
   NHIS Number: TEST123456
   ```
3. **Expected**: Patient created successfully
4. **Actual**: [To be filled during testing]

#### **Step 3: Appointment Booking**
1. **Navigate**: Appointments → Book Appointment
2. **Select Patient**: Test Patient (just created)
3. **Department**: General Practice
4. **Date**: Today
5. **Expected**: Appointment created
6. **Actual**: [To be filled during testing]

#### **Step 4: Patient Check-in**
1. **Navigate**: Queue → OPD Queue
2. **Find Patient**: Test Patient
3. **Check-in**: Click check-in button
4. **Expected**: Patient moves to triage
5. **Actual**: [To be filled during testing]

### 📋 **Test Scenario 2: Clinical Workflow**

#### **Step 1: Nurse Login & Triage**
1. **Login**: nurse1 / Nurse123
2. **Navigate**: Triage → Triage Queue
3. **Select Patient**: Test Patient
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
5. **Expected**: Vitals saved, patient moves to doctor queue
6. **Actual**: [To be filled during testing]

#### **Step 2: Doctor Consultation**
1. **Login**: doctor1 / Doctor123
2. **Navigate**: Clinical → Doctor Queue
3. **Select Patient**: Test Patient
4. **Create Encounter**:
   ```
   Chief Complaint: Headache and fever
   History: Patient has been experiencing symptoms for 3 days
   Diagnosis: Malaria (uncomplicated)
   Treatment Plan: Antimalarial medication + rest
   ```
5. **Expected**: Encounter created successfully
6. **Actual**: [To be filled during testing]

#### **Step 3: Prescription Creation**
1. **Within Encounter**: Add Prescription
2. **Medication**: Artemether/Lumefantrine
3. **Dosage**: 4 tablets twice daily for 3 days
4. **Expected**: Prescription created
5. **Actual**: [To be filled during testing]

#### **Step 4: Lab Order**
1. **Within Encounter**: Order Lab Test
2. **Test**: Full Blood Count (FBC)
3. **Priority**: Routine
4. **Expected**: Lab order created
5. **Actual**: [To be filled during testing]

### 📋 **Test Scenario 3: Maternity Care**

#### **Step 1: Midwife Login**
1. **Login**: midwife1 / Midwife123
2. **Expected**: Successful login to Midwife dashboard
3. **Actual**: [To be filled during testing]

#### **Step 2: Antenatal Visit**
1. **Navigate**: Maternity → Antenatal Visits → New Antenatal Visit
2. **Select Patient**: Ama Mensah (existing test patient)
3. **Record Visit**:
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
4. **Expected**: Antenatal visit recorded
5. **Actual**: [To be filled during testing]

#### **Step 3: Birth Record**
1. **Navigate**: Maternity → Record Birth
2. **Select Mother**: Ama Mensah
3. **Record Delivery**:
   ```
   Delivery Date: 2025-09-08
   Delivery Type: Normal Vaginal Delivery
   Baby Name: Baby Test
   Birth Weight: 3.2kg
   Apgar Score: 9/10
   ```
4. **Expected**: Birth record created
5. **Actual**: [To be filled during testing]

### 📋 **Test Scenario 4: Laboratory Workflow**

#### **Step 1: Lab Tech Login**
1. **Login**: labtech1 / Lab123
2. **Expected**: Successful login to Lab dashboard
3. **Actual**: [To be filled during testing]

#### **Step 2: Lab Order Processing**
1. **Navigate**: Laboratory → Lab Orders
2. **Find Order**: Test Patient - FBC
3. **Sample Collection**:
   ```
   Sample Type: Blood
   Collection Method: Venipuncture
   Collection Time: Now
   ```
4. **Expected**: Sample collected, barcode generated
5. **Actual**: [To be filled during testing]

#### **Step 3: Result Entry**
1. **Navigate**: Laboratory → Result Entry
2. **Find Sample**: Test Patient sample
3. **Enter Results**:
   ```
   WBC: 6.5 x10^9/L
   RBC: 4.2 x10^12/L
   Hemoglobin: 12.5 g/dL
   Platelets: 250 x10^9/L
   Normal Range: All within normal limits
   ```
4. **Expected**: Results saved, order completed
5. **Actual**: [To be filled during testing]

### 📋 **Test Scenario 5: Pharmacy Workflow**

#### **Step 1: Pharmacist Login**
1. **Login**: pharm1 / Pharm123
2. **Expected**: Successful login to Pharmacy dashboard
3. **Actual**: [To be filled during testing]

#### **Step 2: Prescription Processing**
1. **Navigate**: Pharmacy → Prescriptions
2. **Find Prescription**: Test Patient - Antimalarial
3. **Verify & Dispense**:
   ```
   Quantity Dispensed: 24 tablets
   Batch Number: MAL001
   Dispensed By: pharm1
   Instructions: Take with food
   ```
4. **Expected**: Medication dispensed successfully
5. **Actual**: [To be filled during testing]

## 🐛 **Issues Found During Testing**

### ❌ **Critical Issues**
- [ ] Issue 1: [Description]
- [ ] Issue 2: [Description]
- [ ] Issue 3: [Description]

### ⚠️ **Minor Issues**
- [ ] Issue 1: [Description]
- [ ] Issue 2: [Description]
- [ ] Issue 3: [Description]

### ✅ **Working Features**
- [ ] Feature 1: [Description]
- [ ] Feature 2: [Description]
- [ ] Feature 3: [Description]

## 📊 **Testing Results Summary**

### ✅ **Passed Tests**
- Total: [Number]
- Success Rate: [Percentage]%

### ❌ **Failed Tests**
- Total: [Number]
- Failure Rate: [Percentage]%

### 🎯 **Priority Fixes Needed**
1. [Fix 1 - Priority: High]
2. [Fix 2 - Priority: Medium]
3. [Fix 3 - Priority: Low]

## 🚀 **Next Steps**

### ✅ **Immediate Actions**
1. [ ] Document all issues found
2. [ ] Prioritize critical issues
3. [ ] Create fix implementation plan
4. [ ] Test fixes thoroughly

### ✅ **Long-term Improvements**
1. [ ] UI/UX enhancements
2. [ ] Workflow optimizations
3. [ ] Additional testing scenarios
4. [ ] Performance improvements

---

**Status**: 🧪 **Live Testing in Progress**

Use this checklist to systematically test all LHIMS functionality and document results. Update the "Actual" fields as you test each scenario.

---

*Live Testing Session Started: February 8, 2026*  
*Application: http://localhost:8000*  
*Status: Testing in Progress*
