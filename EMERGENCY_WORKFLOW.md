# Emergency Department Workflow

Emergency is treated like **detention/IPD-style care**: patients can receive care **without full details first**. When stabilized, they can be transferred to IPD.

---

## Overview

- **Emergency** = immediate care area (accident, true emergency, or transferred patients).
- **Care without details** = patient can be triaged and treated before name, ID, or full registration are taken.
- **Outcome**: When the patient is **stabilized**, they are **admitted to IPD** (or discharged if no longer needed).

---

## Workflow

### 1. Entry (no full registration required)

- **Quick Register (no details)**  
  **Emergency → Quick Register (no details)**  
  Minimal data: Gender (Male/Female/Unknown), optional brief note (e.g. Accident, Transferred, RTA).  
  Creates a minimal patient (e.g. "Unknown Emergency") and sends them straight to **emergency triage**. Full registration can be done later when the patient is identified or stabilized.

- **Full registration with Emergency box**  
  **Patients → Register Patient** → check "Emergency case".  
  Creates a full patient record and an emergency appointment, then redirects to triage with emergency flag.

### 2. Emergency triage

- Patient lands on **triage** (from Quick Register or from emergency registration).
- Record vitals and initial assessment; payment is not required before emergency care.
- Emergency visits appear on **Emergency Dashboard** and **Emergency Visits**.

### 3. Care

- Doctor/clinician can start an encounter, order labs, prescribe, etc., as for any OPD visit.
- Emergency visits are tagged with `visit_type = emergency` and `payment_status = emergency` so they are clearly separated from routine OPD.

### 4. When stabilized → Admit to IPD

- From **Emergency Dashboard** or **Emergency Visits**, use **Admit to IPD** for the active emergency visit.
- This opens the IPD admission form with the patient pre-selected. Complete ward/bed and admission details to admit the patient to IPD.
- After admission, the patient is managed in IPD (ward, bed, notes, discharge, etc.).

### 5. Updating patient details later

- For Quick-Register patients (e.g. "Unknown Emergency"), use **Patients → Edit** or **View Patient Records → Edit** once the patient is identified, to add name, DOB, ID, contact, and payment mechanism.

---

## Summary

| Step              | Action                                                                 |
|-------------------|------------------------------------------------------------------------|
| Entry             | Quick Register (no details) or Full Registration with Emergency box   |
| Triage            | Emergency triage; care without payment first                          |
| Care              | Encounter, orders, prescriptions as needed                             |
| Stabilized        | **Admit to IPD** from Emergency Dashboard or Emergency Visits          |
| Later             | Update patient details when identified                                |

Emergency is not just "OPD with emergency flag" – it is a **care-first** path (like detention/IPD triage) with optional **Admit to IPD** when the patient is stabilized.
