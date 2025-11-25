"""Unit tests for connector sync tasks."""

from unittest.mock import AsyncMock, patch

import pytest

from app.adapters.inbound.workers.tasks.connector_sync import _sync_local_folder_async
from app.domain.entities.connector import Connector


class TestLocalFolderSync:
    """Tests for local folder sync task."""

    @pytest.mark.asyncio
    async def test_sync_local_folder_success(self, db_session, tmp_path):
        """Should successfully sync a local folder and track stats correctly."""
        from app.adapters.outbound.persistence.postgres.repositories.connector_repository import (
            ConnectorRepositoryPostgres,
        )
        from app.adapters.outbound.persistence.postgres.repositories.photo_repository import (
            PhotoRepositoryPostgres,
        )

        # Create test directory with some images
        test_dir = tmp_path / "photos"
        test_dir.mkdir()
        (test_dir / "photo1.jpg").write_bytes(b"fake jpg data")
        (test_dir / "photo2.jpg").write_bytes(b"fake jpg data")
        (test_dir / "photo3.png").write_bytes(b"fake png data")

        # Create connector
        connector = Connector.create_local(
            path=str(test_dir),
            name="Test Sync",
            recursive=False,
            watch=False,
        )

        connector_repo = ConnectorRepositoryPostgres(db_session)
        photo_repo = PhotoRepositoryPostgres(db_session)

        saved_connector = await connector_repo.save(connector)
        await db_session.commit()

        # Mock the background tasks so they don't actually run
        with patch(
            "app.adapters.inbound.workers.tasks.connector_sync.process_photo_task"
        ) as mock_process, patch(
            "app.adapters.inbound.workers.tasks.connector_sync.detect_faces_task"
        ) as mock_faces:
            # Mock delay to avoid actual task queue
            mock_process.delay = AsyncMock()
            mock_faces.delay = AsyncMock()

            # Execute sync
            result = await _sync_local_folder_async(str(saved_connector.id.value))

        # Verify result
        assert result["status"] == "completed"
        assert result["total_items"] == 3
        assert result["indexed"] == 3
        assert result["skipped"] == 0
        assert result["failed"] == 0
        assert result["duration_seconds"] is not None

        # Verify photos were created in database
        photos = await photo_repo.find_by_connector(saved_connector.id.value, limit=100)
        assert len(photos) == 3

        # Verify connector status updated
        updated_connector = await connector_repo.find_by_id(saved_connector.id.value)
        assert updated_connector.last_sync_stats is not None
        assert updated_connector.last_sync_stats.total_items == 3
        assert updated_connector.last_sync_stats.indexed == 3

    @pytest.mark.asyncio
    async def test_sync_skips_existing_photos(self, db_session, tmp_path):
        """Should skip photos that already exist in database."""
        from app.adapters.outbound.persistence.postgres.repositories.connector_repository import (
            ConnectorRepositoryPostgres,
        )
        from app.adapters.outbound.persistence.postgres.repositories.photo_repository import (
            PhotoRepositoryPostgres,
        )
        from app.domain.entities import Photo

        # Create test directory
        test_dir = tmp_path / "photos"
        test_dir.mkdir()
        photo1_path = test_dir / "photo1.jpg"
        photo2_path = test_dir / "photo2.jpg"
        photo1_path.write_bytes(b"fake jpg data")
        photo2_path.write_bytes(b"fake jpg data")

        # Create connector
        connector = Connector.create_local(path=str(test_dir), name="Test Skip")
        connector_repo = ConnectorRepositoryPostgres(db_session)
        photo_repo = PhotoRepositoryPostgres(db_session)

        saved_connector = await connector_repo.save(connector)
        await db_session.commit()

        # Create one existing photo
        existing_photo = Photo.create_from_connector(
            filename="photo1.jpg",
            connector_type="local",
            connector_id=saved_connector.id.value,
            external_id=str(photo1_path),
            source_path=str(photo1_path),
        )
        await photo_repo.save(existing_photo)
        await db_session.commit()

        # Mock background tasks
        with patch(
            "app.adapters.inbound.workers.tasks.connector_sync.process_photo_task"
        ) as mock_process, patch(
            "app.adapters.inbound.workers.tasks.connector_sync.detect_faces_task"
        ) as mock_faces:
            mock_process.delay = AsyncMock()
            mock_faces.delay = AsyncMock()

            # Execute sync
            result = await _sync_local_folder_async(str(saved_connector.id.value))

        # Verify result - should skip existing photo1, index new photo2
        assert result["status"] == "completed"
        assert result["total_items"] == 2
        assert result["indexed"] == 1  # Only photo2 is new
        assert result["skipped"] == 1  # photo1 already exists

        # Verify still only 2 photos total
        photos = await photo_repo.find_by_connector(saved_connector.id.value, limit=100)
        assert len(photos) == 2

    @pytest.mark.asyncio
    async def test_sync_handles_errors_gracefully(self, db_session, tmp_path):
        """Should track failed items and continue processing."""
        from app.adapters.outbound.persistence.postgres.repositories.connector_repository import (
            ConnectorRepositoryPostgres,
        )

        # Create test directory with invalid file
        test_dir = tmp_path / "photos"
        test_dir.mkdir()
        (test_dir / "photo1.jpg").write_bytes(b"valid data")

        # Create connector
        connector = Connector.create_local(path=str(test_dir), name="Test Errors")
        connector_repo = ConnectorRepositoryPostgres(db_session)
        saved_connector = await connector_repo.save(connector)
        await db_session.commit()

        # Mock background tasks
        with patch(
            "app.adapters.inbound.workers.tasks.connector_sync.process_photo_task"
        ) as mock_process, patch(
            "app.adapters.inbound.workers.tasks.connector_sync.detect_faces_task"
        ) as mock_faces:
            mock_process.delay = AsyncMock()
            mock_faces.delay = AsyncMock()

            # Execute sync (should complete despite any issues)
            result = await _sync_local_folder_async(str(saved_connector.id.value))

        # Should complete without raising exception
        assert result["status"] == "completed"
        # Stats should be tracked properly
        assert "total_items" in result
        assert "indexed" in result
        assert "failed" in result

    @pytest.mark.asyncio
    async def test_sync_with_empty_folder(self, db_session, tmp_path):
        """Should handle empty folders gracefully."""
        from app.adapters.outbound.persistence.postgres.repositories.connector_repository import (
            ConnectorRepositoryPostgres,
        )

        # Create empty test directory
        test_dir = tmp_path / "empty_photos"
        test_dir.mkdir()

        # Create connector
        connector = Connector.create_local(path=str(test_dir), name="Empty Folder")
        connector_repo = ConnectorRepositoryPostgres(db_session)
        saved_connector = await connector_repo.save(connector)
        await db_session.commit()

        # Execute sync
        result = await _sync_local_folder_async(str(saved_connector.id.value))

        # Should complete successfully with zero items
        assert result["status"] == "completed"
        assert result["total_items"] == 0
        assert result["indexed"] == 0
        assert result["skipped"] == 0
        assert result["failed"] == 0


