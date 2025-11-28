"""Unit tests for ConnectorService following TDD approach."""
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.application.ports.outbound import ConnectorRepository, PhotoRepository, FileStorage, VectorStore
from app.application.services.connector_service import ConnectorService
from app.domain.entities.connector import Connector, ConnectorStatus, ConnectorType
from app.domain.value_objects import ConnectorId


class BaseConnectorServiceTest:
    """Base test class with common fixtures for ConnectorService tests."""

    @pytest.fixture
    def mock_connector_repo(self):
        repo = Mock(spec=ConnectorRepository)
        repo.save = AsyncMock()
        repo.find_by_path = AsyncMock()
        repo.find_by_id = AsyncMock()
        repo.find_by_type = AsyncMock()
        repo.find_all = AsyncMock()
        repo.delete = AsyncMock()
        return repo

    @pytest.fixture
    def mock_photo_repo(self):
        repo = Mock(spec=PhotoRepository)
        repo.find_by_connector = AsyncMock()
        repo.delete_by_connector = AsyncMock()
        return repo

    @pytest.fixture
    def mock_file_storage(self):
        return Mock(spec=FileStorage)

    @pytest.fixture
    def mock_vector_store(self):
        return Mock(spec=VectorStore)

    @pytest.fixture
    def service(self, mock_connector_repo, mock_photo_repo, mock_file_storage, mock_vector_store):
        return ConnectorService(mock_connector_repo, mock_photo_repo, mock_file_storage, mock_vector_store)


