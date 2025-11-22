# OPD/IPD Workflow Implementation Plan
## Final Recommendations & Implementation Strategy

---

## 📋 **EXECUTIVE SUMMARY**

This document outlines the final recommendations and implementation plan for incorporating the OPD/IPD workflow separation into the existing LHIMS system. The goal is to clearly distinguish between outpatient (OPD) and inpatient (IPD) workflows while maintaining data integrity and backward compatibility.

---

## 🎯 **FINAL RECOMMENDATIONS**

### **1. Core Database Changes Required**

#### **A. Create OPD Visit Model** ⭐ **CRITICAL**
```python
# New file: app/models/opd_models.py

class OPDVisitStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class OPDVisit(Base):
    __tablename__ = "opd_visits"
    
    id = Column(Integer, primary_key=True, index=True)
    opd_number = Column(String(50), unique=True, nullable=False, index=True)  # "OPD-2024-0001"
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)  # Optional
    
    # Visit Details
    visit_date = Column(DateTime, nullable=False, server_default=func.now())
    status = Column(postgresql.ENUM(OPDVisitStatus, ...), nullable=False, default=OPDVisitStatus.ACTIVE)
    payment_status = Column(String(20), nullable=False, default="pending")  # "pending", "paid", "waived", "emergency"
    
    # Financial
    consultation_charge_created = Column(Boolean, default=False)
    total_charges = Column(Numeric(10, 2), default=Decimal('0.00'))
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    patient = relationship("Patient", back_populates="opd_visits")
    appointment = relationship("Appointment")
    encounters = relationship("Encounter", back_populates="opd_visit")
```

#### **B. Update Encounter Model**
```python
# Modify: app/models/encounter_models.py

class Encounter(Base):
    # ... existing fields ...
    
    # ADD THESE:
    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=True)  # Already exists but verify
    
    # ADD RELATIONSHIP:
    opd_visit = relationship("OPDVisit", back_populates="encounters")
    # admission relationship already exists
    
    # VALIDATION: Either opd_visit_id OR admission_id must be set (enforce in business logic)
```

#### **C. Update Order Models (Optional but Recommended)**
```python
# Modify: app/models/encounter_models.py

class LabOrder(Base):
    # ... existing fields ...
    # ADD:
    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)
    # admission_id already exists via encounter relationship

class RadiologyOrder(Base):
    # ... existing fields ...
    # ADD:
    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)

class Prescription(Base):
    # ... existing fields ...
    # ADD:
    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)
```

#### **D. Update Billing Models**
```python
# Modify: app/models/billing_models.py

class Invoice(Base):
    # ... existing fields ...
    # ADD:
    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)
    # admission_id already exists via encounter relationship

class Charge(Base):
    # ... existing fields ...
    # ADD:
    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)
    # admission_id can be derived from encounter
```

#### **E. Update Patient Model**
```python
# Modify: app/models/patient_models.py

class Patient(Base):
    # ... existing fields ...
    # ADD RELATIONSHIP:
    opd_visits = relationship("OPDVisit", back_populates="patient")
```

---

### **2. Workflow Integration Points**

#### **A. OPD Visit Creation Triggers**

**Scenario 1: New Patient Registration**
```
1. Patient registered → patient_number created
2. If OPD visit type → Create OPDVisit immediately
3. Generate opd_number (e.g., "OPD-2024-0001")
4. If cash patient → Create consultation charge
5. Redirect to triage
```

**Scenario 2: Returning Patient - Start New Visit**
```
1. Front Office clicks "Start New Visit"
2. Create OPDVisit record
3. Generate opd_number
4. Create consultation charge (if cash)
5. Redirect to triage with opd_visit_id in session/query param
```

**Scenario 3: Emergency Patient**
```
1. Create OPDVisit immediately
2. Set payment_status = "emergency" or "waived"
3. Skip payment verification
4. Allow encounter creation
```

#### **B. Encounter Creation Validation**

