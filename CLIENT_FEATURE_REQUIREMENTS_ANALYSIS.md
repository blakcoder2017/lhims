# 📋 Client Feature Requirements Analysis

**Date:** Analysis Date  
**System:** LHIMS (Local Health Information Management System)  
**Client Meeting:** Feature Requirements Review

---

## 🎯 Executive Summary

This document analyzes 29 feature requirements from the client meeting. Each requirement is categorized by:
- **Status:** ✅ Implemented | ⚠️ Partial | ❌ Not Implemented
- **Priority:** 🔴 High | 🟡 Medium | 🟢 Low
- **Complexity:** 🔴 High | 🟡 Medium | 🟢 Low
- **Estimated Effort:** In developer days

---

## 📊 Feature Breakdown

### 1. Wards - IPD (Inpatient Department)
**Status:** ❌ Not Implemented  
**Priority:** 🔴 High  
**Complexity:** 🔴 High  
**Effort:** 10-15 days

**Current State:**
- No ward management system
- No bed tracking
- No inpatient admission/discharge workflow
- No distinction between IPD and OPD

**Requirements:**
- Create ward management (Ward name, capacity, type)
- Bed management (Bed number, status: available/occupied/reserved/maintenance)
- Patient admission workflow
- Bed assignment to patients
- Ward occupancy tracking
- Discharge workflow

**Implementation Plan:**
1. Create `Ward` model (name, capacity, type, status)
2. Create `Bed` model (ward_id, bed_number, status)
3. Create `Admission` model (patient_id, bed_id, admission_date, discharge_date, status)
4. Create admission/discharge workflows
5. Create UI for ward/bed management
6. Integrate with encounter system

---

### 2. OPD (Outpatient Department)
**Status:** ⚠️ Partial  
**Priority:** 🔴 High  
**Complexity:** 🟡 Medium  
**Effort:** 3-5 days

**Current State:**
- Appointment system exists
- Walk-in appointments supported
- No explicit OPD/IPD distinction
- No OPD-specific workflows

**Requirements:**
- Explicit OPD department designation
- OPD-specific appointment types
- OPD queue management
- Distinguish OPD from IPD in workflows

**Implementation Plan:**
1. Add department type (OPD/IPD) to departments
2. Create OPD-specific appointment workflows
3. Add OPD queue view
4. Update UI to show OPD vs IPD clearly

---

### 3. Register - Private Insurance Providers - Dropdown
**Status:** ⚠️ Partial  
**Priority:** 🟡 Medium  
**Complexity:** 🟢 Low  
**Effort:** 2-3 days

**Current State:**
- Insurance provider stored as free text field
- No master list of insurance providers
- No dropdown selection

**Requirements:**
- Create insurance provider master table
- Dropdown selection in registration form
- Ability to add new insurance providers
- Insurance provider management UI

**Implementation Plan:**
1. Create `InsuranceProvider` model (name, code, contact_info, is_active)
2. Create CRUD for insurance providers
3. Update patient registration form to use dropdown
4. Create admin UI for managing insurance providers
5. Migration to populate initial insurance providers

---

### 4. Date of Birth - Auto Update Age Calculation
**Status:** ⚠️ Partial  
**Priority:** 🟡 Medium  
**Complexity:** 🟢 Low  
**Effort:** 1-2 days

**Current State:**
- DOB stored in database
- Age calculated in some places (patient records view)
- Not consistently displayed everywhere
- No automatic age calculation on form inputs

**Requirements:**
- Automatically calculate and display age when DOB is entered
- Show age in years, months, days format
- Update age display in real-time
- Ensure age is calculated consistently across all views

**Implementation Plan:**
1. Create utility function for age calculation
2. Add JavaScript for real-time age calculation in forms
3. Update all patient views to show calculated age
4. Add age to patient API responses
5. Update patient records template

---

### 5. Detention - Monitor Patient Condition
**Status:** ❌ Not Implemented  
**Priority:** 🟡 Medium  
**Complexity:** 🟡 Medium  
**Effort:** 5-7 days

**Current State:**
- No patient detention/monitoring system
- No observation workflows

