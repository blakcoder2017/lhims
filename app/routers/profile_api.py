"""
User Profile Management Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from app.core.templates import templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.core.security import verify_password, get_password_hash

router = APIRouter(tags=["Profile"])


@router.get("/profile", name="view_profile")
def view_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """View user profile"""
    context = {
        "request": request,
        "title": "My Profile",
        "current_user": current_user,
        "user_role": current_user.role.name
    }
    return templates.TemplateResponse("profile/view_profile.html", context)


@router.get("/profile/edit", name="edit_profile")
def edit_profile_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Edit profile page"""
    context = {
        "request": request,
        "title": "Edit Profile",
        "current_user": current_user,
        "user_role": current_user.role.name
    }
    return templates.TemplateResponse("profile/edit_profile.html", context)


@router.post("/profile/edit", name="update_profile", status_code=302)
def update_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    full_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    current_password: Optional[str] = Form(None),
    new_password: Optional[str] = Form(None),
    confirm_password: Optional[str] = Form(None)
):
    """Update user profile"""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    errors = []
    
    # Update full name
    if full_name is not None:
        user.full_name = full_name.strip() if full_name else None
    
    # Update email (check for uniqueness)
    if email is not None:
        email = email.strip() if email else None
        if email:
            # Check if email is already taken by another user
            existing_user = db.query(User).filter(
                User.email == email,
                User.id != user.id
            ).first()
            if existing_user:
                errors.append("Email is already in use by another user")
            else:
                user.email = email
    
    # Handle password change
    if new_password:
        if not current_password:
            errors.append("Current password is required to change password")
        elif not verify_password(current_password, user.hashed_password):
            errors.append("Current password is incorrect")
        elif new_password != confirm_password:
            errors.append("New password and confirmation do not match")
        elif len(new_password) < 6:
            errors.append("New password must be at least 6 characters long")
        else:
            user.set_password(new_password)
    
    if errors:
        context = {
            "request": request,
            "title": "Edit Profile",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "errors": errors,
            "full_name": full_name or user.full_name,
            "email": email or user.email
        }
        return templates.TemplateResponse("profile/edit_profile.html", context)
    
    try:
        db.commit()
        db.refresh(user)
        return RedirectResponse(
            url=str(request.url_for("view_profile")) + "?status=updated",
            status_code=302
        )
    except Exception as e:
        db.rollback()
        context = {
            "request": request,
            "title": "Edit Profile",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "errors": [f"An error occurred: {str(e)}"],
            "full_name": full_name or user.full_name,
            "email": email or user.email
        }
        return templates.TemplateResponse("profile/edit_profile.html", context)

