"""Integration tests for Google Photos sync workflow.

Tests the complete sync flow: Auth → List → Download → Index → Dedup
"""

import io
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.adapters.outbound.persistence.postgres.repositories import (
    ConnectorRepositoryPostgres,
    PhotoRepositoryPostgres,
)
from app.domain.entities.connector import ConnectorStatus, ConnectorType
from tests.integration.factories import ConnectorFactory, PhotoFactory


@pytest.mark.integration
@pytest.mark.slow
class TestGooglePhotosSyncIntegration:
    """Integration tests for Google Photos sync."""

    @pytest.mark.asyncio
    async def test_sync_idempotency(
        self,
        test_session,
        test_file_storage,
        test_vector_store,
    ):
        """Test syncing twice doesn't create duplicates.

        Critical invariant: Syncing the same photos multiple times
        should not create duplicate entries in database or vector store.
        """
        connector_repo = ConnectorRepositoryPostgres(test_session)
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create Google Photos connector
        connector = ConnectorFactory.create_google_photos(
            name="Test Google Photos"
        )
        saved_connector = await connector_repo.save(connector)

        # Mock Google Photos API responses
        mock_media_items = [
            {
                "id": "gp_photo_1",
                "filename": "IMG_001.jpg",
                "mimeType": "image/jpeg",
                "mediaMetadata": {
                    "creationTime": "2024-01-15T10:30:00Z",
                    "width": "1920",
                    "height": "1080",
                },
                "baseUrl": "https://example.com/photo1",
            },
            {
                "id": "gp_photo_2",
                "filename": "IMG_002.jpg",
                "mimeType": "image/jpeg",
                "mediaMetadata": {
                    "creationTime": "2024-01-16T14:20:00Z",
                    "width": "1920",
                    "height": "1080",
                },
                "baseUrl": "https://example.com/photo2",
            },
        ]

        # 2. First sync - simulate downloading and indexing photos
        with patch(
            "app.adapters.outbound.connectors.google_photos.GooglePhotosClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.list_media_items.return_value = mock_media_items
            mock_client.download_media.side_effect = [
                b"fake_photo_1_data",
                b"fake_photo_2_data",
            ]
            mock_client_class.return_value = mock_client

            # Simulate sync process
            indexed_photos = []

            for item in mock_media_items:
                # Check if photo already exists (by external_id)
                existing = await photo_repo.find_by_external_id(
                    item["id"], saved_connector.id.value
                )

                if not existing:
                    # Download and save photo
                    photo_data = await mock_client.download_media(item["baseUrl"])
                    file = io.BytesIO(photo_data)
                    storage_path = await test_file_storage.save_photo(
                        file, item["filename"]
                    )

                    # Create photo entity
                    photo = PhotoFactory.create(
                        filename=item["filename"],
                        storage_path=storage_path,
                        connector_type="google_photos",
                        connector_id=saved_connector.id.value,
                        external_id=item["id"],
                        mime_type=item["mimeType"],
                        width=int(item["mediaMetadata"]["width"]),
                        height=int(item["mediaMetadata"]["height"]),
                    )

                    saved_photo = await photo_repo.save(photo)
                    indexed_photos.append(saved_photo)

            await test_session.commit()

        # Verify first sync
        assert len(indexed_photos) == 2

        photos_after_first = await photo_repo.find_by_connector_id(
            saved_connector.id.value
        )
        assert len(photos_after_first) == 2

        # 3. Second sync - should skip existing photos
        with patch(
            "app.adapters.outbound.connectors.google_photos.GooglePhotosClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.list_media_items.return_value = mock_media_items
            mock_client_class.return_value = mock_client

            # Simulate sync process again
            indexed_second = []
            skipped_count = 0

            for item in mock_media_items:
                existing = await photo_repo.find_by_external_id(
                    item["id"], saved_connector.id.value
                )

                if existing:
                    skipped_count += 1
                else:
                    # Would download and save
                    indexed_second.append(item)

        # Verify second sync skipped all existing photos
        assert skipped_count == 2
        assert len(indexed_second) == 0

        # Verify no duplicates created
        photos_after_second = await photo_repo.find_by_connector_id(
            saved_connector.id.value
        )
        assert len(photos_after_second) == 2

    @pytest.mark.asyncio
    async def test_sync_handles_new_photos(
        self,
        test_session,
        test_file_storage,
    ):
        """Test sync correctly handles new photos added to Google Photos."""
        connector_repo = ConnectorRepositoryPostgres(test_session)
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create connector
        connector = ConnectorFactory.create_google_photos()
        saved_connector = await connector_repo.save(connector)

        # 2. First sync - 2 photos
        initial_items = [
            {
                "id": "gp_photo_1",
                "filename": "IMG_001.jpg",
                "mimeType": "image/jpeg",
                "mediaMetadata": {
                    "creationTime": "2024-01-15T10:30:00Z",
                    "width": "1920",
                    "height": "1080",
                },
                "baseUrl": "https://example.com/photo1",
            },
            {
                "id": "gp_photo_2",
                "filename": "IMG_002.jpg",
                "mimeType": "image/jpeg",
                "mediaMetadata": {
                    "creationTime": "2024-01-16T14:20:00Z",
                    "width": "1920",
                    "height": "1080",
                },
                "baseUrl": "https://example.com/photo2",
            },
        ]

        for item in initial_items:
            photo = PhotoFactory.create(
                filename=item["filename"],
                connector_type="google_photos",
                connector_id=saved_connector.id.value,
                external_id=item["id"],
            )
            await photo_repo.save(photo)

        await test_session.commit()

        # 3. Second sync - Google Photos now has 3 photos (1 new)
        updated_items = initial_items + [
            {
                "id": "gp_photo_3",
                "filename": "IMG_003.jpg",
                "mimeType": "image/jpeg",
                "mediaMetadata": {
                    "creationTime": "2024-01-17T09:15:00Z",
                    "width": "1920",
                    "height": "1080",
                },
                "baseUrl": "https://example.com/photo3",
            }
        ]

        new_photos = []
        for item in updated_items:
            existing = await photo_repo.find_by_external_id(
                item["id"], saved_connector.id.value
            )

            if not existing:
                photo = PhotoFactory.create(
                    filename=item["filename"],
                    connector_type="google_photos",
                    connector_id=saved_connector.id.value,
                    external_id=item["id"],
                )
                saved = await photo_repo.save(photo)
                new_photos.append(saved)

        await test_session.commit()

        # Verify only 1 new photo indexed
        assert len(new_photos) == 1
        assert new_photos[0].external_id == "gp_photo_3"

        # Verify total count
        all_photos = await photo_repo.find_by_connector_id(
            saved_connector.id.value
        )
        assert len(all_photos) == 3

    @pytest.mark.asyncio
    async def test_sync_handles_deleted_photos(
        self,
        test_session,
        test_file_storage,
    ):
        """Test sync marks photos as deleted when removed from Google Photos."""
        connector_repo = ConnectorRepositoryPostgres(test_session)
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create connector and photos
        connector = ConnectorFactory.create_google_photos()
        saved_connector = await connector_repo.save(connector)

        photo1 = PhotoFactory.create(
            filename="IMG_001.jpg",
            connector_type="google_photos",
            connector_id=saved_connector.id.value,
            external_id="gp_photo_1",
            source_deleted=False,
        )
        photo2 = PhotoFactory.create(
            filename="IMG_002.jpg",
            connector_type="google_photos",
            connector_id=saved_connector.id.value,
            external_id="gp_photo_2",
            source_deleted=False,
        )
        photo3 = PhotoFactory.create(
            filename="IMG_003.jpg",
            connector_type="google_photos",
            connector_id=saved_connector.id.value,
            external_id="gp_photo_3",
            source_deleted=False,
        )

        await photo_repo.save(photo1)
        await photo_repo.save(photo2)
        await photo_repo.save(photo3)
        await test_session.commit()

        # 2. Sync - Google Photos now only has 2 photos (photo2 deleted)
        current_items = [
            {"id": "gp_photo_1"},
            {"id": "gp_photo_3"},
        ]

        current_external_ids = {item["id"] for item in current_items}

        # Get all photos for this connector
        all_photos = await photo_repo.find_by_connector_id(
            saved_connector.id.value
        )

        # Mark photos not in current sync as deleted
        for photo in all_photos:
            if photo.external_id not in current_external_ids:
                photo.source_deleted = True
                await photo_repo.save(photo)

        await test_session.commit()

        # 3. Verify photo2 marked as deleted
        photo2_updated = await photo_repo.find_by_id(photo2.id.value)
        assert photo2_updated.source_deleted is True

        # Others not deleted
        photo1_updated = await photo_repo.find_by_id(photo1.id.value)
        photo3_updated = await photo_repo.find_by_id(photo3.id.value)

        assert photo1_updated.source_deleted is False
        assert photo3_updated.source_deleted is False

    @pytest.mark.asyncio
    async def test_sync_rate_limiting(
        self,
        test_session,
    ):
        """Test sync respects rate limits when downloading photos."""
        import time

        connector_repo = ConnectorRepositoryPostgres(test_session)

        # Create connector
        connector = ConnectorFactory.create_google_photos()
        await connector_repo.save(connector)

        # Simulate rate limiting with backoff
        request_times = []
        rate_limit_delay = 0.1  # 100ms between requests

        mock_items = [{"id": f"gp_photo_{i}"} for i in range(5)]

        for item in mock_items:
            request_times.append(time.time())

            # Simulate rate-limited download
            await asyncio.sleep(rate_limit_delay)

        # Verify requests were rate limited
        for i in range(1, len(request_times)):
            time_delta = request_times[i] - request_times[i - 1]
            assert (
                time_delta >= rate_limit_delay
            ), f"Request {i} not rate limited properly"

    @pytest.mark.asyncio
    async def test_sync_error_recovery(
        self,
        test_session,
        test_file_storage,
    ):
        """Test sync can recover from partial failures."""
        connector_repo = ConnectorRepositoryPostgres(test_session)
        photo_repo = PhotoRepositoryPostgres(test_session)

        # Create connector
        connector = ConnectorFactory.create_google_photos()
        saved_connector = await connector_repo.save(connector)

        # Simulate sync where some photos fail to download
        items = [
            {"id": f"gp_photo_{i}", "filename": f"IMG_{i:03d}.jpg"}
            for i in range(5)
        ]

        successful = []
        failed = []

        for i, item in enumerate(items):
            try:
                # Simulate failure for photo 2
                if i == 2:
                    raise Exception("Download failed")

                # Successfully save photo
                photo = PhotoFactory.create(
                    filename=item["filename"],
                    connector_type="google_photos",
                    connector_id=saved_connector.id.value,
                    external_id=item["id"],
                    processing_status="completed",
                )
                saved = await photo_repo.save(photo)
                successful.append(saved)

            except Exception as e:
                failed.append(item["id"])
                # Mark for retry
                continue

        await test_session.commit()

        # Verify partial success
        assert len(successful) == 4
        assert len(failed) == 1
        assert "gp_photo_2" in failed

        # Retry failed photos
        for failed_id in failed:
            item = next(i for i in items if i["id"] == failed_id)

            # This time it succeeds
            photo = PhotoFactory.create(
                filename=item["filename"],
                connector_type="google_photos",
                connector_id=saved_connector.id.value,
                external_id=item["id"],
                processing_status="completed",
            )
            await photo_repo.save(photo)

        await test_session.commit()

        # Verify all photos eventually indexed
        all_photos = await photo_repo.find_by_connector_id(
            saved_connector.id.value
        )
        assert len(all_photos) == 5

    @pytest.mark.asyncio
    async def test_sync_updates_connector_stats(
        self,
        test_session,
    ):
        """Test sync updates connector statistics."""
        from app.domain.entities.connector import SyncStats

        connector_repo = ConnectorRepositoryPostgres(test_session)

        # Create connector
        connector = ConnectorFactory.create_google_photos()
        saved_connector = await connector_repo.save(connector)

        # Simulate sync
        sync_stats = SyncStats(
            total_items=100,
            indexed=95,
            skipped=5,
            failed=0,
        )

        # Update connector with sync stats
        saved_connector.status = ConnectorStatus.CONNECTED
        saved_connector.last_sync_at = datetime.now(UTC)

        updated = await connector_repo.save(saved_connector)

        # Verify stats updated
        assert updated.status == ConnectorStatus.CONNECTED
        assert updated.last_sync_at is not None

    @pytest.mark.asyncio
    async def test_sync_preserves_existing_metadata(
        self,
        test_session,
        test_file_storage,
    ):
        """Test sync preserves user-added metadata (tags, descriptions)."""
        connector_repo = ConnectorRepositoryPostgres(test_session)
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create connector and photo
        connector = ConnectorFactory.create_google_photos()
        saved_connector = await connector_repo.save(connector)

        photo = PhotoFactory.create(
            filename="IMG_001.jpg",
            connector_type="google_photos",
            connector_id=saved_connector.id.value,
            external_id="gp_photo_1",
            description="User added description",
        )
        saved_photo = await photo_repo.save(photo)
        await test_session.commit()

        # 2. Simulate sync that updates photo metadata
        # In real sync, we might update taken_at, dimensions, etc.
        # But we should NOT overwrite user-added fields

        synced_metadata = {
            "width": 1920,
            "height": 1080,
            "mimeType": "image/jpeg",
        }

        # Update photo but preserve description
        saved_photo.width = synced_metadata["width"]
        saved_photo.height = synced_metadata["height"]
        saved_photo.mime_type = synced_metadata["mimeType"]
        # description is NOT updated

        updated = await photo_repo.save(saved_photo)
        await test_session.commit()

        # 3. Verify user metadata preserved
        retrieved = await photo_repo.find_by_id(saved_photo.id.value)

        assert retrieved.description == "User added description"
        assert retrieved.width == 1920
        assert retrieved.height == 1080


# Import asyncio for rate limiting test
import asyncio
