# BDD Tests Quick Reference

## Running Tests

```bash
cd /home/otto/repos/personal/photo-explorer/backend

# All BDD tests
poetry run pytest tests/features/test_runner.py -v

# Specific feature
poetry run pytest tests/features/ -k photo_upload -v

# Critical scenarios only
poetry run pytest tests/features/ -m critical -v

# With coverage
poetry run pytest tests/features/ --cov=app --cov-report=html

# Parallel execution (fast)
poetry run pytest tests/features/ -n auto

# Verbose debugging
poetry run pytest tests/features/ -vv --tb=short --capture=no
```

## Feature Files Overview

| Feature | Scenarios | Coverage |
|---------|-----------|----------|
| **photo_upload.feature** | 8 | Upload, validation, batch, metadata |
| **semantic_search.feature** | 9 | Text search, filters, pagination |
| **face_tagging.feature** | 10 | Detection, clustering, naming, merge |
| **album_management.feature** | 12 | CRUD, sharing, batch operations |
| **folder_sync.feature** | 12 | Registration, monitoring, sync |
| **TOTAL** | **51** | All critical flows |

## Critical Scenarios (Mark: @critical)

```gherkin
photo_upload.feature:
  ✓ Upload single photo successfully
  ✓ Upload photo with face detection

semantic_search.feature:
  ✓ Search with natural language query

face_tagging.feature:
  ✓ Automatic face detection on upload
  ✓ Automatic face clustering
  ✓ Name a face cluster
  ✓ Merge face clusters atomically
  ✓ Search photos by person name

album_management.feature:
  ✓ Create a new album
  ✓ Add photos to album

folder_sync.feature:
  ✓ Register folder for watching
  ✓ Detect new photos automatically
  ✓ Handle nested folders recursively
```

## Step Definition Files

```
tests/features/steps/
├── common.py              # Shared GIVEN/WHEN/THEN (180+ definitions)
├── photo_upload_steps.py  # Upload-specific
├── search_steps.py        # Search queries
├── face_steps.py          # Face operations
├── album_steps.py         # Album CRUD
└── folder_steps.py        # Folder sync
```

## Common Fixtures

```python
# From conftest.py
test_client          # AsyncClient for API calls
test_db              # SQLAlchemy AsyncSession
test_fixtures_dir    # Temporary directory for files
auth_headers         # Authentication headers
context              # Shared dict between steps
sample_photos        # Pre-created test images
mock_ml_services     # Mocked ML service
mock_vector_store    # Mocked vector DB
```

## Common GIVEN Steps

```gherkin
Given the system is ready to accept uploads
Given ML services are available
Given the vector database is initialized
Given face detection service is enabled
Given I am authenticated as a user
Given I have a valid image file "filename.jpg"
Given I have a photo "filename" containing faces
Given I have a photo "filename" with EXIF data
Given I have already uploaded "filename" with hash "abc123"
Given I have photos in my library:
  | photo_id | filename      | date_taken |
  | photo_1  | vacation.jpg  | 2024-07-01 |
Given I have an album "Album Name"
```

## Common WHEN Steps

```gherkin
When I upload the photo
When I upload all photos in batch
When I search for "query"
When I search for "query" with filters:
  | filter        | value  |
When I create an album named "Album Name"
When I add photos to the album
When I remove "photo_id" from the album
When I delete the album
When I register "/folder/path" for watching
When I merge "cluster_1" into "cluster_2"
When I name the cluster "Person Name"
```

## Common THEN Steps

```gherkin
Then the upload should be successful
Then the photo should be stored in the database
Then the photo should be indexed for search
Then the upload should be rejected with status 400
Then the error message should contain "text"
Then faces should be detected in the photo
Then results should be ranked by semantic similarity
Then the album should be created successfully
Then the album should contain 5 photos
Then the folder should be added to watched folders
```

## Scenario Tags

Use `-m` flag to run by tag:

```bash
# Critical flows only
poetry run pytest tests/features/ -m critical

# Upload tests
poetry run pytest tests/features/ -m upload

# Face tests
poetry run pytest tests/features/ -m faces

# Atomic operations
poetry run pytest tests/features/ -m atomic

# Error handling
poetry run pytest tests/features/ -m error
```

## Example: Running Specific Scenarios

```bash
# Single scenario by name
poetry run pytest tests/features/ -k "upload single photo" -v

# All upload scenarios
poetry run pytest tests/features/ -k photo_upload -v

# All critical scenarios
poetry run pytest tests/features/ -m critical -v

# Batch operations
poetry run pytest tests/features/ -m batch -v

# Performance tests
poetry run pytest tests/features/ -m performance -v
```

## Adding a New Test

1. **Add scenario to .feature file**:
```gherkin
Scenario: New behavior
  Given [precondition]
  When [action]
  Then [outcome]
```

