"""Unit tests for PhotoRepository performance - focusing on N+1 query prevention.

Tests for album association efficiency when saving photos.
Following TDD approach.
"""

from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4

import pytest

from app.adapters.outbound.persistence.postgres.models import AlbumModel, PhotoModel
from app.adapters.outbound.persistence.postgres.repositories.photo_repository import (
    PhotoRepositoryPostgres,
)
from app.domain.entities.connector import ConnectorType
from app.domain.entities.photo import Photo


class TestPhotoRepositorySaveWithAlbumsPerformance:
    """Tests for efficient album association when saving photos."""

    @pytest.mark.asyncio
    async def test_save_with_albums_single_query(self):
        """Should use a single batch query to fetch all albums, not N queries."""
        # Given: mock session and a photo with 3 album IDs
        mock_session = AsyncMock()
        repo = PhotoRepositoryPostgres(mock_session)

        album_id1 = uuid4()
        album_id2 = uuid4()
        album_id3 = uuid4()

        photo = Photo.create(
            filename="test.jpg",
            storage_path="/test/test.jpg",
            connector_type=ConnectorType.LOCAL.value,
            connector_id=uuid4(),
        )
        photo.album_ids = [album_id1, album_id2, album_id3]

        # Mock existing photo lookup to return None (new photo)
        mock_session.get.return_value = None

        # Mock album batch query
        mock_album1 = AlbumModel(id=album_id1, name="Album 1")
        mock_album2 = AlbumModel(id=album_id2, name="Album 2")
        mock_album3 = AlbumModel(id=album_id3, name="Album 3")

        # Mock execute to return albums
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            mock_album1,
            mock_album2,
            mock_album3,
        ]
        mock_session.execute.return_value = mock_result

        # When: save the photo
        await repo.save(photo)

        # Then: session.execute should be called for batch album query
        # Look for the SELECT statement with IN clause
        execute_calls = mock_session.execute.call_args_list

        # Filter for SELECT queries (not DELETE)
        select_calls = [
            call
            for call in execute_calls
            if "SELECT" in str(call) and "albums" in str(call).lower()
        ]

        # Should have exactly ONE SELECT query for albums
        assert len(select_calls) == 1, (
            f"Expected 1 batch SELECT query for albums, got {len(select_calls)}. "
            f"This indicates N+1 query pattern."
        )

        # session.get should only be called once for the initial photo lookup
        # NOT called for each album (that would be N+1)
        assert mock_session.get.call_count == 1
        assert mock_session.get.call_args == call(PhotoModel, photo.id.value)

    @pytest.mark.asyncio
    async def test_save_with_10_albums_max_2_queries(self):
        """Should use at most 2 queries regardless of number of albums."""
        # Given: mock session and a photo with 10 album IDs
        mock_session = AsyncMock()
        repo = PhotoRepositoryPostgres(mock_session)

        album_ids = [uuid4() for _ in range(10)]

        photo = Photo.create(
            filename="test.jpg",
            storage_path="/test/test.jpg",
            connector_type=ConnectorType.LOCAL.value,
            connector_id=uuid4(),
        )
        photo.album_ids = album_ids

        # Mock existing photo lookup to return None (new photo)
        mock_session.get.return_value = None

        # Mock album batch query
        mock_albums = [AlbumModel(id=aid, name=f"Album {i}") for i, aid in enumerate(album_ids)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_albums
        mock_session.execute.return_value = mock_result

        # When: save the photo
        await repo.save(photo)

        # Then: should have at most 2 queries total:
        # 1. DELETE for existing associations
        # 2. SELECT for batch album fetch
        execute_calls = mock_session.execute.call_args_list
        assert len(execute_calls) <= 2, (
            f"Expected at most 2 execute calls, got {len(execute_calls)}. "
            f"This indicates N+1 query pattern where each album triggers a query."
        )

    @pytest.mark.asyncio
    async def test_save_with_no_albums_no_batch_query(self):
        """Should not execute album query when photo has no albums."""
        # Given: mock session and a photo with no album IDs
        mock_session = AsyncMock()
        repo = PhotoRepositoryPostgres(mock_session)

        photo = Photo.create(
            filename="test.jpg",
            storage_path="/test/test.jpg",
            connector_type=ConnectorType.LOCAL.value,
            connector_id=uuid4(),
        )
        photo.album_ids = []

        # Mock existing photo lookup to return None (new photo)
        mock_session.get.return_value = None

        # When: save the photo
        await repo.save(photo)

        # Then: should only have DELETE query for associations, no SELECT for albums
        execute_calls = mock_session.execute.call_args_list

        # Check that there's no SELECT query for albums
        select_calls = [
            call
            for call in execute_calls
            if "SELECT" in str(call) and "albums" in str(call).lower()
        ]

        assert len(select_calls) == 0, "Should not execute album SELECT when photo has no albums"

    @pytest.mark.asyncio
    async def test_save_update_existing_photo_with_albums_efficient(self):
        """Should use batch query when updating existing photo with albums."""
        # Given: mock session, existing photo, and new album IDs
        mock_session = AsyncMock()
        repo = PhotoRepositoryPostgres(mock_session)

        photo_id = uuid4()
        album_id1 = uuid4()
        album_id2 = uuid4()

        photo = Photo.create(
            filename="test.jpg",
            storage_path="/test/test.jpg",
            connector_type=ConnectorType.LOCAL.value,
            connector_id=uuid4(),
        )
        photo.album_ids = [album_id1, album_id2]
        photo._id.value = photo_id  # Set existing ID

        # Mock existing photo lookup
        existing_model = PhotoModel(
            id=photo_id,
            filename="test.jpg",
            connector_type=ConnectorType.LOCAL.value,
        )
        existing_model.albums = []
        mock_session.get.return_value = existing_model

        # Mock album batch query
        mock_album1 = AlbumModel(id=album_id1, name="Album 1")
        mock_album2 = AlbumModel(id=album_id2, name="Album 2")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_album1, mock_album2]
        mock_session.execute.return_value = mock_result

        # When: save the photo (update)
        await repo.save(photo)

        # Then: should use batch query for albums, not individual gets
        execute_calls = mock_session.execute.call_args_list
        select_calls = [
            call
            for call in execute_calls
            if "SELECT" in str(call) and "albums" in str(call).lower()
        ]

        # Should have exactly ONE SELECT query for albums
        assert (
            len(select_calls) == 1
        ), f"Expected 1 batch SELECT query for albums during update, got {len(select_calls)}"

    @pytest.mark.asyncio
    async def test_save_handles_missing_albums_gracefully(self):
        """Should handle case where some album IDs don't exist in database."""
        # Given: mock session and photo with album IDs, but only some exist
        mock_session = AsyncMock()
        repo = PhotoRepositoryPostgres(mock_session)

        existing_album_id = uuid4()
        missing_album_id = uuid4()

        photo = Photo.create(
            filename="test.jpg",
            storage_path="/test/test.jpg",
            connector_type=ConnectorType.LOCAL.value,
            connector_id=uuid4(),
        )
        photo.album_ids = [existing_album_id, missing_album_id]

        # Mock existing photo lookup to return None (new photo)
        mock_session.get.return_value = None

        # Mock album batch query - only return one album
        mock_album = AlbumModel(id=existing_album_id, name="Album 1")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_album]
        mock_session.execute.return_value = mock_result

        # When: save the photo
        result = await repo.save(photo)

        # Then: should complete without error and use batch query
        execute_calls = mock_session.execute.call_args_list
        select_calls = [
            call
            for call in execute_calls
            if "SELECT" in str(call) and "albums" in str(call).lower()
        ]

        assert len(select_calls) == 1, "Should still use batch query even with missing albums"
