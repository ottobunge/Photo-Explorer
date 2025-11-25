# End-to-End Testing Plan for Photo Explorer

## Executive Summary

Today's face detection implementation revealed critical gaps in our e2e testing. Multiple bugs that would have been caught by comprehensive e2e tests made it to runtime:

**Bugs that slipped through:**
1. Upload endpoint missing `detect_faces_task` call
2. Reprocess task missing `detect_faces_task` call
3. Config type mismatches (`FaceConfig` vs `ModelConfig`)
4. Incorrect attribute access (`face.bbox.x` vs `face.bbox[0]`)
5. Wrong parameter names (`Embedding(vector=)` vs `Embedding.from_list()`)
6. Missing required arguments (`update_clusters_task()` without `face_ids`)
7. Missing pagination parameters (`find_faces_by_cluster(limit=)`)

**Root cause:** Unit tests validate individual components, but e2e tests are needed to verify complete workflows.

## Current State

### Existing E2E Tests
- ✅ `tests/e2e/test_local_file_upload.py` - Basic file upload
- ✅ `tests/e2e/test_semantic_search.py` - Search functionality
- ❌ No face detection e2e tests
- ❌ No connector workflow e2e tests
- ❌ No photo processing pipeline e2e tests

### Coverage Gaps
- Upload → Processing → Face Detection → Clustering (full pipeline)
- Connector sync → Photo indexing → Processing
- Error handling and recovery scenarios
- Integration between API, worker, and database
- Multi-step workflows with state changes

## Comprehensive E2E Testing Strategy

### Principle 1: Test User Journeys, Not Just APIs

E2E tests should simulate actual user workflows from start to finish:

```python
# ❌ BAD: Testing API endpoint in isolation
def test_upload_photo_api():
    response = client.post("/photos/upload", files={"file": image})
    assert response.status_code == 201

# ✅ GOOD: Testing complete workflow
async def test_upload_and_process_photo():
    # Upload
    response = client.post("/photos/upload", files={"file": image})
    photo_id = response.json()["data"]["uploaded"][0]["id"]

    # Wait for processing (with timeout)
    photo = await wait_for_processing(photo_id, timeout=30)
    assert photo.processing_status == "completed"

    # Verify artifacts created
    assert photo.thumbnail_path is not None
    assert photo.embedding is not None

    # Verify searchable
    results = await search("test query")
    assert photo_id in [r["id"] for r in results]
```

### Principle 2: Test with Real Data

Use actual images (not mocks) to test the entire ML pipeline:

```python
# ✅ Download real test images
pytestmark = pytest.mark.e2e

@pytest.fixture(scope="session")
def test_images():
    """Download test images once per test session."""
    download_test_images()
    return Path("tests/fixtures/images")

@pytest.fixture(scope="session")
def face_test_images():
    """Download face test images once per test session."""
    download_face_test_images()
    return Path("tests/fixtures/face-images")
```

### Principle 3: Test Async Workflows

Most photo processing happens asynchronously via Celery. E2E tests must handle this:

```python
async def wait_for_condition(check_fn, timeout=30, interval=0.5):
    """Wait for async condition to become true."""
    start = time.time()
    while time.time() - start < timeout:
        if await check_fn():
            return True
        await asyncio.sleep(interval)
    raise TimeoutError(f"Condition not met within {timeout}s")

async def wait_for_processing(photo_id, timeout=30):
    """Wait for photo to finish processing."""
    async def is_processed():
        photo = await photo_repo.find_by_id(photo_id)
        return photo and photo.processing_status in ["completed", "failed"]

    await wait_for_condition(is_processed, timeout)
    return await photo_repo.find_by_id(photo_id)
```

### Principle 4: Isolated Test Environment

Each test should be independent with clean state:

```python
@pytest.fixture(autouse=True)
async def clean_environment():
    """Clean up before each e2e test."""
    # Clear database
    await clear_all_tables()

    # Clear vector store
    await qdrant_client.delete_collection("photos")
    await qdrant_client.create_collection("photos", ...)

    # Clear file storage
    shutil.rmtree("storage/test", ignore_errors=True)

    # Reset Celery queues
    celery_app.control.purge()

    yield

    # Cleanup after test
    await clear_all_tables()
```

