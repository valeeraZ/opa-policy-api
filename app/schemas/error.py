from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ErrorResponse(BaseModel):
    """Standard error response schema"""
    error: str = Field(..., description="Error type or category")
    detail: Optional[str] = Field(None, description="Detailed error message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    path: str = Field(..., description="Request path where error occurred")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Service Unavailable",
                "detail": "OPA server is unreachable",
                "timestamp": "2024-01-15T10:30:00Z",
                "path": "/permission"
            }
        }