```python
# Business Logic:
def validate_encounter_creation(patient_id, opd_visit_id=None, admission_id=None):
    """
    Validate that encounter can be created.
    """
    # Rule 1: Must have either opd_visit_id OR admission_id (not both, not neither)
    if not opd_visit_id and not admission_id:
        raise ValueError("Encounter must be linked to either OPD visit or IPD admission")
    
    if opd_visit_id and admission_id:
        raise ValueError("Encounter cannot be linked to both OPD visit and IPD admission")
    
    # Rule 2: If OPD, verify payment (unless emergency)
    if opd_visit_id:
        opd_visit = get_opd_visit(opd_visit_id)
        if opd_visit.payment_status not in ["paid", "waived", "emergency"]:
            # Check if cash patient
            patient = get_patient(patient_id)
            if patient.payment_mechanism == PaymentMechanism.CASH:
                raise ValueError("Payment required before creating encounter")
    
    # Rule 3: If IPD, verify admission status
    if admission_id:
        admission = get_admission(admission_id)
        if admission.status != AdmissionStatus.ADMITTED:
            raise ValueError("Patient must be admitted to create IPD encounter")
    
    return True
```

#### **C. Order Linking Strategy**

**Option 1: Direct Linking (Recommended)**
- Orders link directly to `opd_visit_id` or `admission_id`
- Pros: Clear tracking, easier reporting
- Cons: More database columns

**Option 2: Derived Linking (Simpler)**
- Orders link to `encounter_id` only
- Derive OPD/IPD from encounter relationship
- Pros: Simpler schema
- Cons: Requires joins for reporting

**Recommendation: Hybrid Approach**
- Keep `encounter_id` as primary link (required)
- Add `opd_visit_id` and `admission_id` as optional denormalized fields
- Populate them automatically from encounter relationship
- Use for direct queries and reporting

---

### **3. Number Generation Strategy**

```python
# OPD Number Format: "OPD-YYYY-NNNN"
# Example: "OPD-2024-0001", "OPD-2024-0002"

def generate_opd_number(db: Session) -> str:
    """
    Generate unique OPD visit number.
    Format: OPD-YYYY-NNNN
    """
    current_year = datetime.now().year
    
    # Get last OPD number for this year
    last_visit = db.query(OPDVisit).filter(
        OPDVisit.opd_number.like(f"OPD-{current_year}-%")
    ).order_by(OPDVisit.opd_number.desc()).first()
    
    if last_visit:
        # Extract sequence number
        last_seq = int(last_visit.opd_number.split('-')[-1])
        next_seq = last_seq + 1
    else:
        next_seq = 1
    
    return f"OPD-{current_year}-{next_seq:04d}"

# IPD Number: Use existing admission_number generation
# Format should be consistent: "IPD-YYYY-NNNN" or "ADM-YYYY-NNNN"
```

---

## 📊 **IMPLEMENTATION PHASES**

### **Phase 1: Foundation (Week 1-2)** ⭐ **START HERE**

**Tasks:**
1. ✅ Create `OPDVisit` model
2. ✅ Create database migration
3. ✅ Add `opd_visit_id` to `Encounter` model
4. ✅ Update `Patient` model relationships
5. ✅ Create OPD visit CRUD operations
6. ✅ Create OPD number generation service

**Deliverables:**
- New database table: `opd_visits`
- Updated `encounters` table with `opd_visit_id`
- Basic OPD visit creation API endpoint

**Testing:**
- Create OPD visit for new patient
- Create OPD visit for returning patient
- Verify opd_number generation

---

### **Phase 2: Encounter Integration (Week 2-3)**

**Tasks:**
1. ✅ Update encounter creation to require OPD/IPD link
2. ✅ Add validation logic
3. ✅ Update encounter forms to show OPD/IPD context
4. ✅ Update encounter views to display OPD/IPD info
5. ✅ Migrate existing encounters (backfill opd_visit_id where possible)

**Deliverables:**
- Updated encounter creation workflow
- Validation middleware
- Updated UI forms and views
- Data migration script for existing encounters

**Testing:**
- Create encounter with OPD visit
- Create encounter with IPD admission
- Verify validation prevents invalid combinations
- Test backward compatibility

---

### **Phase 3: Orders & Billing Integration (Week 3-4)**

**Tasks:**
1. ✅ Add `opd_visit_id` to order models (optional)
2. ✅ Add `opd_visit_id` to billing models
3. ✅ Update order creation to link to OPD/IPD
4. ✅ Update billing automation to use OPD/IPD
5. ✅ Create reporting queries for OPD vs IPD

**Deliverables:**
- Updated order models
- Updated billing models
- Updated charge automation service
- Reporting endpoints