**Requirements:**
- Ability to detain patients for observation
- Detention reason tracking
- Detention period tracking
- Monitoring checklist/tasks
- Automatic release after period
- Detention status in patient records

**Implementation Plan:**
1. Create `PatientDetention` model (patient_id, reason, start_date, end_date, status, monitored_by_id)
2. Create detention workflow (detain, monitor, release)
3. Create UI for detention management
4. Add detention status to patient records
5. Create monitoring dashboard for detained patients

---

### 6. National ID is Not Compulsory
**Status:** ❌ Not Implemented (Currently Required)  
**Priority:** 🟡 Medium  
**Complexity:** 🟢 Low  
**Effort:** 1 day

**Current State:**
- National ID is required field (nullable=False, unique=True)
- Registration form requires National ID
- Database constraint enforces uniqueness

**Requirements:**
- Make National ID optional
- Remove unique constraint (or allow multiple NULLs)
- Update registration form
- Update validation logic

**Implementation Plan:**
1. Create migration to make national_id nullable and remove unique constraint for NULLs
2. Update Patient model (nullable=True, unique index with NULL handling)
3. Update registration form (remove required attribute)
4. Update validation in patient_crud
5. Update patient registration API

---

### 7. SMS Integration - Notifications
**Status:** ⚠️ Partial  
**Priority:** 🟡 Medium  
**Complexity:** 🟡 Medium  
**Effort:** 5-7 days

**Current State:**
- SMS service exists (`app/services/sms_service.py`)
- Not integrated into workflows
- No SMS templates
- No SMS sending on events

**Requirements:**
- SMS when patient is registered
- SMS when IPD admission is created
- SMS when test results/radiology are ready
- SMS thank you message when treatment is complete
- Seasonal messages (placeholder for now)
- SMS template management

**Implementation Plan:**
1. Create SMS template model
2. Integrate SMS service into patient registration
3. Integrate SMS into IPD admission workflow
4. Integrate SMS into lab/radiology result workflows
5. Create SMS sending on encounter completion
6. Create SMS template management UI
7. Add SMS preference tracking (opt-in/opt-out)

---

### 8. Triage Queue for Nurses
**Status:** ⚠️ Partial  
**Priority:** 🔴 High  
**Complexity:** 🟡 Medium  
**Effort:** 3-5 days

**Current State:**
- Triage/vitals recording exists
- No queue system for triage
- No nurse-specific queue view
- Nurses can't see pending triage patients

**Requirements:**
- Queue system for patients awaiting triage
- Nurse dashboard showing triage queue
- Queue number assignment for triage
- Ability to mark patients as "triaged"
- Real-time queue updates

**Implementation Plan:**
1. Create triage queue status (pending, in_progress, completed)
2. Create triage queue view for nurses
3. Add queue number to triage workflow
4. Create nurse dashboard with triage queue
5. Update triage API to support queue management
6. Add real-time queue updates

---

### 9. Patients in Triage Queue on Nurses Dashboard
**Status:** ❌ Not Implemented  
**Priority:** 🔴 High  
**Complexity:** 🟡 Medium  
**Effort:** 2-3 days

**Current State:**
- No nurse-specific dashboard
- No triage queue view

**Requirements:**
- Nurse dashboard showing triage queue
- List of patients awaiting vitals
- Ability to select patient from queue
- Mark patient as "vitals recorded"

**Implementation Plan:**
1. Create nurse dashboard route
2. Create triage queue query (patients with appointments but no recent vitals)
3. Create UI for triage queue
4. Add "Record Vitals" action from queue
5. Update queue after vitals recorded

---

### 10. Change "Record Triage" to "Record Vitals"
**Status:** ❌ Not Implemented  
**Priority:** 🟢 Low  
**Complexity:** 🟢 Low  
**Effort:** 0.5 day

**Current State:**
- UI shows "Record Triage" or "Record Vital Signs (Triage)"
- Inconsistent naming

**Requirements:**
- Rename all "Record Triage" to "Record Vitals"
- Update all UI labels
- Update documentation

**Implementation Plan:**
1. Search and replace in templates
2. Update API endpoint names/comments
3. Update documentation

---

