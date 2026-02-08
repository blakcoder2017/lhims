from fastapi import Depends, HTTPException, status, Request, Cookie
from sqlalchemy.orm import Session
from typing import Union, List, Optional
from app.db.database import get_db
from app.models import user_models as models
from app.core.security import verify_access_token
from app.core.config import settings 


def get_current_user(
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # If no token in cookie, raise exception
    if not access_token:
        raise credentials_exception
    
    token_data = verify_access_token(access_token, credentials_exception)
    
    # Eagerly load the role relationship to avoid lazy loading issues
    from sqlalchemy.orm import joinedload
    user = db.query(models.User).options(joinedload(models.User.role)).filter(models.User.id == token_data.id).first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
        
    return user


def role_required(roles: Union[str, List[str]]):
 
    if isinstance(roles, str):
        roles = [roles]
        
    def role_checker(current_user: models.User = Depends(get_current_user)): 
        
        # Ensure role is loaded - handle potential None
        if not current_user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no role assigned. Please contact administrator."
            )
        
        user_role_name = current_user.role.name 
        
        if user_role_name == "Admin": 
            return current_user

        if user_role_name not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{user_role_name}' is not authorized. Required roles: {', '.join(roles)}"
            )
        return current_user

    return role_checker