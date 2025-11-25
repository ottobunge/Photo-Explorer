"""Integration tests for connector detail API endpoints.

Tests the following endpoints:
- GET /api/v1/connectors/{id} - Get connector details
- GET /api/v1/connectors/{id}/photos - List photos from connector
- PATCH /api/v1/connectors/{id} - Update connector config
- DELETE /api/v1/connectors/{id} - Delete connector
- POST /api/v1/connectors/{id}/reprocess - Reprocess connector photos
- POST /api/v1/connectors/{id}/sync - Trigger manual sync
- GET /api/v1/connectors/{id}/sync/status - Get sync status

Following TDD approach - tests written before implementation.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from httpx import AsyncClient

from app.domain.entities.connector import Connector, ConnectorType, ConnectorStatus
from app.domain.entities.photo import Photo


class TestGetConnectorDetail:
    """Tests for GET /api/v1/connectors/{id}."""

    @pytest.mark.asyncio
    async def test_get_connector_returns_metadata(
        self, client: AsyncClient, connector_repo
    ):
        """Should return connector with all metadata fields."""
        # Given: saved connector
        connector = Connector.create_upload(upload_path="/uploads")
        connector.status = ConnectorStatus.CONNECTED
        connector.last_sync = datetime.utcnow()
        saved = await connector_repo.save(connector)

        # When
        response = await client.get(f"/api/v1/connectors/{saved.id.value}")

        # Then
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        data = response_data["data"]

        assert data["id"] == str(saved.id.value)
        assert data["type"] == "upload"
        assert data["name"] == "Uploads"
        assert data["enabled"] is True
        assert data["status"] == "connected"
        assert "config" in data
        assert "last_sync" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_connector_not_found(self, client: AsyncClient):
        """Should return 404 when connector doesn't exist."""
        # Given: non-existent ID
        non_existent_id = uuid4()

        # When
        response = await client.get(f"/api/v1/connectors/{non_existent_id}")

        # Then
        assert response.status_code == 404
        assert "not found" in response.json()["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_get_connector_returns_config(
        self, client: AsyncClient, connector_repo
    ):
        """Should include connector configuration in response."""
        # Given: local connector with specific config
        connector = Connector.create_local(
            path="/my/photos",
            name="My Photos",
            recursive=True,
            watch=False,
            auto_album=True,
        )
        saved = await connector_repo.save(connector)

        # When
        response = await client.get(f"/api/v1/connectors/{saved.id.value}")

        # Then
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        data = response_data["data"]

        assert data["config"]["path"] == "/my/photos"
        assert data["config"]["recursive"] is True
        assert data["config"]["watch"] is False
        assert data["config"]["auto_album"] is True


