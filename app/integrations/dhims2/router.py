"""
DHIMS2 API Routes

FastAPI router for DHIMS2 integration endpoints.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.models.user_models import User
from app.models.dhims2_models import (
    DHIMS2Instance,
    DHIMS2Mapping,
    DHIMS2OrgUnitMapping,
    DHIMS2SubmissionRun,
    SubmissionRunStatus
)
from app.integrations.dhims2 import services, schemas
from app.integrations.dhims2.providers import get_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dhims2", tags=["DHIMS2 Integration"])


# ============== Instance Management ==============

@router.post("/instances", response_model=schemas.DHIMS2InstanceResponse, status_code=status.HTTP_201_CREATED)
def create_instance(
    instance_data: schemas.DHIMS2InstanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Create a new DHIMS2 instance configuration."""
    instance = DHIMS2Instance(
        name=instance_data.name,
        base_url=instance_data.base_url,
        username=instance_data.username,
        password=instance_data.password,
        is_active=instance_data.is_active,
        timeout_seconds=instance_data.timeout_seconds,
        verify_tls=instance_data.verify_tls,
        max_retries=instance_data.max_retries
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


@router.get("/instances", response_model=list)
def list_instances(
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "DHIMS2Preparer", "DHIMS2Approver"])),
    active_only: bool = True
):
    """List DHIMS2 instances."""
    query = db.query(DHIMS2Instance)
    if active_only:
        query = query.filter(DHIMS2Instance.is_active == True)
    return query.all()


@router.get("/instances/{instance_id}", response_model=schemas.DHIMS2InstanceResponse)
def get_instance(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "DHIMS2Preparer", "DHIMS2Approver"]))
):
    """Get a specific instance."""
    instance = db.query(DHIMS2Instance).filter(DHIMS2Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    return instance


# ============== Mapping Management ==============

@router.post("/mappings", response_model=schemas.DHIMS2MappingResponse, status_code=status.HTTP_201_CREATED)
def create_mapping(
    mapping_data: schemas.DHIMS2MappingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Create a new metric mapping."""
    mapping = DHIMS2Mapping(
        instance_id=mapping_data.instance_id,
        internal_metric_key=mapping_data.internal_metric_key,
        dhis2_data_element_uid=mapping_data.dhis2_data_element_uid,
        dhis2_category_option_combo_uid=mapping_data.dhis2_category_option_combo_uid,
        dhis2_attribute_option_combo_uid=mapping_data.dhis2_attribute_option_combo_uid,
        dhis2_dataset_uid=mapping_data.dhis2_dataset_uid,
        value_type=mapping_data.value_type,
        is_active=mapping_data.is_active,
        is_required=mapping_data.is_required,
        description=mapping_data.description,
        validation_config=mapping_data.validation_config,
        created_by=current_user.id
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


@router.get("/mappings", response_model=schemas.MappingListResponse)
def list_mappings(
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "DHIMS2Preparer", "DHIMS2Approver"])),
    instance_id: Optional[int] = Query(None),
    active_only: bool = Query(True)
):
    """List metric mappings."""
    query = db.query(DHIMS2Mapping)
    if instance_id:
        query = query.filter(DHIMS2Mapping.instance_id == instance_id)
    if active_only:
        query = query.filter(DHIMS2Mapping.is_active == True)
    
    mappings = query.all()
    return {"mappings": mappings, "total": len(mappings)}


# ============== Org Unit Mapping Management ==============

@router.post("/org-unit-mappings", response_model=schemas.DHIMS2OrgUnitMappingResponse, status_code=status.HTTP_201_CREATED)
def create_org_unit_mapping(
    mapping_data: schemas.DHIMS2OrgUnitMappingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Create org unit mapping."""
    mapping = DHIMS2OrgUnitMapping(
        instance_id=mapping_data.instance_id,
        internal_org_id=mapping_data.internal_org_id,
        internal_org_type=mapping_data.internal_org_type,
        dhis2_org_unit_uid=mapping_data.dhis2_org_unit_uid,
        dhis2_org_unit_name=mapping_data.dhis2_org_unit_name
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


@router.get("/org-unit-mappings", response_model=list)
def list_org_unit_mappings(
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "DHIMS2Preparer"])),
    instance_id: Optional[int] = Query(None)
):
    """List org unit mappings."""
    query = db.query(DHIMS2OrgUnitMapping)
    if instance_id:
        query = query.filter(DHIMS2OrgUnitMapping.instance_id == instance_id)
    return query.all()


