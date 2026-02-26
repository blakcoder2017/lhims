from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from app.core.templates import templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from urllib.parse import quote

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.lab_catalog_models import LabTest
from app.models.lab_models import ReferenceRange
from app.crud import lab_catalog_crud
from app.schemas.lab_catalog_schemas import LabTestCreate, LabTestUpdate, ReferenceRangeCreate
from app.schemas.lab_catalog_schemas import LabTestUpdate, LabTestActivate

router = APIRouter(tags=["Lab Catalog"])


@router.get("/lab/tests", name="lab_tests_dashboard")
def lab_tests_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Lab Staff"])),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    include_inactive: bool = Query(False)
):
    """Lab test catalog dashboard"""
    tests = lab_catalog_crud.get_all_lab_tests(db, search=search, category=category, limit=100, include_inactive=include_inactive)
    
    # Get unique categories (only from active tests)
    categories = db.query(LabTest.test_category).filter(
        LabTest.is_active == True,
        LabTest.test_category.isnot(None)
    ).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    context = {
        "request": request,
        "title": "Lab Test Catalog",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "tests": tests,
        "categories": categories,
        "search": search,
        "category": category,
        "include_inactive": include_inactive
    }
    return templates.TemplateResponse("lab/test_catalog.html", context)


# Alias route for backward compatibility
@router.get("/lab/catalog", name="lab_catalog_dashboard")
def lab_catalog_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Lab Staff"]))
):
    """Redirect to lab tests dashboard"""
    return RedirectResponse(url="/lab/tests", status_code=302)


