"""
Password Reset API Routes
Handles forgot password and password reset functionality
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from urllib.parse import quote

from app.db.database import get_db
from app.models.user_models import User
from app.services.password_reset_service import (
    create_email_reset_token,
    create_sms_reset_token,
    verify_reset_token,
    verify_otp,
    mark_token_used
)
from app.services.email_service import send_password_reset_email
from app.services.sms_service import send_sms_otp

router = APIRouter(tags=["Password Reset"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/forgot-password", name="forgot_password_page")
def forgot_password_page(request: Request):
    """Forgot password page"""
    status = request.query_params.get("status")
    error = request.query_params.get("error")
    
    context = {
        "request": request,
        "title": "Forgot Password",
        "status": status,
        "error": error
    }
    return templates.TemplateResponse("auth/forgot_password.html", context)


@router.post("/forgot-password", name="request_password_reset", status_code=302)
def request_password_reset(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    reset_method: str = Form("sms"),  # 'sms' or 'email'
    phone_number: Optional[str] = Form(None)
):
    """Request password reset"""
    user = db.query(User).filter(User.username == username).first()
    
    # Don't reveal if user exists (security best practice)
    if not user:
        return RedirectResponse(
            url=str(request.url_for("forgot_password_page")) + "?status=sent",
            status_code=302
        )
    
    try:
        if reset_method == "email":
            if not user.email:
                return RedirectResponse(
                    url=str(request.url_for("forgot_password_page")) + "?error=" + quote("No email address on file"),
                    status_code=302
                )
            reset_token = create_email_reset_token(db, user, user.email)
            reset_link = f"{request.base_url}reset-password?token={reset_token.token}"
            email_sent = send_password_reset_email(user.email, reset_link, user.full_name or user.username)
            
            if not email_sent:
                # Still redirect to success to not reveal email issues
                return RedirectResponse(
                    url=str(request.url_for("forgot_password_page")) + "?status=sent",
                    status_code=302
                )
        
        elif reset_method == "sms":
            if not phone_number:
                return RedirectResponse(
                    url=str(request.url_for("forgot_password_page")) + "?error=" + quote("Phone number required for SMS reset"),
                    status_code=302
                )
            reset_token = create_sms_reset_token(db, user, phone_number)
            sms_sent = send_sms_otp(phone_number, reset_token.otp_code, user.full_name or user.username)
            
            # Redirect to OTP verification page
            return RedirectResponse(
                url=str(request.url_for("verify_otp_page")) + f"?user_id={user.id}",
                status_code=302
            )
        else:
            return RedirectResponse(
                url=str(request.url_for("forgot_password_page")) + "?error=" + quote("Invalid reset method"),
                status_code=302
            )
        
        return RedirectResponse(
            url=str(request.url_for("forgot_password_page")) + "?status=sent",
            status_code=302
        )
    except Exception as e:
        # Log error but don't reveal details to user
        print(f"Error in password reset request: {e}")
        return RedirectResponse(
            url=str(request.url_for("forgot_password_page")) + "?status=sent",
            status_code=302
        )


@router.get("/verify-otp", name="verify_otp_page")
def verify_otp_page(
    request: Request,
    db: Session = Depends(get_db),
    user_id: Optional[int] = Query(None),
    error: Optional[str] = Query(None)
):
    """OTP verification page for SMS reset"""
    if not user_id:
        return RedirectResponse(
            url=str(request.url_for("forgot_password_page")) + "?error=" + quote("Invalid request"),
            status_code=302
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(
            url=str(request.url_for("forgot_password_page")) + "?error=" + quote("User not found"),
            status_code=302
        )
    
    context = {
        "request": request,
        "title": "Verify OTP",
        "user_id": user_id,
        "username": user.username,
        "error": error
    }
    return templates.TemplateResponse("auth/verify_otp.html", context)


@router.post("/verify-otp", name="verify_otp", status_code=302)
def verify_otp_post(
    request: Request,
    db: Session = Depends(get_db),
    user_id: int = Form(...),
    otp: str = Form(...)
):
    """Verify OTP and redirect to password reset"""
    reset_token = verify_otp(db, user_id, otp)
    
    if not reset_token:
        return RedirectResponse(
            url=str(request.url_for("verify_otp_page")) + f"?user_id={user_id}&error=" + quote("Invalid or expired OTP"),
            status_code=302
        )
    
    # Redirect to password reset page with OTP
    return RedirectResponse(
        url=str(request.url_for("reset_password_page")) + f"?user_id={user_id}&otp={otp}",
        status_code=302
    )


@router.get("/reset-password", name="reset_password_page")
def reset_password_page(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    otp: Optional[str] = Query(None),
    error: Optional[str] = Query(None)
):
    """Password reset page"""
    reset_token = None
    
    if token:
        reset_token = verify_reset_token(db, token)
        if not reset_token:
            context = {
                "request": request,
                "title": "Reset Password",
                "error": "Invalid or expired reset token. Please request a new password reset.",
                "token": None
            }
            return templates.TemplateResponse("auth/reset_password.html", context)
    
    elif user_id and otp:
        reset_token = verify_otp(db, user_id, otp)
        if not reset_token:
            context = {
                "request": request,
                "title": "Reset Password",
                "error": "Invalid or expired OTP. Please request a new password reset.",
                "user_id": None,
                "otp": None
            }
            return templates.TemplateResponse("auth/reset_password.html", context)
    
    if not reset_token:
        context = {
            "request": request,
            "title": "Reset Password",
            "error": error or "Missing reset token or OTP. Please request a new password reset.",
            "token": None
        }
        return templates.TemplateResponse("auth/reset_password.html", context)
    
    context = {
        "request": request,
        "title": "Reset Password",
        "token": token,
        "user_id": user_id,
        "otp": otp,
        "error": error,
        "reset_token": reset_token
    }
    return templates.TemplateResponse("auth/reset_password.html", context)


@router.post("/reset-password", name="reset_password", status_code=302)
def reset_password(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Form(None),
    user_id: Optional[int] = Form(None),
    otp: Optional[str] = Form(None),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    """Reset password"""
    # Validation
    if new_password != confirm_password:
        error_param = quote("New password and confirmation do not match")
        if token:
            return RedirectResponse(
                url=str(request.url_for("reset_password_page")) + f"?token={token}&error={error_param}",
                status_code=302
            )
        elif user_id and otp:
            return RedirectResponse(
                url=str(request.url_for("reset_password_page")) + f"?user_id={user_id}&otp={otp}&error={error_param}",
                status_code=302
            )
    
    if len(new_password) < 6:
        error_param = quote("Password must be at least 6 characters long")
        if token:
            return RedirectResponse(
                url=str(request.url_for("reset_password_page")) + f"?token={token}&error={error_param}",
                status_code=302
            )
        elif user_id and otp:
            return RedirectResponse(
                url=str(request.url_for("reset_password_page")) + f"?user_id={user_id}&otp={otp}&error={error_param}",
                status_code=302
            )
    
    # Verify token
    reset_token = None
    if token:
        reset_token = verify_reset_token(db, token)
    elif user_id and otp:
        reset_token = verify_otp(db, user_id, otp)
    
    if not reset_token:
        return RedirectResponse(
            url=str(request.url_for("forgot_password_page")) + "?error=" + quote("Invalid or expired reset token"),
            status_code=302
        )
    
    # Update password
    try:
        user = db.query(User).filter(User.id == reset_token.user_id).first()
        if not user:
            return RedirectResponse(
                url=str(request.url_for("forgot_password_page")) + "?error=" + quote("User not found"),
                status_code=302
            )
        
        user.set_password(new_password)
        mark_token_used(db, reset_token.id)
        db.commit()
        
        return RedirectResponse(
            url=str(request.url_for("login")) + "?status=password_reset",
            status_code=302
        )
    except Exception as e:
        db.rollback()
        print(f"Error resetting password: {e}")
        return RedirectResponse(
            url=str(request.url_for("forgot_password_page")) + "?error=" + quote("An error occurred. Please try again."),
            status_code=302
        )

