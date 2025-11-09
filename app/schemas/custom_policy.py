from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class CustomPolicyCreate(BaseModel):
    """Schema for creating a new custom policy"""
    id: str = Field(..., description="Unique policy identifier", min_length=1, max_length=255)
    name: str = Field(..., description="Policy name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Policy description")
    rego_content: str = Field(..., description="Rego policy content", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "custom-policy-1",
                "name": "Custom Authorization Policy",
                "description": "Policy for custom authorization logic",
                "rego_content": "package custom\n\ndefault allow = false\n\nallow {\n    input.user.role == \"admin\"\n}"
            }
        }


class CustomPolicyEvaluate(BaseModel):
    """Schema for evaluating a custom policy"""
    input_data: Dict[str, Any] = Field(..., description="Input data for policy evaluation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "input_data": {
                    "user": {
                        "role": "admin",
                        "department": "engineering"
                    },
                    "resource": {
                        "type": "document",
                        "owner": "user123"
                    }
                }
            }
        }


class CustomPolicyResponse(BaseModel):
    """Schema for custom policy response with metadata"""
    id: str = Field(..., description="Policy identifier")
    name: str = Field(..., description="Policy name")
    description: Optional[str] = Field(None, description="Policy description")
    s3_key: str = Field(..., description="S3 storage key for policy file")
    version: str = Field(..., description="Policy version")
    creator_id: str = Field(..., description="ID of user who created the policy")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "custom-policy-1",
                "name": "Custom Authorization Policy",
                "description": "Policy for custom authorization logic",
                "s3_key": "policies/custom-policy-1/v1.rego",
                "version": "v1",
                "creator_id": "E12345",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": None
            }
        }


class CustomPolicyEvaluationResult(BaseModel):
    """Schema for custom policy evaluation result"""
    policy_id: str = Field(..., description="Policy identifier")
    result: Dict[str, Any] = Field(..., description="Policy evaluation result from OPA")
    
    class Config:
        json_schema_extra = {
            "example": {
                "policy_id": "custom-policy-1",
                "result": {
                    "allow": True,
                    "reason": "User has admin role"
                }
            }
        }
