"""
Insurance Provider UI Routes

UI routes for managing insurance providers.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, Query
from fastapi.responses import RedirectResponse
from app.core.templates import templates
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.models.user_models import User
from app.schemas.insurance_provider_schemas import InsuranceProviderCreate, InsuranceProviderUpdate
from app.crud import insurance_provider_crud

router = APIRouter(
    prefix="",
    tags=["Insurance Providers UI"]
)



@router.get("/insurance-providers", name="insurance_providers_list")
def list_insurance_providers(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Finance", "Front Office"])),
    active_only: bool = Query(True)
):
    """List all insurance providers"""
    insurance_providers = insurance_provider_crud.get_insurance_providers(db, active_only=active_only)
    
    context = {
        "request": request,
        "title": "Insurance Providers",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "insurance_providers": insurance_providers,
        "active_only": active_only
    }
    return templates.TemplateResponse("admin/insurance_providers_list.html", context)


@router.get("/insurance-providers/create", name="insurance_provider_create_form")
def insurance_provider_create_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Finance"]))
):
    """Show create insurance provider form"""
    context = {
        "request": request,
        "title": "Create Insurance Provider",
        "current_user": current_user,
        "user_role": current_user.role.name
    }
    return templates.TemplateResponse("admin/insurance_provider_form.html", context)


@router.post("/insurance-providers/create", name="insurance_provider_create", status_code=status.HTTP_302_FOUND)
def create_insurance_provider_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Finance"])),
    name: str = Form(...),
    code: Optional[str] = Form(None),
    contact_person: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    co_pay_rate: Optional[str] = Form(None),
    billing_email: Optional[str] = Form(None),
    billing_address: Optional[str] = Form(None)
):
    """Handle create insurance provider form submission"""
    try:
        # Check if provider with same name or code already exists
        if code:
            existing = insurance_provider_crud.get_insurance_provider_by_code(db, code)
            if existing:
                return RedirectResponse(
                    url=str(request.url_for("insurance_provider_create_form")) + "?error=code_exists",
                    status_code=status.HTTP_302_FOUND
                )
        
        existing_name = insurance_provider_crud.get_insurance_provider_by_name(db, name)
        if existing_name:
            return RedirectResponse(
                url=str(request.url_for("insurance_provider_create_form")) + "?error=name_exists",
                status_code=status.HTTP_302_FOUND
            )
        
        insurance_provider_data = InsuranceProviderCreate(
            name=name,
            code=code if code else None,
            contact_person=contact_person if contact_person else None,
            phone_number=phone_number if phone_number else None,
            email=email if email else None,
            address=address if address else None,
            co_pay_rate=co_pay_rate if co_pay_rate else None,
            billing_email=billing_email if billing_email else None,
            billing_address=billing_address if billing_address else None
        )
        
        insurance_provider_crud.create_insurance_provider(db, insurance_provider_data)
        
        return RedirectResponse(
            url=str(request.url_for("insurance_providers_list")) + "?status=created",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("insurance_provider_create_form")) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.get("/insurance-providers/{insurance_provider_id}", name="insurance_provider_detail")
def insurance_provider_detail(
    request: Request,
    insurance_provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Finance", "Front Office"]))
):
    """Show insurance provider detail"""
    insurance_provider = insurance_provider_crud.get_insurance_provider(db, insurance_provider_id)
    if not insurance_provider:
        raise HTTPException(status_code=404, detail="Insurance provider not found")
    
    context = {
        "request": request,
        "title": f"Insurance Provider: {insurance_provider.name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "insurance_provider": insurance_provider
    }
    return templates.TemplateResponse("admin/insurance_provider_detail.html", context)


@router.get("/insurance-providers/{insurance_provider_id}/edit", name="insurance_provider_edit_form")
def insurance_provider_edit_form(
    request: Request,
    insurance_provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Finance"]))
):
    """Show edit insurance provider form"""
    insurance_provider = insurance_provider_crud.get_insurance_provider(db, insurance_provider_id)
    if not insurance_provider:
        raise HTTPException(status_code=404, detail="Insurance provider not found")
    
    context = {
        "request": request,
        "title": f"Edit Insurance Provider: {insurance_provider.name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "insurance_provider": insurance_provider
    }
    return templates.TemplateResponse("admin/insurance_provider_form.html", context)


@router.post("/insurance-providers/{insurance_provider_id}/edit", name="insurance_provider_update", status_code=status.HTTP_302_FOUND)
def update_insurance_provider_form(
    request: Request,
    insurance_provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Finance"])),
    name: str = Form(...),
    code: Optional[str] = Form(None),
    contact_person: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    co_pay_rate: Optional[str] = Form(None),
    billing_email: Optional[str] = Form(None),
    billing_address: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(True)
):
    """Handle update insurance provider form submission"""
    try:
        insurance_provider_update = InsuranceProviderUpdate(
            name=name,
            code=code if code else None,
            contact_person=contact_person if contact_person else None,
            phone_number=phone_number if phone_number else None,
            email=email if email else None,
            address=address if address else None,
            co_pay_rate=co_pay_rate if co_pay_rate else None,
            billing_email=billing_email if billing_email else None,
            billing_address=billing_address if billing_address else None,
            is_active=is_active
        )
        
        insurance_provider = insurance_provider_crud.update_insurance_provider(
            db, insurance_provider_id, insurance_provider_update
        )
        if not insurance_provider:
            raise HTTPException(status_code=404, detail="Insurance provider not found")
        
        return RedirectResponse(
            url=str(request.url_for("insurance_provider_detail", insurance_provider_id=insurance_provider_id)) + "?status=updated",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("insurance_provider_edit_form", insurance_provider_id=insurance_provider_id)) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/insurance-providers/{insurance_provider_id}/delete", name="insurance_provider_delete", status_code=status.HTTP_302_FOUND)
def delete_insurance_provider_form(
    request: Request,
    insurance_provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Handle delete insurance provider form submission"""
    success = insurance_provider_crud.delete_insurance_provider(db, insurance_provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="Insurance provider not found")
    
    return RedirectResponse(
        url=str(request.url_for("insurance_providers_list")) + "?status=deleted",
        status_code=status.HTTP_302_FOUND
    )

