"""Integration test demonstrating RoleMappingService functionality."""

import pytest
from unittest.mock import AsyncMock, Mock

from app.services.role_mapping_service import RoleMappingService
from app.schemas.role_mapping import RoleMappingCreate, RoleMappingUpdate


@pytest.mark.asyncio
async def test_role_mapping_service_workflow():
    """
    Integration test demonstrating the complete workflow:
    1. Create role mapping
    2. Retrieve role mappings
    3. Update role mapping
    4. Delete role mapping

    Each operation should sync to OPA.
    """
    # Setup mocks
    mock_db = Mock()
    mock_opa_service = Mock()
    mock_opa_service.push_policy_data = AsyncMock(return_value=True)

    # Create service instance
    service = RoleMappingService(mock_db, mock_opa_service)

    # Mock repository methods
    from app.models.role_mapping import RoleMapping
    from datetime import datetime

    created_mapping = RoleMapping(
        id=1,
        application_id="test-app",
        environment="DEV",
        ad_group="test-group",
        role="admin",
        created_at=datetime.now(),
    )

    service.repository.create = Mock(return_value=created_mapping)
    service.repository.get_all = Mock(return_value=[created_mapping])
    service.repository.get_by_id = Mock(return_value=created_mapping)
    service.repository.update = Mock(return_value=created_mapping)
    service.repository.delete = Mock(return_value=True)
    service.repository.get_all_as_opa_data = Mock(
        return_value={"role_mappings": {"test-app": {"DEV": {"test-group": "admin"}}}}
    )

    # Step 1: Create role mapping
    create_data = RoleMappingCreate(
        application_id="test-app",
        environment="DEV",
        ad_group="test-group",
        role="admin",
    )
    result = await service.create_role_mapping(create_data)
    assert result.id == 1
    assert result.application_id == "test-app"
    assert mock_opa_service.push_policy_data.call_count == 1

    # Step 2: Retrieve role mappings
    mappings = await service.get_role_mappings()
    assert len(mappings) == 1
    assert mappings[0].id == 1

    # Step 3: Update role mapping
    update_data = RoleMappingUpdate(role="user")
    updated = await service.update_role_mapping(1, update_data)
    assert updated.id == 1
    assert mock_opa_service.push_policy_data.call_count == 2

    # Step 4: Delete role mapping
    deleted = await service.delete_role_mapping(1)
    assert deleted is True
    assert mock_opa_service.push_policy_data.call_count == 3

    # Verify OPA sync was called with correct data structure
    calls = mock_opa_service.push_policy_data.call_args_list
    for call in calls:
        assert call[1]["data_path"] == "role_mappings"
        assert "test-app" in call[1]["data"]


@pytest.mark.asyncio
async def test_role_mapping_service_logging():
    """Verify that logging occurs for all operations."""
    from unittest.mock import patch

    mock_db = Mock()
    mock_opa_service = Mock()
    mock_opa_service.push_policy_data = AsyncMock(return_value=True)

    service = RoleMappingService(mock_db, mock_opa_service)

    from app.models.role_mapping import RoleMapping
    from datetime import datetime

    mapping = RoleMapping(
        id=1,
        application_id="test-app",
        environment="DEV",
        ad_group="test-group",
        role="admin",
        created_at=datetime.now(),
    )

    service.repository.create = Mock(return_value=mapping)
    service.repository.get_all_as_opa_data = Mock(return_value={"role_mappings": {}})

    # Capture log messages
    with patch("app.services.role_mapping_service.logger") as mock_logger:
        create_data = RoleMappingCreate(
            application_id="test-app",
            environment="DEV",
            ad_group="test-group",
            role="admin",
        )
        await service.create_role_mapping(create_data)

        # Verify logging occurred
        assert mock_logger.info.call_count >= 2  # Create + sync

        # Check log messages contain relevant information
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Creating role mapping" in str(call) for call in log_calls)
        assert any("Successfully created" in str(call) for call in log_calls)
