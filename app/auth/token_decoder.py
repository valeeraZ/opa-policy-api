"""Token decoder for extracting user information from JWT tokens."""

from typing import Optional
from jose import JWTError, jwt
from app.schemas.user import UserInfo
from app.exceptions import AuthenticationError


class TokenDecoder:
    """
    Handles decoding and validation of JWT tokens.
    
    This class integrates with existing token decoding functionality
    to extract user information including AD groups, employee ID, email, and name.
    """
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        verify_signature: bool = True
    ):
        """
        Initialize the TokenDecoder.
        
        Args:
            secret_key: Secret key for JWT verification (optional for unverified tokens)
            algorithm: JWT algorithm (default: HS256)
            verify_signature: Whether to verify token signature (default: True)
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.verify_signature = verify_signature
    
    def decode_token(self, token: str) -> UserInfo:
        """
        Decode a JWT token and extract user information.
        
        Args:
            token: JWT token string
            
        Returns:
            UserInfo object containing user details
            
        Raises:
            AuthenticationError: If token is invalid, expired, or missing required fields
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith("Bearer "):
                token = token[7:]
            
            # Decode the token
            if self.verify_signature and self.secret_key:
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[self.algorithm]
                )
            else:
                # Decode without verification (for development/testing)
                # python-jose requires a key even when not verifying, so we pass empty string
                payload = jwt.decode(
                    token,
                    "",
                    options={"verify_signature": False}
                )
            
            # Extract required fields
            employee_id = payload.get("employee_id") or payload.get("sub")
            ad_groups = payload.get("ad_groups", [])
            email = payload.get("email", "")
            name = payload.get("name", "")
            
            # Validate required fields
            if not employee_id:
                raise AuthenticationError("Token missing employee_id or sub claim")
            
            if not isinstance(ad_groups, list):
                raise AuthenticationError("Token ad_groups claim must be a list")
            
            return UserInfo(
                employee_id=employee_id,
                ad_groups=ad_groups,
                email=email,
                name=name
            )
            
        except JWTError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
        except Exception as e:
            raise AuthenticationError(f"Token decoding failed: {str(e)}")
