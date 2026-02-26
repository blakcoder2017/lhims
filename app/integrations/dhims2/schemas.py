"""
Pydantic Schemas for DHIMS2 API

Request and response schemas for the DHIMS2 integration endpoints.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SubmissionRunStatusSchema(str, Enum):
    """Schema for submission run status."""
    DRAFT = "draft"
    VALIDATION_FAILED = "validation_failed"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SUBMITTED = "submitted"
    SUBMIT_FAILED = "submit_failed"
    LOCKED = "locked"


class ValidationStatusSchema(str, Enum):
    """Schema for validation status."""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


# ============== Instance Schemas ==============

class DHIMS2InstanceBase(BaseModel):
    """Base schema for DHIMS2 instance."""
    name: str = Field(..., description="Instance name")
    base_url: str = Field(..., description="DHIS2 base URL")
    username: str = Field(..., description="API username")
    password: str = Field(..., description="API password")
    is_active: bool = Field(default=True)
    timeout_seconds: int = Field(default=30, ge=5, le=120)
    verify_tls: bool = Field(default=True)
    max_retries: int = Field(default=5, ge=1, le=10)


class DHIMS2InstanceCreate(DHIMS2InstanceBase):
    """Schema for creating a DHIMS2 instance."""
    pass


class DHIMS2InstanceUpdate(BaseModel):
    """Schema for updating a DHIMS2 instance."""
    name: Optional[str] = None
    base_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    timeout_seconds: Optional[int] = Field(None, ge=5, le=120)
    verify_tls: Optional[bool] = None
    max_retries: Optional[int] = Field(None, ge=1, le=10)


class DHIMS2InstanceResponse(DHIMS2InstanceBase):
    """Schema for instance response (password hidden)."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True
    
    @validator('password')
    def hide_password(cls, v):
        return "****" if v else None


# ============== Mapping Schemas ==============

class DHIMS2MappingBase(BaseModel):
    """Base schema for DHIMS2 mapping."""
    internal_metric_key: str = Field(..., description="Internal metric key")
    dhis2_data_element_uid: str = Field(..., description="DHIS2 data element UID")
    dhis2_category_option_combo_uid: Optional[str] = Field(None, description="Category option combo UID")
    dhis2_attribute_option_combo_uid: Optional[str] = Field(None, description="Attribute option combo UID")
    dhis2_dataset_uid: Optional[str] = Field(None, description="Dataset UID")
    value_type: str = Field(default="numeric", description="Value type")
    is_active: bool = Field(default=True)
    is_required: bool = Field(default=False, description="Required for submission")
    description: Optional[str] = None
    validation_config: Optional[Dict[str, Any]] = None


class DHIMS2MappingCreate(DHIMS2MappingBase):
    """Schema for creating a mapping."""
    instance_id: int


class DHIMS2MappingUpdate(BaseModel):
    """Schema for updating a mapping."""
    internal_metric_key: Optional[str] = None
    dhis2_data_element_uid: Optional[str] = None
    dhis2_category_option_combo_uid: Optional[str] = None
    dhis2_attribute_option_combo_uid: Optional[str] = None
    dhis2_dataset_uid: Optional[str] = None
    value_type: Optional[str] = None
    is_active: Optional[bool] = None
    is_required: Optional[bool] = None
    description: Optional[str] = None
    validation_config: Optional[Dict[str, Any]] = None


class DHIMS2MappingResponse(DHIMS2MappingBase):
    """Schema for mapping response."""
    id: int
    instance_id: int
    created_by: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ============== Org Unit Mapping Schemas ==============

class DHIMS2OrgUnitMappingBase(BaseModel):
    """Base schema for org unit mapping."""
    internal_org_id: int = Field(..., description="Internal org ID")
    internal_org_type: str = Field(..., description="Type: department, ward, facility")
    dhis2_org_unit_uid: str = Field(..., description="DHIS2 org unit UID")
    dhis2_org_unit_name: Optional[str] = None


