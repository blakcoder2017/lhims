"""
Lab Template Schemas

Pydantic schemas for lab template management including:
- Template CRUD
- Reference ranges
- Template documents/attachments
"""
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


# ============== Lab Template Document Schemas ==============

class LabTemplateDocumentBase(BaseModel):
    """Base schema for lab template document"""
    description: Optional[str] = None
    category: Optional[str] = Field(None, description="SOP, FORM, INSTRUCTION, REFERENCE, OTHER")


class LabTemplateDocumentCreate(LabTemplateDocumentBase):
    """Schema for creating a template document"""
    template_id: UUID


class LabTemplateDocumentUpdate(BaseModel):
    """Schema for updating a template document"""
    description: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None


class LabTemplateDocumentRead(LabTemplateDocumentBase):
    """Schema for reading template document"""
    id: UUID
    template_id: UUID
    filename: str
    original_filename: str
    content_type: str
    file_size: int
    file_path: str
    uploaded_by_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============== Lab Template Schemas (Extended) ==============

class LabTemplateWithDocuments(BaseModel):
    """Lab template with associated documents"""
    id: UUID
    name: str
    discipline: str
    status: str
    current_version: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    documents: List[LabTemplateDocumentRead] = []

    class Config:
        from_attributes = True


# ============== Lab Test with Full Details ==============

class LabTestWithDetails(BaseModel):
    """Lab test with template and reference ranges"""
    id: int
    test_name: str
    test_code: str
    test_category: Optional[str] = None
    test_type: Optional[str] = None
    specimen_type: Optional[str] = None
    description: Optional[str] = None
    template_id: Optional[UUID] = None
    template_version: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True
