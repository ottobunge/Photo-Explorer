# Photo Explorer - BDD Features Summary

## Overview

This document provides a comprehensive overview of the Behavior-Driven Development (BDD) feature files and test infrastructure for the Photo Explorer backend. All critical user flows are covered with executable Gherkin scenarios.

**Status**: ✅ Complete - 51 scenarios across 5 feature files with 180+ step definitions

---

## Feature Files Summary

### 1. Photo Upload and Processing (`photo_upload.feature`)

**File**: `/backend/tests/features/photo_upload.feature`
**Lines**: 83 | **Scenarios**: 8

Covers the complete photo upload and processing pipeline with comprehensive validation.

#### Scenarios Implemented

| Scenario | Tags | Coverage |
|----------|------|----------|
| Upload single photo successfully | @upload @critical | Happy path with metadata extraction |
| Upload photo with face detection | @upload @faces | Face detection and embedding pipeline |
| Reject invalid file type | @upload @validation | Input validation and error handling |
| Handle duplicate photos gracefully | @upload @duplicate | Duplicate detection by hash |
| Upload multiple photos in batch | @upload @batch | Batch processing with async tasks |
| Extract and store photo metadata | @upload @metadata | EXIF data parsing and storage |
| Handle upload errors gracefully | @upload @error | Graceful error handling and rollback |
| Reject files exceeding size limit | @upload @size | File size validation |

#### Key Business Rules

- Single photos return 201 Created with photo ID
- Batch uploads process asynchronously
- Duplicate detection prevents storage duplication
- File size limit: 50MB per file
- Invalid formats rejected with 400 Bad Request
- Corrupted images handled gracefully with 422 Unprocessable Entity
- Metadata (EXIF, camera info, GPS) extracted and stored
- Face detection runs automatically on upload

#### Step Definitions Location

- `tests/features/steps/photo_upload_steps.py` - Upload-specific steps
- `tests/features/steps/common.py` - Shared setup/assertion steps

---

### 2. Semantic Photo Search (`semantic_search.feature`)

**File**: `/backend/tests/features/semantic_search.feature`
**Lines**: 85 | **Scenarios**: 9

Tests natural language photo search powered by semantic embeddings.

#### Scenarios Implemented

| Scenario | Tags | Coverage |
|----------|------|----------|
| Search with natural language query | @search @semantic @critical | Text to embedding search |
| Find conceptually similar photos | @search @semantic | Cross-concept similarity (e.g., "tropical vacation" finds beach) |
| Search with visual similarity | @search @visual | Image-based similarity search |
| Handle empty search results gracefully | @search @empty | Empty result set handling |
| Search with metadata filters | @search @filter | Combined text + filter queries |
| Paginate search results | @search @pagination | Result pagination and metadata |
| Search in different languages | @search @multilingual | Multilingual query support |
| Complex semantic query | @search @complex | Emotional/contextual queries |
| Fast search response | @search @performance | SLA: <500ms for 10k photos |

#### Key Business Rules

- Similarity score threshold: 0.7
- Results ranked by semantic similarity (descending)
- Supports filters: date_from, date_to, has_faces, tags, location
- Pagination: configurable page size (default 10)
- Empty results return 200 (not error)
- Multilingual support via semantic model
- Performance SLA: 500ms for 10,000 photos

#### Data Fixtures

Pre-loaded test photos with descriptions:
- beach.jpg - "sunset at the beach" (ocean, sunset, sand)
- mountain.jpg - "snowy mountain peaks" (snow, mountain, winter)
- dog.jpg - "golden retriever playing" (dog, pet, outdoor)
- city.jpg - "urban skyline at night" (city, night, buildings)
- forest.jpg - "dense green forest" (trees, nature, green)

#### Step Definitions Location

- `tests/features/steps/search_steps.py` - Search-specific steps
- `tests/features/steps/common.py` - Shared steps

---

### 3. Face Detection and Tagging (`face_tagging.feature`)

**File**: `/backend/tests/features/face_tagging.feature`
**Lines**: 107 | **Scenarios**: 10

Comprehensive face detection, clustering, and naming workflows.

#### Scenarios Implemented

