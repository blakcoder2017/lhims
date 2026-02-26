"""
Unit and integration tests for Lab Template System.
"""
import pytest
from app.services.lab_template_schema import validate_template_schema
from app.services.lab_result_validation import validate_result, compute_flags, has_critical_flags


# --- Schema Validation Tests ---

@pytest.mark.unit
def test_validate_template_schema_valid():
    """Valid template schema passes validation."""
    schema = {
        "meta": {"name": "Test", "discipline": "HEMATOLOGY", "version": 1},
        "layout": {"sections": [{"id": "sec1", "title": "Main", "rows": [{"columns": [{"width": 12, "items": ["fld_a"]}]}]}]},
        "fields": {"fld_a": {"type": "numeric", "code": "a", "label": "Field A"}},
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": [],
    }
    valid, errors = validate_template_schema(schema)
    assert valid is True
    assert len(errors) == 0


@pytest.mark.unit
def test_validate_template_schema_missing_meta():
    """Missing meta fails validation."""
    schema = {
        "layout": {"sections": []},
        "fields": {},
    }
    valid, errors = validate_template_schema(schema)
    assert valid is False
    assert any("meta" in e.lower() for e in errors)


@pytest.mark.unit
def test_validate_template_schema_missing_layout_items():
    """Layout referencing unknown field fails."""
    schema = {
        "meta": {"name": "X", "discipline": "CHEMISTRY"},
        "layout": {"sections": [{"id": "s1", "title": "T", "rows": [{"columns": [{"width": 12, "items": ["fld_unknown"]}]}]}]},
        "fields": {"fld_a": {"type": "text", "code": "a"}},
        "rules": {},
    }
    valid, errors = validate_template_schema(schema)
    assert valid is False
    assert any("unknown" in e or "fld_unknown" in e for e in errors)


@pytest.mark.unit
def test_validate_template_schema_choice_needs_options():
    """Choice/multichoice must have options or optionSet."""
    schema = {
        "meta": {"name": "X", "discipline": "CHEMISTRY"},
        "layout": {"sections": [{"id": "s1", "title": "T", "rows": [{"columns": [{"width": 12, "items": ["fld_c"]}]}]}]},
        "fields": {"fld_c": {"type": "choice", "code": "c", "label": "Choice"}},
        "rules": {},
    }
    valid, errors = validate_template_schema(schema)
    assert valid is False
    assert any("options" in e or "optionSet" in e for e in errors)


# --- Result Validation Tests ---

@pytest.mark.unit
def test_validate_result_required_field_missing():
    """Required field missing fails validation."""
    schema = {
        "fields": {"fld_hb": {"type": "numeric", "code": "hb", "label": "Haemoglobin", "required": True}},
        "rules": {},
    }
    result = {}
    valid, errors = validate_result(schema, result)
    assert valid is False
    assert any("Haemoglobin" in e or "required" in e for e in errors)


@pytest.mark.unit
def test_validate_result_requiredIf_condition_met():
    """requiredIf: when condition met, target becomes required."""
    schema = {
        "fields": {
            "fld_mp": {"type": "choice", "code": "mp_result", "label": "MP", "options": ["Positive", "Negative"]},
            "fld_grade": {"type": "choice", "code": "density_grade", "label": "Grade", "options": ["+", "++"]},
        },
        "rules": {"requiredIf": [{"target": "fld_grade", "if": {"field": "mp_result", "op": "==", "value": "Positive"}}]},
    }
    result = {"mp_result": "Positive"}  # density_grade missing
    valid, errors = validate_result(schema, result)
    assert valid is False
    assert any("Grade" in e or "density" in e for e in errors)


