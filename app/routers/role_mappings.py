"""Role mapping management endpoints."""

import logging
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AdminUser
from app.schemas.role_mapping import RoleMappingCreate, RoleMappingUpdate, RoleMappingResponse
from app.services.role_mapping_service import RoleMappingService
from app.services.opa_service import OPAService
from app.exceptions import DatabaseError, ValidationError, OPAConnectionError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/role-mappings", tags=["role-mappings"])


def get_opa_service() -> OPAService:
    """Dependency to get OPA service instance."""
    return OPAService()


@router.post(
    "",
    response_model=RoleMappingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new role mapping",
    description="Create a new role mapping with admin authorization and OPA sync"
)
async def create_role_mapping(
    mapping_data: RoleMappingCreate,
    admin_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
    opa_service: Annotated[OPAService, Depends(get_opa_service)]
) -> RoleMappingResponse:
    """
    Create a new role mapping with admin authorization.
    
    This endpoint:
    1. Validates admin authorization
    2. Checks for duplicate role mappings (app_id + environment + ad_group)
    3. Creates the role mapping in the database
    4. Synchronizes all role mappings to OPA
    5. Logs the operation for audit purposes
    
    Args:
        mapping_data: Role mapping creation data
        admin_user: Authenticated admin user
        db: Database session
        opa_service: OPA service instance
        
    Returns:
        RoleMappingResponse with created role mapping details
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 409 if role mapping conflicts with existing mapping
        HTTPException: 500 if database operation fails
        HTTPException: 503 if OPA synchronization fails
    """
    logger.info(
        f"Admin user {admin_user.employee_id} creating role mapping: "
        f"app={mapping_data.application_id}, env={mapping_data.environment}, "
        f"group={mapping_data.ad_group}"
    )
    
    try:
        role_mapping_service = RoleMappingService(db, opa_service)
        created_mapping = await role_mapping_service.create_role_mapping(mapping_data)
        
        logger.info(
            f"Role mapping {created_mapping.id} created successfully by user {admin_user.employee_id}"
        )
        
        return created_mapping
        
    except DatabaseError as e:
        # Check if it's a conflict error
        if "unique constraint" in str(e.message).lower() or "already exists" in str(e.message).lower():
            logger.warning(
                f"Conflict creating role mapping: {e.message}"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=e.message
            )
        else:
            logger.error(
                f"Database error creating role mapping: {e.message}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database operation failed: {e.message}"
            )
    except OPAConnectionError as e:
        logger.error(
            f"OPA synchronization error after creating role mapping: {e.message}"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Role mapping created but OPA sync failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating role mapping: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating role mapping"
        )


@router.get(
    "",
    response_model=List[RoleMappingResponse],
    status_code=status.HTTP_200_OK,
    summary="List role mappings",
    description="Retrieve all role mappings with optional application ID filter"
)
async def list_role_mappings(
    db: Annotated[Session, Depends(get_db)],
    opa_service: Annotated[OPAService, Depends(get_opa_service)],
    app_id: Optional[str] = Query(None, description="Filter by application ID")
) -> List[RoleMappingResponse]:
    """
    Retrieve all role mappings with optional application ID filter.
    
    This endpoint fetches role mappings from the database.
    No authentication required for listing role mappings.
    
    Args:
        app_id: Optional application ID to filter results
        db: Database session
        opa_service: OPA service instance
        
    Returns:
        List of RoleMappingResponse objects
        
    Raises:
        HTTPException: 500 if database operation fails
    """
    if app_id:
        logger.debug(f"Listing role mappings for application: {app_id}")
    else:
        logger.debug("Listing all role mappings")
    
    try:
        role_mapping_service = RoleMappingService(db, opa_service)
        mappings = await role_mapping_service.get_role_mappings(app_id=app_id)
        
        logger.info(f"Retrieved {len(mappings)} role mappings")
        
        return mappings
        
    except DatabaseError as e:
        logger.error(f"Database error listing role mappings: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database operation failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"Unexpected error listing role mappings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while listing role mappings"
        )