### 11. Nurses Do Much During IPD - Walk-ins They Do Not Do Much
**Status:** ❌ Not Implemented  
**Priority:** 🟡 Medium  
**Complexity:** 🟡 Medium  
**Effort:** 3-5 days

**Current State:**
- No distinction between IPD and walk-in workflows for nurses
- No role-based workflow differences

**Requirements:**
- Different workflows for nurses in IPD vs walk-ins
- IPD nurses have more responsibilities (vitals, monitoring, medication administration)
- Walk-in nurses focus on triage only
- Role-based UI differences

**Implementation Plan:**
1. Define IPD nurse vs walk-in nurse roles
2. Create role-based permissions
3. Update nurse UI based on context (IPD vs OPD)
4. Create IPD-specific nurse workflows
5. Update nurse dashboard based on department

---

### 12. Doctors on Duty
**Status:** ❌ Not Implemented  
**Priority:** 🔴 High  
**Complexity:** 🟡 Medium  
**Effort:** 4-6 days

**Current State:**
- No doctor duty/schedule tracking
- No way to assign doctors to shifts
- No "doctors on duty" view

**Requirements:**
- Doctor duty schedule management
- Track which doctors are on duty
- Assign doctors to shifts/departments
- View doctors on duty
- Assign patients to doctors on duty

**Implementation Plan:**
1. Create `DoctorDuty` model (doctor_id, department, shift_start, shift_end, date, status)
2. Create duty schedule management UI
3. Create "doctors on duty" view
4. Update appointment assignment to show doctors on duty
5. Create duty roster management

---

### 13. Doctors Cannot Create Encounter - Front Desk Creates Encounters
**Status:** ❌ Not Implemented (Currently Doctors Can Create)  
**Priority:** 🔴 High  
**Complexity:** 🟡 Medium  
**Effort:** 2-3 days

**Current State:**
- Doctors can create encounters (`role_required(["Clinician", "Admin"])`)
- Front desk can create encounters
- No restriction on who creates encounters

**Requirements:**
- Only Front Desk can create encounters
- Doctors can only view pending encounters
- Doctors cannot create new encounters
- Doctors cannot create revisits
- Update role permissions

**Implementation Plan:**
1. Update encounter creation endpoint to require "Front Office" role
2. Remove "Clinician" role from encounter creation
3. Create "pending encounters" view for doctors
4. Update doctor UI to show only pending encounters
5. Update encounter workflow documentation

---

### 14. Pay-as-You-Go for Cash Customers (IPD vs OPD Rules)
**Status:** ⚠️ Partial  
**Priority:** 🔴 High  
**Complexity:** 🔴 High  
**Effort:** 7-10 days

**Current State:**
- Billing system exists
- No distinction between IPD and OPD billing
- No pay-as-you-go enforcement
- No automatic charging

**Requirements:**
- Cash customers: Pay-as-you-go for all services (OPD)
- IPD cash customers: Only consumables are pay-as-you-go
- IPD: Ward/bed charges paid at discharge (cashier/finance)
- Automatic charge creation for services
- Payment required before service delivery (OPD)
- IPD billing at discharge

**Implementation Plan:**
1. Create service charge automation for OPD cash customers
2. Create IPD-specific billing rules
3. Distinguish consumables from room charges
4. Create pay-as-you-go workflow for OPD
5. Create IPD billing at discharge workflow
6. Update billing API to enforce payment rules
7. Create charge automation service

---

### 15. Secondary Diagnoses (JSON Format) - Optional JSON Array
**Status:** ✅ Implemented  
**Priority:** 🟢 Low  
**Complexity:** 🟢 Low  
**Effort:** 0 days

**Current State:**
- Secondary diagnoses stored as JSON string in `secondary_diagnosis_codes` field
- Field is optional
- JSON format supported

**Requirements:**
- Already implemented as JSON string
- May need UI improvements for JSON input/display

**Implementation Plan:**
1. Verify JSON format in database
2. Improve UI for JSON input (maybe use array input instead of raw JSON)
3. Add validation for JSON format
4. Update encounter form to support multiple secondary diagnoses

---

### 16. Show List of Labs During Encounter and Radiology (List of Scans)
**Status:** ⚠️ Partial  
**Priority:** 🟡 Medium  
**Complexity:** 🟡 Medium  
**Effort:** 2-3 days

