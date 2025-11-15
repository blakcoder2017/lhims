# 🚀 LHIMS Quick Reference Guide

**Version:** 1.0  
**Print this page and keep it at your workstation**

---

## 🔐 Login

**URL:** [Your LHIMS URL]  
**Default Admin:** `admin` / `Westafrica1` (change immediately!)

---

## 📍 Common Navigation Paths

### Front Office Staff

| Task | Navigation Path |
|------|----------------|
| Register Patient | Front Office → Patient Registration |
| Record Vitals | Front Office → Triage & Vitals |
| View Appointments | Front Office → Appointment & Queue |
| Create Invoice | Finance & Reports → Billing & Payments → Create Invoice |
| Process Payment | Finance & Reports → Billing & Payments → [Select Invoice] → Process Payment |

### Clinicians (Doctors/Nurses)

| Task | Navigation Path |
|------|----------------|
| Search Patient | Clinical Services → Patient EHR Search |
| View Records | Clinical Services → Patient EHR Search → [Select Patient] → View Records |
| Pending Encounters | Clinical Services → Pending Encounters |
| New Encounter | Patient Records → New Encounter |
| Add Lab Order | Encounter Page → Lab Orders → Add Lab Order |
| Add Radiology Order | Encounter Page → Radiology Orders → Add Radiology Order |
| Add Prescription | Encounter Page → Prescriptions → Add Prescription |

### Lab Staff

| Task | Navigation Path |
|------|----------------|
| View Lab Orders | Ancillary Services → Laboratory (LIS) |
| Enter Results | Lab Order → Enter Result |
| Sample Tracking | Ancillary Services → Sample Tracking |
| Quality Control | Ancillary Services → Quality Control |
| Test Catalog | Ancillary Services → Test Catalog |

### Pharmacy Staff

| Task | Navigation Path |
|------|----------------|
| View Prescriptions | Ancillary Services → Pharmacy (PhIS) |
| Dispense Medication | Prescription → Dispense Medication |
| Inventory Management | Ancillary Services → Inventory Management |
| Check Drug Interactions | Ancillary Services → Drug Interactions |
| Inventory Alerts | Alerts → Inventory Alerts |

### Finance Staff

| Task | Navigation Path |
|------|----------------|
| Billing Dashboard | Finance & Reports → Billing & Payments |
| Create Invoice | Billing & Payments → Create Invoice |
| Process Payment | Invoice → Process Payment |
| NHIS Claims | [From Encounter] → Create NHIS Claim |
| Reports | Finance & Reports → Reports & Analytics |

---

## ⚡ Quick Actions

### Patient Registration (Front Office)

1. Front Office → Patient Registration
2. Fill demographics + Financial screening
3. Click "Register Patient"
4. → Auto-redirects to Triage

### Clinical Encounter (Clinician)

1. Search Patient → View Records
2. Click "New Encounter"
3. Fill: Chief Complaint, HPI, PMH, Exam, Assessment, Plan
4. Enter ICD-10 diagnosis
5. Add Orders (Lab/Radiology/Prescriptions)
6. Save Encounter

### Lab Result Entry (Lab Staff)

1. Ancillary Services → Laboratory (LIS)
2. Select Order
3. Click "Enter Result"
4. Enter test results
5. Save → Auto-creates charge

### Medication Dispensing (Pharmacy)

1. Ancillary Services → Pharmacy (PhIS)
2. Select Prescription
3. Check interactions & stock
4. Click "Dispense Medication"
5. Enter batch/expiry
6. Confirm → Auto-updates inventory & creates charge

### Invoice & Payment (Finance)

1. Billing & Payments → Create Invoice
2. Select Patient & Encounter
3. Add Charges (or auto-added from orders)
4. Process Payment
5. Enter payment details
6. Confirm → Receipt generated

---

## 🔑 Key Shortcuts

| Action | Method |
|--------|--------|
| Search Patient | Clinical Services → Patient EHR Search |
| View Dashboard | Click logo or "Dashboard" in sidebar |
| Edit Profile | Click your name → Edit Profile |
| Logout | Top right → Logout button |
| Print | Page → Print button or Ctrl+P |

---

## 📊 Status Meanings

### Encounter Status
- **In Progress** = Being documented
- **Completed** = Finished

### Order Status
- **Pending** = Awaiting fulfillment
- **In Progress** = Being processed
- **Completed** = Done

### Invoice Status
- **Pending** = Awaiting payment
- **Partially Paid** = Some payment received
- **Paid** = Fully paid

---

## ⚠️ Important Reminders

✅ **Always verify patient identity** before creating encounter  
✅ **Check allergies** before prescribing medications  
✅ **Validate lab results** against reference ranges  
✅ **Check stock** before dispensing medications  
✅ **Verify payment method** before processing payment  
✅ **Log out** when finished  

---

## 🆘 Common Issues

| Issue | Quick Fix |
|-------|-----------|
| Can't log in | Check username/password, enable cookies |
| 403 Forbidden | Your role doesn't have access - contact Admin |
| Patient not found | Try different search terms, verify registration |
| Order not showing | Refresh page, check status filters |
| Stock not updating | Verify transaction completed, refresh page |

---

## 📞 Support Contacts

**System Admin:** [Contact Info]  
**IT Support:** [Contact Info]  
**Training:** [Contact Info]  

---

## 🔄 Complete Workflow (Quick View)

```
1. Patient Registration (Front Office)
   ↓
2. Triage & Vitals (Front Office)
   ↓
3. Clinical Encounter (Clinician)
   ↓
4. Orders (Lab/Radiology/Prescriptions) (Clinician)
   ↓
5. Order Fulfillment (Lab/Rad/Pharmacy Staff)
   ↓
6. Billing & Payment (Finance/Front Office)
   ↓
7. Discharge/Follow-up
```

---

**Print Date:** _______________  
**For detailed instructions, see USER_MANUAL.md**