| Scenario | Tags | Coverage |
|----------|------|----------|
| Automatic face detection on upload | @faces @critical | Auto-detection with confidence scoring |
| Automatic face clustering | @faces @clustering @critical | Grouping similar faces (threshold: 0.6) |
| Name a face cluster | @faces @naming @critical | Assigning person names to clusters |
| Merge face clusters atomically | @faces @merge @critical @atomic | Atomic merge with rollback support |
| Split incorrectly grouped faces | @faces @split | Separating mis-grouped faces |
| Search photos by person name | @faces @search @critical | Person-based photo search |
| Handle face detection opt-out | @faces @privacy | Privacy: skip detection if marked private |
| Filter low-quality face detections | @faces @quality | Confidence threshold: >0.8 |
| Update face cluster assignments | @faces @update | Move faces between clusters |
| Delete face data while keeping photos | @faces @delete | Data cleanup without photo deletion |

#### Key Business Rules

- Automatic face detection on upload (if enabled)
- Face embedding: 512-dimensional vector
- Detection confidence threshold: >0.9
- Clustering threshold: 0.6 (cosine similarity)
- Quality filter: confidence >0.8 to keep detection
- Cluster merging must be atomic with rollback on failure
- Cluster naming tags all member faces
- Face detection can be disabled per-photo (privacy)
- Photo remains searchable after face deletion

#### Data Fixtures

Test photos with face counts:
- group.jpg - 3 visible faces
- john1.jpg, john2.jpg, john3.jpg - Same person (clustering test)
- blurry.jpg - Low-confidence detections

#### Step Definitions Location

- `tests/features/steps/face_steps.py` - Face-specific steps
- `tests/features/steps/common.py` - Shared steps

---

### 4. Album Management (`album_management.feature`)

**File**: `/backend/tests/features/album_management.feature`
**Lines**: 124 | **Scenarios**: 12

Album CRUD operations, photo associations, and sharing.

#### Scenarios Implemented

| Scenario | Tags | Coverage |
|----------|------|----------|
| Create a new album | @albums @create @critical | Album creation with metadata |
| Add photos to album | @albums @add @critical | Bulk photo addition (non-destructive) |
| Remove photos from album | @albums @remove | Remove specific photos |
| Delete album without deleting photos | @albums @delete | Album deletion preserves photos |
| List all albums with pagination | @albums @list | Paginated album listing |
| Prevent duplicate album names | @albums @duplicate | Name uniqueness constraint |
| Rename an existing album | @albums @rename | Album update operations |
| Generate shareable album link | @albums @share | Share links with optional expiration |
| Get album statistics | @albums @stats | Photo count, size, date range, tags |
| Set album cover photo | @albums @cover | Thumbnail cover selection |
| Batch operations on albums | @albums @batch | Atomic batch add (50+ photos) |
| Auto-create album from folder import | @albums @auto | Auto-naming from folder structure |

#### Key Business Rules

- Album names must be unique per user
- Adding photos to album doesn't move them (non-destructive)
- Album deletion removes association but keeps photos
- Pagination default: 10 items per page
- Album statistics include: photo_count, total_size_mb, date_range, tags
- Shareable links can have optional expiration
- Cover photo must exist in album
- Batch operations must be atomic (all-or-nothing)
- Folder imports auto-create album with folder name

#### Data Fixtures

Pre-created photos:
- photo_1: vacation1.jpg (2024-07-01)
- photo_2: vacation2.jpg (2024-07-02)
- photo_3: birthday1.jpg (2024-08-15)
- photo_4: birthday2.jpg (2024-08-15)
- photo_5: random.jpg (2024-09-01)

#### Step Definitions Location

- `tests/features/steps/album_steps.py` - Album-specific steps
- `tests/features/steps/common.py` - Shared steps

---

### 5. Local Folder Synchronization (`folder_sync.feature`)

**File**: `/backend/tests/features/folder_sync.feature`
**Lines**: 127 | **Scenarios**: 12

Folder watching, file system monitoring, and sync operations.

#### Scenarios Implemented

| Scenario | Tags | Coverage |
|----------|------|----------|
| Register folder for watching | @sync @register @critical | Folder registration and initial scan |
| Detect new photos automatically | @sync @detect @critical | File system monitoring (5s detection) |
| Handle deleted photos from folder | @sync @delete | Mark as source_deleted, keep in library |
| Skip non-image files | @sync @ignore | Filter documents, videos, text files |
| Handle nested folders recursively | @sync @recursive @critical | Deep folder traversal and import |
| Handle duplicate files across folders | @sync @duplicate | Hash-based deduplication |
| Pause and resume folder watching | @sync @pause | Suspend monitoring temporarily |
| Unregister folder from watching | @sync @unregister | Stop monitoring, keep imported photos |
| Detect modified photos | @sync @modify | Re-process updated files |
| Handle inaccessible folders gracefully | @sync @error | Error logging and retry mechanism |
| Handle large folder efficiently | @sync @performance | SLA: <5min for 10k photos, <500MB RAM |
| Apply filters during folder sync | @sync @filter | Size/extension/date filtering |