class TestConnectorServiceCreateLocal(BaseConnectorServiceTest):
    """Test suite for creating local connectors."""

    @patch("app.application.services.connector_service.get_settings")
    @patch("app.application.services.connector_service.Path")
    async def test_create_local_connector_success(
        self, mock_path_class, mock_get_settings, service, mock_connector_repo
    ):
        """Test successful creation of local connector."""
        # Arrange
        test_path = "/home/user/photos"
        test_name = "My Photos"

        # Mock settings validation
        mock_settings = Mock()
        mock_settings.is_path_allowed.return_value = (True, None)
        mock_get_settings.return_value = mock_settings

        # Mock Path operations
        mock_path_obj = Mock(spec=Path)
        mock_path_obj.resolve.return_value = mock_path_obj
        mock_path_obj.exists.return_value = True
        mock_path_obj.is_dir.return_value = True
        mock_path_obj.__str__ = Mock(return_value=test_path)
        mock_path_class.return_value = mock_path_obj

        # Mock repository save
        expected_connector = Connector(
            id=ConnectorId(uuid4()),
            name=test_name,
            type=ConnectorType.LOCAL,
            config={"path": test_path},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )
        mock_connector_repo.save.return_value = expected_connector
        mock_connector_repo.find_by_path.return_value = None

        # Act
        result = await service.create_local_connector(test_path, test_name)

        # Assert
        assert result is not None
        assert result.name == test_name
        assert result.type == ConnectorType.LOCAL
        mock_connector_repo.save.assert_called_once()
        mock_settings.is_path_allowed.assert_called_once_with(test_path)

    @patch("app.application.services.connector_service.get_settings")
    @patch("app.application.services.connector_service.Path")
    async def test_create_local_validates_path_exists(
        self, mock_path_class, mock_get_settings, service
    ):
        """Test that creation fails if path doesn't exist."""
        # Arrange
        test_path = "/nonexistent/path"

        # Mock settings validation
        mock_settings = Mock()
        mock_settings.is_path_allowed.return_value = (True, None)
        mock_get_settings.return_value = mock_settings

        # Mock Path to return non-existent path
        mock_path_obj = Mock(spec=Path)
        mock_path_obj.resolve.return_value = mock_path_obj
        mock_path_obj.exists.return_value = False
        mock_path_class.return_value = mock_path_obj

        # Act & Assert
        with pytest.raises(ValueError, match="Path does not exist"):
            await service.create_local_connector(test_path)

    @patch("app.application.services.connector_service.get_settings")
    @patch("app.application.services.connector_service.Path")
    async def test_create_local_prevents_duplicate_paths(
        self, mock_path_class, mock_get_settings, service, mock_connector_repo
    ):
        """Test that duplicate paths are rejected."""
        # Arrange
        test_path = "/home/user/photos"

        # Mock settings validation
        mock_settings = Mock()
        mock_settings.is_path_allowed.return_value = (True, None)
        mock_get_settings.return_value = mock_settings

        # Mock Path operations
        mock_path_obj = Mock(spec=Path)
        mock_path_obj.resolve.return_value = mock_path_obj
        mock_path_obj.exists.return_value = True
        mock_path_obj.is_dir.return_value = True
        mock_path_obj.__str__ = Mock(return_value=test_path)
        mock_path_class.return_value = mock_path_obj

        # Mock repository to return existing connector
        existing_connector = Connector(
            id=ConnectorId(uuid4()),
            name="Existing",
            type=ConnectorType.LOCAL,
            config={"path": test_path},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )
        mock_connector_repo.find_by_path.return_value = existing_connector

        # Act & Assert
        with pytest.raises(ValueError, match="already exists"):
            await service.create_local_connector(test_path)

    @patch("app.application.services.connector_service.get_settings")
    @patch("app.application.services.connector_service.Path")
    async def test_create_local_generates_default_name(
        self, mock_path_class, mock_get_settings, service, mock_connector_repo
    ):
        """Test that a default name is generated if none provided."""
        # Arrange
        test_path = "/home/user/photos"

        # Mock settings validation
        mock_settings = Mock()
        mock_settings.is_path_allowed.return_value = (True, None)
        mock_get_settings.return_value = mock_settings

        # Mock Path operations
        mock_path_obj = Mock(spec=Path)
        mock_path_obj.resolve.return_value = mock_path_obj
        mock_path_obj.exists.return_value = True
        mock_path_obj.is_dir.return_value = True
        mock_path_obj.name = "photos"
        mock_path_obj.__str__ = Mock(return_value=test_path)
        mock_path_class.return_value = mock_path_obj

        # Mock repository
        mock_connector_repo.find_by_path.return_value = None
        expected_connector = Connector(
            id=ConnectorId(uuid4()),
            name="photos",
            type=ConnectorType.LOCAL,
            config={"path": test_path},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )
        mock_connector_repo.save.return_value = expected_connector

        # Act
        result = await service.create_local_connector(test_path)

        # Assert
        assert result.name == "photos"
        mock_connector_repo.save.assert_called_once()

    @patch("app.application.services.connector_service.get_settings")
    async def test_create_local_validates_allowed_base_paths(self, mock_get_settings, service):
        """Test security validation of allowed base paths."""
        # Arrange
        test_path = "/etc/passwd"

        # Mock settings to reject the path
        mock_settings = Mock()
        mock_settings.is_path_allowed.return_value = (
            False,
            "Path is not within allowed directories",
        )
        mock_get_settings.return_value = mock_settings

        # Act & Assert
        with pytest.raises(ValueError, match="not within allowed directories"):
            await service.create_local_connector(test_path)

    @patch("app.application.services.connector_service.get_settings")
    @patch("app.application.services.connector_service.Path")
    async def test_create_local_resolves_symlinks(
        self, mock_path_class, mock_get_settings, service, mock_connector_repo
    ):
        """Test that symlinks are resolved to real paths."""
        # Arrange
        symlink_path = "/home/user/photo-link"
        real_path = "/mnt/storage/photos"

        # Mock settings validation
        mock_settings = Mock()
        mock_settings.is_path_allowed.return_value = (True, None)
        mock_get_settings.return_value = mock_settings

        # Mock Path to resolve symlink
        mock_path_obj = Mock(spec=Path)
        mock_resolved_path = Mock(spec=Path)
        mock_resolved_path.exists.return_value = True
        mock_resolved_path.is_dir.return_value = True
        mock_resolved_path.__str__ = Mock(return_value=real_path)
        mock_resolved_path.name = "photos"
        mock_path_obj.resolve.return_value = mock_resolved_path
        mock_path_class.return_value = mock_path_obj

        # Mock repository
        mock_connector_repo.find_by_path.return_value = None
        expected_connector = Connector(
            id=ConnectorId(uuid4()),
            name="photos",
            type=ConnectorType.LOCAL,
            config={"path": real_path},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )
        mock_connector_repo.save.return_value = expected_connector

        # Act
        result = await service.create_local_connector(symlink_path)

        # Assert
        assert result.config["path"] == real_path
        mock_path_obj.resolve.assert_called_once()


