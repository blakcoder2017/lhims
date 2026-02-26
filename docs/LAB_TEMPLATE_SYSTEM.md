# Lab Template System

## Overview

The Lab Template System provides structured, template-driven result entry for laboratory tests. Instead of free-text results, each test type uses a defined template with fields, validation rules, and optional calculations.

## Key Concepts

### Template Lifecycle
- **DRAFT**: Editable schema; can be modified via the Template Builder
- **PUBLISHED**: Immutable; used for result entry
- **ARCHIVED**: No longer available for new orders

### Versioning
- Published templates are immutable
- Each publish creates a new version (v1, v2, ...)
- Results store `template_id` and `template_version_used` at capture time
- Old results remain renderable even after template changes

## Template JSON Format

```json
{
  "meta": {
    "name": "Full Blood Count (FBC)",
    "discipline": "HEMATOLOGY",
    "version": 1
  },
  "layout": {
    "sections": [
      {
        "id": "sec_core",
        "title": "Core Indices",
        "rows": [{
          "columns": [
            {"width": 6, "items": ["fld_hb", "fld_wbc"]},
            {"width": 6, "items": ["fld_platelets"]}
          ]
        }]
      }
    ]
  },
  "fields": {
    "fld_hb": {
      "type": "numeric",
      "code": "hb",
      "label": "Haemoglobin",
      "unit": "g/dL",
      "decimals": 1,
      "required": true,
      "critical": {"low": 5.0, "high": 20.0}
    }
  },
  "rules": {
    "visibility": [],
    "requiredIf": []
  },
  "calculated": []
}
```

### Field Types
- `numeric` – number with optional min/max/decimals/unit
- `text` – free text
- `choice` – single select (options or optionSet)
- `multichoice` – multiple select
- `datetime` – date/time
- `repeat_group` – repeatable block
- `table` – grid (e.g. AST)
- `calculated` – read-only, formula-derived

### Option Sets
Reusable picklists stored in `lab_option_sets` (e.g. DIPSTICK_SCALE, HIV_KIT_NAMES). Reference in fields with `"optionSet": "CODE"`.

## Test Catalog Mapping

1. In Lab Test Catalog, each test can have `template_id` and `template_version`
2. When a lab order is created with that test, the template is resolved on first result entry
3. `lab_order.template_id` and `lab_order.template_version_used` are set
4. Result entry uses the resolved schema

## Result Workflow

- **DRAFT**: Partial save; can edit
- **SUBMITTED**: Validation passed; ready for verification
- **VERIFIED**: Lab scientist verified (`POST /lab/orders/{id}/verify`)
- **RELEASED**: Authorized; final (`POST /lab/orders/{id}/authorize`)
- **AMENDED**: Original marked amended; new order created with `previous_version_id` (`POST /lab/orders/{id}/amend`)

Server-side validation runs on Submit. Reference ranges and critical flags are computed and stored in `flags_json`.

## Creating and Publishing Templates

1. Go to **Laboratory → Result Templates**
2. Click **New Template** → enter name and discipline
3. In the Builder: add sections, drag fields from the palette
4. **Save Draft** to persist changes
5. **Publish** to create an immutable version (validates schema first)

## Ghana Starter Pack

Run `python3 scripts/seed_lab_templates_ghana.py` to seed:
- Option sets: DIPSTICK_SCALE, URINE_COLOUR, ORGANISM_LIST, ANTIBIOTIC_LIST, HIV_KIT_NAMES, etc.
- Templates: FBC, Malaria RDT, U&E, Blood Grouping
- Reference ranges for hb, wbc, platelets, sodium, potassium, creatinine
- Mapping of lab_tests to templates by name/code

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /lab/templates | List templates |
| POST | /lab/templates | Create template |
| GET | /lab/templates/{id} | Builder page |
| PUT | /lab/templates/{id}/draft | Save draft (JSON body) |
| GET | /lab/templates/{id}/resolve?version= | Resolve schema (published) |
| POST | /lab/templates/{id}/publish | Publish draft |
| POST | /lab/templates/{id}/archive | Archive |
