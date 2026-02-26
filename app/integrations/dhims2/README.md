# DHIMS2 Integration Module

Production-ready integration module for submitting routine health service data from LHIMS to Ghana's DHIMS2 (DHIS2-based) system.

## Overview

This module provides a complete solution for:
- Validating health data against Ghana reporting standards
- Approving submissions before sending to DHIMS2
- Submitting data via DHIS2 Web API with robust retry handling
- Maintaining full audit trail of all operations

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# DHIMS2/DHIS2 Base URL
DHIMS2_BASE_URL=https://dhims2.ghana.gov.gh

# DHIMS2 API credentials
DHIMS2_USERNAME=your_username
DHIMS2_PASSWORD=your_password

# API settings
DHIMS2_TIMEOUT_SECONDS=30
DHIMS2_VERIFY_TLS=true
DHIMS2_MAX_RETRIES=5
DHIMS2_BACKOFF_SECONDS=2

# Instance identification
DHIMS2_INSTANCE_NAME=production

# Data locking (days after period end)
DHIMS2_DATA_LOCK_DAYS=60

# Dry run mode (validates but doesn't submit)
DHIMS2_DRY_RUN=false
```

## Database Setup

Run the migration to create required tables:

```bash
alembic upgrade head
```

This creates:
- `dhims2_instances` - DHIMS2 server configurations
- `dhims2_mappings` - Metric to DHIS2 element mappings
- `dhims2_org_unit_mappings` - Facility to org unit mappings
- `dhims2_submission_runs` - Submission packages
- `dhims2_submission_items` - Individual data values
- `dhims2_audit_logs` - Complete audit trail

## Quick Start

### 1. Configure DHIMS2 Instance

Create a DHIMS2 instance via API:

```bash
POST /api/dhims2/instances
{
  "name": "Production DHIMS2",
  "base_url": "https://dhims2.ghana.gov.gh",
  "username": "your_username",
  "password": "your_password",
  "timeout_seconds": 30,
  "verify_tls": true,
  "max_retries": 5
}
```

### 2. Create Metric Mappings

Map your internal metrics to DHIS2 data elements:

```bash
POST /api/dhims2/mappings
{
  "instance_id": 1,
  "internal_metric_key": "OPD_TOTAL",
  "dhis2_data_element_uid": "f7n2E3t1n0W",
  "dhis2_category_option_combo_uid": null,
  "value_type": "numeric",
  "is_required": true
}
```

### 3. Create Org Unit Mappings

Map your facilities to DHIS2 org units:

```bash
POST /api/dhims2/org-unit-mappings
{
  "instance_id": 1,
  "internal_org_id": 1,
  "internal_org_type": "department",
  "dhis2_org_unit_uid": "O6uvpzGd5hi"
}
```

### 4. Build Submission

Create a draft submission from LHIMS data:

```bash
POST /api/dhims2/runs/build
{
  "instance_id": 1,
  "org_unit_uid": "O6uvpzGd5hi",
  "period": "2026-01",
  "report_type": "monthly_service",
  "dataset_uid": "Ds123456789",
  "provider": "aggregated_indicators"
}
```

### 5. Validate

Run data quality checks:

```bash
POST /api/dhims2/runs/1/validate
{
  "required_metrics": ["OPD_TOTAL", "OPD_MALE", "OPD_FEMALE"]
}
```

### 6. Submit for Approval

Move to approval workflow:

```bash
POST /api/dhims2/runs/1/submit-for-approval
```

### 7. Approve (Different User)

Approver reviews and approves:

```bash
POST /api/dhims2/runs/1/approve
```

### 8. Submit to DHIMS2

Send approved data to DHIMS2:

```bash
POST /api/dhims2/runs/1/submit
{
  "dry_run": false
}
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dhims2/instances` | POST | Create instance |
| `/api/dhims2/instances` | GET | List instances |
| `/api/dhims2/mappings` | POST | Create mapping |
| `/api/dhims2/mappings` | GET | List mappings |
| `/api/dhims2/org-unit-mappings` | POST | Create org unit mapping |
| `/api/dhims2/runs/build` | POST | Build submission |
| `/api/dhims2/runs/{id}/validate` | POST | Validate submission |
| `/api/dhims2/runs/{id}/submit-for-approval` | POST | Submit for approval |
| `/api/dhims2/runs/{id}/approve` | POST | Approve submission |
| `/api/dhims2/runs/{id}/submit` | POST | Submit to DHIMS2 |
| `/api/dhims2/runs` | GET | List submissions |
| `/api/dhims2/runs/{id}` | GET | Get submission details |
| `/api/dhims2/metadata/sync` | POST | Sync DHIS2 metadata |
| `/api/dhims2/health` | GET | Check connectivity |

## Approval Workflow

```
DRAFT → PENDING_APPROVAL → APPROVED → SUBMITTED
   ↓          ↓                    ↓
VALIDATION_FAILED    SUBMIT_FAILED
```

Rules:
- Only "Preparer" can create draft runs
- Only "Approver" can approve submissions
- Approver cannot be the same as preparer (unless `allow_self_approval=true`)
- After APPROVED, payload hash is frozen
- After SUBMITTED, run is immutable

## Data Quality Checks

### Completeness
- Required metrics must be present
- Configurable per report type

### Validity
- Numeric values must be valid numbers
- Non-negative checks for counts

### Consistency
- Cross-check rules (e.g., OPD_TOTAL >= OPD_MALE + OPD_FEMALE)
- Configurable rules per metric mapping

### Timeliness
- Warning if submission after due date
- Doesn't block submission

### Locking
- Data locked after 60 days (configurable)
- Override requires justification + audit log

## Error Codes

| Code | Meaning |
|------|---------|
| 401 | Authentication failed |
| 403 | Access forbidden |
| 404 | Resource not found |
| 409 | Data conflict (duplicate) |
| 5xx | DHIS2 server error |

## Security

- Credentials stored encrypted (at rest)
- TLS verification configurable
- Audit logs for all operations
- Role-based access control
- No PII in logs

## Testing

Run unit tests:

```bash
pytest app/integrations/dhims2/tests/test_dhims2.py -v
```

## Common Issues

### Connection Timeout
- Check `DHIMS2_BASE_URL` is correct
- Verify network access to DHIMS2
- Increase `DHIMS2_TIMEOUT_SECONDS`

### Validation Failures
- Check required metrics are mapped
- Verify numeric values are valid
- Review cross-check rules

### Submission Failures
- Check credentials are correct
- Verify org unit UID exists in DHIS2
- Review error summary in response
