"""
Lab Template Resolution Service

Resolves which template and version to use for a lab order result.

Logic:
1. If LabOrder already has template_version_used, use it (stable results)
2. Else use catalog mapping:
   - If LabTest.template_version is set, use it
   - Else use LabTemplate.current_version (latest published)
3. Persist template_id and template_version_used into LabOrder on first open
"""
import uuid
from dataclasses import dataclass
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.models.lab_template_models import LabTemplate, LabTemplateVersion
from app.models.lab_catalog_models import LabTest
from app.models.encounter_models import LabOrder


@dataclass
class ResolvedTemplate:
    """Result of template resolution"""
    template_id: uuid.UUID
    template_version: int
    schema_json: dict
    
    # Source of resolution
    is_persisted: bool  # True if already saved in LabOrder
    is_from_catalog: bool  # True if resolved from catalog (not yet persisted)


class TemplateResolutionError(Exception):
    """Error during template resolution"""
    pass


def resolve_template_for_order(
    db: Session,
    lab_order: LabOrder,
    persist: bool = True
) -> ResolvedTemplate:
    """
    Resolve the template to use for a lab order result.
    
    Args:
        db: Database session
        lab_order: The LabOrder to resolve template for
        persist: Whether to persist resolved template_id and version to LabOrder
        
    Returns:
        ResolvedTemplate with template_id, version, and schema
        
    Raises:
        TemplateResolutionError: If template cannot be resolved
    """
    # 1. If already has template_version_used, use it (stable results)
    if lab_order.template_id and lab_order.template_version_used:
        version = _get_published_version(db, lab_order.template_id, lab_order.template_version_used)
        if version:
            return ResolvedTemplate(
                template_id=lab_order.template_id,
                template_version=lab_order.template_version_used,
                schema_json=version.schema_json,
                is_persisted=True,
                is_from_catalog=False
            )
        # Version not found, fall through to catalog resolution
    
    # 2. Use catalog mapping
    if not lab_order.lab_test_id:
        raise TemplateResolutionError(
            f"LabOrder {lab_order.id} has no lab_test_id and no template_id set"
        )
    
    lab_test = db.query(LabTest).filter(LabTest.id == lab_order.lab_test_id).first()
    if not lab_test:
        raise TemplateResolutionError(
            f"LabTest {lab_order.lab_test_id} not found"
        )
    
    # Get template_id from catalog
    template_id = lab_test.template_id
    if not template_id:
        raise TemplateResolutionError(
            f"LabTest {lab_test.id} has no template_id configured"
        )
    
    # Get version from catalog or use latest published
    if lab_test.template_version:
        template_version = lab_test.template_version
    else:
        # Use latest published version
        template = db.query(LabTemplate).filter(LabTemplate.id == template_id).first()
        if not template:
            raise TemplateResolutionError(f"LabTemplate {template_id} not found")
        
        if not template.current_version:
            raise TemplateResolutionError(
                f"LabTemplate {template_id} has no published versions"
            )
        template_version = template.current_version
    
    # Get the version record
    version = _get_published_version(db, template_id, template_version)
    if not version:
        raise TemplateResolutionError(
            f"Published LabTemplateVersion not found for template {template_id}, version {template_version}"
        )
    
    # 3. Persist to LabOrder on first open (if requested)
    if persist:
        lab_order.template_id = template_id
        lab_order.template_version_used = template_version
        # Don't commit here - let caller manage transaction
    
    return ResolvedTemplate(
        template_id=template_id,
        template_version=template_version,
        schema_json=version.schema_json,
        is_persisted=persist,
        is_from_catalog=True
    )


def _get_published_version(
    db: Session,
    template_id: uuid.UUID,
    version: int
) -> Optional[LabTemplateVersion]:
    """Get a published template version"""
    return db.query(LabTemplateVersion).filter(
        LabTemplateVersion.template_id == template_id,
        LabTemplateVersion.version == version,
        LabTemplateVersion.status == "PUBLISHED"
    ).first()


def get_template_version_schema(
    db: Session,
    template_id: uuid.UUID,
    version: Optional[int] = None
) -> Tuple[dict, int]:
    """
    Get template schema, optionally for specific version.
    If version is None, returns latest published.
    
    Returns:
        (schema_json, version_used)
    """
    if version:
        v = _get_published_version(db, template_id, version)
        if not v:
            raise TemplateResolutionError(
                f"Published version {version} not found for template {template_id}"
            )
        return v.schema_json, version
    
    # Get latest published
    template = db.query(LabTemplate).filter(LabTemplate.id == template_id).first()
    if not template or not template.current_version:
        raise TemplateResolutionError(f"No published version for template {template_id}")
    
    v = _get_published_version(db, template_id, template.current_version)
    if not v:
        raise TemplateResolutionError(
            f"Published version {template.current_version} not found for template {template_id}"
        )
    
    return v.schema_json, template.current_version


def is_template_locked(lab_order: LabOrder) -> bool:
    """
    Check if template is locked for an order (results already submitted).
    Once submitted, the template version used should not change.
    """
    if not lab_order.result_status:
        return False
    # Locked statuses: SUBMITTED, VERIFIED, AUTHORIZED, RELEASED, AMENDED
    locked_statuses = {"SUBMITTED", "VERIFIED", "AUTHORIZED", "RELEASED", "AMENDED"}
    return lab_order.result_status in locked_statuses
