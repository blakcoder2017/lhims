"""
Procedure Catalog API Routes

Routes for procedure catalog management including CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.procedure_catalog_models import ProcedureCatalog
from app.crud import procedure_catalog_crud
from app.schemas.procedure_catalog_schemas import ProcedureCatalogCreate, ProcedureCatalogUpdate

router = APIRouter(tags=["Procedure Catalog"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/procedures/catalog", name="procedure_catalog_dashboard")
def procedure_catalog_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor"])),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    procedure_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """Procedure catalog dashboard"""
    skip = (page - 1) * per_page
    
    procedures, total_count = procedure_catalog_crud.search_procedure_catalog(
        db,
        query=search,
        skip=skip,
        limit=per_page,
        procedure_category=category,
        procedure_type=procedure_type,
        active_only=True
    )
    
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    # Get unique categories
    categories = db.query(ProcedureCatalog.procedure_category).filter(
        ProcedureCatalog.is_active == True,
        ProcedureCatalog.procedure_category.isnot(None)
    ).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    # Get unique procedure types
    procedure_types = db.query(ProcedureCatalog.procedure_type).filter(
        ProcedureCatalog.is_active == True,
        ProcedureCatalog.procedure_type.isnot(None)
    ).distinct().all()
    procedure_types = [pt[0] for pt in procedure_types if pt[0]]
    
    context = {
        "request": request,
        "title": "Procedure Catalog",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "procedures": procedures,
        "categories": categories,
        "procedure_types": procedure_types,
        "search": search,
        "category": category,
        "procedure_type_filter": procedure_type,
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages
    }
    return templates.TemplateResponse("procedures/procedure_catalog.html", context)


@router.get("/procedures/catalog/create", name="procedure_catalog_create_form")
def procedure_catalog_create_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Form to create a new procedure catalog entry"""
    context = {
        "request": request,
        "title": "Create Procedure Type",
        "current_user": current_user,
        "user_role": current_user.role.name
    }
    return templates.TemplateResponse("procedures/procedure_catalog_form.html", context)


@router.post("/procedures/catalog/create", name="create_procedure_catalog", status_code=302)
def create_procedure_catalog(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    procedure_name: str = Form(...),
    procedure_code: Optional[str] = Form(None),
    procedure_category: Optional[str] = Form(None),
    procedure_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    indication: Optional[str] = Form(None),
    preparation_instructions: Optional[str] = Form(None),
    post_procedure_care: Optional[str] = Form(None),
    estimated_duration_minutes: Optional[str] = Form(None),
    typical_duration_minutes: Optional[str] = Form(None),
    cash_price: Optional[str] = Form(None),
    cash_currency: Optional[str] = Form("GHS"),
    nhis_covered: bool = Form(False),
    nhis_code: Optional[str] = Form(None),
    nhis_price: Optional[str] = Form(None),
    private_insurance_covered: bool = Form(False),
    private_insurance_price: Optional[str] = Form(None),
    requires_anesthesia: bool = Form(False),
    typical_anesthesia_type: Optional[str] = Form(None),
    requires_operating_room: bool = Form(False),
    typical_location: Optional[str] = Form(None),
    is_specialized: bool = Form(False),
    requires_consultation: bool = Form(False)
):
    """Create a new procedure catalog entry"""
    try:
        procedure_data = ProcedureCatalogCreate(
            procedure_name=procedure_name,
            procedure_code=procedure_code if procedure_code else None,
            procedure_category=procedure_category if procedure_category else None,
            procedure_type=procedure_type if procedure_type else None,
            description=description if description else None,
            indication=indication if indication else None,
            preparation_instructions=preparation_instructions if preparation_instructions else None,
            post_procedure_care=post_procedure_care if post_procedure_care else None,
            estimated_duration_minutes=int(estimated_duration_minutes.strip()) if estimated_duration_minutes and estimated_duration_minutes.strip() else None,
            typical_duration_minutes=int(typical_duration_minutes.strip()) if typical_duration_minutes and typical_duration_minutes.strip() else None,
            cash_price=Decimal(cash_price) if cash_price else None,
            cash_currency=cash_currency,
            nhis_covered=nhis_covered,
            nhis_code=nhis_code if nhis_code else None,
            nhis_price=Decimal(nhis_price) if nhis_price else None,
            private_insurance_covered=private_insurance_covered,
            private_insurance_price=Decimal(private_insurance_price) if private_insurance_price else None,
            requires_anesthesia=requires_anesthesia,
            typical_anesthesia_type=typical_anesthesia_type if typical_anesthesia_type else None,
            requires_operating_room=requires_operating_room,
            typical_location=typical_location if typical_location else None,
            is_specialized=is_specialized,
            requires_consultation=requires_consultation
        )
        
        procedure = procedure_catalog_crud.create_procedure_catalog(
            db, 
            procedure_data,
            created_by_id=current_user.id
        )
        return RedirectResponse(
            url=request.url_for("view_procedure_catalog", catalog_id=procedure.id),
            status_code=302
        )
    except Exception as e:
        return RedirectResponse(
            url=request.url_for("procedure_catalog_create_form") + f"?error={str(e)}",
            status_code=302
        )


@router.get("/procedures/catalog/{catalog_id}", name="view_procedure_catalog")
def view_procedure_catalog(
    request: Request,
    catalog_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor"]))
):
    """View procedure catalog entry details"""
    procedure = procedure_catalog_crud.get_procedure_catalog(db, catalog_id)
    if not procedure:
        raise HTTPException(status_code=404, detail="Procedure catalog entry not found")
    
    context = {
        "request": request,
        "title": f"Procedure: {procedure.procedure_name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "procedure": procedure
    }
    return templates.TemplateResponse("procedures/procedure_catalog_detail.html", context)


