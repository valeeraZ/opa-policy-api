from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RoleMappingBase(BaseModel):
    """Base role mapping schema with common fields"""
    application_id: str = Field(..., description="Application identifier")
    environment: str = Field(..., description="Environment (e.g., DEV, PROD)")
    ad_group: str = Field(..., description="Active Directory group name")
    role: str = Field(..., description="Role assigned to the AD group (e.g., user, admin)")


class RoleMappingCreate(RoleMappingBase):
    """Schema for creating a new role mapping"""
    
    class Config:
        json_schema_extra = {
            "example": {
                "application_id": "app-a",
                "environment": "DEV",
                "ad_group": "infodir-application-a-admin",
                "role": "admin"
            }
        }


class RoleMappingUpdate(BaseModel):
    """Schema for updating an existing role mapping"""
    environment: Optional[str] = Field(None, description="Environment (e.g., DEV, PROD)")
    ad_group: Optional[str] = Field(None, description="Active Directory group name")
    role: Optional[str] = Field(None, description="Role assigned to the AD group")
    
    class Config:
        json_schema_extra = {
            "example": {
                "role": "user"
            }
        }


class RoleMappingResponse(RoleMappingBase):
    """Schema for role mapping response with metadata"""
    id: int = Field(..., description="Role mapping identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "application_id": "app-a",
                "environment": "DEV",
                "ad_group": "infodir-application-a-admin",
                "role": "admin",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-20T14:45:00Z"
            }
        }
