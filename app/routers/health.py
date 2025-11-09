"""Health check router for monitoring system component status."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.services.opa_service import OPAService
from app.services.s3_service import S3Service
from app.exceptions import OPAConnectionError, DatabaseError, S3Error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


def get_opa_service() -> OPAService:
    """Dependency to get OPA service instance."""
    return OPAService()


def get_s3_service() -> S3Service:
    """Dependency to get S3 service instance."""
    return S3Service()


@router.get("", response_model=Dict[str, Any])
async def health_check(
    db: Session = Depends(get_db),
    opa_service: OPAService = Depends(get_opa_service),
    s3_service: S3Service = Depends(get_s3_service)
) -> JSONResponse:
    """
    Check overall system health including all components.
    
    Returns 200 if all services are healthy, 503 if any service is unhealthy.
    
    Returns:
        JSON response with health status of all components
    """
    health_status = {
        "status": "healthy",
        "components": {}
    }
    
    all_healthy = True
    
    # Check database
    try:
        db.execute(text("SELECT 1"))
        health_status["components"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
        logger.debug("Database health check: healthy")
    except Exception as e:
        all_healthy = False
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        logger.error(f"Database health check failed: {e}")
    
    # Check OPA
    try:
        await opa_service.health_check()
        health_status["components"]["opa"] = {
            "status": "healthy",
            "message": "OPA server is reachable"
        }
        logger.debug("OPA health check: healthy")
    except OPAConnectionError as e:
        all_healthy = False
        health_status["components"]["opa"] = {
            "status": "unhealthy",
            "message": f"OPA server unreachable: {str(e)}"
        }
        logger.error(f"OPA health check failed: {e}")
    except Exception as e:
        all_healthy = False
        health_status["components"]["opa"] = {
            "status": "unhealthy",
            "message": f"OPA health check error: {str(e)}"
        }
        logger.error(f"OPA health check error: {e}")
    finally:
        await opa_service.close()
    
    # Check S3
    try:
        # Try to list objects in the bucket to verify access
        s3_service.s3_client.head_bucket(Bucket=s3_service.bucket)
        health_status["components"]["s3"] = {
            "status": "healthy",
            "message": "S3 bucket is accessible"
        }
        logger.debug("S3 health check: healthy")
    except Exception as e:
        all_healthy = False
        health_status["components"]["s3"] = {
            "status": "unhealthy",
            "message": f"S3 bucket not accessible: {str(e)}"
        }
        logger.error(f"S3 health check failed: {e}")
    
    # Set overall status
    if not all_healthy:
        health_status["status"] = "unhealthy"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_status
        )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=health_status
    )


@router.get("/opa", response_model=Dict[str, Any])
async def health_check_opa(
    opa_service: OPAService = Depends(get_opa_service)
) -> JSONResponse:
    """
    Check OPA server connectivity and health.
    
    Returns 200 if OPA is healthy, 503 if unhealthy.
    
    Returns:
        JSON response with OPA health status
    """
    try:
        await opa_service.health_check()
        response = {
            "status": "healthy",
            "message": "OPA server is reachable and healthy"
        }
        logger.info("OPA health check: healthy")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response
        )
    except OPAConnectionError as e:
        response = {
            "status": "unhealthy",
            "message": f"OPA server unreachable: {str(e)}"
        }
        logger.error(f"OPA health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response
        )
    except Exception as e:
        response = {
            "status": "unhealthy",
            "message": f"OPA health check error: {str(e)}"
        }
        logger.error(f"OPA health check error: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response
        )
    finally:
        await opa_service.close()


@router.get("/db", response_model=Dict[str, Any])
async def health_check_db(
    db: Session = Depends(get_db)
) -> JSONResponse:
    """
    Check database connectivity and health.
    
    Returns 200 if database is healthy, 503 if unhealthy.
    
    Returns:
        JSON response with database health status
    """
    try:
        # Execute a simple query to verify database connection
        db.execute(text("SELECT 1"))
        response = {
            "status": "healthy",
            "message": "Database connection successful"
        }
        logger.info("Database health check: healthy")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response
        )
    except Exception as e:
        response = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        logger.error(f"Database health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response
        )


@router.get("/s3", response_model=Dict[str, Any])
async def health_check_s3(
    s3_service: S3Service = Depends(get_s3_service)
) -> JSONResponse:
    """
    Check S3 bucket accessibility and health.
    
    Returns 200 if S3 is accessible, 503 if unhealthy.
    
    Returns:
        JSON response with S3 health status
    """
    try:
        # Check if bucket is accessible using head_bucket
        s3_service.s3_client.head_bucket(Bucket=s3_service.bucket)
        response = {
            "status": "healthy",
            "message": f"S3 bucket '{s3_service.bucket}' is accessible"
        }
        logger.info("S3 health check: healthy")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response
        )
    except Exception as e:
        response = {
            "status": "unhealthy",
            "message": f"S3 bucket not accessible: {str(e)}"
        }
        logger.error(f"S3 health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response
        )