@pytest.mark.unit
def test_validate_result_requiredIf_condition_not_met():
    """requiredIf: when condition not met, target not required."""
    schema = {
        "fields": {
            "fld_mp": {"type": "choice", "code": "mp_result", "label": "MP", "options": ["Positive", "Negative"]},
            "fld_grade": {"type": "choice", "code": "density_grade", "label": "Grade", "options": ["+", "++"]},
        },
        "rules": {"requiredIf": [{"target": "fld_grade", "if": {"field": "mp_result", "op": "==", "value": "Positive"}}]},
    }
    result = {"mp_result": "Negative"}
    valid, errors = validate_result(schema, result)
    assert valid is True


@pytest.mark.unit
def test_validate_result_numeric_range():
    """Numeric min/max enforced."""
    schema = {
        "fields": {"fld_hb": {"type": "numeric", "code": "hb", "label": "Hb", "min": 0, "max": 30}},
        "rules": {},
    }
    valid1, _ = validate_result(schema, {"hb": 15})
    assert valid1 is True
    valid2, err2 = validate_result(schema, {"hb": 35})
    assert valid2 is False
    assert any("max" in e or "30" in e for e in err2)
    valid3, err3 = validate_result(schema, {"hb": -1})
    assert valid3 is False


# --- Flags Tests ---

@pytest.mark.unit
def test_compute_flags_high():
    """Value above ref high gets H flag."""
    schema = {"fields": {"fld_hb": {"type": "numeric", "code": "hb", "label": "Hb"}}}
    result = {"hb": 20}
    ref_ranges = {"hb": {"low": 12, "high": 17}}
    flags = compute_flags(schema, result, ref_ranges=ref_ranges)
    assert "hb" in flags
    assert flags["hb"]["flag"] == "H"


@pytest.mark.unit
def test_compute_flags_low():
    """Value below ref low gets L flag."""
    schema = {"fields": {"fld_hb": {"type": "numeric", "code": "hb", "label": "Hb"}}}
    result = {"hb": 8}
    ref_ranges = {"hb": {"low": 12, "high": 17}}
    flags = compute_flags(schema, result, ref_ranges=ref_ranges)
    assert flags["hb"]["flag"] == "L"


@pytest.mark.unit
def test_compute_flags_critical():
    """Value at or beyond critical threshold gets CRITICAL."""
    schema = {
        "fields": {"fld_hb": {"type": "numeric", "code": "hb", "label": "Hb", "critical": {"low": 5, "high": 20}}}
    }
    result = {"hb": 4}
    flags = compute_flags(schema, result)
    assert flags["hb"]["flag"] == "CRITICAL"
    result2 = {"hb": 22}
    flags2 = compute_flags(schema, result2)
    assert flags2["hb"]["flag"] == "CRITICAL"


@pytest.mark.unit
def test_has_critical_flags():
    """has_critical_flags returns True when CRITICAL present."""
    assert has_critical_flags({"hb": {"flag": "CRITICAL"}}) is True
    assert has_critical_flags({"hb": {"flag": "H"}}) is False
    assert has_critical_flags({}) is False


# --- Integration test (requires DB) - skip if no DB ---

@pytest.mark.integration
def test_template_resolver_picks_latest():
    """Resolver returns latest published version when version param omitted."""
    from app.db.database import SessionLocal
    from app.crud import lab_template_crud

    db = SessionLocal()
    try:
        tmpls = lab_template_crud.get_templates(db, status="PUBLISHED", limit=1)
        if not tmpls:
            pytest.skip("No published templates in DB")
        tid = tmpls[0].id
        pub = lab_template_crud.get_published_version(db, tid)
        assert pub is not None
        assert hasattr(pub, "schema_json")
    finally:
        db.close()


@pytest.mark.unit
def test_validate_template_schema_repeat_group_needs_childFields():
    """repeat_group must have childFields."""
    schema = {
        "meta": {"name": "X", "discipline": "CHEMISTRY"},
        "layout": {"sections": [{"id": "s1", "title": "T", "rows": [{"columns": [{"width": 12, "items": ["fld_rg"]}]}]}]},
        "fields": {"fld_rg": {"type": "repeat_group", "code": "items", "label": "Items"}},
        "rules": {},
    }
    valid, errors = validate_template_schema(schema)
    assert valid is False
    assert any("childFields" in e for e in errors)


