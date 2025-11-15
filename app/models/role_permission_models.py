from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Table
from sqlalchemy.orm import relationship
from app.db.database import Base


# Association table for many-to-many relationship between Role and Permission
role_permission_association = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True)
)


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

    # Relationships
    roles = relationship("Role", secondary=role_permission_association, back_populates="permissions")

    def __repr__(self):
        return f"<Permission(id={self.id}, name='{self.name}')>"


# Update Role model to include permissions relationship
# This will be done by adding the relationship to the existing Role model

