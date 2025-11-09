"""Tests for custom policy router endpoints."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException, status
from datetime import datetime

from app.routers.custom_policies import (
    upload_custom_policy,
    list_custom_policies,
    get_custom_policy,
    evaluate_custom_policy
)
from app.schemas.custom_policy import (
    CustomPolicyCreate,
    CustomPolicyResponse,
    CustomPolicyEvaluate,
    CustomPolicyEvaluationResult
)
from app.schemas.user import UserInfo
from app.models.custom_policy import CustomPolicy
from app.exceptions import ValidationError, DatabaseError, OPAConnectionError, S3Error


@pytest.fixture
def admin_user():
    """Mock admin user."""
    return UserInfo(
        employee_id="admin123",
        ad_groups=["admin-group", "user-group"],
        email="admin@example.com",
        name="Admin User"
    )


@pytest.fixture
def regular_user():
    """Mock regular user."""
    return UserInfo(
        employee_id="user456",
        ad_groups=["user-group"],
        email="user@example.com",
        name="Regular User"
    )


@pytest.fixture
def sample_policy_create():
    """Sample custom policy create data."""
    return CustomPolicyCreate(
        id="test-policy",
        name="Test Policy",
        description="Test policy description",
        rego_content="package test\n\ndefault allow = false\n\nallow {\n    input.user.role == \"admin\"\n}"
    )


@pytest.fixture
def sample_policy_model():
    """Sample custom policy model."""
    return CustomPolicy(
        id="test-policy",
        name="Test Policy",
        description="Test policy description",
        s3_key="policies/test-policy/v20240115103000.rego",
        version="v20240115103000",
        creator_id="admin123",
        created_at=datetime(2024, 1, 15, 10, 30, 0),
        updated_at=None
    )


@pytest.fixture
def sample_policy_response():
    """Sample custom policy response."""
    return CustomPolicyResponse(
        id="test-policy",
        name="Test Policy",
        description="Test policy description",
        s3_key="policies/test-policy/v20240115103000.rego",
        version="v20240115103000",
        creator_id="admin123",
        created_at=datetime(2024, 1, 15, 10, 30, 0),
        updated_at=None
    )


@pytest.fixture
def sample_evaluation_request():
    """Sample policy evaluation request."""
    return CustomPolicyEvaluate(
        input_data={
            "user": {"role": "admin"},
            "resource": {"type": "document"}
        }
    )


@pytest.fixture
def mock_service():
    """Mock CustomPolicyService."""
    service = Mock()
    # Make async methods return AsyncMock
    service.upload_policy = AsyncMock()
    service.list_policies = AsyncMock()
    service.get_policy = AsyncMock()
    service.evaluate_policy = AsyncMock()
    return service


class TestUploadCustomPolicy:
    """Tests for POST /custom-policies endpoint."""
    
    @pytest.mark.asyncio
    async def test_upload_policy_success(
        self, admin_user, sample_policy_create, sample_policy_model, mock_service
    ):
        """Test successful custom policy upload."""
        # Arrange
        mock_service.upload_policy.return_value = sample_policy_model
        
        # Act
        result = await upload_custom_policy(sample_policy_create, admin_user, mock_service)
        
        # Assert
        assert result.id == "test-policy"
        assert result.name == "Test Policy"
        mock_service.upload_policy.assert_called_once_with(
            policy_data=sample_policy_create,
            creator_id="admin123"
        )
    
    @pytest.mark.asyncio
    async def test_upload_policy_validation_error(
        self, admin_user, sample_policy_create, mock_service
    ):
        """Test uploading policy with invalid Rego syntax returns 400."""
        # Arrange
        mock_service.upload_policy.side_effect = ValidationError(
            message="Rego policy has syntax errors",
            detail="unexpected token at line 5"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_custom_policy(sample_policy_create, admin_user, mock_service)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "syntax errors" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_upload_policy_duplicate(
        self, admin_user, sample_policy_create, mock_service
    ):
        """Test uploading duplicate policy returns 409."""
        # Arrange
        mock_service.upload_policy.side_effect = DatabaseError(
            message="Policy already exists",
            detail="Duplicate key error"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_custom_policy(sample_policy_create, admin_user, mock_service)
        
        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_upload_policy_s3_error(
        self, admin_user, sample_policy_create, mock_service
    ):
        """Test S3 error during upload returns 500."""
        # Arrange
        mock_service.upload_policy.side_effect = S3Error(
            message="Failed to upload to S3",
            detail="Access denied"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_custom_policy(sample_policy_create, admin_user, mock_service)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "S3" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_upload_policy_opa_error(
        self, admin_user, sample_policy_create, mock_service
    ):
        """Test OPA error during upload returns 503."""
        # Arrange
        mock_service.upload_policy.side_effect = OPAConnectionError(
            message="Failed to upload policy to OPA",
            detail="Connection refused"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_custom_policy(sample_policy_create, admin_user, mock_service)
        
        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "OPA" in exc_info.value.detail


class TestListCustomPolicies:
    """Tests for GET /custom-policies endpoint."""
    
    @pytest.mark.asyncio
    async def test_list_policies_success(
        self, regular_user, sample_policy_model, mock_service
    ):
        """Test successful listing of custom policies."""
        # Arrange
        mock_service.list_policies.return_value = [sample_policy_model]
        
        # Act
        result = await list_custom_policies(regular_user, mock_service)
        
        # Assert
        assert len(result) == 1
        assert result[0].id == "test-policy"
        mock_service.list_policies.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_policies_empty(
        self, regular_user, mock_service
    ):
        """Test listing policies when none exist."""
        # Arrange
        mock_service.list_policies.return_value = []
        
        # Act
        result = await list_custom_policies(regular_user, mock_service)
        
        # Assert
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_list_policies_database_error(
        self, regular_user, mock_service
    ):
        """Test database error during listing returns 500."""
        # Arrange
        mock_service.list_policies.side_effect = DatabaseError(
            message="Database connection failed"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_custom_policies(regular_user, mock_service)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestGetCustomPolicy:
    """Tests for GET /custom-policies/{policy_id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_policy_success(
        self, regular_user, sample_policy_model, mock_service
    ):
        """Test successful retrieval of custom policy."""
        # Arrange
        mock_service.get_policy.return_value = sample_policy_model
        
        # Act
        result = await get_custom_policy("test-policy", regular_user, mock_service)
        
        # Assert
        assert result.id == "test-policy"
        assert result.name == "Test Policy"
        mock_service.get_policy.assert_called_once_with("test-policy")
    
    @pytest.mark.asyncio
    async def test_get_policy_not_found(
        self, regular_user, mock_service
    ):
        """Test retrieving non-existent policy returns 404."""
        # Arrange
        mock_service.get_policy.return_value = None
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_custom_policy("nonexistent", regular_user, mock_service)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_policy_database_error(
        self, regular_user, mock_service
    ):
        """Test database error during retrieval returns 500."""
        # Arrange
        mock_service.get_policy.side_effect = DatabaseError(
            message="Database connection failed"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_custom_policy("test-policy", regular_user, mock_service)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestEvaluateCustomPolicy:
    """Tests for POST /custom-policies/{policy_id}/evaluate endpoint."""
    
    @pytest.mark.asyncio
    async def test_evaluate_policy_success(
        self, regular_user, sample_evaluation_request, mock_service
    ):
        """Test successful policy evaluation."""
        # Arrange
        mock_service.evaluate_policy.return_value = {
            "allow": True,
            "reason": "User has admin role"
        }
        
        # Act
        result = await evaluate_custom_policy(
            "test-policy",
            sample_evaluation_request,
            regular_user,
            mock_service
        )
        
        # Assert
        assert result.policy_id == "test-policy"
        assert result.result["allow"] is True
        mock_service.evaluate_policy.assert_called_once_with(
            policy_id="test-policy",
            input_data=sample_evaluation_request.input_data
        )
    
    @pytest.mark.asyncio
    async def test_evaluate_policy_not_found(
        self, regular_user, sample_evaluation_request, mock_service
    ):
        """Test evaluating non-existent policy returns 404."""
        # Arrange
        mock_service.evaluate_policy.side_effect = ValidationError(
            message="Policy 'test-policy' does not exist",
            detail="Policy must be uploaded before evaluation"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await evaluate_custom_policy(
                "test-policy",
                sample_evaluation_request,
                regular_user,
                mock_service
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "does not exist" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_evaluate_policy_opa_error(
        self, regular_user, sample_evaluation_request, mock_service
    ):
        """Test OPA error during evaluation returns 503."""
        # Arrange
        mock_service.evaluate_policy.side_effect = OPAConnectionError(
            message="Failed to evaluate policy",
            detail="OPA server unreachable"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await evaluate_custom_policy(
                "test-policy",
                sample_evaluation_request,
                regular_user,
                mock_service
            )
        
        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Failed to evaluate policy" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_evaluate_policy_with_complex_result(
        self, regular_user, sample_evaluation_request, mock_service
    ):
        """Test policy evaluation with complex result structure."""
        # Arrange
        complex_result = {
            "allow": False,
            "reason": "User lacks required permissions",
            "required_permissions": ["read", "write"],
            "user_permissions": ["read"]
        }
        mock_service.evaluate_policy.return_value = complex_result
        
        # Act
        result = await evaluate_custom_policy(
            "test-policy",
            sample_evaluation_request,
            regular_user,
            mock_service
        )
        
        # Assert
        assert result.policy_id == "test-policy"
        assert result.result["allow"] is False
        assert "required_permissions" in result.result
        assert len(result.result["required_permissions"]) == 2