@router.put(
    "/{mapping_id}",
    response_model=RoleMappingResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a role mapping",
    description="Update an existing role mapping with admin authorization and OPA sync"
)
async def update_role_mapping(
    mapping_id: int,
    mapping_data: RoleMappingUpdate,
    admin_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
    opa_service: Annotated[OPAService, Depends(get_opa_service)]
) -> RoleMappingResponse:
    """
    Update an existing role mapping with admin authorization.
    
    This endpoint:
    1. Validates admin authorization
    2. Checks if role mapping exists
    3. Updates the role mapping in the database
    4. Synchronizes all role mappings to OPA
    5. Logs the operation for audit purposes
    
    Args:
        mapping_id: Role mapping identifier
        mapping_data: Role mapping update data
        admin_user: Authenticated admin user
        db: Database session
        opa_service: OPA service instance
        
    Returns:
        RoleMappingResponse with updated role mapping details
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 404 if role mapping not found
        HTTPException: 409 if update causes conflict
        HTTPException: 500 if database operation fails
        HTTPException: 503 if OPA synchronization fails
    """
    logger.info(
        f"Admin user {admin_user.employee_id} updating role mapping: {mapping_id}"
    )
    
    try:
        role_mapping_service = RoleMappingService(db, opa_service)
        updated_mapping = await role_mapping_service.update_role_mapping(
            mapping_id, mapping_data
        )
        
        logger.info(
            f"Role mapping {mapping_id} updated successfully by user {admin_user.employee_id}"
        )
        
        return updated_mapping
        
    except ValidationError as e:
        logger.warning(
            f"Validation error updating role mapping {mapping_id}: {e.message}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except DatabaseError as e:
        # Check if it's a conflict error
        if "unique constraint" in str(e.message).lower() or "already exists" in str(e.message).lower():
            logger.warning(
                f"Conflict updating role mapping {mapping_id}: {e.message}"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=e.message
            )
        else:
            logger.error(
                f"Database error updating role mapping {mapping_id}: {e.message}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database operation failed: {e.message}"
            )
    except OPAConnectionError as e:
        logger.error(
            f"OPA synchronization error after updating role mapping {mapping_id}: {e.message}"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Role mapping updated but OPA sync failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"Unexpected error updating role mapping {mapping_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating role mapping"
        )


@router.delete(
    "/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a role mapping",
    description="Delete an existing role mapping with admin authorization and OPA sync"
)
async def delete_role_mapping(
    mapping_id: int,
    admin_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
    opa_service: Annotated[OPAService, Depends(get_opa_service)]
) -> None:
    """
    Delete an existing role mapping with admin authorization.
    
    This endpoint:
    1. Validates admin authorization
    2. Deletes the role mapping from the database
    3. Synchronizes all role mappings to OPA
    4. Logs the operation for audit purposes
    
    Args:
        mapping_id: Role mapping identifier
        admin_user: Authenticated admin user
        db: Database session
        opa_service: OPA service instance
        
    Returns:
        None (204 No Content)
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 404 if role mapping not found
        HTTPException: 500 if database operation fails
        HTTPException: 503 if OPA synchronization fails
    """
    logger.info(
        f"Admin user {admin_user.employee_id} deleting role mapping: {mapping_id}"
    )
    
    try:
        role_mapping_service = RoleMappingService(db, opa_service)
        deleted = await role_mapping_service.delete_role_mapping(mapping_id)
        
        if not deleted:
            logger.warning(f"Role mapping not found for deletion: {mapping_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role mapping with id '{mapping_id}' not found"
            )
        
        logger.info(
            f"Role mapping {mapping_id} deleted successfully by user {admin_user.employee_id}"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except DatabaseError as e:
        logger.error(
            f"Database error deleting role mapping {mapping_id}: {e.message}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database operation failed: {e.message}"
        )
    except OPAConnectionError as e:
        logger.error(
            f"OPA synchronization error after deleting role mapping {mapping_id}: {e.message}"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Role mapping deleted but OPA sync failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting role mapping {mapping_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting role mapping"
        )
