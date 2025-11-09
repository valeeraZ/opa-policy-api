"""Main FastAPI application with middleware, routers, and lifecycle management."""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import SessionLocal
from app.exceptions import (
    OPAPermissionAPIException,
    OPAConnectionError,
    DatabaseError,
    S3Error,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
)
from app.routers import permissions
from app.routers import applications
from app.routers import role_mappings
from app.routers import custom_policies
from app.routers import health
from app.services.opa_service import OPAService
from app.services.role_mapping_service import RoleMappingService

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    Handles:
    - Database connection initialization
    - OPA server health check and initialization
    - Base policy upload to OPA
    - Role mappings synchronization to OPA
    """
    logger.info("Starting application initialization...")

    # Initialize OPA service
    opa_service = OPAService()

    try:
        # Check OPA server health
        logger.info("Checking OPA server health...")
        await opa_service.health_check()
        logger.info("OPA server is healthy")

        # Upload base OPA policy
        logger.info("Uploading base OPA policy...")
        await opa_service.upload_base_policy()
        logger.info("Base OPA policy uploaded successfully")

        # Sync existing role mappings to OPA
        logger.info("Synchronizing existing role mappings to OPA...")
        db = SessionLocal()
        try:
            role_mapping_service = RoleMappingService(db, opa_service)
            await role_mapping_service.sync_to_opa()
            logger.info("Role mappings synchronized to OPA successfully")
        except Exception as e:
            logger.warning(f"Failed to sync role mappings on startup: {e}")
            logger.warning(
                "Application will continue, but role mappings may need manual sync"
            )
        finally:
            db.close()

        logger.info("Application initialization completed successfully")

    except OPAConnectionError as e:
        logger.error(f"Failed to initialize OPA: {e.message}")
        logger.error("Application will start but OPA-dependent features may not work")
    except Exception as e:
        logger.error(f"Unexpected error during initialization: {e}")
        logger.error("Application will start but some features may not work correctly")
    finally:
        await opa_service.close()

    # Application is ready
    yield

    # Shutdown
    logger.info("Shutting down application...")


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="FastAPI backend server for OPA-based permission management",
    lifespan=lifespan,
)


# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Logging middleware with request ID tracking
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """
    Middleware for logging requests with unique request ID tracking.

    Adds a unique request ID to each request and logs request/response details.
    """
    # Generate unique request ID
    request_id = str(uuid.uuid4())

    # Add request ID to request state for access in route handlers
    request.state.request_id = request_id

    # Log incoming request
    logger.info(
        f"[{request_id}] {request.method} {request.url.path} - "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )

    # Record start time
    start_time = datetime.now()

    # Process request
    try:
        response = await call_next(request)

        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()

        # Log response
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Status: {response.status_code} - Duration: {duration:.3f}s"
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response

    except Exception as e:
        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()

        # Log error
        logger.error(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Error: {str(e)} - Duration: {duration:.3f}s"
        )
        raise


# Global exception handlers
@app.exception_handler(OPAConnectionError)
async def opa_connection_error_handler(request: Request, exc: OPAConnectionError):
    """Handle OPA connection errors with 503 Service Unavailable."""
    logger.error(f"OPA connection error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "Service Unavailable",
            "detail": exc.message,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
        },
    )


@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    """Handle database errors with 500 Internal Server Error."""
    logger.error(f"Database error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": f"Database operation failed: {exc.message}",
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
        },
    )


@app.exception_handler(S3Error)
async def s3_error_handler(request: Request, exc: S3Error):
    """Handle S3 errors with 500 Internal Server Error."""
    logger.error(f"S3 error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": f"S3 operation failed: {exc.message}",
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
        },
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle validation errors with 400 Bad Request."""
    logger.warning(f"Validation error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Bad Request",
            "detail": exc.message,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
        },
    )


@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors with 401 Unauthorized."""
    logger.warning(f"Authentication error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "Unauthorized",
            "detail": exc.message,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
        },
    )


@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request: Request, exc: AuthorizationError):
    """Handle authorization errors with 403 Forbidden."""
    logger.warning(f"Authorization error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "Forbidden",
            "detail": exc.message,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
        },
    )


@app.exception_handler(OPAPermissionAPIException)
async def generic_api_exception_handler(
    request: Request, exc: OPAPermissionAPIException
):
    """Handle generic API exceptions with 500 Internal Server Error."""
    logger.error(f"API exception: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": exc.message,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
        },
    )


# Register routers
app.include_router(health.router)
app.include_router(permissions.router)
app.include_router(applications.router)
app.include_router(role_mappings.router)
app.include_router(custom_policies.router)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint providing API information."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "description": "OPA Permission API - Dynamic permission management with Open Policy Agent",
        "health_check": "/health",
        "documentation": "/docs",
    }
