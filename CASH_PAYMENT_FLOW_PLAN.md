# Cash Payment Flow Change — Plan for Confirmation

## 1. Current Behaviour (Pay Every Step)

| Step | Current behaviour |
|------|-------------------|
| **Registration** | Cash patients are redirected to **pay consultation** before triage (`/patients/{id}/pay/consultation?return_to=triage`). |
| **Triage (vitals)** | Cash patients must have **paid consultation** before vitals can be recorded. |
| **Check-in** | Cash patients must have **paid consultation** before check-in. |
| **Encounter (see doctor)** | `verify_encounter_workflow` requires **consultation paid** before creating encounter. |
| **Lab** | Charge is created **when doctor orders** lab. Payment is required **before lab result entry**. |
| **Radiology** | Charge is created **when doctor orders** radiology. Payment is required **before radiology report entry**. |
| **Pharmacy** | Charge is created **when prescription is dispensed**. Payment is required **before dispensing**. |

So today: **consultation is paid first** (before triage/check-in/encounter), then **lab/radiology/pharmacy each require payment before** their service.

---

## 2. Desired Behaviour (Clarified)

**Main flow (see doctor + labs → pay once → leave):**

1. **Walk-in** → Registration (no payment).
2. **Triage** → Vitals recorded (no payment).
3. **See doctor** → Encounter created, doctor sees patient (no payment).
4. **Doctor orders labs** → Lab charges added to visit invoice (consultation + lab).
5. **After labs** (lab orders in place) → Cash patient pays **once** (consultation + lab charges) → **patient can leave**.
6. Lab work (sample/result) can be done before or after this payment depending on your process; payment is the gate before they leave.

**Pharmacy and radiology — separate:**

- **Pharmacy (prescription)** and **radiology** are **not** part of this single payment. They are done **separate**.
- When the patient uses pharmacy or radiology, that is a **separate** payment (e.g. pay before dispense, pay before report), or a separate visit/invoice.
- So: **one payment = consultation + labs only**. After that they can leave. Prescription and radiology are paid when/if they use those services, separately.

---

## 2a. Implementation focus (from clarification)

- **Main flow:** Only **lab** is bundled with consultation for the single payment. Payment gate = "visit invoice (consultation + lab) paid" before lab result entry / before patient leaves.
- **Lab:** Require `has_visit_invoice_been_paid(encounter_id)` before lab result entry; redirect to pay consultation+lab if unpaid.
- **Pharmacy and radiology:** Do **not** change — keep current pay-before-dispense and pay-before-report (separate payment). No need to add them to the "visit invoice" or to create prescription/radiology charges on the same invoice as consultation+lab.

---

## 3. Summary of Code Changes

### 3.1 Payment verification (`app/utils/payment_verification.py`)

- **`requires_payment_before_service(..., ChargeType.CONSULTATION)`**  
  - For **OPD cash**: return **`False`** so that:
    - Triage does not require payment.
    - Check-in does not require payment.
    - Encounter creation does not require payment.
- **New rule for OPD cash:**  
  - “Payment required before **ancillary** service” = payment required before **any** of: lab result entry, radiology report entry, pharmacy dispense, procedure.  
  - Implement by: **require payment when the visit’s invoice (encounter/OPD visit) has balance > 0**, not per charge type.
- **New helper (suggested):**  
  - `requires_visit_payment_before_ancillary(db, encounter_id=None, opd_visit_id=None) -> bool`  
  - Returns True for OPD cash if the invoice for this encounter/visit exists and has unpaid balance; False if not cash or invoice is paid.
- **New helper (suggested):**  
  - `has_visit_invoice_been_paid(db, encounter_id=None, opd_visit_id=None) -> bool`  
  - Used by lab, radiology, pharmacy to allow service only when this is True (for cash OPD).

**IPD cash:** Keep current behaviour (admission at discharge; other services pay-as-you-go or as you decide). This plan focuses on **OPD cash**.

---

### 3.2 Registration (`app/routers/patient_api.py`)

- **Cash, non-emergency:**  
  - Do **not** redirect to `/patients/{id}/pay/consultation`.  
  - Redirect to triage, e.g. `/patients/{id}/triage?status=registered`.

---

### 3.3 Triage (`app/routers/triage_api.py`)

- **Remove** the check that requires consultation payment before recording vitals.  
- Allow recording vitals for cash patients without prior payment.  
- Optionally keep creating consultation charge only when it’s needed later (e.g. when encounter is created), not at triage.

---

### 3.4 Check-in (`app/routers/appointment_api.py`)

- **Remove** the block that requires consultation payment before check-in for cash patients.  
- Allow check-in after vitals only (no payment step).

---

### 3.5 Encounter workflow (`app/utils/payment_verification.py` + callers)

- **`verify_encounter_workflow(..., check_payment=True)`**  
  - For OPD cash: do **not** require consultation payment.  
  - So doctor can create encounter and see patient without prior payment.
- **Consultation charge:**  
  - Create when encounter is **created** (or when doctor “starts” encounter), so the visit invoice exists and includes consultation.  
  - Ensure one consultation charge per encounter/visit (no duplicate).

---

### 3.6 Charges created when doctor orders (already partly so)

- **Lab:** Already: charge created when doctor **creates** lab order (`encounter_api`). No change for timing; keep it.
- **Radiology:** Already: charge created when doctor **creates** radiology order. No change for timing.
- **Pharmacy (prescription):** Currently charge is created when prescription is **dispensed**.  
  - **Change:** Create pharmacy charge when doctor **creates** prescription (at order time), with estimated/fixed price, so the “visit invoice” has consultation + labs + radiology + pharmacy before the single payment.  
  - Dispensing then only checks “visit invoice paid” and does not create a new charge (or reconciles quantity if needed).

