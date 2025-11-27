# E2E Tests

End-to-end tests for Photo Explorer backend.

## Overview

E2E tests verify complete workflows from API request to database storage to file system operations. These tests use real infrastructure (PostgreSQL, Qdrant) running in Docker containers.

## Running E2E Tests

### Prerequisites

1. Docker or Podman running
2. Test infrastructure started:
   ```bash
   docker-compose -f docker-compose.test.yml up -d
   ```

### Run All E2E Tests

```bash
cd backend
poetry run pytest tests/e2e/ -v
```

### Run Specific Test File

```bash
poetry run pytest tests/e2e/test_photo_upload_flow.py -v
```

### Run Specific Test

```bash
poetry run pytest tests/e2e/test_photo_upload_flow.py::TestPhotoUploadFlow::test_upload_photo_creates_storage_file -v
```

### Run with Coverage

```bash
poetry run pytest tests/e2e/ -v --cov=app --cov-report=html
```

## Test Organization

### `test_photo_upload_flow.py`

Complete upload workflow testing:
- ✅ Photo upload and storage
- ✅ Multiple file upload
- ✅ File retrieval via API
- ✅ Photo deletion and cleanup
- ✅ Error handling (non-images, empty files)
- ⏭️ Thumbnail generation (requires worker)
- ⏭️ Face detection (requires worker)

### `test_google_photos_sync.py`

Google Photos connector testing:
- Google Photos API authentication
- Photo sync workflow
- Metadata extraction
- Picker API integration

### Other E2E Tests

- `test_photo_api.py` - Photo API endpoints
- `test_photo_processing_flow.py` - Processing workflows
- `test_face_detection_workflow.py` - Face detection flows

## Worker-Dependent Tests

Some tests require Celery worker to be running and are **skipped by default**:

- `test_upload_triggers_thumbnail_generation` - Verifies thumbnail generation
- `test_upload_triggers_face_detection` - Verifies face detection
- `test_photo_with_face_detection` - Full face workflow

### Running Worker Tests

1. Start worker in test mode:
   ```bash
   TESTING=1 poetry run celery -A app.adapters.inbound.workers.celery_app worker --loglevel=info
   ```

2. Run tests without skip:
   ```bash
   poetry run pytest tests/e2e/test_photo_upload_flow.py -v -m "not skip"
   ```

Or enable specific skipped test:
```bash
poetry run pytest tests/e2e/test_photo_upload_flow.py::TestPhotoUploadFlow::test_upload_triggers_thumbnail_generation -v --run-skipped
```

## Test Fixtures

### Image Fixtures

Located in `backend/tests/fixtures/`:
- `hopper.jpg` - 128x128 test image with a person (for face detection tests)

### Pytest Fixtures

Defined in `conftest.py`:
- `client` - Async HTTP client for API testing
- `sample_image_bytes` - Programmatically generated test image
- `sample_image_with_face` - Test image with faces for detection

## Best Practices

### 1. Test Real Workflows

E2E tests should test **complete user workflows**, not just individual endpoints:

```python
async def test_upload_and_search_workflow(client):
    # Upload photo
    # Wait for indexing
    # Search for photo
    # Verify photo appears in results
```

### 2. Verify Side Effects

Check that operations have the expected side effects:

```python
# Verify file exists on disk
file_storage = LocalFileStorage()
assert await file_storage.get_file(storage_path) is not None

# Verify database record
response = await client.get(f"/photos/{photo_id}")
assert response.json()["data"]["storage_path"] == storage_path
```

### 3. Test Error Handling

Verify error cases:

```python
async def test_upload_rejects_non_image_file(client):
    response = await client.post("/photos/upload", ...)
    assert "Invalid file type" in response.json()["data"]["failed"][0]["error"]
```

### 4. Clean Up

Tests should clean up resources:

```python
async def test_upload_and_delete(client):
    # Upload
    photo_id = ...

    # Test
    ...

    # Clean up
    await client.delete(f"/photos/{photo_id}")
```

### 5. Use Descriptive Names

Test names should describe the workflow:
- ✅ `test_upload_photo_creates_storage_file`
- ✅ `test_upload_triggers_thumbnail_generation`
- ❌ `test_photo_upload`
- ❌ `test_api`

## Adding New E2E Tests

1. **Create test file** in `tests/e2e/`
2. **Use async test class**:
   ```python
   @pytest.mark.asyncio
   class TestMyWorkflow:
       async def test_complete_flow(self, client):
           # Test implementation
   ```

3. **Test complete workflows**, not just endpoints
4. **Verify side effects** (database, files, vector store)
5. **Document test purpose** in docstring
6. **Mark worker-dependent tests** with `@pytest.mark.skip`

## Debugging Failed Tests

### View Test Output

```bash
pytest tests/e2e/test_photo_upload_flow.py -v -s
```

### Check Docker Logs

```bash
docker-compose -f docker-compose.test.yml logs postgres
docker-compose -f docker-compose.test.yml logs qdrant
```

### Inspect Test Database

```bash
docker-compose -f docker-compose.test.yml exec postgres psql -U photoexplorer -d photoexplorer_test
```

### Common Issues

**Tests are skipped**: Infrastructure not running
```bash
docker-compose -f docker-compose.test.yml up -d
```

**Import errors**: Wrong directory
```bash
cd backend  # Always run from backend directory
```

**Worker tests fail**: Worker not running (expected, those tests are skipped by default)

## CI/CD Integration

E2E tests run in CI via GitHub Actions:

```yaml
- name: Run E2E tests
  run: |
    docker-compose -f docker-compose.test.yml up -d
    poetry run pytest tests/e2e/ -v --cov=app
    docker-compose -f docker-compose.test.yml down
```

## Coverage Goals

- **Critical paths**: 100% coverage (upload, search, face detection)
- **E2E tests overall**: 80%+ coverage of integration points
- **Combined with unit/integration**: 90%+ overall coverage
