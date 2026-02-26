"""CRUD for Lab Template System - with proper versioning for immutability"""
import hashlib
import json
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.lab_template_models import (
    LabTemplate, LabTemplateVersion,
    LabOptionSet, LabReferenceRange
)


def _compute_checksum(schema_json: dict) -> str:
    """Compute SHA-256 checksum of schema_json for integrity."""
    json_str = json.dumps(schema_json, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


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
    return db.query(LabTemplate).filter(LabTemplate.id == template_id).first()


def get_templates(
    db: Session,
    discipline: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
) -> List[LabTemplate]:
    q = db.query(LabTemplate)
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
