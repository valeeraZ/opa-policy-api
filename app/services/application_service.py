"""Service layer for application management."""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.application import Application
from app.repositories.application_repository import ApplicationRepository
from app.schemas.application import ApplicationCreate, ApplicationUpdate, ApplicationResponse
from app.exceptions import DatabaseError, ValidationError

logger = logging.getLogger(__name__)


class ApplicationService:
    """Service for managing applications with business logic and logging."""

    def __init__(self, db: Session):
        """
        Initialize ApplicationService.
        
        Args:
            db: Database session
        """
        self.db = db
        self.repository = ApplicationRepository(db)

    def create_application(self, app_data: ApplicationCreate) -> ApplicationResponse:
        """
        Create a new application with duplicate check.
        
        Args:
            app_data: Application creation data
            
        Returns:
            Created application response
            
        Raises:
            ValidationError: If application with same ID already exists
            DatabaseError: If database operation fails
        """
        logger.info(f"Creating application with id: {app_data.id}")
        
        # Check for duplicate
        existing = self.repository.get_by_id(app_data.id)
        if existing:
            logger.warning(f"Attempted to create duplicate application: {app_data.id}")
            raise ValidationError(
                message=f"Application with id '{app_data.id}' already exists",
                detail="Application IDs must be unique"
            )
        
        # Create application model
        application = Application(
            id=app_data.id,
            name=app_data.name,
            description=app_data.description
        )
        
        try:
            created_app = self.repository.create(application)
            logger.info(f"Successfully created application: {created_app.id}")
            return ApplicationResponse.model_validate(created_app)
        except DatabaseError as e:
            logger.error(f"Failed to create application {app_data.id}: {e.message}")
            raise

    def get_application(self, app_id: str) -> Optional[ApplicationResponse]:
        """
        Retrieve an application by ID.
        
        Args:
            app_id: Application identifier
            
        Returns:
            Application response if found, None otherwise
            
        Raises:
            DatabaseError: If database operation fails
        """
        logger.debug(f"Retrieving application: {app_id}")
        
        try:
            application = self.repository.get_by_id(app_id)
            if application:
                logger.debug(f"Found application: {app_id}")
                return ApplicationResponse.model_validate(application)
            else:
                logger.debug(f"Application not found: {app_id}")
                return None
        except DatabaseError as e:
            logger.error(f"Failed to retrieve application {app_id}: {e.message}")
            raise

    def list_applications(self) -> List[ApplicationResponse]:
        """
        Retrieve all applications.
        
        Returns:
            List of all applications
            
        Raises:
            DatabaseError: If database operation fails
        """
        logger.debug("Retrieving all applications")
        
        try:
            applications = self.repository.get_all()
            logger.info(f"Retrieved {len(applications)} applications")
            return [ApplicationResponse.model_validate(app) for app in applications]
        except DatabaseError as e:
            logger.error(f"Failed to retrieve applications: {e.message}")
            raise

    def update_application(self, app_id: str, app_data: ApplicationUpdate) -> ApplicationResponse:
        """
        Update an existing application.
        
        Args:
            app_id: Application identifier
            app_data: Updated application data
            
        Returns:
            Updated application response
            
        Raises:
            ValidationError: If application not found
            DatabaseError: If database operation fails
        """
        logger.info(f"Updating application: {app_id}")
        
        # Retrieve existing application
        application = self.repository.get_by_id(app_id)
        if not application:
            logger.warning(f"Attempted to update non-existent application: {app_id}")
            raise ValidationError(
                message=f"Application with id '{app_id}' not found",
                detail="Cannot update non-existent application"
            )
        
        # Update fields if provided
        if app_data.name is not None:
            application.name = app_data.name
        if app_data.description is not None:
            application.description = app_data.description
        
        try:
            updated_app = self.repository.update(application)
            logger.info(f"Successfully updated application: {app_id}")
            return ApplicationResponse.model_validate(updated_app)
        except DatabaseError as e:
            logger.error(f"Failed to update application {app_id}: {e.message}")
            raise

    def delete_application(self, app_id: str) -> bool:
        """
        Delete an application by ID.
        
        Args:
            app_id: Application identifier
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            DatabaseError: If database operation fails
        """
        logger.info(f"Deleting application: {app_id}")
        
        try:
            deleted = self.repository.delete(app_id)
            if deleted:
                logger.info(f"Successfully deleted application: {app_id}")
            else:
                logger.warning(f"Attempted to delete non-existent application: {app_id}")
            return deleted
        except DatabaseError as e:
            logger.error(f"Failed to delete application {app_id}: {e.message}")
            raise
