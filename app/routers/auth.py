from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from app.core.templates import templates
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional, Annotated

from app.db.database import get_db
from app.core.security import create_access_token, verify_password
from app.schemas.token_schemas import Token
from app.models.user_models import User
from app.core.config import settings
from app.core.deps import get_current_user


router = APIRouter()
ui_router = APIRouter(tags=["UI Authentication"])


@router.post("/token", response_model=Token, name="generate_token")
def login(user_credentials: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)]):
    """
    Login endpoint that returns a token.
    For API usage, returns JSON. For form submissions, sets cookie and redirects.
    """
    user = db.query(User).filter(User.username == user_credentials.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")
    
    if not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")
    
    access_token = create_access_token(data={"user_id": user.id})
   
    return {"access_token": access_token, "token_type": "bearer"}


@ui_router.post("/login", name="login_post")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next_url: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Handle form-based login. Sets token as HTTP-only cookie and redirects.
    Supports 'next' parameter to redirect back to original URL.
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        context = {"request": request, "error": "Invalid Credentials"}
        return templates.TemplateResponse("auth/login.html", context, status_code=status.HTTP_401_UNAUTHORIZED)
    
    if not verify_password(password, user.hashed_password):
        context = {"request": request, "error": "Invalid Credentials"}
        return templates.TemplateResponse("auth/login.html", context, status_code=status.HTTP_401_UNAUTHORIZED)
    
    access_token = create_access_token(data={"user_id": user.id})
    
    # Determine redirect URL - use next parameter if provided, otherwise dashboard
    if next_url:
        redirect_url = next_url
    else:
        redirect_url = request.url_for("dashboard")
    
    # Create redirect response
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    
    # Set token as HTTP-only cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",  # Allow cookies for same-site requests including PUT
        path="/",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return response

@ui_router.get("/login", response_class=HTMLResponse, name="login")
async def get_login_page(request: Request, db: Session = Depends(get_db)):
    """Login page with hospital information"""
    from app.crud.hospital_settings_crud import get_hospital_settings
    
    settings = get_hospital_settings(db)
    # If no settings exist, create default
    if not settings:
        from app.crud.hospital_settings_crud import create_hospital_settings
        settings = create_hospital_settings(db)
    
    context = {
        "request": request,
        "error": None,
        "hospital_settings": settings
    }
    return templates.TemplateResponse("auth/login.html", context)

@ui_router.get("/logout", name="logout")
async def logout(request: Request):
    """
    Logout endpoint that clears the authentication cookie and redirects to login.
    """
    response = RedirectResponse(
        url=request.url_for("login"), 
        status_code=status.HTTP_302_FOUND
    )
    # Clear the access_token cookie
    response.delete_cookie(key="access_token")
    return response