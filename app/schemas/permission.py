from pydantic import BaseModel, Field
from typing import Dict


class PermissionRequest(BaseModel):
    """Request model for permission evaluation"""
    token: str = Field(..., description="Authentication token containing user information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class PermissionResponse(BaseModel):
    """Response model containing permissions for all applications"""
    permissions: Dict[str, str] = Field(
        ..., 
        description="Dictionary mapping application IDs to permission levels (user, admin, none)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "permissions": {
                    "app-a": "admin",
                    "app-b": "user",
                    "app-c": "none"
                }
            }
        }


class AppPermissionResponse(BaseModel):
    """Response model for single application permission"""
    application_id: str = Field(..., description="Application identifier")
    role: str = Field(..., description="User's role for this application (user, admin, none)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "application_id": "app-a",
                "role": "admin"
            }
        }
