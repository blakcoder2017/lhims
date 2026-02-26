# LHIMS Lab Workflow - Migration Approach

This document outlines a migration strategy to address the identified gaps while avoiding breaking changes to existing data.

---

## Migration Principles

1. **Backward Compatibility**: All existing data must remain intact
2. **Incremental Changes**: Deploy changes in phases
3. **No Data Loss**: Preserve existing results and orders
4. **Feature Flags**: New features can be toggled on/off

---

## Phase 1: Reference Range Consolidation (High Priority)

### Problem
Two separate reference range systems exist causing confusion:
- `reference_ranges` (generic, linked to lab_tests)
- `lab_reference_ranges` (field-based, linked to template fields)

### Migration Steps

1. **Create data migration script** to copy data from `reference_ranges` to `lab_reference_ranges`
   - Map `test_name` to `field_code` patterns
   - Preserve age/sex ranges

2. **Update `lab_tests.template_id` population**
   - Run script to auto-link tests to templates based on test name matching

3. **Deprecate `reference_ranges` table**
   - Add `is_active = false` flag
   - Update queries to prefer `lab_reference_ranges`

4. **Create UI for `lab_reference_ranges`**
   - Add CRUD in admin interface

### Breaking Changes
- None (additive migration)

---

## Phase 2: Template Version Immutability (High Priority)

### Problem
Published templates can be re-published, violating immutability.

### Migration Steps

1. **Add migration to create new version on publish**
   ```sql
   -- When publishing, INSERT new version instead of UPDATE
   INSERT INTO lab_template_versions (id, template_id, version, status, schema_json, ...)
   SELECT new_id, template_id, current_version + 1, 'PUBLISHED', schema_json, ...
   FROM lab_template_versions WHERE status = 'DRAFT';
   ```

2. **Update publish endpoint** to create new version record

3. **Compute checksum** on publish
   - SHA-256 hash of schema_json

### Breaking Changes
- None

---

## Phase 3: Role-Based Verification/Authorization (High Priority)

### Problem
Same user can verify and authorize results.

### Migration Steps

1. **Add new permissions**
   - `verify_results` - Can verify submitted results
   - `authorize_results` - Can authorize verified results (must be different from verifier)
   - `amend_results` - Can amend released results

2. **Update role definitions**
   - Add "Lab Verifier" role (can verify, cannot authorize)
   - Add "Lab Authorizer" role (can authorize)

3. **Update verify/authorize endpoints**
   ```python
   @router.post("/lab/orders/{id}/verify")
   async def verify_result(order_id, current_user=Depends(role_required(["Lab Staff", "Lab Verifier"]))):
       # Verify implementation

   @router.post("/lab/orders/{id}/authorize")
   async def authorize_result(order_id, current_user=Depends(role_required(["Lab Authorizer"]))):
       # Check that verifier != authorizer
       if lab_order.verified_by_id == current_user.id:
           raise HTTPException(400, "Cannot authorize your own verified results")
   ```

### Breaking Changes
- Existing users may need role reassignment
- Consider default Lab Staff to have both permissions initially, then split

---

## Phase 4: Field-Level Audit Trail (High Priority)

### Problem
Audit events are not field-level; no UI to view history.

### Migration Steps

1. **Add new audit table columns**
   ```sql
   ALTER TABLE lab_audit_events ADD COLUMN field_code VARCHAR(100);
   ALTER TABLE lab_audit_events ADD COLUMN old_value JSONB;
   ALTER TABLE lab_audit_events ADD COLUMN new_value JSONB;
   ```

2. **Update audit logging** in result entry endpoint
   - Track changed fields with before/after values

3. **Create audit history UI**
   - Add "View History" button on lab order detail
   - Show timeline of changes per field

### Breaking Changes
- None

---

## Phase 5: Critical Value Notifications (High Priority)

### Problem
No alert system for critical values.

### Migration Steps

1. **Add notification preferences table**
   ```sql
   CREATE TABLE lab_notification_preferences (
       id SERIAL PRIMARY KEY,
       user_id INTEGER REFERENCES users(id),
       notify_sms BOOLEAN DEFAULT true,
       notify_email BOOLEAN DEFAULT false,
       critical_only BOOLEAN DEFAULT false
   );
   ```

2. **Add notification service**
   - SMS notification via existing SMS service
   - Email notification

3. **Update authorization workflow**
   - Check for critical flags before releasing
   - Require communication documentation
   - Trigger notifications

### Breaking Changes
- None

---

## Phase 6: Template Builder Enhancements (Medium Priority)

### Problem
Template builder lacks field-level reference range configuration.

### Migration Steps

1. **Add reference range fields to template schema**
   ```json
   {
     "code": "Hb",
     "type": "numeric",
     "label": "Hemoglobin",
     "referenceRange": {
       "low": 12.0,
       "high": 17.5,
       "unit": "g/dL",
       "criticalLow": 7.0,
       "criticalHigh": 20.0
     }
   }
   ```

2. **Update template builder UI**
   - Add "Reference Range" section in property panel
   - Pre-populate from `lab_reference_ranges` if exists

3. **Update result validation service**
   - Read ranges from template schema first
   - Fall back to `lab_reference_ranges`

### Breaking Changes
- None

---

## Phase 7: Calculated Fields (Medium Priority)

### Problem
Calculated field formulas not executed.

### Migration Steps

1. **Add calculated field execution engine**
   ```python
   def evaluate_calculated_fields(schema_json, result_json):
       calculated = schema_json.get("calculated", [])
       for calc in calculated:
           target = calc["target_code"]
           formula = calc["formula"]
           # Evaluate formula using result_json values
           result_json[target] = evaluate(formula, result_json)
       return result_json
   ```

2. **Execute on result submission**
   - Call evaluation before storing result
   - Store calculated values in result_json

3. **Support common formulas**
   - Simple arithmetic (+, -, *, /)
   - Ratios (e.g., LDL = Total - HDL - Trig/5)
   - Unit conversions

### Breaking Changes
- None

---

## Rollback Strategy

For each phase:

1. **Database**: Use Alembic migrations with `downgrade()` functions
2. **Code**: Maintain backward-compatible endpoints during transition
3. **Data**: Never delete, use soft-delete flags
4. **Feature Flags**: Can disable new features via config

---

## Testing Strategy

1. **Unit Tests**: Test each service component
2. **Integration Tests**: Test API endpoints with mock data
3. **Manual Testing**: UI testing for each new feature
4. **Data Validation**: Run scripts on test database first
5. **Rollback Test**: Verify downgrade works correctly

---

## Implementation Order

| Phase | Priority | Est. Effort | Dependencies |
|-------|----------|-------------|--------------|
| Phase 1: Reference Range Consolidation | High | 2 days | None |
| Phase 2: Template Version Immutability | High | 1 day | None |
| Phase 3: Role-Based Verification | High | 2 days | Phase 1 |
| Phase 4: Field-Level Audit | High | 3 days | None |
| Phase 5: Critical Value Notifications | High | 2 days | Phase 3 |
| Phase 6: Builder Enhancements | Medium | 3 days | Phase 1 |
| Phase 7: Calculated Fields | Medium | 2 days | None |

**Total Estimated Effort**: ~15 days

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Data migration corruption | Backup before migration, test on copy |
| Breaking existing workflows | Feature flags, gradual rollout |
| Performance impact | Index optimization, caching |
| User confusion | Training, documentation, UI hints |