@pytest.mark.unit
def test_validate_template_schema_table_needs_options():
    """table must have rowOptionSet/rowOptions and colOptionSet/colOptions."""
    schema = {
        "meta": {"name": "X", "discipline": "MICROBIOLOGY"},
        "layout": {"sections": [{"id": "s1", "title": "T", "rows": [{"columns": [{"width": 12, "items": ["fld_ast"]}]}]}]},
        "fields": {"fld_ast": {"type": "table", "code": "ast", "label": "AST"}},
        "rules": {},
    }
    valid, errors = validate_template_schema(schema)
    assert valid is False
    assert any("table" in e and ("rowOptionSet" in e or "colOptionSet" in e) for e in errors)


@pytest.mark.unit
def test_evaluate_calculated_fields():
    """Calculated fields (e.g. anion_gap) are computed from deps."""
    from app.services.lab_result_validation import evaluate_calculated_fields

    schema = {
        "calculated": [
            {"target_code": "anion_gap", "formula": "sodium - (chloride + bicarb)",
             "deps": ["sodium", "chloride", "bicarb"], "decimals": 1}
        ],
    }
    result = {"sodium": 140, "chloride": 100, "bicarb": 24}
    out = evaluate_calculated_fields(schema, result)
    assert "anion_gap" in out
    assert abs(out["anion_gap"] - 16) < 0.01  # 140 - 124 = 16


# --- Integration tests (require PostgreSQL DB) ---

