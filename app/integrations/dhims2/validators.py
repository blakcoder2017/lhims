"""
Data Validation for DHIMS2 Submissions

Implements Ghana-style data quality checks that run BEFORE submission:
- Completeness: Required metrics present
- Validity: Numeric values, non-negative checks
- Consistency: Cross-check rules (sub-totals <= totals)
- Timeliness: Due date checks
- Duplicate prevention
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from enum import Enum

from app.models.dhims2_models import (
    DHIMS2Mapping,
    DHIMS2SubmissionRun,
    DHIMS2SubmissionItem,
    ValidationStatus,
    SubmissionRunStatus
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of a validation check."""
    def __init__(
        self,
        status: ValidationStatus,
        message: str,
        metric_key: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        self.status = status
        self.message = message
        self.metric_key = metric_key
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "message": self.message,
            "metric_key": self.metric_key,
            **self.details
        }


class DataValidator:
    """
    Data quality validator for DHIMS2 submissions.
    
    Implements Ghana health sector data quality requirements.
    """
    
    def __init__(self, db):
        self.db = db
    
    def validate_run(
        self,
        run: DHIMS2SubmissionRun,
        required_metrics: Optional[List[str]] = None,
        cross_check_rules: Optional[List[Dict]] = None
    ) -> Tuple[List[ValidationResult], ValidationStatus]:
        """
        Validate a submission run.
        
        Args:
            run: The submission run to validate
            required_metrics: List of required metric keys
            cross_check_rules: List of cross-check rule definitions
            
        Returns:
            Tuple of (list of validation results, overall status)
        """
        results: List[ValidationResult] = []
        
        # Load items
        items = self.db.query(DHIMS2SubmissionItem).filter(
            DHIMS2SubmissionItem.run_id == run.id
        ).all()
        
        # Create value lookup
        values: Dict[str, Any] = {}
        for item in items:
            values[item.internal_metric_key] = item.value
        
        # 1. Completeness check
        completeness_results = self._check_completeness(
            values, required_metrics or []
        )
        results.extend(completeness_results)
        
        # 2. Validity checks
        validity_results = self._check_validity(items)
        results.extend(validity_results)
        
        # 3. Consistency checks (cross-checks)
        if cross_check_rules:
            consistency_results = self._check_consistency(values, cross_check_rules)
            results.extend(consistency_results)
        
        # Determine overall status
        overall_status = self._determine_overall_status(results)
        
        return results, overall_status
    
    def _check_completeness(
        self,
        values: Dict[str, str],
        required_metrics: List[str]
    ) -> List[ValidationResult]:
        """Check that all required metrics are present."""
        results = []
        
        for metric_key in required_metrics:
            if metric_key not in values:
                results.append(ValidationResult(
                    status=ValidationStatus.FAIL,
                    message=f"Required metric '{metric_key}' is missing",
                    metric_key=metric_key
                ))
            elif values[metric_key] is None or values[metric_key] == '':
                results.append(ValidationResult(
                    status=ValidationStatus.FAIL,
                    message=f"Required metric '{metric_key}' has no value",
                    metric_key=metric_key
                ))
        
        return results
    
    def _check_validity(
        self,
        items: List[DHIMS2SubmissionItem]
    ) -> List[ValidationResult]:
        """Check value validity (numeric, non-negative)."""
        results = []
        
        for item in items:
            # Get the mapping to check value type
            mapping = self.db.query(DHIMS2Mapping).filter(
                DHIMS2Mapping.internal_metric_key == item.internal_metric_key,
                DHIMS2Mapping.is_active == True
            ).first()
            
            if not mapping:
                continue
            
            value = item.value
            value_type = mapping.value_type or "numeric"
            
            # Numeric validation
            if value_type == "numeric":
                try:
                    num_value = float(value)
                    if num_value < 0:
                        results.append(ValidationResult(
                            status=ValidationStatus.FAIL,
                            message=f"Negative value not allowed for '{item.internal_metric_key}'",
                            metric_key=item.internal_metric_key,
                            details={"value": value}
                        ))
                except (ValueError, TypeError):
                    results.append(ValidationResult(
                        status=ValidationStatus.FAIL,
                        message=f"Invalid numeric value for '{item.internal_metric_key}': '{value}'",
                        metric_key=item.internal_metric_key,
                        details={"value": value}
                    ))
            
            # Boolean validation
            elif value_type == "boolean":
                if value.lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
                    results.append(ValidationResult(
                        status=ValidationStatus.FAIL,
                        message=f"Invalid boolean value for '{item.internal_metric_key}': '{value}'",
                        metric_key=item.internal_metric_key,
                        details={"value": value}
                    ))
        
        return results
    
    def _check_consistency(
        self,
        values: Dict[str, str],
        rules: List[Dict]
    ) -> List[ValidationResult]:
        """
        Check consistency rules (e.g., sub-totals <= totals).
        
        Rules format:
        [
            {
                "rule": "total_ge_parts",
                "total": "OPD_TOTAL",
                "parts": ["OPD_MALE", "OPD_FEMALE"],
                "tolerance": 0  # Optional tolerance for floating point
            }
        ]
        """
        results = []
        
        for rule in rules:
            rule_type = rule.get("rule")
            
            if rule_type == "total_ge_parts":
                results.extend(
                    self._check_total_ge_parts(values, rule)
                )
            elif rule_type == "sum_equals":
                results.extend(
                    self._check_sum_equals(values, rule)
                )
        
        return results
    
    def _check_total_ge_parts(
        self,
        values: Dict[str, str],
        rule: Dict
    ) -> List[ValidationResult]:
        """Check that total >= sum of parts."""
        results = []
        
        total_key = rule.get("total")
        parts = rule.get("parts", [])
        tolerance = rule.get("tolerance", 0)
        
        if total_key not in values:
            return results
        
        try:
            total = float(values[total_key])
        except (ValueError, TypeError):
            return results
        
        parts_sum = 0
        missing_parts = []
        
        for part_key in parts:
            if part_key not in values:
                missing_parts.append(part_key)
                continue
            try:
                parts_sum += float(values[part_key])
            except (ValueError, TypeError):
                pass
        
        if missing_parts:
            results.append(ValidationResult(
                status=ValidationStatus.WARN,
                message=f"Cannot verify total >= parts: missing parts {missing_parts}",
                metric_key=total_key,
                details={"missing_parts": missing_parts}
            ))
        elif total < parts_sum - tolerance:
            results.append(ValidationResult(
                status=ValidationStatus.FAIL,
                message=f"Total ({total}) < sum of parts ({parts_sum})",
                metric_key=total_key,
                details={
                    "total": total,
                    "parts_sum": parts_sum,
                    "parts": parts
                }
            ))
        
        return results
    
    def _check_sum_equals(
        self,
        values: Dict[str, str],
        rule: Dict
    ) -> List[ValidationResult]:
        """Check that sum of values equals expected total."""
        results = []
        
        keys = rule.get("keys", [])
        expected = rule.get("expected")
        tolerance = rule.get("tolerance", 0)
        
        if expected is None:
            return results
        
        try:
            expected_value = float(expected)
        except (ValueError, TypeError):
            return results
        
        actual_sum = 0
        missing_keys = []
        
        for key in keys:
            if key not in values:
                missing_keys.append(key)
                continue
            try:
                actual_sum += float(values[key])
            except (ValueError, TypeError):
                pass
        
        if missing_keys:
            results.append(ValidationResult(
                status=ValidationStatus.WARN,
                message=f"Cannot verify sum: missing keys {missing_keys}",
                details={"missing_keys": missing_keys}
            ))
        elif abs(actual_sum - expected_value) > tolerance:
            results.append(ValidationResult(
                status=ValidationStatus.FAIL,
                message=f"Sum ({actual_sum}) != expected ({expected_value})",
                details={
                    "expected": expected_value,
                    "actual_sum": actual_sum,
                    "keys": keys
                }
            ))
        
        return results
    
    def _determine_overall_status(
        self,
        results: List[ValidationResult]
    ) -> ValidationStatus:
        """Determine overall validation status from individual results."""
        has_fail = any(r.status == ValidationStatus.FAIL for r in results)
        has_warn = any(r.status == ValidationStatus.WARN for r in results)
        
        if has_fail:
            return ValidationStatus.FAIL
        elif has_warn:
            return ValidationStatus.WARN
        else:
            return ValidationStatus.PASS


