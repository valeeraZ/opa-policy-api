"""Custom policy management and evaluation endpoints."""

import logging
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AdminUser, CurrentUser
from app.schemas.custom_policy import (
    CustomPolicyCreate,
    CustomPolicyResponse,
    CustomPolicyEvaluate,
    CustomPolicyEvaluationResult,
)
from app.services.custom_policy_service import CustomPolicyService
from app.services.opa_service import OPAService
from app.services.s3_service import S3Service
from app.config import settings
from app.exceptions import ValidationError, OPAConnectionError, S3Error, DatabaseError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/custom-policies", tags=["custom-policies"])


def get_custom_policy_service(
    db: Annotated[Session, Depends(get_db)],
) -> CustomPolicyService:
    """
    Dependency to create CustomPolicyService instance.

    Args:
        db: Database session

    Returns:
        CustomPolicyService instance
    """
    opa_service = OPAService(opa_url=settings.opa_url, timeout=settings.opa_timeout)
    s3_service = S3Service()
    return CustomPolicyService(db, opa_service, s3_service)


@router.post(
    "",
    response_model=CustomPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a custom policy",
    description="Upload and validate a custom Rego policy (admin only)",
)
async def upload_custom_policy(
    policy_data: CustomPolicyCreate,
    admin_user: AdminUser,
    service: Annotated[CustomPolicyService, Depends(get_custom_policy_service)],
) -> CustomPolicyResponse:
    """
    Upload a custom Rego policy with validation.

    This endpoint:
    1. Validates admin authorization
    2. Validates Rego policy syntax using OPA
    3. Stores the policy in S3
    4. Saves policy metadata to the database
    5. Uploads the policy to OPA for evaluation
    6. Logs the operation for audit purposes

    Args:
        policy_data: Custom policy creation data including Rego content
        admin_user: Authenticated admin user
        service: CustomPolicyService instance

    Returns:
        CustomPolicyResponse with created policy metadata

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 400 if Rego policy has syntax errors
        HTTPException: 409 if policy ID already exists
        HTTPException: 500 if storage or OPA operation fails
    """
    logger.info(
        f"Admin user {admin_user.employee_id} uploading custom policy: {policy_data.id}"
    )

    try:
        created_policy = await service.upload_policy(
            policy_data=policy_data, creator_id=admin_user.employee_id
        )

        logger.info(
            f"Custom policy {created_policy.id} uploaded successfully by user {admin_user.employee_id}"
        )

        return CustomPolicyResponse.model_validate(created_policy)

    except ValidationError as e:
        logger.warning(
            f"Validation error uploading custom policy {policy_data.id}: {e.message}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{e.message}: {e.detail}" if e.detail else e.message,
        )
    except DatabaseError as e:
        # Check if it's a duplicate key error
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            logger.warning(f"Duplicate policy ID {policy_data.id}: {e.message}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Policy with id '{policy_data.id}' already exists",
            )
        logger.error(
            f"Database error uploading custom policy {policy_data.id}: {e.message}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database operation failed: {e.message}",
        )
    except S3Error as e:
        logger.error(f"S3 error uploading custom policy {policy_data.id}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store policy in S3: {e.message}",
        )
    except OPAConnectionError as e:
        logger.error(f"OPA error uploading custom policy {policy_data.id}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to upload policy to OPA: {e.message}",
        )
    except Exception as e:
        logger.error(f"Unexpected error uploading custom policy {policy_data.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while uploading custom policy",
        )