# ============== Submission Runs ==============

@router.post("/runs/build", response_model=schemas.SubmissionRunResponse, status_code=status.HTTP_201_CREATED)
def build_submission(
    request_data: schemas.BuildSubmissionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "DHIMS2Preparer"]))
):
    """
    Build a new submission run.
    
    Extracts data from LHIMS and creates a draft submission.
    """
    service = services.SubmissionService(db)
    
    # Get data provider
    try:
        provider = get_provider(request_data.provider, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Get client IP for audit
    client_ip = request.client.host if request.client else None
    
    try:
        run = service.build_submission(
            instance_id=request_data.instance_id,
            org_unit_uid=request_data.org_unit_uid,
            period=request_data.period,
            report_type=request_data.report_type,
            dataset_uid=request_data.dataset_uid,
            data_provider=provider,
            prepared_by=current_user.id,
            username=current_user.username,
            ip_address=client_ip
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return run


@router.post("/runs/{run_id}/validate")
def validate_submission(
    run_id: int,
    request_data: schemas.ValidateSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "DHIMS2Preparer", "DHIMS2Approver"]))
):
    """
    Validate a submission run.
    
    Runs data quality checks and returns results.
    """
    service = services.SubmissionService(db)
    
    try:
        run, results = service.validate_run(
            run_id=run_id,
            required_metrics=request_data.required_metrics,
            cross_check_rules=request_data.cross_check_rules
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {
        "run_id": run.id,
        "status": run.status.value,
        "validation_results": results
    }


@router.post("/runs/{run_id}/submit-for-approval")
def submit_for_approval(
    run_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "DHIMS2Preparer"]))
):
    """Submit a run for approval."""
    service = services.SubmissionService(db)
    client_ip = request.client.host if request.client else None
    
    try:
        run = service.submit_for_approval(
            run_id=run_id,
            user_id=current_user.id,
            username=current_user.username,
            ip_address=client_ip
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"run_id": run.id, "status": run.status.value}


@router.post("/runs/{run_id}/approve")
def approve_submission(
    run_id: int,
    request_data: schemas.ApproveSubmissionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "DHIMS2Approver"]))
):
    """Approve a submission."""
    service = services.SubmissionService(db)
    client_ip = request.client.host if request.client else None
    
    try:
        run = service.approve(
            run_id=run_id,
            user_id=current_user.id,
            username=current_user.username,
            ip_address=client_ip,
            allow_self_approval=request_data.allow_self_approval
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"run_id": run.id, "status": run.status.value}


