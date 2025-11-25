"""Extended tests for ConnectorService - new methods for routes refactoring."""
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.application.ports.outbound import ConnectorRepository, PhotoRepository
from app.application.services.connector_service import ConnectorService
from app.domain.entities.connector import Connector, ConnectorStatus, ConnectorType
from app.domain.entities.photo import Photo
from app.domain.value_objects import ConnectorId, PhotoId


class TestConnectorServiceListConnectorsWithFilters:
    """Test suite for list_connectors with filtering."""

    @pytest.fixture
    def mock_connector_repo(self):
        repo = Mock(spec=ConnectorRepository)
        repo.find_all = AsyncMock()
        return repo

    @pytest.fixture
    def mock_photo_repo(self):
        return Mock(spec=PhotoRepository)

    @pytest.fixture
    def service(self, mock_connector_repo, mock_photo_repo):
        return ConnectorService(mock_connector_repo, mock_photo_repo)

    @pytest.fixture
    def sample_connectors(self):
        """Sample connectors with different types and statuses."""
        return [
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
                name="Local 2",
                type=ConnectorType.LOCAL,
                config={"path": "/path2"},
                status=ConnectorStatus.SYNCING,
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
            Connector(
                id=ConnectorId(uuid4()),
                name="Google Photos 2",
                type=ConnectorType.GOOGLE_PHOTOS,
                config={},
                status=ConnectorStatus.DISCONNECTED,
                enabled=False,
                created_at=datetime.utcnow(),
            ),
        ]

    async def test_list_connectors_no_filters(self, service, mock_connector_repo, sample_connectors):
        """Test listing all connectors without filters."""
        # Arrange
        mock_connector_repo.find_all.return_value = sample_connectors

        # Act
        result = await service.list_connectors()

        # Assert
        assert len(result) == 4
        assert result == sample_connectors
        mock_connector_repo.find_all.assert_called_once()

    async def test_list_connectors_filter_by_type_local(
        self, service, mock_connector_repo, sample_connectors
    ):
        """Test filtering connectors by LOCAL type."""
        # Arrange
        mock_connector_repo.find_all.return_value = sample_connectors

        # Act
        result = await service.list_connectors(connector_type=ConnectorType.LOCAL)

        # Assert
        assert len(result) == 2
        assert all(c.type == ConnectorType.LOCAL for c in result)
        assert result[0].name == "Local 1"
        assert result[1].name == "Local 2"

    async def test_list_connectors_filter_by_type_google_photos(
        self, service, mock_connector_repo, sample_connectors
    ):
        """Test filtering connectors by GOOGLE_PHOTOS type."""
        # Arrange
        mock_connector_repo.find_all.return_value = sample_connectors

        # Act
        result = await service.list_connectors(connector_type=ConnectorType.GOOGLE_PHOTOS)

        # Assert
        assert len(result) == 2
        assert all(c.type == ConnectorType.GOOGLE_PHOTOS for c in result)

    async def test_list_connectors_filter_by_status_connected(
        self, service, mock_connector_repo, sample_connectors
    ):
        """Test filtering connectors by CONNECTED status."""
        # Arrange
        mock_connector_repo.find_all.return_value = sample_connectors

        # Act
        result = await service.list_connectors(status=ConnectorStatus.CONNECTED)

        # Assert
        assert len(result) == 2
        assert all(c.status == ConnectorStatus.CONNECTED for c in result)

    async def test_list_connectors_filter_by_type_and_status(
        self, service, mock_connector_repo, sample_connectors
    ):
        """Test filtering connectors by both type and status."""
        # Arrange
        mock_connector_repo.find_all.return_value = sample_connectors

        # Act
        result = await service.list_connectors(
            connector_type=ConnectorType.GOOGLE_PHOTOS, status=ConnectorStatus.DISCONNECTED
        )

        # Assert
        assert len(result) == 1
        assert result[0].type == ConnectorType.GOOGLE_PHOTOS
        assert result[0].status == ConnectorStatus.DISCONNECTED
        assert result[0].name == "Google Photos 2"

    async def test_list_connectors_filter_returns_empty_when_no_match(
        self, service, mock_connector_repo, sample_connectors
    ):
        """Test filtering returns empty list when no connectors match."""
        # Arrange
        mock_connector_repo.find_all.return_value = sample_connectors

        # Act
        result = await service.list_connectors(
            connector_type=ConnectorType.LOCAL, status=ConnectorStatus.ERROR
        )

        # Assert
        assert len(result) == 0