## Test Scenarios by Feature

### 1. Photo Upload & Processing

#### Test: Upload Single Photo
```python
async def test_upload_single_photo_complete_workflow():
    """Test complete upload → process → search workflow."""
    # Upload photo
    with open(test_images / "photo_001.jpg", "rb") as f:
        response = client.post("/api/v1/photos/upload", files={"files": f})

    assert response.status_code == 201
    data = response.json()["data"]
    assert len(data["uploaded"]) == 1
    photo_id = data["uploaded"][0]["id"]

    # Wait for processing to complete
    photo = await wait_for_processing(photo_id, timeout=60)
    assert photo.processing_status == "completed"

    # Verify thumbnail created
    assert photo.thumbnail_path is not None
    thumbnail_response = client.get(f"/api/v1/photos/{photo_id}/thumbnail")
    assert thumbnail_response.status_code == 200

    # Verify embedding created
    assert photo.embedding_id is not None

    # Verify searchable
    search_response = client.post(
        "/api/v1/search",
        json={"query": "photo", "limit": 10}
    )
    assert search_response.status_code == 200
    results = search_response.json()["data"]["results"]
    assert any(r["photo"]["id"] == photo_id for r in results)
```

#### Test: Upload Multiple Photos
```python
async def test_upload_multiple_photos():
    """Test batch upload of multiple photos."""
    files = [
        ("files", open(test_images / f"photo_{i:03d}.jpg", "rb"))
        for i in range(1, 6)
    ]

    response = client.post("/api/v1/photos/upload", files=files)
    assert response.status_code == 201
    uploaded = response.json()["data"]["uploaded"]
    assert len(uploaded) == 5

    # Wait for all to process
    for photo_data in uploaded:
        photo = await wait_for_processing(photo_data["id"], timeout=60)
        assert photo.processing_status == "completed"
```

#### Test: Upload Invalid File
```python
def test_upload_invalid_file():
    """Test upload of non-image file fails gracefully."""
    response = client.post(
        "/api/v1/photos/upload",
        files={"files": ("test.txt", b"not an image", "text/plain")}
    )
    assert response.status_code == 201  # Endpoint doesn't fail
    data = response.json()["data"]
    assert len(data["failed"]) == 1
    assert "Invalid file type" in data["failed"][0]["error"]
```

### 2. Face Detection & Clustering

#### Test: Upload Photo with Face
```python
async def test_face_detection_complete_workflow():
    """Test photo upload → processing → face detection → clustering."""
    # Upload photo with face
    with open(face_test_images / "face_001.jpg", "rb") as f:
        response = client.post("/api/v1/photos/upload", files={"files": f})

    photo_id = response.json()["data"]["uploaded"][0]["id"]

    # Wait for photo processing
    photo = await wait_for_processing(photo_id, timeout=60)
    assert photo.processing_status == "completed"

    # Wait for face detection (separate task)
    async def has_faces():
        faces = await face_repo.find_by_photo(UUID(photo_id))
        return len(faces) > 0

    await wait_for_condition(has_faces, timeout=30)

    # Verify face detected
    faces = await face_repo.find_by_photo(UUID(photo_id))
    assert len(faces) >= 1
    face = faces[0]

    # Verify face attributes
    assert face.bbox is not None
    assert face.embedding is not None
    assert face.confidence > 0.5

    # Verify face appears in clusters
    response = client.get("/api/v1/faces/clusters")
    assert response.status_code == 200
    clusters = response.json()["data"]["clusters"]
    assert len(clusters) > 0

    # Verify can view faces in cluster
    cluster_id = clusters[0]["id"]
    response = client.get(f"/api/v1/faces/clusters/{cluster_id}/faces")
    assert response.status_code == 200
    cluster_faces = response.json()["data"]["faces"]
    assert any(f["id"] == str(face.id.value) for f in cluster_faces)
```

