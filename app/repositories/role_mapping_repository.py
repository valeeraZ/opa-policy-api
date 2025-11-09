"""Repository for RoleMapping database operations."""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging

from app.models.role_mapping import RoleMapping
from app.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class RoleMappingRepository:
    """Repository for managing RoleMapping entities."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, role_mapping: RoleMapping) -> RoleMapping:
        """
        Create a new role mapping.
        
        Args:
            role_mapping: RoleMapping instance to create
            
        Returns:
            Created RoleMapping instance
            
        Raises:
            DatabaseError: If creation fails or unique constraint is violated
        """
        try:
            self.db.add(role_mapping)
            self.db.commit()
            self.db.refresh(role_mapping)
            logger.info(
                f"Created role mapping: app={role_mapping.application_id}, "
                f"env={role_mapping.environment}, group={role_mapping.ad_group}"
            )
            return role_mapping
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Role mapping conflict: {e}")
            raise DatabaseError(
                message=(
                    f"Role mapping already exists for application '{role_mapping.application_id}', "
                    f"environment '{role_mapping.environment}', and AD group '{role_mapping.ad_group}'"
                ),
                detail=str(e)
            )
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating role mapping: {e}")
            raise DatabaseError(
                message="Failed to create role mapping",
                detail=str(e)
            )

    def get_by_id(self, mapping_id: int) -> Optional[RoleMapping]:
        """
        Retrieve a role mapping by ID.
        
        Args:
            mapping_id: Role mapping ID
            
        Returns:
            RoleMapping instance if found, None otherwise
            
        Raises:
            DatabaseError: If query fails
        """
        try:
            return self.db.query(RoleMapping).filter(RoleMapping.id == mapping_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving role mapping {mapping_id}: {e}")
            raise DatabaseError(
                message=f"Failed to retrieve role mapping {mapping_id}",
                detail=str(e)
            )

    def get_all(self, application_id: Optional[str] = None) -> List[RoleMapping]:
        """
        Retrieve all role mappings, optionally filtered by application ID.
        
        Args:
            application_id: Optional application ID to filter by
            
        Returns:
            List of RoleMapping instances
            
        Raises:
            DatabaseError: If query fails
        """
        try:
            query = self.db.query(RoleMapping)
            if application_id:
                query = query.filter(RoleMapping.application_id == application_id)
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving role mappings: {e}")
            raise DatabaseError(
                message="Failed to retrieve role mappings",
                detail=str(e)
            )

    def get_all_as_opa_data(self) -> Dict[str, Any]:
        """
        Retrieve all role mappings formatted for OPA data structure.
        
        Returns a nested dictionary structure:
        {
            "role_mappings": {
                "app-id": {
                    "ENV": {
                        "ad-group": "role"
                    }
                }
            }
        }
        
        Returns:
            Dictionary formatted for OPA consumption
            
        Raises:
            DatabaseError: If query fails
        """
        try:
            mappings = self.get_all()
            opa_data = {"role_mappings": {}}
            
            for mapping in mappings:
                app_id = mapping.application_id
                env = mapping.environment
                ad_group = mapping.ad_group
                role = mapping.role
                
                # Initialize nested structure if needed
                if app_id not in opa_data["role_mappings"]:
                    opa_data["role_mappings"][app_id] = {}
                
                if env not in opa_data["role_mappings"][app_id]:
                    opa_data["role_mappings"][app_id][env] = {}
                
                # Add the mapping
                opa_data["role_mappings"][app_id][env][ad_group] = role
            
            logger.debug(f"Formatted {len(mappings)} role mappings for OPA")
            return opa_data
        except SQLAlchemyError as e:
            logger.error(f"Database error formatting role mappings for OPA: {e}")
            raise DatabaseError(
                message="Failed to format role mappings for OPA",
                detail=str(e)
            )

    def update(self, role_mapping: RoleMapping) -> RoleMapping:
        """
        Update an existing role mapping.
        
        Args:
            role_mapping: RoleMapping instance with updated values
            
        Returns:
            Updated RoleMapping instance
            
        Raises:
            DatabaseError: If update fails or unique constraint is violated
        """
        try:
            self.db.commit()
            self.db.refresh(role_mapping)
            logger.info(f"Updated role mapping: {role_mapping.id}")
            return role_mapping
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Role mapping conflict during update: {e}")
            raise DatabaseError(
                message="Role mapping conflict: combination already exists",
                detail=str(e)
            )
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating role mapping {role_mapping.id}: {e}")
            raise DatabaseError(
                message=f"Failed to update role mapping {role_mapping.id}",
                detail=str(e)
            )

    def delete(self, mapping_id: int) -> bool:
        """
        Delete a role mapping by ID.
        
        Args:
            mapping_id: Role mapping ID to delete
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            DatabaseError: If deletion fails
        """
        try:
            role_mapping = self.get_by_id(mapping_id)
            if not role_mapping:
                return False
            
            self.db.delete(role_mapping)
            self.db.commit()
            logger.info(f"Deleted role mapping: {mapping_id}")
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting role mapping {mapping_id}: {e}")
            raise DatabaseError(
                message=f"Failed to delete role mapping {mapping_id}",
                detail=str(e)
            )
