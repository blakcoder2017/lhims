"""
Disease Management API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from app.core.templates import templates
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.crud import disease_crud
from app.schemas.disease_schemas import DiseaseCreate, DiseaseUpdate

router = APIRouter(tags=["Diseases"])


@router.get("/admin/diseases", name="diseases_management")
def diseases_management(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Management"])),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200)
):
    """Disease management dashboard"""
    skip = (page - 1) * per_page
    
    diseases = disease_crud.get_diseases(db, skip=skip, limit=per_page, search=search)
    
    # Filter by category if provided
    if category:
        diseases = [d for d in diseases if (d.category.value if hasattr(d.category, 'value') else d.category) == category]
    
    # Get total count for pagination
    all_diseases = disease_crud.get_diseases(db, skip=0, limit=10000, search=search)
    if category:
        all_diseases = [d for d in all_diseases if (d.category.value if hasattr(d.category, 'value') else d.category) == category]
    total = len(all_diseases)
    
    context = {
        "request": request,
        "title": "Disease Management",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "diseases": diseases,
        "search": search,
        "category": category,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page
    }
    return templates.TemplateResponse("admin/diseases.html", context)


@router.get("/admin/diseases/create", name="create_disease_page")
def create_disease_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Form to create a new disease"""
    context = {
        "request": request,
        "title": "Create Disease",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "category": "other"
    }
    return templates.TemplateResponse("admin/create_disease.html", context)


@router.post("/admin/diseases/create", name="create_disease", status_code=302)
def create_disease(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    name: str = Form(...),
    code: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: str = Form("other"),
    dhis2_data_element_uid: Optional[str] = Form(None),
    dhis2_category_option_combo_uid: Optional[str] = Form(None)
):
    """Create a new disease"""
    try:
        disease = disease_crud.create_disease(
            db,
            name=name,
            code=code,
            description=description,
            category=category,
            dhis2_data_element_uid=dhis2_data_element_uid,
            dhis2_category_option_combo_uid=dhis2_category_option_combo_uid,
            created_by_id=current_user.id
        )
        return RedirectResponse(
            url=f"/admin/diseases?status=created&disease_id={disease.id}",
            status_code=302
        )
    except ValueError as e:
        context = {
            "request": request,
            "title": "Create Disease",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "error": str(e),
            "name": name,
            "code": code,
            "description": description,
            "category": category,
            "dhis2_data_element_uid": dhis2_data_element_uid,
            "dhis2_category_option_combo_uid": dhis2_category_option_combo_uid
        }
        return templates.TemplateResponse("admin/create_disease.html", context)
    except Exception as e:
        context = {
            "request": request,
            "title": "Create Disease",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "error": f"Error creating disease: {str(e)}",
            "name": name,
            "code": code,
            "description": description,
            "category": category,
            "dhis2_data_element_uid": dhis2_data_element_uid,
            "dhis2_category_option_combo_uid": dhis2_category_option_combo_uid
        }
        return templates.TemplateResponse("admin/create_disease.html", context)


@router.get("/admin/diseases/{disease_id}/edit", name="edit_disease_page")
def edit_disease_page(
    request: Request,
    disease_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Form to edit a disease"""
    disease = disease_crud.get_disease(db, disease_id)
    if not disease:
        raise HTTPException(status_code=404, detail="Disease not found")
    
    context = {
        "request": request,
        "title": "Edit Disease",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "disease": disease
    }
    return templates.TemplateResponse("admin/edit_disease.html", context)


@router.post("/admin/diseases/{disease_id}/edit", name="update_disease", status_code=302)
def update_disease(
    request: Request,
    disease_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    name: Optional[str] = Form(None),
    code: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    dhis2_data_element_uid: Optional[str] = Form(None),
    dhis2_category_option_combo_uid: Optional[str] = Form(None)
):
    """Update a disease"""
    try:
        update_data = {}
        if name is not None:
            update_data['name'] = name
        if code is not None:
            update_data['code'] = code
        if description is not None:
            update_data['description'] = description
        if category is not None:
            update_data['category'] = category
        if dhis2_data_element_uid is not None:
            update_data['dhis2_data_element_uid'] = dhis2_data_element_uid
        if dhis2_category_option_combo_uid is not None:
            update_data['dhis2_category_option_combo_uid'] = dhis2_category_option_combo_uid
        
        disease_update = DiseaseUpdate(**update_data)
        disease = disease_crud.update_disease(db, disease_id, **update_data)
        
        if not disease:
            raise HTTPException(status_code=404, detail="Disease not found")
        
        return RedirectResponse(
            url=f"/admin/diseases?status=updated&disease_id={disease_id}",
            status_code=302
        )
    except ValueError as e:
        disease = disease_crud.get_disease(db, disease_id)
        context = {
            "request": request,
            "title": "Edit Disease",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "disease": disease,
            "error": str(e)
        }
        return templates.TemplateResponse("admin/edit_disease.html", context)
    except Exception as e:
        disease = disease_crud.get_disease(db, disease_id)
        context = {
            "request": request,
            "title": "Edit Disease",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "disease": disease,
            "error": f"Error updating disease: {str(e)}"
        }
        return templates.TemplateResponse("admin/edit_disease.html", context)


@router.post("/admin/diseases/{disease_id}/delete", name="delete_disease", status_code=302)
def delete_disease(
    request: Request,
    disease_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Delete a disease (soft delete)"""
    success = disease_crud.delete_disease(db, disease_id)
    if not success:
        raise HTTPException(status_code=404, detail="Disease not found")
    
    return RedirectResponse(
        url=f"/admin/diseases?status=deleted&disease_id={disease_id}",
        status_code=302
    )


# API endpoint for searchable dropdown
@router.get("/api/diseases/search", name="search_diseases_api")
def search_diseases_api(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = Query(None)
):
    """API endpoint for searching diseases (for dropdowns)"""
    diseases = disease_crud.get_diseases(db, skip=0, limit=limit, search=q)
    
    if category:
        diseases = [d for d in diseases if (d.category.value if hasattr(d.category, 'value') else d.category) == category]
    
    return JSONResponse(content=[
        {
            "id": d.id,
            "name": d.name,
            "code": d.code,
            "category": d.category.value if hasattr(d.category, 'value') else d.category,
            "dhis2_data_element_uid": d.dhis2_data_element_uid
        }
        for d in diseases
    ])


# DHIMS2 Disease Mapping Management
@router.get("/admin/diseases/mappings", name="disease_mappings")
def disease_mappings_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "DHIMS2Preparer"])),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """DHIMS2 Disease Mapping management page"""
    diseases = disease_crud.get_diseases(db, skip=0, limit=500, search=search)
    
    if category:
        diseases = [d for d in diseases if (d.category.value if hasattr(d.category, 'value') else d.category) == category]
    
    # Get mapping statistics
    mapped_count = len([d for d in diseases if d.dhis2_data_element_uid])
    unmapped_count = len(diseases) - mapped_count
    
    context = {
        "request": request,
        "title": "DHIMS2 Disease Mappings",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "diseases": diseases,
        "mapped_count": mapped_count,
        "unmapped_count": unmapped_count,
        "search": search,
        "selected_category": category
    }
    return templates.TemplateResponse("admin/disease_mappings.html", context)

