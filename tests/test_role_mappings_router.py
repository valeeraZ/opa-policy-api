"""Tests for role mapping router endpoints."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.routers.role_mappings import (
    create_role_mapping,
    list_role_mappings,
    update_role_mapping,
    delete_role_mapping,
)
from app.schemas.role_mapping import (
    RoleMappingCreate,
    RoleMappingUpdate,
    RoleMappingResponse,
)
from app.schemas.user import UserInfo
from app.exceptions import ValidationError, DatabaseError, OPAConnectionError
from datetime import datetime


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def mock_opa_service():
    """Mock OPA service."""
    return Mock()


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
def sample_mapping_create():
    """Sample role mapping create data."""
    return RoleMappingCreate(
        application_id="test-app",
        environment="DEV",
        ad_group="infodir-test-app-admin",
        role="admin",
    )


@pytest.fixture
def sample_mapping_update():
    """Sample role mapping update data."""
    return RoleMappingUpdate(role="user")


@pytest.fixture
def sample_mapping_response():
    """Sample role mapping response."""
    return RoleMappingResponse(
        id=1,
        application_id="test-app",
        environment="DEV",
        ad_group="infodir-test-app-admin",
        role="admin",
        created_at=datetime.now(),
        updated_at=None,
    )


class TestCreateRoleMapping:
    """Tests for POST /role-mappings endpoint."""

    @pytest.mark.asyncio
    @patch("app.routers.role_mappings.RoleMappingService")
    async def test_create_role_mapping_success(
        self,
        mock_service_class,
        mock_db,
        mock_opa_service,
        admin_user,
        sample_mapping_create,
        sample_mapping_response,
    ):
        """Test successful role mapping creation."""
        # Arrange
        mock_service = Mock()
        mock_service.create_role_mapping = AsyncMock(
            return_value=sample_mapping_response
        )
        mock_service_class.return_value = mock_service

        # Act
        result = await create_role_mapping(
            sample_mapping_create, admin_user, mock_db, mock_opa_service
        )

        # Assert
        assert result == sample_mapping_response
        mock_service.create_role_mapping.assert_called_once_with(sample_mapping_create)

    @pytest.mark.asyncio
    @patch("app.routers.role_mappings.RoleMappingService")
    async def test_create_role_mapping_conflict(
        self,
        mock_service_class,
        mock_db,
        mock_opa_service,
        admin_user,
        sample_mapping_create,
    ):
        """Test creating duplicate role mapping returns 409."""
        # Arrange
        mock_service = Mock()
        mock_service.create_role_mapping = AsyncMock(
            side_effect=DatabaseError(
                message="Role mapping with application_id='test-app', environment='DEV', "
                "ad_group='infodir-test-app-admin' already exists (unique constraint violation)"
            )
        )
        mock_service_class.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_role_mapping(
                sample_mapping_create, admin_user, mock_db, mock_opa_service
            )

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "unique constraint" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("app.routers.role_mappings.RoleMappingService")
    async def test_create_role_mapping_database_error(
        self,
        mock_service_class,
        mock_db,
        mock_opa_service,
        admin_user,
        sample_mapping_create,
    ):
        """Test database error during creation returns 500."""
        # Arrange
        mock_service = Mock()
        mock_service.create_role_mapping = AsyncMock(
            side_effect=DatabaseError(message="Database connection failed")
        )
        mock_service_class.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_role_mapping(
                sample_mapping_create, admin_user, mock_db, mock_opa_service
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    @patch("app.routers.role_mappings.RoleMappingService")
    async def test_create_role_mapping_opa_sync_failure(
        self,
        mock_service_class,
        mock_db,
        mock_opa_service,
        admin_user,
        sample_mapping_create,
    ):
        """Test OPA sync failure during creation returns 503."""
        # Arrange
        mock_service = Mock()
        mock_service.create_role_mapping = AsyncMock(
            side_effect=OPAConnectionError(message="OPA server unreachable")
        )
        mock_service_class.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_role_mapping(
                sample_mapping_create, admin_user, mock_db, mock_opa_service
            )

        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "OPA sync failed" in exc_info.value.detail


class TestListRoleMappings:
    """Tests for GET /role-mappings endpoint."""

    @pytest.mark.asyncio
    @patch("app.routers.role_mappings.RoleMappingService")
    async def test_list_role_mappings_success(
        self, mock_service_class, mock_db, mock_opa_service, sample_mapping_response
    ):
        """Test successful listing of role mappings."""
        # Arrange
        mock_service = Mock()
        mock_service.get_role_mappings = AsyncMock(
            return_value=[sample_mapping_response]
        )
        mock_service_class.return_value = mock_service

        # Act
        result = await list_role_mappings(mock_db, mock_opa_service)

        # Assert
        assert len(result) == 1
        assert result[0] == sample_mapping_response
        mock_service.get_role_mappings.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.routers.role_mappings.RoleMappingService")
    async def test_list_role_mappings_with_filter(
        self, mock_service_class, mock_db, mock_opa_service, sample_mapping_response
    ):
        """Test listing role mappings with application ID filter."""
        # Arrange
        mock_service = Mock()
        mock_service.get_role_mappings = AsyncMock(
            return_value=[sample_mapping_response]
        )
        mock_service_class.return_value = mock_service

        # Act
        result = await list_role_mappings(mock_db, mock_opa_service, app_id="test-app")

        # Assert
        assert len(result) == 1
        assert result[0] == sample_mapping_response
        mock_service.get_role_mappings.assert_called_once_with(app_id="test-app")

    @pytest.mark.asyncio
    @patch("app.routers.role_mappings.RoleMappingService")
    async def test_list_role_mappings_empty(
        self, mock_service_class, mock_db, mock_opa_service
    ):
        """Test listing role mappings when none exist."""
        # Arrange
        mock_service = Mock()
        mock_service.get_role_mappings = AsyncMock(return_value=[])
        mock_service_class.return_value = mock_service

        # Act
        result = await list_role_mappings(mock_db, mock_opa_service)

        # Assert
        assert len(result) == 0

    @pytest.mark.asyncio
    @patch("app.routers.role_mappings.RoleMappingService")
    async def test_list_role_mappings_database_error(
        self, mock_service_class, mock_db, mock_opa_service
    ):
        """Test database error during listing returns 500."""
        # Arrange
        mock_service = Mock()
        mock_service.get_role_mappings = AsyncMock(
            side_effect=DatabaseError(message="Database connection failed")
        )
        mock_service_class.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_role_mappings(mock_db, mock_opa_service)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestUpdateRoleMapping:
    """Tests for PUT /role-mappings/{mapping_id} endpoint."""

    @pytest.mark.asyncio
    @patch("app.routers.role_mappings.RoleMappingService")
    async def test_update_role_mapping_success(
        self,
        mock_service_class,
        mock_db,
        mock_opa_service,
        admin_user,
        sample_mapping_update,
        sample_mapping_response,
    ):
        """Test successful role mapping update."""
        # Arrange
        mock_service = Mock()
        mock_service.update_role_mapping = AsyncMock(
            return_value=sample_mapping_response
        )
        mock_service_class.return_value = mock_service

        # Act
        result = await update_role_mapping(
            1, sample_mapping_update, admin_user, mock_db, mock_opa_service
        )

        # Assert
        assert result == sample_mapping_response
        mock_service.update_role_mapping.assert_called_once_with(
            1, sample_mapping_update
        )

    @pytest.mark.asyncio
    @patch("app.routers.role_mappings.RoleMappingService")
    async def test_update_role_mapping_not_found(
        self,
        mock_service_class,
        mock_db,
        mock_opa_service,
        admin_user,
        sample_mapping_update,
    ):
        """Test updating non-existent role mapping returns 404."""
        # Arrange
        mock_service = Mock()
        mock_service.update_role_mapping = AsyncMock(
            side_effect=ValidationError(
                message="Role mapping with id '1' not found",
                detail="Cannot update non-existent role mapping",
            )
        )
        mock_service_class.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_role_mapping(
                1, sample_mapping_update, admin_user, mock_db, mock_opa_service
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    @patch("app.routers.role_mappings.RoleMappingService")
    async def test_update_role_mapping_conflict(
        self,
        mock_service_class,
        mock_db,
        mock_opa_service,
        admin_user,
        sample_mapping_update,
    ):
        """Test updating role mapping with conflict returns 409."""
        # Arrange
        mock_service = Mock()
        mock_service.update_role_mapping = AsyncMock(
            side_effect=DatabaseError(
                message="Role mapping with these values already exists (unique constraint violation)"
            )
        )
        mock_service_class.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_role_mapping(
                1, sample_mapping_update, admin_user, mock_db, mock_opa_service
            )

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    @patch("app.routers.role_mappings.RoleMappingService")
    async def test_update_role_mapping_opa_sync_failure(
        self,
        mock_service_class,
        mock_db,
        mock_opa_service,
        admin_user,
        sample_mapping_update,
    ):
        """Test OPA sync failure during update returns 503."""
        # Arrange
        mock_service = Mock()
        mock_service.update_role_mapping = AsyncMock(
            side_effect=OPAConnectionError(message="OPA server unreachable")
        )
        mock_service_class.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_role_mapping(
                1, sample_mapping_update, admin_user, mock_db, mock_opa_service
            )

        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "OPA sync failed" in exc_info.value.detail


class TestDeleteRoleMapping:
    """Tests for DELETE /role-mappings/{mapping_id} endpoint."""

    @pytest.mark.asyncio
    @patch("app.routers.role_mappings.RoleMappingService")
    async def test_delete_role_mapping_success(
        self, mock_service_class, mock_db, mock_opa_service, admin_user
    ):
        """Test successful role mapping deletion."""
        # Arrange
        mock_service = Mock()
        mock_service.delete_role_mapping = AsyncMock(return_value=True)
        mock_service_class.return_value = mock_service

        # Act
        result = await delete_role_mapping(1, admin_user, mock_db, mock_opa_service)

        # Assert
        assert result is None
        mock_service.delete_role_mapping.assert_called_once_with(1)

    @pytest.mark.asyncio
    @patch("app.routers.role_mappings.RoleMappingService")
    async def test_delete_role_mapping_not_found(
        self, mock_service_class, mock_db, mock_opa_service, admin_user
    ):
        """Test deleting non-existent role mapping returns 404."""
        # Arrange
        mock_service = Mock()
        mock_service.delete_role_mapping = AsyncMock(return_value=False)
        mock_service_class.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_role_mapping(1, admin_user, mock_db, mock_opa_service)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.routers.role_mappings.RoleMappingService")
    async def test_delete_role_mapping_database_error(
        self, mock_service_class, mock_db, mock_opa_service, admin_user
    ):
        """Test database error during deletion returns 500."""
        # Arrange
        mock_service = Mock()
        mock_service.delete_role_mapping = AsyncMock(
            side_effect=DatabaseError(message="Database connection failed")
        )
        mock_service_class.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_role_mapping(1, admin_user, mock_db, mock_opa_service)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    @patch("app.routers.role_mappings.RoleMappingService")
    async def test_delete_role_mapping_opa_sync_failure(
        self, mock_service_class, mock_db, mock_opa_service, admin_user
    ):
        """Test OPA sync failure during deletion returns 503."""
        # Arrange
        mock_service = Mock()
        mock_service.delete_role_mapping = AsyncMock(
            side_effect=OPAConnectionError(message="OPA server unreachable")
        )
        mock_service_class.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_role_mapping(1, admin_user, mock_db, mock_opa_service)

        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "OPA sync failed" in exc_info.value.detail