class TestConnectorServiceGetConnectorPhotos:
    """Test suite for get_connector_photos with pagination."""

    @pytest.fixture
    def mock_connector_repo(self):
        repo = Mock(spec=ConnectorRepository)
        repo.find_by_id = AsyncMock()
        return repo

    @pytest.fixture
    def mock_photo_repo(self):
        repo = Mock(spec=PhotoRepository)
        repo.find_by_connector = AsyncMock()
        repo.count_by_connector = AsyncMock()
        return repo

    @pytest.fixture
    def service(self, mock_connector_repo, mock_photo_repo):
        return ConnectorService(mock_connector_repo, mock_photo_repo)

    @pytest.fixture
    def sample_connector(self):
        return Connector(
            id=ConnectorId(uuid4()),
            name="Test Connector",
            type=ConnectorType.LOCAL,
            config={"path": "/test"},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )

    def create_sample_photo(self, connector_id: str, index: int) -> Photo:
        """Helper to create sample photo."""
        return Photo(
            id=PhotoId(uuid4()),
            filename=f"photo_{index}.jpg",
            connector_id=connector_id,
            storage_path=f"/path/photo_{index}.jpg",
            connector_type="local",
            created_at=datetime.utcnow(),
        )

    async def test_get_connector_photos_success(
        self, service, mock_connector_repo, mock_photo_repo, sample_connector
    ):
        """Test successfully getting paginated photos."""
        # Arrange
        connector_id = sample_connector.id.value
        mock_connector_repo.find_by_id.return_value = sample_connector

        photos = [self.create_sample_photo(connector_id, i) for i in range(20)]
        mock_photo_repo.find_by_connector.return_value = photos
        mock_photo_repo.count_by_connector.return_value = 100

        # Act
        result_photos, total = await service.get_connector_photos(connector_id, page=1, per_page=20)

        # Assert
        assert len(result_photos) == 20
        assert total == 100
        mock_connector_repo.find_by_id.assert_called_once_with(connector_id)
        mock_photo_repo.find_by_connector.assert_called_once_with(
            connector_id, limit=20, offset=0
        )
        mock_photo_repo.count_by_connector.assert_called_once_with(connector_id)

    async def test_get_connector_photos_second_page(
        self, service, mock_connector_repo, mock_photo_repo, sample_connector
    ):
        """Test pagination calculates correct offset."""
        # Arrange
        connector_id = sample_connector.id.value
        mock_connector_repo.find_by_id.return_value = sample_connector

        photos = [self.create_sample_photo(connector_id, i) for i in range(20, 40)]
        mock_photo_repo.find_by_connector.return_value = photos
        mock_photo_repo.count_by_connector.return_value = 100

        # Act
        result_photos, total = await service.get_connector_photos(connector_id, page=2, per_page=20)

        # Assert
        assert len(result_photos) == 20
        assert total == 100
        # Offset should be (2-1) * 20 = 20
        mock_photo_repo.find_by_connector.assert_called_once_with(
            connector_id, limit=20, offset=20
        )

    async def test_get_connector_photos_custom_per_page(
        self, service, mock_connector_repo, mock_photo_repo, sample_connector
    ):
        """Test custom per_page parameter."""
        # Arrange
        connector_id = sample_connector.id.value
        mock_connector_repo.find_by_id.return_value = sample_connector

        photos = [self.create_sample_photo(connector_id, i) for i in range(50)]
        mock_photo_repo.find_by_connector.return_value = photos
        mock_photo_repo.count_by_connector.return_value = 200

        # Act
        result_photos, total = await service.get_connector_photos(
            connector_id, page=1, per_page=50
        )

        # Assert
        assert len(result_photos) == 50
        assert total == 200
        mock_photo_repo.find_by_connector.assert_called_once_with(
            connector_id, limit=50, offset=0
        )

    async def test_get_connector_photos_connector_not_found(
        self, service, mock_connector_repo, mock_photo_repo
    ):
        """Test error when connector doesn't exist."""
        # Arrange
        connector_id = uuid4()
        mock_connector_repo.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Connector not found"):
            await service.get_connector_photos(connector_id)

        # Verify photo repo was never called
        mock_photo_repo.find_by_connector.assert_not_called()
        mock_photo_repo.count_by_connector.assert_not_called()

    async def test_get_connector_photos_empty_result(
        self, service, mock_connector_repo, mock_photo_repo, sample_connector
    ):
        """Test getting photos when connector has no photos."""
        # Arrange
        connector_id = sample_connector.id.value
        mock_connector_repo.find_by_id.return_value = sample_connector

        mock_photo_repo.find_by_connector.return_value = []
        mock_photo_repo.count_by_connector.return_value = 0

        # Act
        result_photos, total = await service.get_connector_photos(connector_id)

        # Assert
        assert len(result_photos) == 0
        assert total == 0


