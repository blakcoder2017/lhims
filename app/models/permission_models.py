from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.db.database import Base


class Permission(Base):
    """
    SQLAlchemy Model for system permissions.
    Defines what actions can be performed in the system.
    """
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "view_patients", "create_encounters"
    description = Column(String(255), nullable=True)  # Human-readable description
    module = Column(String(50), nullable=True, index=True)  # Module/area: "patients", "billing", "admin", etc.
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationship to roles (many-to-many) - using string reference to avoid circular import
    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")

    def __repr__(self):
        return f"<Permission(id={self.id}, name='{self.name}')>"

