"""Unit tests for ConnectorRepository.

Following TDD approach - these tests define the expected behavior
before implementation.
"""

from datetime import datetime
from uuid import uuid4

import pytest

from app.domain.entities.connector import Connector, ConnectorStatus, ConnectorType


class TestConnectorRepositoryFindAll:
    """Tests for finding all connectors."""

    @pytest.mark.asyncio
    async def test_find_all_returns_empty_list_when_no_connectors(self, connector_repo):
        """Should return empty list when no connectors exist."""
        # When
        result = await connector_repo.find_all()

        # Then
        assert result == []
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_find_all_returns_all_connectors(self, connector_repo):
        """Should return all connectors from database."""
        # Given: 3 different connectors
        google_connector = Connector.create_google_photos(name="Google Photos")
        local_connector = Connector.create_local(path="/photos", name="My Photos")
        upload_connector = Connector.create_upload(upload_path="/uploads")

        await connector_repo.save(google_connector)
        await connector_repo.save(local_connector)
        await connector_repo.save(upload_connector)

        # When
        result = await connector_repo.find_all()

        # Then
        assert len(result) == 3
        types = {c.type for c in result}
        assert types == {
            ConnectorType.GOOGLE_PHOTOS,
            ConnectorType.LOCAL,
            ConnectorType.UPLOAD,
        }


class TestConnectorRepositoryFindById:
    """Tests for finding connector by ID."""

    @pytest.mark.asyncio
    async def test_find_by_id_returns_none_when_not_found(self, connector_repo):
        """Should return None when connector doesn't exist."""
        # Given: non-existent ID
        non_existent_id = uuid4()

        # When
        result = await connector_repo.find_by_id(non_existent_id)

        # Then
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_id_returns_correct_connector(self, connector_repo):
        """Should return the connector with matching ID."""
        # Given: saved connector
        connector = Connector.create_upload(upload_path="/uploads")
        saved = await connector_repo.save(connector)

        # When
        result = await connector_repo.find_by_id(saved.id.value)

        # Then
        assert result is not None
        assert result.id.value == saved.id.value
        assert result.name == "Uploads"
        assert result.type == ConnectorType.UPLOAD

    @pytest.mark.asyncio
    async def test_find_by_id_returns_full_connector_data(self, connector_repo):
        """Should return connector with all fields populated."""
        # Given: connector with specific config
        connector = Connector.create_local(
            path="/my/photos",
            name="Test Folder",
            recursive=True,
            watch=False,
            auto_album=True,
        )
        saved = await connector_repo.save(connector)

        # When
        result = await connector_repo.find_by_id(saved.id.value)

        # Then
        assert result.config["path"] == "/my/photos"
        assert result.config["recursive"] is True
        assert result.config["watch"] is False
        assert result.config["auto_album"] is True
        assert result.status == ConnectorStatus.CONNECTED


class TestConnectorRepositoryFindByType:
    """Tests for finding connectors by type."""

    @pytest.mark.asyncio
    async def test_find_by_type_returns_none_when_not_found(self, connector_repo):
        """Should return None when no connector of that type exists."""
        # When
        result = await connector_repo.find_by_type(ConnectorType.GOOGLE_PHOTOS.value)

        # Then
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_type_returns_first_matching_connector(self, connector_repo):
        """Should return first connector of specified type."""
        # Given: 2 local connectors
        local1 = Connector.create_local(path="/photos1", name="Photos 1")
        local2 = Connector.create_local(path="/photos2", name="Photos 2")

        await connector_repo.save(local1)
        await connector_repo.save(local2)

        # When
        result = await connector_repo.find_by_type(ConnectorType.LOCAL.value)

        # Then
        assert result is not None
        assert result.type == ConnectorType.LOCAL

    @pytest.mark.asyncio
    async def test_find_by_type_filters_correctly(self, connector_repo):
        """Should only return connector of specified type."""
        # Given: different connector types
        google = Connector.create_google_photos(name="Google")
        local = Connector.create_local(path="/photos", name="Local")
        upload = Connector.create_upload(upload_path="/uploads")

        await connector_repo.save(google)
        await connector_repo.save(local)
        await connector_repo.save(upload)

        # When
        result = await connector_repo.find_by_type(ConnectorType.UPLOAD.value)

        # Then
        assert result.type == ConnectorType.UPLOAD
        assert result.name == "Uploads"


class TestConnectorRepositoryFindEnabled:
    """Tests for finding enabled connectors only."""

    @pytest.mark.asyncio
    async def test_find_enabled_returns_empty_when_all_disabled(self, connector_repo):
        """Should return empty list when all connectors are disabled."""
        # Given: 2 disabled connectors
        connector1 = Connector.create_local(path="/photos", name="Local")
        connector1.enabled = False
        connector2 = Connector.create_upload(upload_path="/uploads")
        connector2.enabled = False

        await connector_repo.save(connector1)
        await connector_repo.save(connector2)

        # When
        result = await connector_repo.find_enabled()

        # Then
        assert result == []

    @pytest.mark.asyncio
    async def test_find_enabled_filters_out_disabled_connectors(self, connector_repo):
        """Should only return enabled connectors."""
        # Given: mix of enabled and disabled
        enabled1 = Connector.create_local(path="/photos1", name="Enabled 1")
        enabled1.enabled = True

        disabled = Connector.create_local(path="/photos2", name="Disabled")
        disabled.enabled = False

        enabled2 = Connector.create_upload(upload_path="/uploads")
        enabled2.enabled = True

        await connector_repo.save(enabled1)
        await connector_repo.save(disabled)
        await connector_repo.save(enabled2)

        # When
        result = await connector_repo.find_enabled()

        # Then
        assert len(result) == 2
        assert all(c.enabled for c in result)
        assert disabled.id.value not in [c.id.value for c in result]


