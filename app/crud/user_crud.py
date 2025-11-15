"""
User CRUD Operations
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional

from app.models.user_models import User, Role
from app.schemas.user_schemas import UserCreate, UserBase


def create_user(db: Session, user: UserCreate) -> User:
    """Create a new user"""
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise ValueError(f"Username '{user.username}' already exists")
    
    # Check if email already exists (if provided)
    if user.email:
        existing_email = db.query(User).filter(User.email == user.email).first()
        if existing_email:
            raise ValueError(f"Email '{user.email}' is already in use")
    
    # Verify role exists
    role = db.query(Role).filter(Role.id == user.role_id).first()
    if not role:
        raise ValueError(f"Role with ID {user.role_id} not found")
    
    # Create user
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role_id=user.role_id,
        is_active=True
    )
    
    # Set password
    db_user.set_password(user.password)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user(db: Session, user_id: int) -> User:
    """Get a user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> User:
    """Get a user by username"""
    return db.query(User).filter(User.username == username).first()


def get_users(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None, role_id: Optional[int] = None, is_active: Optional[bool] = None):
    """
    Get all users with optional search, filtering, and pagination.
    Returns tuple of (users list, total count)
    """
    from typing import Tuple, List
    
    query = db.query(User)
    
    # Apply search
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.username.ilike(search_term),
                User.full_name.ilike(search_term),
                User.email.ilike(search_term)
            )
        )
    
    # Apply role filter
    if role_id:
        query = query.filter(User.role_id == role_id)
    
    # Apply active filter
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # Get total count before pagination
    total_count = query.count()
    
    # Apply pagination and ordering
    users = query.order_by(User.id.desc()).offset(skip).limit(limit).all()
    
    return users, total_count


def get_doctors(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None):
    """
    Get all doctors (users with Doctor role) with optional search and pagination.
    Returns tuple of (doctors list, total count)
    """
    from typing import Tuple, List
    
    # Get Doctor role ID (not Clinician, to separate doctors from nurses)
    doctor_role = db.query(Role).filter(Role.name == "Doctor").first()
    if not doctor_role:
        return [], 0
    
    query = db.query(User).filter(User.role_id == doctor_role.id, User.is_active == True)
    
    # Apply search
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.username.ilike(search_term),
                User.full_name.ilike(search_term),
                User.email.ilike(search_term)
            )
        )
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination and ordering
    doctors = query.order_by(User.full_name.asc()).offset(skip).limit(limit).all()
    
    return doctors, total_count


def update_user(db: Session, user_id: int, user_update: dict) -> User:
    """Update a user"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise ValueError(f"User with ID {user_id} not found")
    
    # Check username uniqueness (if changing)
    if "username" in user_update and user_update["username"] != db_user.username:
        existing = db.query(User).filter(User.username == user_update["username"]).first()
        if existing:
            raise ValueError(f"Username '{user_update['username']}' already exists")
    
    # Check email uniqueness (if changing)
    if "email" in user_update and user_update["email"] and user_update["email"] != db_user.email:
        existing = db.query(User).filter(User.email == user_update["email"]).first()
        if existing:
            raise ValueError(f"Email '{user_update['email']}' is already in use")
    
    # Check role exists (if changing)
    if "role_id" in user_update:
        role = db.query(Role).filter(Role.id == user_update["role_id"]).first()
        if not role:
            raise ValueError(f"Role with ID {user_update['role_id']} not found")
    
    # Update fields
    for key, value in user_update.items():
        if key == "password":
            db_user.set_password(value)
        elif hasattr(db_user, key):
            setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    """Soft delete a user (set is_active to False)"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return False
    
    db_user.is_active = False
    db.commit()
    return True

