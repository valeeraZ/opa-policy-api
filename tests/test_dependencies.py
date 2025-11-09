"""Tests for FastAPI dependencies."""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.dependencies import get_current_user, require_admin, get_token_decoder
from app.auth.token_decoder import TokenDecoder
from app.schemas.user import UserInfo
from app.config import settings
from jose import jwt


def create_test_token(payload: dict, secret: str = "test_secret") -> str:
    """Helper function to create test JWT tokens."""
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_get_current_user_valid_token():
    """Test get_current_user with a valid token."""
    payload = {
        "employee_id": "E12345",
        "ad_groups": ["infodir-app-admin"],
        "email": "test@example.com",
        "name": "Test User"
    }
    token = create_test_token(payload)
    
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    token_decoder = TokenDecoder(verify_signature=False)
    
    user_info = await get_current_user(credentials, token_decoder)
    
    assert user_info.employee_id == "E12345"
    assert user_info.ad_groups == ["infodir-app-admin"]
    assert user_info.email == "test@example.com"
    assert user_info.name == "Test User"


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    """Test get_current_user with an invalid token."""
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.token")
    token_decoder = TokenDecoder(verify_signature=False)
    
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials, token_decoder)
    
    assert exc_info.value.status_code == 401
    assert "Invalid token" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_require_admin_with_admin_user():
    """Test require_admin with a user who has admin privileges."""
    user_info = UserInfo(
        employee_id="E12345",
        ad_groups=[settings.admin_ad_group, "other-group"],
        email="admin@example.com",
        name="Admin User"
    )
    
    result = await require_admin(user_info)
    
    assert result == user_info


@pytest.mark.asyncio
async def test_require_admin_without_admin_privileges():
    """Test require_admin with a user who lacks admin privileges."""
    user_info = UserInfo(
        employee_id="E12345",
        ad_groups=["infodir-app-user", "other-group"],
        email="user@example.com",
        name="Regular User"
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(user_info)
    
    assert exc_info.value.status_code == 403
    assert "Admin privileges required" in str(exc_info.value.detail)


def test_get_token_decoder():
    """Test get_token_decoder returns a properly configured TokenDecoder."""
    decoder = get_token_decoder()
    
    assert isinstance(decoder, TokenDecoder)
    assert decoder.algorithm == settings.jwt_algorithm
    assert decoder.verify_signature == settings.jwt_verify_signature
