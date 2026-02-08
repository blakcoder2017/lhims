# Patient Records Fix - Missing Related Data

**Date**: February 8, 2026  
**Issue**: Procedures, Lab, Billing, Maternity records not saving/reflection on patient records  
**Root Cause**: Missing relationships in patient records view context  
**Status**: ✅ **Identified & Solution Ready**

## 🔍 Problem Analysis

### ❌ **Current Issue**
When users create:
- **Procedures** - They don't appear in patient records
- **Lab Orders** - They don't appear in patient records  
- **Billing/Invoices** - They don't appear in patient records
- **Maternity Records** - They don't appear in patient records

### ✅ **Root Cause Identified**
The `view_patient_records` function in `patient_records_api.py` is **missing the following data** in its context:

1. **Lab Orders** - Not loaded and passed to template
2. **Procedures** - Not loaded and passed to template
3. **Birth Records** - Not loaded and passed to template
4. **Radiology Orders** - Not loaded and passed to template

## 🔧 Solution Required

### ✅ **Missing Data in Patient Records Context**

The current context (lines 404-431) includes:
```python
context = {
    "request": request,
    "title": f"Patient Records: {patient.first_name} {patient.last_name}",
    "current_user": current_user,
    "user_role": current_user.role.name,
    "patient": patient,
    "patient_age": patient_age,
    "appointments": appointments,          # ✅ Included
    "encounters": encounters,            # ✅ Included
    "vitals_records": vitals_records,      # ✅ Included
    "admissions": admissions,            # ✅ Included
    "opd_visits": opd_visits,          # ✅ Included
    "invoices": invoices,                # ✅ Included
    # ❌ MISSING DATA BELOW ❌
    "lab_orders": ???,                 # Missing
    "procedures": ???,               # Missing
    "birth_records": ???,             # Missing
    "radiology_orders": ???,           # Missing
    "antenatal_visits": ???,          # Missing
}
```

## 🛠️ **Fix Implementation**

### ✅ **Add Missing Data Loading**

Add the following imports and data loading to `view_patient_records` function:

#### **1. Add Required Imports**
```python
# Add to existing imports (around line 22)
from app.models.encounter_models import LabOrder, RadiologyOrder
from app.models.procedure_models import Procedure
from app.models.antenatal_models import AntenatalVisit
from app.models.birth_models import BirthRecord
```

#### **2. Add Missing Data Loading**
```python
# Add after line 220 (after admissions loading)

# Get all lab orders for this patient
from app.crud import encounter_crud
lab_orders = encounter_crud.get_lab_orders_by_patient(db, patient_id)

# Get all procedures for this patient  
from app.crud import procedure_crud
procedures, _ = procedure_crud.get_procedures(db, patient_id=patient_id, limit=50)

# Get all radiology orders for this patient
radiology_orders = encounter_crud.get_radiology_orders_by_patient(db, patient_id)

# Get all antenatal visits for this patient
from app.crud import antenatal_crud
antenatal_visits = antenatal_crud.get_antenatal_visits_by_patient(db, patient_id)

# Get all birth records for this patient
from app.crud import birth_crud
birth_records = birth_crud.get_birth_records_by_patient(db, patient_id)
```

#### **3. Add Missing Data to Timeline**
```python
# Add after line 349 (after OPD visits in timeline)

# Add lab orders to timeline
for lab_order in lab_orders:
    timeline.append({
        "date": lab_order.ordered_at,
        "type": "lab_order",
        "title": f"Lab Order: {lab_order.test_name}",
        "description": f"Status: {lab_order.status.value}, Test: {lab_order.test_code}",
        "details": lab_order,
    })

# Add procedures to timeline
for procedure in procedures:
    timeline.append({
        "date": procedure.scheduled_date or procedure.created_at,
        "type": "procedure",
        "title": f"Procedure: {procedure.procedure_name}",
        "description": f"Status: {procedure.status.value}, Type: {procedure.procedure_type.value}",
        "details": procedure,
    })

# Add radiology orders to timeline
for rad_order in radiology_orders:
    timeline.append({
        "date": rad_order.ordered_at,
        "type": "radiology_order", 
        "title": f"Radiology: {rad_order.study_type}",
        "description": f"Status: {rad_order.status.value}, Study: {rad_order.study_type}",
        "details": rad_order,
    })

# Add antenatal visits to timeline
for antenatal_visit in antenatal_visits:
    timeline.append({
        "date": antenatal_visit.visit_date,
        "type": "antenatal_visit",
        "title": f"Antenatal Visit: Visit #{antenatal_visit.visit_number}",
        "description": f"GA: {antenatal_visit.gestational_weeks} weeks, Status: {antenatal_visit.status.value}",
        "details": antenatal_visit,
    })

# Add birth records to timeline
for birth_record in birth_records:
    timeline.append({
        "date": birth_record.birth_date,
        "type": "birth_record",
        "title": f"Birth: {birth_record.baby_name or 'Baby'}",
        "description": f"Delivery Type: {birth_record.delivery_type}, Weight: {birth_record.birth_weight}kg",
        "details": birth_record,
    })
```