**Testing:**
- Create orders linked to OPD visit
- Create orders linked to IPD admission
- Verify billing aggregation
- Test reporting queries

---

### **Phase 4: UI/UX Updates (Week 4-5)**

**Tasks:**
1. ✅ Add "Start New Visit" button to patient records
2. ✅ Create OPD visit dashboard
3. ✅ Update patient records to show OPD/IPD history
4. ✅ Add OPD/IPD filters to reports
5. ✅ Update encounter forms with OPD/IPD context

**Deliverables:**
- Updated patient records page
- OPD visit management UI
- Enhanced encounter forms
- Reporting dashboards

**Testing:**
- User acceptance testing
- Workflow validation
- UI responsiveness

---

### **Phase 5: Advanced Features (Week 5-6)**

**Tasks:**
1. ✅ OPD visit completion workflow
2. ✅ Visit-to-visit continuity tracking
3. ✅ Advanced reporting (OPD vs IPD analytics)
4. ✅ Integration with existing IPD admission workflow
5. ✅ Documentation and training materials

**Deliverables:**
- Complete OPD workflow
- Analytics dashboard
- User documentation
- Admin guide

---

## 🔄 **MIGRATION STRATEGY**

### **Backward Compatibility**

**Challenge:** Existing encounters don't have `opd_visit_id` or `admission_id`.

**Solution:**
1. Make `opd_visit_id` and `admission_id` nullable initially
2. Create data migration script:
   ```python
   # For existing encounters:
   # - If encounter has appointment → create OPD visit retroactively
   # - If encounter has admission → link admission_id
   # - If neither → mark as "legacy" and allow manual assignment
   ```
3. Gradual migration: New encounters require OPD/IPD link, old ones remain valid

### **Data Migration Script**

```python
def migrate_existing_encounters(db: Session):
    """
    Migrate existing encounters to OPD/IPD structure.
    """
    encounters = db.query(Encounter).filter(
        Encounter.opd_visit_id.is_(None),
        Encounter.admission_id.is_(None)
    ).all()
    
    for encounter in encounters:
        # Strategy 1: If has appointment, create OPD visit
        if encounter.appointment_id:
            opd_visit = create_opd_visit_retroactive(
                db, 
                patient_id=encounter.patient_id,
                appointment_id=encounter.appointment_id,
                visit_date=encounter.encounter_date
            )
            encounter.opd_visit_id = opd_visit.id
        
        # Strategy 2: If has admission, link it
        elif encounter.admission_id:  # Check if relationship exists
            # Already linked via admission relationship
            pass
        
        # Strategy 3: Create generic OPD visit for orphaned encounters
        else:
            opd_visit = create_opd_visit_retroactive(
                db,
                patient_id=encounter.patient_id,
                visit_date=encounter.encounter_date
            )
            encounter.opd_visit_id = opd_visit.id
    
    db.commit()
```

---

## ✅ **POSSIBLE OUTCOMES**

### **Positive Outcomes** 🎯

1. **Clear Workflow Separation**
   - OPD and IPD workflows are distinct and trackable
   - Better reporting and analytics
   - Improved billing accuracy

2. **Enhanced Data Integrity**
   - All encounters linked to either OPD visit or IPD admission
   - Clear audit trail
   - Better patient history tracking

3. **Improved Billing**
   - Per-visit billing for OPD
   - Per-admission billing for IPD
   - Accurate charge aggregation

4. **Better Reporting**
   - OPD visit statistics
   - IPD admission statistics
   - Patient visit history
   - Financial reports by module

5. **Scalability**
   - Foundation for future features
   - Support for multiple visits per day
   - Support for complex billing scenarios

### **Challenges & Risks** ⚠️

1. **Data Migration Complexity**
   - **Risk:** Existing encounters may not map cleanly
   - **Mitigation:** Gradual migration, manual review for edge cases

2. **User Training**
   - **Risk:** Staff need to learn new workflow
   - **Mitigation:** Comprehensive training, clear documentation

3. **Performance Impact**
   - **Risk:** Additional joins in queries
   - **Mitigation:** Proper indexing, query optimization

4. **Backward Compatibility**
   - **Risk:** Breaking existing integrations
   - **Mitigation:** Make fields nullable initially, gradual rollout

