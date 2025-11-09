from pydantic import BaseModel, Field
from typing import List


class UserInfo(BaseModel):
    """User information extracted from token"""
    employee_id: str = Field(..., description="Employee ID from token")
    ad_groups: List[str] = Field(..., description="List of AD groups the user belongs to")
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="User full name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "employee_id": "E12345",
                "ad_groups": ["infodir-application-a-admin", "infodir-application-b-user"],
                "email": "user@example.com",
                "name": "John Doe"
            }
        }
