from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Supplier(Base):
    """
    SQLAlchemy Model for suppliers/vendors.
    Tracks supplier information for inventory management.
    """
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    
    # Supplier Information
    name = Column(String(255), nullable=False, index=True)  # Supplier name
    code = Column(String(50), unique=True, nullable=True, index=True)  # Supplier code
    contact_person = Column(String(255), nullable=True)  # Contact person name
    
    # Contact Information
    email = Column(String(255), nullable=True)  # Email address
    phone = Column(String(50), nullable=True)  # Phone number
    mobile = Column(String(50), nullable=True)  # Mobile number
    address = Column(Text, nullable=True)  # Physical address
    city = Column(String(100), nullable=True)  # City
    country = Column(String(100), nullable=True, default="Ghana")  # Country
    
    # Business Information
    tax_id = Column(String(100), nullable=True)  # Tax identification number
    registration_number = Column(String(100), nullable=True)  # Business registration number
    
    # Payment Terms
    payment_terms = Column(String(100), nullable=True)  # Payment terms (e.g., Net 30)
    credit_limit = Column(Numeric(10, 2), nullable=True)  # Credit limit
    
    # Status
    is_active = Column(Boolean, default=True)  # Is supplier active
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    stock_items = relationship("StockItem", back_populates="supplier_obj")
    
    def __repr__(self):
        return f"<Supplier(id={self.id}, name='{self.name}')>"

