"""Tests for health check router."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from botocore.exceptions import ClientError

from app.routers.health import router
from app.services.opa_service import OPAService
from app.services.s3_service import S3Service
from app.exceptions import OPAConnectionError


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock(spec=Session)
    return db


@pytest.fixture
def mock_opa_service():
    """Mock OPA service."""
    service = Mock(spec=OPAService)
    service.health_check = AsyncMock()
    service.close = AsyncMock()
    return service


@pytest.fixture
def mock_s3_service():
    """Mock S3 service."""
    service = Mock(spec=S3Service)
    service.bucket = "test-bucket"
    service.s3_client = Mock()
    return service


@pytest.fixture
def client(mock_db, mock_opa_service, mock_s3_service):
    """Create test client with mocked dependencies."""
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    
    # Override dependencies
    def override_get_db():
        return mock_db
    
    def override_get_opa_service():
        return mock_opa_service
    
    def override_get_s3_service():
        return mock_s3_service
    
    from app.routers.health import get_opa_service, get_s3_service
    from app.database import get_db
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_opa_service] = override_get_opa_service
    app.dependency_overrides[get_s3_service] = override_get_s3_service
    
    return TestClient(app)


class TestHealthCheckEndpoint:
    """Tests for GET /health endpoint."""
    
    def test_health_check_all_healthy(self, client, mock_db, mock_opa_service, mock_s3_service):
        """Test health check when all services are healthy."""
        # Arrange
        mock_db.execute.return_value = None
        mock_opa_service.health_check.return_value = True
        mock_s3_service.s3_client.head_bucket.return_value = {}
        
        # Act
        response = client.get("/health")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["components"]["database"]["status"] == "healthy"
        assert data["components"]["opa"]["status"] == "healthy"
        assert data["components"]["s3"]["status"] == "healthy"
    
    def test_health_check_database_unhealthy(self, client, mock_db, mock_opa_service, mock_s3_service):
        """Test health check when database is unhealthy."""
        # Arrange
        mock_db.execute.side_effect = Exception("Database connection failed")
        mock_opa_service.health_check.return_value = True
        mock_s3_service.s3_client.head_bucket.return_value = {}
        
        # Act
        response = client.get("/health")
        
        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["components"]["database"]["status"] == "unhealthy"
        assert "Database connection failed" in data["components"]["database"]["message"]
    
    def test_health_check_opa_unhealthy(self, client, mock_db, mock_opa_service, mock_s3_service):
        """Test health check when OPA is unhealthy."""
        # Arrange
        mock_db.execute.return_value = None
        mock_opa_service.health_check.side_effect = OPAConnectionError("OPA unreachable")
        mock_s3_service.s3_client.head_bucket.return_value = {}
        
        # Act
        response = client.get("/health")
        
        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["components"]["opa"]["status"] == "unhealthy"
        assert "OPA server unreachable" in data["components"]["opa"]["message"]
    
    def test_health_check_s3_unhealthy(self, client, mock_db, mock_opa_service, mock_s3_service):
        """Test health check when S3 is unhealthy."""
        # Arrange
        mock_db.execute.return_value = None
        mock_opa_service.health_check.return_value = True
        mock_s3_service.s3_client.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "Bucket not found"}},
            "HeadBucket"
        )
        
        # Act
        response = client.get("/health")
        
        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["components"]["s3"]["status"] == "unhealthy"
    
    def test_health_check_all_unhealthy(self, client, mock_db, mock_opa_service, mock_s3_service):
        """Test health check when all services are unhealthy."""
        # Arrange
        mock_db.execute.side_effect = Exception("Database error")
        mock_opa_service.health_check.side_effect = OPAConnectionError("OPA error")
        mock_s3_service.s3_client.head_bucket.side_effect = Exception("S3 error")
        
        # Act
        response = client.get("/health")
        
        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["components"]["database"]["status"] == "unhealthy"
        assert data["components"]["opa"]["status"] == "unhealthy"
        assert data["components"]["s3"]["status"] == "unhealthy"


class TestHealthCheckOPAEndpoint:
    """Tests for GET /health/opa endpoint."""
    
    def test_opa_health_check_healthy(self, client, mock_opa_service):
        """Test OPA health check when OPA is healthy."""
        # Arrange
        mock_opa_service.health_check.return_value = True
        
        # Act
        response = client.get("/health/opa")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "OPA server is reachable" in data["message"]
    
    def test_opa_health_check_unhealthy(self, client, mock_opa_service):
        """Test OPA health check when OPA is unhealthy."""
        # Arrange
        mock_opa_service.health_check.side_effect = OPAConnectionError("Connection refused")
        
        # Act
        response = client.get("/health/opa")
        
        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "OPA server unreachable" in data["message"]
    
    def test_opa_health_check_exception(self, client, mock_opa_service):
        """Test OPA health check with unexpected exception."""
        # Arrange
        mock_opa_service.health_check.side_effect = Exception("Unexpected error")
        
        # Act
        response = client.get("/health/opa")
        
        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "OPA health check error" in data["message"]


class TestHealthCheckDBEndpoint:
    """Tests for GET /health/db endpoint."""
    
    def test_db_health_check_healthy(self, client, mock_db):
        """Test database health check when database is healthy."""
        # Arrange
        mock_db.execute.return_value = None
        
        # Act
        response = client.get("/health/db")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "Database connection successful" in data["message"]
    
    def test_db_health_check_unhealthy(self, client, mock_db):
        """Test database health check when database is unhealthy."""
        # Arrange
        mock_db.execute.side_effect = Exception("Connection timeout")
        
        # Act
        response = client.get("/health/db")
        
        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "Database connection failed" in data["message"]


class TestHealthCheckS3Endpoint:
    """Tests for GET /health/s3 endpoint."""
    
    def test_s3_health_check_healthy(self, client, mock_s3_service):
        """Test S3 health check when S3 is accessible."""
        # Arrange
        mock_s3_service.s3_client.head_bucket.return_value = {}
        
        # Act
        response = client.get("/health/s3")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "S3 bucket" in data["message"]
        assert "accessible" in data["message"]
    
    def test_s3_health_check_unhealthy(self, client, mock_s3_service):
        """Test S3 health check when S3 is not accessible."""
        # Arrange
        mock_s3_service.s3_client.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "403", "Message": "Access Denied"}},
            "HeadBucket"
        )
        
        # Act
        response = client.get("/health/s3")
        
        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "S3 bucket not accessible" in data["message"]
    
    def test_s3_health_check_bucket_not_found(self, client, mock_s3_service):
        """Test S3 health check when bucket doesn't exist."""
        # Arrange
        mock_s3_service.s3_client.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "The specified bucket does not exist"}},
            "HeadBucket"
        )
        
        # Act
        response = client.get("/health/s3")
        
        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "S3 bucket not accessible" in data["message"]
