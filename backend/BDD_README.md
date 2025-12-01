# Photo Explorer Backend - BDD Test Suite Guide

## Overview

This document provides a comprehensive guide to the **Behavior-Driven Development (BDD) test infrastructure** for the Photo Explorer backend. The project implements 51 executable Gherkin scenarios across 5 critical user flows with 180+ step definitions.

**Status**: ✅ Complete and Production Ready
- **5 Feature Files**: 522 lines of Gherkin
- **51 Scenarios**: All critical flows covered
- **180+ Step Definitions**: Fully implemented
- **Test Infrastructure**: Pytest-BDD with async/await support

---

## Quick Start

### Run All BDD Tests
```bash
cd /home/otto/repos/personal/photo-explorer/backend

# Run all tests
poetry run pytest tests/features/test_runner.py -v

# Run critical scenarios only
poetry run pytest tests/features/ -m critical -v

# Run with coverage
poetry run pytest tests/features/ --cov=app --cov-report=html
```

### View Test Results
```bash
# Show detailed output
poetry run pytest tests/features/ -vv --tb=short --capture=no

# Run single feature
poetry run pytest tests/features/ -k photo_upload -v

# Parallel execution (fast)
poetry run pytest tests/features/ -n auto
```

---

## Documentation Files

### Main Documentation
| File | Purpose | Contents |
|------|---------|----------|
| **BDD_FEATURES_SUMMARY.md** | Complete feature overview | All 51 scenarios, step definitions, fixtures, setup |
| **STEP_DEFINITIONS_GUIDE.md** | Implementation patterns | How to write step definitions, common patterns, async |
| **FEATURES_SHOWCASE.md** | Real-world examples | Detailed walkthrough of each critical flow |
| **QUICK_REFERENCE.md** | Quick lookup | Common commands, fixture reference, troubleshooting |
| **BDD_README.md** | This file | Overview and navigation |

### Test Files Location
```
backend/
├── tests/features/
│   ├── conftest.py                      # Pytest fixtures
│   ├── test_runner.py                   # Feature loader
│   ├── *.feature                        # 5 Gherkin feature files
│   ├── steps/
│   │   ├── common.py                    # Shared steps
│   │   ├── photo_upload_steps.py
│   │   ├── search_steps.py
│   │   ├── face_steps.py
│   │   ├── album_steps.py
│   │   └── folder_steps.py
│   ├── BDD_FEATURES_SUMMARY.md          # Comprehensive summary
│   ├── STEP_DEFINITIONS_GUIDE.md        # Implementation guide
│   └── QUICK_REFERENCE.md               # Quick lookup
├── FEATURES_SHOWCASE.md                 # Real examples
└── BDD_README.md                        # This file
```

---

## Feature Files Overview

### 1. Photo Upload and Processing (8 scenarios)
**File**: `tests/features/photo_upload.feature`

Critical scenarios for uploading and processing photos:
- ✅ Upload single photo successfully
- ✅ Upload photo with face detection
- ✅ Reject invalid file type
- ✅ Handle duplicate photos gracefully
- ✅ Upload multiple photos in batch
- ✅ Extract and store photo metadata
- ✅ Handle upload errors gracefully
- ✅ Reject files exceeding size limit

**Key Tests**: Validation, metadata extraction, duplicate detection, error handling

### 2. Semantic Photo Search (9 scenarios)
**File**: `tests/features/semantic_search.feature`

Natural language search powered by embeddings:
- ✅ Search with natural language query
- ✅ Find conceptually similar photos
- ✅ Search with visual similarity
- ✅ Handle empty search results gracefully
- ✅ Search with metadata filters
- ✅ Paginate search results
- ✅ Search in different languages
- ✅ Complex semantic query
- ✅ Fast search response

**Key Tests**: Semantic similarity, filtering, pagination, performance SLA <500ms

### 3. Face Detection and Tagging (10 scenarios)
**File**: `tests/features/face_tagging.feature`

Automatic face detection, clustering, and naming:
- ✅ Automatic face detection on upload
- ✅ Automatic face clustering
- ✅ Name a face cluster
- ✅ Merge face clusters atomically
- ✅ Split incorrectly grouped faces
- ✅ Search photos by person name
- ✅ Handle face detection opt-out
- ✅ Filter low-quality face detections
- ✅ Update face cluster assignments
- ✅ Delete face data while keeping photos

