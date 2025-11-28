"""Unit tests for PhotoRepository connector-related queries.

Tests for querying photos by connector, counting photos per connector, etc.
Following TDD approach.
"""


import pytest

from app.domain.entities.connector import Connector, ConnectorType
from app.domain.entities.photo import Photo


class TestPhotoRepositoryFindByConnector:
    """Tests for finding photos by connector ID."""

    @pytest.mark.asyncio
    async def test_find_by_connector_returns_empty_when_no_photos(self, photo_repo, connector_repo):
        """Should return empty list when connector has no photos."""
        # Given: connector with no photos
        connector = Connector.create_upload(upload_path="/uploads")
        saved_connector = await connector_repo.save(connector)

        # When
        result = await photo_repo.find_by_connector(saved_connector.id.value, limit=20, offset=0)

        # Then
        assert result == []

    @pytest.mark.asyncio
    async def test_find_by_connector_returns_matching_photos(self, photo_repo, connector_repo):
        """Should return only photos from specified connector."""
        # Given: 2 connectors with photos
        connector1 = Connector.create_upload(upload_path="/uploads")
        connector2 = Connector.create_local(path="/photos", name="Local")

        saved_c1 = await connector_repo.save(connector1)
        saved_c2 = await connector_repo.save(connector2)

        # Photos from connector 1
        photo1 = Photo.create(
            filename="upload1.jpg",
            storage_path="/uploads/upload1.jpg",
            connector_type=ConnectorType.UPLOAD.value,
            connector_id=saved_c1.id.value,
        )
        photo2 = Photo.create(
            filename="upload2.jpg",
            storage_path="/uploads/upload2.jpg",
            connector_type=ConnectorType.UPLOAD.value,
            connector_id=saved_c1.id.value,
        )

        # Photo from connector 2
        photo3 = Photo.create(
            filename="local1.jpg",
            storage_path="/photos/local1.jpg",
            connector_type=ConnectorType.LOCAL.value,
            connector_id=saved_c2.id.value,
        )

        await photo_repo.save(photo1)
        await photo_repo.save(photo2)
        await photo_repo.save(photo3)

        # When: query connector 1
        result = await photo_repo.find_by_connector(saved_c1.id.value, limit=20, offset=0)

        # Then: only photos from connector 1
        assert len(result) == 2
        filenames = {p.filename for p in result}
        assert filenames == {"upload1.jpg", "upload2.jpg"}
        assert all(p.connector_id == saved_c1.id.value for p in result)

    @pytest.mark.asyncio
    async def test_find_by_connector_paginates_correctly(self, photo_repo, connector_repo):
        """Should respect limit and offset for pagination."""
        # Given: connector with 5 photos
        connector = Connector.create_upload(upload_path="/uploads")
        saved_connector = await connector_repo.save(connector)

        # Create 5 photos
        for i in range(5):
            photo = Photo.create(
                filename=f"photo{i}.jpg",
                storage_path=f"/uploads/photo{i}.jpg",
                connector_type=ConnectorType.UPLOAD.value,
                connector_id=saved_connector.id.value,
            )
            await photo_repo.save(photo)

        # When: first page (limit 2)
        page1 = await photo_repo.find_by_connector(saved_connector.id.value, limit=2, offset=0)

        # Then
        assert len(page1) == 2

        # When: second page
        page2 = await photo_repo.find_by_connector(saved_connector.id.value, limit=2, offset=2)

        # Then
        assert len(page2) == 2

        # When: third page
        page3 = await photo_repo.find_by_connector(saved_connector.id.value, limit=2, offset=4)

        # Then
        assert len(page3) == 1

        # Ensure no overlap
        page1_ids = {p.id.value for p in page1}
        page2_ids = {p.id.value for p in page2}
        page3_ids = {p.id.value for p in page3}

        assert len(page1_ids & page2_ids) == 0
        assert len(page2_ids & page3_ids) == 0

    @pytest.mark.asyncio
    async def test_find_by_connector_handles_deleted_connector(self, photo_repo, connector_repo):
        """Should handle case where connector was deleted (photos orphaned)."""
        # Given: connector with photos, then deleted
        connector = Connector.create_upload(upload_path="/uploads")
        saved_connector = await connector_repo.save(connector)

        photo = Photo.create(
            filename="test.jpg",
            storage_path="/uploads/test.jpg",
            connector_type=ConnectorType.UPLOAD.value,
            connector_id=saved_connector.id.value,
        )
        await photo_repo.save(photo)

        # Delete connector (sets photos.connector_id = NULL)
        await connector_repo.delete(saved_connector.id.value)

        # When: try to find photos by deleted connector ID
        result = await photo_repo.find_by_connector(saved_connector.id.value, limit=20, offset=0)

        # Then: no photos returned (connector_id is NULL)
        assert result == []

    @pytest.mark.asyncio
    async def test_find_by_connector_empty_result_when_no_photos(self, photo_repo, connector_repo):
        """Should return empty list for connector with zero photos."""
        # Given: connector with no photos
        connector = Connector.create_local(path="/photos", name="Empty")
        saved_connector = await connector_repo.save(connector)

        # When
        result = await photo_repo.find_by_connector(saved_connector.id.value, limit=20, offset=0)

        # Then
        assert result == []
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_find_by_connector_orders_by_created_at_desc(self, photo_repo, connector_repo):
        """Should return photos ordered by created_at descending (newest first)."""
        # Given: connector with photos created at different times
        connector = Connector.create_upload(upload_path="/uploads")
        saved_connector = await connector_repo.save(connector)

        from datetime import datetime, timedelta

        # Create photos with different timestamps
        for i in range(3):
            photo = Photo.create(
                filename=f"photo{i}.jpg",
                storage_path=f"/uploads/photo{i}.jpg",
                connector_type=ConnectorType.UPLOAD.value,
                connector_id=saved_connector.id.value,
            )
            # Manually set created_at to ensure order
            photo.created_at = datetime.utcnow() - timedelta(days=i)
            await photo_repo.save(photo)

        # When
        result = await photo_repo.find_by_connector(saved_connector.id.value, limit=20, offset=0)

        # Then: ordered by created_at descending
        assert len(result) == 3
        assert result[0].filename == "photo0.jpg"  # Newest
        assert result[1].filename == "photo1.jpg"
        assert result[2].filename == "photo2.jpg"  # Oldest


