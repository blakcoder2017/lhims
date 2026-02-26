"""
Procedure Catalog API Routes

Routes for procedure catalog management including CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from app.core.templates import templates
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from decimal import Decimal

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.procedure_catalog_models import ProcedureCatalog
from app.models.department_models import Department
from app.crud import procedure_catalog_crud
from app.crud import department_crud
from app.schemas.procedure_catalog_schemas import ProcedureCatalogCreate, ProcedureCatalogUpdate
from app.utils.charge_types_utils import get_charge_types

router = APIRouter(tags=["Procedure Catalog"])


# ==================== API Endpoints for Department Filter ====================

@router.get("/api/v1/procedures/departments", name="api_procedure_departments")
def get_procedure_departments(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all active departments for procedure dropdown filtering.
    Returns list of departments with id and name.
    """
    departments = db.query(Department).filter(
        Department.is_active == True
    ).order_by(Department.name).all()
    
    dept_list = [
        {
            "id": dept.id,
            "name": dept.name,
            "code": dept.code
        }
        for dept in departments
    ]
    
    return JSONResponse(content={"departments": dept_list})


@router.get("/api/v1/procedures/by-department/{department_id}", name="api_procedures_by_department")
def get_procedures_by_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get procedure catalog items filtered by department.
    Returns list of procedures belonging to the specified department.
    """
    # Verify department exists
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    
    # Get procedures for this department
    procedures, total_count = procedure_catalog_crud.search_procedure_catalog(
        db,
        skip=0,
        limit=500,  # High limit to get all procedures in department
        department_id=department_id,
        active_only=True
    )
    
    procedure_list = [
        {
            "id": proc.id,
            "name": proc.procedure_name,
            "code": proc.procedure_code,
            "cash_price": float(proc.cash_price) if proc.cash_price else 0,
            "procedure_type": proc.procedure_type,
            "charge_type": proc.charge_type,
            "department_id": proc.department_id
        }
        for proc in procedures
    ]
    
    return JSONResponse(content={
        "department": {
            "id": department.id,
            "name": department.name
        },
        "procedures": procedure_list,
        "total": total_count
    })


@router.get("/api/v1/procedures/all", name="api_all_procedures")
def get_all_procedures(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all active procedure catalog items (without department filter).
    Returns list of all procedures.
    """
    procedures, total_count = procedure_catalog_crud.search_procedure_catalog(
        db,
        skip=0,
        limit=500,
        active_only=True
    )
    
    procedure_list = [
        {
            "id": proc.id,
            "name": proc.procedure_name,
            "code": proc.procedure_code,
            "cash_price": float(proc.cash_price) if proc.cash_price else 0,
            "procedure_type": proc.procedure_type,
            "charge_type": proc.charge_type,
            "department_id": proc.department_id
        }
        for proc in procedures
    ]
    
    return JSONResponse(content={
        "procedures": procedure_list,
        "total": total_count
    })


