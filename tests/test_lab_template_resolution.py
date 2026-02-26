"""
Unit tests for Lab Template Resolution Service

Tests:
1. Creating result bundle with template_version_used (stable results)
2. Resolver logic stability - uses persisted version when available
3. Resolution from catalog when not set
4. Latest published version fallback
"""
import pytest
import uuid
from unittest.mock import MagicMock, patch

from app.services.lab_template_resolution import (
    resolve_template_for_order,
    get_template_version_schema,
    is_template_locked,
    TemplateResolutionError,
    ResolvedTemplate
)


class TestResolveTemplateForOrder:
    """Tests for resolve_template_for_order function."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = MagicMock()
        return db
    
    @pytest.fixture
    def sample_template_id(self):
        """Sample template UUID."""
        return uuid.uuid4()
    
    @pytest.fixture
    def sample_lab_test_id(self):
        """Sample lab test UUID (integer)."""
        return 1
    
    def test_uses_persisted_template_version(self, mock_db, sample_template_id):
        """When LabOrder has template_version_used, it should be used (stable results)."""
        # Create LabOrder with already persisted template info
        lab_order = MagicMock()
        lab_order.id = 100
        lab_order.template_id = sample_template_id
        lab_order.template_version_used = 1
        lab_order.lab_test_id = None  # Not needed when template is already set
        lab_order.result_status = None
        
        # Create mock version
        mock_version = MagicMock()
        mock_version.schema_json = {"meta": {"name": "CBC"}, "fields": {}}
        
        # Setup mock query
        mock_db.query.return_value.filter.return_value.first.return_value = mock_version
        
        # Resolve
        result = resolve_template_for_order(mock_db, lab_order, persist=False)
        
        # Verify it uses persisted version
        assert result.template_id == sample_template_id
        assert result.template_version == 1
        assert result.is_persisted is True
        assert result.is_from_catalog is False
        assert result.schema_json == {"meta": {"name": "CBC"}, "fields": {}}
    
    def test_resolves_from_catalog_with_specific_version(self, mock_db, sample_template_id):
        """When no persisted version, resolves from LabTest with specific template_version."""
        # Create LabOrder without template info
        lab_order = MagicMock()
        lab_order.id = 100
        lab_order.template_id = None  # Not set
        lab_order.template_version_used = None  # Not set
        lab_order.lab_test_id = 1
        lab_order.result_status = None
        
        # Create mock LabTest
        mock_lab_test = MagicMock()
        mock_lab_test.id = 1
        mock_lab_test.template_id = sample_template_id
        mock_lab_test.template_version = 2  # Specific version
        
        # Create mock template
        mock_template = MagicMock()
        mock_template.id = sample_template_id
        mock_template.current_version = 5  # Latest is 5, but we want version 2
        
        # Create mock version
        mock_version = MagicMock()
        mock_version.schema_json = {"meta": {"name": "CBC v2"}, "fields": {}}
        
        # Track queries - return appropriate mocks based on what's being queried
        def query_side_effect(model):
            mock_query = MagicMock()
            if model.__name__ == 'LabTest':
                mock_query.filter.return_value.first.return_value = mock_lab_test
            elif model.__name__ == 'LabTemplate':
                mock_query.filter.return_value.first.return_value = mock_template
            elif model.__name__ == 'LabTemplateVersion':
                mock_query.filter.return_value.first.return_value = mock_version
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        # Resolve
        result = resolve_template_for_order(mock_db, lab_order, persist=True)
        
        # Verify it resolved from catalog with specific version
        assert result.template_id == sample_template_id
        assert result.template_version == 2  # Uses specific version from catalog
        assert result.is_persisted is True
        assert result.is_from_catalog is True
    
    def test_resolves_latest_published_version(self, mock_db, sample_template_id):
        """When LabTest has no template_version, uses latest published."""
        # Create LabOrder without template info
        lab_order = MagicMock()
        lab_order.id = 100
        lab_order.template_id = None
        lab_order.template_version_used = None
        lab_order.lab_test_id = 1
        lab_order.result_status = None
        
        # Create mock LabTest with no specific version
        mock_lab_test = MagicMock()
        mock_lab_test.id = 1
        mock_lab_test.template_id = sample_template_id
        mock_lab_test.template_version = None  # No specific version - use latest
        
        # Create mock template
        mock_template = MagicMock()
        mock_template.id = sample_template_id
        mock_template.current_version = 3  # Latest published version
        
        # Create mock version
        mock_version = MagicMock()
        mock_version.schema_json = {"meta": {"name": "CBC v3"}, "fields": {}}
        
        # Track queries
        def query_side_effect(model):
            mock_query = MagicMock()
            if model.__name__ == 'LabTest':
                mock_query.filter.return_value.first.return_value = mock_lab_test
            elif model.__name__ == 'LabTemplate':
                mock_query.filter.return_value.first.return_value = mock_template
            elif model.__name__ == 'LabTemplateVersion':
                mock_query.filter.return_value.first.return_value = mock_version
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        # Resolve
        result = resolve_template_for_order(mock_db, lab_order, persist=True)
        
        # Verify it uses latest published version
        assert result.template_id == sample_template_id
        assert result.template_version == 3  # Uses latest from template.current_version
        assert result.is_from_catalog is True
    
    def test_raises_error_when_no_lab_test(self, mock_db):
        """Raises error when LabOrder has no lab_test_id and no template_id."""
        lab_order = MagicMock()
        lab_order.id = 100
        lab_order.template_id = None
        lab_order.template_version_used = None
        lab_order.lab_test_id = None
        
        with pytest.raises(TemplateResolutionError) as exc_info:
            resolve_template_for_order(mock_db, lab_order)
        
        assert "no lab_test_id and no template_id" in str(exc_info.value)
    
    def test_raises_error_when_catalog_has_no_template(self, mock_db):
        """Raises error when LabTest has no template_id configured."""
        lab_order = MagicMock()
        lab_order.id = 100
        lab_order.template_id = None
        lab_order.template_version_used = None
        lab_order.lab_test_id = 1
        
        mock_lab_test = MagicMock()
        mock_lab_test.id = 1
        mock_lab_test.template_id = None  # No template configured
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_lab_test
        
        with pytest.raises(TemplateResolutionError) as exc_info:
            resolve_template_for_order(mock_db, lab_order)
        
        assert "no template_id configured" in str(exc_info.value)


class TestGetTemplateVersionSchema:
    """Tests for get_template_version_schema function."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = MagicMock()
        return db
    
    def test_get_specific_version(self, mock_db):
        """Get schema for a specific version."""
        template_id = uuid.uuid4()
        
        mock_version = MagicMock()
        mock_version.schema_json = {"meta": {"name": "Test"}}
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_version
        
        schema, version = get_template_version_schema(mock_db, template_id, version=2)
        
        assert schema == {"meta": {"name": "Test"}}
        assert version == 2
    
    def test_get_latest_published_version(self, mock_db):
        """Get schema for latest published version when version is None."""
        template_id = uuid.uuid4()
        
        mock_template = MagicMock()
        mock_template.current_version = 5
        
        mock_version = MagicMock()
        mock_version.schema_json = {"meta": {"name": "Test v5"}}
        
        # First query for template, then for version
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_template,  # First call: get template
            mock_version    # Second call: get version
        ]
        
        schema, version = get_template_version_schema(mock_db, template_id, version=None)
        
        assert schema == {"meta": {"name": "Test v5"}}
        assert version == 5