@router.get("/lab/tests/{test_id}", name="view_lab_test")
def view_lab_test(
    request: Request,
    test_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Lab Staff"]))
):
    """View lab test details (for both active and inactive tests)"""
    test = lab_catalog_crud.get_lab_test_by_id_any_status(db, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    reference_ranges = lab_catalog_crud.get_reference_ranges(db, test_id=test_id)
    
    context = {
        "request": request,
        "title": f"Test: {test.test_name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "test": test,
        "reference_ranges": reference_ranges
    }
    return templates.TemplateResponse("lab/test_detail.html", context)


@router.post("/lab/tests", name="create_lab_test", status_code=302)
def create_lab_test(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Lab Staff"])),
    test_name: str = Form(...),
    test_code: Optional[str] = Form(None),
    test_category: Optional[str] = Form(None),
    test_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    specimen_type: Optional[str] = Form(None),
    cost: Optional[str] = Form(None),
    nhis_covered: bool = Form(False)
):
    """Create a new lab test"""
    from decimal import Decimal
    from urllib.parse import quote
    
    test_data = LabTestCreate(
        test_name=test_name,
        test_code=test_code,
        test_category=test_category,
        test_type=test_type,
        description=description,
        specimen_type=specimen_type,
        cost=Decimal(cost) if cost else None,
        nhis_covered=nhis_covered
    )
    
    try:
        test = lab_catalog_crud.create_lab_test(db, test_data)
        return RedirectResponse(url=f"/lab/tests/{test.id}", status_code=302)
    except ValueError as e:
        # Redirect back with error message
        error_msg = quote(str(e))
        return RedirectResponse(
            url=f"/lab/tests?error={error_msg}",
            status_code=302
        )


@router.post("/lab/tests/{test_id}", name="update_lab_test", status_code=302)
def update_lab_test(
    request: Request,
    test_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    test_name: Optional[str] = Form(None),
    test_code: Optional[str] = Form(None),
    test_category: Optional[str] = Form(None),
    test_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    specimen_type: Optional[str] = Form(None),
    cost: Optional[str] = Form(None),
    nhis_covered: bool = Form(False)
):
    """Update an existing lab test"""
    from decimal import Decimal
    from urllib.parse import quote
    
    # Build update data - only include non-None values
    update_data = {}
    if test_name is not None:
        update_data["test_name"] = test_name
    if test_code is not None:
        update_data["test_code"] = test_code
    if test_category is not None:
        update_data["test_category"] = test_category
    if test_type is not None:
        update_data["test_type"] = test_type
    if description is not None:
        update_data["description"] = description
    if specimen_type is not None:
        update_data["specimen_type"] = specimen_type
    if cost is not None and cost != "":
        update_data["cost"] = Decimal(cost)
    update_data["nhis_covered"] = nhis_covered
    
    test_update = LabTestUpdate(**update_data)
    
    try:
        test = lab_catalog_crud.update_lab_test(db, test_id, test_update)
        if not test:
            return RedirectResponse(url=f"/lab/tests?error=Test not found", status_code=302)
        return RedirectResponse(url=f"/lab/tests/{test_id}?status=updated", status_code=302)
    except ValueError as e:
        error_msg = quote(str(e))
        return RedirectResponse(
            url=f"/lab/tests/{test_id}?error={error_msg}",
            status_code=302
        )


@router.post("/lab/tests/{test_id}/delete", name="delete_lab_test")
def delete_lab_test(
    test_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Soft delete a lab test with validation for related orders"""
    result = lab_catalog_crud.delete_lab_test(db, test_id)
    
    if not result.get("success"):
        error = result.get("error")
        if error == "not_found":
            raise HTTPException(status_code=404, detail=result.get("message", "Test not found"))
        elif error == "has_related_orders":
            # Redirect back with error message
            error_msg = quote(result.get("message", "Cannot delete test with related orders"))
            return RedirectResponse(
                url=f"/lab/tests?error={error_msg}",
                status_code=302
            )
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Delete failed"))
    
    # Success - redirect back with success message
    success_msg = quote(result.get("message", "Lab test deleted successfully"))
    return RedirectResponse(
        url=f"/lab/tests?success={success_msg}",
        status_code=302
    )


@router.post("/lab/tests/{test_id}/toggle-status", name="toggle_lab_test_status")
def toggle_lab_test_status(
    test_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    activate: bool = Form(...)
):
    """
    Activate or deactivate a lab test.
    
    Use activate=true to activate a test, activate=false to deactivate.
    """
    result = lab_catalog_crud.toggle_lab_test_status(db, test_id, activate)
    
    if not result.get("success"):
        error = result.get("error")
        if error == "not_found":
            raise HTTPException(status_code=404, detail=result.get("message", "Test not found"))
        elif error == "already_active":
            raise HTTPException(status_code=400, detail=result.get("message", "Test is already active"))
        elif error == "already_inactive":
            raise HTTPException(status_code=400, detail=result.get("message", "Test is already inactive"))
        elif error == "has_related_orders":
            # Redirect back with error message
            error_msg = quote(result.get("message", "Cannot deactivate test with related orders"))
            return RedirectResponse(
                url=f"/lab/tests?error={error_msg}",
                status_code=302
            )
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Operation failed"))
    
    # Success - redirect back with success message
    action = "activated" if activate else "deactivated"
    success_msg = quote(result.get("message", f"Lab test {action} successfully"))
    return RedirectResponse(
        url=f"/lab/tests?success={success_msg}",
        status_code=302
    )


# --- API Endpoints for Autocomplete Search ---

@router.get("/api/v1/lab/tests/search", name="lab_tests_search_api")
def search_lab_tests_api(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Search query (test name or code)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return")
):
    """
    Search lab tests by name or code. Used for autocomplete dropdown in lab order forms.
    Returns JSON array of matching tests with id, name, code, category, and cost.
    """
    query = db.query(LabTest).filter(LabTest.is_active == True)
    
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            (LabTest.test_name.ilike(search_term)) | 
            (LabTest.test_code.ilike(search_term))
        )
    
    if category:
        query = query.filter(LabTest.test_category == category)
    
    tests = query.order_by(LabTest.test_name).limit(limit).all()
    
    return [
        {
            "id": test.id,
            "test_name": test.test_name,
            "test_code": test.test_code,
            "test_category": test.test_category,
            "cost": float(test.cost) if test.cost else 0
        }
        for test in tests
    ]


@router.get("/api/v1/lab/tests/categories", name="lab_tests_categories_api")
def get_lab_test_categories_api(db: Session = Depends(get_db)):
    """
    Get all unique test categories with counts. Used for category filter buttons.
    """
    from sqlalchemy import func
    
    results = db.query(
        LabTest.test_category,
        func.count(LabTest.id).label('count')
    ).filter(
        LabTest.is_active == True,
        LabTest.test_category.isnot(None)
    ).group_by(LabTest.test_category).all()
    
    return [
        {"category": r[0], "count": r[1]}
        for r in results if r[0]
    ]


@router.get("/lab/reference-ranges", name="reference_ranges_dashboard")
def reference_ranges_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Lab Staff"])),
    test_id: Optional[int] = Query(None)
):
    """Reference ranges management dashboard"""
    ranges = lab_catalog_crud.get_reference_ranges(db, test_id=test_id)
    tests = lab_catalog_crud.get_lab_tests(db, limit=200)
    
    context = {
        "request": request,
        "title": "Reference Ranges",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "ranges": ranges,
        "tests": tests,
        "test_id": test_id
    }
    return templates.TemplateResponse("lab/reference_ranges.html", context)


@router.post("/lab/reference-ranges", name="create_reference_range", status_code=302)
def create_reference_range(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Lab Staff"])),
    test_id: Optional[int] = Form(None),
    test_name: str = Form(...),
    normal_min: Optional[str] = Form(None),
    normal_max: Optional[str] = Form(None),
    critical_low: Optional[str] = Form(None),
    critical_high: Optional[str] = Form(None),
    unit: Optional[str] = Form(None)
):
    """Create a reference range"""
    from decimal import Decimal
    
    range_data = ReferenceRangeCreate(
        test_id=test_id,
        test_name=test_name,
        normal_min=Decimal(normal_min) if normal_min else None,
        normal_max=Decimal(normal_max) if normal_max else None,
        critical_low=Decimal(critical_low) if critical_low else None,
        critical_high=Decimal(critical_high) if critical_high else None,
        unit=unit
    )
    
    range_obj = lab_catalog_crud.create_reference_range(db, range_data)
    return RedirectResponse(url="/lab/reference-ranges?status=created", status_code=302)