class DHIMS2OrgUnitMappingCreate(DHIMS2OrgUnitMappingBase):
    """Schema for creating org unit mapping."""
    instance_id: int


class DHIMS2OrgUnitMappingResponse(DHIMS2OrgUnitMappingBase):
    """Schema for org unit mapping response."""
    id: int
    instance_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ============== Submission Run Schemas ==============

class BuildSubmissionRequest(BaseModel):
    """Request to build a submission."""
    instance_id: int = Field(..., description="DHIMS2 instance ID")
    org_unit_uid: str = Field(..., description="DHIS2 org unit UID")
    period: str = Field(..., description="Period (YYYY-MM)")
    report_type: str = Field(..., description="Report type")
    dataset_uid: Optional[str] = Field(None, description="DHIS2 dataset UID")
    provider: str = Field(default="aggregated_indicators", description="Data provider name")


class ValidateSubmissionRequest(BaseModel):
    """Request to validate a submission."""
    required_metrics: Optional[List[str]] = Field(None, description="Required metric keys")
    cross_check_rules: Optional[List[Dict[str, Any]]] = Field(None, description="Cross-check rules")


class SubmitForApprovalRequest(BaseModel):
    """Request to submit for approval."""
    pass


class ApproveSubmissionRequest(BaseModel):
    """Request to approve submission."""
    allow_self_approval: bool = Field(default=False, description="Allow preparer to approve")


class SubmitToDHIMS2Request(BaseModel):
    """Request to submit to DHIMS2."""
    dry_run: bool = Field(default=False, description="Validate but don't submit")
    justification: Optional[str] = Field(None, description="Justification for override")


class LockSubmissionRequest(BaseModel):
    """Request to lock a submission."""
    justification: str = Field(..., description="Reason for locking")


class ValidationResultItem(BaseModel):
    """Individual validation result."""
    status: ValidationStatusSchema
    message: str
    metric_key: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class SubmissionRunResponse(BaseModel):
    """Schema for submission run response."""
    id: int
    instance_id: int
    org_unit_uid: str
    period: str
    report_type: str
    dataset_uid: Optional[str]
    status: SubmissionRunStatusSchema
    payload_hash: Optional[str]
    prepared_by: Optional[int]
    prepared_at: Optional[datetime]
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    submitted_at: Optional[datetime]
    dhis2_import_count: Optional[Dict[str, Any]]
    error_summary: Optional[str]
    is_locked: bool
    locked_at: Optional[datetime]
    lock_justification: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    items: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        from_attributes = True


class SubmissionItemResponse(BaseModel):
    """Schema for submission item."""
    id: int
    internal_metric_key: str
    value: str
    dhis2_data_element_uid: str
    dhis2_category_option_combo_uid: Optional[str]
    dhis2_attribute_option_combo_uid: Optional[str]
    validation_status: ValidationStatusSchema
    validation_notes: Optional[str]
    
    class Config:
        from_attributes = True


# ============== Metadata Sync Schemas ==============

class MetadataSyncRequest(BaseModel):
    """Request to sync metadata from DHIS2."""
    sync_org_units: bool = Field(default=True)
    sync_data_elements: bool = Field(default=True)
    sync_data_sets: bool = Field(default=True)
    sync_category_combos: bool = Field(default=True)


class MetadataSyncResponse(BaseModel):
    """Response from metadata sync."""
    org_units_synced: int = 0
    data_elements_synced: int = 0
    data_sets_synced: int = 0
    category_combos_synced: int = 0
    errors: List[str] = Field(default_factory=list)


# ============== List Schemas ==============

class SubmissionRunListResponse(BaseModel):
    """Paginated list of submission runs."""
    runs: List[SubmissionRunResponse]
    total: int
    page: int
    page_size: int


class MappingListResponse(BaseModel):
    """List of mappings."""
    mappings: List[DHIMS2MappingResponse]
    total: int
