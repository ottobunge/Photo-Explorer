# Integration Tests

This directory contains integration tests that test the full stack working together.

## Overview

Integration tests verify that multiple components work correctly when integrated:
- Database operations (PostgreSQL)
- Vector store operations (Qdrant)
- File storage operations
- Worker tasks (mocked)
- External APIs (mocked)

## Test Structure

### Fixtures (`conftest.py`)

Provides test fixtures for integration testing:
- `test_db_engine` - Fresh database engine with schema
- `test_session` - Database session with automatic rollback
- `test_file_storage` - Temporary file storage
- `test_vector_store` - Qdrant with unique test collections
- `sample_image_bytes` - Minimal valid JPEG for testing

### Factories (`factories.py`)

Test data factories for creating domain entities:
- `PhotoFactory` - Create Photo entities with sensible defaults
- `AlbumFactory` - Create Album entities
- `FaceFactory` - Create Face entities
- `ConnectorFactory` - Create Connector entities
- `EmbeddingFactory` - Create test embeddings (CLIP, face)

## Test Suites

### 1. Photo Upload and Processing Flow (`test_photo_processing_flow.py`)

Tests the complete photo upload and processing pipeline:
- Upload photo via file storage
- Create photo in database
- Generate thumbnail
- Create embedding in Qdrant
- Detect faces
- Handle processing failures
- Batch processing
- Cascade deletion

**Key Tests:**
- `test_upload_photo_end_to_end` - Full workflow from upload to completion
- `test_photo_with_face_detection` - Photo processing with face detection
- `test_multiple_photos_batch_processing` - Batch processing multiple photos
- `test_photo_deletion_cascade` - Verify cascade deletion of faces and embeddings

### 2. Search Flow (`test_search_flow.py`)

Tests semantic search functionality:
- Index photos with embeddings
- Semantic search by embedding
- Visual similarity search
- Filtering by connector/album
- Ranking by similarity score
- Face similarity search

**Key Tests:**
- `test_index_and_search_photos` - Basic indexing and search
- `test_search_with_similar_embeddings` - Similar photos rank higher
- `test_search_with_filtering_by_connector` - Filter search results
- `test_search_ranking_by_similarity` - Verify proper ranking
- `test_face_similarity_search` - Face clustering via similarity

### 3. Album Management (`test_album_management.py`)

Tests album CRUD operations and photo associations:
- Create album
- Add photos to album
- Remove photos from album
- Delete album
- Cascade behavior
- Cover photo management
- Pagination

**Key Tests:**
- `test_create_album` - Basic album creation
- `test_add_photos_to_album` - Photo-album associations
- `test_remove_photos_from_album` - Remove photos from album
- `test_delete_album` - Album deletion with cascade
- `test_album_cascade_delete_associations` - Junction table cleanup

### 4. Face Detection and Clustering (`test_face_detection_clustering.py`)

Tests face detection and clustering workflows:
- Detect faces in photos
- Store face embeddings
- Cluster similar faces
- Tag faces with person names
- Find photos by face

**Key Tests:**
- `test_detect_and_store_faces` - Face detection workflow
- `test_store_face_embeddings_in_vector_store` - Face embedding storage
- `test_cluster_similar_faces` - Face clustering by similarity
- `test_assign_cluster_to_faces` - Cluster assignment
- `test_find_photos_by_face_cluster` - Find photos containing a person

### 5. Google Photos Sync Flow (`test_google_photos_sync.py`)

Tests Google Photos sync with mocked API:
- Initial sync imports all photos
- Incremental sync adds new photos
- Handle deleted photos
- Update metadata
- Handle pagination
- Rate limiting
- Multiple accounts

**Key Tests:**
- `test_initial_sync_imports_photos` - Full initial sync
- `test_incremental_sync_adds_new_photos` - Only import new photos
- `test_sync_handles_deleted_photos` - Mark deleted photos
- `test_sync_updates_metadata` - Update changed metadata
- `test_sync_handles_api_pagination` - Handle paginated responses

## Running Tests

### Run all integration tests
```bash
pytest backend/tests/integration/ -v
```