@router.get("/procedures/catalog/{catalog_id}/edit", name="procedure_catalog_edit_form")
def procedure_catalog_edit_form(
    request: Request,
    catalog_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Form to edit a procedure catalog entry"""
    procedure = procedure_catalog_crud.get_procedure_catalog(db, catalog_id)
    if not procedure:
        raise HTTPException(status_code=404, detail="Procedure catalog entry not found")
    
    context = {
        "request": request,
        "title": f"Edit Procedure: {procedure.procedure_name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "procedure": procedure
    }
    return templates.TemplateResponse("procedures/procedure_catalog_form.html", context)


@router.post("/procedures/catalog/{catalog_id}/update", name="update_procedure_catalog", status_code=302)
def update_procedure_catalog(
    request: Request,
    catalog_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    procedure_name: Optional[str] = Form(None),
    procedure_code: Optional[str] = Form(None),
    procedure_category: Optional[str] = Form(None),
    procedure_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    indication: Optional[str] = Form(None),
    preparation_instructions: Optional[str] = Form(None),
    post_procedure_care: Optional[str] = Form(None),
    estimated_duration_minutes: Optional[int] = Form(None),
    typical_duration_minutes: Optional[int] = Form(None),
    cash_price: Optional[str] = Form(None),
    cash_currency: Optional[str] = Form(None),
    nhis_covered: Optional[bool] = Form(None),
    nhis_code: Optional[str] = Form(None),
    nhis_price: Optional[str] = Form(None),
    private_insurance_covered: Optional[bool] = Form(None),
    private_insurance_price: Optional[str] = Form(None),
    requires_anesthesia: Optional[bool] = Form(None),
    typical_anesthesia_type: Optional[str] = Form(None),
    requires_operating_room: Optional[bool] = Form(None),
    typical_location: Optional[str] = Form(None),
    is_specialized: Optional[bool] = Form(None),
    requires_consultation: Optional[bool] = Form(None),
    is_active: Optional[bool] = Form(None)
):
    """Update a procedure catalog entry"""
    try:
        update_data = {}
        
        if procedure_name:
            update_data["procedure_name"] = procedure_name
        if procedure_code is not None:
            update_data["procedure_code"] = procedure_code if procedure_code else None
        if procedure_category is not None:
            update_data["procedure_category"] = procedure_category if procedure_category else None
        if procedure_type is not None:
            update_data["procedure_type"] = procedure_type if procedure_type else None
        if description is not None:
            update_data["description"] = description if description else None
        if indication is not None:
            update_data["indication"] = indication if indication else None
        if preparation_instructions is not None:
            update_data["preparation_instructions"] = preparation_instructions if preparation_instructions else None
        if post_procedure_care is not None:
            update_data["post_procedure_care"] = post_procedure_care if post_procedure_care else None
        if estimated_duration_minutes is not None:
            update_data["estimated_duration_minutes"] = int(estimated_duration_minutes.strip()) if estimated_duration_minutes and estimated_duration_minutes.strip() else None
        if typical_duration_minutes is not None:
            update_data["typical_duration_minutes"] = int(typical_duration_minutes.strip()) if typical_duration_minutes and typical_duration_minutes.strip() else None
        if cash_price is not None:
            update_data["cash_price"] = Decimal(cash_price) if cash_price else None
        if cash_currency:
            update_data["cash_currency"] = cash_currency
        if nhis_covered is not None:
            update_data["nhis_covered"] = nhis_covered
        if nhis_code is not None:
            update_data["nhis_code"] = nhis_code if nhis_code else None
        if nhis_price is not None:
            update_data["nhis_price"] = Decimal(nhis_price) if nhis_price else None
        if private_insurance_covered is not None:
            update_data["private_insurance_covered"] = private_insurance_covered
        if private_insurance_price is not None:
            update_data["private_insurance_price"] = Decimal(private_insurance_price) if private_insurance_price else None
        if requires_anesthesia is not None:
            update_data["requires_anesthesia"] = requires_anesthesia
        if typical_anesthesia_type is not None:
            update_data["typical_anesthesia_type"] = typical_anesthesia_type if typical_anesthesia_type else None
        if requires_operating_room is not None:
            update_data["requires_operating_room"] = requires_operating_room
        if typical_location is not None:
            update_data["typical_location"] = typical_location if typical_location else None
        if is_specialized is not None:
            update_data["is_specialized"] = is_specialized
        if requires_consultation is not None:
            update_data["requires_consultation"] = requires_consultation
        if is_active is not None:
            update_data["is_active"] = is_active
        
        procedure_update = ProcedureCatalogUpdate(**update_data)
        procedure = procedure_catalog_crud.update_procedure_catalog(
            db,
            catalog_id,
            procedure_update,
            updated_by_id=current_user.id
        )
        
        if not procedure:
            raise HTTPException(status_code=404, detail="Procedure catalog entry not found")
        
        return RedirectResponse(
            url=request.url_for("view_procedure_catalog", catalog_id=catalog_id),
            status_code=302
        )
    except Exception as e:
        return RedirectResponse(
            url=request.url_for("procedure_catalog_edit_form", catalog_id=catalog_id) + f"?error={str(e)}",
            status_code=302
        )

