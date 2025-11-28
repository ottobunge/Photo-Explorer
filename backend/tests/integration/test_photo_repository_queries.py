"""Integration tests for PhotoRepository query optimization.

This module specifically tests that N+1 query problems are resolved
through proper eager loading of relationships.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.adapters.outbound.persistence.postgres.models import (
    AlbumModel,
    ConnectorModel,
    FaceModel,
    PhotoModel,
)
from app.adapters.outbound.persistence.postgres.repositories.photo_repository import (
    PhotoRepositoryPostgres,
)
from app.domain.entities.connector import ConnectorStatus, ConnectorType


class QueryCounter:
    """Helper to count SQL queries executed."""

    def __init__(self):
        self.count = 0
        self.queries = []

    def reset(self):
        """Reset the counter."""
        self.count = 0
        self.queries = []

    def callback(self, conn, cursor, statement, parameters, context, executemany):
        """SQLAlchemy event callback to count queries."""
        self.count += 1
        self.queries.append(statement)


@pytest.fixture
def query_counter(db_session):
    """Fixture that provides query counting functionality."""
    counter = QueryCounter()
    event.listen(Engine, "before_cursor_execute", counter.callback)
    yield counter
    event.remove(Engine, "before_cursor_execute", counter.callback)


@pytest.fixture
async def sample_data(db_session):
    """Create sample data for testing."""
    # Create connector
    connector = ConnectorModel(
        id=uuid4(),
        type=ConnectorType.GOOGLE_PHOTOS,
        name="Test Connector",
        enabled=True,
        status=ConnectorStatus.CONNECTED,
        config={},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(connector)
    await db_session.flush()

    # Create albums
    albums = []
    for i in range(3):
        album = AlbumModel(
            id=uuid4(),
            name=f"Test Album {i}",
            created_at=datetime.now(timezone.utc),
        )
        albums.append(album)
        db_session.add(album)

    await db_session.flush()

    # Create photos with relationships
    photos = []
    for i in range(5):
        photo = PhotoModel(
            id=uuid4(),
            filename=f"photo_{i}.jpg",
            created_at=datetime.now(timezone.utc),
            connector_type="google_photos",
            connector_id=connector.id,
            external_id=f"external_{i}",
            mime_type="image/jpeg",
            processing_status="completed",
        )

        # Add album associations
        photo.albums = [albums[i % 3]]

        # Add faces
        for j in range(2):
            face = FaceModel(
                id=uuid4(),
                photo_id=photo.id,
                bbox_x=0.1,
                bbox_y=0.1,
                bbox_width=0.2,
                bbox_height=0.2,
                created_at=datetime.now(timezone.utc),
            )
            photo.faces.append(face)

        photos.append(photo)
        db_session.add(photo)

    await db_session.flush()
    await db_session.commit()

    return {
        "connector": connector,
        "albums": albums,
        "photos": photos,
    }


@pytest.mark.asyncio
async def test_find_by_id_no_n_plus_1(db_session, sample_data, query_counter):
    """Test that find_by_id uses eager loading to avoid N+1 queries."""
    repo = PhotoRepositoryPostgres(db_session)
    photo_id = sample_data["photos"][0].id

    # Clear session to force fresh queries
    db_session.expunge_all()
    query_counter.reset()

    # Execute find_by_id
    result = await repo.find_by_id(photo_id)

    # Should execute:
    # 1. SELECT for the photo with eager loading
    # 2. SELECT for albums (via selectinload)
    # 3. SELECT for faces (via selectinload)
    # 4. SELECT for connector (via selectinload)
    # Total: ~4 queries max (not N+1)
    assert query_counter.count <= 4, (
        f"Expected at most 4 queries, got {query_counter.count}. "
        f"This indicates N+1 query problem. Queries: {query_counter.queries}"
    )
    assert result is not None
    assert result.id.value == photo_id


@pytest.mark.asyncio
async def test_find_all_no_n_plus_1(db_session, sample_data, query_counter):
    """Test that find_all uses eager loading to avoid N+1 queries."""
    repo = PhotoRepositoryPostgres(db_session)

    # Clear session to force fresh queries
    db_session.expunge_all()
    query_counter.reset()

    # Execute find_all
    results = await repo.find_all(limit=10)

    # Should execute:
    # 1. SELECT for photos
    # 2. SELECT for all albums (via selectinload)
    # 3. SELECT for all faces (via selectinload)
    # 4. SELECT for all connectors (via selectinload)
    # Total: ~4 queries regardless of number of photos (not N+1)
    assert query_counter.count <= 4, (
        f"Expected at most 4 queries, got {query_counter.count}. "
        f"This indicates N+1 query problem. Queries: {query_counter.queries}"
    )
    assert len(results) == 5


@pytest.mark.asyncio
async def test_find_by_connector_no_n_plus_1(db_session, sample_data, query_counter):
    """Test that find_by_connector uses eager loading to avoid N+1 queries."""
    repo = PhotoRepositoryPostgres(db_session)
    connector_id = sample_data["connector"].id

    # Clear session to force fresh queries
    db_session.expunge_all()
    query_counter.reset()

    # Execute find_by_connector
    results = await repo.find_by_connector(connector_id)

    # Should execute:
    # 1. SELECT for photos filtered by connector
    # 2. SELECT for all albums (via selectinload)
    # 3. SELECT for all faces (via selectinload)
    # 4. SELECT for connector (via selectinload)
    # Total: ~4 queries regardless of number of photos
    assert query_counter.count <= 4, (
        f"Expected at most 4 queries, got {query_counter.count}. "
        f"This indicates N+1 query problem. Queries: {query_counter.queries}"
    )
    assert len(results) == 5


@pytest.mark.asyncio
async def test_find_pending_processing_no_n_plus_1(db_session, sample_data, query_counter):
    """Test that find_pending_processing uses eager loading to avoid N+1 queries."""
    # Create pending photos
    for i in range(3):
        photo = PhotoModel(
            id=uuid4(),
            filename=f"pending_{i}.jpg",
            created_at=datetime.now(timezone.utc),
            connector_type="local",
            mime_type="image/jpeg",
            processing_status="pending",
        )
        db_session.add(photo)

    await db_session.flush()
    await db_session.commit()

    repo = PhotoRepositoryPostgres(db_session)

    # Clear session to force fresh queries
    db_session.expunge_all()
    query_counter.reset()

    # Execute find_pending_processing
    results = await repo.find_pending_processing()

    # Should execute:
    # 1. SELECT for pending photos
    # 2. SELECT for albums (via selectinload)
    # 3. SELECT for faces (via selectinload)
    # 4. SELECT for connectors (via selectinload)
    # Total: ~4 queries regardless of number of photos
    assert query_counter.count <= 4, (
        f"Expected at most 4 queries, got {query_counter.count}. "
        f"This indicates N+1 query problem. Queries: {query_counter.queries}"
    )
    assert len(results) >= 3


@pytest.mark.asyncio
async def test_find_by_external_id_no_n_plus_1(db_session, sample_data, query_counter):
    """Test that find_by_external_id uses eager loading to avoid N+1 queries."""
    repo = PhotoRepositoryPostgres(db_session)
    connector_id = sample_data["connector"].id

    # Clear session to force fresh queries
    db_session.expunge_all()
    query_counter.reset()

    # Execute find_by_external_id
    result = await repo.find_by_external_id("external_0", connector_id)

    # Should execute at most 4 queries (main + 3 eager loads)
    assert query_counter.count <= 4, (
        f"Expected at most 4 queries, got {query_counter.count}. "
        f"This indicates N+1 query problem. Queries: {query_counter.queries}"
    )
    assert result is not None


@pytest.mark.asyncio
async def test_find_by_original_path_no_n_plus_1(db_session, sample_data, query_counter):
    """Test that find_by_original_path uses eager loading to avoid N+1 queries."""
    # Update one photo with source_path
    photo = sample_data["photos"][0]
    photo.source_path = "/test/path/photo_0.jpg"
    await db_session.flush()
    await db_session.commit()

    repo = PhotoRepositoryPostgres(db_session)

    # Clear session to force fresh queries
    db_session.expunge_all()
    query_counter.reset()

    # Execute find_by_original_path
    result = await repo.find_by_original_path("/test/path/photo_0.jpg")

    # Should execute at most 4 queries (main + 3 eager loads)
    assert query_counter.count <= 4, (
        f"Expected at most 4 queries, got {query_counter.count}. "
        f"This indicates N+1 query problem. Queries: {query_counter.queries}"
    )
    assert result is not None


@pytest.mark.asyncio
async def test_access_relationships_without_additional_queries(db_session, sample_data):
    """Test that accessing relationships doesn't trigger additional queries."""
    repo = PhotoRepositoryPostgres(db_session)
    photo_id = sample_data["photos"][0].id

    # Clear session and get photo
    db_session.expunge_all()
    result = await repo.find_by_id(photo_id)

    # Now create a new session to ensure we're testing lazy loading
    db_session.expunge_all()

    # Access relationships - should already be loaded
    # If these trigger queries, it means eager loading is not working
    assert result is not None

    # The domain entity should have all data loaded
    # This is verified by the mapper which accesses the relationships
    assert result.connector_id is not None
    assert result.album_ids is not None
    assert isinstance(result.album_ids, list)