class TestConnectorRepositorySave:
    """Tests for saving connectors."""

    @pytest.mark.asyncio
    async def test_save_creates_new_connector(self, connector_repo):
        """Should create new connector in database."""
        # Given: new connector
        connector = Connector.create_upload(upload_path="/uploads")

        # When
        result = await connector_repo.save(connector)

        # Then
        assert result.id.value is not None
        assert result.name == "Uploads"

        # Verify it's in database
        found = await connector_repo.find_by_id(result.id.value)
        assert found is not None

    @pytest.mark.asyncio
    async def test_save_updates_existing_connector(self, connector_repo):
        """Should update existing connector when saving again."""
        # Given: saved connector
        connector = Connector.create_local(path="/old", name="Old Name")
        saved = await connector_repo.save(connector)

        # When: modify and save again
        saved.name = "New Name"
        saved.config = {"path": "/new"}
        updated = await connector_repo.save(saved)

        # Then
        assert updated.id.value == saved.id.value
        assert updated.name == "New Name"
        assert updated.config["path"] == "/new"

        # Verify in database
        found = await connector_repo.find_by_id(saved.id.value)
        assert found.name == "New Name"

    @pytest.mark.asyncio
    async def test_save_preserves_all_fields(self, connector_repo):
        """Should preserve all connector fields."""
        # Given: connector with specific values
        connector = Connector.create_local(
            path="/photos",
            name="Test",
            recursive=True,
            watch=True,
            auto_album=False,
        )
        connector.enabled = True
        connector.status = ConnectorStatus.CONNECTED
        connector.last_sync = datetime.utcnow()
        connector.last_sync_stats = {"indexed": 10, "skipped": 2}
        connector.error_message = None

        # When
        saved = await connector_repo.save(connector)

        # Then: all fields preserved
        found = await connector_repo.find_by_id(saved.id.value)
        assert found.enabled is True
        assert found.status == ConnectorStatus.CONNECTED
        assert found.last_sync is not None
        assert found.last_sync_stats["indexed"] == 10
        assert found.error_message is None


class TestConnectorRepositoryDelete:
    """Tests for deleting connectors."""

    @pytest.mark.asyncio
    async def test_delete_removes_connector(self, connector_repo):
        """Should remove connector from database."""
        # Given: saved connector
        connector = Connector.create_upload(upload_path="/uploads")
        saved = await connector_repo.save(connector)

        # When
        result = await connector_repo.delete(saved.id.value)

        # Then
        assert result is True

        # Verify not in database
        found = await connector_repo.find_by_id(saved.id.value)
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(self, connector_repo):
        """Should return False when connector doesn't exist."""
        # Given: non-existent ID
        non_existent_id = uuid4()

        # When
        result = await connector_repo.delete(non_existent_id)

        # Then
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_sets_null_on_photos(self, connector_repo, photo_repo):
        """Should set connector_id to NULL on associated photos."""
        # Given: connector with photos
        connector = Connector.create_upload(upload_path="/uploads")
        saved_connector = await connector_repo.save(connector)

        # Create photos associated with connector
        from app.domain.entities.photo import Photo

        photo1 = Photo.create(
            filename="test1.jpg",
            storage_path="/uploads/test1.jpg",
            connector_type=ConnectorType.UPLOAD.value,
            connector_id=saved_connector.id.value,
        )
        photo2 = Photo.create(
            filename="test2.jpg",
            storage_path="/uploads/test2.jpg",
            connector_type=ConnectorType.UPLOAD.value,
            connector_id=saved_connector.id.value,
        )

        await photo_repo.save(photo1)
        await photo_repo.save(photo2)

        # When: delete connector
        await connector_repo.delete(saved_connector.id.value)

        # Then: photos still exist but connector_id is NULL
        found_photo1 = await photo_repo.find_by_id(photo1.id.value)
        found_photo2 = await photo_repo.find_by_id(photo2.id.value)

        assert found_photo1 is not None
        assert found_photo2 is not None
        assert found_photo1.connector_id is None
        assert found_photo2.connector_id is None


# Fixtures


@pytest.fixture
async def connector_repo(db_session):
    """Provide ConnectorRepository instance with test database session."""
    from app.adapters.outbound.persistence.postgres.repositories.connector_repository import (
        PostgresConnectorRepository,
    )

    return PostgresConnectorRepository(db_session)


@pytest.fixture
async def photo_repo(db_session):
    """Provide PhotoRepository instance with test database session."""
    from app.adapters.outbound.persistence.postgres.repositories.photo_repository import (
        PostgresPhotoRepository,
    )

    return PostgresPhotoRepository(db_session)