2. **Add steps to appropriate steps/*.py**:
```python
from pytest_bdd import given, when, then, parsers

@given(parsers.parse('I have {count:d} items'))
def setup_items(count: int, context):
    context.items = [create_item() for _ in range(count)]

@when('I perform action')
async def perform_action(test_client, context):
    response = await test_client.post("/api/action")
    context.response = response

@then('action should succeed')
def assert_success(context):
    assert context.response.status_code == 200
```

3. **Run the test**:
```bash
poetry run pytest tests/features/ -k "new behavior" -v
```

## Test Data Directory

```
tests/features/
├── conftest.py      # Creates temp dirs and fixtures
└── test_runner.py

# Test files created dynamically in:
/tmp/pytest-{random}/test_{scenario}/fixtures/
├── images/          # Test photos created here
└── files/           # Test files created here
```

## Key Test Files

**Feature Files** (522 lines, 51 scenarios):
- `/home/otto/repos/personal/photo-explorer/backend/tests/features/photo_upload.feature`
- `/home/otto/repos/personal/photo-explorer/backend/tests/features/semantic_search.feature`
- `/home/otto/repos/personal/photo-explorer/backend/tests/features/face_tagging.feature`
- `/home/otto/repos/personal/photo-explorer/backend/tests/features/album_management.feature`
- `/home/otto/repos/personal/photo-explorer/backend/tests/features/folder_sync.feature`

**Step Definitions** (180+ implementations):
- `/home/otto/repos/personal/photo-explorer/backend/tests/features/steps/common.py`
- `/home/otto/repos/personal/photo-explorer/backend/tests/features/steps/photo_upload_steps.py`
- `/home/otto/repos/personal/photo-explorer/backend/tests/features/steps/search_steps.py`
- `/home/otto/repos/personal/photo-explorer/backend/tests/features/steps/face_steps.py`
- `/home/otto/repos/personal/photo-explorer/backend/tests/features/steps/album_steps.py`
- `/home/otto/repos/personal/photo-explorer/backend/tests/features/steps/folder_steps.py`

**Configuration**:
- `/home/otto/repos/personal/photo-explorer/backend/tests/features/conftest.py` - Fixtures
- `/home/otto/repos/personal/photo-explorer/backend/tests/features/test_runner.py` - Loader

## Documentation Files

- `BDD_FEATURES_SUMMARY.md` - Complete feature overview
- `STEP_DEFINITIONS_GUIDE.md` - Implementation patterns
- `QUICK_REFERENCE.md` - This file

## Performance Targets (from features)

| Operation | Target | Test |
|-----------|--------|------|
| Photo upload | <2s | single photo |
| Batch upload | <10s | 50 photos |
| Search (10k photos) | <500ms | semantic_search |
| Face detection | <5s | per photo |
| Face clustering | <10s | 100 faces |
| Folder sync | <5min | 10k photos |
| New photo detection | <5s | file monitoring |

## Troubleshooting

### Test fails with "Step not found"
- Check step definition spelling in steps/*.py
- Ensure it's imported in test_runner.py
- Match parameter types: `{param:d}`, `{param:f}`, `{param}`

### Async errors
- Mark step functions as `async def`
- Use `await` for all async calls
- Pass fixtures that support async

### Database errors
- Use `test_db` fixture for queries
- Commit after writes: `await test_db.commit()`
- Use SQLAlchemy select() not raw SQL

### File not found
- Use `test_fixtures_dir` fixture
- Files created in temp dir per test
- Check path construction (Path objects)

## Useful Commands

```bash
# List all tests
poetry run pytest tests/features/ --collect-only -q

# Run with detailed output
poetry run pytest tests/features/ -vv --tb=short --capture=no

# Run single test
poetry run pytest tests/features/test_runner.py::test_upload_single_photo_successfully -v

# Generate coverage HTML
poetry run pytest tests/features/ --cov=app --cov-report=html
# Open htmlcov/index.html

# Run without output buffering (see prints)
poetry run pytest tests/features/ -s

# Stop on first failure
poetry run pytest tests/features/ -x

# Run last failed
poetry run pytest tests/features/ --lf
```

## Architecture Diagram

```
Feature File (Gherkin)
        ↓
pytest-bdd parser
        ↓
Step Definition Functions
        ↓
     Fixtures
        ↓
   ┌─────────────┬─────────────┬──────────────┐
   ↓             ↓              ↓               ↓
test_client   test_db    test_fixtures_dir   context
  (API)      (Database)     (Files)         (Sharing)
   ↓             ↓              ↓
  FastAPI    SQLAlchemy    PIL/File I/O
   ↓             ↓              ↓
  Domain   Repositories    File System
 Models      (Adapters)
```

---

**Last Updated**: December 1, 2025
**Status**: Production Ready
**Coverage**: 51 scenarios, 180+ step definitions, 5 critical flows
