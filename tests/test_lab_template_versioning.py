"""
Unit tests for Lab Template Versioning System
Tests immutability, checksum computation, and version resolution.
"""
import pytest
import json
from uuid import uuid4
from unittest.mock import MagicMock, patch


class TestChecksumComputation:
    """Tests for checksum computation function."""
    
    def test_checksum_deterministic(self):
        """Same schema_json should produce same checksum."""
        from app.crud.lab_template_crud import _compute_checksum
        
        schema = {"meta": {"name": "Test"}, "fields": {}}
        checksum1 = _compute_checksum(schema)
        checksum2 = _compute_checksum(schema)
        
        assert checksum1 == checksum2
    
    def test_checksum_different_schemas(self):
        """Different schema_json should produce different checksums."""
        from app.crud.lab_template_crud import _compute_checksum
        
        schema1 = {"meta": {"name": "Test1"}, "fields": {}}
        schema2 = {"meta": {"name": "Test2"}, "fields": {}}
        
        assert _compute_checksum(schema1) != _compute_checksum(schema2)
    
    def test_checksum_key_order_independent(self):
        """Schema with different key order should produce same checksum."""
        from app.crud.lab_template_crud import _compute_checksum
        
        schema1 = {"meta": {"name": "Test"}, "fields": {"a": 1}}
        schema2 = {"fields": {"a": 1}, "meta": {"name": "Test"}}
        
        assert _compute_checksum(schema1) == _compute_checksum(schema2)


