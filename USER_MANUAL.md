# 📘 LHIMS User Manual & Workflow Guide

**Version:** 1.0  
**Last Updated:** 2025-01-XX  
**System:** Local Health Information Management System (LHIMS)

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [User Roles & Permissions](#user-roles--permissions)
3. [Getting Started](#getting-started)
4. [Complete Workflows](#complete-workflows)
5. [Step-by-Step Tutorials](#step-by-step-tutorials)
6. [Common Tasks](#common-tasks)
7. [Troubleshooting](#troubleshooting)
8. [Appendix](#appendix)

---

## 🏥 System Overview

### What is LHIMS?

The **Local Health Information Management System (LHIMS)** is a comprehensive hospital management system designed to digitize and streamline healthcare operations. It provides end-to-end patient care management from registration through billing, with integrated modules for:

- Patient Registration & Demographics
- Triage & Vital Signs
- Clinical Documentation
- Laboratory Information System (LIS)
- Radiology Information System (RIS)
- Pharmacy Information System (PhIS)
- Billing & Payment Processing
- NHIS Claims Management
- Reports & Analytics

### Key Features

✅ **Complete Patient Journey Tracking** - From registration to discharge  
✅ **Electronic Health Records (EHR)** - Comprehensive patient medical history  
✅ **Computerized Provider Order Entry (CPOE)** - Lab, Radiology, and Pharmacy orders  
✅ **Automated Billing** - Charge aggregation and invoice generation  
✅ **NHIS Integration Ready** - Framework for National Health Insurance Scheme claims  
✅ **Role-Based Access Control** - Secure access based on user roles  
✅ **Real-Time Dashboards** - Key metrics and analytics  
✅ **Offline Capable** - Works without internet connection  

---

## 👥 User Roles & Permissions

### Role Descriptions

| Role | Description | Key Responsibilities |
|------|-------------|---------------------|
| **Admin** | System Administrator | Full system access, user management, system settings |
| **Front Office** | Registration & Triage Staff | Patient registration, triage, vital signs, appointments |
| **Clinician** | Doctors & Nurses | Clinical encounters, diagnoses, order entry, patient records |
| **Lab Staff** | Laboratory Technicians | Lab order fulfillment, result entry, sample tracking, QC |
| **Pharmacy Staff** | Pharmacists & Pharmacy Technicians | Prescription dispensing, inventory management, drug interactions |
| **Finance** | Billing & Accounts Staff | Invoice creation, payment processing, NHIS claims, reports |
| **Management** | Hospital Administrators | Reports, analytics, dashboards (read-only access) |

### Access Matrix

| Feature | Admin | Front Office | Clinician | Lab Staff | Pharmacy Staff | Finance | Management |
|---------|:-----:|:------------:|:---------:|:---------:|:--------------:|:-------:|:----------:|
| Patient Registration | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Triage & Vitals | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Patient Search | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Medical Records | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Clinical Encounters | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Lab Orders | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Lab Results | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Radiology Orders | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Radiology Reports | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Prescriptions | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Medication Dispensing | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Inventory Management | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Billing & Invoices | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Payment Processing | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| NHIS Claims | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Reports & Analytics | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| User Management | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| System Settings | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 🚀 Getting Started

### Logging In

1. **Open your web browser** and navigate to the LHIMS URL (provided by your IT administrator)
2. **Enter your credentials:**
   - Username: Your assigned username
   - Password: Your password
3. **Click "Sign In"**
4. You will be redirected to your role-specific dashboard

### First-Time Login

If this is your first time logging in:
- **Default Admin Credentials:**
  - Username: `admin`
  - Password: `Westafrica1` (change immediately after first login)
- **Change your password** by clicking on your name in the sidebar → "Edit Profile" → "Change Password"

### Navigation Overview

The LHIMS interface consists of:

1. **Top Navigation Bar:**
   - User role indicator
   - Logout button

2. **Sidebar Menu:**
   - Role-specific menu items
   - Organized by functional areas
   - Collapsible sections

3. **Main Content Area:**
   - Dashboard with key metrics
   - Forms and data entry screens
   - Reports and analytics

4. **User Panel (Sidebar):**
   - Your name (click to view profile)
   - Edit Profile button
   - Your role

---

## 🔄 Complete Workflows

### Workflow 1: Patient Registration to Discharge

This is the complete patient journey through the hospital system.

```
1. Patient Arrival
   ↓
2. Patient Registration (Front Office)
   ↓
3. Financial Screening (Front Office)
   ↓
4. Triage & Vital Signs (Front Office)
   ↓
5. Appointment Scheduling (Front Office)
   ↓
6. Clinical Encounter (Clinician)
   ↓
7. Order Entry - Lab/Radiology/Prescriptions (Clinician)
   ↓
8. Order Fulfillment (Lab Staff / Radiology Staff / Pharmacy Staff)
   ↓
9. Billing & Invoice Generation (Finance / Front Office)
   ↓
10. Payment Processing (Finance / Front Office)
   ↓
11. Discharge / Follow-up
```

### Workflow 2: Clinical Encounter Documentation

```
1. Search for Patient (Clinician)
   ↓
2. View Patient Records (Clinician)
   ↓
3. Create New Encounter (Clinician)
   ↓
4. Document Chief Complaint & History (Clinician)
   ↓
5. Document Physical Examination (Clinician)
   ↓
6. Enter Diagnoses (ICD-10) (Clinician)
   ↓
7. Create Treatment Plan (Clinician)
   ↓
8. Enter Orders (Lab/Radiology/Prescriptions) (Clinician)
   ↓
9. Complete Encounter (Clinician)
```

### Workflow 3: Laboratory Order Fulfillment

```
1. Receive Lab Order (Lab Staff)
   ↓
2. Create Sample Record with Barcode (Lab Staff)
   ↓
3. Collect Sample (Lab Staff)
   ↓
4. Perform Test (Lab Staff)
   ↓
5. Enter Results (Lab Staff)
   ↓
6. Validate Results Against Reference Ranges (System)
   ↓
7. Mark Order as Completed (Lab Staff)
   ↓
8. Charge Automatically Created (System)
```

### Workflow 4: Pharmacy Prescription Fulfillment

```
1. Receive Prescription Order (Pharmacy Staff)
   ↓
2. Check Drug Interactions (System)
   ↓
3. Check Formulary Compliance (System)
   ↓
4. Check Stock Availability (System)
   ↓
5. Dispense Medication (Pharmacy Staff)
   ↓
6. Update Inventory (System)
   ↓
7. Mark Prescription as Dispensed (Pharmacy Staff)
   ↓
8. Charge Automatically Created (System)
```

### Workflow 5: Billing & Payment

```
1. Encounter Completed (System)
   ↓
2. Orders Completed (System)
   ↓
3. Charges Automatically Aggregated (System)
   ↓
4. Invoice Created/Updated (Finance / Front Office)
   ↓
5. Payment Method Selected (Finance / Front Office)
   ↓
6. Co-pay Calculated (if NHIS) (System)
   ↓
7. Payment Processed (Finance / Front Office)
   ↓
8. Receipt Generated (System)
```

---

## 📚 Step-by-Step Tutorials

### Tutorial 1: Registering a New Patient

**Role Required:** Front Office

**Steps:**

1. **Navigate to Patient Registration**
   - Click **"Front Office"** in the sidebar
   - Click **"Patient Registration"**

2. **Fill in Patient Demographics**
   - **First Name:** Enter patient's first name
   - **Last Name:** Enter patient's last name
   - **Date of Birth:** Select date (format: YYYY-MM-DD)
   - **Gender:** Select from dropdown (Male/Female/Other)
   - **National ID:** Enter Ghana Card or National ID number
   - **Phone Number:** Enter contact number (optional)
   - **Address:** Enter patient's address (optional)

3. **Complete Financial Screening**
   - **Payment Mechanism:** Select one:
     - Cash
     - NHIS (National Health Insurance Scheme)
     - Private Insurance
     - Self-Pay
   - **If NHIS:** Enter NHIS number
   - **If Private Insurance:** Enter:
     - Insurance Provider name
     - Policy Number

4. **Submit Registration**
   - Click **"Register Patient"** button
   - System will check for duplicate National ID
   - If successful, you'll be redirected to the Triage page

5. **Next Steps**
   - After registration, proceed to Triage & Vital Signs

**Important Notes:**
- National ID must be unique (system will prevent duplicates)
- All required fields are marked with *
- Patient is automatically assigned a unique Patient ID

---

### Tutorial 2: Recording Triage & Vital Signs

**Role Required:** Front Office or Clinician

**Steps:**

1. **Access Triage Page**
   - After patient registration, you'll be automatically redirected
   - Or navigate: **Front Office** → **Triage & Vitals**
   - Search for patient and click **"Triage"**

2. **Record Vital Signs**
   - **Temperature:** Enter in °C (e.g., 36.5)
   - **Blood Pressure:** Enter as Systolic/Diastolic (e.g., 120/80)
   - **Notes:** Add any additional observations (optional)

3. **Save Vital Signs**
   - Click **"Save Vital Signs"** button
   - Record is saved with timestamp
   - You'll be redirected to Patient Records page

**Important Notes:**
- Vital signs are recorded with timestamp
- All records are linked to the staff member who recorded them
- Historical vital signs can be viewed in Patient Records

---

### Tutorial 3: Creating a Clinical Encounter

**Role Required:** Clinician

**Steps:**

1. **Search for Patient**
   - Navigate: **Clinical Services** → **Patient EHR Search**
   - Enter patient name, National ID, or phone number
   - Click **"Search"**
   - Click on the patient from results

2. **View Patient Records** (Optional but Recommended)
   - Review patient's medical history
   - Check previous encounters
   - Review vital signs history
   - Check allergies and medications

3. **Create New Encounter**
   - Click **"New Encounter"** button (on patient records page)
   - Or navigate directly: `/patients/{patient_id}/encounters/new`

4. **Document Chief Complaint & History**
   - **Chief Complaint:** Patient's main reason for visit
   - **History of Present Illness (HPI):** Detailed history of current illness
   - **Past Medical History:** Previous conditions, surgeries, etc.
   - **Allergies:** Known allergies (if not already documented)
   - **Current Medications:** Medications patient is currently taking

5. **Document Physical Examination**
   - Enter findings from physical examination
   - Be thorough and specific

6. **Enter Assessment & Plan**
   - **Assessment:** Clinical assessment/diagnosis
   - **Plan:** Treatment plan and recommendations

7. **Enter Diagnoses**
   - **Primary Diagnosis Code:** ICD-10 code (e.g., J11.1)
   - **Primary Diagnosis Description:** Description of diagnosis
   - **Secondary Diagnoses:** Additional diagnosis codes (optional, JSON format)

8. **Save Encounter**
   - Click **"Create Encounter"** button
   - Encounter is created with status "In Progress"
   - You'll be redirected to the Encounter View page

9. **Add Orders** (if needed)
   - From the Encounter View page, you can add:
     - Lab Orders
     - Radiology Orders
     - Prescriptions

**Important Notes:**
- Encounter can be saved and completed later
- Status: "In Progress" → "Completed"
- All information is saved to patient's medical record
- ICD-10 codes should be accurate for billing and reporting

---

### Tutorial 4: Creating Lab Orders

**Role Required:** Clinician

**Steps:**

1. **Access Encounter**
   - Navigate to encounter (from Pending Encounters or Patient Records)
   - Or create new encounter first

2. **Add Lab Order**
   - Scroll to **"Lab Orders"** section on Encounter page
   - Click **"Add Lab Order"** button

3. **Fill in Lab Order Details**
   - **Test Name:** Enter test name (e.g., "Complete Blood Count", "Blood Glucose")
   - **Test Type:** Select from dropdown:
     - Blood Test
     - Urine Test
     - Stool Test
     - Other
   - **Priority:** Select priority level:
     - Routine
     - Urgent
     - Stat (Immediate)
   - **Clinical Indication:** Reason for test (optional)
   - **Special Instructions:** Any special instructions (optional)

4. **Submit Order**
   - Click **"Create Lab Order"** button
   - Order is created with status "Pending"
   - Lab staff will see the order in their dashboard

**Important Notes:**
- Lab orders are linked to the encounter
- Orders can be viewed by Lab Staff immediately
- Status progression: Pending → In Progress → Completed

---

### Tutorial 5: Entering Lab Results

**Role Required:** Lab Staff

**Steps:**

1. **Access Lab Dashboard**
   - Navigate: **Ancillary Services** → **Laboratory (LIS)**
   - View pending lab orders

2. **Select Order to Fulfill**
   - Click on an order from the list
   - Review order details and patient information

3. **Create Sample Record** (Optional but Recommended)
   - Navigate: **Ancillary Services** → **Sample Tracking**
   - Click **"Create Sample"**
   - Enter:
     - Lab Order ID
     - Sample Type
     - Barcode (auto-generated or manual)
     - Collection Date/Time
   - Save sample record

4. **Enter Lab Results**
   - From Lab Order detail page, click **"Enter Result"**
   - Enter test results:
     - For numeric values: Enter the value
     - For text results: Enter description
   - **Result Format:** Can be structured (JSON) or free text

5. **Validate Results** (Automatic)
   - System checks against reference ranges (if configured)
   - Critical values are flagged
   - Validation status is displayed

6. **Complete Order**
   - Click **"Save Result"** button
   - Order status changes to "Completed"
   - Charge is automatically created for billing

**Important Notes:**
- Results are validated against reference ranges automatically
- Critical values trigger alerts
- Results are immediately available to clinicians
- Charges are automatically created upon completion

---

### Tutorial 6: Creating Prescriptions

**Role Required:** Clinician

**Steps:**

1. **Access Encounter**
   - Navigate to encounter (from Pending Encounters or Patient Records)

2. **Add Prescription**
   - Scroll to **"Prescriptions"** section
   - Click **"Add Prescription"** button

3. **Fill in Prescription Details**
   - **Medication Name:** Enter medication name (e.g., "Paracetamol 500mg")
   - **Dosage:** Enter dosage (e.g., "500mg")
   - **Frequency:** Enter frequency (e.g., "Twice daily", "TID", "QID")
   - **Duration:** Enter duration (e.g., "5 days", "1 week")
   - **Quantity:** Enter quantity to dispense
   - **Instructions:** Special instructions for patient (optional)
   - **Priority:** Select priority:
     - Routine
     - Urgent
     - Stat

4. **Check Drug Interactions** (Automatic)
   - System checks against patient's documented allergies
   - Drug interaction warnings are displayed
   - Review warnings before submitting

5. **Submit Prescription**
   - Click **"Create Prescription"** button
   - Prescription is created with status "Pending"
   - Pharmacy staff will see the prescription in their dashboard

**Important Notes:**
- Prescriptions are linked to the encounter
- Drug interaction checking is automatic
- Allergy warnings are displayed
- Status progression: Pending → Dispensed

---

### Tutorial 7: Dispensing Medications

**Role Required:** Pharmacy Staff

**Steps:**

1. **Access Pharmacy Dashboard**
   - Navigate: **Ancillary Services** → **Pharmacy (PhIS)**
   - View pending prescriptions

2. **Select Prescription to Dispense**
   - Click on a prescription from the list
   - Review prescription details and patient information

3. **Check Drug Interactions** (Automatic)
   - System displays any drug interaction warnings
   - Review warnings carefully

4. **Check Formulary Compliance** (Automatic)
   - System checks if medication is in formulary
   - Warnings displayed if not compliant

5. **Check Stock Availability**
   - System shows available stock
   - If low stock, alert is displayed
   - If out of stock, you cannot dispense

6. **Dispense Medication**
   - Click **"Dispense Medication"** button
   - Enter:
     - Batch Number (if applicable)
     - Expiry Date (if applicable)
     - Quantity Dispensed
   - Click **"Confirm Dispensing"**

7. **Update Inventory** (Automatic)
   - Stock is automatically deducted
   - Transaction is recorded
   - Charge is automatically created for billing

**Important Notes:**
- Stock availability is checked automatically
- Inventory is updated automatically upon dispensing
- Charges are automatically created
- Prescription status changes to "Dispensed"

---

### Tutorial 8: Creating and Processing Invoices

**Role Required:** Finance or Front Office

**Steps:**

1. **Access Billing Dashboard**
   - Navigate: **Finance & Reports** → **Billing & Payments**
   - View existing invoices or create new

2. **Create New Invoice**
   - Click **"Create Invoice"** button
   - Or navigate: **Billing & Payments** → **Create Invoice**

3. **Select Patient**
   - Search for patient by name or ID
   - Select patient from results

4. **Link to Encounter** (Optional)
   - If invoice is for a specific encounter, select encounter
   - Charges from completed orders are automatically added

5. **Add Charges**
   - Click **"Add Charge"** button
   - Enter:
     - **Charge Type:** Select (Consultation, Lab, Radiology, Pharmacy, Procedure, Other)
     - **Description:** Description of charge
     - **Quantity:** Number of units
     - **Unit Price:** Price per unit
     - **Discount:** Discount amount (if any)
     - **Tax Rate:** Tax percentage (if applicable)
   - Click **"Add Charge"**

6. **Review Invoice**
   - Check all charges
   - Verify totals
   - Review patient payment mechanism (NHIS, Cash, etc.)

7. **Process Payment**
   - Click **"Process Payment"** button
   - Enter:
     - **Amount:** Payment amount
     - **Payment Method:** Select (Cash, Mobile Money, Card, Bank Transfer, NHIS, Private Insurance)
     - **Transaction Reference:** Reference number (if applicable)
     - **Receipt Number:** Receipt number (if applicable)
     - **Notes:** Additional notes (optional)
   - Click **"Process Payment"**

8. **View Invoice**
   - Invoice status updates
   - Payment is recorded
   - Receipt can be printed

**Important Notes:**
- Charges from completed orders are automatically added
- Co-pay is automatically calculated for NHIS patients
- Multiple payments can be processed for one invoice
- Invoice status: Draft → Pending → Partially Paid → Paid

---

### Tutorial 9: Viewing Patient Medical Records

**Role Required:** Any Clinical Staff (Clinician, Front Office, Lab Staff, Pharmacy Staff, Admin)

**Steps:**

1. **Search for Patient**
   - Navigate: **Clinical Services** → **Patient EHR Search**
   - Or: **Patient Records** (for Lab/Pharmacy Staff)
   - Enter search criteria:
     - Patient name
     - National ID
     - Phone number
   - Click **"Search"**

2. **Select Patient**
   - Click on patient from search results
   - Or click **"View Records"** button

3. **View Patient Records**
   - **Demographics Tab:**
     - Full patient information
     - Age calculation
     - Contact details
     - Financial information
   - **Appointment History:**
     - All appointments chronologically
     - Appointment details (type, status, department)
     - Chief complaints
   - **Vital Signs History:**
     - All vital signs recordings
     - Temperature and blood pressure trends
     - Recorded by staff member
   - **Timeline View:**
     - Combined chronological timeline
     - All appointments and vital signs
     - Most recent first

4. **View Specific Encounters**
   - Click on an encounter from the timeline
   - View complete encounter details:
     - Chief complaint
     - History
     - Physical examination
     - Diagnoses
     - Orders (Lab, Radiology, Prescriptions)
     - Results and reports

**Important Notes:**
- All clinical staff can view patient records
- Historical data is available
- Records are organized chronologically
- Complete medical history is accessible

---

### Tutorial 10: Managing Inventory

**Role Required:** Pharmacy Staff or Admin

**Steps:**

1. **Access Inventory Dashboard**
   - Navigate: **Ancillary Services** → **Inventory Management**
   - View current inventory status

2. **View Medications**
   - Browse medication list
   - Search by name
   - Filter by status (Active, Low Stock, Out of Stock)

3. **Add New Medication** (if Admin)
   - Click **"Add Medication"** button
   - Enter:
     - Medication name
     - Generic name
     - Dosage form
     - Unit of measure
     - Reorder level
   - Save medication

4. **Add Stock Item**
   - Click on a medication
   - Click **"Add Stock"** button
   - Enter:
     - Batch number
     - Expiry date
     - Quantity
     - Unit cost
     - Supplier (if configured)
   - Save stock item

5. **View Stock Alerts**
   - Navigate: **Alerts** → **Inventory Alerts**
   - View:
     - Low stock items
     - Out of stock items
     - Expired items
     - Items needing reorder

6. **Record Inventory Transactions**
   - Stock adjustments
   - Stock transfers
   - Stock returns

**Important Notes:**
- Stock is automatically updated when medications are dispensed
- Alerts are generated for low stock and expired items
- Batch and expiry tracking is available
- Supplier management is integrated

---

## 🔧 Common Tasks

### How to Change Your Password

1. Click on your name in the sidebar (top of sidebar)
2. Click **"Edit Profile"** button
3. Click **"Change Password"** tab
4. Enter:
   - Current password
   - New password
   - Confirm new password
5. Click **"Change Password"** button

### How to Edit Your Profile

1. Click on your name in the sidebar
2. Click **"Edit Profile"** button
3. Update:
   - Full Name
   - Email
4. Click **"Update Profile"** button

### How to View Pending Encounters

1. Navigate: **Clinical Services** → **Pending Encounters**
2. View list of in-progress encounters for today
3. Click **"View/Edit"** to access an encounter

### How to Search for a Patient

1. Navigate: **Clinical Services** → **Patient EHR Search**
2. Enter search term (name, ID, or phone)
3. Click **"Search"**
4. Click on patient from results

### How to Print an Encounter

1. Open the encounter you want to print
2. Click **"Print Encounter"** button (top of page)
3. Browser print dialog will open
4. Select printer and print

### How to Print an Invoice

1. Open the invoice you want to print
2. Click **"Print Invoice"** button
3. Browser print dialog will open
4. Select printer and print

### How to View Reports

1. Navigate: **Finance & Reports** → **Reports & Analytics**
2. Select report type:
   - Revenue Report
   - Invoice Report
3. Select date range
4. View report

### How to Export Data

1. Navigate: **System Admin** → **DB/System Settings**
2. Select resource type (Patients, Invoices, etc.)
3. Select format (CSV or JSON)
4. Click **"Export"** button
5. File will download

---

## 🐛 Troubleshooting

### Common Issues and Solutions

#### Issue: Cannot Log In

**Possible Causes:**
- Incorrect username or password
- Account is inactive
- Browser cookies disabled

**Solutions:**
1. Verify username and password (case-sensitive)
2. Contact Admin to check account status
3. Enable cookies in browser settings
4. Clear browser cache and try again

#### Issue: Cannot Access a Page (403 Forbidden)

**Possible Causes:**
- Insufficient role permissions
- Page requires specific role

**Solutions:**
1. Check if your role has access to this feature
2. Contact Admin if you believe you should have access
3. Refer to Access Matrix in this manual

#### Issue: Patient Not Found in Search

**Possible Causes:**
- Patient not registered
- Incorrect search criteria
- Patient record is inactive

**Solutions:**
1. Verify search criteria (try different search terms)
2. Check if patient is registered
3. Contact Admin if patient should exist

#### Issue: Cannot Create Encounter

**Possible Causes:**
- Not logged in as Clinician
- Patient not selected
- Required fields missing

**Solutions:**
1. Verify you're logged in as Clinician or Admin
2. Ensure patient is selected
3. Fill in all required fields (marked with *)

#### Issue: Lab Order Not Showing

**Possible Causes:**
- Order not created
- Wrong status filter
- Order assigned to different staff

**Solutions:**
1. Verify order was created successfully
2. Check status filters
3. Refresh the page
4. Check if order is assigned to you

#### Issue: Stock Not Updating

**Possible Causes:**
- Transaction not completed
- System error
- Inventory not properly configured

**Solutions:**
1. Verify transaction was completed
2. Refresh the page
3. Check inventory transactions log
4. Contact Admin if issue persists

#### Issue: Invoice Not Generating Charges

**Possible Causes:**
- Orders not completed
- Charges not automatically created
- Invoice not linked to encounter

**Solutions:**
1. Verify orders are completed
2. Check if charges exist
3. Manually add charges if needed
4. Link invoice to encounter

#### Issue: Payment Not Processing

**Possible Causes:**
- Invalid payment amount
- Missing required fields
- System error

**Solutions:**
1. Verify payment amount is valid
2. Fill in all required fields
3. Check payment method is correct
4. Try again or contact Finance/Admin

---

## 📎 Appendix

### A. Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Search | `Ctrl + F` (in search boxes) |
| Print | `Ctrl + P` |
| Refresh | `F5` or `Ctrl + R` |
| Go to Dashboard | Click logo or "Dashboard" in sidebar |

### B. Field Definitions

**Chief Complaint:** Patient's main reason for visiting  
**HPI (History of Present Illness):** Detailed history of current illness  
**PMH (Past Medical History):** Previous medical conditions  
**ICD-10:** International Classification of Diseases, 10th Revision  
**CPOE:** Computerized Provider Order Entry  
**EHR/EMR:** Electronic Health Record / Electronic Medical Record  
**NHIS:** National Health Insurance Scheme (Ghana)  
**PACS:** Picture Archiving and Communication System  
**LIS:** Laboratory Information System  
**RIS:** Radiology Information System  
**PhIS:** Pharmacy Information System  

### C. Status Definitions

**Encounter Status:**
- **In Progress:** Encounter is being documented
- **Completed:** Encounter is finished
- **Cancelled:** Encounter was cancelled

**Order Status:**
- **Pending:** Order created, awaiting fulfillment
- **In Progress:** Order is being processed
- **Completed:** Order is fulfilled
- **Cancelled:** Order was cancelled

**Invoice Status:**
- **Draft:** Invoice is being created
- **Pending:** Invoice is awaiting payment
- **Partially Paid:** Some payment received
- **Paid:** Fully paid
- **Cancelled:** Invoice was cancelled

**Payment Status:**
- **Pending:** Payment is being processed
- **Completed:** Payment is successful
- **Failed:** Payment failed
- **Refunded:** Payment was refunded

### D. Contact Information

For technical support or questions:
- **System Administrator:** Contact your IT department
- **Training:** Contact your supervisor or training coordinator
- **System Issues:** Report to Admin or IT support

### E. System Requirements

**Browser Compatibility:**
- Chrome (recommended)
- Firefox
- Safari
- Edge

**Minimum Requirements:**
- Modern web browser (latest version)
- JavaScript enabled
- Cookies enabled
- Internet connection (for initial setup, system works offline)

### F. Data Privacy & Security

- All patient data is confidential
- Access is logged and audited
- Do not share your login credentials
- Log out when finished
- Report security concerns immediately

---

## 📝 Document History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-01-XX | Initial release | LHIMS Development Team |

---

**End of Manual**

For the most up-to-date information, please refer to the system help documentation or contact your system administrator.