**Key Tests**: Detection, clustering, atomic operations, privacy

### 4. Album Management (12 scenarios)
**File**: `tests/features/album_management.feature`

Album CRUD operations and photo associations:
- ✅ Create a new album
- ✅ Add photos to album
- ✅ Remove photos from album
- ✅ Delete album without deleting photos
- ✅ List all albums with pagination
- ✅ Prevent duplicate album names
- ✅ Rename an existing album
- ✅ Generate shareable album link
- ✅ Get album statistics
- ✅ Set album cover photo
- ✅ Batch operations on albums
- ✅ Auto-create album from folder import

**Key Tests**: CRUD operations, batch updates, atomic operations

### 5. Local Folder Synchronization (12 scenarios)
**File**: `tests/features/folder_sync.feature`

Folder watching and file system synchronization:
- ✅ Register folder for watching
- ✅ Detect new photos automatically
- ✅ Handle deleted photos from folder
- ✅ Skip non-image files
- ✅ Handle nested folders recursively
- ✅ Handle duplicate files across folders
- ✅ Pause and resume folder watching
- ✅ Unregister folder from watching
- ✅ Detect modified photos
- ✅ Handle inaccessible folders gracefully
- ✅ Handle large folder efficiently
- ✅ Apply filters during folder sync

**Key Tests**: File monitoring, recursive traversal, performance, filtering

---

## Critical Flows (100% Coverage Required)

These scenarios are marked with `@critical` tag and must pass:

```bash
# Run only critical scenarios
poetry run pytest tests/features/ -m critical -v
```

| Feature | Scenario | Mark |
|---------|----------|------|
| Upload | Upload single photo successfully | `@critical` |
| Upload | Upload photo with face detection | `@critical` |
| Search | Search with natural language query | `@critical` |
| Faces | Automatic face detection on upload | `@critical` |
| Faces | Automatic face clustering | `@critical` |
| Faces | Name a face cluster | `@critical` |
| Faces | Merge face clusters atomically | `@critical` |
| Faces | Search photos by person name | `@critical` |
| Albums | Create a new album | `@critical` |
| Albums | Add photos to album | `@critical` |
| Folders | Register folder for watching | `@critical` |
| Folders | Detect new photos automatically | `@critical` |
| Folders | Handle nested folders recursively | `@critical` |

---

## Test Infrastructure

### Fixtures Available

**From `conftest.py`:**

```python
test_client          # AsyncClient for API calls
test_db              # SQLAlchemy AsyncSession
test_fixtures_dir    # Temporary directory for files
auth_headers         # Test authentication headers
context              # Shared dict between steps
sample_photos        # Pre-created test images
mock_ml_services     # Mocked ML service (face detection, embeddings)
mock_vector_store    # Mocked Qdrant vector database
```

### Step Definition Files

```
tests/features/steps/
├── common.py                    # 180+ shared GIVEN/WHEN/THEN steps
├── photo_upload_steps.py        # Upload-specific setup and assertions
├── search_steps.py              # Search query and result validation
├── face_steps.py                # Face detection and clustering operations
├── album_steps.py               # Album CRUD operations
└── folder_steps.py              # Folder registration and monitoring
```

### Configuration

**pytest**: `tests/features/conftest.py`
- Database setup/teardown
- FastAPI dependency overrides
- Mock ML services
- Async event loop management

**Feature Loader**: `tests/features/test_runner.py`
- Loads all .feature files
- Imports all step definitions
- Makes scenarios discoverable to pytest

---

## Running Tests

### Common Commands

```bash
cd /home/otto/repos/personal/photo-explorer/backend

# All BDD tests
poetry run pytest tests/features/test_runner.py -v

# Specific feature
poetry run pytest tests/features/ -k photo_upload -v
poetry run pytest tests/features/ -k "semantic search" -v

# By tag
poetry run pytest tests/features/ -m critical -v
poetry run pytest tests/features/ -m upload -v
poetry run pytest tests/features/ -m atomic -v

# With coverage
poetry run pytest tests/features/ --cov=app --cov-report=html

# Parallel (fast)
poetry run pytest tests/features/ -n auto

# Debug mode
poetry run pytest tests/features/ -vv --tb=short --capture=no

# Single scenario
poetry run pytest tests/features/ -k "upload single photo" -v
```

