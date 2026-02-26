"""
DHIMS2 Submission Services

Business logic for:
- Building submission packages
- Approval workflow
- Submitting to DHIMS2
- Audit logging
"""
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import hashlib

from sqlalchemy.orm import Session

from app.models.dhims2_models import (
    DHIMS2Instance,
    DHIMS2Mapping,
    DHIMS2OrgUnitMapping,
    DHIMS2SubmissionRun,
    DHIMS2SubmissionItem,
    DHIMS2AuditLog,
    SubmissionRunStatus,
    ValidationStatus
)
from app.integrations.dhims2.client import Dhis2Client, compute_payload_hash, DHIS2Exception
from app.integrations.dhims2.validators import DataValidator, PeriodLockChecker
from app.core.config import settings

logger = logging.getLogger(__name__)


class AuditLogger:
    """Audit logger for DHIMS2 operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log(
        self,
        user_id: int,
        username: str,
        action: str,
        run_id: Optional[int] = None,
        mapping_id: Optional[int] = None,
        instance_id: Optional[int] = None,
        before_status: Optional[str] = None,
        after_status: Optional[str] = None,
        justification: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Create an audit log entry."""
        log_entry = DHIMS2AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            run_id=run_id,
            mapping_id=mapping_id,
            instance_id=instance_id,
            before_status=before_status,
            after_status=after_status,
            justification=justification,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.utcnow()
        )
        self.db.add(log_entry)
        self.db.commit()
        
        logger.info(
            f"DHIMS2 Audit: user={username}, action={action}, "
            f"run_id={run_id}, status={before_status}->{after_status}"
        )


