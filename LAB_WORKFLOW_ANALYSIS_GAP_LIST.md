# LHIMS Lab Workflow - Gap List

This document identifies gaps between the current implementation and the requirements for a complete template-driven lab result entry system.

---

## 1. Template-Driven Result Entry

### Current State
- ✅ Template resolution from `LabTest.template_id`
- ✅ Schema-based form rendering in [`lab_order_detail.html`](app/templates/ancillary/lab_order_detail.html)
- ✅ JSONB storage in `lab_orders.result_json`
- ✅ Free-text fallback (`lab_orders.result` field)

### Gaps
| Gap ID | Description | Severity |
|--------|-------------|----------|
| G-001 | No dedicated "Result Entry" page for template-driven data entry - it's embedded in order detail | Medium |
| G-002 | Template field types include numeric, text, choice, multichoice, datetime, table, repeat_group, calculated - but **calculated field formulas are not executed** on the server during entry | High |
| G-003 | No auto-save functionality for draft results | Medium |
| G-004 | Field-level validation errors are not clearly displayed in the UI | Medium |

---

## 2. Template Builder UI

### Current State
- ✅ Visual drag-and-drop builder in [`template_builder.html`](app/templates/lab/template_builder.html:1)
- ✅ Component palette (numeric, text, choice, multichoice, section)
- ✅ Property panel for field configuration
- ✅ Preview functionality with simulated patient context
- ✅ Save draft / Publish workflow
- ✅ Field properties: code, label, type, required, min/max, decimals, options, optionSet, critical flag

### Gaps
| Gap ID | Description | Severity |
|--------|-------------|----------|
| G-005 | No field-level reference range configuration in builder UI - ranges must be added separately via `lab_reference_ranges` table | High |
| G-006 | No visual "conditional logic" builder - rules must be manually entered as JSON | Medium |
| G-007 | No "test binding" UI to link templates to `lab_tests` catalog entries | Medium |
| G-008 | No duplicate/copy template functionality | Low |
| G-009 | Template builder only accessible to Admin role - Lab Staff cannot create templates | Medium |

---

## 3. Template Versioning & Immutability

### Current State
- ✅ `LabTemplateVersion` table with immutable PUBLISHED versions
- ✅ Version history view (`/lab/templates/{id}/versions`)
- ✅ `lab_templates.current_version` tracks published version
- ✅ `lab_orders.template_version_used` stores which version was used for each result
- ✅ Checksum field available but not populated

### Gaps
| Gap ID | Description | Severity |
|--------|-------------|----------|
| G-010 | Published templates can be **re-published** (status changed in place) - violates true immutability | High |
| G-011 | No mechanism to view what results used which template version | Low |
| G-012 | Checksum field exists but is not computed/stored on publish | Low |
| G-013 | No "rollback" capability if published template has errors | Medium |

---

## 4. Result JSON Storage

### Current State
- ✅ `lab_orders.result_json` (JSONB) stores structured results keyed by field code
- ✅ `lab_orders.flags_json` (JSONB) stores abnormal/critical flags
- ✅ Backward compatibility with free-text `lab_orders.result`

### Gaps
| Gap ID | Description | Severity |
|--------|-------------|----------|
| G-014 | No structured storage for **result comments/notes** separate from the template schema | Low |
| G-015 | No **instrument/equipment linkage** - results should optionally store which analyzer produced the value | Medium |
| G-016 | No **QC linkage at field level** - results don't reference which QC batch was used | Medium |

---

## 5. Reference Ranges + Flags

### Current State
- ✅ Two reference range systems:
  1. [`reference_ranges`](app/models/lab_models.py:140) (generic, linked to `lab_tests`)
  2. [`lab_reference_ranges`](app/models/lab_template_models.py:77) (field-based, linked to template fields)
- ✅ Flags computed via [`lab_result_validation.py`](app/services/lab_result_validation.py)
- ✅ Critical flag support in template schema (`"critical": true`)
- ✅ Reference range lookup by sex and age

