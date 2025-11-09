"""Repository for Application database operations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging

from app.models.application import Application
from app.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class ApplicationRepository:
    """Repository for managing Application entities."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, application: Application) -> Application:
        """
        Create a new application.
        
        Args:
            application: Application instance to create
            
        Returns:
            Created Application instance
            
        Raises:
            DatabaseError: If creation fails or application_id already exists
        """
        try:
            self.db.add(application)
            self.db.commit()
            self.db.refresh(application)
            logger.info(f"Created application: {application.id}")
            return application
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Application with id {application.id} already exists: {e}")
            raise DatabaseError(
                message=f"Application with id '{application.id}' already exists",
                detail=str(e)
            )
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating application: {e}")
            raise DatabaseError(
                message="Failed to create application",
                detail=str(e)
            )

    def get_by_id(self, app_id: str) -> Optional[Application]:
        """
        Retrieve an application by ID.
        
        Args:
            app_id: Application ID
            
        Returns:
            Application instance if found, None otherwise
            
        Raises:
            DatabaseError: If query fails
        """
        try:
            return self.db.query(Application).filter(Application.id == app_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving application {app_id}: {e}")
            raise DatabaseError(
                message=f"Failed to retrieve application {app_id}",
                detail=str(e)
            )

    def get_all(self) -> List[Application]:
        """
        Retrieve all applications.
        
        Returns:
            List of all Application instances
            
        Raises:
            DatabaseError: If query fails
        """
        try:
            return self.db.query(Application).all()
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving applications: {e}")
            raise DatabaseError(
                message="Failed to retrieve applications",
                detail=str(e)
            )

    def update(self, application: Application) -> Application:
        """
        Update an existing application.
        
        Args:
            application: Application instance with updated values
            
        Returns:
            Updated Application instance
            
        Raises:
            DatabaseError: If update fails
        """
        try:
            self.db.commit()
            self.db.refresh(application)
            logger.info(f"Updated application: {application.id}")
            return application
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating application {application.id}: {e}")
            raise DatabaseError(
                message=f"Failed to update application {application.id}",
                detail=str(e)
            )

    def delete(self, app_id: str) -> bool:
        """
        Delete an application by ID.
        
        Args:
            app_id: Application ID to delete
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            DatabaseError: If deletion fails
        """
        try:
            application = self.get_by_id(app_id)
            if not application:
                return False
            
            self.db.delete(application)
            self.db.commit()
            logger.info(f"Deleted application: {app_id}")
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting application {app_id}: {e}")
            raise DatabaseError(
                message=f"Failed to delete application {app_id}",
                detail=str(e)
            )
