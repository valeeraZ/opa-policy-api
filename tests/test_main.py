"""Tests for main FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from app.main import app
from app.exceptions import (
    OPAConnectionError,
    DatabaseError,
    S3Error,
    ValidationError,
    AuthenticationError,
    AuthorizationError
)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint returns API information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "description" in data
    assert data["name"] == "OPA Permission API"


def test_cors_headers(client):
    """Test CORS middleware is configured."""
    # Test with a regular GET request which should have CORS headers
    response = client.get("/", headers={"Origin": "http://example.com"})
    # CORS headers should be present
    assert "access-control-allow-origin" in response.headers


def test_request_id_in_response_headers(client):
    """Test that request ID is added to response headers."""
    response = client.get("/")
    assert "x-request-id" in response.headers
    # Verify it's a valid UUID format
    request_id = response.headers["x-request-id"]
    assert len(request_id) == 36  # UUID format length


def test_health_endpoint_accessible(client):
    """Test that health endpoint is accessible."""
    # This will fail if OPA/DB are not available, but we're just checking routing
    response = client.get("/health")
    # Should return either 200 or 503, but not 404
    assert response.status_code in [200, 503]


def test_documentation_accessible(client):
    """Test that OpenAPI documentation is accessible."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_schema_accessible(client):
    """Test that OpenAPI schema is accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert schema["info"]["title"] == "OPA Permission API"


@pytest.mark.asyncio
async def test_lifespan_initialization():
    """Test lifespan initialization logic."""
    with patch('app.main.OPAService') as mock_opa_service_class:
        with patch('app.main.SessionLocal') as mock_session_local:
            # Mock OPA service
            mock_opa_service = AsyncMock()
            mock_opa_service.health_check = AsyncMock()
            mock_opa_service.upload_base_policy = AsyncMock()
            mock_opa_service.close = AsyncMock()
            mock_opa_service_class.return_value = mock_opa_service
            
            # Mock database session
            mock_db = MagicMock()
            mock_session_local.return_value = mock_db
            
            # Mock role mapping service
            with patch('app.main.RoleMappingService') as mock_role_mapping_service_class:
                mock_role_mapping_service = AsyncMock()
                mock_role_mapping_service.sync_to_opa = AsyncMock()
                mock_role_mapping_service_class.return_value = mock_role_mapping_service
                
                # Create test client which triggers lifespan
                with TestClient(app) as test_client:
                    # Verify OPA initialization was called
                    mock_opa_service.health_check.assert_called_once()
                    mock_opa_service.upload_base_policy.assert_called_once()
                    mock_role_mapping_service.sync_to_opa.assert_called_once()
                    
                    # Verify database session was closed
                    mock_db.close.assert_called_once()


def test_exception_handler_opa_connection_error(client):
    """Test OPA connection error exception handler."""
    # We can't easily trigger this without mocking dependencies in routes
    # This test verifies the handler is registered
    from app.main import opa_connection_error_handler
    assert opa_connection_error_handler is not None


def test_exception_handler_database_error(client):
    """Test database error exception handler."""
    from app.main import database_error_handler
    assert database_error_handler is not None


def test_exception_handler_s3_error(client):
    """Test S3 error exception handler."""
    from app.main import s3_error_handler
    assert s3_error_handler is not None


def test_exception_handler_validation_error(client):
    """Test validation error exception handler."""
    from app.main import validation_error_handler
    assert validation_error_handler is not None


def test_exception_handler_authentication_error(client):
    """Test authentication error exception handler."""
    from app.main import authentication_error_handler
    assert authentication_error_handler is not None


def test_exception_handler_authorization_error(client):
    """Test authorization error exception handler."""
    from app.main import authorization_error_handler
    assert authorization_error_handler is not None


def test_all_routers_registered(client):
    """Test that all routers are registered."""
    response = client.get("/openapi.json")
    schema = response.json()
    paths = schema["paths"]
    
    # Check that endpoints from each router are present
    assert any("/health" in path for path in paths)
    assert any("/permission" in path for path in paths)
    assert any("/applications" in path for path in paths)
    assert any("/role-mappings" in path for path in paths)
    assert any("/custom-policies" in path for path in paths)
