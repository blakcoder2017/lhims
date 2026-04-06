"""CRUD for Lab Template System - with proper versioning for immutability"""
import hashlib
import json
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.lab_template_models import (
    LabTemplate, LabTemplateVersion,
    LabOptionSet, LabReferenceRange
)


def _compute_checksum(schema_json: dict) -> str:
    """Compute SHA-256 checksum of schema_json for integrity."""
    json_str = json.dumps(schema_json, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


# --- Template Usage Tracking ---
def increment_template_usage(db: Session, template_id: UUID) -> None:
    """Increment the usage count for a template."""
    tmpl = get_template(db, template_id)
    if tmpl:
        tmpl.usage_count = (tmpl.usage_count or 0) + 1
        from datetime import datetime
        tmpl.last_used_at = datetime.utcnow()
        db.commit()


def get_template_usage_stats(db: Session, template_id: UUID) -> dict:
    """Get usage statistics for a template."""
    tmpl = get_template(db, template_id)
    if not tmpl:
        return None
    return {
        "usage_count": tmpl.usage_count or 0,
        "last_used_at": tmpl.last_used_at.isoformat() if tmpl.last_used_at else None,
        "created_at": tmpl.created_at.isoformat() if tmpl.created_at else None,
    }


def get_most_used_templates(db: Session, limit: int = 10) -> List[LabTemplate]:
    """Get most used templates."""
    return (
        db.query(LabTemplate)
        .filter(LabTemplate.status != "ARCHIVED")
        .order_by(LabTemplate.usage_count.desc().nullslast())
        .limit(limit)
        .all()
    )


# --- Template Cloning ---
def clone_template(
    db: Session,
    template_id: UUID,
    new_name: str,
    new_discipline: str,
    created_by_id: int
) -> LabTemplate:
    """Clone an existing template with its latest published schema."""
    source = get_template(db, template_id)
    if not source:
        return None
    
    # Get the latest published version or draft
    published = get_published_version(db, template_id)
    draft = get_draft_version(db, template_id)
    source_schema = None
    if published:
        source_schema = published.schema_json
    elif draft:
        source_schema = draft.schema_json
    
    if not source_schema:
        return None
    
    # Update metadata in schema
    new_schema = json.loads(json.dumps(source_schema))
    new_schema["meta"]["name"] = new_name
    new_schema["meta"]["discipline"] = new_discipline
    new_schema["meta"]["cloned_from"] = str(template_id)
    
    return create_template(db, new_name, new_discipline, created_by_id, new_schema)


# --- Template Export/Import ---
def export_template(db: Session, template_id: UUID) -> Optional[dict]:
    """Export template with all its versions and metadata."""
    tmpl = get_template(db, template_id)
    if not tmpl:
        return None
    
    versions = get_template_versions(db, template_id)
    
    return {
        "template": {
            "name": tmpl.name,
            "discipline": tmpl.discipline,
            "status": tmpl.status,
            "current_version": tmpl.current_version,
        },
        "versions": [
            {
                "version": v.version,
                "status": v.status,
                "schema_json": v.schema_json,
                "change_note": v.change_note,
                "checksum": v.checksum,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
        "exported_at": json.dumps({"exported_at": "now"}, default=str),
    }


def import_template(
    db: Session,
    template_data: dict,
    created_by_id: int
) -> LabTemplate:
    """Import a template from JSON data."""
    tmpl_info = template_data.get("template", {})
    versions = template_data.get("versions", [])
    
    # Create new template
    tmpl = LabTemplate(
        name=tmpl_info.get("name", "Imported Template"),
        discipline=tmpl_info.get("discipline", "General"),
        status="DRAFT",
        created_by_id=created_by_id
    )
    db.add(tmpl)
    db.flush()
    
    # Import versions
    for v in versions:
        ver = LabTemplateVersion(
            template_id=tmpl.id,
            version=v.get("version", 1),
            status=v.get("status", "DRAFT"),
            schema_json=v.get("schema_json", {}),
            change_note=v.get("change_note", "Imported"),
            checksum=v.get("checksum"),
            created_by_id=created_by_id
        )
        db.add(ver)
    
    # Set current version
    if versions:
        tmpl.current_version = max(v.get("version", 1) for v in versions)
        published = [v for v in versions if v.get("status") == "PUBLISHED"]
        if published:
            tmpl.status = "PUBLISHED"
    
    db.commit()
    db.refresh(tmpl)
    return tmpl


# --- Bulk Operations ---
def bulk_archive_templates(db: Session, template_ids: List[UUID]) -> int:
    """Archive multiple templates. Returns count of archived templates."""
    count = 0
    for template_id in template_ids:
        tmpl = get_template(db, template_id)
        if tmpl:
            tmpl.status = "ARCHIVED"
            count += 1
    db.commit()
    return count


def bulk_unarchive_templates(db: Session, template_ids: List[UUID]) -> int:
    """Unarchive multiple templates. Returns count of unarchived templates."""
    count = 0
    for template_id in template_ids:
        tmpl = get_template(db, template_id)
        if tmpl and tmpl.status == "ARCHIVED":
            tmpl.status = "DRAFT"
            count += 1
    db.commit()
    return count


# --- Soft Delete ---
def soft_delete_template(db: Session, template_id: UUID) -> Optional[LabTemplate]:
    """Soft delete a template (mark as deleted but keep data)."""
    tmpl = get_template(db, template_id)
    if not tmpl:
        return None
    tmpl.is_deleted = True
    tmpl.deleted_at = func.now()
    db.commit()
    db.refresh(tmpl)
    return tmpl


def restore_template(db: Session, template_id: UUID) -> Optional[LabTemplate]:
    """Restore a soft-deleted template."""
    tmpl = db.query(LabTemplate).filter(
        LabTemplate.id == template_id,
        LabTemplate.is_deleted == True
    ).first()
    if not tmpl:
        return None
    tmpl.is_deleted = False
    tmpl.deleted_at = None
    db.commit()
    db.refresh(tmpl)
    return tmpl


def get_deleted_templates(db: Session) -> List[LabTemplate]:
    """Get all soft-deleted templates."""
    return db.query(LabTemplate).filter(LabTemplate.is_deleted == True).all()


def get_all_disciplines(db: Session) -> List[str]:
    """Get all unique disciplines from templates."""
    result = db.query(LabTemplate.discipline).distinct().order_by(LabTemplate.discipline).all()
    return [d[0] for d in result if d[0]]


# --- Search and Filtering ---
def search_templates(
    db: Session,
    query: Optional[str] = None,
    discipline: Optional[str] = None,
    status: Optional[str] = None,
    include_deleted: bool = False,
    page: int = 1,
    page_size: int = 20
) -> tuple[List[LabTemplate], int]:
    """Search templates with filters and pagination. Returns (templates, total_count)."""
    q = db.query(LabTemplate)
    
    if not include_deleted:
        q = q.filter(LabTemplate.is_deleted != True)
    
    if query:
        search_pattern = f"%{query}%"
        q = q.filter(LabTemplate.name.ilike(search_pattern))
    
    if discipline:
        q = q.filter(LabTemplate.discipline == discipline)
    
    if status:
        q = q.filter(LabTemplate.status == status)
    
    # Get total count before pagination
    total = q.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    templates = q.order_by(LabTemplate.name).offset(offset).limit(page_size).all()
    
    return templates, total


# --- Option Sets ---
def get_option_set(db: Session, code: str) -> Optional[LabOptionSet]:
    return db.query(LabOptionSet).filter(LabOptionSet.code == code).first()


def get_all_option_sets(db: Session) -> List[LabOptionSet]:
    return db.query(LabOptionSet).order_by(LabOptionSet.code).all()


def upsert_option_set(db: Session, code: str, options_json: list) -> LabOptionSet:
    existing = get_option_set(db, code)
    if existing:
        existing.options_json = options_json
        db.commit()
        db.refresh(existing)
        return existing
    obj = LabOptionSet(code=code, options_json=options_json)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# --- Templates ---
def create_template(
    db: Session,
    name: str,
    discipline: str,
    created_by_id: int,
    schema_json: dict
) -> LabTemplate:
    tmpl = LabTemplate(
        name=name,
        discipline=discipline,
        status="DRAFT",
        created_by_id=created_by_id
    )
    db.add(tmpl)
    db.flush()
    ver = LabTemplateVersion(
        template_id=tmpl.id,
        version=1,
        status="DRAFT",
        schema_json=schema_json,
        created_by_id=created_by_id
    )
    db.add(ver)
    db.commit()
    db.refresh(tmpl)
    return tmpl


def get_template(db: Session, template_id: UUID) -> Optional[LabTemplate]:
    return db.query(LabTemplate).filter(
        LabTemplate.id == template_id,
        LabTemplate.is_deleted != True
    ).first()


def get_templates(
    db: Session,
    discipline: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
) -> List[LabTemplate]:
    q = db.query(LabTemplate).filter(LabTemplate.is_deleted != True)
    if discipline:
        q = q.filter(LabTemplate.discipline == discipline)
    if status:
        q = q.filter(LabTemplate.status == status)
    return q.order_by(LabTemplate.name).limit(limit).all()


def get_draft_version(db: Session, template_id: UUID) -> Optional[LabTemplateVersion]:
    return (
        db.query(LabTemplateVersion)
        .filter(
            LabTemplateVersion.template_id == template_id,
            LabTemplateVersion.status == "DRAFT"
        )
        .order_by(LabTemplateVersion.version.desc())
        .first()
    )


def get_published_version(
    db: Session,
    template_id: UUID,
    version: Optional[int] = None
) -> Optional[LabTemplateVersion]:
    q = (
        db.query(LabTemplateVersion)
        .filter(
            LabTemplateVersion.template_id == template_id,
            LabTemplateVersion.status == "PUBLISHED"
        )
    )
    if version is not None:
        q = q.filter(LabTemplateVersion.version == version)
    return q.order_by(LabTemplateVersion.version.desc()).first()


def get_version(db: Session, template_id: UUID, version: int) -> Optional[LabTemplateVersion]:
    """Get a specific version by version number (any status)."""
    return (
        db.query(LabTemplateVersion)
        .filter(
            LabTemplateVersion.template_id == template_id,
            LabTemplateVersion.version == version
        )
        .first()
    )


def save_draft(db: Session, template_id: UUID, schema_json: dict, created_by_id: int) -> Optional[LabTemplateVersion]:
    draft = get_draft_version(db, template_id)
    if draft:
        draft.schema_json = schema_json
        draft.created_by_id = created_by_id
        db.commit()
        db.refresh(draft)
        return draft
    tmpl = get_template(db, template_id)
    if not tmpl:
        return None
    next_ver = (db.query(LabTemplateVersion).filter(LabTemplateVersion.template_id == template_id)
                .count()) + 1
    ver = LabTemplateVersion(
        template_id=template_id,
        version=next_ver,
        status="DRAFT",
        schema_json=schema_json,
        created_by_id=created_by_id
    )
    db.add(ver)
    db.commit()
    db.refresh(ver)
    return ver


def publish_version(
    db: Session,
    template_id: UUID,
    change_note: Optional[str] = None,
    created_by_id: Optional[int] = None
) -> Optional[LabTemplateVersion]:
    """
    Publish draft - creates NEW immutable PUBLISHED version.
    This preserves immutability: published versions are never modified.
    
    - Gets the current draft version
    - Creates a NEW version record with status PUBLISHED (version = current_version + 1)
    - Computes checksum for the new published version
    - Updates template.current_version
    - Keeps the old draft as historical record
    """
    from uuid import uuid4
    
    draft = get_draft_version(db, template_id)
    if not draft:
        return None
    
    # Get current published version to increment
    current_published = get_published_version(db, template_id)
    new_version = (current_published.version + 1) if current_published else 1
    
    # Compute checksum for integrity
    checksum = _compute_checksum(draft.schema_json)
    
    # Create NEW version record (immutable PUBLISHED)
    new_published = LabTemplateVersion(
        id=uuid4(),
        template_id=template_id,
        version=new_version,
        status="PUBLISHED",
        schema_json=draft.schema_json,
        change_note=change_note,
        created_by_id=created_by_id or draft.created_by_id,
        checksum=checksum
    )
    db.add(new_published)
    
    # Update template metadata
    tmpl = get_template(db, template_id)
    if tmpl:
        tmpl.current_version = new_version
        tmpl.status = "PUBLISHED"
    
    # Note: We keep the old draft version in the database as historical record
    # It remains with status='DRAFT' but is no longer the latest draft
    
    db.commit()
    db.refresh(new_published)
    return new_published


def archive_template(db: Session, template_id: UUID) -> Optional[LabTemplate]:
    tmpl = get_template(db, template_id)
    if not tmpl:
        return None
    tmpl.status = "ARCHIVED"
    db.commit()
    db.refresh(tmpl)
    return tmpl


def get_template_versions(db: Session, template_id: UUID) -> List[LabTemplateVersion]:
    return (
        db.query(LabTemplateVersion)
        .filter(LabTemplateVersion.template_id == template_id)
        .order_by(LabTemplateVersion.version.desc())
        .all()
    )


# --- Reference Ranges (field-based) ---
def get_reference_range(
    db: Session,
    field_code: str,
    sex: str = "ANY",
    age_days: Optional[int] = None
) -> Optional[LabReferenceRange]:
    q = db.query(LabReferenceRange).filter(LabReferenceRange.field_code == field_code)
    q = q.filter(LabReferenceRange.sex.in_([sex, "ANY"]))
    if age_days is not None:
        q = q.filter(
            (LabReferenceRange.age_min_days == None) | (LabReferenceRange.age_min_days <= age_days),
            (LabReferenceRange.age_max_days == None) | (LabReferenceRange.age_max_days >= age_days)
        )
    return q.first()


def get_reference_range_for_patient(
    db: Session,
    template_id: Optional[str] = None,
    field_code: str = "",
    age_days: Optional[int] = None,
    sex: str = "ANY",
    gestational_age_weeks: Optional[int] = None
) -> Optional[LabReferenceRange]:
    """
    Get reference range for a patient based on age, sex, and gestational age.
    This is a wrapper around get_reference_range that accepts additional parameters.
    """
    return get_reference_range(db, field_code=field_code, sex=sex, age_days=age_days)
