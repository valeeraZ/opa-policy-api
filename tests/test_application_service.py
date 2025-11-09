"""Tests for ApplicationService."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from app.services.application_service import ApplicationService
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.models.application import Application
from app.exceptions import ValidationError


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock()


@pytest.fixture
def mock_repository(monkeypatch):
    """Create a mock repository."""
    mock_repo = Mock()

    def mock_init(self, db):
        self.db = db
        self.repository = mock_repo

    monkeypatch.setattr(ApplicationService, "__init__", mock_init)
    return mock_repo


def test_create_application_success(mock_db, mock_repository):
    """Test successful application creation."""
    # Arrange
    service = ApplicationService(mock_db)
    app_data = ApplicationCreate(id="test-app", name="Test App", description="Test")

    mock_repository.get_by_id.return_value = None
    created_app = Application(
        id="test-app", name="Test App", description="Test", created_at=datetime.now()
    )
    mock_repository.create.return_value = created_app

    # Act
    result = service.create_application(app_data)

    # Assert
    assert result.id == "test-app"
    assert result.name == "Test App"
    mock_repository.get_by_id.assert_called_once_with("test-app")
    mock_repository.create.assert_called_once()


def test_create_application_duplicate(mock_db, mock_repository):
    """Test creating duplicate application raises ValidationError."""
    # Arrange
    service = ApplicationService(mock_db)
    app_data = ApplicationCreate(id="test-app", name="Test App")

    existing_app = Application(
        id="test-app", name="Existing", created_at=datetime.now()
    )
    mock_repository.get_by_id.return_value = existing_app

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        service.create_application(app_data)

    assert "already exists" in str(exc_info.value.message)
    mock_repository.create.assert_not_called()


def test_get_application_found(mock_db, mock_repository):
    """Test retrieving existing application."""
    # Arrange
    service = ApplicationService(mock_db)
    app = Application(id="test-app", name="Test App", created_at=datetime.now())
    mock_repository.get_by_id.return_value = app

    # Act
    result = service.get_application("test-app")

    # Assert
    assert result is not None
    assert result.id == "test-app"
    mock_repository.get_by_id.assert_called_once_with("test-app")


def test_get_application_not_found(mock_db, mock_repository):
    """Test retrieving non-existent application."""
    # Arrange
    service = ApplicationService(mock_db)
    mock_repository.get_by_id.return_value = None

    # Act
    result = service.get_application("nonexistent")

    # Assert
    assert result is None


def test_list_applications(mock_db, mock_repository):
    """Test listing all applications."""
    # Arrange
    service = ApplicationService(mock_db)
    apps = [
        Application(id="app1", name="App 1", created_at=datetime.now()),
        Application(id="app2", name="App 2", created_at=datetime.now()),
    ]
    mock_repository.get_all.return_value = apps

    # Act
    result = service.list_applications()

    # Assert
    assert len(result) == 2
    assert result[0].id == "app1"
    assert result[1].id == "app2"


def test_update_application_success(mock_db, mock_repository):
    """Test successful application update."""
    # Arrange
    service = ApplicationService(mock_db)
    app_data = ApplicationUpdate(name="Updated Name", description="Updated")

    existing_app = Application(
        id="test-app", name="Old Name", created_at=datetime.now()
    )
    mock_repository.get_by_id.return_value = existing_app
    mock_repository.update.return_value = existing_app

    # Act
    result = service.update_application("test-app", app_data)

    # Assert
    assert result.name == "Updated Name"
    mock_repository.update.assert_called_once()


def test_update_application_not_found(mock_db, mock_repository):
    """Test updating non-existent application raises ValidationError."""
    # Arrange
    service = ApplicationService(mock_db)
    app_data = ApplicationUpdate(name="Updated Name")
    mock_repository.get_by_id.return_value = None

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        service.update_application("nonexistent", app_data)

    assert "not found" in str(exc_info.value.message)


def test_delete_application_success(mock_db, mock_repository):
    """Test successful application deletion."""
    # Arrange
    service = ApplicationService(mock_db)
    mock_repository.delete.return_value = True

    # Act
    result = service.delete_application("test-app")

    # Assert
    assert result is True
    mock_repository.delete.assert_called_once_with("test-app")


def test_delete_application_not_found(mock_db, mock_repository):
    """Test deleting non-existent application."""
    # Arrange
    service = ApplicationService(mock_db)
    mock_repository.delete.return_value = False

    # Act
    result = service.delete_application("nonexistent")

    # Assert
    assert result is False
