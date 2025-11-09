"""Custom exceptions for the OPA Permission API."""


class OPAPermissionAPIException(Exception):
    """Base exception for all OPA Permission API errors."""

    def __init__(self, message: str, detail: str = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class OPAConnectionError(OPAPermissionAPIException):
    """Raised when OPA server is unreachable or connection fails."""

    pass


class DatabaseError(OPAPermissionAPIException):
    """Raised when database operations fail."""

    pass


class S3Error(OPAPermissionAPIException):
    """Raised when S3 operations fail."""

    pass


class ValidationError(OPAPermissionAPIException):
    """Raised when input validation fails."""

    pass


class AuthenticationError(OPAPermissionAPIException):
    """Raised when authentication fails."""

    pass


class AuthorizationError(OPAPermissionAPIException):
    """Raised when authorization fails (user lacks required permissions)."""

    pass