class TestPhotoRepositoryCountByConnector:
    """Tests for counting photos by connector."""

    @pytest.mark.asyncio
    async def test_count_by_connector_returns_zero_when_no_photos(self, photo_repo, connector_repo):
        """Should return 0 when connector has no photos."""
        # Given: empty connector
        connector = Connector.create_upload(upload_path="/uploads")
        saved_connector = await connector_repo.save(connector)

        # When
        count = await photo_repo.count_by_connector(saved_connector.id.value)

        # Then
        assert count == 0

    @pytest.mark.asyncio
    async def test_count_by_connector_returns_accurate_count(self, photo_repo, connector_repo):
        """Should return exact count of photos for connector."""
        # Given: connector with 3 photos
        connector = Connector.create_local(path="/photos", name="Test")
        saved_connector = await connector_repo.save(connector)

        for i in range(3):
            photo = Photo.create(
                filename=f"photo{i}.jpg",
                storage_path=f"/photos/photo{i}.jpg",
                connector_type=ConnectorType.LOCAL.value,
                connector_id=saved_connector.id.value,
            )
            await photo_repo.save(photo)

        # When
        count = await photo_repo.count_by_connector(saved_connector.id.value)

        # Then
        assert count == 3

    @pytest.mark.asyncio
    async def test_count_by_connector_only_counts_matching_connector(
        self, photo_repo, connector_repo
    ):
        """Should not count photos from other connectors."""
        # Given: 2 connectors with photos
        connector1 = Connector.create_upload(upload_path="/uploads")
        connector2 = Connector.create_local(path="/photos", name="Local")

        saved_c1 = await connector_repo.save(connector1)
        saved_c2 = await connector_repo.save(connector2)

        # 2 photos in connector 1
        for i in range(2):
            photo = Photo.create(
                filename=f"upload{i}.jpg",
                storage_path=f"/uploads/upload{i}.jpg",
                connector_type=ConnectorType.UPLOAD.value,
                connector_id=saved_c1.id.value,
            )
            await photo_repo.save(photo)

        # 5 photos in connector 2
        for i in range(5):
            photo = Photo.create(
                filename=f"local{i}.jpg",
                storage_path=f"/photos/local{i}.jpg",
                connector_type=ConnectorType.LOCAL.value,
                connector_id=saved_c2.id.value,
            )
            await photo_repo.save(photo)

        # When: count connector 1
        count1 = await photo_repo.count_by_connector(saved_c1.id.value)
        count2 = await photo_repo.count_by_connector(saved_c2.id.value)

        # Then
        assert count1 == 2
        assert count2 == 5

    @pytest.mark.asyncio
    async def test_count_by_connector_handles_deleted_connector(self, photo_repo, connector_repo):
        """Should return 0 for deleted connector (orphaned photos)."""
        # Given: connector with photos, then deleted
        connector = Connector.create_upload(upload_path="/uploads")
        saved_connector = await connector_repo.save(connector)

        photo = Photo.create(
            filename="test.jpg",
            storage_path="/uploads/test.jpg",
            connector_type=ConnectorType.UPLOAD.value,
            connector_id=saved_connector.id.value,
        )
        await photo_repo.save(photo)

        # Delete connector
        await connector_repo.delete(saved_connector.id.value)

        # When
        count = await photo_repo.count_by_connector(saved_connector.id.value)

        # Then: 0 because photo.connector_id is NULL
        assert count == 0


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
