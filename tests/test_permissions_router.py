"""Tests for permission evaluation endpoints."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.routers.permissions import evaluate_all_permissions, evaluate_app_permission
from app.schemas.user import UserInfo
from app.schemas.application import ApplicationResponse
from app.schemas.role_mapping import RoleMappingResponse
from app.services.opa_service import OPAService
from app.exceptions import OPAConnectionError, DatabaseError
from datetime import datetime


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    return UserInfo(
        employee_id="E12345",
        ad_groups=["infodir-app-a-admin", "infodir-app-b-user"],
        email="test@example.com",
        name="Test User",
    )


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def mock_opa_service():
    """Create a mock OPA service."""
    service = Mock(spec=OPAService)
    service.evaluate_permissions = AsyncMock()
    return service


@pytest.fixture
def mock_applications():
    """Create mock applications."""
    return [
        ApplicationResponse(
            id="app-a",
            name="Application A",
            description="Test app A",
            created_at=datetime.now(),
            updated_at=None,
            role_mappings=[],
        ),
        ApplicationResponse(
            id="app-b",
            name="Application B",
            description="Test app B",
            created_at=datetime.now(),
            updated_at=None,
            role_mappings=[],
        ),
    ]


@pytest.fixture
def mock_role_mappings():
    """Create mock role mappings."""
    return [
        RoleMappingResponse(
            id=1,
            application_id="app-a",
            environment="DEV",
            ad_group="infodir-app-a-admin",
            role="admin",
            created_at=datetime.now(),
            updated_at=None,
        ),
        RoleMappingResponse(
            id=2,
            application_id="app-b",
            environment="DEV",
            ad_group="infodir-app-b-user",
            role="user",
            created_at=datetime.now(),
            updated_at=None,
        ),
    ]


@pytest.mark.asyncio
async def test_evaluate_all_permissions_success(
    mock_user, mock_db, mock_opa_service, mock_applications, mock_role_mappings
):
    """Test successful evaluation of all permissions."""
    # Mock the services
    with (
        patch("app.routers.permissions.ApplicationService") as MockAppService,
        patch("app.routers.permissions.RoleMappingService") as MockRMService,
    ):
        # Setup application service mock
        app_service_instance = MockAppService.return_value
        app_service_instance.list_applications.return_value = mock_applications

        # Setup role mapping service mock
        rm_service_instance = MockRMService.return_value
        rm_service_instance.get_role_mappings = AsyncMock(
            return_value=mock_role_mappings
        )

        # Setup OPA service mock
        mock_opa_service.evaluate_permissions.return_value = {
            "app-a": "admin",
            "app-b": "user",
        }

        # Call the endpoint
        response = await evaluate_all_permissions(
            current_user=mock_user, db=mock_db, opa_service=mock_opa_service
        )

        # Assertions
        assert response.permissions == {"app-a": "admin", "app-b": "user"}
        app_service_instance.list_applications.assert_called_once()
        rm_service_instance.get_role_mappings.assert_called_once()
        mock_opa_service.evaluate_permissions.assert_called_once()


@pytest.mark.asyncio
async def test_evaluate_all_permissions_no_applications(
    mock_user, mock_db, mock_opa_service
):
    """Test evaluation when no applications exist."""
    with patch("app.routers.permissions.ApplicationService") as MockAppService:
        # Setup application service mock to return empty list
        app_service_instance = MockAppService.return_value
        app_service_instance.list_applications.return_value = []

        # Call the endpoint
        response = await evaluate_all_permissions(
            current_user=mock_user, db=mock_db, opa_service=mock_opa_service
        )

        # Assertions
        assert response.permissions == {}
        app_service_instance.list_applications.assert_called_once()


@pytest.mark.asyncio
async def test_evaluate_all_permissions_opa_connection_error(
    mock_user, mock_db, mock_opa_service, mock_applications, mock_role_mappings
):
    """Test handling of OPA connection errors."""
    with (
        patch("app.routers.permissions.ApplicationService") as MockAppService,
        patch("app.routers.permissions.RoleMappingService") as MockRMService,
    ):
        # Setup mocks
        app_service_instance = MockAppService.return_value
        app_service_instance.list_applications.return_value = mock_applications

        rm_service_instance = MockRMService.return_value
        rm_service_instance.get_role_mappings = AsyncMock(
            return_value=mock_role_mappings
        )

        # Setup OPA service to raise connection error
        mock_opa_service.evaluate_permissions.side_effect = OPAConnectionError(
            "OPA server unreachable"
        )

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await evaluate_all_permissions(
                current_user=mock_user, db=mock_db, opa_service=mock_opa_service
            )

        # Assertions
        assert exc_info.value.status_code == 503
        assert "OPA server is unreachable" in exc_info.value.detail


@pytest.mark.asyncio
async def test_evaluate_all_permissions_database_error(
    mock_user, mock_db, mock_opa_service
):
    """Test handling of database errors."""
    with patch("app.routers.permissions.ApplicationService") as MockAppService:
        # Setup application service to raise database error
        app_service_instance = MockAppService.return_value
        app_service_instance.list_applications.side_effect = DatabaseError(
            "Database connection failed"
        )

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await evaluate_all_permissions(
                current_user=mock_user, db=mock_db, opa_service=mock_opa_service
            )

        # Assertions
        assert exc_info.value.status_code == 500
        assert "Database operation failed" in exc_info.value.detail


@pytest.mark.asyncio
async def test_evaluate_app_permission_success(
    mock_user, mock_db, mock_opa_service, mock_applications, mock_role_mappings
):
    """Test successful evaluation of single app permission."""
    with (
        patch("app.routers.permissions.ApplicationService") as MockAppService,
        patch("app.routers.permissions.RoleMappingService") as MockRMService,
    ):
        # Setup application service mock
        app_service_instance = MockAppService.return_value
        app_service_instance.get_application.return_value = mock_applications[0]

        # Setup role mapping service mock
        rm_service_instance = MockRMService.return_value
        rm_service_instance.get_role_mappings = AsyncMock(
            return_value=mock_role_mappings
        )

        # Setup OPA service mock
        mock_opa_service.evaluate_permissions.return_value = {"app-a": "admin"}

        # Call the endpoint
        response = await evaluate_app_permission(
            app_id="app-a",
            current_user=mock_user,
            db=mock_db,
            opa_service=mock_opa_service,
        )

        # Assertions
        assert response.application_id == "app-a"
        assert response.role == "admin"
        app_service_instance.get_application.assert_called_once_with("app-a")
        rm_service_instance.get_role_mappings.assert_called_once()
        mock_opa_service.evaluate_permissions.assert_called_once()


@pytest.mark.asyncio
async def test_evaluate_app_permission_not_found(mock_user, mock_db, mock_opa_service):
    """Test evaluation when application does not exist."""
    with patch("app.routers.permissions.ApplicationService") as MockAppService:
        # Setup application service mock to return None
        app_service_instance = MockAppService.return_value
        app_service_instance.get_application.return_value = None

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await evaluate_app_permission(
                app_id="non-existent",
                current_user=mock_user,
                db=mock_db,
                opa_service=mock_opa_service,
            )

        # Assertions
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_evaluate_app_permission_default_none(
    mock_user, mock_db, mock_opa_service, mock_applications, mock_role_mappings
):
    """Test that default role is 'none' when not in OPA result."""
    with (
        patch("app.routers.permissions.ApplicationService") as MockAppService,
        patch("app.routers.permissions.RoleMappingService") as MockRMService,
    ):
        # Setup mocks
        app_service_instance = MockAppService.return_value
        app_service_instance.get_application.return_value = mock_applications[0]

        rm_service_instance = MockRMService.return_value
        rm_service_instance.get_role_mappings = AsyncMock(
            return_value=mock_role_mappings
        )

        # Setup OPA service mock to return empty permissions
        mock_opa_service.evaluate_permissions.return_value = {}

        # Call the endpoint
        response = await evaluate_app_permission(
            app_id="app-a",
            current_user=mock_user,
            db=mock_db,
            opa_service=mock_opa_service,
        )

        # Assertions
        assert response.application_id == "app-a"
        assert response.role == "none"


@pytest.mark.asyncio
async def test_evaluate_app_permission_opa_connection_error(
    mock_user, mock_db, mock_opa_service, mock_applications, mock_role_mappings
):
    """Test handling of OPA connection errors for single app."""
    with (
        patch("app.routers.permissions.ApplicationService") as MockAppService,
        patch("app.routers.permissions.RoleMappingService") as MockRMService,
    ):
        # Setup mocks
        app_service_instance = MockAppService.return_value
        app_service_instance.get_application.return_value = mock_applications[0]

        rm_service_instance = MockRMService.return_value
        rm_service_instance.get_role_mappings = AsyncMock(
            return_value=mock_role_mappings
        )

        # Setup OPA service to raise connection error
        mock_opa_service.evaluate_permissions.side_effect = OPAConnectionError(
            "OPA server unreachable"
        )

        # Call the endpoint and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await evaluate_app_permission(
                app_id="app-a",
                current_user=mock_user,
                db=mock_db,
                opa_service=mock_opa_service,
            )

        # Assertions
        assert exc_info.value.status_code == 503
        assert "OPA server is unreachable" in exc_info.value.detail