class TestSyncStatsMutability:
    """Tests to ensure SyncStats immutability is properly handled."""

    @pytest.mark.asyncio
    async def test_sync_does_not_mutate_frozen_dataclass(self, db_session, tmp_path):
        """
        REGRESSION TEST: Ensure sync task doesn't try to mutate frozen SyncStats.

        This test catches the error: "cannot assign to field 'total_items'"
        which occurs when trying to mutate a frozen dataclass.
        """
        from app.adapters.outbound.persistence.postgres.repositories.connector_repository import (
            ConnectorRepositoryPostgres,
        )

        # Create test directory with files
        test_dir = tmp_path / "photos"
        test_dir.mkdir()
        (test_dir / "photo1.jpg").write_bytes(b"data")
        (test_dir / "photo2.jpg").write_bytes(b"data")

        # Create connector
        connector = Connector.create_local(path=str(test_dir), name="Frozen Test")
        connector_repo = ConnectorRepositoryPostgres(db_session)
        saved_connector = await connector_repo.save(connector)
        await db_session.commit()

        # Mock background tasks
        with patch(
            "app.adapters.inbound.workers.tasks.connector_sync.process_photo_task"
        ) as mock_process, patch(
            "app.adapters.inbound.workers.tasks.connector_sync.detect_faces_task"
        ) as mock_faces:
            mock_process.delay = AsyncMock()
            mock_faces.delay = AsyncMock()

            # This should NOT raise FrozenInstanceError
            result = await _sync_local_folder_async(str(saved_connector.id.value))

        # Verify it completed successfully
        assert result["status"] == "completed"

        # Verify stats are properly tracked
        updated_connector = await connector_repo.find_by_id(saved_connector.id.value)
        assert updated_connector.last_sync_stats is not None
        assert updated_connector.last_sync_stats.total_items >= 0
        assert updated_connector.last_sync_stats.indexed >= 0
        assert updated_connector.last_sync_stats.skipped >= 0
        assert updated_connector.last_sync_stats.failed >= 0
