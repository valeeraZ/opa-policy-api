"""Tests for RoleMappingService."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.services.role_mapping_service import RoleMappingService
from app.schemas.role_mapping import RoleMappingCreate, RoleMappingUpdate
from app.models.role_mapping import RoleMapping
from app.exceptions import ValidationError, DatabaseError, OPAConnectionError


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock()


@pytest.fixture
def mock_opa_service():
    """Create a mock OPA service."""
    mock_opa = Mock()
    mock_opa.push_policy_data = AsyncMock(return_value=True)
    return mock_opa


@pytest.fixture
def mock_repository(monkeypatch):
    """Create a mock repository."""
    mock_repo = Mock()

    def mock_init(self, db, opa_service):
        self.db = db
        self.repository = mock_repo
        self.opa_service = opa_service

    monkeypatch.setattr(RoleMappingService, "__init__", mock_init)
    return mock_repo


@pytest.mark.asyncio
async def test_create_role_mapping_success(mock_db, mock_opa_service, mock_repository):
    """Test successful role mapping creation with OPA sync."""
    # Arrange
    service = RoleMappingService(mock_db, mock_opa_service)
    mapping_data = RoleMappingCreate(
        application_id="app-a",
        environment="DEV",
        ad_group="infodir-app-a-admin",
        role="admin",
    )

    created_mapping = RoleMapping(
        id=1,
        application_id="app-a",
        environment="DEV",
        ad_group="infodir-app-a-admin",
        role="admin",
        created_at=datetime.now(),
    )
    mock_repository.create.return_value = created_mapping
    mock_repository.get_all_as_opa_data.return_value = {
        "role_mappings": {"app-a": {"DEV": {"infodir-app-a-admin": "admin"}}}
    }

    # Act
    result = await service.create_role_mapping(mapping_data)

    # Assert
    assert result.id == 1
    assert result.application_id == "app-a"
    assert result.role == "admin"
    mock_repository.create.assert_called_once()
    mock_opa_service.push_policy_data.assert_called_once()


@pytest.mark.asyncio
async def test_create_role_mapping_conflict(mock_db, mock_opa_service, mock_repository):
    """Test creating conflicting role mapping raises DatabaseError."""
    # Arrange
    service = RoleMappingService(mock_db, mock_opa_service)
    mapping_data = RoleMappingCreate(
        application_id="app-a",
        environment="DEV",
        ad_group="infodir-app-a-admin",
        role="admin",
    )

    mock_repository.create.side_effect = DatabaseError(
        message="Role mapping already exists", detail="Unique constraint violation"
    )

    # Act & Assert
    with pytest.raises(DatabaseError) as exc_info:
        await service.create_role_mapping(mapping_data)

    assert "already exists" in str(exc_info.value.message)
    mock_opa_service.push_policy_data.assert_not_called()


@pytest.mark.asyncio
async def test_create_role_mapping_opa_sync_failure(
    mock_db, mock_opa_service, mock_repository
):
    """Test OPA sync failure after successful creation."""
    # Arrange
    service = RoleMappingService(mock_db, mock_opa_service)
    mapping_data = RoleMappingCreate(
        application_id="app-a",
        environment="DEV",
        ad_group="infodir-app-a-admin",
        role="admin",
    )

    created_mapping = RoleMapping(
        id=1,
        application_id="app-a",
        environment="DEV",
        ad_group="infodir-app-a-admin",
        role="admin",
        created_at=datetime.now(),
    )
    mock_repository.create.return_value = created_mapping
    mock_repository.get_all_as_opa_data.return_value = {"role_mappings": {}}
    mock_opa_service.push_policy_data.side_effect = OPAConnectionError(
        "OPA server unreachable", detail="Connection timeout"
    )

    # Act & Assert
    with pytest.raises(OPAConnectionError):
        await service.create_role_mapping(mapping_data)


@pytest.mark.asyncio
async def test_get_role_mappings_all(mock_db, mock_opa_service, mock_repository):
    """Test retrieving all role mappings."""
    # Arrange
    service = RoleMappingService(mock_db, mock_opa_service)
    mappings = [
        RoleMapping(
            id=1,
            application_id="app-a",
            environment="DEV",
            ad_group="group1",
            role="admin",
            created_at=datetime.now(),
        ),
        RoleMapping(
            id=2,
            application_id="app-b",
            environment="PROD",
            ad_group="group2",
            role="user",
            created_at=datetime.now(),
        ),
    ]
    mock_repository.get_all.return_value = mappings

    # Act
    result = await service.get_role_mappings()

    # Assert
    assert len(result) == 2
    assert result[0].id == 1
    assert result[1].id == 2
    mock_repository.get_all.assert_called_once_with(application_id=None)


@pytest.mark.asyncio
async def test_get_role_mappings_filtered(mock_db, mock_opa_service, mock_repository):
    """Test retrieving role mappings filtered by application ID."""
    # Arrange
    service = RoleMappingService(mock_db, mock_opa_service)
    mappings = [
        RoleMapping(
            id=1,
            application_id="app-a",
            environment="DEV",
            ad_group="group1",
            role="admin",
            created_at=datetime.now(),
        )
    ]
    mock_repository.get_all.return_value = mappings

    # Act
    result = await service.get_role_mappings(app_id="app-a")

    # Assert
    assert len(result) == 1
    assert result[0].application_id == "app-a"
    mock_repository.get_all.assert_called_once_with(application_id="app-a")


@pytest.mark.asyncio
async def test_update_role_mapping_success(mock_db, mock_opa_service, mock_repository):
    """Test successful role mapping update with OPA sync."""
    # Arrange
    service = RoleMappingService(mock_db, mock_opa_service)
    mapping_data = RoleMappingUpdate(role="user")

    existing_mapping = RoleMapping(
        id=1,
        application_id="app-a",
        environment="DEV",
        ad_group="group1",
        role="admin",
        created_at=datetime.now(),
    )
    mock_repository.get_by_id.return_value = existing_mapping
    mock_repository.update.return_value = existing_mapping
    mock_repository.get_all_as_opa_data.return_value = {"role_mappings": {}}

    # Act
    result = await service.update_role_mapping(1, mapping_data)

    # Assert
    assert result.role == "user"
    mock_repository.update.assert_called_once()
    mock_opa_service.push_policy_data.assert_called_once()


@pytest.mark.asyncio
async def test_update_role_mapping_not_found(
    mock_db, mock_opa_service, mock_repository
):
    """Test updating non-existent role mapping raises ValidationError."""
    # Arrange
    service = RoleMappingService(mock_db, mock_opa_service)
    mapping_data = RoleMappingUpdate(role="user")
    mock_repository.get_by_id.return_value = None

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        await service.update_role_mapping(999, mapping_data)

    assert "not found" in str(exc_info.value.message)
    mock_opa_service.push_policy_data.assert_not_called()


@pytest.mark.asyncio
async def test_update_role_mapping_partial(mock_db, mock_opa_service, mock_repository):
    """Test partial update of role mapping fields."""
    # Arrange
    service = RoleMappingService(mock_db, mock_opa_service)
    mapping_data = RoleMappingUpdate(environment="PROD")

    existing_mapping = RoleMapping(
        id=1,
        application_id="app-a",
        environment="DEV",
        ad_group="group1",
        role="admin",
        created_at=datetime.now(),
    )
    mock_repository.get_by_id.return_value = existing_mapping
    mock_repository.update.return_value = existing_mapping
    mock_repository.get_all_as_opa_data.return_value = {"role_mappings": {}}

    # Act
    result = await service.update_role_mapping(1, mapping_data)

    # Assert
    assert result.environment == "PROD"
    assert result.role == "admin"  # Unchanged
    mock_repository.update.assert_called_once()


@pytest.mark.asyncio
async def test_delete_role_mapping_success(mock_db, mock_opa_service, mock_repository):
    """Test successful role mapping deletion with OPA sync."""
    # Arrange
    service = RoleMappingService(mock_db, mock_opa_service)
    mock_repository.delete.return_value = True
    mock_repository.get_all_as_opa_data.return_value = {"role_mappings": {}}

    # Act
    result = await service.delete_role_mapping(1)

    # Assert
    assert result is True
    mock_repository.delete.assert_called_once_with(1)
    mock_opa_service.push_policy_data.assert_called_once()


@pytest.mark.asyncio
async def test_delete_role_mapping_not_found(
    mock_db, mock_opa_service, mock_repository
):
    """Test deleting non-existent role mapping."""
    # Arrange
    service = RoleMappingService(mock_db, mock_opa_service)
    mock_repository.delete.return_value = False

    # Act
    result = await service.delete_role_mapping(999)

    # Assert
    assert result is False
    mock_opa_service.push_policy_data.assert_not_called()


@pytest.mark.asyncio
async def test_sync_to_opa_success(mock_db, mock_opa_service, mock_repository):
    """Test successful synchronization of role mappings to OPA."""
    # Arrange
    service = RoleMappingService(mock_db, mock_opa_service)
    opa_data = {
        "role_mappings": {
            "app-a": {
                "DEV": {"infodir-app-a-admin": "admin", "infodir-app-a-user": "user"},
                "PROD": {"infodir-app-a-admin": "admin"},
            },
            "app-b": {"DEV": {"infodir-app-b-user": "user"}},
        }
    }
    mock_repository.get_all_as_opa_data.return_value = opa_data

    # Act
    result = await service.sync_to_opa()

    # Assert
    assert result is True
    mock_repository.get_all_as_opa_data.assert_called_once()
    mock_opa_service.push_policy_data.assert_called_once_with(
        data_path="role_mappings", data=opa_data["role_mappings"]
    )


@pytest.mark.asyncio
async def test_sync_to_opa_database_error(mock_db, mock_opa_service, mock_repository):
    """Test sync failure due to database error."""
    # Arrange
    service = RoleMappingService(mock_db, mock_opa_service)
    mock_repository.get_all_as_opa_data.side_effect = DatabaseError(
        message="Database connection failed", detail="Connection timeout"
    )

    # Act & Assert
    with pytest.raises(DatabaseError):
        await service.sync_to_opa()

    mock_opa_service.push_policy_data.assert_not_called()


@pytest.mark.asyncio
async def test_sync_to_opa_connection_error(mock_db, mock_opa_service, mock_repository):
    """Test sync failure due to OPA connection error."""
    # Arrange
    service = RoleMappingService(mock_db, mock_opa_service)
    mock_repository.get_all_as_opa_data.return_value = {"role_mappings": {}}
    mock_opa_service.push_policy_data.side_effect = OPAConnectionError(
        "OPA server unreachable", detail="Connection refused"
    )

    # Act & Assert
    with pytest.raises(OPAConnectionError):
        await service.sync_to_opa()
