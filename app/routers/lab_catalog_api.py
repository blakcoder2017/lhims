from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.lab_catalog_models import LabTest
from app.models.lab_models import ReferenceRange
from app.crud import lab_catalog_crud
from app.schemas.lab_catalog_schemas import LabTestCreate, ReferenceRangeCreate

router = APIRouter(tags=["Lab Catalog"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/lab/tests", name="lab_tests_dashboard")
def lab_tests_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Lab Staff"])),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None)
):
    """Lab test catalog dashboard"""
    tests = lab_catalog_crud.get_lab_tests(db, search=search, category=category, limit=100)
    
    # Get unique categories
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
        "category": category
    }
    return templates.TemplateResponse("lab/test_catalog.html", context)


@router.get("/lab/tests/{test_id}", name="view_lab_test")
def view_lab_test(
    request: Request,
    test_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Lab Staff"]))
):
    """View lab test details"""
    test = lab_catalog_crud.get_lab_test(db, test_id)
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
    
    test = lab_catalog_crud.create_lab_test(db, test_data)
    return RedirectResponse(url=f"/lab/tests/{test.id}", status_code=302)


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

