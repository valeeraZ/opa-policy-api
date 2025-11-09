"""Tests for OPA Service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from app.services.opa_service import OPAService
from app.schemas.user import UserInfo
from app.models.application import Application
from app.models.role_mapping import RoleMapping
from app.exceptions import OPAConnectionError


@pytest.fixture
def opa_service():
    """Create OPA service instance for testing."""
    service = OPAService(opa_url="http://localhost:8181", timeout=5)
    return service


@pytest.fixture
def sample_user_info():
    """Sample user info for testing."""
    return UserInfo(
        employee_id="E12345",
        ad_groups=["infodir-application-a-admin", "infodir-application-b-user"],
        email="test@example.com",
        name="Test User"
    )


@pytest.fixture
def sample_applications():
    """Sample applications for testing."""
    app1 = Application(id="app-a", name="Application A", description="Test App A")
    app2 = Application(id="app-b", name="Application B", description="Test App B")
    return [app1, app2]


@pytest.fixture
def sample_role_mappings():
    """Sample role mappings for testing."""
    mapping1 = RoleMapping(
        id=1,
        application_id="app-a",
        environment="DEV",
        ad_group="infodir-application-a-admin",
        role="admin"
    )
    mapping2 = RoleMapping(
        id=2,
        application_id="app-b",
        environment="DEV",
        ad_group="infodir-application-b-user",
        role="user"
    )
    return [mapping1, mapping2]


@pytest.mark.asyncio
async def test_health_check_success(opa_service):
    """Test successful health check."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    with patch.object(opa_service.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await opa_service.health_check()
        
        assert result is True
        mock_get.assert_called_once_with("http://localhost:8181/health")


@pytest.mark.asyncio
async def test_health_check_failure_with_retry(opa_service):
    """Test health check with retries on failure."""
    import httpx
    
    with patch.object(opa_service.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.RequestError("Connection refused")
        
        with pytest.raises(OPAConnectionError) as exc_info:
            await opa_service.health_check()
        
        assert "OPA server is unreachable" in str(exc_info.value.message)
        assert mock_get.call_count == 3  # Should retry 3 times


@pytest.mark.asyncio
async def test_upload_base_policy_success(opa_service):
    """Test successful base policy upload."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    policy_content = "package permissions\n\ndefault allow = false"
    
    with patch('builtins.open', mock_open(read_data=policy_content)):
        with patch.object(opa_service.client, 'put', new_callable=AsyncMock) as mock_put:
            mock_put.return_value = mock_response
            
            result = await opa_service.upload_base_policy("test_policy.rego")
            
            assert result is True
            mock_put.assert_called_once()


@pytest.mark.asyncio
async def test_evaluate_permissions_success(opa_service, sample_user_info, sample_applications, sample_role_mappings):
    """Test successful permission evaluation."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "app-a": "admin",
            "app-b": "user"
        }
    }
    
    with patch.object(opa_service.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await opa_service.evaluate_permissions(
            sample_user_info,
            sample_applications,
            sample_role_mappings
        )
        
        assert result == {"app-a": "admin", "app-b": "user"}
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_push_policy_data_success(opa_service):
    """Test successful policy data push."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    test_data = {
        "app-a": {
            "DEV": {
                "infodir-application-a-admin": "admin"
            }
        }
    }
    
    with patch.object(opa_service.client, 'put', new_callable=AsyncMock) as mock_put:
        mock_put.return_value = mock_response
        
        result = await opa_service.push_policy_data("role_mappings", test_data)
        
        assert result is True
        mock_put.assert_called_once_with(
            "http://localhost:8181/v1/data/role_mappings",
            json=test_data
        )


@pytest.mark.asyncio
async def test_upload_policy_success(opa_service):
    """Test successful policy upload."""
    mock_response = MagicMock()
    mock_response.status_code = 201
    
    policy_content = "package custom\n\nallow = true"
    
    with patch.object(opa_service.client, 'put', new_callable=AsyncMock) as mock_put:
        mock_put.return_value = mock_response
        
        result = await opa_service.upload_policy("custom_policy", policy_content)
        
        assert result is True
        mock_put.assert_called_once()


@pytest.mark.asyncio
async def test_evaluate_custom_policy_success(opa_service):
    """Test successful custom policy evaluation."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {"allow": True}
    }
    
    input_data = {"user": "test", "action": "read"}
    
    with patch.object(opa_service.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await opa_service.evaluate_custom_policy("custom_policy", input_data)
        
        assert result == {"allow": True}
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_format_opa_input(opa_service, sample_user_info, sample_applications, sample_role_mappings):
    """Test OPA input formatting."""
    result = opa_service._format_opa_input(
        sample_user_info,
        sample_applications,
        sample_role_mappings
    )
    
    assert result["user"]["employee_id"] == "E12345"
    assert "infodir-application-a-admin" in result["user"]["ad_groups"]
    assert result["applications"] == ["app-a", "app-b"]