@pytest.mark.asyncio
async def test_save_photo_with_albums_efficient_query(db_session, query_counter):
    """Test that saving a photo with multiple albums uses efficient batch query.

    This is the integration test for the N+1 query fix in album associations.
    Should use single batch SELECT for all albums, not N individual queries.
    """
    from app.domain.entities.photo import Photo

    # Given: Create some albums in database
    albums = []
    album_ids = []
    for i in range(5):
        album = AlbumModel(
            id=uuid4(),
            name=f"Test Album {i}",
            created_at=datetime.now(timezone.utc),
        )
        albums.append(album)
        album_ids.append(album.id)
        db_session.add(album)

    await db_session.flush()
    await db_session.commit()

    # Create connector
    connector = ConnectorModel(
        id=uuid4(),
        type=ConnectorType.LOCAL,
        name="Test Connector",
        enabled=True,
        status=ConnectorStatus.CONNECTED,
        config={"path": "/test"},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(connector)
    await db_session.flush()
    await db_session.commit()

    repo = PhotoRepositoryPostgres(db_session)

    # Create photo with multiple album associations
    photo = Photo.create(
        filename="test.jpg",
        storage_path="/test/test.jpg",
        connector_type=ConnectorType.LOCAL.value,
        connector_id=connector.id,
    )
    photo.album_ids = album_ids

    # Clear session to force fresh queries
    db_session.expunge_all()
    query_counter.reset()

    # When: save the photo
    result = await repo.save(photo)

    # Then: Should execute efficient queries:
    # 1. GET PhotoModel by ID (check if exists)
    # 2. DELETE existing associations
    # 3. SELECT albums in batch (NOT 5 individual SELECTs)
    # 4. INSERT photo
    # 5. FLUSH/other housekeeping
    # Total: Should be around 5-7 queries, NOT 5 + number_of_albums

    # The key assertion: query count should NOT scale with number of albums
    # With N+1 bug: would be ~10+ queries (1 per album + overhead)
    # With fix: should be ~7 queries regardless of album count
    assert query_counter.count <= 8, (
        f"Expected at most 8 queries for saving photo with 5 albums, got {query_counter.count}. "
        f"This indicates N+1 query problem where each album triggers a separate query. "
        f"Queries executed: {query_counter.queries}"
    )

    # Verify the photo was saved with all album associations
    assert result is not None
    assert len(result.album_ids) == 5
    assert set(result.album_ids) == set(album_ids)


@pytest.mark.asyncio
async def test_save_photo_with_10_albums_query_count_constant(db_session, query_counter):
    """Test that query count doesn't increase linearly with number of albums.

    This test verifies that the batch query optimization works correctly
    by ensuring query count stays constant regardless of album count.
    """
    from app.domain.entities.photo import Photo

    # Given: Create 10 albums in database
    albums = []
    album_ids = []
    for i in range(10):
        album = AlbumModel(
            id=uuid4(),
            name=f"Test Album {i}",
            created_at=datetime.now(timezone.utc),
        )
        albums.append(album)
        album_ids.append(album.id)
        db_session.add(album)

    await db_session.flush()
    await db_session.commit()

    # Create connector
    connector = ConnectorModel(
        id=uuid4(),
        type=ConnectorType.LOCAL,
        name="Test Connector",
        enabled=True,
        status=ConnectorStatus.CONNECTED,
        config={"path": "/test"},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(connector)
    await db_session.flush()
    await db_session.commit()

    repo = PhotoRepositoryPostgres(db_session)

    # Create photo with 10 album associations
    photo = Photo.create(
        filename="test_10.jpg",
        storage_path="/test/test_10.jpg",
        connector_type=ConnectorType.LOCAL.value,
        connector_id=connector.id,
    )
    photo.album_ids = album_ids

    # Clear session to force fresh queries
    db_session.expunge_all()
    query_counter.reset()

    # When: save the photo
    result = await repo.save(photo)

    # Then: Query count should still be similar to 5 albums case
    # Should NOT be 10+ queries higher
    assert query_counter.count <= 8, (
        f"Expected at most 8 queries for saving photo with 10 albums, got {query_counter.count}. "
        f"Query count should not scale with number of albums. "
        f"Queries executed: {query_counter.queries}"
    )

    # Verify the photo was saved with all album associations
    assert result is not None
    assert len(result.album_ids) == 10
    assert set(result.album_ids) == set(album_ids)


@pytest.mark.asyncio
async def test_bulk_delete_removes_photos_from_db(db_session, sample_data):
    """Test that bulk delete actually removes photos from database."""
    repo = PhotoRepositoryPostgres(db_session)

    # Get photo IDs to delete
    photo_ids = [
        sample_data["photos"][0].id,
        sample_data["photos"][1].id,
        sample_data["photos"][2].id,
    ]

    # Verify photos exist before deletion
    for photo_id in photo_ids:
        photo = await repo.find_by_id(photo_id)
        assert photo is not None

    # When: delete_many is called
    deleted_count = await repo.delete_many(photo_ids)
    await db_session.commit()

    # Then: should return correct count
    assert deleted_count == 3

    # Verify photos are actually deleted
    for photo_id in photo_ids:
        photo = await repo.find_by_id(photo_id)
        assert photo is None

    # Verify other photos still exist
    remaining_photo = await repo.find_by_id(sample_data["photos"][3].id)
    assert remaining_photo is not None


@pytest.mark.asyncio
async def test_bulk_delete_cascades_to_faces(db_session, sample_data):
    """Test that bulk delete cascades to related faces."""
    from sqlalchemy import select

    from app.adapters.outbound.persistence.postgres.models import FaceModel

    repo = PhotoRepositoryPostgres(db_session)

    # Get a photo ID that has faces
    photo_id = sample_data["photos"][0].id

    # Verify the photo has faces before deletion
    stmt = select(FaceModel).where(FaceModel.photo_id == photo_id)
    result = await db_session.execute(stmt)
    faces_before = result.scalars().all()
    assert len(faces_before) > 0, "Photo should have faces for this test"

    # When: delete_many is called
    deleted_count = await repo.delete_many([photo_id])
    await db_session.commit()

    # Then: should delete the photo
    assert deleted_count == 1

    # Verify faces are also deleted (cascade)
    stmt = select(FaceModel).where(FaceModel.photo_id == photo_id)
    result = await db_session.execute(stmt)
    faces_after = result.scalars().all()
    assert len(faces_after) == 0, "Faces should be cascade deleted"


@pytest.mark.asyncio
async def test_bulk_delete_in_transaction(db_session, sample_data):
    """Test that bulk delete works correctly within a transaction."""
    repo = PhotoRepositoryPostgres(db_session)

    # Get photo IDs
    photo_ids = [sample_data["photos"][0].id, sample_data["photos"][1].id]

    # When: delete_many is called without commit
    deleted_count = await repo.delete_many(photo_ids)

    # Then: should return correct count
    assert deleted_count == 2

    # Photos should be deleted in current transaction
    for photo_id in photo_ids:
        photo = await repo.find_by_id(photo_id)
        assert photo is None

    # Rollback the transaction
    await db_session.rollback()

    # After rollback, photos should still exist
    for photo_id in photo_ids:
        photo = await repo.find_by_id(photo_id)
        assert photo is not None, "Photos should still exist after rollback"


@pytest.mark.asyncio
async def test_bulk_delete_with_empty_list(db_session, sample_data):
    """Test that bulk delete handles empty list gracefully."""
    repo = PhotoRepositoryPostgres(db_session)

    # When: delete_many is called with empty list
    deleted_count = await repo.delete_many([])

    # Then: should return 0
    assert deleted_count == 0

    # All photos should still exist
    all_photos = await repo.find_all(limit=100)
    assert len(all_photos) == 5


@pytest.mark.asyncio
async def test_bulk_delete_with_non_existent_ids(db_session, sample_data):
    """Test that bulk delete handles non-existent IDs gracefully."""
    repo = PhotoRepositoryPostgres(db_session)

    # Mix of existing and non-existent IDs
    existing_id = sample_data["photos"][0].id
    non_existent_id1 = uuid4()
    non_existent_id2 = uuid4()

    # When: delete_many is called with mix of IDs
    deleted_count = await repo.delete_many([existing_id, non_existent_id1, non_existent_id2])
    await db_session.commit()

    # Then: should return count of actually deleted rows (1)
    assert deleted_count == 1

    # Verify only the existing photo was deleted
    photo = await repo.find_by_id(existing_id)
    assert photo is None


@pytest.mark.asyncio
async def test_bulk_delete_performs_single_query(db_session, sample_data, query_counter):
    """Test that bulk delete uses single DELETE query, not N queries."""
    repo = PhotoRepositoryPostgres(db_session)

    # Get multiple photo IDs
    photo_ids = [photo.id for photo in sample_data["photos"][:4]]

    # Clear session and reset counter
    db_session.expunge_all()
    query_counter.reset()

    # When: delete_many is called
    await repo.delete_many(photo_ids)

    # Then: should execute at most 2 queries (DELETE + possibly housekeeping)
    # Not N individual DELETE queries
    assert query_counter.count <= 2, (
        f"Expected at most 2 queries for bulk delete of {len(photo_ids)} photos, "
        f"got {query_counter.count}. This indicates N+1 query problem. "
        f"Queries: {query_counter.queries}"
    )

    # Verify at least one query was a DELETE
    delete_queries = [q for q in query_counter.queries if "DELETE" in q.upper()]
    assert len(delete_queries) >= 1, "Should have executed at least one DELETE query"


@pytest.mark.asyncio
async def test_bulk_delete_large_batch(db_session):
    """Test that bulk delete can handle a large batch of photos efficiently."""
    from app.domain.entities.connector import ConnectorType
    from app.domain.entities.photo import Photo

    # Create a connector first
    connector = ConnectorModel(
        id=uuid4(),
        type=ConnectorType.LOCAL,
        name="Test Connector",
        enabled=True,
        status=ConnectorStatus.CONNECTED,
        config={"path": "/test"},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(connector)
    await db_session.flush()

    # Create 100 photos
    photo_ids = []
    repo = PhotoRepositoryPostgres(db_session)

    for i in range(100):
        photo = Photo.create(
            filename=f"bulk_test_{i}.jpg",
            storage_path=f"/test/bulk_test_{i}.jpg",
            connector_type=ConnectorType.LOCAL.value,
            connector_id=connector.id,
        )
        saved_photo = await repo.save(photo)
        photo_ids.append(saved_photo.id.value)

    await db_session.commit()

    # When: delete_many is called with large batch
    deleted_count = await repo.delete_many(photo_ids)
    await db_session.commit()

    # Then: should delete all 100 photos
    assert deleted_count == 100

    # Verify all photos are deleted
    for photo_id in photo_ids:
        photo = await repo.find_by_id(photo_id)
        assert photo is None