---

### 3.7 Single payment gate (lab, radiology, pharmacy)

- **Lab (result entry):**  
  - For OPD cash: do **not** require “payment for this lab order” specifically.  
  - Require: “visit invoice (for this encounter/OPD visit) is paid.”  
  - Use `has_visit_invoice_been_paid(db, encounter_id=..., opd_visit_id=...)`. If False, redirect to payment page (or show “Pay visit invoice first”).
- **Radiology (report entry):** Same: require visit invoice paid; redirect to payment if not.
- **Pharmacy (dispensing):** Same: require visit invoice paid.  
  - Ensure prescription charge exists on the visit invoice (created at order time as above).

---

### 3.8 Where the patient pays (“Pay before anything else”)

- **Option A (recommended):**  
  - After doctor saves orders, show a clear message: “Patient must pay at cashier before lab/radiology/pharmacy.”  
  - When patient goes to lab/radiology/pharmacy, if visit invoice is unpaid, redirect to **one** payment page: e.g. `/patients/{id}/pay/visit?encounter_id=...` or `/patients/{id}/pay/invoice?invoice_id=...` that shows the **full visit invoice** (consultation + all orders) and allows a single payment.
- **Option B:**  
  - From doctor’s summary screen, a “Send to cashier / Collect payment” button that links to the same visit invoice payment page.

So: **one payment page per visit** (one invoice = consultation + all orders for that encounter/visit).

---

### 3.9 Invoice and OPD visit (consultation + labs)

- One invoice per encounter (or per OPD visit) for **consultation + lab** charges.  
- Cash payment is recorded against that invoice; when balance is 0, `has_visit_invoice_been_paid` is True and **lab** can enter result (patient can leave).  
- Radiology and pharmacy use their own invoices or payment checks (unchanged).

---

## 4. Files to Touch (Checklist)

| File | Change |
|------|--------|
| `app/utils/payment_verification.py` | 1) OPD cash: `requires_payment_before_service(..., CONSULTATION)` → False. 2) Add `requires_visit_payment_before_ancillary` and `has_visit_invoice_been_paid`. 3) In `verify_encounter_workflow`, skip payment requirement for OPD cash. |
| `app/routers/patient_api.py` | Cash (non-emergency): redirect to triage, not to pay/consultation. |
| `app/routers/triage_api.py` | Remove consultation payment check before recording vitals. |
| `app/routers/appointment_api.py` | Remove consultation payment check before check-in. |
| `app/routers/encounter_api.py` | Ensure consultation charge is created when encounter is created (if not already). Create prescription charge when prescription is **created** (not only at dispense). |
| `app/routers/ancillary_services_api.py` | Lab result entry, radiology report entry, pharmacy dispense: for OPD cash, require “visit invoice paid” (new helper) instead of per-service payment; redirect to visit invoice payment page if unpaid. |
| `app/services/charge_automation.py` | Add or use a path to create prescription charge at order time (when doctor creates prescription); ensure it’s attached to the same encounter invoice. |
| Payment UI (e.g. `app/routers/payment_ui_routes.py`, templates) | Ensure there is a route like “Pay visit invoice” that shows the full invoice for the encounter/visit and accepts payment (single page after doctor orders). |

---

## 5. Edge Cases to Confirm

1. **Doctor orders only labs (no radiology/pharmacy):**  
   Invoice = consultation + lab charges. Patient pays once; lab can enter results. No radiology/pharmacy. **OK.**
2. **Doctor orders labs + radiology + pharmacy:**  
   Invoice = consultation + lab + radiology + pharmacy. Patient pays once; all three can proceed after payment. **OK.**
3. **Doctor adds a late order (e.g. extra lab) after patient already paid:**  
   Options: (A) Add charge to same invoice and require top-up before that new service; or (B) Allow one “add to existing visit invoice” and one more payment. Recommend (A) for simplicity: new charge → invoice balance > 0 → lab/radiology/pharmacy still check “visit paid” and block until top-up. **Confirm.**
4. **Walk-in with no encounter (e.g. direct lab order):**  
   If you have flows without an encounter, define which invoice (e.g. by `opd_visit_id` or new “visit”) is used and apply the same rule: one invoice, one payment before any ancillary. **Confirm if applicable.**
5. **NHIS / private insurance:**  
   No change; they are not “cash pay every step”. Only **cash** flow changes as above.

---

## 6. Confirmation Checklist for You

Before implementation, please confirm:

- [ ] **Flow:** Walk-in → Triage → See doctor → Doctor orders **labs** → **Single payment (consultation + lab)** → Patient can leave. Agree?
- [ ] **Pharmacy and radiology** are **separate** — not part of this payment; pay when they use pharmacy / radiology (current behaviour). Agree?
- [ ] **Consultation charge** created when encounter is created (not before triage). Agree?
- [ ] **Single payment** = consultation + **labs only** (one invoice for this visit). Agree?
- [ ] **Lab:** Require visit invoice paid before lab result entry (or before patient leaves). Agree?
- [ ] **IPD cash** unchanged (this plan is OPD cash only). Agree?
- [ ] **Emergency:** Keep bypass (no payment before triage/stabilization). Agree?

Once you confirm these, implementation can follow this plan.