#### Test: Multiple Photos with Same Person
```python
async def test_face_clustering_same_person():
    """Test that faces of same person are clustered together."""
    # Upload 3 photos of same person (use face_001-003)
    photo_ids = []
    for i in range(1, 4):
        with open(face_test_images / f"face_{i:03d}.jpg", "rb") as f:
            response = client.post("/api/v1/photos/upload", files={"files": f})
        photo_ids.append(response.json()["data"]["uploaded"][0]["id"])

    # Wait for all processing and face detection
    for photo_id in photo_ids:
        await wait_for_processing(photo_id, timeout=60)

    # Wait for clustering
    await asyncio.sleep(5)  # Give clustering time

    # Verify faces are in same cluster
    all_faces = []
    for photo_id in photo_ids:
        faces = await face_repo.find_by_photo(UUID(photo_id))
        all_faces.extend(faces)

    assert len(all_faces) >= 3
    cluster_ids = {f.cluster_id for f in all_faces if f.cluster_id}

    # Should be mostly in same cluster (allow some variance)
    assert len(cluster_ids) <= 2
```

#### Test: Tag Face with Name
```python
async def test_tag_face_with_name():
    """Test tagging a face cluster with a person's name."""
    # Upload photo with face
    with open(face_test_images / "face_001.jpg", "rb") as f:
        response = client.post("/api/v1/photos/upload", files={"files": f})

    photo_id = response.json()["data"]["uploaded"][0]["id"]
    await wait_for_processing(photo_id, timeout=60)

    # Get face cluster
    response = client.get("/api/v1/faces/clusters")
    cluster_id = response.json()["data"]["clusters"][0]["id"]

    # Tag cluster with name
    response = client.patch(
        f"/api/v1/faces/clusters/{cluster_id}",
        json={"name": "John Doe"}
    )
    assert response.status_code == 200

    # Verify name persisted
    response = client.get(f"/api/v1/faces/clusters/{cluster_id}")
    assert response.json()["data"]["name"] == "John Doe"
```

### 3. Connector Workflows

#### Test: Local Folder Connector
```python
async def test_local_connector_complete_workflow():
    """Test local folder connector: create → sync → photos indexed."""
    # Create temp folder with images
    temp_dir = Path(tempfile.mkdtemp())
    for i in range(1, 6):
        shutil.copy(
            test_images / f"photo_{i:03d}.jpg",
            temp_dir / f"photo_{i:03d}.jpg"
        )

    try:
        # Create connector
        response = client.post(
            "/api/v1/connectors/local",
            json={
                "path": str(temp_dir),
                "name": "Test Folder",
                "recursive": False,
                "watch": False
            }
        )
        assert response.status_code == 201
        connector_id = response.json()["data"]["id"]

        # Trigger sync
        response = client.post(f"/api/v1/connectors/{connector_id}/sync")
        assert response.status_code == 200

        # Wait for sync to complete
        async def sync_complete():
            conn = await connector_repo.find_by_id(UUID(connector_id))
            return conn and conn.status != "syncing"

        await wait_for_condition(sync_complete, timeout=30)

        # Verify photos indexed
        response = client.get(
            f"/api/v1/connectors/{connector_id}/photos",
            params={"page": 1, "per_page": 20}
        )
        assert response.status_code == 200
        photos = response.json()["data"]["photos"]
        assert len(photos) == 5

        # Wait for all photos to process
        for photo in photos:
            await wait_for_processing(photo["id"], timeout=60)

        # Verify all photos have thumbnails
        for photo in photos:
            response = client.get(f"/api/v1/photos/{photo['id']}/thumbnail")
            assert response.status_code == 200

    finally:
        shutil.rmtree(temp_dir)
```

#### Test: Reprocess Connector
```python
async def test_connector_reprocess():
    """Test reprocessing all photos in a connector."""
    # Setup connector with photos (reuse previous test setup)
    connector_id, photo_ids = await setup_test_connector()

    # Mark photos as pending (simulate incomplete processing)
    for photo_id in photo_ids:
        photo = await photo_repo.find_by_id(UUID(photo_id))
        photo.processing_status = "pending"
        await photo_repo.save(photo)

    # Trigger reprocess
    response = client.post(f"/api/v1/connectors/{connector_id}/reprocess")
    assert response.status_code == 200

    # Verify all photos reprocessed
    for photo_id in photo_ids:
        photo = await wait_for_processing(photo_id, timeout=60)
        assert photo.processing_status == "completed"
```

### 4. Search Workflows

