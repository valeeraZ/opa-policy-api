"""Repository for CustomPolicy database operations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging

from app.models.custom_policy import CustomPolicy
from app.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class CustomPolicyRepository:
    """Repository for managing CustomPolicy entities."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, custom_policy: CustomPolicy) -> CustomPolicy:
        """
        Create a new custom policy.
        
        Args:
            custom_policy: CustomPolicy instance to create
            
        Returns:
            Created CustomPolicy instance
            
        Raises:
            DatabaseError: If creation fails or policy_id already exists
        """
        try:
            self.db.add(custom_policy)
            self.db.commit()
            self.db.refresh(custom_policy)
            logger.info(f"Created custom policy: {custom_policy.id}")
            return custom_policy
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Custom policy with id {custom_policy.id} already exists: {e}")
            raise DatabaseError(
                message=f"Custom policy with id '{custom_policy.id}' already exists",
                detail=str(e)
            )
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating custom policy: {e}")
            raise DatabaseError(
                message="Failed to create custom policy",
                detail=str(e)
            )

    def get_by_id(self, policy_id: str) -> Optional[CustomPolicy]:
        """
        Retrieve a custom policy by ID.
        
        Args:
            policy_id: Custom policy ID
            
        Returns:
            CustomPolicy instance if found, None otherwise
            
        Raises:
            DatabaseError: If query fails
        """
        try:
            return self.db.query(CustomPolicy).filter(CustomPolicy.id == policy_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving custom policy {policy_id}: {e}")
            raise DatabaseError(
                message=f"Failed to retrieve custom policy {policy_id}",
                detail=str(e)
            )

    def get_all(self) -> List[CustomPolicy]:
        """
        Retrieve all custom policies.
        
        Returns:
            List of all CustomPolicy instances
            
        Raises:
            DatabaseError: If query fails
        """
        try:
            return self.db.query(CustomPolicy).all()
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving custom policies: {e}")
            raise DatabaseError(
                message="Failed to retrieve custom policies",
                detail=str(e)
            )

    def update(self, custom_policy: CustomPolicy) -> CustomPolicy:
        """
        Update an existing custom policy.
        
        Args:
            custom_policy: CustomPolicy instance with updated values
            
        Returns:
            Updated CustomPolicy instance
            
        Raises:
            DatabaseError: If update fails
        """
        try:
            self.db.commit()
            self.db.refresh(custom_policy)
            logger.info(f"Updated custom policy: {custom_policy.id}")
            return custom_policy
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating custom policy {custom_policy.id}: {e}")
            raise DatabaseError(
                message=f"Failed to update custom policy {custom_policy.id}",
                detail=str(e)
            )

    def delete(self, policy_id: str) -> bool:
        """
        Delete a custom policy by ID.
        
        Args:
            policy_id: Custom policy ID to delete
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            DatabaseError: If deletion fails
        """
        try:
            custom_policy = self.get_by_id(policy_id)
            if not custom_policy:
                return False
            
            self.db.delete(custom_policy)
            self.db.commit()
            logger.info(f"Deleted custom policy: {policy_id}")
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting custom policy {policy_id}: {e}")
            raise DatabaseError(
                message=f"Failed to delete custom policy {policy_id}",
                detail=str(e)
            )
