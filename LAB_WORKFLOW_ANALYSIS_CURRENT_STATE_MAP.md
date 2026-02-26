# LHIMS Lab Workflow - Current State Map

## 1. Database Tables/Models

### Core Lab Tables

| Table | Model File | Purpose |
|-------|-----------|---------|
| `lab_tests` | [`lab_catalog_models.py`](app/models/lab_catalog_models.py:9) | Master catalog of available lab tests |
| `lab_orders` | [`encounter_models.py`](app/models/encounter_models.py:88) | Lab test orders (linked to encounters or walk-in patients) |
| `lab_samples` | [`lab_models.py`](app/models/lab_models.py:28) | Sample tracking with barcodes |
| `reference_ranges` | [`lab_models.py`](app/models/lab_models.py:140) | Test reference ranges (normal/critical values) |
| `qc_records` | [`lab_models.py`](app/models/lab_models.py:85) | Quality control records |

### Template System Tables

| Table | Model File | Purpose |
|-------|-----------|---------|
| `lab_templates` | [`lab_template_models.py`](app/models/lab_template_models.py:28) | Template metadata (DRAFT/PUBLISHED/ARCHIVED) |
| `lab_template_versions` | [`lab_template_models.py`](app/models/lab_template_models.py:45) | Immutable versioned schemas (schema_json) |
| `lab_option_sets` | [`lab_template_models.py`](app/models/lab_template_models.py:17) | Reusable picklists (e.g., DIPSTICK_SCALE) |
| `lab_reference_ranges` | [`lab_template_models.py`](app/models/lab_template_models.py:77) | Field-based reference ranges (field_code, sex, age) |
| `lab_audit_events` | [`lab_template_models.py`](app/models/lab_template_models.py:63) | Lab-specific audit trail |

### Lab Inventory Tables

| Table | Model File | Purpose |
|-------|-----------|---------|
| `lab_equipment` | [`lab_inventory_models.py`](app/models/lab_inventory_models.py:43) | Lab equipment inventory |
| `lab_reagents` | [`lab_inventory_models.py`](app/models/lab_inventory_models.py:178) | Reagent inventory |

---

## 2. API Routes/Routers

### Lab Ordering
- **[`walk_in_orders_api.py`](app/routers/walk_in_orders_api.py)** - Walk-in lab order creation and management
- **[`encounter_api.py`](app/routers/encounter_api.py)** - Lab order creation via clinical encounters

### Lab Receiving & Sample Tracking
- **[`lab_tracking_api.py`](app/routers/lab_tracking_api.py)**:
  - `/lab/samples` - Sample dashboard
  - `/lab/samples/{id}` - Sample detail view
  - `/lab/orders/{id}/create-sample` - Sample creation with barcode
  - `/lab/samples/{id}/receive` - Mark sample as received

### Results Entry
- **[`ancillary_services_api.py`](app/routers/ancillary_services_api.py)**:
  - `/lab/orders/{id}` - View order and enter results (template-driven or free-text)
  - `/lab/orders/{id}/enter-result` - POST endpoint for result entry
  - `/lab/orders/{id}/verify` - Verify result
  - `/lab/orders/{id}/authorize` - Authorize and release result

### Template Management
- **[`lab_template_api.py`](app/routers/lab_template_api.py)**:
  - `/lab/templates` - List templates
  - `/lab/templates/new` - Create new template
  - `/lab/templates/{id}` - Template builder (Admin only)
  - `/lab/templates/{id}/draft` - Save draft
  - `/lab/templates/{id}/publish` - Publish template
  - `/lab/templates/{id}/preview` - Preview with simulated patient
  - `/lab/templates/{id}/versions` - Version history

### Test Catalog
- **[`lab_catalog_api.py`](app/routers/lab_catalog_api.py)**:
  - `/lab/tests` - Lab test catalog dashboard
  - `/lab/tests/{id}` - Test detail and management
  - `/lab/reference-ranges` - Reference range management

---

## 3. Services