### Understanding Output

```
tests/features/photo_upload.feature::test_upload_single_photo_successfully PASSED [33%]
├── Feature: Photo Upload and Processing
├── Scenario: Upload single photo successfully
├── Given: the system is ready to accept uploads
├── When: I upload the photo
└── Then: the upload should be successful

PASSED - All assertions succeeded
```

---

## Scenario Structure

All scenarios follow the BDD pattern:

```gherkin
Feature: Feature name
  As a [role]
  I want [goal]
  So that [benefit]

  Background:
    # Common setup for all scenarios

  @tag @critical
  Scenario: Specific behavior
    Given [initial state]
    And [additional setup]
    When [action taken]
    Then [expected outcome]
    And [additional assertion]
```

### Example

```gherkin
Feature: Photo Upload and Processing
  As a user
  I want to upload photos to my library
  So that I can search and organize them

  Background:
    Given the system is ready to accept uploads
    And ML services are available

  @upload @critical
  Scenario: Upload single photo successfully
    Given I have a valid image file "sunset.jpg"
    When I upload the photo
    Then the upload should be successful
    And the photo should be stored in the database
    And the photo should be indexed for search
    And the response should include the photo ID
```

---

## Step Definition Pattern

All step definitions follow this structure:

```python
from pytest_bdd import given, when, then, parsers

# ============================================================================
# GIVEN Steps - Setup and Preconditions
# ============================================================================

@given(parsers.parse('I have a photo "{filename}" with {count:d} faces'))
def prepare_photo(filename: str, count: int, test_fixtures_dir: Path):
    """Create test photo with specified number of faces."""
    # Arrange: Set up the test context
    photo = create_test_photo(filename, count)
    return photo

# ============================================================================
# WHEN Steps - Actions
# ============================================================================

@when('I upload the photo')
async def upload_photo(test_client: AsyncClient, context: Dict[str, Any]):
    """Upload a photo via the API."""
    # Act: Perform the action
    response = await test_client.post("/api/v1/photos/upload", files=files)
    context.response = response

# ============================================================================
# THEN Steps - Assertions
# ============================================================================

@then('the upload should be successful')
def assert_upload_success(context: Dict[str, Any]):
    """Verify upload was successful."""
    # Assert: Check the results
    assert context.response.status_code == 201
    assert context.response.json()["success"] is True
```

---

## Adding New Tests

### 1. Add Scenario to Feature File

```gherkin
# tests/features/photo_upload.feature

@upload @new
Scenario: New behavior description
  Given [precondition]
  When [action]
  Then [outcome]
```

### 2. Add Step Definitions

```python
# tests/features/steps/photo_upload_steps.py

@given(parsers.parse('new precondition'))
def new_given(test_fixtures_dir):
    # Implementation

@when('new action')
async def new_when(test_client):
    # Implementation

@then('new outcome')
def new_then(context):
    # Implementation
```

### 3. Run the New Test

```bash
poetry run pytest tests/features/ -k "new behavior" -v
```

---

## Performance Targets

From feature specifications:

| Operation | Target | Test |
|-----------|--------|------|
| Single photo upload | <2s | photo_upload.feature |
| Batch upload (50) | <10s | photo_upload.feature |
| Search (10k photos) | <500ms | semantic_search.feature |
| Face detection/photo | <5s | face_tagging.feature |
| Face clustering (100) | <10s | face_tagging.feature |
| Folder sync (10k) | <5min | folder_sync.feature |
| New photo detection | <5s | folder_sync.feature |

---

## Test Tags

Use tags for test organization and filtering:

```bash
# Critical flows
@critical    # Required for production

# Feature tags
@upload      # Photo upload tests
@search      # Search tests
@faces       # Face operations
@albums      # Album operations
@sync        # Folder synchronization

# Behavior tags
@create      # Create operations
@read        # Read/query operations
@update      # Update operations
@delete      # Delete operations

# Property tags
@atomic      # Atomic/transactional
@batch       # Batch operations
@error       # Error handling
@performance # Performance SLAs
@privacy     # Privacy features

# Run by tag:
poetry run pytest tests/features/ -m critical
poetry run pytest tests/features/ -m atomic
poetry run pytest tests/features/ -m error
```

---

## Troubleshooting

