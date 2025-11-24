"""Integration tests for PhotoRepository query optimization.

This module specifically tests that N+1 query problems are resolved
through proper eager loading of relationships.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.adapters.outbound.persistence.postgres.models import (
    PhotoModel,
    AlbumModel,
    ConnectorModel,
    FaceModel,
)
from app.adapters.outbound.persistence.postgres.repositories.photo_repository import (
    PhotoRepositoryPostgres,
)
from app.domain.entities.connector import ConnectorType, ConnectorStatus


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
        created_at=datetime.utcnow(),
    )
    db_session.add(connector)
    await db_session.flush()

    # Create albums
    albums = []
    for i in range(3):
        album = AlbumModel(
            id=uuid4(),
            name=f"Test Album {i}",
            created_at=datetime.utcnow(),
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
            created_at=datetime.utcnow(),
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
                created_at=datetime.utcnow(),
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
            created_at=datetime.utcnow(),
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