class PeriodLockChecker:
    """
    Check if a period is locked for editing.
    
    Based on DHIMS2_DATA_LOCK_DAYS configuration.
    """
    
    def __init__(self):
        self.lock_days = settings.DHIMS2_DATA_LOCK_DAYS
    
    def is_locked(
        self,
        period: str,
        submitted_at: Optional[datetime] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if period is locked.
        
        Args:
            period: Period string (e.g., "2026-01")
            submitted_at: When the data was submitted (defaults to now)
            
        Returns:
            Tuple of (is_locked, reason)
        """
        if submitted_at is None:
            submitted_at = datetime.utcnow()
        
        try:
            # Parse period (assuming YYYY-MM format)
            period_date = datetime.strptime(period + "-01", "%Y-%m-%d")
        except ValueError:
            # Try quarterly format (YYYYQ1)
            try:
                year = int(period[:4])
                quarter = int(period[-1])
                # Approximate to end of quarter
                month = quarter * 3
                period_date = datetime(year, month, 1)
            except ValueError:
                return False, "Cannot determine period date"
        
        # Calculate lock date (period end + lock days)
        from dateutil.relativedelta import relativedelta
        lock_date = period_date + relativedelta(months=1)  # End of period
        lock_date = lock_date + relativedelta(days=self.lock_days)
        
        if submitted_at > lock_date:
            return True, f"Period locked: {self.lock_days} days after period end have passed"
        
        return False, None
    
    def can_edit(
        self,
        run: DHIMS2SubmissionRun,
        user_has_override_permission: bool = False,
        override_justification: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a run can be edited.
        
        Args:
            run: The submission run
            user_has_override_permission: Whether user can override locks
            override_justification: Justification for override
            
        Returns:
            Tuple of (can_edit, reason)
        """
        # Check if explicitly locked
        if run.is_locked:
            if user_has_override_permission and override_justification:
                return True, "Override granted"
            return False, "Run is explicitly locked"
        
        # Check period lock
        if run.submitted_at:
            is_locked, reason = self.is_locked(run.period, run.submitted_at)
            if is_locked:
                if user_has_override_permission and override_justification:
                    return True, "Override granted"
                return False, reason
        
        return True, None