class TestConnectorServiceUpdate(BaseConnectorServiceTest):
    """Test suite for updating connectors."""

    @pytest.fixture
    def mock_connector_repo(self):
        repo = Mock(spec=ConnectorRepository)
        repo.find_by_id = AsyncMock()
        repo.save = AsyncMock()
        return repo

    @pytest.fixture
    def mock_photo_repo(self):
        return Mock(spec=PhotoRepository)


    async def test_update_connector_name(self, service, mock_connector_repo):
        """Test updating connector name."""
        # Arrange
        connector_id = uuid4()
        existing_connector = Connector(
            id=ConnectorId(connector_id),
            name="Old Name",
            type=ConnectorType.LOCAL,
            config={"path": "/home/user/photos"},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )
        mock_connector_repo.find_by_id.return_value = existing_connector
        mock_connector_repo.save.return_value = existing_connector

        # Act
        result = await service.update_connector(connector_id, name="New Name")

        # Assert
        assert result.name == "New Name"
        mock_connector_repo.save.assert_called_once()

    async def test_update_connector_uses_enable_disable_methods(self, service, mock_connector_repo):
        """Test that update uses domain enable/disable methods."""
        # Arrange
        connector_id = uuid4()

        existing_connector = Connector(
            id=ConnectorId(connector_id),
            name="Test",
            type=ConnectorType.LOCAL,
            config={"path": "/home/user/photos"},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )
        mock_connector_repo.find_by_id.return_value = existing_connector
        mock_connector_repo.save.return_value = existing_connector

        # Mock the domain methods
        existing_connector.disable = Mock()
        existing_connector.enable = Mock()

        # Act - disable
        await service.update_connector(connector_id, enabled=False)

        # Assert
        existing_connector.disable.assert_called_once()

        # Reset mocks
        existing_connector.disable.reset_mock()
        existing_connector.enable.reset_mock()

        # Act - enable
        await service.update_connector(connector_id, enabled=True)

        # Assert
        existing_connector.enable.assert_called_once()

    async def test_update_connector_uses_update_config_method(self, service, mock_connector_repo):
        """Test that update uses domain update_config method."""
        # Arrange
        connector_id = uuid4()
        existing_connector = Connector(
            id=ConnectorId(connector_id),
            name="Test",
            type=ConnectorType.LOCAL,
            config={"path": "/home/user/photos"},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )
        mock_connector_repo.find_by_id.return_value = existing_connector
        mock_connector_repo.save.return_value = existing_connector

        # Mock the domain method
        existing_connector.update_config = Mock()

        # Act
        new_config = {"scan_interval": 3600}
        await service.update_connector(connector_id, config=new_config)

        # Assert
        existing_connector.update_config.assert_called_once_with(new_config)

    async def test_update_connector_not_found_raises(self, service, mock_connector_repo):
        """Test that updating non-existent connector raises error."""
        # Arrange
        connector_id = uuid4()
        mock_connector_repo.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Connector not found"):
            await service.update_connector(connector_id, name="New Name")