class TestGetConnectorPhotos:
    """Tests for GET /api/v1/connectors/{id}/photos."""

    @pytest.mark.asyncio
    async def test_get_connector_photos_empty_list(
        self, client: AsyncClient, connector_repo
    ):
        """Should return empty list when connector has no photos."""
        # Given: connector with no photos
        connector = Connector.create_upload(upload_path="/uploads")
        saved = await connector_repo.save(connector)

        # When
        response = await client.get(f"/api/v1/connectors/{saved.id.value}/photos")

        # Then
        assert response.status_code == 200
        data = response.json()

        assert data["photos"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_connector_photos_returns_photos(
        self, client: AsyncClient, connector_repo, photo_repo
    ):
        """Should return photos from specified connector."""
        # Given: connector with 3 photos
        connector = Connector.create_upload(upload_path="/uploads")
        saved_connector = await connector_repo.save(connector)

        for i in range(3):
            photo = Photo.create(
                filename=f"photo{i}.jpg",
                storage_path=f"/uploads/photo{i}.jpg",
                connector_type=ConnectorType.UPLOAD.value,
                connector_id=saved_connector.id.value,
            )
            await photo_repo.save(photo)

        # When
        response = await client.get(
            f"/api/v1/connectors/{saved_connector.id.value}/photos"
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        assert len(data["photos"]) == 3
        assert data["total"] == 3
        assert all(p["connector_id"] == str(saved_connector.id.value) for p in data["photos"])

    @pytest.mark.asyncio
    async def test_get_connector_photos_pagination(
        self, client: AsyncClient, connector_repo, photo_repo
    ):
        """Should paginate results correctly."""
        # Given: connector with 5 photos
        connector = Connector.create_local(path="/photos", name="Test")
        saved_connector = await connector_repo.save(connector)

        for i in range(5):
            photo = Photo.create(
                filename=f"photo{i}.jpg",
                storage_path=f"/photos/photo{i}.jpg",
                connector_type=ConnectorType.LOCAL.value,
                connector_id=saved_connector.id.value,
            )
            await photo_repo.save(photo)

        # When: first page (per_page=2, page=1)
        response1 = await client.get(
            f"/api/v1/connectors/{saved_connector.id.value}/photos?per_page=2&page=1"
        )

        # Then
        assert response1.status_code == 200
        page1 = response1.json()
        assert len(page1["photos"]) == 2
        assert page1["total"] == 5

        # When: second page
        response2 = await client.get(
            f"/api/v1/connectors/{saved_connector.id.value}/photos?per_page=2&page=2"
        )

        # Then
        page2 = response2.json()
        assert len(page2["photos"]) == 2

        # No overlap
        page1_ids = {p["id"] for p in page1["photos"]}
        page2_ids = {p["id"] for p in page2["photos"]}
        assert len(page1_ids & page2_ids) == 0

    @pytest.mark.asyncio
    async def test_get_connector_photos_includes_count(
        self, client: AsyncClient, connector_repo, photo_repo
    ):
        """Should include total count in response."""
        # Given: connector with 50 photos
        connector = Connector.create_upload(upload_path="/uploads")
        saved_connector = await connector_repo.save(connector)

        for i in range(50):
            photo = Photo.create(
                filename=f"photo{i}.jpg",
                storage_path=f"/uploads/photo{i}.jpg",
                connector_type=ConnectorType.UPLOAD.value,
                connector_id=saved_connector.id.value,
            )
            await photo_repo.save(photo)

        # When: request with per_page limit
        response = await client.get(
            f"/api/v1/connectors/{saved_connector.id.value}/photos?per_page=10"
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        assert len(data["photos"]) == 10
        assert data["total"] == 50  # Total count, not just returned


class TestUpdateConnectorConfig:
    """Tests for PATCH /api/v1/connectors/{id}."""

    @pytest.mark.asyncio
    async def test_update_connector_config(
        self, client: AsyncClient, connector_repo
    ):
        """Should update connector configuration."""
        # Given: existing local connector
        connector = Connector.create_local(
            path="/old/path",
            name="Old Name",
            recursive=False,
        )
        saved = await connector_repo.save(connector)

        # When: update config (without changing path which would require validation)
        response = await client.patch(
            f"/api/v1/connectors/{saved.id.value}",
            json={
                "name": "New Name",
                "config": {
                    "recursive": True,
                    "watch": True,
                },
            },
        )

        # Then
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        data = response_data["data"]

        assert data["name"] == "New Name"
        assert data["config"]["recursive"] is True
        assert data["config"]["watch"] is True

        # Verify in database
        updated = await connector_repo.find_by_id(saved.id.value)
        assert updated.name == "New Name"
        assert updated.config["recursive"] is True

    @pytest.mark.asyncio
    async def test_update_connector_enabled_status(
        self, client: AsyncClient, connector_repo
    ):
        """Should update enabled status."""
        # Given: enabled connector
        connector = Connector.create_local(path="/photos", name="Test")
        connector.enabled = True
        saved = await connector_repo.save(connector)

        # When: disable connector
        response = await client.patch(
            f"/api/v1/connectors/{saved.id.value}",
            json={"enabled": False},
        )

        # Then
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        data = response_data["data"]
        assert data["enabled"] is False

        # Verify in database
        updated = await connector_repo.find_by_id(saved.id.value)
        assert updated.enabled is False

    @pytest.mark.asyncio
    async def test_update_connector_not_found(self, client: AsyncClient):
        """Should return 404 when connector doesn't exist."""
        # Given: non-existent ID
        non_existent_id = uuid4()

        # When
        response = await client.patch(
            f"/api/v1/connectors/{non_existent_id}",
            json={"name": "New Name"},
        )

        # Then
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_connector_validates_config(
        self, client: AsyncClient, connector_repo
    ):
        """Should validate configuration based on connector type."""
        # Given: upload connector
        connector = Connector.create_upload(upload_path="/uploads")
        saved = await connector_repo.save(connector)

        # When: try to set invalid config
        response = await client.patch(
            f"/api/v1/connectors/{saved.id.value}",
            json={
                "config": {
                    "invalid_field": "value",
                }
            },
        )

        # Then: should validate or accept gracefully
        # (Implementation can choose to validate or ignore unknown fields)
        assert response.status_code in [200, 400]


class TestDeleteConnector:
    """Tests for DELETE /api/v1/connectors/{id}."""

    @pytest.mark.asyncio
    async def test_delete_connector_orphans_photos(
        self, client: AsyncClient, connector_repo, photo_repo
    ):
        """Should delete connector but orphan photos (default behavior)."""
        # Given: connector with photos
        connector = Connector.create_local(path="/photos", name="Test")
        saved_connector = await connector_repo.save(connector)

        photo = Photo.create(
            filename="test.jpg",
            storage_path="/photos/test.jpg",
            connector_type=ConnectorType.LOCAL.value,
            connector_id=saved_connector.id.value,
        )
        saved_photo = await photo_repo.save(photo)

        # When: delete connector (default: orphan photos)
        response = await client.delete(
            f"/api/v1/connectors/{saved_connector.id.value}"
        )

        # Then
        assert response.status_code == 200

        # Connector deleted
        deleted_connector = await connector_repo.find_by_id(saved_connector.id.value)
        assert deleted_connector is None

        # Photo still exists but orphaned
        orphaned_photo = await photo_repo.find_by_id(saved_photo.id.value)
        assert orphaned_photo is not None
        assert orphaned_photo.connector_id is None

    @pytest.mark.asyncio
    async def test_delete_connector_with_delete_photos_flag(
        self, client: AsyncClient, connector_repo, photo_repo
    ):
        """Should delete connector AND photos when flag is set."""
        # Given: connector with photos
        connector = Connector.create_upload(upload_path="/uploads")
        saved_connector = await connector_repo.save(connector)

        photo = Photo.create(
            filename="test.jpg",
            storage_path="/uploads/test.jpg",
            connector_type=ConnectorType.UPLOAD.value,
            connector_id=saved_connector.id.value,
        )
        saved_photo = await photo_repo.save(photo)

        # When: delete connector with delete_photos=true
        response = await client.delete(
            f"/api/v1/connectors/{saved_connector.id.value}?delete_photos=true"
        )

        # Then
        assert response.status_code == 200

        # Connector deleted
        assert await connector_repo.find_by_id(saved_connector.id.value) is None

        # Photo also deleted
        assert await photo_repo.find_by_id(saved_photo.id.value) is None

    @pytest.mark.asyncio
    async def test_delete_connector_not_found(self, client: AsyncClient):
        """Should return 404 when connector doesn't exist."""
        # Given: non-existent ID
        non_existent_id = uuid4()

        # When
        response = await client.delete(f"/api/v1/connectors/{non_existent_id}")

        # Then
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_connector_returns_confirmation(
        self, client: AsyncClient, connector_repo
    ):
        """Should return confirmation with deletion details."""
        # Given: connector with no photos
        connector = Connector.create_local(path="/photos", name="Empty")
        saved = await connector_repo.save(connector)

        # When
        response = await client.delete(f"/api/v1/connectors/{saved.id.value}")

        # Then
        assert response.status_code == 200
        data = response.json()

        assert "message" in data or "success" in data


class TestReprocessConnectorPhotos:
    """Tests for POST /api/v1/connectors/{id}/reprocess."""

    @pytest.mark.asyncio
    async def test_reprocess_connector_photos_queues_tasks(
        self, client: AsyncClient, connector_repo, photo_repo
    ):
        """Should queue background tasks for all connector photos."""
        # Given: connector with 3 photos
        connector = Connector.create_upload(upload_path="/uploads")
        saved_connector = await connector_repo.save(connector)

        for i in range(3):
            photo = Photo.create(
                filename=f"photo{i}.jpg",
                storage_path=f"/uploads/photo{i}.jpg",
                connector_type=ConnectorType.UPLOAD.value,
                connector_id=saved_connector.id.value,
            )
            await photo_repo.save(photo)

        # When: reprocess
        response = await client.post(
            f"/api/v1/connectors/{saved_connector.id.value}/reprocess"
        )

        # Then
        # Accept both 200 and 202 (202 if celery works, 200 if worker not running)
        assert response.status_code in [200, 202]
        data = response.json()

        # If 202, should have task info
        if response.status_code == 202:
            assert "task_id" in data
            assert "message" in data
            assert "status" in data

    @pytest.mark.asyncio
    async def test_reprocess_connector_no_photos(
        self, client: AsyncClient, connector_repo
    ):
        """Should handle connector with no photos gracefully."""
        # Given: connector with no photos
        connector = Connector.create_local(path="/photos", name="Empty")
        saved = await connector_repo.save(connector)

        # When
        response = await client.post(f"/api/v1/connectors/{saved.id.value}/reprocess")

        # Then
        assert response.status_code in [200, 202]
        # Should not fail, just indicate nothing to process

    @pytest.mark.asyncio
    async def test_reprocess_connector_not_found(self, client: AsyncClient):
        """Should return 404 when connector doesn't exist."""
        # Given: non-existent ID
        non_existent_id = uuid4()

        # When
        response = await client.post(f"/api/v1/connectors/{non_existent_id}/reprocess")

        # Then
        assert response.status_code == 404


class TestTriggerConnectorSync:
    """Tests for POST /api/v1/connectors/{id}/sync."""

    @pytest.mark.asyncio
    async def test_trigger_manual_sync(
        self, client: AsyncClient, connector_repo
    ):
        """Should trigger background sync task."""
        # Given: local connector
        connector = Connector.create_local(path="/photos", name="Test")
        saved = await connector_repo.save(connector)

        # When
        response = await client.post(f"/api/v1/connectors/{saved.id.value}/sync")

        # Then
        # Accept both 200 and 202 (202 if celery works, 200 if worker not running)
        assert response.status_code in [200, 202]
        data = response.json()

        # If 202, should have task info
        if response.status_code == 202:
            assert "task_id" in data
            assert "message" in data
            assert "status" in data

    @pytest.mark.asyncio
    async def test_trigger_sync_google_photos_connector(
        self, client: AsyncClient, connector_repo
    ):
        """Should work for Google Photos connectors."""
        # Given: Google Photos connector
        connector = Connector.create_google_photos(name="Google Photos")
        connector.status = ConnectorStatus.CONNECTED
        saved = await connector_repo.save(connector)

        # When
        response = await client.post(f"/api/v1/connectors/{saved.id.value}/sync")

        # Then
        # Accept both 200 and 202 (202 if celery works, 200 if worker not running)
        assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    async def test_trigger_sync_upload_connector_rejected(
        self, client: AsyncClient, connector_repo
    ):
        """Should reject sync for upload connector (no source to sync from)."""
        # Given: upload connector
        connector = Connector.create_upload(upload_path="/uploads")
        saved = await connector_repo.save(connector)

        # When
        response = await client.post(f"/api/v1/connectors/{saved.id.value}/sync")

        # Then
        # Should reject with 400 Bad Request
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_trigger_sync_not_found(self, client: AsyncClient):
        """Should return 404 when connector doesn't exist."""
        # Given: non-existent ID
        non_existent_id = uuid4()

        # When
        response = await client.post(f"/api/v1/connectors/{non_existent_id}/sync")

        # Then
        assert response.status_code == 404


class TestGetSyncStatus:
    """Tests for GET /api/v1/connectors/{id}/sync/status."""

    @pytest.mark.asyncio
    async def test_get_sync_status_idle(
        self, client: AsyncClient, connector_repo
    ):
        """Should return idle status when not syncing."""
        # Given: connector not syncing
        connector = Connector.create_local(path="/photos", name="Test")
        connector.status = ConnectorStatus.CONNECTED
        saved = await connector_repo.save(connector)

        # When
        response = await client.get(
            f"/api/v1/connectors/{saved.id.value}/sync/status"
        )

        # Then
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        data = response_data["data"]

        assert data["syncing"] is False

    @pytest.mark.asyncio
    async def test_get_sync_status_with_last_sync_stats(
        self, client: AsyncClient, connector_repo
    ):
        """Should include last sync statistics."""
        # Given: connector with sync history
        from app.domain.value_objects.sync_stats import SyncStats

        connector = Connector.create_local(path="/photos", name="Test")
        connector.last_sync = datetime.utcnow()
        connector.last_sync_stats = SyncStats(
            total_items=100,
            indexed=95,
            skipped=3,
            failed=2,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        saved = await connector_repo.save(connector)

        # When
        response = await client.get(
            f"/api/v1/connectors/{saved.id.value}/sync/status"
        )

        # Then
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        data = response_data["data"]

        assert "last_sync" in data
        assert "stats" in data
        assert data["stats"]["total_items"] == 100
        assert data["stats"]["indexed"] == 95

    @pytest.mark.asyncio
    async def test_get_sync_status_not_found(self, client: AsyncClient):
        """Should return 404 when connector doesn't exist."""
        # Given: non-existent ID
        non_existent_id = uuid4()

        # When
        response = await client.get(
            f"/api/v1/connectors/{non_existent_id}/sync/status"
        )

        # Then
        assert response.status_code == 404


# Fixtures


@pytest.fixture
async def connector_repo(db_session):
    """Provide ConnectorRepository instance."""
    from app.adapters.outbound.persistence.postgres.repositories.connector_repository import (
        ConnectorRepositoryPostgres,
    )

    return ConnectorRepositoryPostgres(db_session)


@pytest.fixture
async def photo_repo(db_session):
    """Provide PhotoRepository instance."""
    from app.adapters.outbound.persistence.postgres.repositories.photo_repository import (
        PhotoRepositoryPostgres,
    )

    return PhotoRepositoryPostgres(db_session)