class TestIsTemplateLocked:
    """Tests for is_template_locked function."""
    
    def test_not_locked_when_no_status(self):
        """Not locked when result_status is None."""
        lab_order = MagicMock()
        lab_order.result_status = None
        
        assert is_template_locked(lab_order) is False
    
    def test_not_locked_when_draft(self):
        """Not locked when result_status is DRAFT."""
        lab_order = MagicMock()
        lab_order.result_status = "DRAFT"
        
        assert is_template_locked(lab_order) is False
    
    def test_locked_when_submitted(self):
        """Locked when result_status is SUBMITTED."""
        lab_order = MagicMock()
        lab_order.result_status = "SUBMITTED"
        
        assert is_template_locked(lab_order) is True
    
    def test_locked_when_verified(self):
        """Locked when result_status is VERIFIED."""
        lab_order = MagicMock()
        lab_order.result_status = "VERIFIED"
        
        assert is_template_locked(lab_order) is True
    
    def test_locked_when_authorized(self):
        """Locked when result_status is AUTHORIZED."""
        lab_order = MagicMock()
        lab_order.result_status = "AUTHORIZED"
        
        assert is_template_locked(lab_order) is True
    
    def test_locked_when_released(self):
        """Locked when result_status is RELEASED."""
        lab_order = MagicMock()
        lab_order.result_status = "RELEASED"
        
        assert is_template_locked(lab_order) is True
    
    def test_locked_when_amended(self):
        """Locked when result_status is AMENDED."""
        lab_order = MagicMock()
        lab_order.result_status = "AMENDED"
        
        assert is_template_locked(lab_order) is True


class TestResolvedTemplate:
    """Tests for ResolvedTemplate dataclass."""
    
    def test_dataclass_creation(self):
        """Test ResolvedTemplate can be created with expected values."""
        template_id = uuid.uuid4()
        
        result = ResolvedTemplate(
            template_id=template_id,
            template_version=3,
            schema_json={"meta": {"name": "Test"}},
            is_persisted=True,
            is_from_catalog=False
        )
        
        assert result.template_id == template_id
        assert result.template_version == 3
        assert result.schema_json == {"meta": {"name": "Test"}}
        assert result.is_persisted is True
        assert result.is_from_catalog is False
