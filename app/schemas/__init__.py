"""Pydantic schemas for request/response validation"""

from app.schemas.user import UserInfo
from app.schemas.permission import (
    PermissionRequest,
    PermissionResponse,
    AppPermissionResponse,
)
from app.schemas.application import (
    ApplicationBase,
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
)
from app.schemas.role_mapping import (
    RoleMappingBase,
    RoleMappingCreate,
    RoleMappingUpdate,
    RoleMappingResponse,
)
from app.schemas.custom_policy import (
    CustomPolicyCreate,
    CustomPolicyEvaluate,
    CustomPolicyResponse,
    CustomPolicyEvaluationResult,
)
from app.schemas.error import ErrorResponse

__all__ = [
    # User
    "UserInfo",
    # Permission
    "PermissionRequest",
    "PermissionResponse",
    "AppPermissionResponse",
    # Application
    "ApplicationBase",
    "ApplicationCreate",
    "ApplicationUpdate",
    "ApplicationResponse",
    # Role Mapping
    "RoleMappingBase",
    "RoleMappingCreate",
    "RoleMappingUpdate",
    "RoleMappingResponse",
    # Custom Policy
    "CustomPolicyCreate",
    "CustomPolicyEvaluate",
    "CustomPolicyResponse",
    "CustomPolicyEvaluationResult",
    # Error
    "ErrorResponse",
]