**Current State:**
- Lab orders displayed in encounter view
- Radiology orders displayed in encounter view
- May need better organization and display

**Requirements:**
- Clear list of lab tests ordered during encounter
- Clear list of radiology scans ordered during encounter
- Show order status
- Show results if available
- Better UI organization

**Implementation Plan:**
1. Review current encounter view
2. Improve lab orders display (table format, status badges)
3. Improve radiology orders display
4. Add filters (pending, completed, all)
5. Add result preview in encounter view

---

### 17. Encounter Cannot Be Closed if Labs/Radiology Pending
**Status:** ❌ Not Implemented  
**Priority:** 🔴 High  
**Complexity:** 🟡 Medium  
**Effort:** 2-3 days

**Current State:**
- Encounters can be closed regardless of order status
- No validation for pending orders
- No enforcement of order completion

**Requirements:**
- Prevent encounter closure if lab orders pending
- Prevent encounter closure if radiology orders pending
- Show warning message
- Allow force close with reason (admin only)

**Implementation Plan:**
1. Add validation in encounter close endpoint
2. Check for pending lab orders
3. Check for pending radiology orders
4. Show error message if pending orders
5. Add force close option for admin
6. Update encounter close UI

---

### 18. Doctor Can View Results on Encounter Page
**Status:** ⚠️ Partial  
**Priority:** 🔴 High  
**Complexity:** 🟡 Medium  
**Effort:** 3-4 days

**Current State:**
- Lab results can be viewed in lab dashboard
- Radiology reports can be viewed in radiology dashboard
- Results not directly visible on encounter page
- Doctors need to navigate away to see results

**Requirements:**
- Show lab results directly on encounter page
- Show radiology reports directly on encounter page
- Display results in readable format
- Show result status (pending, completed, abnormal)
- Link to full result details

**Implementation Plan:**
1. Update encounter view to include lab results
2. Update encounter view to include radiology reports
3. Create result display components
4. Add result status indicators
5. Add links to full result details
6. Update encounter API to include results

---

### 19. Generate Receipt Number Automatically
**Status:** ❌ Not Implemented  
**Priority:** 🟡 Medium  
**Complexity:** 🟢 Low  
**Effort:** 1-2 days

**Current State:**
- Invoice numbers are generated
- Receipt numbers may not be automatically generated
- Payment receipts may not have unique numbers

**Requirements:**
- Automatic receipt number generation
- Unique receipt numbers
- Receipt number format (e.g., REC-YYYY-XXXXX)
- Receipt number in payment records
- Receipt printing with number

**Implementation Plan:**
1. Create receipt number generation function
2. Add receipt_number field to payment model
3. Auto-generate on payment creation
4. Update payment API
5. Update receipt printing template
6. Add receipt number to payment UI

---

### 20. Track Expenses
**Status:** ❌ Not Implemented  
**Priority:** 🟡 Medium  
**Complexity:** 🟡 Medium  
**Effort:** 5-7 days

**Current State:**
- Revenue tracking exists (invoices, payments)
- No expense tracking
- No expense management

**Requirements:**
- Record expenses of any kind
- Expense categories
- Expense tracking and reporting
- Expense vs revenue comparison
- Expense approval workflow (optional)

**Implementation Plan:**
1. Create `Expense` model (amount, category, description, date, approved_by_id, status)
2. Create expense categories
3. Create expense CRUD operations
4. Create expense management UI
5. Create expense reporting
6. Create expense vs revenue dashboard
7. Add expense approval workflow (optional)

---

### 21. Patients List with Search and Filter
**Status:** ⚠️ Partial  
**Priority:** 🟡 Medium  
**Complexity:** 🟡 Medium  
**Effort:** 2-3 days

**Current State:**
- Patient search exists
- Search by name, ID, phone
- No advanced filtering
- No patient list view with filters

**Requirements:**
- Patient list view
- Search functionality
- Filter by date, department, status
- Sortable columns
- Pagination
- Export functionality

**Implementation Plan:**
1. Create patient list page
2. Add search functionality
3. Add filters (date range, department, payment mechanism, status)
4. Add sorting
5. Add pagination
6. Add export to CSV/Excel
7. Update patient search API

