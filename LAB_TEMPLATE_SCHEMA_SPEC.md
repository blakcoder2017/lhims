# Lab Template JSON Schema Specification

This document defines the structure of `schema_json` used in `lab_template_versions`.

## Top-Level Structure

```json
{
  "meta": { ... },
  "layout": { ... },
  "fields": { ... },
  "rules": { ... },
  "calculated": [ ... ]
}
```

---

## 1. Meta Section

Contains template metadata.

```json
{
  "meta": {
    "name": "Complete Blood Count",
    "discipline": "HEMATOLOGY",
    "version": 1,
    "description": "Standard CBC with differential"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name of the template |
| `discipline` | string | Yes | Lab discipline (HEMATOLOGY, CHEMISTRY, MICROBIOLOGY, etc.) |
| `version` | integer | No | Template version number |
| `description` | string | No | Human-readable description |

---

## 2. Layout Section

Defines the visual structure - sections, rows, columns, and items.

```json
{
  "layout": {
    "sections": [
      {
        "id": "sec_patient",
        "title": "Patient Information",
        "rows": [
          {
            "columns": [
              {
                "width": 6,
                "items": ["patient_id", "collection_date"]
              },
              {
                "width": 6,
                "items": ["patient_name"]
              }
            }
          }
        ]
      }
    ]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `sections` | array | Ordered list of sections |
| `sections[].id` | string | Unique section identifier |
| `sections[].title` | string | Section header text |
| `sections[].rows` | array | Rows within section |
| `rows[].columns` | array | Columns in row (widths should sum to 12) |
| `columns[].width` | integer | Bootstrap column width (1-12) |
| `columns[].items` | array | Field IDs to display in this column |

---

## 3. Fields Section

Dictionary of field definitions, keyed by field ID.

```json
{
  "fields": {
    "hemoglobin": {
      "code": "Hb",
      "type": "numeric",
      "label": "Hemoglobin",
      "placeholder": "Enter Hb value",
      "required": true,
      "min": 0,
      "max": 30,
      "decimals": 1,
      "unit": "g/dL",
      "critical": false,
      "criticalLow": 7.0,
      "criticalHigh": 20.0,
      "tooltip": "Hemoglobin level"
    },
    "blood_group": {
      "code": "BG",
      "type": "choice",
      "label": "Blood Group",
      "options": ["A", "B", "AB", "O"],
      "required": true
    },
    "notes": {
      "code": "NOTES",
      "type": "text",
      "label": "Laboratory Notes",
      "rows": 3
    }
  }
}
```

### Common Field Properties

| Property | Type | Description |
|----------|------|-------------|
| `code` | string | **Required** - Unique code for result storage and reference range lookup |
| `type` | string | **Required** - Field type (see below) |
| `label` | string | Display label |
| `placeholder` | string | Input placeholder text |
| `required` | boolean | Is field required? |
| `tooltip` | string | Help text |
| `readOnly` | boolean | Read-only field |
| `hidden` | boolean | Hidden field |

### Field Types

#### numeric
```json
{
  "type": "numeric",
  "min": 0,
  "max": 100,
  "decimals": 2,
  "unit": "mg/dL",
  "critical": true,
  "criticalLow": 10.0,
  "criticalHigh": 500.0,
  "referenceRange": {
    "low": 70,
    "high": 120
  }
}
```

#### text
```json
{
  "type": "text",
  "rows": 3,
  "maxLength": 500
}
```

#### choice (single select)
```json
{
  "type": "choice",
  "options": ["Negative", "Positive", "Trace"],
  "optionSet": "DIPSTICK_SCALE"
}
```

#### multichoice (multi select)
```json
{
  "type": "multichoice",
  "options": ["Fever", "Cough", "Fatigue", "Other"],
  "minSelected": 1,
  "maxSelected": 3
}
```

#### datetime
```json
{
  "type": "datetime",
  "format": "YYYY-MM-DD HH:mm"
}
```

#### note (display text)
```json
{
  "type": "note",
  "content": "Specimen received in good condition",
  "cssClass": "alert-info"
}
```

#### divider (visual separator)
```json
{
  "type": "divider",
  "title": "Section Header"
}
```

#### repeat_group (repeating fields)
```json
{
  "type": "repeat_group",
  "label": "Culture Results",
  "minRepeats": 1,
  "maxRepeats": 5,
  "childFields": ["organism", "colony_count", "sensitivity"]
}
```

#### table (grid)
```json
{
  "type": "table",
  "label": "Differential Count",
  "rowOptions": ["Neutrophils", "Lymphocytes", "Monocytes", "Eosinophils", "Basophils"],
  "colOptions": ["%", "Absolute"],
  "rowOptionSet": "DIFF_CELLS",
  "colOptionSet": "DIFF_UNITS"
}
```

---

## 4. Rules Section

Conditional logic for field visibility and required status.

```json
{
  "rules": {
    "visibility": [
      {
        "target": "sensitivity_fields",
        "showIf": {
          "field": "culture_result",
          "op": "==",
          "value": "Positive"
        }
      }
    ],
    "requiredIf": [
      {
        "target": "organism",
        "if": {
          "field": "culture_performed",
          "op": "==",
          "value": true
        }
      }
    ]
  }
}
```

### Visibility Rule
```json
{
  "target": "field_id_to_show",
  "showIf": {
    "field": "trigger_field_id",
    "op": "==|!=|contains|not contains|in|not in",
    "value": "trigger_value"
  }
}
```

### RequiredIf Rule
```json
{
  "target": "field_id",
  "if": {
    "field": "trigger_field_id",
    "op": "==|!=",
    "value": "value"
  }
}
```

---

## 5. Calculated Section

Auto-computed fields based on formulas.

```json
{
  "calculated": [
    {
      "target_code": "mch",
      "formula": "Hb * 1000 / RBC",
      "deps": ["hemoglobin", "rbc_count"],
      "label": "MCH",
      "unit": "pg",
      "decimals": 1
    },
    {
      "target_code": "anion_gap",
      "formula": "Na + K - (Cl + HCO3)",
      "deps": ["sodium", "potassium", "chloride", "bicarbonate"],
      "label": "Anion Gap",
      "unit": "mEq/L"
    }
  ]
}
```

### Formula Syntax
- Basic arithmetic: `+`, `-`, `*`, `/`
- Parentheses for grouping
- Field codes as variable names
- Example: `(field_a + field_b) / 2`

---

## Example: Complete CBC Template

```json
{
  "meta": {
    "name": "Complete Blood Count",
    "discipline": "HEMATOLOGY",
    "version": 1
  },
  "layout": {
    "sections": [
      {
        "id": "sec_main",
        "title": "CBC Results",
        "rows": [
          {
            "columns": [
              {"width": 4, "items": ["hemoglobin"]},
              {"width": 4, "items": ["hematocrit"]},
              {"width": 4, "items": ["rbc_count"]}
            ]
          },
          {
            "columns": [
              {"width": 12, "items": ["differential_table"]}
            ]
          }
        ]
      }
    ]
  },
  "fields": {
    "hemoglobin": {
      "code": "Hb",
      "type": "numeric",
      "label": "Hemoglobin",
      "unit": "g/dL",
      "decimals": 1,
      "critical": true,
      "criticalLow": 7.0,
      "criticalHigh": 20.0,
      "required": true
    },
    "hematocrit": {
      "code": "Hct",
      "type": "numeric",
      "label": "Hematocrit",
      "unit": "%",
      "decimals": 1,
      "required": true
    },
    "rbc_count": {
      "code": "RBC",
      "type": "numeric",
      "label": "RBC Count",
      "unit": "10^6/uL",
      "decimals": 2
    },
    "differential_table": {
      "code": "DIFF",
      "type": "table",
      "label": "Differential Count",
      "rowOptions": ["Neutrophils", "Lymphocytes", "Monocytes", "Eosinophils", "Basophils"],
      "colOptions": ["%", "Absolute"]
    }
  },
  "rules": {
    "visibility": [],
    "requiredIf": []
  },
  "calculated": [
    {
      "target_code": "mch",
      "formula": "Hb * 1000 / RBC",
      "deps": ["hemoglobin", "rbc_count"],
      "label": "MCH",
      "unit": "pg"
    }
  ]
}
```
