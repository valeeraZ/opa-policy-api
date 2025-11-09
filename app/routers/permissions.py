"""Permission evaluation endpoints."""

import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.permission import PermissionResponse, AppPermissionResponse
from app.schemas.user import UserInfo
from app.services.application_service import ApplicationService
from app.services.opa_service import OPAService
from app.exceptions import OPAConnectionError, DatabaseError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/permission", tags=["permissions"])


def get_opa_service() -> OPAService:
    """Dependency to get OPA service instance."""
    return OPAService()


@router.post(
    "",
    response_model=PermissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate permissions for all applications",
    description="Decode user token and return permission levels for all applications",
)
async def evaluate_all_permissions(
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    opa_service: Annotated[OPAService, Depends(get_opa_service)],
) -> PermissionResponse:
    """
    Evaluate permissions for all applications for the authenticated user.

    This endpoint:
    1. Extracts user information from the authentication token
    2. Fetches all applications from the database
    3. Fetches all role mappings from the database
    4. Calls OPA to evaluate permissions
    5. Returns a dictionary mapping application IDs to permission levels

    Args:
        current_user: Authenticated user information from token
        db: Database session
        opa_service: OPA service instance

    Returns:
        PermissionResponse containing permissions for all applications

    Raises:
        HTTPException: 401 if token is invalid (handled by dependency)
        HTTPException: 503 if OPA server is unreachable
        HTTPException: 500 if database operation fails
    """
    logger.info(f"Evaluating permissions for user: {current_user.employee_id}")

    try:
        # Fetch all applications
        app_service = ApplicationService(db)
        applications = app_service.list_applications()

        if not applications:
            logger.info("No applications found in database")
            return PermissionResponse(permissions={})

        # Convert to model objects for OPA service
        from app.models.application import Application

        app_models = [
            Application(id=app.id, name=app.name, description=app.description)
            for app in applications
        ]

        # Fetch all role mappings
        # role_mapping_service = RoleMappingService(db, opa_service)
        # role_mappings_response = await role_mapping_service.get_role_mappings()

        # Convert to model objects for OPA service
        # from app.models.role_mapping import RoleMapping
        # role_mapping_models = [
        #     RoleMapping(
        #         id=rm.id,
        #         application_id=rm.application_id,
        #         environment=rm.environment,
        #         ad_group=rm.ad_group,
        #         role=rm.role
        #     )
        #     for rm in role_mappings_response
        # ]

        # Evaluate permissions via OPA
        permissions = await opa_service.evaluate_permissions(
            user_info=current_user,
            applications=app_models,
        )

        logger.info(
            f"Successfully evaluated permissions for user {current_user.employee_id}: "
            f"{len(permissions)} applications"
        )

        return PermissionResponse(permissions=permissions)

    except OPAConnectionError as e:
        logger.error(f"OPA connection error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OPA server is unreachable: {e.message}",
        )
    except DatabaseError as e:
        logger.error(f"Database error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database operation failed: {e.message}",
        )
    except Exception as e:
        logger.error(f"Unexpected error evaluating permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while evaluating permissions",
        )


@router.get(
    "/{app_id}",
    response_model=AppPermissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate permission for a specific application",
    description="Check user's permission level for a single application",
)
async def evaluate_app_permission(
    app_id: str,
    current_user: Annotated[UserInfo, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    opa_service: Annotated[OPAService, Depends(get_opa_service)],
) -> AppPermissionResponse:
    """
    Evaluate permission for a specific application for the authenticated user.

    This endpoint:
    1. Extracts user information from the authentication token
    2. Fetches the specified application from the database
    3. Fetches all role mappings from the database
    4. Calls OPA to evaluate permissions
    5. Returns the permission level for the specified application

    Args:
        app_id: Application identifier
        current_user: Authenticated user information from token
        db: Database session
        opa_service: OPA service instance

    Returns:
        AppPermissionResponse containing permission for the specified application

    Raises:
        HTTPException: 401 if token is invalid (handled by dependency)
        HTTPException: 404 if application does not exist
        HTTPException: 503 if OPA server is unreachable
        HTTPException: 500 if database operation fails
    """
    logger.info(
        f"Evaluating permission for user {current_user.employee_id} on app: {app_id}"
    )

    try:
        # Fetch the specific application
        app_service = ApplicationService(db)
        application = app_service.get_application(app_id)

        if not application:
            logger.warning(f"Application not found: {app_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with id '{app_id}' not found",
            )

        # Convert to model object for OPA service
        from app.models.application import Application

        app_model = Application(
            id=application.id,
            name=application.name,
            description=application.description,
        )

        # Fetch all role mappings
        # role_mapping_service = RoleMappingService(db, opa_service)
        # role_mappings_response = await role_mapping_service.get_role_mappings()

        # Convert to model objects for OPA service
        # from app.models.role_mapping import RoleMapping
        # role_mapping_models = [
        #     RoleMapping(
        #         id=rm.id,
        #         application_id=rm.application_id,
        #         environment=rm.environment,
        #         ad_group=rm.ad_group,
        #         role=rm.role
        #     )
        #     for rm in role_mappings_response
        # ]

        # Evaluate permissions via OPA (for all apps, then extract the one we need)
        permissions = await opa_service.evaluate_permissions(
            user_info=current_user,
            applications=[app_model],
        )

        # Extract the permission for the requested application
        role = permissions.get(app_id, "none")

        logger.info(
            f"Successfully evaluated permission for user {current_user.employee_id} "
            f"on app {app_id}: {role}"
        )

        return AppPermissionResponse(application_id=app_id, role=role)

    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except OPAConnectionError as e:
        logger.error(f"OPA connection error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OPA server is unreachable: {e.message}",
        )
    except DatabaseError as e:
        logger.error(f"Database error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database operation failed: {e.message}",
        )
    except Exception as e:
        logger.error(f"Unexpected error evaluating permission for app {app_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while evaluating permission",
        )
