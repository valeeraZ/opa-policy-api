from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ApplicationBase(BaseModel):
    """Base application schema with common fields"""
    name: str = Field(..., description="Application name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Application description")


class ApplicationCreate(ApplicationBase):
    """Schema for creating a new application"""
    id: str = Field(..., description="Unique application identifier", min_length=1, max_length=255)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "app-a",
                "name": "Application A",
                "description": "Main business application"
            }
        }


class ApplicationUpdate(ApplicationBase):
    """Schema for updating an existing application"""
    name: Optional[str] = Field(None, description="Application name", min_length=1, max_length=255)
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Application Name",
                "description": "Updated description"
            }
        }


class ApplicationResponse(ApplicationBase):
    """Schema for application response with metadata"""
    id: str = Field(..., description="Application identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "app-a",
                "name": "Application A",
                "description": "Main business application",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-20T14:45:00Z"
            }
        }