### Run specific test suite
```bash
pytest backend/tests/integration/test_photo_processing_flow.py -v
pytest backend/tests/integration/test_search_flow.py -v
pytest backend/tests/integration/test_album_management.py -v
pytest backend/tests/integration/test_face_detection_clustering.py -v
pytest backend/tests/integration/test_google_photos_sync.py -v
```

### Run specific test
```bash
pytest backend/tests/integration/test_photo_processing_flow.py::TestPhotoUploadAndProcessingFlow::test_upload_photo_end_to_end -v
```

### Run with coverage
```bash
pytest backend/tests/integration/ --cov=app --cov-report=html
```

## Test Database

Tests use either:
1. In-memory SQLite (default, fast, no setup)
2. Test PostgreSQL database (set `TEST_DATABASE_URL` env var)

Example test database URL:
```bash
export TEST_DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/photo_explorer_test"
```

## Test Vector Store

Tests create unique Qdrant collections for each test run to avoid conflicts:
- Collection names: `test_photos_{uuid}` and `test_faces_{uuid}`
- Automatically cleaned up after each test

Requires Qdrant running:
```bash
docker run -p 6333:6333 qdrant/qdrant
```

## Test File Storage

Tests use temporary directories that are automatically cleaned up:
- Photos: `{tmpdir}/photos/`
- Thumbnails: `{tmpdir}/thumbnails/`
- Faces: `{tmpdir}/faces/`

## Mocking Strategy

### External APIs (Google Photos)
- Mock with `MockGooglePhotosItem` class
- Simulates API responses without real HTTP calls
- Tests sync logic without API dependencies

### ML Services (Face Detection, Embeddings)
- Use `EmbeddingFactory` to create test embeddings
- Mock ML service calls when needed
- Focus on data flow, not ML accuracy

### Worker Tasks
- Test database/storage operations directly
- Mock Celery task execution
- Verify task logic without async workers running

## Best Practices

1. **Isolation**: Each test is independent, no shared state
2. **Cleanup**: All fixtures clean up automatically
3. **Fast**: Use in-memory SQLite when possible
4. **Realistic**: Use real database operations, not mocks
5. **Comprehensive**: Test happy path and error cases
6. **Readable**: Clear test names and comments

## Test Data

### Sample Image
Tests use a minimal valid JPEG (1x1 pixel) from `sample_image_bytes` fixture.

### Embeddings
- CLIP embeddings: 768-dimensional (configurable)
- Face embeddings: 512-dimensional (InsightFace)
- Normalized vectors for cosine similarity

### Factories
Use factories to create test data:
```python
# Create photo
photo = PhotoFactory.create(filename="test.jpg")

# Create batch
photos = PhotoFactory.create_batch(5)

# Create with custom values
photo = PhotoFactory.create(
    filename="custom.jpg",
    width=3840,
    height=2160,
)
```

## Coverage Goals

Integration tests aim for:
- 90%+ coverage of repository implementations
- 100% coverage of critical workflows (upload, sync, search)
- All cascade behaviors tested
- All error paths tested

## Troubleshooting

### Tests fail with "collection not found"
- Ensure Qdrant is running on port 6333
- Check `QDRANT_URL` environment variable

### Tests fail with database errors
- Check PostgreSQL is running (if using test DB)
- Verify `TEST_DATABASE_URL` is correct
- Ensure test database exists and is accessible

### Tests timeout
- Increase pytest timeout: `pytest --timeout=300`
- Check for hanging async operations
- Verify cleanup is happening

### Memory issues
- Tests create temporary files - ensure disk space
- Vector store collections are cleaned up
- Database sessions are properly closed

## Future Improvements

1. Add tests for:
   - Concurrent operations
   - Large-scale batch processing
   - Performance benchmarks
   - Error recovery scenarios

2. Add Docker Compose for test dependencies:
   - PostgreSQL
   - Qdrant
   - Redis

3. Add integration with CI/CD:
   - Automated test runs
   - Coverage reporting
   - Performance regression detection

4. Add more external service mocks:
   - OAuth providers
   - Cloud storage (S3, GCS)
   - CDN services