#### **4. Add Missing Data to Context**
```python
# Update context dictionary (around line 404)
context = {
    "request": request,
    "title": f"Patient Records: {patient.first_name} {patient.last_name}",
    "current_user": current_user,
    "user_role": current_user.role.name,
    "patient": patient,
    "patient_age": patient_age,
    "appointments": appointments,
    "encounters": encounters,
    "vitals_records": vitals_records,
    "vitals_history": vitals_records,
    "admissions": admissions,
    "current_admission": current_admission,
    "opd_visits": opd_visits,
    "active_opd_visit": active_opd_visit,
    "opd_visits_count": opd_visits_count,
    "invoices": invoices,
    "invoice_summary": invoice_summary,
    # ✅ NEW ADDITIONS ✅
    "lab_orders": lab_orders,
    "procedures": procedures,
    "radiology_orders": radiology_orders,
    "antenatal_visits": antenatal_visits,
    "birth_records": birth_records,
    "timeline": timeline,  # Will now include all data
    "bp_chart_data": bp_chart_data,
    "vitals_chart_data": vitals_chart_data,
    "appointment_count": appointment_count,
    "vitals_count": vitals_count,
    "admissions_count": admissions_count,
    "workflow_complete": workflow_complete,
    "missing_step": missing_step,
    "has_checked_in_appointment": has_checked_in_appointment
}
```

## 🎯 **Required CRUD Functions**

### ✅ **Check if These Functions Exist**

The following CRUD functions need to exist and work properly:

1. **`get_lab_orders_by_patient`** in `encounter_crud.py`
2. **`get_radiology_orders_by_patient`** in `encounter_crud.py`  
3. **`get_procedures`** in `procedure_crud.py` (✅ Already exists)
4. **`get_antenatal_visits_by_patient`** in `antenatal_crud.py`
5. **`get_birth_records_by_patient`** in `birth_crud.py`

### ✅ **If Missing, Create These Functions**

```python
# In encounter_crud.py
def get_lab_orders_by_patient(db: Session, patient_id: int, limit: int = 100):
    """Get all lab orders for a specific patient."""
    return db.query(LabOrder).filter(
        LabOrder.patient_id == patient_id,
        LabOrder.is_active == True
    ).order_by(LabOrder.ordered_at.desc()).limit(limit).all()

def get_radiology_orders_by_patient(db: Session, patient_id: int, limit: int = 100):
    """Get all radiology orders for a specific patient."""
    return db.query(RadiologyOrder).filter(
        RadiologyOrder.patient_id == patient_id,
        RadiologyOrder.is_active == True
    ).order_by(RadiologyOrder.ordered_at.desc()).limit(limit).all()

# In antenatal_crud.py
def get_antenatal_visits_by_patient(db: Session, patient_id: int, limit: int = 100):
    """Get all antenatal visits for a specific patient."""
    return db.query(AntenatalVisit).filter(
        AntenatalVisit.patient_id == patient_id,
        AntenatalVisit.is_active == True
    ).order_by(AntenatalVisit.visit_date.desc()).limit(limit).all()

# In birth_crud.py
def get_birth_records_by_patient(db: Session, patient_id: int, limit: int = 100):
    """Get all birth records for a specific patient."""
    return db.query(BirthRecord).filter(
        BirthRecord.mother_patient_id == patient_id,
        BirthRecord.is_active == True
    ).order_by(BirthRecord.birth_date.desc()).limit(limit).all()
```

## 📋 Template Updates Required

### ✅ **Update Patient Records Template**

The `clinical/patient_records.html` template needs to display the new data:

