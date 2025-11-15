# 📘 LHIMS Comprehensive User Workflows

**Version:** 2.0  
**Last Updated:** 2025-11-11  
**System:** Local Health Information Management System (LHIMS)

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [User Roles & Access](#user-roles--access)
3. [Complete Workflows by Role](#complete-workflows-by-role)
4. [Common Tasks](#common-tasks)
5. [Quick Reference](#quick-reference)

---

## 🏥 System Overview

LHIMS is a comprehensive hospital management system designed for Ghana healthcare facilities. It manages the complete patient journey from registration through billing, with integrated modules for clinical care, laboratory, radiology, pharmacy, and financial management.

### Key Modules
- **Patient Management** - Registration, demographics, medical records
- **Front Office** - Appointments, triage, vital signs
- **Clinical Services** - Encounters, diagnoses, orders
- **Laboratory (LIS)** - Test orders, sample tracking, results
- **Radiology (RIS)** - Imaging orders, PACS, reports
- **Pharmacy (PhIS)** - Prescriptions, inventory, dispensing
- **Billing & Finance** - Invoices, payments, receipts, NHIS claims
- **Administration** - User management, settings, reports

---

## 👥 User Roles & Access

### Role Descriptions

| Role | Description | Primary Functions |
|------|-------------|-------------------|
| **Admin** | System Administrator | Full system access, user/role management, system configuration |
| **Front Office** | Registration & Reception | Patient registration, appointments, triage, vital signs, check-in |
| **Clinician** | Doctors & Nurses | Clinical encounters, diagnoses, orders (lab/radiology/prescriptions), patient records |
| **Lab Staff** | Laboratory Technicians | Lab order processing, sample collection/tracking, result entry, quality control |
| **Pharmacy Staff** | Pharmacists & Technicians | Prescription dispensing, inventory management, drug interactions, formulary |
| **Radiology Staff** | Radiologists & Technicians | Radiology order processing, image upload (PACS), report entry |
| **Finance** | Billing & Accounts | Invoice creation, payment processing, NHIS claims, financial reports |
| **Management** | Hospital Administrators | Reports, analytics, dashboards (read-only) |

---

## 🔄 Complete Workflows by Role

### 1. Front Office Staff Workflow

#### Daily Tasks
1. **Login** → Dashboard
2. **Patient Registration** (if new patient)
   - Navigate: Front Office → Patient Registration
   - Enter patient demographics
   - System auto-generates Patient ID (DGMS-XXXXX)
   - Save patient record
3. **Appointment Management**
   - Navigate: Front Office → Appointment & Queue
   - View today's appointments by department
   - Check-in patients as they arrive
   - Update appointment status
4. **Triage & Vital Signs**
   - Navigate: Front Office → Triage & Vitals
   - Search for patient
   - Record vital signs (BP, temperature, pulse, etc.)
   - Save triage data
5. **Billing (if authorized)**
   - Navigate: Billing & Payments
   - View invoices
   - Process payments
   - Print receipts

#### Patient Check-in Process
1. Go to **Appointment & Queue**
2. Find patient in the list
3. Click **"Check In"** button
4. Select appointment status (Checked In, In Progress, etc.)
5. Patient appears in doctor's queue

---

### 2. Clinician (Doctor/Nurse) Workflow

#### Patient Consultation Process

**Step 1: Access Patient Queue**
- Navigate: Dashboard → **Appointments** or **Pending Encounters**
- View list of checked-in patients
- Click on patient name to view details

**Step 2: Create/View Encounter**
- If new encounter: Click **"New Encounter"** button
- If existing: Click on encounter from patient records
- Fill in clinical information:
  - Chief Complaint
  - History of Present Illness
  - Physical Examination
  - Assessment/Diagnosis
  - Plan

**Step 3: Add Orders (Lab, Radiology, Prescriptions)**

**Lab Orders:**
- In encounter page, scroll to **"Lab Orders"** section
- Click **"Add Lab Order"**
- Enter test name, priority, instructions
- Submit order
- Order appears in Lab dashboard

**Radiology Orders:**
- In encounter page, scroll to **"Radiology Orders"** section
- Click **"Add Radiology Order"**
- Enter study type, body part, priority
- Submit order
- Order appears in Radiology dashboard

**Prescriptions:**
- In encounter page, scroll to **"Prescriptions"** section
- Click to expand prescription form
- **Medication Search:**
  - Type medication name → See autocomplete with stock status
  - Select from inventory (links medication_id) OR
  - Type free text for medications not in inventory
- Enter dosage, frequency, duration, quantity, instructions
- Click **"Add Prescription"**
- Prescription appears in Pharmacy dashboard
- Can add multiple prescriptions without leaving page (AJAX)

**Step 4: Complete Encounter**
- Review all orders and documentation
- Click **"Complete Encounter"** button
- Encounter is finalized

#### Viewing Patient Records
- Navigate: **Clinical Services → Patient EHR Search**
- Search by: Name, Patient ID (DGMS-XXXXX), Phone, Date of Birth
- Click on patient to view:
  - Demographics
  - All encounters
  - Lab results
  - Radiology reports
  - Prescriptions
  - PACS images (if available)

#### Viewing Pending Orders
- **Pending Lab Results:** Dashboard → Pending Lab Results
- **Pending Radiology:** Dashboard → Pending Radiology
- **Pending Prescriptions:** Dashboard → Pending Prescriptions (if applicable)

---

### 3. Lab Staff Workflow

#### Processing Lab Orders

**Step 1: View Pending Orders**
- Navigate: **Laboratory (LIS) → Lab Dashboard**
- View list of pending lab orders
- Orders show: Patient name, test name, priority, ordered by

**Step 2: Sample Collection**
- Click on order to view details
- Navigate: **Sample Tracking**
- Create sample record:
  - Select order
  - Enter collection date/time
  - Assign sample ID/barcode
  - Update status to "Collected"

**Step 3: Sample Receipt (if collected elsewhere)**
- Navigate: **Sample Tracking**
- Find sample by ID/barcode
- Mark as "Received"
- Sample moves to processing queue

**Step 4: Result Entry**
- Navigate: **Lab Dashboard**
- Click on order → **"Enter Results"**
- Enter test results:
  - Values for each test component
  - Reference ranges (auto-populated)
  - Flags for abnormal values
  - Comments/notes
- Save results
- Results visible to ordering clinician

**Step 5: Quality Control**
- Navigate: **Quality Control**
- Enter QC results for controls
- Review QC charts
- Verify system accuracy

#### Test Catalog Management
- Navigate: **Test Catalog**
- Add/edit test definitions
- Set reference ranges
- Configure test parameters

---

### 4. Pharmacy Staff Workflow

#### Prescription Dispensing Process

**Step 1: View Pending Prescriptions**
- Navigate: **Pharmacy (PhIS) → Pharmacy Dashboard**
- View list of pending prescriptions
- Prescriptions show: Patient, medication, dosage, quantity

**Step 2: Review Prescription**
- Click on prescription to view details
- System shows:
  - **Stock Availability:** In Stock / Low Stock / Out of Stock
  - **Formulary Compliance:** NHIS coverage, formulary status
  - **Drug Interactions:** Warnings if applicable
  - **Patient Information**

**Step 3: Dispense Medication**

**If Medication is IN STOCK:**
- Select stock batch (if multiple available)
- Click **"Mark as Dispensed"**
- System:
  - Updates inventory (reduces stock)
  - Creates inventory transaction
  - Marks prescription as completed
  - Auto-creates charge for billing

**If Medication is OUT OF STOCK or NOT IN INVENTORY:**
- System automatically shows **"Print Prescription"** button
- Click to print prescription on thermal receipt printer
- Patient receives printed prescription to take to another pharmacy
- Prescription marked appropriately

**Step 4: Inventory Management**
- Navigate: **Inventory Management**
- View medication stock levels
- Add new medications
- Add stock to existing medications
- Adjust stock (add, remove, expiry, damage)
- View low stock alerts
- Manage suppliers

#### Medication Search & Linking
- When doctor prescribes:
  - If medication selected from inventory → Linked via `medication_id`
  - If typed manually → No link (free text)
- Pharmacy sees:
  - Linked medications: Direct inventory check, instant stock status
  - Unlinked medications: Matching by code/name, or marked as "Not in Inventory"

---

### 5. Radiology Staff Workflow

#### Processing Radiology Orders

**Step 1: View Pending Orders**
- Navigate: **Radiology → Radiology Dashboard**
- View list of pending radiology orders
- Orders show: Patient, study type, priority, body part

**Step 2: Schedule/Perform Study**
- Click on order to view details
- Navigate: **Radiology Schedule** (if scheduling needed)
- Update order status as study progresses

**Step 3: Upload Images (PACS)**
- Navigate: **PACS Images**
- Click **"Upload Image"**
- Select radiology order
- Upload image file (DICOM, JPEG, PNG)
- Enter metadata:
  - Image number
  - Study type
  - Body part
  - Image type
  - Study description
- Save image
- Image linked to order

**Step 4: Enter Report**
- In order detail page
- Click **"Enter Report"**
- Enter radiology findings
- Save report
- Report visible to ordering clinician

**Step 5: View Images**
- Navigate: **PACS Images**
- Filter by order, patient, date
- Click on image to view
- Add annotations if needed
- Download images

---

### 6. Finance Staff Workflow

#### Invoice & Payment Processing

**Step 1: View Invoices**
- Navigate: **Billing & Payments**
- View list of invoices
- Filter by status, patient, date

**Step 2: Create Invoice (if needed)**
- Click **"Create Invoice"**
- Select patient
- Add charges:
  - Service type (consultation, lab, radiology, pharmacy, etc.)
  - Quantity
  - Unit price (from Service Pricing if configured)
- Apply discounts/taxes if applicable
- Save invoice

**Step 3: Process Payment**
- Click on invoice to view details
- Click **"Process Payment"**
- Enter:
  - Payment amount
  - Payment method (Cash, Mobile Money, Card, Bank Transfer, NHIS)
  - Transaction reference (if applicable)
  - Receipt number (if applicable)
- Submit payment
- **Receipt automatically prints** on thermal receipt printer

**Step 4: Print Receipt**
- After payment, receipt page opens automatically
- Or click **"Print Receipt"** button on invoice page
- Receipt formatted for 80mm thermal printer
- Contains:
  - Hospital header (name, logo, address)
  - Receipt number, date
  - Patient information
  - Payment details
  - Invoice charges summary
  - Footer with received by, timestamp

**Step 5: NHIS Claims (if applicable)**
- Navigate: **NHIS Claims** (if module enabled)
- Create claim for NHIS-covered services
- Submit claim
- Track claim status

#### Service Pricing Management
- Navigate: **System Admin → Service Pricing**
- Set prices for:
  - Consultations
  - Lab tests
  - Radiology studies
  - Pharmacy items
  - Other services
- Prices used for automatic charge creation

---

### 7. Admin Workflow

#### User Management
1. Navigate: **System Admin → User & Role Management**
2. **Add New User:**
   - Click **"Add New User"**
   - Enter: Username, Full Name, Email, Password
   - Select Role
   - Save user
3. **Edit User:**
   - Click on user
   - Update information
   - Change role if needed
4. **Role Permissions:**
   - Navigate: **System Admin → Role Permissions**
   - Select role
   - Check/uncheck permissions
   - Save changes

#### Hospital Settings
1. Navigate: **System Admin → Hospital Settings**
2. Enter:
   - Hospital Name
   - Address
   - Phone, Email
   - Upload Logo
3. Save settings
4. Logo and name appear on:
   - Login page
   - Receipts
   - Reports

#### Service Pricing
1. Navigate: **System Admin → Service Pricing**
2. **Add Service:**
   - Service name, code
   - Charge type (consultation, lab, radiology, pharmacy, etc.)
   - Category
   - Unit price
   - Currency (GHS)
   - Description
3. **Edit/Delete** services as needed
4. Prices automatically used when creating charges

#### System Settings
1. Navigate: **System Admin → DB/System Settings**
2. View system information
3. Export data (Patients, Invoices, etc.) in CSV/JSON format
4. View audit logs

---

## 📝 Common Tasks

### Searching for Patients
**All Roles (except Finance/Management):**
- Navigate: **Patient Records** or **Patient EHR Search**
- Search by:
  - Patient Name
  - Patient ID (DGMS-XXXXX)
  - Phone Number
  - Date of Birth
- Click on patient to view full record

### Printing Prescriptions
**When medication is out of stock or not in inventory:**
1. Pharmacy staff views prescription
2. System automatically shows **"Print Prescription"** button
3. Click button → Opens print view
4. Print on thermal receipt printer (80mm)
5. Patient receives prescription to take elsewhere

### Printing Payment Receipts
**After payment processing:**
1. Receipt page opens automatically
2. Or click **"Print Receipt"** from invoice page
3. Receipt formatted for thermal printer
4. Contains all payment and invoice details

### Viewing PACS Images
**For Clinicians and Radiology Staff:**
1. Navigate: **Radiology → PACS Images**
2. Filter by order, patient, date
3. Click on image thumbnail to view full image
4. View annotations if any
5. Download image if needed
6. **From Encounter Page:** View up to 4 thumbnails, click to see all

### Adding Multiple Prescriptions
**For Clinicians:**
1. In encounter page, expand **"Prescriptions"** section
2. Fill prescription form
3. Click **"Add Prescription"**
4. Prescription adds to list (no page reload)
5. Form clears automatically
6. Repeat for additional prescriptions
7. All prescriptions saved to encounter

### Inventory Stock Management
**For Pharmacy Staff:**
1. Navigate: **Inventory Management**
2. **Add Medication:**
   - Click **"Add New Medication"**
   - Enter medication details
   - Save
3. **Add Stock:**
   - Click on medication
   - Click **"Add Stock"**
   - Enter: Batch number, quantity, expiry date, supplier, purchase price
   - Save
4. **Adjust Stock:**
   - Click on stock item
   - Click **"Adjust Stock"**
   - Select type: Add, Remove, Expiry, Damage
   - Enter quantity
   - Save

---

## 🚀 Quick Reference

### Navigation Shortcuts

| Task | Navigation Path |
|------|----------------|
| Patient Registration | Front Office → Patient Registration |
| Appointments | Front Office → Appointment & Queue |
| Triage | Front Office → Triage & Vitals |
| Patient Search | Clinical Services → Patient EHR Search |
| Pending Encounters | Clinical Services → Pending Encounters |
| Lab Dashboard | Laboratory (LIS) → Lab Dashboard |
| Pharmacy Dashboard | Pharmacy (PhIS) → Pharmacy Dashboard |
| Inventory | Pharmacy (PhIS) → Inventory Management |
| Radiology Dashboard | Radiology → Radiology Dashboard |
| PACS Images | Radiology → PACS Images |
| Billing | Billing & Payments |
| Reports | Reports & Analytics |
| User Management | System Admin → User & Role Management |
| Hospital Settings | System Admin → Hospital Settings |
| Service Pricing | System Admin → Service Pricing |
| Role Permissions | System Admin → Role Permissions |

### Keyboard Shortcuts
- **Ctrl/Cmd + P** - Print current page
- **Esc** - Close modals/dropdowns

### Important Notes

1. **Patient IDs:** Auto-generated starting with "DGMS" (e.g., DGMS-00001)
2. **Prescriptions:** Medications not in inventory are automatically printable
3. **Receipts:** Formatted for 80mm thermal receipt printers
4. **Stock Alerts:** Low stock and expired items show on dashboard
5. **Drug Interactions:** Checked automatically when dispensing
6. **NHIS Coverage:** Verified during prescription review

---

## 🔧 Troubleshooting

### Common Issues

**Issue:** Cannot access a page
- **Solution:** Check your role permissions. Contact admin if you need access.

**Issue:** Medication not found in search
- **Solution:** Medication may not be in inventory. Type medication name manually.

**Issue:** Cannot print receipt
- **Solution:** Ensure printer is set as default. Check browser print settings.

**Issue:** Stock not updating
- **Solution:** Verify you selected correct batch. Check transaction log.

**Issue:** Prescription not showing in pharmacy
- **Solution:** Ensure encounter is saved. Check prescription status.

---

## 📞 Support

For technical support or questions:
- Contact your system administrator
- Refer to system documentation
- Check audit logs for error details

---

**End of Document**

