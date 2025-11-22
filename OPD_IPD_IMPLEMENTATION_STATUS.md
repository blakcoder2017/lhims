# OPD/IPD Implementation Status

## ✅ **COMPLETED PHASES**

### **Phase 1: Foundation** ✅ **COMPLETE**

1. ✅ **OPD Visit Model Created**
   - File: `app/models/opd_models.py`
   - Model: `OPDVisit` with all required fields
   - Status enum: `OPDVisitStatus`
   - Relationships: Patient, Appointment, Encounters, Invoices

2. ✅ **Database Migration Created**
   - File: `migrations/versions/a1b2c3d4e5f6_add_opd_visits_and_update_encounters_billing.py`
   - Creates `opd_visits` table
   - Adds `opd_visit_id` to `encounters` table
   - Adds `admission_id` to `encounters` table (if not exists)
   - Adds `opd_visit_id` and `admission_id` to `invoices` table
   - Adds `opd_visit_id` and `admission_id` to `charges` table

3. ✅ **Encounter Model Updated**
   - File: `app/models/encounter_models.py`
   - Added `opd_visit_id` field
   - Added `admission_id` field (verified)
   - Updated relationships

4. ✅ **Patient Model Updated**
   - File: `app/models/patient_models.py`
   - Added `opd_visits` relationship

5. ✅ **Billing Models Updated**
   - File: `app/models/billing_models.py`
   - Added `opd_visit_id` to `Invoice` model
   - Added `admission_id` to `Invoice` model
   - Added `opd_visit_id` to `Charge` model
   - Added `admission_id` to `Charge` model
   - Updated relationships

6. ✅ **OPD CRUD Operations**
   - File: `app/crud/opd_crud.py`
   - `generate_opd_number()` - Generates unique OPD numbers (OPD-YYYY-NNNN)
   - `create_opd_visit()` - Creates new OPD visit
   - `get_opd_visit()` - Get by ID
   - `get_opd_visit_by_number()` - Get by OPD number
   - `get_opd_visits_by_patient()` - Get all visits for patient
   - `get_opd_visits()` - Get all with filters
   - `get_active_opd_visit_by_patient()` - Get active visit
   - `update_opd_visit()` - Update visit
   - `complete_opd_visit()` - Mark as completed
   - `cancel_opd_visit()` - Cancel visit
   - `update_opd_visit_payment_status()` - Update payment status
   - `mark_consultation_charge_created()` - Mark charge created
   - `update_opd_visit_total_charges()` - Update total charges
   - `delete_opd_visit()` - Soft delete

7. ✅ **OPD Schemas**
   - File: `app/schemas/opd_schemas.py`
   - `OPDVisitBase` - Base schema
   - `OPDVisitCreate` - Create schema
   - `OPDVisitUpdate` - Update schema
   - `OPDVisit` - Read schema
   - `OPDVisitWithPatient` - Extended schema

8. ✅ **OPD API Endpoints**
   - File: `app/routers/opd_api.py`
   - `POST /api/v1/opd-visits` - Create OPD visit
   - `GET /api/v1/opd-visits` - List all OPD visits (with filters)
   - `GET /api/v1/opd-visits/{id}` - Get by ID
   - `GET /api/v1/opd-visits/number/{opd_number}` - Get by number
   - `GET /api/v1/patients/{id}/opd-visits` - Get patient's visits
   - `GET /api/v1/patients/{id}/opd-visits/active` - Get active visit
   - `PUT /api/v1/opd-visits/{id}` - Update visit
   - `POST /api/v1/opd-visits/{id}/complete` - Complete visit
   - `POST /api/v1/opd-visits/{id}/cancel` - Cancel visit
   - `PUT /api/v1/opd-visits/{id}/payment-status` - Update payment status
   - `DELETE /api/v1/opd-visits/{id}` - Delete visit (Admin only)

9. ✅ **Router Registration**
   - File: `app/main.py`
   - OPD API router registered

10. ✅ **Model Registration**
    - File: `app/models/__init__.py`
    - OPDVisit and OPDVisitStatus imported

---

### **Phase 2: Encounter Integration** ✅ **COMPLETE**