---

### 22. Patient History with Charts on Vitals and Invoices
**Status:** ⚠️ Partial  
**Priority:** 🟡 Medium  
**Complexity:** 🟡 Medium  
**Effort:** 4-6 days

**Current State:**
- Patient history exists (encounters, appointments, vitals)
- No charts/graphs
- Invoice history displayed but not charted
- No visualizations

**Requirements:**
- Chart vitals over time (temperature, BP, pulse)
- Chart invoice history
- Visual representation of patient trends
- Interactive charts
- Export charts

**Implementation Plan:**
1. Integrate charting library (Chart.js or similar)
2. Create vitals chart component
3. Create invoice history chart
4. Add charts to patient records view
5. Create chart data API endpoints
6. Add chart customization options

---

### 23. Add Procedures (Surgery and Others) to Patients
**Status:** ❌ Not Implemented  
**Priority:** 🟡 Medium  
**Complexity:** 🟡 Medium  
**Effort:** 5-7 days

**Current State:**
- No procedure tracking
- No surgery records
- Procedures not linked to patients

**Requirements:**
- Record procedures for patients
- Procedure types (surgery, minor procedures, etc.)
- Procedure details (date, doctor, type, notes)
- Procedure billing
- Procedure history in patient records

**Implementation Plan:**
1. Create `Procedure` model (patient_id, encounter_id, procedure_type, procedure_name, date, performed_by_id, notes, status)
2. Create procedure types catalog
3. Create procedure CRUD operations
4. Create procedure management UI
5. Link procedures to encounters
6. Add procedure billing
7. Add procedures to patient history

---

### 24. Detain or Admit Patient - Track Wards and Beds
**Status:** ❌ Not Implemented  
**Priority:** 🔴 High  
**Complexity:** 🔴 High  
**Effort:** 10-12 days

**Current State:**
- No admission system
- No ward/bed tracking
- No patient detention system

**Requirements:**
- Admit patients to wards
- Assign beds to patients
- Track ward occupancy
- Track bed status
- Admission workflow
- Discharge workflow
- Bed assignment
- Ward transfer

