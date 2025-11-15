"""
Doctor List API Routes

Routes for viewing and searching doctors with pagination and filtering.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.models.user_models import User
from app.crud import user_crud

router = APIRouter(
    prefix="",
    tags=["Doctors"]
)

templates = Jinja2Templates(directory="app/templates")


@router.get("/doctors/list", name="doctors_list")
def doctors_list_page(
    request: Request,
    query: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Doctor list page with pagination, filtering, and search functionality.
    Shows all doctors (users with Doctor role only, excluding nurses).
    """
    # Calculate skip
    skip = (page - 1) * per_page
    
    # Get doctors with pagination
    doctors, total_count = user_crud.get_doctors(
        db,
        skip=skip,
        limit=per_page,
        search=query
    )
    
    # Calculate pagination info
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    context = {
        "request": request,
        "title": "Doctors List",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "doctors": doctors,
        "search_query": query or "",
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages,
    }
    
    return templates.TemplateResponse("admin/doctors_list.html", context)

