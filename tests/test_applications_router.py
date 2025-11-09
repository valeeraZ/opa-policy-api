"""Tests for application router endpoints."""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.routers.applications import (
    create_application,
    list_applications,
    get_application,
    update_application,
    delete_application,
)
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
)
from app.schemas.user import UserInfo
from app.exceptions import ValidationError, DatabaseError
from datetime import datetime


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def admin_user():
    """Mock admin user."""
    return UserInfo(
        employee_id="admin123",
        ad_groups=["admin-group", "user-group"],
        email="admin@example.com",
        name="Admin User",
    )


@pytest.fixture
def sample_app_create():
    """Sample application create data."""
    return ApplicationCreate(
        id="test-app", name="Test Application", description="Test description"
    )


@pytest.fixture
def sample_app_update():
    """Sample application update data."""
    return ApplicationUpdate(
        name="Updated Application", description="Updated description"
    )


@pytest.fixture
def sample_app_response():
    """Sample application response."""
    return ApplicationResponse(
        id="test-app",
        name="Test Application",
        description="Test description",
        created_at=datetime.now(),
        updated_at=None,
    )


class TestCreateApplication:
    """Tests for POST /applications endpoint."""

    @pytest.mark.asyncio
    @patch("app.routers.applications.ApplicationService")
    async def test_create_application_success(
        self,
        mock_service_class,
        mock_db,
        admin_user,
        sample_app_create,
        sample_app_response,
    ):
        """Test successful application creation."""
        # Arrange
        mock_service = Mock()
        mock_service.create_application.return_value = sample_app_response
        mock_service_class.return_value = mock_service

        # Act
        result = await create_application(sample_app_create, admin_user, mock_db)

        # Assert
        assert result == sample_app_response
        mock_service.create_application.assert_called_once_with(sample_app_create)

    @pytest.mark.asyncio
    @patch("app.routers.applications.ApplicationService")
    async def test_create_application_duplicate(
        self, mock_service_class, mock_db, admin_user, sample_app_create
    ):
        """Test creating duplicate application returns 409."""
        # Arrange
        mock_service = Mock()
        mock_service.create_application.side_effect = ValidationError(
            message="Application with id 'test-app' already exists",
            detail="Application IDs must be unique",
        )
        mock_service_class.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_application(sample_app_create, admin_user, mock_db)

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.routers.applications.ApplicationService")
    async def test_create_application_database_error(
        self, mock_service_class, mock_db, admin_user, sample_app_create
    ):
        """Test database error during creation returns 500."""
        # Arrange
        mock_service = Mock()
        mock_service.create_application.side_effect = DatabaseError(
            message="Database connection failed"
        )
        mock_service_class.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_application(sample_app_create, admin_user, mock_db)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestListApplications:
    """Tests for GET /applications endpoint."""

    @pytest.mark.asyncio
    @patch("app.routers.applications.ApplicationService")
    async def test_list_applications_success(
        self, mock_service_class, mock_db, sample_app_response
    ):
        """Test successful listing of applications."""
        # Arrange
        mock_service = Mock()
        mock_service.list_applications.return_value = [sample_app_response]
        mock_service_class.return_value = mock_service

        # Act
        result = await list_applications(mock_db)

        # Assert
        assert len(result) == 1
        assert result[0] == sample_app_response
        mock_service.list_applications.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.routers.applications.ApplicationService")
    async def test_list_applications_empty(self, mock_service_class, mock_db):
        """Test listing applications when none exist."""
        # Arrange
        mock_service = Mock()
        mock_service.list_applications.return_value = []
        mock_service_class.return_value = mock_service

        # Act
        result = await list_applications(mock_db)

        # Assert
        assert len(result) == 0

    @pytest.mark.asyncio
    @patch("app.routers.applications.ApplicationService")
    async def test_list_applications_database_error(self, mock_service_class, mock_db):
        """Test database error during listing returns 500."""
        # Arrange
        mock_service = Mock()
        mock_service.list_applications.side_effect = DatabaseError(
            message="Database connection failed"
        )
        mock_service_class.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_applications(mock_db)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestGetApplication:
    """Tests for GET /applications/{app_id} endpoint."""

    @pytest.mark.asyncio
    @patch("app.routers.applications.ApplicationService")
    async def test_get_application_success(
        self, mock_service_class, mock_db, sample_app_response
    ):
        """Test successful retrieval of application."""
        # Arrange
        mock_service = Mock()
        mock_service.get_application.return_value = sample_app_response
        mock_service_class.return_value = mock_service

        # Act
        result = await get_application("test-app", mock_db)

        # Assert
        assert result == sample_app_response
        mock_service.get_application.assert_called_once_with("test-app")

    @pytest.mark.asyncio
    @patch("app.routers.applications.ApplicationService")
    async def test_get_application_not_found(self, mock_service_class, mock_db):
        """Test retrieving non-existent application returns 404."""
        # Arrange
        mock_service = Mock()
        mock_service.get_application.return_value = None
        mock_service_class.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_application("nonexistent", mock_db)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail


class TestUpdateApplication:
    """Tests for PUT /applications/{app_id} endpoint."""

    @pytest.mark.asyncio
    @patch("app.routers.applications.ApplicationService")
    async def test_update_application_success(
        self,
        mock_service_class,
        mock_db,
        admin_user,
        sample_app_update,
        sample_app_response,
    ):
        """Test successful application update."""
        # Arrange
        mock_service = Mock()
        mock_service.update_application.return_value = sample_app_response
        mock_service_class.return_value = mock_service

        # Act
        result = await update_application(
            "test-app", sample_app_update, admin_user, mock_db
        )

        # Assert
        assert result == sample_app_response
        mock_service.update_application.assert_called_once_with(
            "test-app", sample_app_update
        )

    @pytest.mark.asyncio
    @patch("app.routers.applications.ApplicationService")
    async def test_update_application_not_found(
        self, mock_service_class, mock_db, admin_user, sample_app_update
    ):
        """Test updating non-existent application returns 404."""
        # Arrange
        mock_service = Mock()
        mock_service.update_application.side_effect = ValidationError(
            message="Application with id 'test-app' not found",
            detail="Cannot update non-existent application",
        )
        mock_service_class.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_application("test-app", sample_app_update, admin_user, mock_db)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteApplication:
    """Tests for DELETE /applications/{app_id} endpoint."""

    @pytest.mark.asyncio
    @patch("app.routers.applications.ApplicationService")
    async def test_delete_application_success(
        self, mock_service_class, mock_db, admin_user
    ):
        """Test successful application deletion."""
        # Arrange
        mock_service = Mock()
        mock_service.delete_application.return_value = True
        mock_service_class.return_value = mock_service

        # Act
        result = await delete_application("test-app", admin_user, mock_db)

        # Assert
        assert result is None
        mock_service.delete_application.assert_called_once_with("test-app")

    @pytest.mark.asyncio
    @patch("app.routers.applications.ApplicationService")
    async def test_delete_application_not_found(
        self, mock_service_class, mock_db, admin_user
    ):
        """Test deleting non-existent application returns 404."""
        # Arrange
        mock_service = Mock()
        mock_service.delete_application.return_value = False
        mock_service_class.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_application("test-app", admin_user, mock_db)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail
