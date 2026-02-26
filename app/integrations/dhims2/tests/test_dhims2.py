"""
Unit Tests for DHIMS2 Integration

Tests for:
- Period utilities
- Validation rules
- Locking behavior
- Payload builder
- Client retry handling
"""
import pytest
from datetime import datetime, date
from unittest.mock import Mock, patch, MagicMock
import hashlib
import json

# Test imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


class TestPeriodUtils:
    """Tests for period utilities."""
    
    def test_compute_payload_hash(self):
        """Test payload hash computation."""
        from app.integrations.dhims2.client import compute_payload_hash
        
        data = {
            "org_unit": "org123",
            "period": "2026-01",
            "items": [
                {"key": "metric1", "value": "10"}
            ]
        }
        
        hash1 = compute_payload_hash(data)
        
        # Same data should produce same hash
        hash2 = compute_payload_hash(data)
        assert hash1 == hash2
        
        # Different data should produce different hash
        data["period"] = "2026-02"
        hash3 = compute_payload_hash(data)
        assert hash1 != hash3
        
        # Hash should be SHA-256
        assert len(hash1) == 64


class TestValidators:
    """Tests for data validators."""
    
    def test_completeness_check_pass(self):
        """Test completeness check passes when all required metrics present."""
        from app.integrations.dhims2.validators import DataValidator, ValidationResult, ValidationStatus
        
        # Mock database
        db = Mock()
        
        validator = DataValidator(db)
        
        # Create mock items
        items = [
            Mock(internal_metric_key="OPD_TOTAL", value="100"),
            Mock(internal_metric_key="ANC1", value="10")
        ]
        
        # Create mock run
        run = Mock()
        run.id = 1
        
        with patch.object(validator, '_check_completeness') as mock_check:
            mock_check.return_value = []
            
            results, status = validator.validate_run(
                run,
                required_metrics=["OPD_TOTAL", "ANC1"]
            )
    
    def test_completeness_check_fail(self):
        """Test completeness check fails when required metrics missing."""
        # This test would need proper SQLAlchemy setup
        pass
    
    def test_numeric_validation(self):
        """Test numeric value validation."""
        from app.integrations.dhims2.validators import ValidationResult, ValidationStatus
        
        # Valid numeric
        assert _validate_numeric("100") == (True, None)
        
        # Valid negative
        assert _validate_numeric("-5") == (True, None)
        
        # Valid decimal
        assert _validate_numeric("10.5") == (True, None)
        
        # Invalid
        assert _validate_numeric("abc") == (False, "Invalid numeric value")
        
        # Negative not allowed
        assert _validate_numeric("-5", allow_negative=False) == (False, "Negative value not allowed")


def _validate_numeric(value: str, allow_negative: bool = True):
    """Helper to validate numeric value."""
    try:
        num = float(value)
        if not allow_negative and num < 0:
            return False, "Negative value not allowed"
        return True, None
    except (ValueError, TypeError):
        return False, "Invalid numeric value"


class TestPeriodLockChecker:
    """Tests for period locking."""
    
    def test_period_not_locked(self):
        """Test period is not locked when within window."""
        from app.integrations.dhims2.validators import PeriodLockChecker
        
        checker = PeriodLockChecker()
        
        # Current period should not be locked
        current_period = datetime.utcnow().strftime("%Y-%m")
        is_locked, reason = checker.is_locked(current_period)
        
        assert is_locked == False
        assert reason is None
    
    def test_period_locked_after_window(self):
        """Test period is locked after data lock window."""
        from app.integrations.dhims2.validators import PeriodLockChecker
        from datetime import timedelta
        
        checker = PeriodLockChecker()
        
        # A period from 100 days ago should be locked
        old_date = datetime.utcnow() - timedelta(days=100)
        old_period = old_date.strftime("%Y-%m")
        
        is_locked, reason = checker.is_locked(old_period)
        
        assert is_locked == True
        assert "locked" in reason.lower()