class TestConnectorServiceDisconnectGooglePhotos:
    """Test suite for disconnect_google_photos_connectors."""

    @pytest.fixture
    def mock_connector_repo(self):
        repo = Mock(spec=ConnectorRepository)
        repo.find_all = AsyncMock()
        repo.save = AsyncMock()
        return repo

    @pytest.fixture
    def mock_photo_repo(self):
        return Mock(spec=PhotoRepository)

    @pytest.fixture
    def service(self, mock_connector_repo, mock_photo_repo):
        return ConnectorService(mock_connector_repo, mock_photo_repo)

    async def test_disconnect_google_photos_single_connector(
        self, service, mock_connector_repo
    ):
        """Test disconnecting a single Google Photos connector."""
        # Arrange
        gp_connector = Connector(
            id=ConnectorId(uuid4()),
            name="Google Photos",
            type=ConnectorType.GOOGLE_PHOTOS,
            config={},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )

        mock_connector_repo.find_all.return_value = [gp_connector]
        mock_connector_repo.save.return_value = gp_connector

        # Act
        count = await service.disconnect_google_photos_connectors()

        # Assert
        assert count == 1
        assert gp_connector.status == ConnectorStatus.DISCONNECTED
        mock_connector_repo.save.assert_called_once()

    async def test_disconnect_google_photos_multiple_connectors(
        self, service, mock_connector_repo
    ):
        """Test disconnecting multiple Google Photos connectors."""
        # Arrange
        gp_connectors = [
            Connector(
                id=ConnectorId(uuid4()),
                name=f"Google Photos {i}",
                type=ConnectorType.GOOGLE_PHOTOS,
                config={},
                status=ConnectorStatus.CONNECTED,
                enabled=True,
                created_at=datetime.utcnow(),
            )
            for i in range(3)
        ]

        local_connector = Connector(
            id=ConnectorId(uuid4()),
            name="Local",
            type=ConnectorType.LOCAL,
            config={"path": "/test"},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )

        mock_connector_repo.find_all.return_value = gp_connectors + [local_connector]

        # Act
        count = await service.disconnect_google_photos_connectors()

        # Assert
        assert count == 3
        # Verify all Google Photos connectors are disconnected
        for connector in gp_connectors:
            assert connector.status == ConnectorStatus.DISCONNECTED
        # Verify local connector is unchanged
        assert local_connector.status == ConnectorStatus.CONNECTED
        # Verify save was called for each Google Photos connector
        assert mock_connector_repo.save.call_count == 3

    async def test_disconnect_google_photos_no_connectors(self, service, mock_connector_repo):
        """Test disconnecting when no Google Photos connectors exist."""
        # Arrange
        mock_connector_repo.find_all.return_value = []

        # Act
        count = await service.disconnect_google_photos_connectors()

        # Assert
        assert count == 0
        mock_connector_repo.save.assert_not_called()

    async def test_disconnect_google_photos_uses_domain_method(
        self, service, mock_connector_repo
    ):
        """Test that set_disconnected domain method is used (not direct mutation)."""
        # Arrange
        gp_connector = Connector(
            id=ConnectorId(uuid4()),
            name="Google Photos",
            type=ConnectorType.GOOGLE_PHOTOS,
            config={},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )

        # Mock the domain method to track its usage
        original_set_disconnected = gp_connector.set_disconnected
        gp_connector.set_disconnected = Mock(side_effect=original_set_disconnected)

        mock_connector_repo.find_all.return_value = [gp_connector]

        # Act
        await service.disconnect_google_photos_connectors()

        # Assert - domain method was called
        gp_connector.set_disconnected.assert_called_once()
        # And status was actually updated
        assert gp_connector.status == ConnectorStatus.DISCONNECTED


class TestConnectorServiceCreateGooglePhotosWithEmail:
    """Test suite for create_google_photos_connector with email."""

    @pytest.fixture
    def mock_connector_repo(self):
        repo = Mock(spec=ConnectorRepository)
        repo.save = AsyncMock()
        return repo

    @pytest.fixture
    def mock_photo_repo(self):
        return Mock(spec=PhotoRepository)

    @pytest.fixture
    def service(self, mock_connector_repo, mock_photo_repo):
        return ConnectorService(mock_connector_repo, mock_photo_repo)

    async def test_create_google_photos_with_email(self, service, mock_connector_repo):
        """Test creating Google Photos connector with email."""
        # Arrange
        test_name = "Google Photos (user@example.com)"
        test_email = "user@example.com"

        expected_connector = Connector(
            id=ConnectorId(uuid4()),
            name=test_name,
            type=ConnectorType.GOOGLE_PHOTOS,
            config={"email": test_email},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )
        mock_connector_repo.save.return_value = expected_connector

        # Act
        result = await service.create_google_photos_connector(name=test_name, email=test_email)

        # Assert
        assert result.name == test_name
        assert result.config["email"] == test_email
        assert result.status == ConnectorStatus.CONNECTED
        mock_connector_repo.save.assert_called_once()

    async def test_create_google_photos_without_email(self, service, mock_connector_repo):
        """Test creating Google Photos connector without email."""
        # Arrange
        test_name = "Google Photos"

        expected_connector = Connector(
            id=ConnectorId(uuid4()),
            name=test_name,
            type=ConnectorType.GOOGLE_PHOTOS,
            config={},
            status=ConnectorStatus.CONNECTED,
            enabled=True,
            created_at=datetime.utcnow(),
        )
        mock_connector_repo.save.return_value = expected_connector

        # Act
        result = await service.create_google_photos_connector(name=test_name)

        # Assert
        assert result.name == test_name
        assert "email" not in result.config
        assert result.status == ConnectorStatus.CONNECTED
        mock_connector_repo.save.assert_called_once()
