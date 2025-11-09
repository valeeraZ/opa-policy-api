"""FastAPI dependencies for authentication and authorization."""

from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.token_decoder import TokenDecoder
from app.schemas.user import UserInfo
from app.config import settings
from app.exceptions import AuthenticationError, AuthorizationError


# HTTP Bearer token security scheme
security = HTTPBearer()


def get_token_decoder() -> TokenDecoder:
    """
    Dependency to get a configured TokenDecoder instance.
    
    Returns:
        TokenDecoder configured with application settings
    """
    return TokenDecoder(
        secret_key=settings.jwt_secret_key if settings.jwt_secret_key else None,
        algorithm=settings.jwt_algorithm,
        verify_signature=settings.jwt_verify_signature
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    token_decoder: Annotated[TokenDecoder, Depends(get_token_decoder)]
) -> UserInfo:
    """
    Extract and validate user information from the authorization token.
    
    This dependency decodes the JWT token from the Authorization header
    and returns the user information.
    
    Args:
        credentials: HTTP Bearer credentials from the request
        token_decoder: TokenDecoder instance for decoding tokens
        
    Returns:
        UserInfo object containing user details
        
    Raises:
        HTTPException: 401 if token is invalid or missing required fields
    """
    try:
        user_info = token_decoder.decode_token(credentials.credentials)
        return user_info
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_admin(
    current_user: Annotated[UserInfo, Depends(get_current_user)]
) -> UserInfo:
    """
    Verify that the current user has administrative privileges.
    
    This dependency checks if the user belongs to the admin AD group
    configured in the application settings.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserInfo object if user is an admin
        
    Raises:
        HTTPException: 403 if user does not have admin privileges
    """
    admin_group = settings.admin_ad_group
    
    if admin_group not in current_user.ad_groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Admin privileges required. User must be member of '{admin_group}' AD group.",
        )
    
    return current_user


# Type aliases for cleaner endpoint signatures
CurrentUser = Annotated[UserInfo, Depends(get_current_user)]
AdminUser = Annotated[UserInfo, Depends(require_admin)]