class SubmissionService:
    """
    Service for managing DHIMS2 submission workflow.
    
    Workflow:
    1. BUILD: Extract data and create draft run
    2. VALIDATE: Run data quality checks
    3. SUBMIT_FOR_APPROVAL: Move to pending approval
    4. APPROVE: Approve the submission
    5. SUBMIT: Send to DHIMS2
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.validator = DataValidator(db)
        self.lock_checker = PeriodLockChecker()
    
    def build_submission(
        self,
        instance_id: int,
        org_unit_uid: str,
        period: str,
        report_type: str,
        dataset_uid: Optional[str],
        data_provider,  # ReportingDataProvider implementation
        prepared_by: int,
        username: str,
        ip_address: Optional[str] = None
    ) -> DHIMS2SubmissionRun:
        """
        Build a new submission run from data provider.
        
        Args:
            instance_id: DHIMS2 instance ID
            org_unit_uid: DHIS2 org unit UID
            period: Period string (e.g., "2026-01")
            report_type: Report type identifier
            dataset_uid: DHIS2 dataset UID
            data_provider: Provider to extract data
            prepared_by: User ID who prepared
            username: Username for audit
            ip_address: Client IP for audit
            
        Returns:
            Created submission run
        """
        # Get active mappings for this instance
        mappings = self.db.query(DHIMS2Mapping).filter(
            DHIMS2Mapping.instance_id == instance_id,
            DHIMS2Mapping.is_active == True
        ).all()
        
        if not mappings:
            raise ValueError(f"No active mappings found for instance {instance_id}")
        
        # Extract data from provider
        raw_data = data_provider.get_values(
            org_unit_uid=org_unit_uid,
            period=period,
            report_type=report_type
        )
        
        # Create submission run
        run = DHIMS2SubmissionRun(
            instance_id=instance_id,
            org_unit_uid=org_unit_uid,
            period=period,
            report_type=report_type,
            dataset_uid=dataset_uid,
            status=SubmissionRunStatus.DRAFT,
            prepared_by=prepared_by,
            prepared_at=datetime.utcnow()
        )
        self.db.add(run)
        self.db.flush()  # Get the run ID
        
        # Create submission items
        items: List[DHIMS2SubmissionItem] = []
        for mapping in mappings:
            if mapping.internal_metric_key in raw_data:
                value = str(raw_data[mapping.internal_metric_key])
                
                item = DHIMS2SubmissionItem(
                    run_id=run.id,
                    internal_metric_key=mapping.internal_metric_key,
                    value=value,
                    dhis2_data_element_uid=mapping.dhis2_data_element_uid,
                    dhis2_category_option_combo_uid=mapping.dhis2_category_option_combo_uid,
                    dhis2_attribute_option_combo_uid=mapping.dhis2_attribute_option_combo_uid,
                    validation_status=ValidationStatus.PASS,
                    source_table=data_provider.source_table,
                    source_record_id=raw_data.get(f"{mapping.internal_metric_key}_record_id")
                )
                items.append(item)
                self.db.add(item)
        
        self.db.flush()
        
        # Compute payload hash
        payload_data = {
            "org_unit": org_unit_uid,
            "period": period,
            "report_type": report_type,
            "items": [
                {
                    "key": item.internal_metric_key,
                    "value": item.value,
                    "de_uid": item.dhis2_data_element_uid,
                    "coc_uid": item.dhis2_category_option_combo_uid
                }
                for item in items
            ]
        }
        run.payload_hash = compute_payload_hash(payload_data)
        
        self.db.commit()
        
        # Audit log
        audit = AuditLogger(self.db)
        audit.log(
            user_id=prepared_by,
            username=username,
            action="BUILD",
            run_id=run.id,
            instance_id=instance_id,
            before_status=None,
            after_status=SubmissionRunStatus.DRAFT.value,
            ip_address=ip_address
        )
        
        logger.info(
            f"Built submission run: id={run.id}, org_unit={org_unit_uid}, "
            f"period={period}, items={len(items)}"
        )
        
        return run
    
    def validate_run(
        self,
        run_id: int,
        required_metrics: Optional[List[str]] = None,
        cross_check_rules: Optional[List[Dict]] = None
    ) -> Tuple[DHIMS2SubmissionRun, List[Dict]]:
        """
        Validate a submission run.
        
        Args:
            run_id: Run ID
            required_metrics: Required metric keys
            cross_check_rules: Cross-check rules
            
        Returns:
            Tuple of (updated run, validation results)
        """
        run = self.db.query(DHIMS2SubmissionRun).filter(
            DHIMS2SubmissionRun.id == run_id
        ).first()
        
        if not run:
            raise ValueError(f"Run {run_id} not found")
        
        if run.status not in [SubmissionRunStatus.DRAFT, SubmissionRunStatus.VALIDATION_FAILED]:
            raise ValueError(f"Cannot validate run in status: {run.status}")
        
        # Run validation
        results, overall_status = self.validator.validate_run(
            run, required_metrics, cross_check_rules
        )
        
        # Update items with validation status
        for result in results:
            if result.metric_key:
                item = self.db.query(DHIMS2SubmissionItem).filter(
                    DHIMS2SubmissionItem.run_id == run_id,
                    DHIMS2SubmissionItem.internal_metric_key == result.metric_key
                ).first()
                
                if item:
                    item.validation_status = result.status
                    item.validation_notes = result.message
        
        # Update run status
        if overall_status == ValidationStatus.FAIL:
            run.status = SubmissionRunStatus.VALIDATION_FAILED
        else:
            run.status = SubmissionRunStatus.DRAFT
        
        self.db.commit()
        
        # Convert results to dicts
        result_dicts = [r.to_dict() for r in results]
        
        logger.info(
            f"Validated run: id={run_id}, status={run.status.value}, "
            f"results={len(result_dicts)}"
        )
        
        return run, result_dicts
    
    def submit_for_approval(
        self,
        run_id: int,
        user_id: int,
        username: str,
        ip_address: Optional[str] = None
    ) -> DHIMS2SubmissionRun:
        """
        Submit a run for approval.
        
        Args:
            run_id: Run ID
            user_id: User ID
            username: Username
            ip_address: Client IP
            
        Returns:
            Updated run
        """
        run = self.db.query(DHIMS2SubmissionRun).filter(
            DHIMS2SubmissionRun.id == run_id
        ).first()
        
        if not run:
            raise ValueError(f"Run {run_id} not found")
        
        if run.status != SubmissionRunStatus.DRAFT:
            raise ValueError(f"Cannot submit for approval: status is {run.status}")
        
        # Check if data changed since approval (if previously approved)
        # For now, just check that prepared_by != user_id for separation of duties
        
        old_status = run.status.value
        run.status = SubmissionRunStatus.PENDING_APPROVAL
        
        self.db.commit()
        
        # Audit log
        audit = AuditLogger(self.db)
        audit.log(
            user_id=user_id,
            username=username,
            action="SUBMIT_FOR_APPROVAL",
            run_id=run_id,
            instance_id=run.instance_id,
            before_status=old_status,
            after_status=run.status.value,
            ip_address=ip_address
        )
        
        logger.info(f"Submitted run for approval: id={run_id}")
        
        return run
    
    def approve(
        self,
        run_id: int,
        user_id: int,
        username: str,
        ip_address: Optional[str] = None,
        allow_self_approval: bool = False
    ) -> DHIMS2SubmissionRun:
        """
        Approve a submission run.
        
        Args:
            run_id: Run ID
            user_id: Approver user ID
            username: Approver username
            ip_address: Client IP
            allow_self_approval: Allow preparer to approve
            
        Returns:
            Updated run
        """
        run = self.db.query(DHIMS2SubmissionRun).filter(
            DHIMS2SubmissionRun.id == run_id
        ).first()
        
        if not run:
            raise ValueError(f"Run {run_id} not found")
        
        if run.status != SubmissionRunStatus.PENDING_APPROVAL:
            raise ValueError(f"Cannot approve: status is {run.status}")
        
        # Check for self-approval
        if run.prepared_by == user_id and not allow_self_approval:
            raise ValueError("Self-approval not allowed. Use separate approver.")
        
        old_status = run.status.value
        run.status = SubmissionRunStatus.APPROVED
        run.approved_by = user_id
        run.approved_at = datetime.utcnow()
        
        # Re-compute payload hash to freeze the data
        items = self.db.query(DHIMS2SubmissionItem).filter(
            DHIMS2SubmissionItem.run_id == run_id
        ).all()
        
        payload_data = {
            "org_unit": run.org_unit_uid,
            "period": run.period,
            "report_type": run.report_type,
            "items": [
                {
                    "key": item.internal_metric_key,
                    "value": item.value,
                    "de_uid": item.dhis2_data_element_uid,
                    "coc_uid": item.dhis2_category_option_combo_uid
                }
                for item in items
            ]
        }
        run.payload_hash = compute_payload_hash(payload_data)
        
        self.db.commit()
        
        # Audit log
        audit = AuditLogger(self.db)
        audit.log(
            user_id=user_id,
            username=username,
            action="APPROVE",
            run_id=run_id,
            instance_id=run.instance_id,
            before_status=old_status,
            after_status=run.status.value,
            ip_address=ip_address
        )
        
        logger.info(f"Approved run: id={run_id} by user {user_id}")
        
        return run
    
    def submit_to_dhims2(
        self,
        run_id: int,
        user_id: int,
        username: str,
        dry_run: bool = False,
        ip_address: Optional[str] = None
    ) -> Tuple[DHIMS2SubmissionRun, Dict[str, Any]]:
        """
        Submit an approved run to DHIMS2.
        
        Args:
            run_id: Run ID
            user_id: User ID
            username: Username
            dry_run: If True, validate but don't submit
            ip_address: Client IP
            
        Returns:
            Tuple of (updated run, DHIS2 response)
        """
        run = self.db.query(DHIMS2SubmissionRun).filter(
            DHIMS2SubmissionRun.id == run_id
        ).first()
        
        if not run:
            raise ValueError(f"Run {run_id} not found")
        
        if run.status not in [SubmissionRunStatus.APPROVED, SubmissionRunStatus.DRAFT]:
            raise ValueError(f"Cannot submit: status is {run.status}")
        
        # Check lock status
        can_edit, reason = self.lock_checker.can_edit(run)
        if not can_edit:
            raise ValueError(f"Cannot submit: {reason}")
        
        # Get instance
        instance = self.db.query(DHIMS2Instance).filter(
            DHIMS2Instance.id == run.instance_id
        ).first()
        
        if not instance:
            raise ValueError(f"Instance {run.instance_id} not found")
        
        # Get submission items
        items = self.db.query(DHIMS2SubmissionItem).filter(
            DHIMS2SubmissionItem.run_id == run_id
        ).all()
        
        # Build data values payload
        data_values = []
        for item in items:
            value_obj = {
                "dataElement": item.dhis2_data_element_uid,
                "value": item.value
            }
            if item.dhis2_category_option_combo_uid:
                value_obj["categoryOptionCombo"] = item.dhis2_category_option_combo_uid
            if item.dhis2_attribute_option_combo_uid:
                value_obj["attributeOptionCombo"] = item.dhis2_attribute_option_combo_uid
            
            data_values.append(value_obj)
        
        # Create client
        client = Dhis2Client(
            base_url=instance.base_url,
            username=instance.username,
            password=instance.password,
            timeout=instance.timeout_seconds,
            verify_tls=instance.verify_tls,
            max_retries=instance.max_retries
        )
        
        # Submit
        old_status = run.status.value
        
        try:
            # Override dry_run from settings
            effective_dry_run = settings.DHIMS2_DRY_RUN or dry_run
            
            response = client.submit_data_values(
                data_set=run.dataset_uid or "",
                org_unit=run.org_unit_uid,
                period=run.period,
                data_values=data_values,
                dry_run=effective_dry_run
            )
            
            # Extract import counts
            import_count = response.get("importCount", {})
            
            run.status = SubmissionRunStatus.SUBMITTED
            run.submitted_at = datetime.utcnow()
            run.dhis2_import_count = import_count
            
            # Store sanitized response
            run.dhis2_response = json.dumps({
                "status": response.get("status"),
                "importCount": import_count,
                "description": response.get("description", "")[:500]
            })
            
            logger.info(
                f"Submitted to DHIMS2: id={run_id}, "
                f"imported={import_count.get('imported')}, "
                f"updated={import_count.get('updated')}, "
                f"ignored={import_count.get('ignored')}"
            )
            
        except DHIS2Exception as e:
            run.status = SubmissionRunStatus.SUBMIT_FAILED
            run.error_summary = str(e.message)[:500]
            
            logger.error(f"DHIMS2 submission failed: id={run_id}, error={e.message}")
            
            # Audit log for failure
            audit = AuditLogger(self.db)
            audit.log(
                user_id=user_id,
                username=username,
                action="SUBMIT_FAILED",
                run_id=run_id,
                instance_id=run.instance_id,
                before_status=old_status,
                after_status=run.status.value,
                justification=str(e.message),
                ip_address=ip_address
            )
            
            raise
        
        self.db.commit()
        
        # Audit log
        audit = AuditLogger(self.db)
        audit.log(
            user_id=user_id,
            username=username,
            action="SUBMIT",
            run_id=run_id,
            instance_id=run.instance_id,
            before_status=old_status,
            after_status=run.status.value,
            ip_address=ip_address
        )
        
        return run, response
    
    def get_runs(
        self,
        instance_id: Optional[int] = None,
        org_unit_uid: Optional[str] = None,
        period: Optional[str] = None,
        status: Optional[SubmissionRunStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DHIMS2SubmissionRun]:
        """Get submission runs with filters."""
        query = self.db.query(DHIMS2SubmissionRun)
        
        if instance_id:
            query = query.filter(DHIMS2SubmissionRun.instance_id == instance_id)
        if org_unit_uid:
            query = query.filter(DHIMS2SubmissionRun.org_unit_uid == org_unit_uid)
        if period:
            query = query.filter(DHIMS2SubmissionRun.period == period)
        if status:
            query = query.filter(DHIMS2SubmissionRun.status == status)
        
        return query.order_by(
            DHIMS2SubmissionRun.created_at.desc()
        ).offset(offset).limit(limit).all()
    
    def lock_run(
        self,
        run_id: int,
        user_id: int,
        username: str,
        justification: str,
        ip_address: Optional[str] = None
    ) -> DHIMS2SubmissionRun:
        """Lock a run to prevent editing."""
        run = self.db.query(DHIMS2SubmissionRun).filter(
            DHIMS2SubmissionRun.id == run_id
        ).first()
        
        if not run:
            raise ValueError(f"Run {run_id} not found")
        
        old_status = run.status.value
        run.is_locked = True
        run.locked_at = datetime.utcnow()
        run.locked_by = user_id
        run.lock_justification = justification
        
        self.db.commit()
        
        audit = AuditLogger(self.db)
        audit.log(
            user_id=user_id,
            username=username,
            action="LOCK",
            run_id=run_id,
            instance_id=run.instance_id,
            before_status=old_status,
            after_status=old_status,
            justification=justification,
            ip_address=ip_address
        )
        
        return run
