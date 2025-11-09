"""Tests for authentication and token decoding."""

import pytest
from jose import jwt
from datetime import datetime, timedelta
from app.auth.token_decoder import TokenDecoder
from app.exceptions import AuthenticationError


def create_test_token(payload: dict, secret: str = "test_secret") -> str:
    """Helper function to create test JWT tokens."""
    return jwt.encode(payload, secret, algorithm="HS256")


def test_token_decoder_valid_token():
    """Test decoding a valid token with all required fields."""
    payload = {
        "employee_id": "E12345",
        "ad_groups": ["infodir-app-admin", "infodir-app-user"],
        "email": "test@example.com",
        "name": "Test User",
        "exp": datetime.now() + timedelta(hours=1),
    }
    token = create_test_token(payload)

    decoder = TokenDecoder(secret_key="test_secret", verify_signature=True)
    user_info = decoder.decode_token(token)

    assert user_info.employee_id == "E12345"
    assert user_info.ad_groups == ["infodir-app-admin", "infodir-app-user"]
    assert user_info.email == "test@example.com"
    assert user_info.name == "Test User"


def test_token_decoder_with_sub_claim():
    """Test decoding a token that uses 'sub' instead of 'employee_id'."""
    payload = {
        "sub": "E67890",
        "ad_groups": ["infodir-app-user"],
        "email": "user@example.com",
        "name": "Another User",
    }
    token = create_test_token(payload)

    decoder = TokenDecoder(verify_signature=False)
    user_info = decoder.decode_token(token)

    assert user_info.employee_id == "E67890"


def test_token_decoder_bearer_prefix():
    """Test decoding a token with 'Bearer ' prefix."""
    payload = {
        "employee_id": "E12345",
        "ad_groups": ["infodir-app-user"],
        "email": "test@example.com",
        "name": "Test User",
    }
    token = "Bearer " + create_test_token(payload)

    decoder = TokenDecoder(verify_signature=False)
    user_info = decoder.decode_token(token)

    assert user_info.employee_id == "E12345"


def test_token_decoder_missing_employee_id():
    """Test that decoding fails when employee_id and sub are missing."""
    payload = {
        "ad_groups": ["infodir-app-user"],
        "email": "test@example.com",
        "name": "Test User",
    }
    token = create_test_token(payload)

    decoder = TokenDecoder(verify_signature=False)

    with pytest.raises(
        AuthenticationError, match="Token missing employee_id or sub claim"
    ):
        decoder.decode_token(token)


def test_token_decoder_invalid_ad_groups():
    """Test that decoding fails when ad_groups is not a list."""
    payload = {
        "employee_id": "E12345",
        "ad_groups": "not-a-list",
        "email": "test@example.com",
        "name": "Test User",
    }
    token = create_test_token(payload)

    decoder = TokenDecoder(verify_signature=False)

    with pytest.raises(AuthenticationError, match="ad_groups claim must be a list"):
        decoder.decode_token(token)


def test_token_decoder_invalid_token():
    """Test that decoding fails with an invalid token."""
    decoder = TokenDecoder(verify_signature=False)

    with pytest.raises(AuthenticationError, match="Invalid token"):
        decoder.decode_token("invalid.token.here")


def test_token_decoder_default_values():
    """Test that missing optional fields use default values."""
    payload = {"employee_id": "E12345"}
    token = create_test_token(payload)

    decoder = TokenDecoder(verify_signature=False)
    user_info = decoder.decode_token(token)

    assert user_info.employee_id == "E12345"
    assert user_info.ad_groups == []
    assert user_info.email == ""
    assert user_info.name == ""