#### Key Business Rules

- Folder registration scans existing photos immediately
- File monitoring detects new/modified/deleted within 5 seconds
- Recursive option enables nested folder traversal
- Duplicate detection uses file hash comparison
- Non-image files (PDF, MP4, TXT) automatically skipped
- Deleted files marked as "source_deleted" but kept in library
- Folder watching can be paused/resumed without data loss
- Modified files are re-processed with new embeddings
- Inaccessible folders logged and retried periodically
- Batch processing for initial scan (10k photos in <5 minutes)

#### Supported Filters

- min_size_kb - Minimum file size
- max_size_mb - Maximum file size
- extensions - Comma-separated allowed extensions (jpg, png, heic)
- modified_after - Only import files modified after date

#### Folder Structure Example

```
/photos/
├── camera/
│   ├── img001.jpg (already imported)
│   ├── img002.jpg (already imported)
│   └── img003.jpg (new, detected within 5s)
├── archive/
│   └── old001.jpg
└── nested/
    └── deep/
        └── folder/
            └── photo.jpg
```

#### Step Definitions Location

- `tests/features/steps/folder_steps.py` - Folder-specific steps
- `tests/features/steps/common.py` - Shared steps

---

## Test Infrastructure

### Project Structure

```
backend/
├── tests/
│   ├── features/                    # BDD test suite
│   │   ├── conftest.py             # Pytest fixtures and configuration
│   │   ├── test_runner.py          # Feature file loader
│   │   ├── *.feature               # Gherkin feature files (5 files, 51 scenarios)
│   │   └── steps/                  # Step definitions (180+ steps)
│   │       ├── common.py           # Shared GIVEN/WHEN/THEN steps
│   │       ├── photo_upload_steps.py
│   │       ├── search_steps.py
│   │       ├── face_steps.py
│   │       ├── album_steps.py
│   │       ├── folder_steps.py
│   │       └── __init__.py
│   ├── unit/                        # Unit tests (domain layer)
│   ├── integration/                 # Integration tests (API, repositories)
│   └── conftest.py
├── app/
│   ├── domain/
│   ├── application/
│   ├── adapters/
│   └── main.py
└── pyproject.toml
```

### Dependencies

```toml
pytest = "^7.0"
pytest-asyncio = "^0.21"
pytest-bdd = "^6.0"
httpx = "^0.24"
sqlalchemy = "^2.0"
pillow = "^10.0"
piexif = "^0.0.14"
```

### Fixtures Available

Located in `tests/features/conftest.py`:

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `event_loop` | session | Async event loop for all tests |
| `test_settings` | session | Override app settings for testing |
| `test_db` | function | Clean database session per test |
| `test_client` | function | AsyncClient with dependency overrides |
| `test_fixtures_dir` | function | Temp directory for test files |
| `auth_headers` | function | Test authentication headers |
| `context` | function | Shared context dict between steps |
| `sample_photos` | function | Pre-created test image files |
| `mock_ml_services` | function | Mocked face/embedding services |
| `mock_vector_store` | function | Mocked Qdrant vector store |

### Running Tests

```bash
# Run all BDD tests
cd backend
poetry run pytest tests/features/test_runner.py -v

# Run specific feature
poetry run pytest tests/features/test_runner.py -k photo_upload

# Run with markers
poetry run pytest tests/features/test_runner.py -m critical

# Run with coverage
poetry run pytest tests/features/test_runner.py --cov=app --cov-report=html

# Run in parallel (fast)
poetry run pytest tests/features/test_runner.py -n auto

# Debug mode (verbose output)
poetry run pytest tests/features/test_runner.py -vv --tb=short
```

### Step Definition Organization

```python
# Each step definition file follows this pattern:

from pytest_bdd import given, when, then, parsers

# ============================================================================
# GIVEN Steps - Setup and Preconditions
# ============================================================================

@given(parsers.parse('I have a photo "{filename}"'))
def setup_photo(filename: str, context):
    # Arrange
    pass

# ============================================================================
# WHEN Steps - Actions
# ============================================================================

@when(parsers.parse('I upload the photo'))
async def upload_photo(context):
    # Act
    pass

# ============================================================================
# THEN Steps - Assertions
# ============================================================================

@then('the upload should be successful')
def assert_upload_success(context):
    # Assert
    pass
```

### Test Markers

Used for organizing test execution:

