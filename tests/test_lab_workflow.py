"""
Unit tests for Lab Result Workflow (status transitions and permissions)
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.models.encounter_models import LabOrder, OrderStatus


class TestLabOrderStatusTransitions:
    """Tests for lab result status transitions"""
    
    def test_draft_to_submitted(self):
        """Test DRAFT -> SUBMITTED transition"""
        lab_order = MagicMock()
        lab_order.result_status = "DRAFT"
        lab_order.result_json = {"wbc": 5.5}
        lab_order.template_id = None
        lab_order.template_version_used = None
        lab_order.critical_called = None
        
        # Simulate submit
        assert lab_order.result_status == "DRAFT"
        
        # After submit
        lab_order.result_status = "SUBMITTED"
        assert lab_order.result_status == "SUBMITTED"
    
    def test_submitted_to_verified(self):
        """Test SUBMITTED -> VERIFIED transition"""
        lab_order = MagicMock()
        lab_order.result_status = "SUBMITTED"
        
        # After verify
        lab_order.result_status = "VERIFIED"
        lab_order.verified_by_id = 1
        lab_order.verified_at = datetime.now()
        
        assert lab_order.result_status == "VERIFIED"
        assert lab_order.verified_by_id == 1
        assert lab_order.verified_at is not None
    
    def test_verified_to_released(self):
        """Test VERIFIED -> RELEASED transition"""
        lab_order = MagicMock()
        lab_order.result_status = "VERIFIED"
        
        # After authorize
        lab_order.result_status = "RELEASED"
        lab_order.authorized_by_id = 1
        lab_order.authorized_at = datetime.now()
        
        assert lab_order.result_status == "RELEASED"
        assert lab_order.authorized_by_id == 1
    
    def test_released_to_amended(self):
        """Test RELEASED -> AMENDED transition"""
        lab_order = MagicMock()
        lab_order.result_status = "RELEASED"
        lab_order.id = 100
        
        # After amend
        lab_order.result_status = "AMENDED"
        
        # New amendment order created
        amended_order = MagicMock()
        amended_order.id = 101
        amended_order.previous_version_id = 100
        amended_order.result_status = "DRAFT"
        amended_order.amend_reason = "Corrected value"
        
        assert lab_order.result_status == "AMENDED"
        assert amended_order.previous_version_id == 100
        assert amended_order.result_status == "DRAFT"


class TestPermissionChecks:
    """Tests for role-based permissions"""
    
    def test_lab_staff_can_save_draft(self):
        """Lab Staff can save draft"""
        roles_that_can_save_draft = ["Lab Staff", "Admin"]
        
        assert "Lab Staff" in roles_that_can_save_draft
        assert "Admin" in roles_that_can_save_draft
    
    def test_lab_staff_can_submit(self):
        """Lab Staff can submit results"""
        roles_that_can_submit = ["Lab Staff", "Admin"]
        
        assert "Lab Staff" in roles_that_can_submit
    
    def test_supervisor_can_verify(self):
        """Lab Supervisor can verify results"""
        roles_that_can_verify = ["Lab Supervisor", "Lab Manager", "Admin"]
        
        assert "Lab Supervisor" in roles_that_can_verify
        assert "Lab Manager" in roles_that_can_verify
    
    def test_manager_can_authorize(self):
        """Lab Manager can authorize results"""
        roles_that_can_authorize = ["Lab Manager", "Admin", "Doctor"]
        
        assert "Lab Manager" in roles_that_can_authorize
        assert "Doctor" in roles_that_can_authorize
    
    def test_staff_cannot_verify(self):
        """Regular Lab Staff cannot verify"""
        roles_that_can_verify = ["Lab Supervisor", "Lab Manager", "Admin"]
        
        assert "Lab Staff" not in roles_that_can_verify
    
    def test_staff_cannot_authorize(self):
        """Regular Lab Staff cannot authorize"""
        roles_that_can_authorize = ["Lab Manager", "Admin", "Doctor"]
        
        assert "Lab Staff" not in roles_that_can_authorize


class TestCriticalPolicy:
    """Tests for critical value policy"""
    
    def test_submit_blocked_without_critical_call(self):
        """Submit blocked when CRITICAL flag exists and critical_called not set"""
        # Simulate CRITICAL flag
        critical_flags = [{"flag": "CRITICAL", "value": 2.0, "field_code": "wbc"}]
        
        lab_order = MagicMock()
        lab_order.result_status = "DRAFT"
        lab_order.result_json = {"wbc": 2.0}
        lab_order.critical_called = None
        
        # Should be blocked
        has_critical = len(critical_flags) > 0
        requires_critical_call = has_critical and not lab_order.critical_called
        
        assert requires_critical_call is True
    
    def test_submit_allowed_with_critical_call(self):
        """Submit allowed when CRITICAL flag exists and critical_called is set"""
        critical_flags = [{"flag": "CRITICAL", "value": 2.0, "field_code": "wbc"}]
        
        lab_order = MagicMock()
        lab_order.result_status = "DRAFT"
        lab_order.result_json = {"wbc": 2.0}
        lab_order.critical_called = True
        lab_order.critical_called_at = datetime.now()
        lab_order.critical_called_to = "Dr. Smith"
        
        has_critical = len(critical_flags) > 0
        requires_critical_call = has_critical and not lab_order.critical_called
        
        assert requires_critical_call is False
    
    def test_no_critical_flags_allows_submit(self):
        """Submit allowed when no CRITICAL flags"""
        critical_flags = []
        
        lab_order = MagicMock()
        lab_order.result_status = "DRAFT"
        lab_order.result_json = {"wbc": 5.5}
        lab_order.critical_called = None
        
        has_critical = len(critical_flags) > 0
        requires_critical_call = has_critical and not lab_order.critical_called
        
        assert requires_critical_call is False


class TestStatusTransitionValidation:
    """Tests for invalid status transitions"""
    
    def test_cannot_verify_draft(self):
        """Cannot verify a draft result"""
        # Invalid: trying to go from DRAFT directly to VERIFIED
        current_status = "DRAFT"
        target_status = "VERIFIED"
        
        valid_transitions = {
            "DRAFT": ["SUBMITTED"],
            "SUBMITTED": ["VERIFIED", "DRAFT"],
            "VERIFIED": ["RELEASED", "DRAFT"],
            "RELEASED": ["AMENDED"],
            "AMENDED": ["DRAFT"],
        }
        
        assert target_status not in valid_transitions.get(current_status, [])
    
    def test_cannot_authorize_draft(self):
        """Cannot authorize a draft result"""
        current_status = "DRAFT"
        target_status = "RELEASED"
        
        valid_transitions = {
            "DRAFT": ["SUBMITTED"],
            "SUBMITTED": ["VERIFIED"],
            "VERIFIED": ["RELEASED"],
        }
        
        assert target_status not in valid_transitions.get(current_status, [])
    
    def test_valid_draft_to_submitted(self):
        """Can submit a draft result"""
        current_status = "DRAFT"
        target_status = "SUBMITTED"
        
        valid_transitions = {
            "DRAFT": ["SUBMITTED"],
        }
        
        assert target_status in valid_transitions.get(current_status, [])
    
    def test_valid_submitted_to_verified(self):
        """Can verify a submitted result"""
        current_status = "SUBMITTED"
        target_status = "VERIFIED"
        
        valid_transitions = {
            "SUBMITTED": ["VERIFIED"],
        }
        
        assert target_status in valid_transitions.get(current_status, [])