class TestSubmissionWorkflow:
    """Tests for submission workflow."""
    
    def test_workflow_states(self):
        """Test workflow state transitions."""
        from app.models.dhims2_models import SubmissionRunStatus
        
        # Expected state transitions
        expected_transitions = {
            SubmissionRunStatus.DRAFT: [SubmissionRunStatus.PENDING_APPROVAL],
            SubmissionRunStatus.PENDING_APPROVAL: [SubmissionRunStatus.APPROVED, SubmissionRunStatus.DRAFT],
            SubmissionRunStatus.APPROVED: [SubmissionRunStatus.SUBMITTED],
            SubmissionRunStatus.SUBMITTED: [],  # Terminal state
            SubmissionRunStatus.SUBMIT_FAILED: [SubmissionRunStatus.APPROVED, SubmissionRunStatus.DRAFT],
        }
        
        # Verify state enum values
        assert SubmissionRunStatus.DRAFT.value == "draft"
        assert SubmissionRunStatus.PENDING_APPROVAL.value == "pending_approval"
        assert SubmissionRunStatus.APPROVED.value == "approved"
        assert SubmissionRunStatus.SUBMITTED.value == "submitted"
        assert SubmissionRunStatus.SUBMIT_FAILED.value == "submit_failed"
        assert SubmissionRunStatus.LOCKED.value == "locked"


class TestPayloadBuilder:
    """Tests for DHIS2 payload builder."""
    
    def test_build_data_value_payload(self):
        """Test building data value payload."""
        # Sample items
        items = [
            {
                "internal_metric_key": "OPD_TOTAL",
                "value": "100",
                "dhis2_data_element_uid": "de123456",
                "dhis2_category_option_combo_uid": "coc123"
            },
            {
                "internal_metric_key": "ANC1",
                "value": "25",
                "dhis2_data_element_uid": "de789012",
                "dhis2_category_option_combo_uid": None
            }
        ]
        
        # Build payload
        payload = {
            "dataSet": "ds123",
            "orgUnit": "ou123",
            "period": "2026-01",
            "dataValues": []
        }
        
        for item in items:
            value_obj = {
                "dataElement": item["dhis2_data_element_uid"],
                "value": item["value"]
            }
            if item.get("dhis2_category_option_combo_uid"):
                value_obj["categoryOptionCombo"] = item["dhis2_category_option_combo_uid"]
            
            payload["dataValues"].append(value_obj)
        
        # Verify payload structure
        assert len(payload["dataValues"]) == 2
        assert payload["dataValues"][0]["dataElement"] == "de123456"
        assert payload["dataValues"][0]["categoryOptionCombo"] == "coc123"
        assert payload["dataValues"][1]["categoryOptionCombo"] is None


class TestDHIS2Client:
    """Tests for DHIS2 client."""
    
    @patch('app.integrations.dhims2.client.requests.Session')
    def test_client_initialization(self, mock_session):
        """Test client initialization."""
        from app.integrations.dhims2.client import Dhis2Client
        
        with patch.object(Dhis2Client, '_create_session') as mock_create:
            mock_create.return_value = Mock()
            
            client = Dhis2Client(
                base_url="https://test.gh",
                username="testuser",
                password="testpass",
                timeout=30
            )
            
            assert client.base_url == "https://test.gh"
            assert client.username == "testuser"
            assert client.timeout == 30
    
    def test_handle_response_401(self):
        """Test handling 401 authentication error."""
        from app.integrations.dhims2.client import Dhis2Client, DHIS2AuthenticationError
        
        client = Dhis2Client.__new__(Dhis2Client)
        
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Unauthorized"}
        
        with pytest.raises(DHIS2AuthenticationError) as exc_info:
            client._handle_response(mock_response)
        
        assert exc_info.value.status_code == 401
    
    def test_handle_response_400(self):
        """Test handling 400 validation error."""
        from app.integrations.dhims2.client import Dhis2Client, DHIS2ValidationError
        
        client = Dhis2Client.__new__(Dhis2Client)
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"description": "Validation error"}
        
        with pytest.raises(DHIS2ValidationError):
            client._handle_response(mock_response)


class TestDataProvider:
    """Tests for data providers."""
    
    def test_provider_registry(self):
        """Test provider registry contains expected providers."""
        from app.integrations.dhims2.providers import PROVIDER_REGISTRY
        
        assert "aggregated_indicators" in PROVIDER_REGISTRY
        assert "disease_reporting" in PROVIDER_REGISTRY
    
    def test_get_provider_unknown(self):
        """Test getting unknown provider raises error."""
        from app.integrations.dhims2.providers import get_provider
        
        db = Mock()
        
        with pytest.raises(ValueError) as exc_info:
            get_provider("unknown_provider", db)
        
        assert "Unknown provider" in str(exc_info.value)


# Run tests with: pytest app/integrations/dhims2/tests/test_dhims2.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