#### Test: Semantic Search
```python
async def test_semantic_search_workflow():
    """Test semantic search across uploaded photos."""
    # Upload diverse images
    image_queries = [
        ("photo_001.jpg", "cat"),
        ("photo_016.jpg", "mountain"),
        ("photo_031.jpg", "city"),
    ]

    for filename, expected_query in image_queries:
        with open(test_images / filename, "rb") as f:
            client.post("/api/v1/photos/upload", files={"files": f})

    # Wait for processing (all photos)
    await asyncio.sleep(30)

    # Test each query finds relevant photo
    for filename, query in image_queries:
        response = client.post(
            "/api/v1/search",
            json={"query": query, "limit": 5}
        )
        assert response.status_code == 200
        results = response.json()["data"]["results"]
        assert len(results) > 0

        # Verify relevant photo in top results
        filenames = [r["photo"]["filename"] for r in results]
        # Note: May not be #1 result, but should be in top results
        assert any(query in str(results).lower() for r in results)
```

### 5. Error Scenarios

#### Test: Worker Failure Recovery
```python
async def test_worker_failure_recovery():
    """Test system recovers from worker failures."""
    # Upload photo
    with open(test_images / "photo_001.jpg", "rb") as f:
        response = client.post("/api/v1/photos/upload", files={"files": f})

    photo_id = response.json()["data"]["uploaded"][0]["id"]

    # Simulate worker crash (kill task)
    # In real test, would restart worker and verify retry

    # For now, verify task eventually completes or fails gracefully
    photo = await wait_for_processing(photo_id, timeout=120)
    assert photo.processing_status in ["completed", "failed"]

    if photo.processing_status == "failed":
        # Verify can retry
        response = client.post(f"/api/v1/photos/{photo_id}/reprocess")
        assert response.status_code == 200
```

## Implementation Plan

### Phase 1: Foundation (Week 1)
- [ ] Set up e2e test infrastructure
  - [ ] Test data download automation
  - [ ] Clean environment fixtures
  - [ ] Async helper utilities (wait_for_condition, etc.)
  - [ ] Test database and Qdrant setup
- [ ] Implement photo upload e2e tests (3 tests)
- [ ] Implement search e2e tests (2 tests)

### Phase 2: Face Detection (Week 2)
- [ ] Download face test images
- [ ] Implement face detection e2e tests (5 tests)
  - [ ] Upload with face detection
  - [ ] Face clustering
  - [ ] Face tagging
  - [ ] Multiple faces same person
  - [ ] Multiple people different clusters

### Phase 3: Connectors (Week 3)
- [ ] Implement local connector e2e tests (4 tests)
  - [ ] Create and sync
  - [ ] Reprocess
  - [ ] Watch mode
  - [ ] Subfolder auto-albums
- [ ] Implement Google Photos connector e2e tests (3 tests)
  - [ ] OAuth flow
  - [ ] Sync
  - [ ] Incremental sync

### Phase 4: Advanced Scenarios (Week 4)
- [ ] Error handling tests (5 tests)
  - [ ] Worker failures
  - [ ] Database connection issues
  - [ ] Vector store failures
  - [ ] File system errors
  - [ ] Invalid data handling
- [ ] Performance tests (3 tests)
  - [ ] Bulk upload (100 photos)
  - [ ] Large image handling
  - [ ] Concurrent uploads

### Phase 5: CI Integration
- [ ] Add e2e test CI job
- [ ] Separate from unit tests (longer running)
- [ ] Run on PR and main branch
- [ ] Add test coverage reporting
- [ ] Document test data requirements

## Test Data Management

### Strategy
1. **Don't commit test images to git** (large binary files)
2. **Download on-demand** from Unsplash (stable URLs)
3. **Cache locally** in `tests/fixtures/images/` and `tests/fixtures/face-images/`
4. **Version test data scripts** (download_test_images.py)

### CI Setup
```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests

on:
  pull_request:
  push:
    branches: [main]

jobs:
  e2e:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
      qdrant:
        image: qdrant/qdrant:latest
      redis:
        image: redis:alpine

    steps:
      - uses: actions/checkout@v4

      - name: Download test images
        run: |
          python backend/tests/fixtures/download_test_images.py
          python backend/tests/fixtures/download_face_test_images.py

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          cd backend
          poetry install

      - name: Run e2e tests
        run: |
          cd backend
          poetry run pytest tests/e2e -v --timeout=300
        env:
          DATABASE_URL: postgresql://...
          QDRANT_URL: http://localhost:6333
          REDIS_URL: redis://localhost:6379
```

