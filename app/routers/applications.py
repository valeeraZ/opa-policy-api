"""Application management endpoints."""

import logging
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AdminUser
from app.schemas.application import ApplicationCreate, ApplicationUpdate, ApplicationResponse
from app.services.application_service import ApplicationService
from app.exceptions import DatabaseError, ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new application",
    description="Create a new application (admin only)"
)
async def create_application(
    app_data: ApplicationCreate,
    admin_user: AdminUser,
    db: Annotated[Session, Depends(get_db)]
) -> ApplicationResponse:
    """
    Create a new application with admin authorization.
    
    This endpoint:
    1. Validates admin authorization
    2. Checks for duplicate application IDs
    3. Creates the application in the database
    4. Logs the operation for audit purposes
    
    Args:
        app_data: Application creation data
        admin_user: Authenticated admin user
        db: Database session
        
    Returns:
        ApplicationResponse with created application details
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 409 if application ID already exists
        HTTPException: 500 if database operation fails
    """
    logger.info(
        f"Admin user {admin_user.employee_id} creating application: {app_data.id}"
    )
    
    try:
        app_service = ApplicationService(db)
        created_app = app_service.create_application(app_data)
        
        logger.info(
            f"Application {created_app.id} created successfully by user {admin_user.employee_id}"
        )
        
        return created_app
        
    except ValidationError as e:
        logger.warning(
            f"Validation error creating application {app_data.id}: {e.message}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )
    except DatabaseError as e:
        logger.error(
            f"Database error creating application {app_data.id}: {e.message}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database operation failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating application {app_data.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating application"
        )


@router.get(
    "",
    response_model=List[ApplicationResponse],
    status_code=status.HTTP_200_OK,
    summary="List all applications",
    description="Retrieve all applications"
)
async def list_applications(
    db: Annotated[Session, Depends(get_db)]
) -> List[ApplicationResponse]:
    """
    Retrieve all applications.
    
    This endpoint fetches all applications from the database.
    No authentication required for listing applications.
    
    Args:
        db: Database session
        
    Returns:
        List of ApplicationResponse objects
        
    Raises:
        HTTPException: 500 if database operation fails
    """
    logger.debug("Listing all applications")
    
    try:
        app_service = ApplicationService(db)
        applications = app_service.list_applications()
        
        logger.info(f"Retrieved {len(applications)} applications")
        
        return applications
        
    except DatabaseError as e:
        logger.error(f"Database error listing applications: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database operation failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"Unexpected error listing applications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while listing applications"
        )


@router.get(
    "/{app_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get application by ID",
    description="Retrieve a specific application by its ID"
)
async def get_application(
    app_id: str,
    db: Annotated[Session, Depends(get_db)]
) -> ApplicationResponse:
    """
    Retrieve a specific application by ID.
    
    This endpoint fetches a single application from the database.
    No authentication required for retrieving applications.
    
    Args:
        app_id: Application identifier
        db: Database session
        
    Returns:
        ApplicationResponse with application details
        
    Raises:
        HTTPException: 404 if application not found
        HTTPException: 500 if database operation fails
    """
    logger.debug(f"Retrieving application: {app_id}")
    
    try:
        app_service = ApplicationService(db)
        application = app_service.get_application(app_id)
        
        if not application:
            logger.warning(f"Application not found: {app_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with id '{app_id}' not found"
            )
        
        logger.debug(f"Retrieved application: {app_id}")
        
        return application
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except DatabaseError as e:
        logger.error(f"Database error retrieving application {app_id}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database operation failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving application {app_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving application"
        )


@router.put(
    "/{app_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an application",
    description="Update an existing application (admin only)"
)
async def update_application(
    app_id: str,
    app_data: ApplicationUpdate,
    admin_user: AdminUser,
    db: Annotated[Session, Depends(get_db)]
) -> ApplicationResponse:
    """
    Update an existing application with admin authorization.
    
    This endpoint:
    1. Validates admin authorization
    2. Checks if application exists
    3. Updates the application in the database
    4. Logs the operation for audit purposes
    
    Args:
        app_id: Application identifier
        app_data: Application update data
        admin_user: Authenticated admin user
        db: Database session
        
    Returns:
        ApplicationResponse with updated application details
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 404 if application not found
        HTTPException: 500 if database operation fails
    """
    logger.info(
        f"Admin user {admin_user.employee_id} updating application: {app_id}"
    )
    
    try:
        app_service = ApplicationService(db)
        updated_app = app_service.update_application(app_id, app_data)
        
        logger.info(
            f"Application {app_id} updated successfully by user {admin_user.employee_id}"
        )
        
        return updated_app
        
    except ValidationError as e:
        logger.warning(
            f"Validation error updating application {app_id}: {e.message}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except DatabaseError as e:
        logger.error(
            f"Database error updating application {app_id}: {e.message}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database operation failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"Unexpected error updating application {app_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating application"
        )


@router.delete(
    "/{app_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an application",
    description="Delete an existing application (admin only)"
)
async def delete_application(
    app_id: str,
    admin_user: AdminUser,
    db: Annotated[Session, Depends(get_db)]
) -> None:
    """
    Delete an existing application with admin authorization.
    
    This endpoint:
    1. Validates admin authorization
    2. Deletes the application from the database
    3. Logs the operation for audit purposes
    
    Args:
        app_id: Application identifier
        admin_user: Authenticated admin user
        db: Database session
        
    Returns:
        None (204 No Content)
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 404 if application not found
        HTTPException: 500 if database operation fails
    """
    logger.info(
        f"Admin user {admin_user.employee_id} deleting application: {app_id}"
    )
    
    try:
        app_service = ApplicationService(db)
        deleted = app_service.delete_application(app_id)
        
        if not deleted:
            logger.warning(f"Application not found for deletion: {app_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with id '{app_id}' not found"
            )
        
        logger.info(
            f"Application {app_id} deleted successfully by user {admin_user.employee_id}"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except DatabaseError as e:
        logger.error(
            f"Database error deleting application {app_id}: {e.message}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database operation failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting application {app_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting application"
        )