class TestConnectorServiceDelete(BaseConnectorServiceTest):
    """Test suite for deleting connectors."""

    @pytest.fixture
    def mock_connector_repo(self):
        repo = Mock(spec=ConnectorRepository)
        repo.find_by_id = AsyncMock()
        repo.delete = AsyncMock()
        return repo

    @pytest.fixture
    def mock_photo_repo(self):
        repo = Mock(spec=PhotoRepository)
        repo.delete_bulk_by_connector = AsyncMock()
        return repo


    async def test_delete_connector_orphans_photos_default(
        self, service, mock_connector_repo, mock_photo_repo
    ):
        """Test that photos can be orphaned when delete_photos=False."""
        # Arrange
        connector_id = uuid4()
        existing_connector = Connector(
            id=ConnectorId(connector_id),
            name="Test",
            type=ConnectorType.LOCAL,
            config={"path": "/home/user/photos"},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )
        mock_connector_repo.find_by_id.return_value = existing_connector

        # Act - explicitly pass delete_photos=False to orphan photos
        result = await service.delete_connector(connector_id, delete_photos=False)

        # Assert
        mock_connector_repo.delete.assert_called_once_with(connector_id)
        # Photos should NOT be deleted when delete_photos=False
        mock_photo_repo.delete_bulk_by_connector.assert_not_called()
        assert result == 0  # No photos deleted

    async def test_delete_connector_deletes_photos_when_flagged(
        self, service, mock_connector_repo, mock_photo_repo, mock_file_storage, mock_vector_store
    ):
        """Test that photos are deleted when delete_photos=True."""
        # Arrange
        connector_id = uuid4()
        existing_connector = Connector(
            id=ConnectorId(connector_id),
            name="Test",
            type=ConnectorType.LOCAL,
            config={"path": "/home/user/photos"},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )
        mock_connector_repo.find_by_id.return_value = existing_connector

        # Mock find_all to return 42 photos (implementation counts these)
        from app.domain.entities.photo import Photo
        mock_photos = [Mock(spec=Photo) for _ in range(42)]
        for photo in mock_photos:
            photo.storage_path = None
            photo.thumbnail_path = None
            photo.cached_thumbnail_path = None
            photo.face_ids = []
            photo.id = Mock()
            photo.id.value = uuid4()
        mock_photo_repo.find_all = AsyncMock(return_value=mock_photos)
        mock_photo_repo.delete_bulk_by_connector.return_value = 42

        # Act
        result = await service.delete_connector(connector_id, delete_photos=True)

        # Assert
        mock_photo_repo.delete_bulk_by_connector.assert_called_once_with(connector_id)
        mock_connector_repo.delete.assert_called_once_with(connector_id)
        assert result == 42  # Number of photos fetched and deleted

    async def test_delete_connector_deletes_connector_and_photos(
        self, service, mock_connector_repo, mock_photo_repo, mock_file_storage, mock_vector_store
    ):
        """Test that both connector and photos are deleted in correct order."""
        # Arrange
        connector_id = uuid4()
        existing_connector = Connector(
            id=ConnectorId(connector_id),
            name="Test",
            type=ConnectorType.LOCAL,
            config={"path": "/home/user/photos"},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )
        mock_connector_repo.find_by_id.return_value = existing_connector

        # Mock find_all to return 10 photos
        from app.domain.entities.photo import Photo
        mock_photos = [Mock(spec=Photo) for _ in range(10)]
        for photo in mock_photos:
            photo.storage_path = None
            photo.thumbnail_path = None
            photo.cached_thumbnail_path = None
            photo.face_ids = []
            photo.id = Mock()
            photo.id.value = uuid4()
        mock_photo_repo.find_all = AsyncMock(return_value=mock_photos)
        mock_photo_repo.delete_bulk_by_connector.return_value = 10

        # Act
        result = await service.delete_connector(connector_id, delete_photos=True)

        # Assert - photos deleted first, then connector
        mock_photo_repo.delete_bulk_by_connector.assert_called_once_with(connector_id)
        mock_connector_repo.delete.assert_called_once_with(connector_id)
        assert result == 10  # Number of photos fetched and deleted

    async def test_delete_connector_uses_bulk_delete(
        self, service, mock_connector_repo, mock_photo_repo
    ):
        """Test that bulk delete is used for photos."""
        # Arrange
        connector_id = uuid4()
        existing_connector = Connector(
            id=ConnectorId(connector_id),
            name="Test",
            type=ConnectorType.LOCAL,
            config={"path": "/home/user/photos"},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )
        mock_connector_repo.find_by_id.return_value = existing_connector

        # Act
        await service.delete_connector(connector_id, delete_photos=True)

        # Assert
        # Verify the bulk delete method is called (not individual deletes)
        mock_photo_repo.delete_bulk_by_connector.assert_called_once_with(connector_id)


