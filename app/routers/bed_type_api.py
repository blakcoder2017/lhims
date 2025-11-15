"""
Bed Type API Routes

API routes for managing bed types.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.models.user_models import User
from app.models.bed_type_models import BedType
from app.schemas.bed_type_schemas import (
    BedTypeCreate, BedTypeUpdate, BedType
)
from app.crud import bed_type_crud

router = APIRouter(
    prefix="/api/v1/bed-types",
    tags=["Bed Types"]
)


# API Endpoints
@router.post("", response_model=BedType, status_code=status.HTTP_201_CREATED)
def create_bed_type(
    bed_type: BedTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Create a new bed type (JSON API)"""
    # Check if bed type with same name or code already exists
    if bed_type.code:
        existing = bed_type_crud.get_bed_type_by_code(db, bed_type.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bed type with code '{bed_type.code}' already exists"
            )
    
    existing_name = bed_type_crud.get_bed_type_by_name(db, bed_type.name)
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bed type with name '{bed_type.name}' already exists"
        )
    
    return bed_type_crud.create_bed_type(db, bed_type)


@router.get("", response_model=List[BedType])
def list_bed_types(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """List all bed types (JSON API)"""
    bed_types, total = bed_type_crud.get_bed_types(db, skip=skip, limit=limit, active_only=active_only)
    return bed_types


@router.get("/{bed_type_id}", response_model=BedType)
def get_bed_type(
    bed_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Get a bed type by ID (JSON API)"""
    bed_type = bed_type_crud.get_bed_type(db, bed_type_id)
    if not bed_type:
        raise HTTPException(status_code=404, detail="Bed type not found")
    return bed_type


@router.put("/{bed_type_id}", response_model=BedType)
def update_bed_type(
    bed_type_id: int,
    bed_type_update: BedTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Update a bed type (JSON API)"""
    bed_type = bed_type_crud.update_bed_type(db, bed_type_id, bed_type_update)
    if not bed_type:
        raise HTTPException(status_code=404, detail="Bed type not found")
    return bed_type


@router.delete("/{bed_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bed_type(
    bed_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Delete a bed type (soft delete) (JSON API)"""
    success = bed_type_crud.delete_bed_type(db, bed_type_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bed type not found")
    return None
