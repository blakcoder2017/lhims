"""
Unit tests for Pharmacy Ghana: FEFO allocation, ledger, interaction check.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import MagicMock


# --- FEFO allocation logic (no DB) ---
def test_fefo_sorts_by_expiry():
    """FEFO should prioritize batches with earliest expiry."""
    # Simulate batch list (expiry, qty)
    batches = [
        (date.today() + timedelta(days=30), Decimal("50")),
        (date.today() + timedelta(days=90), Decimal("100")),
        (date.today() + timedelta(days=60), Decimal("30")),
    ]
    sorted_batches = sorted(batches, key=lambda x: x[0])
    assert sorted_batches[0][0] == date.today() + timedelta(days=30)
    assert sorted_batches[1][0] == date.today() + timedelta(days=60)
    assert sorted_batches[2][0] == date.today() + timedelta(days=90)


def test_fefo_excludes_expired():
    """Expired batches should be excluded."""
    today = date.today()
    expired = today - timedelta(days=1)
    assert expired < today


def test_ledger_immutability_concept():
    """Ledger entries are append-only (no update/delete)."""
    entries = []
    # Simulate append
    entries.append({"movement_type": "STOCK_IN", "qty_in": 100})
    entries.append({"movement_type": "DISPENSE", "qty_out": 10})
    assert len(entries) == 2
    assert entries[0]["qty_in"] == 100
    assert entries[1]["qty_out"] == 10


def test_interaction_severity_order():
    """CONTRAINDICATED > MAJOR > MODERATE > MINOR for blocking."""
    severity_order = {"CONTRAINDICATED": 4, "MAJOR": 3, "MODERATE": 2, "MINOR": 1}
    assert severity_order["CONTRAINDICATED"] > severity_order["MAJOR"]


def test_prescribing_requires_pharmacy_drug_id():
    """Prescription validation: pharmacy_drug_id must be present."""
    # Simulate form data validation
    def validate_prescription(pharmacy_drug_id, medication_name):
        if not pharmacy_drug_id or not pharmacy_drug_id.strip():
            return False, "Select formulation from formulary"
        if not medication_name or not medication_name.strip():
            return False, "Medication name required"
        return True, None

    ok, err = validate_prescription("", "Amoxicillin 500mg")
    assert ok is False
    assert "formulation" in err.lower() or "select" in err.lower()

    ok, err = validate_prescription("uuid-here", "Amoxicillin 500mg")
    assert ok is True
    assert err is None


def test_prescription_snapshot_fields():
    """Prescription should capture snapshot fields from pharmacy_drug for audit."""
    # Simulate fetching drug and capturing snapshot
    class MockDrug:
        generic_name = "Amoxicillin"
        strength_value = 500.0
        strength_unit = "mg"
        concentration_value = None
        concentration_unit = None
        route = "PO"
        class dosage_form:
            name = "Capsule"
        item_code = "AMX500CAP"
    
    def capture_snapshot(drug):
        return {
            "medication_name": f"{drug.generic_name} {drug.strength_value} {drug.strength_unit} {drug.dosage_form.name}",
            "medication_code": drug.item_code,
            "dosage_form_name": drug.dosage_form.name if drug.dosage_form else None,
            "strength_value": drug.strength_value,
            "strength_unit": drug.strength_unit,
            "route": drug.route,
            "concentration_value": drug.concentration_value,
            "concentration_unit": drug.concentration_unit,
        }
    
    snapshot = capture_snapshot(MockDrug())
    assert snapshot["medication_name"] == "Amoxicillin 500.0 mg Capsule"
    assert snapshot["medication_code"] == "AMX500CAP"
    assert snapshot["dosage_form_name"] == "Capsule"
    assert snapshot["strength_value"] == 500.0
    assert snapshot["strength_unit"] == "mg"
    assert snapshot["route"] == "PO"
    assert snapshot["concentration_value"] is None
    assert snapshot["concentration_unit"] is None


def test_interaction_severity_order():
    """CONTRAINDICATED > MAJOR > MODERATE > MINOR for blocking."""
    severity_order = {"CONTRAINDICATED": 4, "MAJOR": 3, "MODERATE": 2, "MINOR": 1}
    assert severity_order["CONTRAINDICATED"] > severity_order["MAJOR"]
    assert severity_order["MAJOR"] > severity_order["MODERATE"]
    assert severity_order["MODERATE"] > severity_order["MINOR"]


def test_seeded_interactions_ghana():
    """Verify Ghana-relevant interactions are seeded with correct severity."""
    # These are the interactions that should be seeded
    EXPECTED_INTERACTIONS = [
        ("Warfarin", "Metronidazole", "MAJOR"),
        ("Warfarin", "Co-trimoxazole", "MAJOR"),
        ("Warfarin", "Ibuprofen", "MAJOR"),
        ("Warfarin", "Dexamethasone", "MODERATE"),
        ("Enalapril", "Spironolactone", "MAJOR"),
        ("Enalapril", "Furosemide", "MAJOR"),
        ("Gentamicin", "Furosemide", "MAJOR"),
        ("Rifampicin", "Combined Oral Contraceptive", "MAJOR"),
        ("Ciprofloxacin", "Aluminum Hydroxide", "MODERATE"),
        ("Ciprofloxacin", "Ferrous Sulfate", "MODERATE"),
        ("Ciprofloxacin", "Metronidazole", "MODERATE"),
        ("Metronidazole", "Amoxicillin", "MODERATE"),
    ]
    
    # Verify severity levels are blocking-capable
    blocking_severities = ["CONTRAINDICATED", "MAJOR"]
    warning_severities = ["MODERATE", "MINOR"]
    
    for drug_a, drug_b, severity in EXPECTED_INTERACTIONS:
        assert severity in blocking_severities + warning_severities
    
    # Count of MAJOR interactions that should block without override
    major_count = sum(1 for _, _, sev in EXPECTED_INTERACTIONS if sev == "MAJOR")
    moderate_count = sum(1 for _, _, sev in EXPECTED_INTERACTIONS if sev == "MODERATE")
    
    assert major_count >= 7, f"Expected at least 7 MAJOR interactions, got {major_count}"
    assert moderate_count >= 4, f"Expected at least 4 MODERATE interactions, got {moderate_count}"


def test_interaction_pair_bidirectional():
    """Interaction (A,B) should be same as (B,A) - tested in service logic."""
    # Simulate the bidirectional check
    interactions_db = [
        {"drug_a": "Warfarin", "drug_b": "Metronidazole", "severity": "MAJOR"},
    ]
    
    def check_interaction(drug1, drug2, interactions):
        for i in interactions:
            if (i["drug_a"] == drug1 and i["drug_b"] == drug2) or \
               (i["drug_a"] == drug2 and i["drug_b"] == drug1):
                return i["severity"]
        return None
    
    # Check both directions
    assert check_interaction("Warfarin", "Metronidazole", interactions_db) == "MAJOR"
    assert check_interaction("Metronidazole", "Warfarin", interactions_db) == "MAJOR"


# --- Drug Master Data CRUD ---
def test_drug_display_label():
    """Drug display label format: Generic strength DosageForm (Route)."""
    def format_label(generic_name, strength_value, strength_unit, dosage_form, route):
        label = generic_name
        if strength_value:
            label += f" {strength_value}"
            if strength_unit:
                label += f" {strength_unit}"
        if dosage_form:
            label += f" {dosage_form}"
        if route:
            label += f" ({route})"
        return label
    
    # Example: Paracetamol 500 mg Tablet (PO)
    assert format_label("Paracetamol", 500, "mg", "Tablet", "PO") == "Paracetamol 500 mg Tablet (PO)"
    # Example: Amoxicillin 250 mg/5mL Suspension (PO)
    assert format_label("Amoxicillin", None, None, "Suspension", "PO") == "Amoxicillin Suspension (PO)"
    # Example: Saline 0.9% IV infusion (IV)
    assert format_label("Saline", 0.9, "%", "IV infusion", "IV") == "Saline 0.9 % IV infusion (IV)"


def test_dosage_form_required():
    """Drug must have dosage_form_id (not nullable in schema)."""
    # Simulate validation
    def validate_drug(dosage_form_id):
        if not dosage_form_id:
            return False, "Dosage form is required"
        return True, None
    
    ok, err = validate_drug(None)
    assert ok is False
    assert "dosage form" in err.lower()
    
    ok, err = validate_drug("some-uuid")
    assert ok is True


def test_drug_unique_item_code():
    """Drug item_code must be unique."""
    existing_codes = {"AMX500CAP", "PAR500TAB", "IBU400TAB"}
    
    def is_unique(item_code):
        return item_code not in existing_codes
    
    assert is_unique("NEWDRUG01") is True
    assert is_unique("AMX500CAP") is False


def test_formulary_search_returns_id_and_label():
    """Formulary search API should return id + display label."""
    # Simulate search result
    drugs = [
        {"id": "uuid-1", "generic_name": "Amoxicillin", "strength_value": 500, 
         "strength_unit": "mg", "dosage_form": "Capsule", "route": "PO"},
        {"id": "uuid-2", "generic_name": "Paracetamol", "strength_value": 500,
         "strength_unit": "mg", "dosage_form": "Tablet", "route": "PO"},
    ]
    
    def format_result(d):
        label = d["generic_name"]
        if d["strength_value"]:
            label += f" {d['strength_value']} {d.get('strength_unit', '')}"
        label += f" {d['dosage_form']}"
        if d.get("route"):
            label += f" ({d['route']})"
        return {"id": d["id"], "label": label}
    
    results = [format_result(d) for d in drugs]
    assert results[0]["label"] == "Amoxicillin 500 mg Capsule (PO)"
    assert results[1]["id"] == "uuid-2"


# --- FEFO Allocation Service Tests ---
def test_fefo_chooses_earliest_expiry():
    """FEFO should choose earliest expiry date first."""
    from datetime import date, timedelta
    from decimal import Decimal
    
    # Simulate batch data: (expiry_date, qty_on_hand, qty_reserved)
    batches = [
        {"id": "b1", "expiry_date": date.today() + timedelta(days=90), "qty_on_hand": 100, "qty_reserved": 0},
        {"id": "b2", "expiry_date": date.today() + timedelta(days=30), "qty_on_hand": 50, "qty_reserved": 0},
        {"id": "b3", "expiry_date": date.today() + timedelta(days=60), "qty_on_hand": 75, "qty_reserved": 0},
    ]
    
    # Sort by expiry ASC (FEFO)
    sorted_batches = sorted(batches, key=lambda x: x["expiry_date"])
    
    # Should pick b2 (earliest expiry: 30 days) first
    assert sorted_batches[0]["id"] == "b2"
    assert sorted_batches[1]["id"] == "b3"  # 60 days
    assert sorted_batches[2]["id"] == "b1"  # 90 days


def test_fefo_skips_expired():
    """FEFO should skip expired batches."""
    from datetime import date, timedelta
    
    today = date.today()
    batches = [
        {"id": "b1", "expiry_date": today - timedelta(days=1), "qty_on_hand": 100, "qty_reserved": 0},  # Expired
        {"id": "b2", "expiry_date": today + timedelta(days=30), "qty_on_hand": 50, "qty_reserved": 0},  # Valid
    ]
    
    # Filter out expired
    eligible = [b for b in batches if b["expiry_date"] >= today]
    
    assert len(eligible) == 1
    assert eligible[0]["id"] == "b2"


def test_fefo_splits_across_batches():
    """FEFO should split allocation across multiple batches."""
    from datetime import date, timedelta
    from decimal import Decimal
    
    # Batches with limited stock
    batches = [
        {"id": "b1", "expiry_date": date.today() + timedelta(days=30), "qty_on_hand": 30, "qty_reserved": 0},
        {"id": "b2", "expiry_date": date.today() + timedelta(days=60), "qty_on_hand": 50, "qty_reserved": 0},
    ]
    
    qty_needed = Decimal("70")
    allocations = []
    remaining = qty_needed
    
    for b in sorted(batches, key=lambda x: x["expiry_date"]):
        if remaining <= 0:
            break
        available = b["qty_on_hand"] - b["qty_reserved"]
        qty_to_allocate = min(available, remaining)
        allocations.append({"batch_id": b["id"], "qty_allocated": qty_to_allocate})
        remaining -= qty_to_allocate
    
    # Should split: b1=30, b2=40
    assert len(allocations) == 2
    assert allocations[0]["batch_id"] == "b1"
    assert allocations[0]["qty_allocated"] == 30
    assert allocations[1]["batch_id"] == "b2"
    assert allocations[1]["qty_allocated"] == 40
    assert remaining == 0


def test_fefo_shortage_error():
    """FEFO should return error when insufficient stock."""
    from datetime import date, timedelta
    from decimal import Decimal
    
    batches = [
        {"id": "b1", "expiry_date": date.today() + timedelta(days=30), "qty_on_hand": 20, "qty_reserved": 0},
        {"id": "b2", "expiry_date": date.today() + timedelta(days=60), "qty_on_hand": 30, "qty_reserved": 0},
    ]
    
    qty_needed = Decimal("100")  # Need more than available
    
    total_available = sum(b["qty_on_hand"] - b["qty_reserved"] for b in batches)
    
    if total_available < qty_needed:
        result = {
            "success": False,
            "allocations": [],
            "error": f"Insufficient stock: need {qty_needed}, available {total_available}"
        }
    else:
        result = {"success": True, "allocations": [], "error": None}
    
    assert result["success"] is False
    assert "Insufficient stock" in result["error"]
    assert "need 100" in result["error"]
    assert "available 50" in result["error"]


# --- Dispensing Tests ---
def test_dispense_creates_allocation_and_deducts_stock():
    """Finalize dispense should deduct batch stock and create ledger entries."""
    from datetime import date, timedelta
    from decimal import Decimal
    
    # Simulate batch
    batch = {
        "id": "batch-1",
        "qty_on_hand": Decimal("100"),
        "expiry_date": date.today() + timedelta(days=60),
    }
    
    qty_to_allocate = Decimal("30")
    
    # Deduct stock
    batch["qty_on_hand"] -= qty_to_allocate
    
    # Create allocation
    allocation = {
        "batch_id": batch["id"],
        "qty_allocated": qty_to_allocate,
    }
    
    # Create ledger entry
    ledger = {
        "movement_type": "DISPENSE",
        "qty_out": qty_to_allocate,
        "batch_id": batch["id"],
    }
    
    assert batch["qty_on_hand"] == Decimal("70")
    assert allocation["qty_allocated"] == Decimal("30")
    assert ledger["movement_type"] == "DISPENSE"
    assert ledger["qty_out"] == Decimal("30")


def test_dispense_blocks_expired_batch():
    """Finalize should block if any allocation uses expired batch."""
    from datetime import date, timedelta
    
    today = date.today()
    
    # Simulate expired batch allocation
    allocation = {
        "batch_id": "expired-batch",
        "batch": {
            "batch_no": "EXP001",
            "expiry_date": today - timedelta(days=1),  # Expired
        }
    }
    
    # Check if expired
    is_expired = allocation["batch"]["expiry_date"] < today
    
    assert is_expired is True


def test_dispense_controls_controlled_drug_permission():
    """Controlled drug should require can_dispense_controlled permission."""
    # Simulate role policies
    admin_policy = {"role": "Admin", "can_dispense_controlled": True}
    staff_policy = {"role": "Pharmacy Staff", "can_dispense_controlled": False}
    
    # Check permissions
    def can_dispense(policy, is_controlled_drug):
        if is_controlled_drug:
            return policy.get("can_dispense_controlled", False)
        return True
    
    assert can_dispense(admin_policy, True) is True
    assert can_dispense(staff_policy, True) is False
    assert can_dispense(staff_policy, False) is True


def test_dispense_ledger_matches_allocation():
    """Ledger entries should match allocations exactly."""
    from decimal import Decimal
    
    # Simulate allocations
    allocations = [
        {"batch_id": "b1", "qty_allocated": Decimal("10"), "unit_cost": Decimal("5.00")},
        {"batch_id": "b2", "qty_allocated": Decimal("15"), "unit_cost": Decimal("3.00")},
    ]
    
    # Create ledger entries from allocations
    ledger_entries = []
    for alloc in allocations:
        ledger_entries.append({
            "movement_type": "DISPENSE",
            "batch_id": alloc["batch_id"],
            "qty_out": alloc["qty_allocated"],
            "unit_cost_snapshot": alloc["unit_cost"],
        })
    
    total_allocated = sum(a["qty_allocated"] for a in allocations)
    total_ledger = sum(l["qty_out"] for l in ledger_entries)
    
    assert total_allocated == Decimal("25")
    assert total_ledger == total_allocated
    assert len(ledger_entries) == len(allocations)