```html
<!-- Add to patient records template -->
<section class="content">
    <div class="container-fluid">
        <!-- Existing sections... -->
        
        <!-- NEW: Lab Orders Section -->
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">
                            <i class="fas fa-flask"></i>
                            Laboratory Orders
                        </h3>
                    </div>
                    <div class="card-body">
                        {% if lab_orders %}
                            <div class="table-responsive">
                                <table class="table table-striped">
                                    <thead>
                                        <tr>
                                            <th>Order Date</th>
                                            <th>Test Name</th>
                                            <th>Status</th>
                                            <th>Ordered By</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for lab_order in lab_orders %}
                                        <tr>
                                            <td>{{ lab_order.ordered_at.strftime('%Y-%m-%d') }}</td>
                                            <td>{{ lab_order.test_name }}</td>
                                            <td><span class="badge badge-{{ lab_order.status }}">{{ lab_order.status.value }}</span></td>
                                            <td>{{ lab_order.ordered_by.full_name if lab_order.ordered_by else 'N/A' }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        {% else %}
                            <p class="text-muted">No lab orders found.</p>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
        
        <!-- NEW: Procedures Section -->
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">
                            <i class="fas fa-procedures"></i>
                            Procedures
                        </h3>
                    </div>
                    <div class="card-body">
                        {% if procedures %}
                            <div class="table-responsive">
                                <table class="table table-striped">
                                    <thead>
                                        <tr>
                                            <th>Date</th>
                                            <th>Procedure</th>
                                            <th>Type</th>
                                            <th>Status</th>
                                            <th>Performed By</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for procedure in procedures %}
                                        <tr>
                                            <td>{{ procedure.scheduled_date.strftime('%Y-%m-%d') if procedure.scheduled_date else procedure.created_at.strftime('%Y-%m-%d') }}</td>
                                            <td>{{ procedure.procedure_name }}</td>
                                            <td>{{ procedure.procedure_type.value }}</td>
                                            <td><span class="badge badge-{{ procedure.status }}">{{ procedure.status.value }}</span></td>
                                            <td>{{ procedure.performed_by.full_name if procedure.performed_by else 'N/A' }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        {% else %}
                            <p class="text-muted">No procedures found.</p>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
        
        <!-- NEW: Maternity Section -->
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">
                            <i class="fas fa-baby"></i>
                            Maternity Records
                        </h3>
                    </div>
                    <div class="card-body">
                        {% if antenatal_visits %}
                            <h5>Antenatal Visits</h5>
                            <div class="table-responsive">
                                <table class="table table-striped">
                                    <thead>
                                        <tr>
                                            <th>Visit Date</th>
                                            <th>Visit #</th>
                                            <th>GA (Weeks)</th>
                                            <th>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for visit in antenatal_visits %}
                                        <tr>
                                            <td>{{ visit.visit_date.strftime('%Y-%m-%d') }}</td>
                                            <td>{{ visit.visit_number }}</td>
                                            <td>{{ visit.gestational_weeks }}</td>
                                            <td><span class="badge badge-{{ visit.status }}">{{ visit.status.value }}</span></td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            {% endif %}
                        
                        {% if birth_records %}
                            <h5>Birth Records</h5>
                            <div class="table-responsive">
                                <table class="table table-striped">
                                    <thead>
                                        <tr>
                                            <th>Birth Date</th>
                                            <th>Baby Name</th>
                                            <th>Weight</th>
                                            <th>Delivery Type</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for birth in birth_records %}
                                        <tr>
                                            <td>{{ birth.birth_date.strftime('%Y-%m-%d') }}</td>
                                            <td>{{ birth.baby_name or 'Not specified' }}</td>
                                            <td>{{ birth.birth_weight }}kg</td>
                                            <td>{{ birth.delivery_type }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            {% endif %}
                        
                        {% if not antenatal_visits and not birth_records %}
                            <p class="text-muted">No maternity records found.</p>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>
```

## 🏆 **Expected Results After Fix**

### ✅ **Complete Patient Records View**

After implementing this fix, the patient records page will show:

1. **📋 Demographics** - Patient基本信息
2. **📅 Appointments** - Scheduled appointments  
3. **🏥 Encounters** - Clinical visits
4. **🩺 Vitals History** - Vital signs over time
5. **🏥 Admissions** - Hospital admissions
6. **💊 OPD Visits** - Outpatient visits
7. **💰 Invoices/Billing** - Financial records
8. **🔬 Lab Orders** - Laboratory test orders ✨ **NEW**
9. **⚕️ Procedures** - Medical procedures ✨ **NEW**
10. **🤰 Antenatal Visits** - Pregnancy care ✨ **NEW**
11. **👶 Birth Records** - Delivery records ✨ **NEW**
12. **📷 Radiology Orders** - Imaging studies ✨ **NEW**
13. **📊 Timeline** - Complete medical timeline ✨ **ENHANCED**

### ✅ **Data Persistence Fixed**

- **Procedures** will save and appear in patient records
- **Lab Orders** will save and appear in patient records
- **Billing** will save and appear in patient records
- **Maternity** will save and appear in patient records
- **Timeline** will show complete medical history

## 🎯 **Implementation Priority**

### ✅ **High Priority**
1. **Fix patient_records_api.py** - Add missing data loading
2. **Verify CRUD functions** - Ensure patient-specific queries exist
3. **Update template** - Display all data types
4. **Test integration** - Verify data flows correctly

### ✅ **Testing Required**
1. **Create Procedure** → Verify appears in patient records
2. **Create Lab Order** → Verify appears in patient records  
3. **Create Antenatal Visit** → Verify appears in patient records
4. **Create Birth Record** → Verify appears in patient records
5. **Timeline Integration** → Verify all events appear in timeline

---

**Status**: ✅ **Solution Ready - Implement to Fix Patient Records**

The issue is clearly identified and the complete solution is provided. Implement these changes to ensure all medical records properly save and reflect on patient records.

---

*Analysis completed on February 8, 2026*  
*Issue: Patient Records Missing Related Data*  
*Solution: Complete Data Loading & Display*  
*Status: Ready for Implementation*