@router.post("/runs/{run_id}/submit")
def submit_to_dhims2(
    run_id: int,
    request_data: schemas.SubmitToDHIMS2Request,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "DHIMS2Approver"]))
):
    """
    Submit an approved run to DHIMS2.
    
    If dry_run is true, validates but doesn't actually submit.
    """
    service = services.SubmissionService(db)
    client_ip = request.client.host if request.client else None
    
    try:
        run, response = service.submit_to_dhims2(
            run_id=run_id,
            user_id=current_user.id,
            username=current_user.username,
            dry_run=request_data.dry_run,
            ip_address=client_ip
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {
        "run_id": run.id,
        "status": run.status.value,
        "dry_run": request_data.dry_run,
        "import_count": run.dhis2_import_count,
        "error_summary": run.error_summary
    }


@router.get("/runs", response_model=schemas.SubmissionRunListResponse)
def list_runs(
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "DHIMS2Preparer", "DHIMS2Approver"])),
    instance_id: Optional[int] = Query(None),
    org_unit_uid: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    status: Optional[SubmissionRunStatus] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200)
):
    """List submission runs with filters."""
    service = services.SubmissionService(db)
    
    offset = (page - 1) * page_size
    runs = service.get_runs(
        instance_id=instance_id,
        org_unit_uid=org_unit_uid,
        period=period,
        status=status,
        limit=page_size,
        offset=offset
    )
    
    # Get total count
    query = db.query(DHIMS2SubmissionRun)
    if instance_id:
        query = query.filter(DHIMS2SubmissionRun.instance_id == instance_id)
    if org_unit_uid:
        query = query.filter(DHIMS2SubmissionRun.org_unit_uid == org_unit_uid)
    if period:
        query = query.filter(DHIMS2SubmissionRun.period == period)
    if status:
        query = query.filter(DHIMS2SubmissionRun.status == status)
    
    total = query.count()
    
    return {
        "runs": runs,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/runs/{run_id}", response_model=schemas.SubmissionRunResponse)
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "DHIMS2Preparer", "DHIMS2Approver"])),
    include_items: bool = Query(False)
):
    """Get a specific submission run."""
    run = db.query(DHIMS2SubmissionRun).filter(DHIMS2SubmissionRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if include_items:
        from app.models.dhims2_models import DHIMS2SubmissionItem
        items = db.query(DHIMS2SubmissionItem).filter(DHIMS2SubmissionItem.run_id == run_id).all()
        run.items = items
    
    return run


@router.post("/runs/{run_id}/lock")
def lock_run(
    run_id: int,
    request_data: schemas.LockSubmissionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Lock a submission run."""
    service = services.SubmissionService(db)
    client_ip = request.client.host if request.client else None
    
    try:
        run = service.lock_run(
            run_id=run_id,
            user_id=current_user.id,
            username=current_user.username,
            justification=request_data.justification,
            ip_address=client_ip
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"run_id": run.id, "is_locked": run.is_locked}


# ============== Metadata Sync ==============

@router.post("/metadata/sync")
def sync_metadata(
    request_data: schemas.MetadataSyncRequest,
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """
    Sync metadata from DHIMS2.
    
    Fetches org units, data elements, data sets, etc. from DHIS2.
    """
    from app.integrations.dhims2.client import Dhis2Client, DHIS2Exception
    
    instance = db.query(DHIMS2Instance).filter(DHIMS2Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    client = Dhis2Client(
        base_url=instance.base_url,
        username=instance.username,
        password=instance.password,
        timeout=instance.timeout_seconds,
        verify_tls=instance.verify_tls,
        max_retries=instance.max_retries
    )
    
    response = schemas.MetadataSyncResponse()
    errors: list = []
    
    # Test connection first
    try:
        client.test_connection()
    except DHIS2Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {e.message}")
    
    # Sync org units
    if request_data.sync_org_units:
        try:
            org_units = client.get_organisation_units(
                fields=["id", "name", "level", "parent"]
            )
            response.org_units_synced = len(org_units)
            logger.info(f"Synced {len(org_units)} org units from DHIS2")
        except DHIS2Exception as e:
            errors.append(f"Org units sync failed: {e.message}")
    
    # Sync data elements
    if request_data.sync_data_elements:
        try:
            data_elements = client.get_data_elements(
                fields=["id", "name", "code"]
            )
            response.data_elements_synced = len(data_elements)
            logger.info(f"Synced {len(data_elements)} data elements from DHIS2")
        except DHIS2Exception as e:
            errors.append(f"Data elements sync failed: {e.message}")
    
    # Sync data sets
    if request_data.sync_data_sets:
        try:
            data_sets = client.get_data_sets(
                fields=["id", "name", "code"]
            )
            response.data_sets_synced = len(data_sets)
            logger.info(f"Synced {len(data_sets)} data sets from DHIS2")
        except DHIS2Exception as e:
            errors.append(f"Data sets sync failed: {e.message}")
    
    # Sync category combos
    if request_data.sync_category_combos:
        try:
            category_combos = client.get_category_option_combos(
                fields=["id", "name"]
            )
            response.category_combos_synced = len(category_combos)
            logger.info(f"Synced {len(category_combos)} category combos from DHIS2")
        except DHIS2Exception as e:
            errors.append(f"Category combos sync failed: {e.message}")
    
    response.errors = errors
    return response


# ============== Health Check ==============

@router.get("/health")
def health_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Check DHIMS2 connectivity."""
    from app.integrations.dhims2.client import Dhis2Client, DHIS2Exception
    from app.core.config import settings
    
    if not settings.DHIMS2_BASE_URL:
        return {"status": "not_configured", "message": "DHIMS2 not configured"}
    
    try:
        client = Dhis2Client()
        client.test_connection()
        user_info = client.get_user_info()
        return {
            "status": "healthy",
            "base_url": settings.DHIMS2_BASE_URL,
            "user": user_info.get("userCredentials", {}).get("username"),
            "instance": settings.DHIMS2_INSTANCE_NAME
        }
    except DHIS2Exception as e:
        return {
            "status": "error",
            "message": e.message
        }