@router.get("/procedures/catalog", name="procedure_catalog_dashboard")
def procedure_catalog_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor"])),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    procedure_type: Optional[str] = Query(None),
    charge_type: Optional[str] = Query(None),  # Filter by charge type
    department_id: Optional[int] = Query(None),  # Kept for reference
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
        charge_type=charge_type,  # Use charge type filter
        department_id=department_id,
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
    
    # Get charge types for filter (replaces department filter)
    charge_types = get_charge_types(db)
    
    # Get departments for reference
    departments = db.query(Department).filter(Department.is_active == True).order_by(Department.name).all()
    
    context = {
        "request": request,
        "title": "Procedure Catalog",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "procedures": procedures,
        "categories": categories,
        "procedure_types": procedure_types,
        "charge_types": charge_types,
        "departments": departments,
        "search": search,
        "category": category,
        "procedure_type_filter": procedure_type,
        "charge_type_filter": charge_type,
        "department_id_filter": department_id,
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
    departments = db.query(Department).filter(Department.is_active == True).order_by(Department.name).all()
    charge_types = get_charge_types(db)
    context = {
        "request": request,
        "title": "Create Procedure Type",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "departments": departments,
        "charge_types": charge_types
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
    charge_type: str = Form(...),  # Charge type for billing (required)
    department_id: Optional[str] = Form(None),  # Accept as string to handle empty values
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
        # Convert department_id from string to int or None
        dept_id = None
        if department_id and department_id.strip():
            try:
                dept_id = int(department_id.strip())
            except ValueError:
                pass  # Keep as None if conversion fails
        
        # Handle "None" string values - convert to actual None
        procedure_code_value = procedure_code
        if procedure_code_value == "None" or procedure_code_value == "":
            procedure_code_value = None
        procedure_category_value = procedure_category
        if procedure_category_value == "None" or procedure_category_value == "":
            procedure_category_value = None
        procedure_type_value = procedure_type
        if procedure_type_value == "None" or procedure_type_value == "":
            procedure_type_value = None
        description_value = description
        if description_value == "None" or description_value == "":
            description_value = None
        indication_value = indication
        if indication_value == "None" or indication_value == "":
            indication_value = None
        prep_value = preparation_instructions
        if prep_value == "None" or prep_value == "":
            prep_value = None
        post_care_value = post_procedure_care
        if post_care_value == "None" or post_care_value == "":
            post_care_value = None
        nhis_code_value = nhis_code
        if nhis_code_value == "None" or nhis_code_value == "":
            nhis_code_value = None
        anesthesia_value = typical_anesthesia_type
        if anesthesia_value == "None" or anesthesia_value == "":
            anesthesia_value = None
        location_value = typical_location
        if location_value == "None" or location_value == "":
            location_value = None
        
        procedure_data = ProcedureCatalogCreate(
            procedure_name=procedure_name,
            procedure_code=procedure_code_value,
            procedure_category=procedure_category_value,
            procedure_type=procedure_type_value,
            charge_type=charge_type,  # Charge type is required
            department_id=dept_id,
            description=description_value,
            indication=indication_value,
            preparation_instructions=prep_value,
            post_procedure_care=post_care_value,
            estimated_duration_minutes=int(estimated_duration_minutes.strip()) if estimated_duration_minutes and estimated_duration_minutes.strip() else None,
            typical_duration_minutes=int(typical_duration_minutes.strip()) if typical_duration_minutes and typical_duration_minutes.strip() else None,
            cash_price=Decimal(cash_price) if cash_price else None,
            cash_currency=cash_currency,
            nhis_covered=nhis_covered,
            nhis_code=nhis_code_value,
            nhis_price=Decimal(nhis_price) if nhis_price else None,
            private_insurance_covered=private_insurance_covered,
            private_insurance_price=Decimal(private_insurance_price) if private_insurance_price else None,
            requires_anesthesia=requires_anesthesia,
            typical_anesthesia_type=anesthesia_value,
            requires_operating_room=requires_operating_room,
            typical_location=location_value,
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
    except ValueError as e:
        # Handle duplicate procedure code errors
        return RedirectResponse(
            url=str(request.url_for("procedure_catalog_create_form")) + f"?error={str(e)}",
            status_code=302
        )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("procedure_catalog_create_form")) + f"?error={str(e)}",
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
    
    departments = db.query(Department).filter(Department.is_active == True).order_by(Department.name).all()
    charge_types = get_charge_types(db)
    
    context = {
        "request": request,
        "title": f"Procedure: {procedure.procedure_name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "procedure": procedure,
        "departments": departments,
        "charge_types": charge_types
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
    
    departments = db.query(Department).filter(Department.is_active == True).order_by(Department.name).all()
    charge_types = get_charge_types(db)
    
    context = {
        "request": request,
        "title": f"Edit Procedure: {procedure.procedure_name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "procedure": procedure,
        "departments": departments,
        "charge_types": charge_types
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
    charge_type: str = Form(...),  # Charge type for billing (required)
    department_id: Optional[str] = Form(None),  # Accept as string to handle empty values
    description: Optional[str] = Form(None),
    indication: Optional[str] = Form(None),
    preparation_instructions: Optional[str] = Form(None),
    post_procedure_care: Optional[str] = Form(None),
    estimated_duration_minutes: Optional[str] = Form(None),
    typical_duration_minutes: Optional[str] = Form(None),
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
        # Convert department_id from string to int or None
        dept_id = None
        if department_id and department_id.strip():
            try:
                dept_id = int(department_id.strip())
            except ValueError:
                pass  # Keep as None if conversion fails
        
        update_data = {}
        
        if procedure_name:
            update_data["procedure_name"] = procedure_name
        # Handle procedure_code: convert string "None" to actual None
        if procedure_code is not None:
            code_value = procedure_code
            if code_value == "None" or code_value == "":
                code_value = None
            update_data["procedure_code"] = code_value
        if procedure_category is not None:
            update_data["procedure_category"] = procedure_category if procedure_category else None
        if procedure_type is not None:
            update_data["procedure_type"] = procedure_type if procedure_type else None
        if charge_type is not None:
            update_data["charge_type"] = charge_type if charge_type else None
        if department_id is not None:
            update_data["department_id"] = dept_id
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
            code_value = nhis_code
            if code_value == "None" or code_value == "":
                code_value = None
            update_data["nhis_code"] = code_value
        if nhis_price is not None:
            update_data["nhis_price"] = Decimal(nhis_price) if nhis_price else None
        if private_insurance_covered is not None:
            update_data["private_insurance_covered"] = private_insurance_covered
        if private_insurance_price is not None:
            update_data["private_insurance_price"] = Decimal(private_insurance_price) if private_insurance_price else None
        if requires_anesthesia is not None:
            update_data["requires_anesthesia"] = requires_anesthesia
        if typical_anesthesia_type is not None:
            code_value = typical_anesthesia_type
            if code_value == "None" or code_value == "":
                code_value = None
            update_data["typical_anesthesia_type"] = code_value
        if requires_operating_room is not None:
            update_data["requires_operating_room"] = requires_operating_room
        if typical_location is not None:
            code_value = typical_location
            if code_value == "None" or code_value == "":
                code_value = None
            update_data["typical_location"] = code_value
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
    except ValueError as e:
        # Handle duplicate procedure code errors
        return RedirectResponse(
            url=str(request.url_for("procedure_catalog_edit_form", catalog_id=catalog_id)) + f"?error={str(e)}",
            status_code=302
        )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("procedure_catalog_edit_form", catalog_id=catalog_id)) + f"?error={str(e)}",
            status_code=302
        )

