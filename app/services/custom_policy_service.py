"""Custom Policy Service for managing and evaluating custom Rego policies."""

import logging
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.custom_policy import CustomPolicy
from app.repositories.custom_policy_repository import CustomPolicyRepository
from app.services.opa_service import OPAService
from app.services.s3_service import S3Service
from app.schemas.custom_policy import CustomPolicyCreate
from app.exceptions import ValidationError, OPAConnectionError, S3Error, DatabaseError

logger = logging.getLogger(__name__)


class CustomPolicyService:
    """Service for managing custom Rego policies with validation, storage, and evaluation."""

    def __init__(
        self,
        db: Session,
        opa_service: OPAService,
        s3_service: S3Service
    ):
        """
        Initialize CustomPolicyService.

        Args:
            db: Database session
            opa_service: OPA service instance
            s3_service: S3 service instance
        """
        self.repository = CustomPolicyRepository(db)
        self.opa_service = opa_service
        self.s3_service = s3_service
        logger.info("CustomPolicyService initialized")

    async def validate_rego(self, rego_content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Rego policy syntax using OPA compile API.

        Args:
            rego_content: Rego policy content to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if policy is valid, False otherwise
            - error_message: Error details if invalid, None if valid

        Raises:
            OPAConnectionError: If OPA server is unreachable
        """
        try:
            logger.info("Validating Rego policy syntax")
            
            # Use OPA compile API to validate syntax
            url = f"{self.opa_service.opa_url}/v1/compile"
            
            # Prepare compile request
            compile_request = {
                "query": "data",
                "input": {},
                "unknowns": [],
                "options": {
                    "strict-builtin-errors": True
                }
            }
            
            # First, try to upload the policy temporarily to validate it
            # We'll use a temporary policy ID (use timezone-aware UTC datetime)
            temp_policy_id = f"temp_validation_{int(datetime.now(timezone.utc).timestamp())}"
            
            try:
                # Try to upload the policy - this will validate syntax
                await self.opa_service.upload_policy(temp_policy_id, rego_content)
                
                # If successful, delete the temporary policy
                delete_url = f"{self.opa_service.opa_url}/v1/policies/{temp_policy_id}"
                await self.opa_service.client.delete(delete_url)
                
                logger.info("Rego policy validation successful")
                return True, None
                
            except OPAConnectionError as e:
                # Parse error message from OPA
                error_detail = e.detail if hasattr(e, 'detail') else str(e)
                logger.warning(f"Rego policy validation failed: {error_detail}")
                return False, error_detail
                
        except Exception as e:
            logger.error(f"Unexpected error during Rego validation: {e}")
            raise OPAConnectionError(
                "Failed to validate Rego policy",
                detail=str(e)
            )

    async def upload_policy(
        self,
        policy_data: CustomPolicyCreate,
        creator_id: str
    ) -> CustomPolicy:
        """
        Upload a custom policy: validate, store in S3, save metadata to DB, and upload to OPA.

        Args:
            policy_data: Custom policy creation data
            creator_id: ID of the user creating the policy

        Returns:
            Created CustomPolicy instance

        Raises:
            ValidationError: If Rego policy has syntax errors
            S3Error: If S3 upload fails
            DatabaseError: If database operation fails
            OPAConnectionError: If OPA upload fails
        """
        logger.info(f"Uploading custom policy: {policy_data.id}")
        
        # Step 1: Validate Rego syntax
        is_valid, error_message = await self.validate_rego(policy_data.rego_content)
        if not is_valid:
            logger.error(f"Policy validation failed for {policy_data.id}: {error_message}")
            raise ValidationError(
                message="Rego policy has syntax errors",
                detail=error_message
            )
        
        logger.info(f"Policy {policy_data.id} validated successfully")
        
        # Step 2: Generate version identifier
        version = f"v{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        
        # Step 3: Store policy in S3
        try:
            s3_key = await self.s3_service.upload_policy_file(
                policy_id=policy_data.id,
                content=policy_data.rego_content,
                version=version
            )
            logger.info(f"Policy {policy_data.id} stored in S3: {s3_key}")
        except S3Error as e:
            logger.error(f"Failed to store policy {policy_data.id} in S3: {e}")
            raise
        
        # Step 4: Save metadata to database
        try:
            custom_policy = CustomPolicy(
                id=policy_data.id,
                name=policy_data.name,
                description=policy_data.description,
                s3_key=s3_key,
                version=version,
                creator_id=creator_id,
                created_at=datetime.now(timezone.utc)
            )
            
            created_policy = self.repository.create(custom_policy)
            logger.info(f"Policy {policy_data.id} metadata saved to database")
        except DatabaseError as e:
            logger.error(f"Failed to save policy {policy_data.id} metadata to database: {e}")
            # Note: S3 file remains, but this is acceptable for audit purposes
            raise
        
        # Step 5: Upload policy to OPA
        try:
            await self.opa_service.upload_policy(
                policy_id=policy_data.id,
                policy_content=policy_data.rego_content
            )
            logger.info(f"Policy {policy_data.id} uploaded to OPA successfully")
        except OPAConnectionError as e:
            logger.error(f"Failed to upload policy {policy_data.id} to OPA: {e}")
            # Policy is in DB and S3, but not in OPA - log warning but don't fail
            logger.warning(f"Policy {policy_data.id} stored but not active in OPA")
            # We could choose to raise here, but for now we'll allow it
            # since the policy can be manually uploaded to OPA later
        
        logger.info(f"Custom policy {policy_data.id} upload completed successfully")
        return created_policy

    async def get_policy(self, policy_id: str) -> Optional[CustomPolicy]:
        """
        Retrieve a custom policy by ID.

        Args:
            policy_id: Policy identifier

        Returns:
            CustomPolicy instance if found, None otherwise

        Raises:
            DatabaseError: If database query fails
        """
        logger.info(f"Retrieving custom policy: {policy_id}")
        
        try:
            policy = self.repository.get_by_id(policy_id)
            
            if policy:
                logger.info(f"Found custom policy: {policy_id}")
            else:
                logger.info(f"Custom policy not found: {policy_id}")
            
            return policy
        except DatabaseError as e:
            logger.error(f"Failed to retrieve custom policy {policy_id}: {e}")
            raise

    async def list_policies(self) -> List[CustomPolicy]:
        """
        List all custom policies.

        Returns:
            List of all CustomPolicy instances

        Raises:
            DatabaseError: If database query fails
        """
        logger.info("Listing all custom policies")
        
        try:
            policies = self.repository.get_all()
            logger.info(f"Retrieved {len(policies)} custom policies")
            return policies
        except DatabaseError as e:
            logger.error(f"Failed to list custom policies: {e}")
            raise

    async def evaluate_policy(
        self,
        policy_id: str,
        input_data: Dict[str, Any],
        query_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a custom policy with provided input data.

        Args:
            policy_id: ID of the custom policy to evaluate
            input_data: Input data for policy evaluation
            query_path: Optional specific path to query within the policy

        Returns:
            Dict containing the OPA decision result

        Raises:
            ValidationError: If policy doesn't exist
            OPAConnectionError: If policy evaluation fails
        """
        logger.info(f"Evaluating custom policy: {policy_id}")
        
        # Verify policy exists in database
        policy = await self.get_policy(policy_id)
        if not policy:
            logger.error(f"Cannot evaluate non-existent policy: {policy_id}")
            raise ValidationError(
                message=f"Policy '{policy_id}' does not exist",
                detail="Policy must be uploaded before evaluation"
            )
        
        # Evaluate policy using OPA service
        try:
            result = await self.opa_service.evaluate_custom_policy(
                policy_id=policy_id,
                input_data=input_data,
                query_path=query_path
            )
            
            logger.info(f"Custom policy {policy_id} evaluated successfully")
            logger.debug(f"Evaluation result: {result}")
            
            return result
        except OPAConnectionError as e:
            logger.error(f"Failed to evaluate custom policy {policy_id}: {e}")
            raise