| Service | File | Purpose |
|---------|------|---------|
| Lab Report PDF Generation | [`lab_report_service.py`](app/services/lab_report_service.py) | PDF report generation for lab results |
| Result Validation | [`result_validation.py`](app/services/result_validation.py) | Validate free-text results against reference ranges |
| Template Schema Validation | [`lab_template_schema.py`](app/services/lab_template_schema.py) | Validate template schema before publishing |
| Result Validation (Template) | [`lab_result_validation.py`](app/services/lab_result_validation.py) | Validate structured results, compute flags |
| Lab Sample Service | [`lab_sample_service.py`](app/services/lab_sample_service.py) | Sample management logic |
| Lab Analytics | [`lab_analytics_service.py`](app/services/lab_analytics_service.py) | Analytics and reporting |

---

## 4. Jinja2 Templates/Pages

### Lab Templates (`app/templates/lab/`)

| Template | Purpose |
|----------|---------|
| `templates_list.html` | List all lab templates |
| `template_new.html` | Create new template form |
| `template_builder.html` | Visual template builder UI |
| `template_preview.html` | Preview template with reference ranges |
| `template_versions.html` | Version history view |
| `test_catalog.html` | Lab test catalog management |
| `test_detail.html` | Individual test details |
| `reference_ranges.html` | Reference range management |
| `samples_dashboard.html` | Sample tracking dashboard |
| `sample_detail.html` | Sample detail with barcode |
| `qc_dashboard.html` | Quality control records |
| `print_lab_result.html` | Print-friendly result report |
| `analytics_dashboard.html` | Lab analytics dashboard |

### Ancillary Templates (`app/templates/ancillary/`)

| Template | Purpose |
|----------|---------|
| `lab_dashboard.html` | Main lab dashboard |
| `lab_order_detail.html` | Lab order detail and result entry form |

---

## 5. Role/Permission System

### Roles (from [`seed_admin.py`](scripts/seed_admin.py:21))
- `Admin` - Full system access
- `Lab Staff` - Lab order fulfillment
- `Doctor` - Clinical encounters, order creation
- `Nurse` - Patient care, triage support
- `Front Office` - Walk-in order registration

### Permission Checks

| Route | Required Role |
|-------|--------------|
| `/lab/templates` | Admin, Lab Staff |
| `/lab/templates/{id}` (builder) | Admin only |
| `/lab/orders/{id}/enter-result` | Lab Staff, Admin |
| `/lab/orders/{id}/verify` | Lab Staff, Admin |
| `/lab/orders/{id}/authorize` | Lab Staff, Admin |
| `/lab/samples/*` | Lab Staff, Admin |
| `/lab/tests` | Admin, Lab Staff |

### Permission Model
- **[`permission_models.py`](app/models/permission_models.py)** - Permission definitions
- **[`role_permission_models.py`](app/models/role_permission_models.py)** - Role-permission associations
- **[`role_permissions_api.py`](app/routers/role_permissions_api.py)** - Admin UI for permission management

---

## 6. Result Workflow Status Values

The [`LabOrder`](app/models/encounter_models.py:88) model uses `result_status` field with these values:

| Status | Meaning |
|--------|---------|
| `DRAFT` | Result being entered |
| `SUBMITTED` | Result submitted, pending verification |
| `VERIFIED` | Verified by lab staff |
| `AUTHORIZED` | Authorized and released |
| `RELEASED` | Released to patient/clinical team |
| `AMENDED` | Result amended after release |

---

## 7. Key Field Mappings

### LabOrder Model (result storage)
```
- result: Text (free-text results)
- result_json: JSONB (structured template-driven results)
- flags_json: JSONB (abnormal/critical flags per field)
- template_id: UUID (link to lab_templates)
- template_version_used: Integer
- verified_by_id, verified_at: Verification tracking
- authorized_by_id, authorized_at: Authorization tracking
- previous_version_id: Self-reference for amendments
- amend_reason: Text
```

### Template Version Immutability
- Published versions in `lab_template_versions` have `status = "PUBLISHED"`
- Draft versions have `status = "DRAFT"`
- Publishing changes draft status to PUBLISHED and increments version
- **Published versions are NOT modified** - new draft creates new version

---

## 8. Audit Trail

The system uses:
1. **Generic audit** - via [`audit_models.py`](app/models/audit_models.py) 
2. **Lab-specific audit** - via [`LabAuditEvent`](app/models/lab_template_models.py:63) table

Audit actions tracked: `create`, `update`, `submit`, `verify`, `authorize`, `amend`
