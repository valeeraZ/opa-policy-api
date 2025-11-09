"""Tests for CustomPolicyService."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.custom_policy_service import CustomPolicyService
from app.services.opa_service import OPAService
from app.services.s3_service import S3Service
from app.models.custom_policy import CustomPolicy
from app.schemas.custom_policy import CustomPolicyCreate
from app.exceptions import ValidationError, OPAConnectionError, S3Error, DatabaseError


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def mock_opa_service():
    """Mock OPA service."""
    service = Mock(spec=OPAService)
    service.opa_url = "http://localhost:8181"
    service.client = AsyncMock()
    service.upload_policy = AsyncMock(return_value=True)
    service.evaluate_custom_policy = AsyncMock(return_value={"allow": True})
    return service


@pytest.fixture
def mock_s3_service():
    """Mock S3 service."""
    service = Mock(spec=S3Service)
    service.upload_policy_file = AsyncMock(return_value="policies/test-policy/v1.rego")
    service.download_policy_file = AsyncMock(
        return_value="package test\ndefault allow = false"
    )
    service.list_policy_versions = AsyncMock(return_value=["v1", "v2"])
    return service


@pytest.fixture
def custom_policy_service(mock_db, mock_opa_service, mock_s3_service):
    """Create CustomPolicyService instance with mocked dependencies."""
    return CustomPolicyService(
        db=mock_db, opa_service=mock_opa_service, s3_service=mock_s3_service
    )


@pytest.fixture
def sample_policy_create():
    """Sample policy creation data."""
    return CustomPolicyCreate(
        id="test-policy",
        name="Test Policy",
        description="A test policy",
        rego_content='package test\n\ndefault allow = false\n\nallow {\n    input.user.role == "admin"\n}',
    )


@pytest.fixture
def sample_custom_policy():
    """Sample CustomPolicy model instance."""
    return CustomPolicy(
        id="test-policy",
        name="Test Policy",
        description="A test policy",
        s3_key="policies/test-policy/v1.rego",
        version="v1",
        creator_id="E12345",
        created_at=datetime.now(),
    )


class TestValidateRego:
    """Tests for validate_rego method."""

    @pytest.mark.asyncio
    async def test_validate_rego_success(self, custom_policy_service, mock_opa_service):
        """Test successful Rego validation."""
        rego_content = "package test\ndefault allow = false"

        # Mock successful upload and delete
        mock_opa_service.upload_policy.return_value = True
        mock_opa_service.client.delete = AsyncMock(return_value=Mock(status_code=200))

        is_valid, error_message = await custom_policy_service.validate_rego(
            rego_content
        )

        assert is_valid is True
        assert error_message is None
        mock_opa_service.upload_policy.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_rego_syntax_error(
        self, custom_policy_service, mock_opa_service
    ):
        """Test Rego validation with syntax error."""
        rego_content = "package test\ninvalid syntax here"

        # Mock OPA returning validation error
        mock_opa_service.upload_policy.side_effect = OPAConnectionError(
            "Syntax error", detail="unexpected token"
        )

        is_valid, error_message = await custom_policy_service.validate_rego(
            rego_content
        )

        assert is_valid is False
        assert error_message is not None
        assert "unexpected token" in error_message


class TestUploadPolicy:
    """Tests for upload_policy method."""

    @pytest.mark.asyncio
    async def test_upload_policy_success(
        self,
        custom_policy_service,
        sample_policy_create,
        mock_opa_service,
        mock_s3_service,
        sample_custom_policy,
    ):
        """Test successful policy upload."""
        # Mock validation success
        with patch.object(
            custom_policy_service, "validate_rego", return_value=(True, None)
        ):
            # Mock repository create
            custom_policy_service.repository.create = Mock(
                return_value=sample_custom_policy
            )

            result = await custom_policy_service.upload_policy(
                policy_data=sample_policy_create, creator_id="E12345"
            )

            assert result.id == "test-policy"
            assert result.name == "Test Policy"
            mock_s3_service.upload_policy_file.assert_called_once()
            mock_opa_service.upload_policy.assert_called_once()
            custom_policy_service.repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_policy_validation_failure(
        self, custom_policy_service, sample_policy_create
    ):
        """Test policy upload with validation failure."""
        # Mock validation failure
        with patch.object(
            custom_policy_service, "validate_rego", return_value=(False, "Syntax error")
        ):
            with pytest.raises(ValidationError) as exc_info:
                await custom_policy_service.upload_policy(
                    policy_data=sample_policy_create, creator_id="E12345"
                )

            assert "syntax errors" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_upload_policy_s3_failure(
        self, custom_policy_service, sample_policy_create, mock_s3_service
    ):
        """Test policy upload with S3 failure."""
        # Mock validation success
        with patch.object(
            custom_policy_service, "validate_rego", return_value=(True, None)
        ):
            # Mock S3 failure
            mock_s3_service.upload_policy_file.side_effect = S3Error(
                "S3 upload failed", detail="Connection timeout"
            )

            with pytest.raises(S3Error):
                await custom_policy_service.upload_policy(
                    policy_data=sample_policy_create, creator_id="E12345"
                )

    @pytest.mark.asyncio
    async def test_upload_policy_database_failure(
        self, custom_policy_service, sample_policy_create, mock_s3_service
    ):
        """Test policy upload with database failure."""
        # Mock validation success
        with patch.object(
            custom_policy_service, "validate_rego", return_value=(True, None)
        ):
            # Mock database failure
            custom_policy_service.repository.create = Mock(
                side_effect=DatabaseError("Database error", detail="Duplicate key")
            )

            with pytest.raises(DatabaseError):
                await custom_policy_service.upload_policy(
                    policy_data=sample_policy_create, creator_id="E12345"
                )

            # S3 upload should have been called before DB failure
            mock_s3_service.upload_policy_file.assert_called_once()


class TestGetPolicy:
    """Tests for get_policy method."""

    @pytest.mark.asyncio
    async def test_get_policy_success(
        self, custom_policy_service, sample_custom_policy
    ):
        """Test successful policy retrieval."""
        custom_policy_service.repository.get_by_id = Mock(
            return_value=sample_custom_policy
        )

        result = await custom_policy_service.get_policy("test-policy")

        assert result is not None
        assert result.id == "test-policy"
        custom_policy_service.repository.get_by_id.assert_called_once_with(
            "test-policy"
        )

    @pytest.mark.asyncio
    async def test_get_policy_not_found(self, custom_policy_service):
        """Test policy retrieval when policy doesn't exist."""
        custom_policy_service.repository.get_by_id = Mock(return_value=None)

        result = await custom_policy_service.get_policy("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_policy_database_error(self, custom_policy_service):
        """Test policy retrieval with database error."""
        custom_policy_service.repository.get_by_id = Mock(
            side_effect=DatabaseError("Database error", detail="Connection lost")
        )

        with pytest.raises(DatabaseError):
            await custom_policy_service.get_policy("test-policy")


class TestListPolicies:
    """Tests for list_policies method."""

    @pytest.mark.asyncio
    async def test_list_policies_success(
        self, custom_policy_service, sample_custom_policy
    ):
        """Test successful policies listing."""
        policies = [sample_custom_policy]
        custom_policy_service.repository.get_all = Mock(return_value=policies)

        result = await custom_policy_service.list_policies()

        assert len(result) == 1
        assert result[0].id == "test-policy"
        custom_policy_service.repository.get_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_policies_empty(self, custom_policy_service):
        """Test listing policies when none exist."""
        custom_policy_service.repository.get_all = Mock(return_value=[])

        result = await custom_policy_service.list_policies()

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_policies_database_error(self, custom_policy_service):
        """Test listing policies with database error."""
        custom_policy_service.repository.get_all = Mock(
            side_effect=DatabaseError("Database error", detail="Connection lost")
        )

        with pytest.raises(DatabaseError):
            await custom_policy_service.list_policies()


class TestEvaluatePolicy:
    """Tests for evaluate_policy method."""

    @pytest.mark.asyncio
    async def test_evaluate_policy_success(
        self, custom_policy_service, sample_custom_policy, mock_opa_service
    ):
        """Test successful policy evaluation."""
        custom_policy_service.repository.get_by_id = Mock(
            return_value=sample_custom_policy
        )
        mock_opa_service.evaluate_custom_policy.return_value = {"allow": True}

        input_data = {"user": {"role": "admin"}}
        result = await custom_policy_service.evaluate_policy(
            policy_id="test-policy", input_data=input_data
        )

        assert result == {"allow": True}
        mock_opa_service.evaluate_custom_policy.assert_called_once_with(
            policy_id="test-policy", input_data=input_data, query_path=None
        )

    @pytest.mark.asyncio
    async def test_evaluate_policy_with_query_path(
        self, custom_policy_service, sample_custom_policy, mock_opa_service
    ):
        """Test policy evaluation with specific query path."""
        custom_policy_service.repository.get_by_id = Mock(
            return_value=sample_custom_policy
        )
        mock_opa_service.evaluate_custom_policy.return_value = True

        input_data = {"user": {"role": "admin"}}
        result = await custom_policy_service.evaluate_policy(
            policy_id="test-policy", input_data=input_data, query_path="allow"
        )

        assert result is True
        mock_opa_service.evaluate_custom_policy.assert_called_once_with(
            policy_id="test-policy", input_data=input_data, query_path="allow"
        )

    @pytest.mark.asyncio
    async def test_evaluate_policy_not_found(self, custom_policy_service):
        """Test evaluating non-existent policy."""
        custom_policy_service.repository.get_by_id = Mock(return_value=None)

        with pytest.raises(ValidationError) as exc_info:
            await custom_policy_service.evaluate_policy(
                policy_id="nonexistent", input_data={}
            )

        assert "does not exist" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_evaluate_policy_opa_error(
        self, custom_policy_service, sample_custom_policy, mock_opa_service
    ):
        """Test policy evaluation with OPA error."""
        custom_policy_service.repository.get_by_id = Mock(
            return_value=sample_custom_policy
        )
        mock_opa_service.evaluate_custom_policy.side_effect = OPAConnectionError(
            "OPA error", detail="Connection refused"
        )

        with pytest.raises(OPAConnectionError):
            await custom_policy_service.evaluate_policy(
                policy_id="test-policy", input_data={}
            )
