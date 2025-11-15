from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.audit_models import AuditAction


class AuditLogBase(BaseModel):
    user_id: int
    username: Optional[str] = Field(None, max_length=100)
    action: AuditAction
    resource_type: Optional[str] = Field(None, max_length=100)
    resource_id: Optional[int] = None
    ip_address: Optional[str] = Field(None, max_length=50)
    user_agent: Optional[str] = Field(None, max_length=500)
    request_method: Optional[str] = Field(None, max_length=10)
    request_path: Optional[str] = Field(None, max_length=500)
    old_values: Optional[str] = None
    new_values: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(None, max_length=50)
    error_message: Optional[str] = None


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogRead(AuditLogBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

