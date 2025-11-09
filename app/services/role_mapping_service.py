"""Service layer for role mapping management."""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.role_mapping import RoleMapping
from app.repositories.role_mapping_repository import RoleMappingRepository
from app.schemas.role_mapping import (
    RoleMappingCreate,
    RoleMappingUpdate,
    RoleMappingResponse,
)
from app.services.opa_service import OPAService
from app.exceptions import DatabaseError, ValidationError, OPAConnectionError

logger = logging.getLogger(__name__)


class RoleMappingService:
    """Service for managing role mappings with business logic, OPA sync, and logging."""

    def __init__(self, db: Session, opa_service: OPAService):
        """
        Initialize RoleMappingService.

        Args:
            db: Database session
            opa_service: OPA service for policy data synchronization
        """
        self.db = db
        self.repository = RoleMappingRepository(db)
        self.opa_service = opa_service

    async def create_role_mapping(
        self, mapping_data: RoleMappingCreate
    ) -> RoleMappingResponse:
        """
        Create a new role mapping with conflict detection and OPA sync.

        Args:
            mapping_data: Role mapping creation data

        Returns:
            Created role mapping response

        Raises:
            DatabaseError: If role mapping conflicts or database operation fails
            OPAConnectionError: If OPA synchronization fails
        """
        logger.info(
            f"Creating role mapping: app={mapping_data.application_id}, "
            f"env={mapping_data.environment}, group={mapping_data.ad_group}"
        )

        # Create role mapping model
        role_mapping = RoleMapping(
            application_id=mapping_data.application_id,
            environment=mapping_data.environment,
            ad_group=mapping_data.ad_group,
            role=mapping_data.role,
        )

        try:
            # Create in database (repository handles conflict detection)
            created_mapping = self.repository.create(role_mapping)
            logger.info(
                f"Successfully created role mapping with id: {created_mapping.id}"
            )

            # Sync to OPA
            await self.sync_to_opa()

            return RoleMappingResponse.model_validate(created_mapping)
        except DatabaseError as e:
            logger.error(f"Failed to create role mapping: {e.message}")
            raise
        except OPAConnectionError as e:
            logger.error(
                f"Failed to sync role mappings to OPA after creation: {e.message}"
            )
            # Note: The mapping was created in DB but OPA sync failed
            # Consider if we should rollback or let it be synced later
            raise

    async def get_role_mappings(
        self, app_id: Optional[str] = None
    ) -> List[RoleMappingResponse]:
        """
        Retrieve role mappings with optional application ID filter.

        Args:
            app_id: Optional application ID to filter by

        Returns:
            List of role mapping responses

        Raises:
            DatabaseError: If database operation fails
        """
        if app_id:
            logger.debug(f"Retrieving role mappings for application: {app_id}")
        else:
            logger.debug("Retrieving all role mappings")

        try:
            mappings = self.repository.get_all(application_id=app_id)
            logger.info(f"Retrieved {len(mappings)} role mappings")
            return [RoleMappingResponse.model_validate(mapping) for mapping in mappings]
        except DatabaseError as e:
            logger.error(f"Failed to retrieve role mappings: {e.message}")
            raise

    async def update_role_mapping(
        self, mapping_id: int, mapping_data: RoleMappingUpdate
    ) -> RoleMappingResponse:
        """
        Update an existing role mapping and sync to OPA.

        Args:
            mapping_id: Role mapping identifier
            mapping_data: Updated role mapping data

        Returns:
            Updated role mapping response

        Raises:
            ValidationError: If role mapping not found
            DatabaseError: If database operation fails or conflict occurs
            OPAConnectionError: If OPA synchronization fails
        """
        logger.info(f"Updating role mapping: {mapping_id}")

        # Retrieve existing role mapping
        role_mapping = self.repository.get_by_id(mapping_id)
        if not role_mapping:
            logger.warning(
                f"Attempted to update non-existent role mapping: {mapping_id}"
            )
            raise ValidationError(
                message=f"Role mapping with id '{mapping_id}' not found",
                detail="Cannot update non-existent role mapping",
            )

        # Update fields if provided
        if mapping_data.environment is not None:
            role_mapping.environment = mapping_data.environment
        if mapping_data.ad_group is not None:
            role_mapping.ad_group = mapping_data.ad_group
        if mapping_data.role is not None:
            role_mapping.role = mapping_data.role

        try:
            # Update in database
            updated_mapping = self.repository.update(role_mapping)
            logger.info(f"Successfully updated role mapping: {mapping_id}")

            # Sync to OPA
            await self.sync_to_opa()

            return RoleMappingResponse.model_validate(updated_mapping)
        except DatabaseError as e:
            logger.error(f"Failed to update role mapping {mapping_id}: {e.message}")
            raise
        except OPAConnectionError as e:
            logger.error(
                f"Failed to sync role mappings to OPA after update: {e.message}"
            )
            raise

    async def delete_role_mapping(self, mapping_id: int) -> bool:
        """
        Delete a role mapping by ID and sync to OPA.

        Args:
            mapping_id: Role mapping identifier

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseError: If database operation fails
            OPAConnectionError: If OPA synchronization fails
        """
        logger.info(f"Deleting role mapping: {mapping_id}")

        try:
            deleted = self.repository.delete(mapping_id)
            if deleted:
                logger.info(f"Successfully deleted role mapping: {mapping_id}")

                # Sync to OPA
                await self.sync_to_opa()
            else:
                logger.warning(
                    f"Attempted to delete non-existent role mapping: {mapping_id}"
                )

            return deleted
        except DatabaseError as e:
            logger.error(f"Failed to delete role mapping {mapping_id}: {e.message}")
            raise
        except OPAConnectionError as e:
            logger.error(
                f"Failed to sync role mappings to OPA after deletion: {e.message}"
            )
            raise

    async def sync_to_opa(self) -> bool:
        """
        Synchronize all role mappings to OPA by pushing updated data.

        This method retrieves all role mappings from the database,
        formats them for OPA consumption, and pushes them to OPA's
        data API.

        Returns:
            True if synchronization successful

        Raises:
            DatabaseError: If database operation fails
            OPAConnectionError: If OPA push fails
        """
        logger.info("Synchronizing role mappings to OPA")

        try:
            # Get all role mappings formatted for OPA
            opa_data = self.repository.get_all_as_opa_data()

            # Push to OPA Data API
            # The data structure is already wrapped with "role_mappings" key
            # We need to push just the inner structure to the role_mappings path
            await self.opa_service.push_policy_data(
                data_path="role_mappings", data=opa_data["role_mappings"]
            )

            logger.info("Successfully synchronized role mappings to OPA")
            return True
        except DatabaseError as e:
            logger.error(f"Failed to retrieve role mappings for OPA sync: {e.message}")
            raise
        except OPAConnectionError as e:
            logger.error(f"Failed to push role mappings to OPA: {e.message}")
            raise
