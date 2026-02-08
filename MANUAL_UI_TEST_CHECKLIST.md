# Manual UI Testing Checklist (admin / password123)

Use this checklist to test the application after logging in at **http://localhost:8001/login** with **username: admin**, **password: password123**.

---

## 1. Login & Dashboard
- [ ] Open http://localhost:8001/login
- [ ] Enter username: **admin**, password: **password123**
- [ ] Click **Sign in** → should redirect to Dashboard (/)
- [ ] Dashboard loads with sidebar and main content (no 500 error)

---

## 2. Front Office & Patients
- [ ] **Patients** → **Patients List** (`/patients/list`) – list loads
- [ ] **Patients** → **Register Patient** (`/patients/register`) – form loads
- [ ] **Front Office** → **Queue** (`/front-office/queue`) – queue page loads
- [ ] **Appointments** → **Manage Appointments** (`/appointments/manage`) – page loads
- [ ] **Direct Service Requests** – dashboard loads (if in sidebar)

---

## 3. Nurse
- [ ] **Nurse** → **Nurse Dashboard** (`/nurse/dashboard`)
- [ ] **Nurse** → **Triage Queue** (`/nurse/triage-queue`)
- [ ] Open a patient triage link → triage page loads (no payment block for vitals)

---

## 4. Doctor
- [ ] **Doctor** → **Doctor Dashboard** (`/doctor/dashboard`)
- [ ] **Doctor** → **Doctor Queue** (`/doctor/queue`)
- [ ] **Doctor** → **Appointments** (`/doctor/appointments`) if present

---

## 5. OPD
- [ ] **OPD** → **OPD Dashboard** (`/opd/dashboard`)

---

## 6. Emergency
- [ ] **Emergency** → **Emergency Dashboard** (`/emergency/dashboard`)
- [ ] **Emergency** → **Emergency Visits** (`/emergency/visits`) – list loads; filter by Active / Completed / All
- [ ] **Emergency** → **Quick Register (no details)** (`/emergency/quick-register`) – minimal form (gender, optional note); submit creates patient and redirects to triage; visit appears on Emergency page
- [ ] From Emergency Dashboard/Visits: **Admit to IPD** opens IPD admission form with patient pre-selected

---

## 7. IPD
- [ ] **IPD** → **IPD Dashboard** (`/ipd/dashboard`)
- [ ] **IPD** → **Wards** (`/ipd/wards`)
- [ ] **IPD** → **Admissions** (`/ipd/admissions`)
- [ ] **IPD** → **New Admission** (`/ipd/admissions/new`) – form loads
- [ ] Open an admission detail → **Record Vitals**, **Record Administration**, **Record Fluid** modals open and work

---

## 8. Pharmacy & Inventory
- [ ] **Pharmacy** → **Pharmacy** (`/pharmacy`) – dashboard loads (no 500)
- [ ] **Pharmacy** → **Inventory** (`/pharmacy/inventory`)
- [ ] **Formulary**, **Drug interactions**, **Suppliers** – pages load

---

## 9. Lab
- [ ] **Lab** → **Lab Dashboard** (`/lab`)
- [ ] **Lab Samples**, **QC**, **Lab Tests**, **Reference Ranges** – pages load

---

## 10. Radiology
- [ ] **Radiology** → **Radiology Dashboard** (`/radiology`)
- [ ] **Schedule**, **PACS** – pages load

---

## 11. Procedures
- [ ] **Procedures** → **Procedure Dashboard** (`/procedures/dashboard`) – stats and recent procedures
- [ ] **Procedures** → **Procedures List** (`/procedures`)
- [ ] **Procedure Catalog** (`/procedures/catalog`) – page loads
- [ ] **New Procedure** – form loads

## 12. Maternity (Antenatal + Births)
- [ ] **Maternity** → **Antenatal Dashboard** (`/midwife/dashboard`) – stats, recent and upcoming visits
- [ ] **Maternity** → **Antenatal Visits** (`/midwife/visits`) – list loads; View link opens visit detail
- [ ] **New Antenatal Visit** (`/midwife/visits/create`) – form with patient search, LMP, EDD, hemoglobin, blood group, supplements
- [ ] **Antenatal Visit Detail** (`/midwife/visits/{id}`) – view full visit; Edit, New Visit, Record Birth actions
- [ ] **Maternity** → **Births Dashboard** (`/births/dashboard`) – stats and recent births
- [ ] **Birth Records** (`/births`) – list with outcome filter; View link opens birth detail
- [ ] **Record Birth** (`/births/create`) – form with mother search, default today, length, head circ, Apgar 10min
- [ ] **Birth Record Detail** (`/births/{id}`) – view full record; mother's antenatal visits shown

---

## 12. Billing & Reports
- [ ] **Billing** → **Billing Dashboard** (`/billing`)
- [ ] **Claims** (NHIS / Private) – pages load
- [ ] **Reports** → **Reports Dashboard** (`/reports`)
- [ ] **Financial**, **Income statement**, **Demographics**, **Disease**, **Pharmacy**, **Lab**, **Radiology**, **OPD**, **IPD**, **Procedure**, **Expense** reports – each loads or redirects appropriately

---

## 15. Admin & Settings
- [ ] **Admin** → **User & Role Management** (`/admin/users`)
- [ ] **Doctors List** (`/doctors/list`)
- [ ] **Hospital Settings** (`/admin/hospital-settings`)
- [ ] **Service Pricing** (`/admin/service-pricing`)
- [ ] **Diseases** (`/admin/diseases`)
- [ ] **Insurance Providers** (`/insurance-providers`)
- [ ] **Ward Types**, **Departments**, **Shift Types**, **Bed Types**, **Procedure Catalog**
- [ ] **SMS Messaging** (if present)

---

## 16. Buttons & Forms (sample)
- [ ] On any list page: **Create** / **Add** buttons open forms or new pages
- [ ] **Save** / **Submit** on a form either saves or shows validation
- [ ] **Cancel** / **Back** returns to previous or list page
- [ ] **Logout** (top right) logs out and returns to login page

---

## Automated route test (optional)

With the app running and valid admin credentials:

```bash
cd /path/to/lhims
source venv/bin/activate
LHIMS_TEST_USER=admin LHIMS_TEST_PASSWORD=password123 python -m pytest tests/test_ui_routes_after_login.py -v
```

If login fails (401), create/reset admin with:

```bash
python scripts/seed_admin.py
```

Then use the credentials printed by the script (or the default admin/password123 if the script sets that).
