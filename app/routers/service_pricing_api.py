from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.crud import service_pricing_crud
from app.schemas.service_pricing_schemas import ServicePricingCreate, ServicePricingUpdate

router = APIRouter(tags=["Service Pricing"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/admin/service-pricing", name="service_pricing_management")
def service_pricing_management(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    charge_type_filter: Optional[str] = Query(None)
):
    """Service pricing management dashboard"""
    from app.models.billing_models import ChargeType
    
    pricing_list = service_pricing_crud.get_all_service_pricing(db, limit=1000, include_inactive=False)
    
    if charge_type_filter:
        pricing_list = [p for p in pricing_list if p.charge_type == charge_type_filter]
    
    # Get all charge types for filter
    charge_types = [ct.value for ct in ChargeType]
    
    context = {
        "request": request,
        "title": "Service Pricing Management",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "pricing_list": pricing_list,
        "charge_types": charge_types,
        "charge_type_filter": charge_type_filter
    }
    return templates.TemplateResponse("admin/service_pricing.html", context)


@router.get("/admin/service-pricing/create", name="create_service_pricing_page")
def create_service_pricing_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Page for creating a new service pricing"""
    from app.models.billing_models import ChargeType
    
    context = {
        "request": request,
        "title": "Create Service Pricing",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "charge_types": [ct.value for ct in ChargeType]
    }
    return templates.TemplateResponse("admin/create_service_pricing.html", context)


@router.post("/admin/service-pricing/create", name="create_service_pricing", status_code=302)
def create_service_pricing(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    service_name: str = Form(...),
    service_code: Optional[str] = Form(None),
    charge_type: str = Form(...),
    category: Optional[str] = Form(None),
    unit_price: str = Form(...),
    currency: str = Form(default="GHS"),
    description: Optional[str] = Form(None),
    is_active: bool = Form(default=True)
):
    """Create a new service pricing"""
    try:
        pricing_data = ServicePricingCreate(
            service_name=service_name,
            service_code=service_code if service_code else None,
            charge_type=charge_type,
            category=category if category else None,
            unit_price=Decimal(unit_price),
            currency=currency,
            description=description if description else None,
            is_active=is_active
        )
        
        service_pricing_crud.create_service_pricing(db, pricing_data, current_user.id)
        
        return RedirectResponse(
            url=f"/admin/service-pricing?status=created",
            status_code=302
        )
    except Exception as e:
        from app.models.billing_models import ChargeType
        context = {
            "request": request,
            "title": "Create Service Pricing",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "charge_types": [ct.value for ct in ChargeType],
            "error": f"Error creating service pricing: {str(e)}"
        }
        return templates.TemplateResponse("admin/create_service_pricing.html", context)


@router.get("/admin/service-pricing/{pricing_id}/edit", name="edit_service_pricing_page")
def edit_service_pricing_page(
    request: Request,
    pricing_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Page for editing service pricing"""
    from app.models.billing_models import ChargeType
    
    pricing = service_pricing_crud.get_service_pricing(db, pricing_id)
    if not pricing:
        raise HTTPException(status_code=404, detail="Service pricing not found")
    
    context = {
        "request": request,
        "title": "Edit Service Pricing",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "pricing": pricing,
        "charge_types": [ct.value for ct in ChargeType]
    }
    return templates.TemplateResponse("admin/edit_service_pricing.html", context)


@router.post("/admin/service-pricing/{pricing_id}/edit", name="update_service_pricing", status_code=302)
def update_service_pricing(
    request: Request,
    pricing_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    service_name: Optional[str] = Form(None),
    service_code: Optional[str] = Form(None),
    charge_type: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    unit_price: Optional[str] = Form(None),
    currency: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None)
):
    """Update service pricing"""
    try:
        update_data = {}
        if service_name is not None:
            update_data['service_name'] = service_name
        if service_code is not None:
            update_data['service_code'] = service_code
        if charge_type is not None:
            update_data['charge_type'] = charge_type
        if category is not None:
            update_data['category'] = category
        if unit_price is not None:
            update_data['unit_price'] = Decimal(unit_price)
        if currency is not None:
            update_data['currency'] = currency
        if description is not None:
            update_data['description'] = description
        if is_active is not None:
            update_data['is_active'] = is_active
        
        pricing_update = ServicePricingUpdate(**update_data)
        service_pricing_crud.update_service_pricing(db, pricing_id, pricing_update, current_user.id)
        
        return RedirectResponse(
            url=f"/admin/service-pricing?status=updated",
            status_code=302
        )
    except Exception as e:
        from app.models.billing_models import ChargeType
        pricing = service_pricing_crud.get_service_pricing(db, pricing_id)
        context = {
            "request": request,
            "title": "Edit Service Pricing",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "pricing": pricing,
            "charge_types": [ct.value for ct in ChargeType],
            "error": f"Error updating service pricing: {str(e)}"
        }
        return templates.TemplateResponse("admin/edit_service_pricing.html", context)