- `@critical` - Critical user flows (required 100% E2E coverage)
- `@upload` - Photo upload tests
- `@search` - Search tests
- `@semantic` - Semantic search
- `@visual` - Visual similarity
- `@faces` - Face detection/tagging
- `@clustering` - Face clustering
- `@naming` - Face naming
- `@merge` - Cluster merging (atomic)
- `@albums` - Album tests
- `@sync` - Folder sync tests
- `@error` - Error handling
- `@performance` - Performance SLAs
- `@atomic` - Atomic/transactional operations

---

## Feature Completeness Matrix

### Critical Flows (100% Coverage Required)

| Flow | Feature | Scenarios | Status |
|------|---------|-----------|--------|
| Photo Upload | photo_upload.feature | 8 | ✅ Complete |
| Semantic Search | semantic_search.feature | 9 | ✅ Complete |
| Face Tagging | face_tagging.feature | 10 | ✅ Complete |
| Album Management | album_management.feature | 12 | ✅ Complete |
| Folder Sync | folder_sync.feature | 12 | ✅ Complete |

**Total**: 51 scenarios across 5 feature files

### Scenario Categories

| Category | Count | Examples |
|----------|-------|----------|
| Happy Path | 20+ | Upload succeeds, search finds results, album created |
| Validation | 8+ | Invalid file type, size limit, duplicate names |
| Error Handling | 6+ | Corrupted files, inaccessible folders, network errors |
| Performance | 3+ | 10k photos search, large folder sync |
| Privacy | 2+ | Face detection opt-out, private photos |
| Atomicity | 3+ | Batch operations, cluster merging with rollback |
| Edge Cases | 9+ | Empty results, deleted sources, filter combinations |

---

## BDD Best Practices Applied

### 1. Behavior-Focused Scenarios

✅ Scenarios describe **what the system does**, not **how** it does it

```gherkin
# GOOD - Behavior-focused
Scenario: Upload single photo successfully
  Given I have a valid image file "sunset.jpg"
  When I upload the photo
  Then the upload should be successful
  And the photo should be stored in the database
  And the photo should be indexed for search

# AVOID - Implementation-focused (not used in our features)
# Scenario: Photo service calls repository save method
#   When service.save(photo) is called
#   Then repository.insert() is invoked
```

### 2. Business Language

✅ Scenarios use **ubiquitous language** from the domain

```gherkin
# Business terms used consistently:
- "photo" (not "image" or "file")
- "embedding" (not "feature vector")
- "cluster" (not "group" or "collection")
- "semantic search" (not "vector similarity search")
- "face tagging" (not "face classification")
```

### 3. Clear Preconditions (Given)

✅ Each scenario explicitly states required setup

```gherkin
Background:
  Given the system is ready to accept uploads
  And ML services are available

Scenario: ...
  Given I have a valid image file "sunset.jpg"
  When I upload the photo
  ...
```

### 4. Single Responsibility

✅ Each scenario tests one behavior

```gherkin
# Each scenario focuses on a single aspect:
Scenario: Upload single photo successfully        # Happy path
Scenario: Reject invalid file type                # Validation
Scenario: Handle upload errors gracefully         # Error handling
Scenario: Upload multiple photos in batch         # Batch processing
```

### 5. Executable Specifications

✅ Every scenario is implemented with step definitions

```python
# Every Gherkin step has a corresponding Python implementation
@given(parsers.parse('I have a valid image file "{filename}"'))
def prepare_valid_image(filename: str, test_fixtures_dir: Path):
    # Implementation with actual file creation
    create_test_image(file_path, filename)
    assert file_path.exists()
```

### 6. Data-Driven Testing

✅ Using Gherkin data tables for multiple examples

```gherkin
Scenario: Extract and store photo metadata
  When I upload the photo
  Then the following metadata should be extracted:
    | field         | value                |
    | camera_make   | Canon                |
    | camera_model  | EOS R5               |
    | taken_at      | 2024-03-15T10:30:00  |
    | gps_latitude  | 37.7749              |
    | gps_longitude | -122.4194            |
```

### 7. Clear Assertions

✅ Specific, testable outcomes (not vague)

```gherkin
# GOOD - Specific and measurable
Then the photo should be stored in the database
And the photo should be indexed for search
And metadata should be extracted from the photo
And the response should include the photo ID

# AVOID - Vague (not used)
# Then the system should work correctly
# And everything should be fine
```

---

## Step Definition Coverage

### Common Steps (shared across all features)

**File**: `tests/features/steps/common.py` (180+ steps defined)