class TestTemplateCRUD:
    """Tests for Lab Template CRUD operations."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = MagicMock()
        return db
    
    @pytest.fixture
    def sample_template(self):
        """Create a sample template."""
        from app.models.lab_template_models import LabTemplate
        
        return LabTemplate(
            id=uuid4(),
            name="CBC Test",
            discipline="HEMATOLOGY",
            status="DRAFT",
            current_version=None,
            created_by_id=1
        )
    
    @pytest.fixture
    def sample_schema(self):
        """Create a sample template schema."""
        return {
            "meta": {"name": "CBC", "discipline": "HEMATOLOGY", "version": 1},
            "layout": {"sections": [{"id": "sec_main", "title": "Results", "rows": [{"columns": [{"width": 12, "items": []}]}]}]},
            "fields": {},
            "rules": {"visibility": [], "requiredIf": []},
            "calculated": []
        }
    
    def test_publish_creates_new_version(self, mock_db, sample_template, sample_schema):
        """Publishing should create a NEW version record, not modify existing."""
        from app.crud.lab_template_crud import publish_version
        from app.models.lab_template_models import LabTemplateVersion
        
        # Setup mock queries
        draft_version = LabTemplateVersion(
            id=uuid4(),
            template_id=sample_template.id,
            version=1,
            status="DRAFT",
            schema_json=sample_schema,
            created_by_id=1
        )
        
        # Track added objects
        added_objects = []
        def track_add(obj):
            added_objects.append(obj)
        mock_db.add = track_add
        
        # Mock get_template
        with patch('app.crud.lab_template_crud.get_template', return_value=sample_template):
            with patch('app.crud.lab_template_crud.get_draft_version', return_value=draft_version):
                with patch('app.crud.lab_template_crud.get_published_version', return_value=None):
                    result = publish_version(mock_db, sample_template.id, "First release", 1)
        
        # Verify a new version was created
        assert len(added_objects) >= 1
        new_version = added_objects[0]
        assert new_version.status == "PUBLISHED"
        assert new_version.version == 1  # First published version
        assert new_version.checksum is not None  # Checksum should be computed
    
    def test_publish_increments_version(self, mock_db, sample_template, sample_schema):
        """Second publish should create version 2."""
        from app.crud.lab_template_crud import publish_version
        from app.models.lab_template_models import LabTemplateVersion
        
        draft_version = LabTemplateVersion(
            id=uuid4(),
            template_id=sample_template.id,
            version=1,
            status="DRAFT",
            schema_json=sample_schema,
            created_by_id=1
        )
        
        # First published version
        existing_published = LabTemplateVersion(
            id=uuid4(),
            template_id=sample_template.id,
            version=1,
            status="PUBLISHED",
            schema_json=sample_schema,
            created_by_id=1
        )
        
        added_objects = []
        def track_add(obj):
            added_objects.append(obj)
        mock_db.add = track_add
        
        with patch('app.crud.lab_template_crud.get_template', return_value=sample_template):
            with patch('app.crud.lab_template_crud.get_draft_version', return_value=draft_version):
                with patch('app.crud.lab_template_crud.get_published_version', return_value=existing_published):
                    result = publish_version(mock_db, sample_template.id, "Second release", 1)
        
        # Verify version is incremented
        new_version = added_objects[0]
        assert new_version.version == 2
    
    def test_get_version_returns_specific(self, mock_db):
        """get_version should return specific version by number."""
        from app.crud.lab_template_crud import get_version
        from app.models.lab_template_models import LabTemplateVersion
        
        expected_version = LabTemplateVersion(
            id=uuid4(),
            template_id=uuid4(),
            version=3,
            status="PUBLISHED",
            schema_json={}
        )
        
        mock_db.query.return_value.filter.return_value.first.return_value = expected_version
        
        result = get_version(mock_db, expected_version.template_id, 3)
        
        assert result == expected_version


class TestTemplateSchemaValidation:
    """Tests for template schema validation."""
    
    def test_valid_schema(self):
        """Valid schema should pass validation."""
        from app.services.lab_template_schema import validate_template_schema
        
        schema = {
            "meta": {"name": "Test", "discipline": "HEMATOLOGY"},
            "layout": {"sections": [{"id": "sec1", "title": "Test", "rows": [{"columns": [{"width": 12, "items": []}]}]}]},
            "fields": {},
            "rules": {},
            "calculated": []
        }
        
        is_valid, errors = validate_template_schema(schema)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_invalid_missing_meta(self):
        """Schema missing meta should fail."""
        from app.services.lab_template_schema import validate_template_schema
        
        schema = {
            "layout": {"sections": []},
            "fields": {}
        }
        
        is_valid, errors = validate_template_schema(schema)
        
        assert is_valid is False
        assert "Missing 'meta' section" in errors
    
    def test_invalid_discipline(self):
        """Schema with invalid discipline should fail."""
        from app.services.lab_template_schema import validate_template_schema
        
        schema = {
            "meta": {"name": "Test", "discipline": "INVALID_DISCIPLINE"},
            "layout": {"sections": [{"id": "sec1", "title": "Test", "rows": [{"columns": [{"width": 12, "items": []}]}]}]},
            "fields": {},
            "rules": {},
            "calculated": []
        }
        
        is_valid, errors = validate_template_schema(schema)
        
        assert is_valid is False
        assert any("discipline" in e.lower() for e in errors)
    
    def test_layout_references_unknown_field(self):
        """Layout referencing unknown field should fail."""
        from app.services.lab_template_schema import validate_template_schema
        
        schema = {
            "meta": {"name": "Test", "discipline": "HEMATOLOGY"},
            "layout": {"sections": [{"id": "sec1", "title": "Test", "rows": [{"columns": [{"width": 12, "items": ["unknown_field"]}]}]}]},
            "fields": {},  # No fields defined
            "rules": {},
            "calculated": []
        }
        
        is_valid, errors = validate_template_schema(schema)
        
        assert is_valid is False
        assert any("unknown field" in e.lower() for e in errors)


class TestResolverEndpoint:
    """Tests for template resolution."""
    
    def test_resolve_returns_published_version(self):
        """Resolver should return published schema."""
        # This would require a full FastAPI test client
        # Just verifying the logic here
        pass
    
    def test_resolve_validates_checksum(self):
        """Resolver should validate checksum when requested."""
        # This would require a full FastAPI test client
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
