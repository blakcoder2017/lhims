"""
Insurance Provider API Routes

Routes for managing insurance providers.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.models.user_models import User
from app.models.insurance_provider_models import InsuranceProvider
from app.schemas.insurance_provider_schemas import (
    InsuranceProviderCreate, InsuranceProviderUpdate, InsuranceProvider
)
from app.crud import insurance_provider_crud

router = APIRouter(
    prefix="/api/v1/insurance-providers",
    tags=["Insurance Providers"]
)

templates = Jinja2Templates(directory="app/templates")


# API Endpoints
@router.post("", response_model=InsuranceProvider, status_code=status.HTTP_201_CREATED)
def create_insurance_provider(
    insurance_provider: InsuranceProviderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Finance"]))
):
    """Create a new insurance provider (JSON API)"""
    # Check if provider with same name or code already exists
    if insurance_provider.code:
        existing = insurance_provider_crud.get_insurance_provider_by_code(db, insurance_provider.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insurance provider with code '{insurance_provider.code}' already exists"
            )
    
    existing_name = insurance_provider_crud.get_insurance_provider_by_name(db, insurance_provider.name)
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insurance provider with name '{insurance_provider.name}' already exists"
        )
    
    return insurance_provider_crud.create_insurance_provider(db, insurance_provider)


@router.get("", response_model=List[InsuranceProvider])
def get_insurance_providers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all insurance providers"""
    return insurance_provider_crud.get_insurance_providers(db, skip=skip, limit=limit, active_only=active_only)


@router.get("/{insurance_provider_id}", response_model=InsuranceProvider)
def get_insurance_provider(
    insurance_provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get an insurance provider by ID"""
    insurance_provider = insurance_provider_crud.get_insurance_provider(db, insurance_provider_id)
    if not insurance_provider:
        raise HTTPException(status_code=404, detail="Insurance provider not found")
    return insurance_provider


@router.put("/{insurance_provider_id}", response_model=InsuranceProvider)
def update_insurance_provider(
    insurance_provider_id: int,
    insurance_provider_update: InsuranceProviderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Finance"]))
):
    """Update an insurance provider"""
    insurance_provider = insurance_provider_crud.update_insurance_provider(
        db, insurance_provider_id, insurance_provider_update
    )
    if not insurance_provider:
        raise HTTPException(status_code=404, detail="Insurance provider not found")
    return insurance_provider


@router.delete("/{insurance_provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_insurance_provider(
    insurance_provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Delete an insurance provider (soft delete)"""
    success = insurance_provider_crud.delete_insurance_provider(db, insurance_provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="Insurance provider not found")
    return None