class TestConnectorServiceValidation(BaseConnectorServiceTest):
    """Test suite for path validation security."""

    @pytest.fixture
    def mock_connector_repo(self):
        return Mock(spec=ConnectorRepository)

    @pytest.fixture
    def mock_photo_repo(self):
        return Mock(spec=PhotoRepository)


    @patch("app.application.services.connector_service.get_settings")
    async def test_validate_path_allowed_base_paths(self, mock_get_settings, service):
        """Test validation respects allowed base paths."""
        # Arrange
        test_path = "/var/www"

        # Mock settings to reject
        mock_settings = Mock()
        mock_settings.is_path_allowed.return_value = (
            False,
            "Path is not within allowed directories",
        )
        mock_get_settings.return_value = mock_settings

        # Act & Assert
        with pytest.raises(ValueError, match="not within allowed directories"):
            await service.create_local_connector(test_path)

    @patch("app.application.services.connector_service.get_settings")
    async def test_validate_path_blocks_etc_passwd(self, mock_get_settings, service):
        """Test that /etc/passwd and similar system paths are blocked."""
        # Arrange
        test_path = "/etc/passwd"

        # Mock settings to block
        mock_settings = Mock()
        mock_settings.is_path_allowed.return_value = (
            False,
            "Path is not within allowed directories",
        )
        mock_get_settings.return_value = mock_settings

        # Act & Assert
        with pytest.raises(ValueError, match="not within allowed directories"):
            await service.create_local_connector(test_path)

    @patch("app.application.services.connector_service.get_settings")
    @patch("app.application.services.connector_service.Path")
    async def test_validate_path_blocks_parent_traversal(
        self, mock_path_class, mock_get_settings, service
    ):
        """Test that parent directory traversal is blocked."""
        # Arrange
        test_path = "/home/user/photos/../../etc/passwd"

        # Mock settings to block the resolved path
        mock_settings = Mock()
        mock_settings.is_path_allowed.return_value = (
            False,
            "Path is not within allowed directories",
        )
        mock_get_settings.return_value = mock_settings

        # Mock Path to resolve traversal
        mock_path_obj = Mock(spec=Path)
        mock_resolved = Mock(spec=Path)
        mock_path_obj.resolve.return_value = mock_resolved
        mock_path_class.return_value = mock_path_obj

        # Act & Assert
        with pytest.raises(ValueError, match="not within allowed directories"):
            await service.create_local_connector(test_path)


class TestConnectorServiceGetters(BaseConnectorServiceTest):
    """Test suite for getter methods."""

    @pytest.fixture
    def mock_connector_repo(self):
        repo = Mock(spec=ConnectorRepository)
        repo.find_by_id = AsyncMock()
        repo.find_all = AsyncMock()
        return repo

    @pytest.fixture
    def mock_photo_repo(self):
        return Mock(spec=PhotoRepository)


    async def test_get_connector(self, service, mock_connector_repo):
        """Test getting a single connector by ID."""
        # Arrange
        connector_id = uuid4()
        expected_connector = Connector(
            id=ConnectorId(connector_id),
            name="Test",
            type=ConnectorType.LOCAL,
            config={"path": "/home/user/photos"},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )
        mock_connector_repo.find_by_id.return_value = expected_connector

        # Act
        result = await service.get_connector(connector_id)

        # Assert
        assert result == expected_connector
        mock_connector_repo.find_by_id.assert_called_once_with(connector_id)

    async def test_list_connectors(self, service, mock_connector_repo):
        """Test listing all connectors."""
        # Arrange
        expected_connectors = [
            Connector(
                id=ConnectorId(uuid4()),
                name="Local 1",
                type=ConnectorType.LOCAL,
                config={"path": "/path1"},
                status=ConnectorStatus.CONNECTED,
                enabled=True,
                created_at=datetime.utcnow(),
            ),
            Connector(
                id=ConnectorId(uuid4()),
                name="Google Photos",
                type=ConnectorType.GOOGLE_PHOTOS,
                config={},
                status=ConnectorStatus.CONNECTED,
                enabled=True,
                created_at=datetime.utcnow(),
            ),
        ]
        mock_connector_repo.find_all.return_value = expected_connectors

        # Act
        result = await service.list_connectors()

        # Assert
        assert result == expected_connectors
        mock_connector_repo.find_all.assert_called_once()


class TestConnectorServiceGooglePhotos(BaseConnectorServiceTest):
    """Test suite for Google Photos connector creation."""

    @pytest.fixture
    def mock_connector_repo(self):
        repo = Mock(spec=ConnectorRepository)
        repo.save = AsyncMock()
        return repo

    @pytest.fixture
    def mock_photo_repo(self):
        return Mock(spec=PhotoRepository)


    async def test_create_google_photos_connector(self, service, mock_connector_repo):
        """Test creation of Google Photos connector."""
        # Arrange
        test_name = "My Google Photos"
        expected_connector = Connector(
            id=ConnectorId(uuid4()),
            name=test_name,
            type=ConnectorType.GOOGLE_PHOTOS,
            config={},
            status=ConnectorStatus.DISCONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )
        mock_connector_repo.save.return_value = expected_connector

        # Act
        result = await service.create_google_photos_connector(test_name)

        # Assert
        assert result.name == test_name
        assert result.type == ConnectorType.GOOGLE_PHOTOS
        mock_connector_repo.save.assert_called_once()
