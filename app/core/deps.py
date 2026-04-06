from fastapi import Depends, HTTPException, status, Request, Cookie
from sqlalchemy.orm import Session
from typing import Union, List, Optional
import logging
from app.db.database import get_db
from app.models import user_models as models
from app.core.security import verify_access_token
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_user_permissions(user) -> List[str]:
    """
    Get all permissions for a user from the database only.
    Permissions are assigned via the admin panel (/admin/roles/permissions)
    
    Args:
        user: User model instance with loaded role and permissions
        
    Returns:
        List of permission names
    """
    permissions = set()
    
    # Get permissions from database
    if user.role and user.role.permissions:
        permissions = [perm.name for perm in user.role.permissions]
    
    return list(permissions)


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
        logger.warning("Authentication failed: No access token found in cookie")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please login again.",
            headers={"WWW-Authenticate": "Bearer", "X-Redirect-Url": "/login"},
        )
    
    # Log token info for debugging (first 20 chars only for security)
    logger.debug(f"Verifying token: {access_token[:20]}...")
    
    try:
        token_data = verify_access_token(access_token, credentials_exception)
        logger.debug(f"Token verified successfully for user_id: {token_data.id}")
    except HTTPException as e:
        logger.warning(f"Token verification failed: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {str(e)}")
        raise credentials_exception
    
    # Eagerly load the role and permissions relationship to avoid lazy loading issues
    from sqlalchemy.orm import joinedload
    user = db.query(models.User).options(
        joinedload(models.User.role),
        joinedload(models.User.role).joinedload(models.Role.permissions)
    ).filter(models.User.id == token_data.id).first()
    
    if user is None:
        logger.warning(f"User not found for token user_id: {token_data.id}")
        raise credentials_exception
    
    if not user.is_active:
        logger.warning(f"User account is inactive: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    logger.debug(f"User authenticated successfully: {user.username} (role: {user.role.name if user.role else 'None'})")
    return user


def role_required(roles: Union[str, List[str]]):
    """
    Dependency to check if the user has one of the required roles.
    
    If the role has NO permissions assigned in the admin panel,
    the user will be denied access (except Admin which has full access).
    
    Management role is treated similarly to Admin for most routes,
    but settings routes remain Admin-only.
    """
    if isinstance(roles, str):
        roles = [roles]
    
    # Settings routes that should remain Admin-only
    admin_only_routes = [
        "/admin/settings",
        "/admin/roles/permissions",
        "/api/v1/admin/roles/permissions",
    ]
    
    def role_checker(request: Request, current_user: models.User = Depends(get_current_user)): 
        
        # Ensure role is loaded - handle potential None
        if not current_user.role:
            logger.warning(f"User {current_user.username} has no role assigned")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this module. Please contact system administrator."
            )
        
        user_role_name = current_user.role.name 
        
        # Admin has full access regardless of permissions
        if user_role_name.lower() == "admin": 
            return current_user
        
        # Management role has broad access similar to Admin (except settings)
        if user_role_name.lower() == "management":
            # Check if this is a settings/admin-only route
            request_path = request.url.path if request else ""
            for admin_route in admin_only_routes:
                if request_path.startswith(admin_route):
                    logger.warning(f"Management user {current_user.username} attempted to access admin-only route {request_path}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You do not have permission to access this module. Please contact system administrator."
                    )
            # Management has access to all other routes that require Admin
            if "Admin" in roles:
                return current_user
            # For non-Admin roles, check if Management is included or grant access
            if "Management" in roles:
                return current_user
            # Grant Management access to common operational roles
            operational_roles = ["Front Office", "Finance", "Doctor", "Nurse", "Clinician", 
                                "Pharmacy Staff", "Lab Staff", "Radiology Staff", "Midwife"]
            for op_role in operational_roles:
                if op_role in roles:
                    return current_user
            # Default: allow Management through for routes that specify multiple roles
            if any(r in ["Admin", "Finance", "Management", "Doctor", "Nurse", "Front Office", 
                       "Clinician", "Pharmacy Staff", "Lab Staff", "Radiology Staff", "Midwife"] for r in roles):
                return current_user
        
        # Case-insensitive role check
        allowed_roles_lower = [role.lower() for role in roles]
        if user_role_name.lower() not in allowed_roles_lower:
            logger.warning(f"User {current_user.username} with role {user_role_name} not in required roles {roles}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this module. Please contact system administrator."
            )
        
        # Check if the role has any permissions assigned in admin panel
        user_permissions = get_user_permissions(current_user)
        if not user_permissions:
            logger.warning(f"User {current_user.username} with role {user_role_name} has no permissions assigned")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role has no permissions assigned. Please contact system administrator."
            )
        
        return current_user

    return role_checker


def permission_required(permissions: Union[str, List[str]]):
    """
    Dependency to check if the user has required permissions.
    
    Permissions are assigned via the admin panel (/admin/roles/permissions)
    
    Args:
        permissions: Single permission string or list of permission strings.
                    User needs ALL specified permissions to access the endpoint.
    
    Usage:
        @router.get("/", dependencies=[Depends(permission_required("patient_view"))])
        or
        @router.get("/", dependencies=[Depends(permission_required(["patient_view", "patient_edit"]))])
    """
    if isinstance(permissions, str):
        permissions = [permissions]
    
    def permission_checker(current_user: models.User = Depends(get_current_user)):
        # Ensure role is loaded
        if not current_user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has no role assigned. Please contact system administrator."
            )
        
        user_role_name = current_user.role.name
        
        # Admin has full access regardless of permissions
        if user_role_name.lower() == "admin":
            return current_user
        
        # Get user's permissions from database
        user_permissions = get_user_permissions(current_user)
        
        # Check if user has all required permissions
        missing_permissions = []
        for perm in permissions:
            if perm not in user_permissions:
                missing_permissions.append(perm)
        
        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(missing_permissions)}. Please contact system administrator."
            )
        
        return current_user
    
    return permission_checker


def permission_required_any(permissions: Union[str, List[str]]):
    """
    Dependency to check if the user has ANY of the required permissions.
    
    Permissions are assigned via the admin panel (/admin/roles/permissions)
    
    Args:
        permissions: Single permission string or list of permission strings.
                    User needs AT LEAST ONE of the specified permissions.
    
    Usage:
        @router.get("/", dependencies=[Depends(permission_required_any("patient_view"))])
    """
    if isinstance(permissions, str):
        permissions = [permissions]
    
    def permission_checker(current_user: models.User = Depends(get_current_user)):
        # Ensure role is loaded
        if not current_user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has no role assigned. Please contact system administrator."
            )
        
        user_role_name = current_user.role.name
        
        # Admin has full access regardless of permissions
        if user_role_name.lower() == "admin":
            return current_user
        
        # Get user's permissions from database
        user_permissions = get_user_permissions(current_user)
        
        # Check if user has at least one of the required permissions
        has_permission = any(perm in user_permissions for perm in permissions)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have any of the required permissions. Please contact system administrator."
            )
        
        return current_user
    
    return permission_checker