#### Setup Steps (Given)
- System readiness and health checks
- ML/Vector database initialization
- Authentication and user setup
- Photo library preparation
- Album and cluster creation

#### Action Steps (When)
- Photo upload (single/batch)
- Search queries
- Album operations (create, add, remove)
- Folder registration
- Face cluster operations

#### Assertion Steps (Then)
- Response status validation
- Database state verification
- Search result ranking
- Metadata presence checks
- Error message validation

### Feature-Specific Steps

| File | Coverage | Key Steps |
|------|----------|-----------|
| `photo_upload_steps.py` | EXIF, faces, corruption, size | 25+ steps |
| `search_steps.py` | Semantic, filters, pagination | 20+ steps |
| `face_steps.py` | Detection, clustering, naming | 30+ steps |
| `album_steps.py` | CRUD, photos, sharing | 25+ steps |
| `folder_steps.py` | Registration, sync, filtering | 30+ steps |

---

## Extending the Features

### Adding a New Scenario

```gherkin
# 1. Add to existing .feature file

Scenario: New behavior description
  Given [precondition]
  When [action]
  Then [outcome]
  And [additional outcome]
```

### Adding a New Step Definition

```python
# 2. Add to appropriate steps/*.py file

from pytest_bdd import given, when, then, parsers

@given(parsers.parse('I have {count:d} photos'))
def prepare_photos(count: int, context):
    """Create N photos for testing."""
    context.photos = [create_photo() for _ in range(count)]

@when(parsers.parse('I perform action "{action}"'))
async def perform_action(action: str, test_client: AsyncClient, context):
    """Execute the action."""
    response = await test_client.post(f"/api/action/{action}")
    context.response = response

@then(parsers.parse('I should see {expected:d} results'))
def assert_result_count(expected: int, context):
    """Verify result count."""
    actual = len(context.search_results)
    assert actual == expected, f"Expected {expected}, got {actual}"
```

### Running Updated Tests

```bash
# Test just the new scenario
poetry run pytest tests/features/test_runner.py -k "new_behavior"

# Test entire feature
poetry run pytest tests/features/test_runner.py -k "photo_upload"

# All BDD tests
poetry run pytest tests/features/test_runner.py
```

---

## Performance Benchmarks

From feature specifications:

| Scenario | SLA | Notes |
|----------|-----|-------|
| Single photo upload | <2s | Includes processing (thumbnails, embeddings) |
| Batch upload (50 photos) | <10s | Async, completion monitored |
| Semantic search (10k photos) | <500ms | Vector DB query + ranking |
| Face detection per photo | <5s | ML model inference |
| Face clustering (100 faces) | <10s | Algorithm execution |
| Folder sync (10k photos) | <5min | Initial batch scan |
| Folder detection (new photo) | <5s | File system monitoring |

---

## Known Limitations

### Current Mocks

- ML services (face detection, embedding generation) are mocked
- Vector store (Qdrant) is mocked in-memory
- File storage uses temporary directories

### Not Covered (Out of Scope)

- Real ML model performance
- Database persistence across test runs (cleaned up after each test)
- Actual file system watching (mocked)
- Network failures and retries
- OAuth/third-party integrations (stubbed)

### When to Add Integration Tests

Add integration tests (in `tests/integration/`) when you need to:
- Test real database queries
- Test API routes end-to-end
- Test with real ML model inference
- Test file system integration
- Test error handling paths

---

## Related Documentation

- **Architecture**: `spec/06-architecture-patterns.md`
- **Testing Strategy**: `spec/05-testing-strategy.md`
- **Features**: `spec/04-features.md`
- **API Specification**: `spec/03-api-specification.md`

---

## Quick Reference Commands

```bash
cd /home/otto/repos/personal/photo-explorer/backend

# Run all BDD tests
poetry run pytest tests/features/test_runner.py -v

# Run specific feature
poetry run pytest tests/features/ -k photo_upload -v

# Run critical scenarios only
poetry run pytest tests/features/ -m critical -v

# Run with coverage report
poetry run pytest tests/features/ --cov=app --cov-report=term-missing

# Run in parallel (faster)
poetry run pytest tests/features/ -n auto

# Run with detailed output
poetry run pytest tests/features/ -vv --tb=short --capture=no

# List all scenarios (dry run)
poetry run pytest tests/features/ --collect-only -q

# Run single scenario by name
poetry run pytest tests/features/ -k "upload single photo" -v
```

---

**Last Updated**: December 1, 2025
**Total Lines of Gherkin**: 522
**Total Scenarios**: 51
**Step Definitions**: 180+
**Features**: 5 critical flows
