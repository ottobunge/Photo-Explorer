"""Integration tests for local folder connector API.

Tests the following endpoints:
- POST /api/v1/connectors/local - Create local folder connector
- PATCH /api/v1/connectors/{id} - Update local connector config
- POST /api/v1/connectors/{id}/sync - Trigger folder scan

Following TDD approach - tests written before implementation.
"""

import pytest
from pathlib import Path
from uuid import uuid4
import tempfile
import shutil

from httpx import AsyncClient

from app.domain.entities.connector import Connector, ConnectorType, ConnectorStatus


class TestCreateLocalConnector:
    """Tests for POST /api/v1/connectors/local."""

    @pytest.mark.asyncio
    async def test_create_local_connector_success(
        self, client: AsyncClient, connector_repo, temp_photos_dir
    ):
        """Should create local connector with valid path."""
        # Given: valid folder path
        folder_path = str(temp_photos_dir)

        # When
        response = await client.post(
            "/api/v1/connectors/local",
            json={
                "path": folder_path,
                "name": "My Photos",
                "recursive": True,
                "watch": False,
                "autoAlbum": False,
            },
        )

        # Then
        assert response.status_code == 201
        data = response.json()

        assert data["type"] == "local"
        assert data["name"] == "My Photos"
        assert data["status"] == "connected"
        assert data["config"]["path"] == folder_path
        assert data["config"]["recursive"] is True
        assert data["config"]["watch"] is False
        assert "id" in data

        # Verify in database
        connectors = await connector_repo.find_all()
        assert any(c.config.get("path") == folder_path for c in connectors)

    @pytest.mark.asyncio
    async def test_create_local_connector_minimal_config(
        self, client: AsyncClient, temp_photos_dir
    ):
        """Should create connector with minimal required fields."""
        # Given: only path provided
        folder_path = str(temp_photos_dir)

        # When
        response = await client.post(
            "/api/v1/connectors/local",
            json={"path": folder_path},
        )

        # Then
        assert response.status_code == 201
        data = response.json()

        # Should have sensible defaults
        assert data["config"]["path"] == folder_path
        assert "recursive" in data["config"]
        assert "watch" in data["config"]

    @pytest.mark.asyncio
    async def test_create_local_connector_validates_path_exists(
        self, client: AsyncClient
    ):
        """Should validate that path exists."""
        # Given: non-existent path
        invalid_path = "/this/path/does/not/exist/at/all"

        # When
        response = await client.post(
            "/api/v1/connectors/local",
            json={"path": invalid_path, "name": "Invalid"},
        )

        # Then
        assert response.status_code == 400
        assert "path" in response.json()["detail"].lower() or "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_local_connector_validates_path_is_directory(
        self, client: AsyncClient, temp_photos_dir
    ):
        """Should validate that path is a directory, not a file."""
        # Given: path to a file, not directory
        test_file = temp_photos_dir / "test.txt"
        test_file.write_text("test")

        # When
        response = await client.post(
            "/api/v1/connectors/local",
            json={"path": str(test_file), "name": "File Path"},
        )

        # Then
        assert response.status_code == 400
        assert "directory" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_local_connector_prevents_duplicates(
        self, client: AsyncClient, connector_repo, temp_photos_dir
    ):
        """Should prevent creating duplicate connector for same path."""
        # Given: existing connector for path
        folder_path = str(temp_photos_dir)
        existing = Connector.create_local(path=folder_path, name="Existing")
        await connector_repo.save(existing)

        # When: try to create another for same path
        response = await client.post(
            "/api/v1/connectors/local",
            json={"path": folder_path, "name": "Duplicate"},
        )

        # Then
        assert response.status_code == 409  # Conflict
        assert "already exists" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_local_connector_generates_default_name(
        self, client: AsyncClient, temp_photos_dir
    ):
        """Should generate default name from path if not provided."""
        # Given: path without name
        folder_path = str(temp_photos_dir)

        # When
        response = await client.post(
            "/api/v1/connectors/local",
            json={"path": folder_path},
        )

        # Then
        assert response.status_code == 201
        data = response.json()

        # Should have a name (derived from path or default)
        assert data["name"] is not None
        assert len(data["name"]) > 0

    @pytest.mark.asyncio
    async def test_create_local_connector_returns_full_connector(
        self, client: AsyncClient, temp_photos_dir
    ):
        """Should return complete connector object."""
        # When
        response = await client.post(
            "/api/v1/connectors/local",
            json={
                "path": str(temp_photos_dir),
                "name": "Test",
                "recursive": True,
            },
        )

        # Then
        assert response.status_code == 201
        data = response.json()

        # Check all expected fields
        required_fields = [
            "id",
            "type",
            "name",
            "enabled",
            "status",
            "config",
            "createdAt",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"


class TestUpdateLocalConnectorPath:
    """Tests for updating local connector path."""

    @pytest.mark.asyncio
    async def test_update_local_connector_path(
        self, client: AsyncClient, connector_repo, temp_photos_dir
    ):
        """Should update local connector folder path."""
        # Given: existing local connector
        old_path = str(temp_photos_dir)
        connector = Connector.create_local(path=old_path, name="Test")
        saved = await connector_repo.save(connector)

        # Create new directory for new path
        new_dir = temp_photos_dir.parent / "new_photos"
        new_dir.mkdir(exist_ok=True)
        new_path = str(new_dir)

        # When: update path
        response = await client.patch(
            f"/api/v1/connectors/{saved.id.value}",
            json={
                "config": {
                    "path": new_path,
                    "recursive": True,
                }
            },
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        assert data["config"]["path"] == new_path

        # Verify in database
        updated = await connector_repo.find_by_id(saved.id.value)
        assert updated.config["path"] == new_path

        # Cleanup
        shutil.rmtree(new_dir)

    @pytest.mark.asyncio
    async def test_update_local_connector_validates_new_path(
        self, client: AsyncClient, connector_repo, temp_photos_dir
    ):
        """Should validate new path exists."""
        # Given: existing connector
        connector = Connector.create_local(path=str(temp_photos_dir), name="Test")
        saved = await connector_repo.save(connector)

        # When: update to invalid path
        response = await client.patch(
            f"/api/v1/connectors/{saved.id.value}",
            json={
                "config": {
                    "path": "/invalid/path/nowhere",
                }
            },
        )

        # Then
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_local_connector_config_options(
        self, client: AsyncClient, connector_repo, temp_photos_dir
    ):
        """Should update recursive, watch, autoAlbum options."""
        # Given: connector with specific config
        connector = Connector.create_local(
            path=str(temp_photos_dir),
            name="Test",
            recursive=False,
            watch=False,
            auto_album=False,
        )
        saved = await connector_repo.save(connector)

        # When: update all options
        response = await client.patch(
            f"/api/v1/connectors/{saved.id.value}",
            json={
                "config": {
                    "recursive": True,
                    "watch": True,
                    "autoAlbum": True,
                }
            },
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        assert data["config"]["recursive"] is True
        assert data["config"]["watch"] is True
        assert data["config"]["autoAlbum"] is True


class TestTriggerLocalFolderScan:
    """Tests for triggering local folder scan."""

    @pytest.mark.asyncio
    async def test_trigger_folder_scan(
        self, client: AsyncClient, connector_repo, temp_photos_dir
    ):
        """Should trigger background task to scan folder."""
        # Given: local connector with photos in folder
        connector = Connector.create_local(path=str(temp_photos_dir), name="Test")
        saved = await connector_repo.save(connector)

        # Add some test images to folder
        (temp_photos_dir / "photo1.jpg").write_bytes(b"fake image data")
        (temp_photos_dir / "photo2.jpg").write_bytes(b"fake image data")

        # When: trigger sync
        response = await client.post(f"/api/v1/connectors/{saved.id.value}/sync")

        # Then
        assert response.status_code == 202
        data = response.json()

        # Should indicate background task started
        assert "taskId" in data or "message" in data

    @pytest.mark.asyncio
    async def test_trigger_scan_updates_status_to_syncing(
        self, client: AsyncClient, connector_repo, temp_photos_dir
    ):
        """Should update connector status to syncing."""
        # Given: local connector
        connector = Connector.create_local(path=str(temp_photos_dir), name="Test")
        saved = await connector_repo.save(connector)

        # When: trigger sync
        await client.post(f"/api/v1/connectors/{saved.id.value}/sync")

        # Then: check status updated
        # Note: In real implementation, status would be updated by background task
        # This test verifies the endpoint accepts the request
        response = await client.get(
            f"/api/v1/connectors/{saved.id.value}/sync/status"
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_trigger_scan_empty_folder(
        self, client: AsyncClient, connector_repo, temp_photos_dir
    ):
        """Should handle empty folder gracefully."""
        # Given: connector with empty folder
        connector = Connector.create_local(path=str(temp_photos_dir), name="Empty")
        saved = await connector_repo.save(connector)

        # When
        response = await client.post(f"/api/v1/connectors/{saved.id.value}/sync")

        # Then: should not fail
        assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    async def test_trigger_scan_recursive_option(
        self, client: AsyncClient, connector_repo, temp_photos_dir
    ):
        """Should respect recursive configuration."""
        # Given: connector with recursive=True
        connector = Connector.create_local(
            path=str(temp_photos_dir),
            name="Recursive",
            recursive=True,
        )
        saved = await connector_repo.save(connector)

        # Create nested folder structure
        nested_dir = temp_photos_dir / "subfolder" / "nested"
        nested_dir.mkdir(parents=True)
        (nested_dir / "deep_photo.jpg").write_bytes(b"fake image")

        # When
        response = await client.post(f"/api/v1/connectors/{saved.id.value}/sync")

        # Then
        assert response.status_code == 202
        # Background task should scan nested folders


class TestLocalConnectorEdgeCases:
    """Edge cases and error handling for local connectors."""

    @pytest.mark.asyncio
    async def test_create_connector_with_special_characters_in_path(
        self, client: AsyncClient, temp_photos_dir
    ):
        """Should handle paths with special characters."""
        # Given: path with spaces and special chars
        special_dir = temp_photos_dir.parent / "My Photos (2024)"
        special_dir.mkdir(exist_ok=True)

        # When
        response = await client.post(
            "/api/v1/connectors/local",
            json={"path": str(special_dir), "name": "Special Path"},
        )

        # Then
        assert response.status_code == 201

        # Cleanup
        shutil.rmtree(special_dir)

    @pytest.mark.asyncio
    async def test_create_connector_with_relative_path(
        self, client: AsyncClient
    ):
        """Should reject or convert relative paths."""
        # When: use relative path
        response = await client.post(
            "/api/v1/connectors/local",
            json={"path": "./photos", "name": "Relative"},
        )

        # Then: should reject or convert to absolute
        # Implementation choice: reject for clarity
        assert response.status_code in [400, 201]

    @pytest.mark.asyncio
    async def test_update_connector_type_not_allowed(
        self, client: AsyncClient, connector_repo, temp_photos_dir
    ):
        """Should not allow changing connector type."""
        # Given: local connector
        connector = Connector.create_local(path=str(temp_photos_dir), name="Test")
        saved = await connector_repo.save(connector)

        # When: try to change type
        response = await client.patch(
            f"/api/v1/connectors/{saved.id.value}",
            json={"type": "google_photos"},
        )

        # Then: should ignore or reject
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            # If accepted, type should not have changed
            data = response.json()
            assert data["type"] == "local"


# Fixtures


@pytest.fixture
def temp_photos_dir(tmp_path):
    """Create temporary directory for test photos."""
    photos_dir = tmp_path / "test_photos"
    photos_dir.mkdir()
    yield photos_dir
    # Cleanup happens automatically with tmp_path


@pytest.fixture
async def connector_repo(db_session):
    """Provide ConnectorRepository instance."""
    from app.adapters.outbound.persistence.postgres.repositories.connector_repository import (
        PostgresConnectorRepository,
    )

    return PostgresConnectorRepository(db_session)