5. **Workflow Disruption**
   - **Risk:** Temporary disruption during migration
   - **Mitigation:** Phased rollout, rollback plan

---

## 🎯 **SUCCESS CRITERIA**

### **Technical Success**
- ✅ All new encounters require OPD/IPD link
- ✅ OPD visit creation works for new and returning patients
- ✅ Billing correctly aggregates by OPD/IPD
- ✅ Reports show accurate OPD vs IPD statistics
- ✅ No data loss during migration

### **Business Success**
- ✅ Staff can complete OPD workflow without confusion
- ✅ Billing accuracy improves
- ✅ Reporting provides actionable insights
- ✅ Patient history is clear and accessible

### **User Experience Success**
- ✅ Workflow is intuitive
- ✅ Forms are clear and contextual
- ✅ Reports are easy to understand
- ✅ Training time is minimal

---

## 📝 **NEXT STEPS**

### **Immediate Actions (This Week)**

1. **Review & Approve Plan**
   - Review this document with stakeholders
   - Get approval for Phase 1 implementation

2. **Create OPD Model**
   - Create `app/models/opd_models.py`
   - Define `OPDVisit` model
   - Create database migration

3. **Update Encounter Model**
   - Add `opd_visit_id` field
   - Update relationships
   - Create migration

4. **Create OPD Service**
   - Create `app/services/opd_service.py`
   - Implement OPD number generation
   - Implement OPD visit creation logic

### **Short-term Actions (Next 2 Weeks)**

5. **Update UI Routes**
   - Add "Start New Visit" functionality
   - Update patient records page
   - Update encounter creation flow

6. **Testing**
   - Unit tests for OPD service
   - Integration tests for workflow
   - User acceptance testing

---

## 🔧 **TECHNICAL SPECIFICATIONS**

### **Database Schema Changes**

```sql
-- New table
CREATE TABLE opd_visits (
    id SERIAL PRIMARY KEY,
    opd_number VARCHAR(50) UNIQUE NOT NULL,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    appointment_id INTEGER REFERENCES appointments(id),
    visit_date TIMESTAMP NOT NULL DEFAULT NOW(),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    payment_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    consultation_charge_created BOOLEAN DEFAULT FALSE,
    total_charges NUMERIC(10,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    updated_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_opd_visits_patient ON opd_visits(patient_id);
CREATE INDEX idx_opd_visits_opd_number ON opd_visits(opd_number);
CREATE INDEX idx_opd_visits_visit_date ON opd_visits(visit_date);

-- Update encounters table
ALTER TABLE encounters ADD COLUMN opd_visit_id INTEGER REFERENCES opd_visits(id);
CREATE INDEX idx_encounters_opd_visit ON encounters(opd_visit_id);

-- Update invoices table (optional)
ALTER TABLE invoices ADD COLUMN opd_visit_id INTEGER REFERENCES opd_visits(id);
CREATE INDEX idx_invoices_opd_visit ON invoices(opd_visit_id);
```

### **API Endpoints**

```python
# New endpoints needed:
POST   /api/v1/opd-visits/create          # Create OPD visit
GET    /api/v1/opd-visits/{id}            # Get OPD visit details
GET    /api/v1/patients/{id}/opd-visits   # Get patient's OPD visits
PUT    /api/v1/opd-visits/{id}/complete   # Complete OPD visit
GET    /api/v1/opd-visits                 # List OPD visits (with filters)
```

---

## 📚 **DOCUMENTATION REQUIREMENTS**

1. **Developer Documentation**
   - OPD/IPD model relationships
   - API endpoint documentation
   - Migration guide

2. **User Documentation**
   - OPD workflow guide
   - IPD workflow guide
   - Troubleshooting guide

3. **Admin Documentation**
   - Configuration guide
   - Reporting guide
   - Billing setup

---

## 🎉 **CONCLUSION**

This implementation plan provides a clear path to incorporate OPD/IPD workflow separation into the existing LHIMS system. The phased approach ensures minimal disruption while providing clear benefits in data integrity, billing accuracy, and reporting capabilities.

**Key Takeaways:**
- ✅ Start with Phase 1 (OPD Visit model)
- ✅ Maintain backward compatibility
- ✅ Gradual migration strategy
- ✅ Comprehensive testing at each phase
- ✅ Clear success criteria

**Ready to proceed?** Start with Phase 1 implementation!