1. ✅ **Encounter Validation Service**
   - File: `app/services/opd_validation.py`
   - `validate_encounter_creation()` - Validates OPD/IPD linkage
   - `auto_link_opd_visit()` - Auto-links OPD visit from appointment

2. ✅ **Encounter Schema Updated**
   - File: `app/schemas/encounter_schemas.py`
   - Added `opd_visit_id` to `EncounterBase`
   - Added `admission_id` to `EncounterBase`

3. ✅ **Encounter CRUD Updated**
   - File: `app/crud/encounter_crud.py`
   - `create_encounter()` now validates OPD/IPD linkage
   - Auto-links OPD visit if appointment exists

4. ✅ **Encounter API Updated**
   - File: `app/routers/encounter_api.py`
   - Form endpoint accepts `opd_visit_id` and `admission_id`
   - Validation errors handled gracefully

---

## 🔄 **IN PROGRESS / PENDING**

### **Phase 3: Orders & Billing Integration** ⏳ **PENDING**

- [ ] Add `opd_visit_id` to order models (LabOrder, RadiologyOrder, Prescription)
- [ ] Update order creation to link to OPD/IPD
- [ ] Update billing automation to use OPD/IPD links
- [ ] Create reporting queries for OPD vs IPD

### **Phase 4: UI/UX Updates** ⏳ **PENDING**

- [ ] Create "Start New Visit" UI route
- [ ] Update patient records page to show OPD visits
- [ ] Add "Start New Visit" button to patient records
- [ ] Update encounter forms with OPD/IPD context
- [ ] Create OPD visit dashboard
- [ ] Add OPD/IPD filters to reports

### **Phase 5: Advanced Features** ⏳ **PENDING**

- [ ] Create data migration script for existing encounters
- [ ] OPD visit completion workflow
- [ ] Visit-to-visit continuity tracking
- [ ] Advanced reporting (OPD vs IPD analytics)
- [ ] Documentation and training materials

---

## 📋 **NEXT STEPS**

### **Immediate (High Priority)**

1. **Run Database Migration**
   ```bash
   alembic upgrade head
   ```

2. **Create "Start New Visit" UI Route**
   - Add route to create OPD visit and redirect to triage
   - Add button to patient records page

3. **Update Patient Records Page**
   - Display OPD visits history
   - Show active OPD visit if exists
   - Add "Start New Visit" button

4. **Update Encounter Form**
   - Auto-populate `opd_visit_id` from active visit
   - Show OPD/IPD context in form

### **Short-term (Medium Priority)**

5. **Update Order Models**
   - Add `opd_visit_id` to LabOrder, RadiologyOrder, Prescription
   - Update order creation logic

6. **Update Billing Automation**
   - Link charges to OPD visits
   - Aggregate billing by OPD visit

7. **Create Data Migration Script**
   - Migrate existing encounters to OPD structure
   - Handle edge cases

### **Long-term (Low Priority)**

8. **Advanced Features**
   - OPD visit completion workflow
   - Analytics dashboard
   - Reporting enhancements

---

## 🧪 **TESTING CHECKLIST**

- [ ] Create OPD visit for new patient
- [ ] Create OPD visit for returning patient
- [ ] Verify OPD number generation
- [ ] Create encounter with OPD visit link
- [ ] Create encounter with IPD admission link
- [ ] Verify validation prevents invalid combinations
- [ ] Test payment verification for OPD visits
- [ ] Test auto-linking OPD visit from appointment
- [ ] Test backward compatibility with existing encounters

---

## 📝 **NOTES**

- All models, schemas, CRUD operations, and API endpoints are complete for Phase 1 and Phase 2
- Database migration is ready but needs to be run
- Validation logic is in place
- Auto-linking logic is implemented
- UI components need to be created/updated
- Data migration script needs to be created for existing encounters

---

## 🚀 **READY TO USE**

The following features are **ready to use** after running the migration:

1. ✅ Create OPD visits via API
2. ✅ Query OPD visits
3. ✅ Link encounters to OPD visits or IPD admissions
4. ✅ Validate encounter creation
5. ✅ Auto-link OPD visits from appointments

---

**Last Updated:** 2025-01-15
**Status:** Phase 1 & 2 Complete, Phase 3-5 Pending

