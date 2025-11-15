# 🧾 CHANGELOG — LHIMS (Local Health Information Management System)

**Project Goal:**  
To build a modular, offline-resilient, and scalable health information management system (LHIMS) using **FastAPI + Jinja2 + AdminLTE**, deployable on local Ubuntu desktops and scalable to national-level health infrastructure.

---

## 📆 Version History

### **v0.1.0 — Project Initialization (Phase 1 & 2 Complete)**  
**Date:** 2025-11-08  
**Author:** Sherifdeen Abubakari  

---

## 🧩 1. Project Setup Summary

**Project Name:** `LHIMS`  
**Environment:** Local Ubuntu 22.04 LTS  
**Python Version:** 3.10 +  
**Framework:** [FastAPI](https://fastapi.tiangolo.com/)  
**Templating Engine:** [Jinja2](https://jinja.palletsprojects.com/)  
**UI Framework:** [AdminLTE v3.2.0](https://adminlte.io/) (local copy)  
**Runtime Server:** [Uvicorn](https://www.uvicorn.org/)  
**License:** Internal / Proprietary (TBD)

---

## 🧰 2. Tech Stack Overview

| Layer | Technology | Purpose |
|:--|:--|:--|
| Backend | FastAPI | Asynchronous backend framework for API routes and HTML responses |
| Templating | Jinja2 | Server-side rendering of AdminLTE HTML templates |
| Frontend | AdminLTE 3.2 (Bootstrap 5) | Responsive admin dashboard layout |
| Static Assets | Local `/static/adminlte/` | Offline CSS/JS hosting |
| Web Server | Uvicorn (ASGI) | Local server for dev & production |
| Environment | Ubuntu Desktop | Single machine deployment |
| Version Control | Git | Track changes and branches |
| Database (planned) | SQLite (local) + PostgreSQL (central) | Offline-first design |
| ORM (planned) | SQLAlchemy + Alembic | Schema & migrations |
| Auth (planned) | OAuth2 + JWT | Role-based access |
| Dashboard UI | AdminLTE | Consistent UI across modules |
| Front-end Deps | Bootstrap 5, jQuery, Font Awesome | Bundled with AdminLTE |

---

## 📦 3. Python Dependencies Installed

```bash
pip install fastapi uvicorn[standard] sqlalchemy alembic jinja2 python-multipart

## 4. Directory Structure (Phase 2)
lhims/
├── app/
│   ├── main.py
│   ├── templates/
│   │   ├── base.html
│   │   └── index.html
│   ├── static/
│   │   ├── adminlte/
│   │   │   ├── css/
│   │   │   ├── js/
│   │   │   └── plugins/
│   │   └── custom/
│   ├── routers/
│   ├── models/
│   ├── schemas/
│   ├── db/
│   ├── core/
│   └── __init__.py
├── venv/
└── CHANGELOG.md

# 5. Core Configuration app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="LHIMS")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Welcome"})

# 6. AdminLTE Integration - Version: v3.2.0 (local) Installation Steps
cd app/static/adminlte
wget https://github.com/ColorlibHQ/AdminLTE/archive/refs/tags/v3.2.0.zip -O adminlte.zip
unzip adminlte.zip
mv AdminLTE-3.2.0/dist/* .
mv AdminLTE-3.2.0/plugins/* plugins/
rm -rf AdminLTE-3.2.0 adminlte.zip

# 7. Templating
#base.html
<link rel="stylesheet" href="/static/adminlte/css/adminlte.min.css">
<link rel="stylesheet" href="/static/adminlte/plugins/fontawesome-free/css/all.min.css">
<script src="/static/adminlte/plugins/jquery/jquery.min.js"></script>
<script src="/static/adminlte/plugins/bootstrap/js/bootstrap.bundle.min.js"></script>
<script src="/static/adminlte/js/adminlte.min.js"></script>

#index.html
{% extends "base.html" %}
{% block content %}
<section class="content p-4">
  <div class="container-fluid">
    <div class="alert alert-info">
      <h5>✅ FastAPI + AdminLTE Installed</h5>
      <p>Integration verified successfully.</p>
    </div>
  </div>
</section>
{% endblock %}

# 8. Development Commands
Command	Purpose
source venv/bin/activate	Activate virtual environment
uvicorn app.main:app --reload	Start dev server
pip freeze > requirements.txt	Record dependencies
deactivate	Exit environment

#9. Verification Checklist
Feature	Status	Notes
FastAPI app	✅	Runs successfully
Jinja2 templates	✅	Rendered index.html
Static assets	✅	AdminLTE CSS/JS served
Offline operation	✅	All assets local
Database engine	⏳	Phase 3
Auth module	⏳	Phase 4
Registration module	⏳	Phase 5

#10. Next Phase — Core & Database Setup (Phase 3)

Goals

Create core/config.py, db/database.py

Initialize SQLAlchemy engine + session

Add first model Patient

Integrate Alembic for migrations

Configure SQLite (local) → PostgreSQL (central)

Expected Deliverables

Database connected to FastAPI

migrations/ folder created

First table created via Alembic


#11. Security & Version Control

Add .env for environment variables

Create .gitignore excluding venv/, .env, __pycache__/, *.db

Restrict LAN access until HTTPS enabled

All AdminLTE assets hosted locally for privacy & offline use

#12. Summary of Accomplishments

✅ FastAPI + Jinja2 skeleton
✅ Local AdminLTE integration (off-grid ready)
✅ Organized modular folder structure
✅ Verified server startup and template rendering
✅ Prepared for Phase 3 (DB foundation)


✅ PHASE 3 COMPLETION CHECKLIST
Component	Description	Status
PostgreSQL Installed	Server running on Ubuntu	✅
Database Created	lhims with user lhims_user	✅
SQLAlchemy Configured	Using Postgres driver	✅
Alembic Migrations	Successful creation of tables	✅
Verified Connection	Uvicorn startup tested	✅
🚀 Next Phase Options

Now you’re production-ready with PostgreSQL.
You can choose what to build next:

Option	Description
A. Phase 4 – Authentication System	Users table, role-based access, JWT login
B. Phase 5 – Patient Registration UI	Web form + API endpoint to add patients
C. Phase 6 – AdminLTE Dashboard	Add dashboard cards and metrics

# 🧾 CHANGELOG — LHIMS (Local Health Information Management System)

**Project Goal:** To build a modular, offline-resilient, and scalable health information management system (LHIMS) using **FastAPI + Jinja2 + AdminLTE**, deployable on local Ubuntu desktops and scalable to national-level health infrastructure.

---

## 📆 Version History

### **v0.1.0 — Project Initialization (Phase 1 & 2 Complete)** **Date:** 2025-11-08  
**Author:** Sherifdeen Abubakari  

---

## 🧩 1. Project Setup Summary

| Layer | Technology | Purpose |
|:--|:--|:--|
| Backend | FastAPI | Asynchronous backend framework for API routes and HTML responses |
| Templating | Jinja2 | Server-side rendering of AdminLTE HTML templates |
| Frontend | AdminLTE 3.2 (Bootstrap 5) | Responsive admin dashboard layout |
| Runtime Server | Uvicorn | High-performance ASGI server |
| Static Assets| Local AdminLTE | Ensures offline resilience & security |

---

## 🧰 2. Tech Stack Overview

| Feature | Status | Notes |
|:---|:---|:---|
| FastAPI app | ✅ | Runs successfully |
| Jinja2 templates | ✅ | Rendered index.html |
| Static assets | ✅ | AdminLTE CSS/JS served locally |
| Database engine | ✅ | PostgreSQL connected via SQLAlchemy |
| Auth module | ✅ | JWT-based authentication implemented |
| RBAC core | ✅ | Role-based access control core implemented |
| Registration module | ⏳ | Next Phase |

---

### **v0.2.0 — Phase 3-7: Database & Authentication Core**
**Date:** 2025-11-09
**Author:** Sherifdeen Abubakari

**Goals:** Establish the database connection and the core FastAPI security module (Models, Schemas, JWT logic).

**Changes:**

1.  **DB Core:** Created `app/core/config.py` and `app/db/database.py` to manage connection settings and SQLAlchemy engine.
2.  **Models:** Created core ORM models for `User` and `Role` (`app/models/user_models.py`).
3.  **Alembic:** Initialized and configured Alembic for database migrations.
4.  **Schemas:** Created Pydantic schemas for data validation (`app/schemas/user_schemas.py`, `app/schemas/token_schemas.py`).
5.  **Security:** Implemented JWT token creation and password hashing (`app/core/security.py`).
6.  **API:** Created the `/token` API endpoint (`app/routers/auth.py`) that returns a JWT upon successful login.

---

### **v0.4.0 — Phase 8-11: PostgreSQL, Seeding, & Security Layer**
**Date:** 2025-11-09
**Author:** Sherifdeen Abubakari

**Goals:** Migrate the project to PostgreSQL. Create seed data. Implement custom UI styling. Implement and stabilize the full security layer (JWT cookie validation, RBAC, and global 401 handling).

**Changes:**

**Phase 8: PostgreSQL Migration & Seeding**
1.  **Dependency:** Added `psycopg2-binary` for PostgreSQL connection.
2.  **Core:** Modified `app/db/database.py` to remove SQLite-specific `connect_args`.
3.  **Seeding:** Created and ran `scripts/seed_admin.py` to:
    * Seed all core roles (Admin, Clinician, Front Office, etc.).
    * Create the default admin user: **Username: `admin` / Password: `password`**.

**Phase 10: UI Theme Customization**
1.  **Custom CSS:** Created `app/static/custom/custom.css` to add accent colors (blue headers, orange action buttons) matching the provided screenshots.
2.  **Templates:** Updated `app/templates/base.html` to load `custom.css`.
3.  **Layout:** Updated `app/templates/index.html` with the full AdminLTE structure (dark sidebar, white navbar) and initial role-based navigation logic.

**Phase 11: Security Layer & RBAC Core**
1.  **Dependencies:** Created `app/core/deps.py` with `get_current_user` (validates JWT cookie) and `role_required` (RBAC core).
2.  **Security Enforcement:** Applied `Depends(get_current_user)` to the `GET /` dashboard route, forcing the login page (`/login`) as the true landing page.
3.  **Login Flow Fix:** Revised `app/routers/ui_routes.py` to ensure `request.url_for()` is explicitly cast to `str()` when used with the internal `httpx` client, resolving `TypeError`.
4.  **Global Handler Fix:** Modified the global exception handler in `app/main.py` to correctly:
    * Redirect UI route 401s to `/login`.
    * Return a standard **JSON 401** error for the internal `/token` API, resolving the critical communication error during form login.

**Verification Checklist (Phase 8-11)**
| Feature | Status | Notes |
|:---|:---|:---|
| PostgreSQL Connection | ✅ | Stable and running |
| Admin User Login | ✅ | Verified: `admin`/`password` successfully redirects to dashboard |
| UI Theme | ✅ | Dark sidebar, blue/orange accents implemented |
| Dashboard Protection | ✅ | Unauthorized access redirects to `/login` |
| RBAC Template Logic | ✅ | Sidebar menus display based on `user_role` variable |

**Next Phase — Patient Registration Module**
* **Target:** Implement **Step 1: Patient Registration & Triage Workflow**.
* **Task:** Create the necessary API, Pydantic schemas, and AdminLTE form for adding new patients.

---

### **v0.5.0 — Appointment/Queue Management & Financial Screening (Workflow Steps 2 & 3)**
**Date:** 2025-01-XX  
**Author:** Sherifdeen Abubakari 

**Goals:** Implement Appointment/Queue Management (Workflow Step 2) and Financial Screening (Workflow Step 3) to complete the Front Office workflow.

**Changes:**

**1. Appointment/Queue Management System (Workflow Step 2)**
   - **Models:** Created `app/models/appointment_models.py` with `Appointment` model supporting:
     - Multiple appointment types (Walk-In, Scheduled, Emergency, Follow-Up)
     - Appointment status tracking (Scheduled, Checked-In, In-Progress, Completed, Cancelled, No-Show)
     - Queue number assignment per department
     - Priority levels (1-10 scale)
     - Department-based scheduling
     - Chief complaint and notes fields
   - **Schemas:** Created `app/schemas/appointment_schemas.py` with Pydantic schemas for appointment data validation
   - **CRUD:** Created `app/crud/appointment_crud.py` with operations for:
     - Creating appointments with automatic queue number assignment
     - Retrieving appointments by patient, department, or status
     - Updating appointment status with automatic timestamp tracking
     - Getting today's queue with filtering
   - **API:** Created `app/routers/appointment_api.py` with endpoints for:
     - Creating appointments via form submission
     - Updating appointment status
     - Viewing appointment queue with department filtering
   - **UI:** Created `app/templates/front_office/queue.html` for queue management interface

**2. Financial Screening (Workflow Step 3)**
   - **Patient Model Enhancement:** Updated `app/models/patient_models.py` to include:
     - Payment mechanism enum (Cash, NHIS, Private Insurance, Self-Pay)
     - NHIS membership number field
     - Private insurance provider and policy number fields
   - **Patient Schema Update:** Updated `app/schemas/patient_schemas.py` to include financial screening fields
   - **Registration Form:** Enhanced `app/templates/front_office/register_patient.html` with:
     - Payment mechanism selection dropdown
     - Conditional display of NHIS fields when NHIS is selected
     - Conditional display of private insurance fields when Private Insurance is selected
     - JavaScript for dynamic form field visibility
   - **API Update:** Updated `app/routers/patient_api.py` to handle financial screening data during registration
   - **Triage Page:** Updated `app/templates/front_office/triage_page.html` to display financial screening information

**3. Enhanced Triage Workflow**
   - **Appointment Creation:** Added appointment creation form to triage page
   - **Workflow Integration:** Integrated appointment creation with patient registration and triage workflow
   - **Financial Display:** Added financial screening information display on triage page

**4. Authentication Fix**
   - **Cookie-Based Auth:** Fixed login and redirection by implementing HTTP-only cookie-based authentication
   - **Security:** Replaced `OAuth2PasswordBearer` (header-based) with cookie-based token storage
   - **Login Flow:** Updated login form to use server-side form submission with cookie setting
   - **Logout:** Enhanced logout endpoint to clear authentication cookie

**Verification Checklist (v0.5.0)**
| Feature | Status | Notes |
|:---|:---|:---|
| Appointment Model | ✅ | Supports all appointment types and statuses |
| Queue Management | ✅ | Automatic queue number assignment per department |
| Financial Screening | ✅ | Cash, NHIS, and Private Insurance support |
| Patient Registration | ✅ | Includes financial screening in registration form |
| Triage Workflow | ✅ | Integrated with appointment creation |
| Queue UI | ✅ | Department-filtered queue view |
| Authentication | ✅ | Cookie-based authentication working correctly |
| Database Migration | ⏳ | Migration script needed for new models |

**Next Phase — Clinical Encounter Module (Workflow Steps 5-7)**
* **Target:** Implement **Clinical Encounter Workflow** (Encounter Access, Diagnosis & Orders, Order Management).
* **Tasks:** 
  - Create Encounter model and clinical documentation
  - Implement CPOE (Computerized Provider Order Entry)
  - Create order management system for Lab, Radiology, and Pharmacy
  - Integrate with diagnosis coding (ICD-10)

---

### **v0.6.0 — Patient Medical Records (EHR/EMR) Viewing**
**Date:** 2025-01-XX  
**Author:** Sherifdeen Abubakari  

**Goals:** Implement comprehensive patient medical records viewing for doctors, nurses, and clinical staff to access patient history over the years.

**Changes:**

**1. Patient Search Functionality**
   - **Search API:** Created `app/routers/patient_records_api.py` with patient search endpoint
   - **Search Criteria:** Search by name, national ID, or phone number
   - **Search UI:** Created `app/templates/clinical/patient_search.html` for patient search interface
   - **Access Control:** Accessible by Admin, Clinician, Front Office, and Nurses

**2. Patient Medical Records View**
   - **Records Page:** Created comprehensive patient medical records view page
   - **Demographics Display:** Full patient demographics with age calculation
   - **Appointment History:** Complete appointment history with status, department, and details
   - **Vital Signs History:** All vital signs records chronologically
   - **Timeline View:** Combined timeline of all patient interactions (appointments + vitals)
   - **Statistics:** Summary statistics (appointment count, vitals count, patient since date)
   - **UI:** Created `app/templates/clinical/patient_records.html` with timeline and tables

**3. Medical History Timeline**
   - **Chronological View:** Timeline showing all patient interactions in chronological order
   - **Event Types:** Distinguishes between appointments and vital signs recordings
   - **Detailed Information:** Shows complete details for each event
   - **Visual Timeline:** AdminLTE timeline component for visual representation

**4. Navigation Integration**
   - **Sidebar Link:** Added "Patient EHR Search" link to Clinical Services menu
   - **Breadcrumbs:** Added breadcrumb navigation for easy navigation
   - **Quick Actions:** Quick links to triage and other patient actions

**Verification Checklist (v0.6.0)**
| Feature | Status | Notes |
|:---|:---|:---|
| Patient Search | ✅ | Search by name, ID, or phone |
| Medical Records View | ✅ | Comprehensive patient history |
| Appointment History | ✅ | All appointments displayed |
| Vital Signs History | ✅ | All vitals displayed |
| Timeline View | ✅ | Chronological timeline |
| Access Control | ✅ | Restricted to clinical staff |
| Navigation | ✅ | Integrated into sidebar |

**Next Phase — Clinical Encounter Module (Workflow Steps 5-7)**
* **Target:** Implement **Clinical Encounter Workflow** (Encounter Access, Diagnosis & Orders, Order Management).
* **Tasks:** 
  - Create Encounter model and clinical documentation
  - Implement CPOE (Computerized Provider Order Entry)
  - Create order management system for Lab, Radiology, and Pharmacy
  - Integrate with diagnosis coding (ICD-10)
---

### **v0.10.0 — Complete System Implementation**
**Date:** 2025-11-09  
**Author:** Sherifdeen Abubakari  

**Goals:** Implement all remaining features including main dashboard, lab test catalog, reference ranges, supplier management, audit logging, user management, system settings, data export, print functionality, radiology scheduling, and comprehensive alerts system.

**Changes:**

**1. Main Dashboard with Real-Time Metrics**
   - **Dashboard API:** Enhanced dashboard route with comprehensive statistics
   - **Metrics Display:** Patient, appointment, encounter, order statistics
   - **Financial Metrics:** Revenue today/month, outstanding invoices
   - **Inventory Alerts:** Low stock, expired items, out of stock counts
   - **Lab Statistics:** Pending samples tracking
   - **Role-Based Content:** Dashboard content varies by user role
   - **UI:** Created comprehensive dashboard template with metric cards and quick actions

**2. Lab Test Catalog Management**
   - **Model:** Created `LabTest` model with test information, categories, specimen types, pricing
   - **CRUD:** Created `lab_catalog_crud.py` with full CRUD operations
   - **Schemas:** Created `lab_catalog_schemas.py` for data validation
   - **API:** Created `lab_catalog_api.py` with test catalog dashboard and management
   - **UI:** Created test catalog dashboard with search, filtering, and test detail views
   - **Reference Ranges:** Enhanced reference ranges to link to lab tests
   - **Reference Ranges UI:** Created reference ranges management dashboard

**3. Supplier Management**
   - **Model:** Created `Supplier` model with contact information, business details, payment terms
   - **CRUD:** Created `supplier_crud.py` with full CRUD operations
   - **Schemas:** Created `supplier_schemas.py` for data validation
   - **API:** Created `supplier_api.py` with supplier dashboard and management
   - **UI:** Created supplier dashboard with search and supplier detail views
   - **Integration:** Linked stock items to suppliers

**4. Audit Logging System**
   - **Model:** Created `AuditLog` model with action tracking, user attribution, IP address, request details
   - **CRUD:** Created `audit_crud.py` with log creation and filtering
   - **Schemas:** Created `audit_schemas.py` for data validation
   - **Middleware:** Created `audit_middleware.py` for automatic request logging (optional)
   - **API:** Created audit logs dashboard in `admin_api.py`
   - **UI:** Created audit logs dashboard with filtering by user, action, resource type, date range

**5. User Management Interface**
   - **API:** Created user management dashboard in `admin_api.py`
   - **UI:** Created user management page with user listing, search, and role display
   - **Features:** User search by username, name, or email

**6. System Settings Interface**
   - **API:** Created system settings page in `admin_api.py`
   - **UI:** Created system settings page with system information and quick export actions
   - **Features:** System version, database info, quick export links

**7. Data Export Functionality**
   - **API:** Created export endpoints in `admin_api.py` for CSV and JSON export
   - **Supported Resources:** Patients, invoices (expandable)
   - **Audit Trail:** Export actions logged in audit trail
   - **Formats:** CSV and JSON export formats

**8. Print Functionality**
   - **Print Buttons:** Added print buttons to invoice detail, patient records, and encounter pages
   - **Print Styles:** Added print-friendly CSS in base template
   - **Features:** Hides navigation and buttons when printing, page-break optimization

**9. Radiology Study Scheduling**
   - **API:** Created `radiology_scheduling_api.py` with scheduling dashboard
   - **UI:** Created radiology schedule page with date selection and study listing
   - **Features:** View scheduled studies by date, filter pending orders

**10. Comprehensive Alerts System**
   - **Inventory Alerts:** Created inventory alerts dashboard showing low stock, expired items, reorder needed
   - **Critical Value Alerts:** Created critical value alerts for lab results
   - **Allergy Alerts:** Created allergy alerts for prescriptions
   - **API:** Created `alerts_api.py` with all alert endpoints
   - **UI:** Created alert dashboards for each alert type
   - **Integration:** Alerts linked to inventory, lab results, and prescriptions

**11. Database Migrations**
   - **Migration:** Created migration for lab tests, suppliers, and audit logs tables
   - **Enum Types:** Created `auditaction` enum type
   - **Foreign Keys:** Added foreign keys for reference ranges to lab tests, stock items to suppliers

**12. Navigation Updates**
   - **Sidebar:** Added links for all new features in sidebar navigation
   - **Role-Based Menus:** Updated menu visibility based on user roles
   - **Quick Access:** Added quick action links in dashboard

**Verification Checklist (v0.10.0)**
| Feature | Status | Notes |
|:---|:---|:---|
| Main Dashboard | ✅ | Real-time metrics and statistics |
| Lab Test Catalog | ✅ | Full CRUD with UI |
| Reference Ranges UI | ✅ | Management dashboard |
| Supplier Management | ✅ | Full CRUD with UI |
| Audit Logging | ✅ | Model, CRUD, and UI |
| User Management UI | ✅ | User listing and search |
| System Settings UI | ✅ | System info and exports |
| Data Export | ✅ | CSV and JSON export |
| Print Functionality | ✅ | Print buttons and styles |
| Radiology Scheduling | ✅ | Scheduling dashboard |
| Alerts System | ✅ | Inventory, critical values, allergies |
| Database Migrations | ✅ | All migrations applied |

**Next Phase — NHIS Claims Integration**
* **Target:** Implement **NHIS Claims Integration** when NHIA API becomes available.
* **Tasks:** 
  - NHIS eligibility checking
  - Claim packaging
  - Claim submission
  - Claim tracking