**Implementation Plan:**
1. Implement wards system (see requirement #1)
2. Implement bed management (see requirement #1)
3. Create admission workflow
4. Create discharge workflow
5. Create bed assignment UI
6. Create ward occupancy dashboard
7. Integrate with encounter system
8. Create admission/discharge reports

---

### 25. Doctors Should See Queued Patients
**Status:** ⚠️ Partial  
**Priority:** 🔴 High  
**Complexity:** 🟡 Medium  
**Effort:** 2-3 days

**Current State:**
- Appointment queue exists
- Doctors can view appointments
- May need better queue visibility
- May need real-time updates

**Requirements:**
- Doctor dashboard showing queued patients
- Real-time queue updates
- Filter by department
- Sort by priority
- Mark patients as "seen"
- Queue status indicators

**Implementation Plan:**
1. Create doctor queue dashboard
2. Add real-time queue updates (WebSocket or polling)
3. Add queue filters
4. Add queue sorting
5. Add "mark as seen" functionality
6. Update queue UI for doctors
7. Add queue notifications

---

### 26. Patient Transfers (Send and Receive)
**Status:** ❌ Not Implemented  
**Priority:** 🟡 Medium  
**Complexity:** 🟡 Medium  
**Effort:** 6-8 days

**Current State:**
- No patient transfer system
- No inter-facility transfer tracking

**Requirements:**
- Send patients to other facilities
- Receive patients from other facilities
- Transfer documentation
- Transfer reasons
- Transfer status tracking
- Transfer history

**Implementation Plan:**
1. Create `PatientTransfer` model (patient_id, from_facility, to_facility, transfer_date, reason, status, transferred_by_id)
2. Create facility master table
3. Create transfer workflow (initiate, approve, complete)
4. Create transfer UI
5. Create transfer documentation
6. Add transfer to patient history
7. Create transfer reports

---

### 27. Encounter Cannot Be Closed Without Settling Bills (Admitted Patients)
**Status:** ❌ Not Implemented  
**Priority:** 🔴 High  
**Complexity:** 🟡 Medium  
**Effort:** 2-3 days

**Current State:**
- Encounters can be closed regardless of billing status
- No validation for outstanding bills
- No enforcement of payment before discharge

**Requirements:**
- Prevent encounter closure if bills not settled (for admitted patients)
- Check for outstanding invoices
- Show outstanding balance
- Allow payment before closing encounter
- Exception for insurance patients (billed later)

**Implementation Plan:**
1. Add validation in encounter close endpoint
2. Check for outstanding invoices for admitted patients
3. Check patient admission status
4. Show error if bills not settled
5. Add payment link in encounter close UI
6. Update encounter close workflow
7. Add exception for insurance patients

---

### 28. Add Antenatal to List of Services
**Status:** ❌ Not Implemented  
**Priority:** 🟡 Medium  
**Complexity:** 🟢 Low  
**Effort:** 1-2 days

**Current State:**
- Service list exists
- Antenatal not in service list
- No antenatal-specific workflows

**Requirements:**
- Add antenatal to service catalog
- Antenatal-specific appointments
- Antenatal tracking
- Antenatal billing

**Implementation Plan:**
1. Add antenatal to service pricing catalog
2. Add antenatal to department list
3. Create antenatal appointment type
4. Add antenatal to service selection
5. Update service pricing UI
6. Add antenatal-specific fields (optional)

---

### 29. Add Languages Patient Can Speak on Registration
**Status:** ❌ Not Implemented  
**Priority:** 🟢 Low  
**Complexity:** 🟢 Low  
**Effort:** 1-2 days

**Current State:**
- Patient registration doesn't include languages
- No language tracking

**Requirements:**
- Add languages field to patient registration
- Multiple languages support
- Language selection dropdown
- Language in patient records

**Implementation Plan:**
1. Add `languages` field to Patient model (JSON array or comma-separated)
2. Create language master list
3. Update patient registration form (multi-select)
4. Update patient records display
5. Update patient API
6. Add language to patient search (optional)

---

## 🎯 Prioritization Summary

### 🔴 High Priority (Must Have)
1. Wards - IPD (Requirement #1)
2. OPD (Requirement #2)
3. Triage Queue for Nurses (Requirement #8)
4. Patients in Triage Queue on Nurses (Requirement #9)
5. Doctors on Duty (Requirement #12)
6. Doctors Cannot Create Encounter (Requirement #13)
7. Pay-as-You-Go for Cash Customers (Requirement #14)
8. Encounter Cannot Be Closed if Labs/Radiology Pending (Requirement #17)
9. Doctor Can View Results on Encounter Page (Requirement #18)
10. Detain or Admit Patient - Track Wards and Beds (Requirement #24)
11. Doctors Should See Queued Patients (Requirement #25)
12. Encounter Cannot Be Closed Without Settling Bills (Requirement #27)

### 🟡 Medium Priority (Should Have)
1. Register - Private Insurance Providers (Requirement #3)
2. Date of Birth - Auto Update Age (Requirement #4)
3. Detention - Monitor Patient Condition (Requirement #5)
4. National ID is Not Compulsory (Requirement #6)
5. SMS Integration (Requirement #7)
6. Nurses Do Much During IPD (Requirement #11)
7. Show List of Labs/Radiology (Requirement #16)
8. Generate Receipt Number Automatically (Requirement #19)
9. Track Expenses (Requirement #20)
10. Patients List with Search and Filter (Requirement #21)
11. Patient History with Charts (Requirement #22)
12. Add Procedures (Requirement #23)
13. Patient Transfers (Requirement #26)
14. Add Antenatal to Services (Requirement #28)

### 🟢 Low Priority (Nice to Have)
1. Change "Record Triage" to "Record Vitals" (Requirement #10)
2. Secondary Diagnoses JSON (Requirement #15) - Already Implemented
3. Add Languages Patient Can Speak (Requirement #29)

---

## 📈 Implementation Roadmap

### Phase 1: Critical Workflow Fixes (2-3 weeks)
- Fix prescription creation error ✅ (DONE)
- Doctors cannot create encounters (Requirement #13)
- Encounter cannot be closed if labs/radiology pending (Requirement #17)
- Encounter cannot be closed without settling bills (Requirement #27)
- National ID is not compulsory (Requirement #6)
- Change "Record Triage" to "Record Vitals" (Requirement #10)

### Phase 2: Core IPD/OPD Infrastructure (3-4 weeks)
- Wards - IPD (Requirement #1)
- OPD (Requirement #2)
- Detain or Admit Patient - Track Wards and Beds (Requirement #24)
- Doctors on Duty (Requirement #12)
- Pay-as-You-Go for Cash Customers (Requirement #14)

### Phase 3: Queue and Workflow Improvements (2-3 weeks)
- Triage Queue for Nurses (Requirement #8)
- Patients in Triage Queue on Nurses (Requirement #9)
- Doctors Should See Queued Patients (Requirement #25)
- Nurses Do Much During IPD (Requirement #11)

### Phase 4: Enhanced Features (3-4 weeks)
- Doctor Can View Results on Encounter Page (Requirement #18)
- Show List of Labs/Radiology (Requirement #16)
- Register - Private Insurance Providers (Requirement #3)
- Date of Birth - Auto Update Age (Requirement #4)
- Generate Receipt Number Automatically (Requirement #19)

### Phase 5: Additional Features (4-5 weeks)
- SMS Integration (Requirement #7)
- Detention - Monitor Patient Condition (Requirement #5)
- Track Expenses (Requirement #20)
- Patients List with Search and Filter (Requirement #21)
- Patient History with Charts (Requirement #22)
- Add Procedures (Requirement #23)
- Patient Transfers (Requirement #26)
- Add Antenatal to Services (Requirement #28)
- Add Languages Patient Can Speak (Requirement #29)

---

## 🔧 Technical Considerations

### Database Changes Required
1. New tables: `wards`, `beds`, `admissions`, `insurance_providers`, `doctor_duties`, `expenses`, `procedures`, `patient_transfers`, `patient_detentions`, `sms_templates`
2. Schema changes: `patients` (national_id nullable, languages field), `encounters` (admission_id, detention_id), `invoices` (receipt_number)
3. New relationships: Patient -> Admission, Patient -> Detention, Encounter -> Admission, etc.

### API Changes Required
1. New endpoints for wards, beds, admissions, insurance providers, doctor duties, expenses, procedures, transfers, detentions
2. Updated endpoints for encounters (restrict creation, validate closure)
3. Updated endpoints for patients (optional national_id, languages)
4. New endpoints for queue management
5. New endpoints for SMS sending

### UI Changes Required
1. New pages: Wards management, Beds management, Admissions, Doctor duties, Expenses, Procedures, Transfers, Detentions, Insurance providers
2. Updated pages: Patient registration, Encounter creation/view, Triage queue, Doctor dashboard, Nurse dashboard
3. New components: Queue views, Charts, Result displays, Bed assignment, Ward occupancy

### Integration Points
1. SMS service integration
2. Billing system integration (pay-as-you-go, IPD billing)
3. Encounter system integration (admission, detention, procedures)
4. Queue system integration (triage, doctor queue)
5. Charting library integration

---

## 📝 Notes

1. **Prescription Error Fixed:** The prescription creation error has been fixed by improving form data handling and validation.

2. **Dependencies:** Some features depend on others (e.g., IPD features depend on wards/beds, admission depends on IPD, etc.)

3. **Testing:** Each feature should be thoroughly tested, especially workflow-related features.

4. **Documentation:** Update user manuals and workflow documentation as features are implemented.

5. **Training:** Staff training may be required for new workflows (IPD, queue management, etc.)

---

## ✅ Next Steps

1. **Review and Approve:** Client should review this analysis and approve prioritization
2. **Detailed Planning:** Create detailed implementation plans for Phase 1 features
3. **Database Design:** Finalize database schema changes
4. **API Design:** Design API endpoints for new features
5. **UI/UX Design:** Design UI mockups for new features
6. **Development:** Start Phase 1 implementation
7. **Testing:** Test each feature as it's implemented
8. **Deployment:** Deploy features in phases

---

**Document Version:** 1.0  
**Last Updated:** Analysis Date  
**Prepared By:** Development Team