### Gaps
| Gap ID | Description | Severity |
|--------|-------------|----------|
| G-017 | **Two separate reference range systems** - creates confusion; should consolidate to field-based system | High |
| G-018 | No UI to manage `lab_reference_ranges` - only `reference_ranges` has a UI | High |
| G-019 | Reference ranges cannot specify **different units per range** (e.g., mmol/L vs mg/dL) | Medium |
| G-020 | No "panic/critical value" alert notification system integrated | High |
| G-021 | No SMS/notification to clinicians for critical results | High |

---

## 6. Verification/Authorization Workflow

### Current State
- ✅ Status flow: DRAFT → SUBMITTED → VERIFIED → AUTHORIZED/RELEASED
- ✅ Verify endpoint: [`/lab/orders/{id}/verify`](app/routers/ancillary_services_api.py:701)
- ✅ Authorize endpoint: [`/lab/orders/{id}/authorize`](app/routers/ancillary_services_api.py:724)
- ✅ Verified_by_id, verified_at, authorized_by_id, authorized_at fields
- ✅ Critical result check before authorization (requires communication documentation)

### Gaps
| Gap ID | Description | Severity |
|--------|-------------|----------|
| G-022 | **No role separation** - same user can verify AND authorize (should require different roles) | High |
| G-023 | No "second verifier" for specific test types (e.g., pathologist review for complex tests) | Medium |
| G-024 | No configurable workflow - some labs may not need authorization step | Medium |
| G-025 | No "reject result" workflow - only amendment is available | Medium |
| G-026 | Critical value communication tracking is minimal (just a checkbox) | Medium |

---

## 7. Audit Trail & Amendments

### Current State
- ✅ [`LabAuditEvent`](app/models/lab_template_models.py:63) table with action types: create, update, submit, verify, authorize, amend
- ✅ Amendment creates new `LabOrder` with `previous_version_id` link
- ✅ Amendment reason stored in `amend_reason` field

### Gaps
| Gap ID | Description | Severity |
|--------|-------------|----------|
| G-027 | Audit events are **not linked to specific fields** - cannot see which field was changed | High |
| G-028 | No UI to view audit history for a lab order | High |
| G-029 | Amendment doesn't preserve original result as JSON snapshot - just links to previous order | Medium |
| G-030 | No "reason required" enforcement for amendments | Medium |
| G-031 | No "notify clinician of amendment" functionality | Medium |
| G-032 | Generic audit table exists but lab-specific audit is separate - **duplication/confusion** | Low |

---

## 8. Additional Gaps

| Gap ID | Description | Severity |
|--------|-------------|----------|
| G-033 | **No specimen rejection workflow** - only sample status exists but no formal rejection form | Medium |
| G-034 | No "result hold/pending" status for abnormal results requiring repeat testing | Medium |
| G-035 | No integration with LIS (Laboratory Information System) instruments | High |
| G-036 | No barcoding/printing labels from the UI | Medium |
| G-037 | No "result copied to" functionality for duplicate results | Low |
| G-038 | Template fields don't have "comment/notes" field option for operator remarks | Low |

---

## Summary by Severity

### High Priority (Should Fix)
- G-002: Calculated field formulas not executed
- G-005: No field-level reference range in builder
- G-010: Published templates can be modified (violates immutability)
- G-017: Two reference range systems
- G-020/021: No critical value alerts/notifications
- G-022: Same user can verify and authorize
- G-027: Audit not field-level
- G-028: No audit history UI

### Medium Priority (Should Consider)
- G-001, G-003, G-004: UX improvements for result entry
- G-006, G-007, G-009: Template builder enhancements
- G-011, G-012, G-013: Version management
- G-015, G-016: Equipment/QC linkage
- G-018, G-019, G-023, G-024, G-025, G-026, G-029, G-030, G-031, G-033, G-034

### Low Priority (Nice to Have)
- G-008, G-014, G-032, G-035, G-036, G-037, G-038