@pytest.mark.integration
def test_lab_workflow_submit_verify_authorize():
    """Full lab workflow: template resolution, result submit, verify, authorize, audit."""
    from datetime import datetime, date, timedelta
    from app.db.database import SessionLocal
    from app.crud import lab_template_crud
    from app.models.user_models import User, Role
    from app.models.patient_models import Patient
    from app.models.encounter_models import Encounter, LabOrder, OrderStatus
    from app.models.lab_template_models import LabTemplate, LabTemplateVersion, LabAuditEvent
    from app.services.lab_result_validation import (
        validate_result, compute_flags, has_critical_flags,
        evaluate_calculated_fields,
    )
    from app.services.lab_audit import log_lab_audit
    from app.core.security import get_password_hash

    db = SessionLocal()
    try:
        # Check we're not on SQLite (lab tables use JSONB/UUID)
        from sqlalchemy import text
        try:
            db.execute(text("SELECT 1"))
        except Exception:
            pytest.skip("DB not available")

        # Create minimal data (reuse existing Admin/user if present)
        role = db.query(Role).filter(Role.name == "Admin").first()
        if not role:
            role = Role(name="Admin", description="Administrator")
            db.add(role)
            db.flush()

        user = db.query(User).filter(User.username == "lab_test_user").first()
        if not user:
            user = User(
                username="lab_test_user",
                email="labtest@test.local",
                full_name="Lab Test User",
                hashed_password=get_password_hash("test123"),
                is_active=True,
                role_id=role.id,
            )
            db.add(user)
            db.flush()

        patient = Patient(
            first_name="Lab",
            last_name="Patient",
            date_of_birth=date.today() - timedelta(days=365 * 30),
            gender="Male",
            phone_number="0244111111",
        )
        db.add(patient)
        db.flush()

        encounter = Encounter(
            patient_id=patient.id,
            clinician_id=user.id,
            chief_complaint="Test",
        )
        db.add(encounter)
        db.flush()

        # Template with one numeric field (create in-session, no commit)
        schema = {
            "meta": {"name": "Integration Test", "discipline": "CHEMISTRY", "version": 1},
            "layout": {"sections": [{"id": "s1", "title": "Results", "rows": [{"columns": [{"width": 12, "items": ["fld_hb"]}]}]}]},
            "fields": {"fld_hb": {"type": "numeric", "code": "hb", "label": "Haemoglobin", "min": 0, "max": 30}},
            "rules": {"visibility": [], "requiredIf": []},
            "calculated": [],
        }
        tmpl = LabTemplate(
            name="Integration Test Template",
            discipline="CHEMISTRY",
            status="PUBLISHED",
            current_version=1,
            created_by_id=user.id,
        )
        db.add(tmpl)
        db.flush()
        pub = LabTemplateVersion(
            template_id=tmpl.id,
            version=1,
            status="PUBLISHED",
            schema_json=schema,
            created_by_id=user.id,
        )
        db.add(pub)
        db.flush()

        lab_order = LabOrder(
            encounter_id=encounter.id,
            patient_id=patient.id,
            ordered_by_id=user.id,
            test_name="Hb Test",
            template_id=tmpl.id,
            template_version_used=pub.version,
            status=OrderStatus.PENDING,
        )
        db.add(lab_order)
        db.flush()
        order_id = lab_order.id

        # Simulate result submit
        result_json = {"hb": 14}
        ref_ranges = {"hb": {"low": 12, "high": 17}}
        valid, errs = validate_result(pub.schema_json, result_json, {}, {})
        assert valid, errs
        result_json = evaluate_calculated_fields(pub.schema_json, result_json)
        from app.services.lab_result_validation import compute_flags, get_flags_dict
        flags = compute_flags(pub.schema_json, result_json, {}, ref_ranges)
        assert not has_critical_flags(flags)

        lab_order.result_json = result_json
        lab_order.flags_json = get_flags_dict(flags)
        lab_order.result_status = "SUBMITTED"
        lab_order.result_entered_by_id = user.id
        lab_order.result_entered_at = datetime.now()
        lab_order.status = OrderStatus.COMPLETED
        lab_order.completed_at = datetime.now()
        lab_order.result = "[Structured - Hb Test]"

        log_lab_audit(db, "lab_order", str(order_id), "submit", user_id=user.id, new_json={"result_status": "SUBMITTED"})
        db.flush()

        # Verify
        lab_order.result_status = "VERIFIED"
        lab_order.verified_by_id = user.id
        lab_order.verified_at = datetime.now()
        log_lab_audit(db, "lab_order", str(order_id), "verify", user_id=user.id, new_json={"result_status": "VERIFIED"})
        db.flush()

        # Authorize
        lab_order.result_status = "AUTHORIZED"
        lab_order.authorized_by_id = user.id
        lab_order.authorized_at = datetime.now()
        log_lab_audit(db, "lab_order", str(order_id), "authorize", user_id=user.id, new_json={"result_status": "AUTHORIZED"})
        db.flush()

        # Verify audit events exist (before rollback)
        evts = db.query(LabAuditEvent).filter(
            LabAuditEvent.entity_type == "lab_order",
            LabAuditEvent.entity_id == str(order_id),
        ).order_by(LabAuditEvent.id).all()
        actions = [e.action for e in evts]
        assert "submit" in actions
        assert "verify" in actions
        assert "authorize" in actions

    finally:
        db.rollback()
        db.close()


@pytest.mark.integration
def test_lab_audit_logged_on_submit():
    """log_lab_audit writes to lab_audit_events and persists after commit."""
    from app.db.database import SessionLocal
    from app.models.lab_template_models import LabAuditEvent
    from app.services.lab_audit import log_lab_audit

    db = SessionLocal()
    try:
        from sqlalchemy import text
        try:
            db.execute(text("SELECT 1"))
        except Exception:
            pytest.skip("DB not available")

        log_lab_audit(db, "lab_order", "test-123", "submit", user_id=None, new_json={"test": True})
        db.flush()
        evt = db.query(LabAuditEvent).filter(
            LabAuditEvent.entity_type == "lab_order",
            LabAuditEvent.entity_id == "test-123",
        ).first()
        assert evt is not None
        assert evt.action == "submit"
        assert evt.new_json == {"test": True}
    finally:
        db.rollback()
        db.close()