@router.get(
    "",
    response_model=List[CustomPolicyResponse],
    status_code=status.HTTP_200_OK,
    summary="List all custom policies",
    description="Retrieve all custom policies",
)
async def list_custom_policies(
    current_user: CurrentUser,
    service: Annotated[CustomPolicyService, Depends(get_custom_policy_service)],
) -> List[CustomPolicyResponse]:
    """
    Retrieve all custom policies.

    This endpoint fetches all custom policy metadata from the database.
    Requires authentication.

    Args:
        current_user: Authenticated user
        service: CustomPolicyService instance

    Returns:
        List of CustomPolicyResponse objects

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 500 if database operation fails
    """
    logger.debug(f"User {current_user.employee_id} listing all custom policies")

    try:
        policies = await service.list_policies()

        logger.info(
            f"User {current_user.employee_id} retrieved {len(policies)} custom policies"
        )

        return [CustomPolicyResponse.model_validate(p) for p in policies]

    except DatabaseError as e:
        logger.error(f"Database error listing custom policies: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database operation failed: {e.message}",
        )
    except Exception as e:
        logger.error(f"Unexpected error listing custom policies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while listing custom policies",
        )


@router.get(
    "/{policy_id}",
    response_model=CustomPolicyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get custom policy by ID",
    description="Retrieve a specific custom policy by its ID",
)
async def get_custom_policy(
    policy_id: str,
    current_user: CurrentUser,
    service: Annotated[CustomPolicyService, Depends(get_custom_policy_service)],
) -> CustomPolicyResponse:
    """
    Retrieve a specific custom policy by ID.

    This endpoint fetches a single custom policy metadata from the database.
    Requires authentication.

    Args:
        policy_id: Policy identifier
        current_user: Authenticated user
        service: CustomPolicyService instance

    Returns:
        CustomPolicyResponse with policy metadata

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 404 if policy not found
        HTTPException: 500 if database operation fails
    """
    logger.debug(
        f"User {current_user.employee_id} retrieving custom policy: {policy_id}"
    )

    try:
        policy = await service.get_policy(policy_id)

        if not policy:
            logger.warning(f"Custom policy not found: {policy_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Custom policy with id '{policy_id}' not found",
            )

        logger.debug(
            f"User {current_user.employee_id} retrieved custom policy: {policy_id}"
        )

        return CustomPolicyResponse.model_validate(policy)

    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except DatabaseError as e:
        logger.error(
            f"Database error retrieving custom policy {policy_id}: {e.message}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database operation failed: {e.message}",
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving custom policy {policy_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving custom policy",
        )


@router.post(
    "/{policy_id}/evaluate",
    response_model=CustomPolicyEvaluationResult,
    status_code=status.HTTP_200_OK,
    summary="Evaluate a custom policy",
    description="Evaluate a custom policy with provided input data",
)
async def evaluate_custom_policy(
    policy_id: str,
    evaluation_request: CustomPolicyEvaluate,
    current_user: CurrentUser,
    service: Annotated[CustomPolicyService, Depends(get_custom_policy_service)],
) -> CustomPolicyEvaluationResult:
    """
    Evaluate a custom policy with provided input data.

    This endpoint:
    1. Validates user authentication
    2. Verifies the policy exists
    3. Sends the input data to OPA for evaluation
    4. Returns the evaluation result
    5. Logs the operation for audit purposes

    Args:
        policy_id: Policy identifier
        evaluation_request: Input data for policy evaluation
        current_user: Authenticated user
        service: CustomPolicyService instance

    Returns:
        CustomPolicyEvaluationResult with OPA decision

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 404 if policy not found
        HTTPException: 503 if OPA server is unreachable
        HTTPException: 500 if evaluation fails
    """
    logger.info(
        f"User {current_user.employee_id} evaluating custom policy: {policy_id}"
    )

    try:
        result = await service.evaluate_policy(
            policy_id=policy_id, input_data=evaluation_request.input_data
        )

        logger.info(
            f"Custom policy {policy_id} evaluated successfully for user {current_user.employee_id}"
        )

        return CustomPolicyEvaluationResult(policy_id=policy_id, result=result)

    except ValidationError as e:
        logger.warning(
            f"Validation error evaluating custom policy {policy_id}: {e.message}"
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except OPAConnectionError as e:
        logger.error(f"OPA error evaluating custom policy {policy_id}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to evaluate policy: {e.message}",
        )
    except Exception as e:
        logger.error(f"Unexpected error evaluating custom policy {policy_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while evaluating custom policy",
        )
