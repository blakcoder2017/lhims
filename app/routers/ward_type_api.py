"""
Ward Type API Routes

API routes for managing ward types.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.models.user_models import User
from app.models.ward_type_models import WardType
from app.schemas.ward_type_schemas import (
    WardTypeCreate, WardTypeUpdate, WardType
)
from app.crud import ward_type_crud

router = APIRouter(
    prefix="/api/v1/ward-types",
    tags=["Ward Types"]
)


# API Endpoints
@router.post("", response_model=WardType, status_code=status.HTTP_201_CREATED)
def create_ward_type(
    ward_type: WardTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Create a new ward type (JSON API)"""
    # Check if ward type with same name or code already exists
    if ward_type.code:
        existing = ward_type_crud.get_ward_type_by_code(db, ward_type.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ward type with code '{ward_type.code}' already exists"
            )
    
    existing_name = ward_type_crud.get_ward_type_by_name(db, ward_type.name)
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ward type with name '{ward_type.name}' already exists"
        )
    
    return ward_type_crud.create_ward_type(db, ward_type)


@router.get("", response_model=List[WardType])
def get_ward_types(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all ward types"""
    ward_types, total_count = ward_type_crud.get_ward_types(db, skip=skip, limit=limit, active_only=active_only)
    return ward_types


@router.get("/{ward_type_id}", response_model=WardType)
def get_ward_type(
    ward_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a ward type by ID"""
    ward_type = ward_type_crud.get_ward_type(db, ward_type_id)
    if not ward_type:
        raise HTTPException(status_code=404, detail="Ward type not found")
    return ward_type


@router.put("/{ward_type_id}", response_model=WardType)
def update_ward_type(
    ward_type_id: int,
    ward_type_update: WardTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Update a ward type"""
    ward_type = ward_type_crud.update_ward_type(
        db, ward_type_id, ward_type_update
    )
    if not ward_type:
        raise HTTPException(status_code=404, detail="Ward type not found")
    return ward_type


@router.delete("/{ward_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ward_type(
    ward_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Delete a ward type (soft delete)"""
    success = ward_type_crud.delete_ward_type(db, ward_type_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ward type not found")
    return None