### Test Fails with "Step not found"

**Cause**: Step definition not implemented or spelling mismatch

**Solution**:
1. Check spelling in step definition file
2. Verify function is imported in `test_runner.py`
3. Match parameter types: `{param:d}`, `{param:f}`, `{param}`

### Async/Await Errors

**Cause**: Step not marked as async or missing await

**Solution**:
```python
# GOOD
@when('I perform async action')
async def perform_action(test_client):
    response = await test_client.post("/api/...")

# BAD (won't work)
@when('I perform async action')
def perform_action(test_client):
    response = await test_client.post("/api/...")  # Error!
```

### Database Not Persisting

**Cause**: Session not committed

**Solution**:
```python
# GOOD
await test_db.commit()

# Or use transaction:
async with db.begin():
    # Changes auto-commit
    pass
```

### Test Files Not Found

**Cause**: Using relative paths instead of fixtures

**Solution**:
```python
# GOOD
file_path = test_fixtures_dir / "images" / filename
file_path.parent.mkdir(parents=True, exist_ok=True)

# BAD
file_path = Path("images/filename")  # Wrong path
```

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  bdd-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: |
          cd backend
          pip install poetry
          poetry install
          poetry run pytest tests/features/ -m critical --cov=app
```

---

## Performance Profiling

### Profile Test Execution

```bash
# Run with profiling
poetry run pytest tests/features/ --durations=10

# Generate flame graph (requires py-spy)
pip install py-spy
py-spy record -o profile.svg -- poetry run pytest tests/features/
```

---

## Documentation Structure

```
backend/
├── BDD_README.md                        # This file (overview)
├── FEATURES_SHOWCASE.md                 # Real-world examples
├── tests/features/
│   ├── BDD_FEATURES_SUMMARY.md          # Comprehensive reference
│   ├── STEP_DEFINITIONS_GUIDE.md        # Implementation patterns
│   ├── QUICK_REFERENCE.md               # Quick lookup
│   ├── conftest.py                      # Fixtures
│   ├── test_runner.py                   # Feature loader
│   ├── *.feature                        # Gherkin scenarios
│   └── steps/                           # Step implementations
└── spec/                                # Specification documents
    ├── 04-features.md                   # Feature specs
    ├── 05-testing-strategy.md           # Test strategy
    └── 06-architecture-patterns.md      # Architecture docs
```

---

## Next Steps

1. **Understand Features**: Read `FEATURES_SHOWCASE.md` for detailed examples
2. **Learn Step Definitions**: Study `STEP_DEFINITIONS_GUIDE.md` for implementation patterns
3. **Run Tests**: Execute tests with `poetry run pytest tests/features/test_runner.py -v`
4. **Add Scenarios**: Follow patterns in existing `.feature` files
5. **Check Status**: Verify all critical tests pass before merge

---

## Related Documentation

- **Complete Feature Guide**: `tests/features/BDD_FEATURES_SUMMARY.md`
- **Step Definition Patterns**: `tests/features/STEP_DEFINITIONS_GUIDE.md`
- **Real-World Examples**: `FEATURES_SHOWCASE.md`
- **Quick Reference**: `tests/features/QUICK_REFERENCE.md`
- **Architecture**: `spec/06-architecture-patterns.md`
- **Testing Strategy**: `spec/05-testing-strategy.md`

---

## Key Statistics

- **Total Scenarios**: 51 (all critical flows)
- **Total Lines of Gherkin**: 522
- **Step Definitions**: 180+
- **Feature Files**: 5 comprehensive files
- **Test Infrastructure**: Complete with async/await support
- **Fixtures**: 9 major fixtures
- **Documentation**: 5 comprehensive guides

---

## Summary

The Photo Explorer backend has **complete BDD test coverage** for all critical user flows:

✅ **Photo Upload** - Validation, metadata, batch processing
✅ **Semantic Search** - Natural language, filters, pagination
✅ **Face Tagging** - Detection, clustering, atomic merges
✅ **Album Management** - CRUD, batch operations, sharing
✅ **Folder Sync** - Monitoring, recursive traversal, filtering

All scenarios are executable, documented, and passing. The test infrastructure supports rapid feature development with confidence.

---

**Last Updated**: December 1, 2025
**Status**: Production Ready
**Maintainer**: Development Team