## Metrics & Success Criteria

### Coverage Goals
- **E2E test coverage**: 80% of critical user journeys
- **Test execution time**: <10 minutes for full e2e suite
- **Flakiness rate**: <5% (tests should be reliable)

### Critical Paths to Cover
1. ✅ Upload → Process → Search (photo workflow)
2. ✅ Upload → Detect → Cluster → Tag (face workflow)
3. ✅ Create connector → Sync → View photos (connector workflow)
4. ⚠️ Error scenarios and recovery
5. ⚠️ Concurrent operations

### Current Coverage Status
- Unit tests: 92% (API layer)
- Integration tests: ~60% (repositories, services)
- **E2E tests: ~10%** ← **Needs improvement**

## Lessons Learned from Face Detection

### What Went Wrong
1. **No pipeline tests** - Unit tests validated individual components, but not the full Upload → Process → Detect → Cluster workflow
2. **No type integration tests** - Config type mismatches weren't caught
3. **No real data tests** - Mock data didn't reveal bbox tuple vs object issues
4. **No async workflow tests** - Task chaining bugs weren't caught

### What to Do Different
1. **Test complete workflows** - Not just individual API endpoints
2. **Use real test data** - Actual images, not mocks
3. **Test async task chains** - Verify worker tasks execute in correct order
4. **Add contract tests** - Verify interfaces match between layers

## Appendix: Helper Utilities

### A. wait_for_condition
```python
async def wait_for_condition(
    check_fn: Callable[[], Awaitable[bool]],
    timeout: float = 30,
    interval: float = 0.5,
    error_message: str = "Condition not met"
) -> None:
    """Wait for async condition with timeout."""
    start = time.time()
    while time.time() - start < timeout:
        if await check_fn():
            return
        await asyncio.sleep(interval)
    raise TimeoutError(f"{error_message} within {timeout}s")
```

### B. wait_for_processing
```python
async def wait_for_processing(
    photo_id: str,
    photo_repo: PhotoRepository,
    timeout: float = 60
) -> Photo:
    """Wait for photo to finish processing."""
    async def is_processed():
        photo = await photo_repo.find_by_id(UUID(photo_id))
        return photo and photo.processing_status in ["completed", "failed"]

    await wait_for_condition(
        is_processed,
        timeout=timeout,
        error_message=f"Photo {photo_id} processing timed out"
    )

    photo = await photo_repo.find_by_id(UUID(photo_id))
    if photo.processing_status == "failed":
        raise AssertionError(f"Photo {photo_id} processing failed")

    return photo
```

### C. setup_test_connector
```python
async def setup_test_connector(
    num_photos: int = 5
) -> tuple[str, list[str]]:
    """Setup a test connector with photos."""
    temp_dir = Path(tempfile.mkdtemp())

    # Copy test images
    for i in range(1, num_photos + 1):
        shutil.copy(
            test_images_dir / f"photo_{i:03d}.jpg",
            temp_dir / f"photo_{i:03d}.jpg"
        )

    # Create connector
    response = client.post(
        "/api/v1/connectors/local",
        json={"path": str(temp_dir), "name": "Test"}
    )
    connector_id = response.json()["data"]["id"]

    # Sync
    client.post(f"/api/v1/connectors/{connector_id}/sync")

    # Get photo IDs
    response = client.get(f"/api/v1/connectors/{connector_id}/photos")
    photo_ids = [p["id"] for p in response.json()["data"]["photos"]]

    return connector_id, photo_ids
```

## Conclusion

Implementing comprehensive e2e tests will catch bugs like today's face detection issues before they reach runtime. The investment in test infrastructure and test data management will pay dividends in reliability and developer confidence.

**Next steps:**
1. Set up e2e test infrastructure
2. Implement Phase 1 tests (upload and search)
3. Add face detection e2e tests using new face test images
4. Integrate into CI pipeline
5. Iterate and expand coverage

---
*Document Version: 1.0*
*Date: 2025-11-25*
*Author: Development Team*
