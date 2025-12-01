# Step Definitions Implementation Guide

This guide provides detailed documentation for implementing and maintaining BDD step definitions for the Photo Explorer backend.

## Directory Structure

```
tests/features/
├── conftest.py                      # Pytest configuration and fixtures
├── test_runner.py                   # Feature file loader for pytest-bdd
├── STEP_DEFINITIONS_GUIDE.md        # This file
├── *.feature                        # 5 Gherkin feature files
└── steps/
    ├── __init__.py
    ├── common.py                    # Shared GIVEN/WHEN/THEN steps (180+ definitions)
    ├── photo_upload_steps.py        # Photo upload specific steps
    ├── search_steps.py              # Search feature steps
    ├── face_steps.py                # Face detection/tagging steps
    ├── album_steps.py               # Album management steps
    └── folder_steps.py              # Folder synchronization steps
```

## Step Definition Pattern

All step definitions follow this structure:

```python
from pytest_bdd import given, when, then, parsers
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# ============================================================================
# GIVEN Steps - Setup and Preconditions
# ============================================================================

@given(parsers.parse('some precondition'))
def setup_precondition(fixture_name: Type, context: Dict[str, Any]) -> ReturnType:
    """
    Docstring describing what this step does.

    Args:
        fixture_name: Description of fixture
        context: Shared context dictionary between steps

    Returns:
        Value to use in subsequent steps
    """
    # Arrange: Set up the test context
    context.data = "value"
    return context.data

# ============================================================================
# WHEN Steps - Actions
# ============================================================================

@when(parsers.parse('I perform action "{param}"'))
async def perform_action(
    param: str,
    test_client: AsyncClient,
    context: Dict[str, Any]
) -> None:
    """
    Execute the action being tested.

    Args:
        param: Parameter from Gherkin step
        test_client: AsyncClient for API calls
        context: Shared context dictionary
    """
    # Act: Perform the action
    response = await test_client.post("/api/endpoint", json={"param": param})
    context.response = response
    context.result = response.json()

# ============================================================================
# THEN Steps - Assertions
# ============================================================================

@then(parsers.parse('outcome should be "{expected}"'))
def assert_outcome(expected: str, context: Dict[str, Any]) -> None:
    """
    Verify the expected outcome.

    Args:
        expected: Expected value from Gherkin step
        context: Shared context dictionary
    """
    # Assert: Check the results
    assert context.result["status"] == expected
```

## Available Fixtures

From `conftest.py`:

```python
@pytest.fixture(scope="function")
async def test_db() -> AsyncSession:
    """Clean database session for each test."""
    # Use for database queries and assertions

@pytest.fixture
async def test_client(test_db: AsyncSession) -> AsyncClient:
    """AsyncClient with dependency overrides."""
    # Use for API calls

@pytest.fixture
def test_fixtures_dir(tmp_path: Path) -> Path:
    """Temporary directory for test files."""
    # Use for file creation

@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Test authentication headers."""
    # Use for authenticated API calls

@pytest.fixture
def context() -> Dict[str, Any]:
    """Shared context between steps in same scenario."""
    # Use to share data between Given/When/Then steps

@pytest.fixture
def sample_photos(test_fixtures_dir: Path) -> Dict[str, Path]:
    """Pre-created test image files."""
    # Use for photo-based scenarios
```

## Parameterized Steps with parsers

### Parse Simple Parameters

```python
# In feature file:
# When I upload <count> photos
# or: When I upload 5 photos

@when(parsers.parse('I upload {count:d} photos'))
def upload_multiple(count: int, context):
    context.count = count

# Supported types:
# {param:d}      - Integer
# {param:f}      - Float
# {param:w}      - Word (no spaces)
# {param}        - String (default)
```

### Parse Complex Parameters

```python
# In feature file:
# When I search for "sunset" with limit 10

@when(parsers.parse('I search for "{query}" with limit {limit:d}'))
def search_with_limit(query: str, limit: int, context):
    context.query = query
    context.limit = limit
```

### Parse Data Tables

```python
# In feature file:
# When I upload these photos:
#   | filename    | type   |
#   | photo1.jpg  | image  |
#   | photo2.png  | image  |

@when('I upload these photos:')
def upload_data_table(request):
    # request.getfixturevalue('request') gives access to the table
    table = request.getfixturevalue('request').getfixturevalue('pytestbdd_definition').table
    for row in table:
        filename = row['filename']
        photo_type = row['type']
```

## Common Implementation Patterns

### 1. File Creation Step

```python
from pathlib import Path
from PIL import Image

@given(parsers.parse('I have a valid image file "{filename}"'))
def create_test_image(filename: str, test_fixtures_dir: Path) -> Path:
    """Create a test image file."""
    file_path = test_fixtures_dir / "images" / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create image with PIL
    img = Image.new("RGB", (200, 200), color=(255, 100, 50))
    img.save(file_path, "JPEG")

    assert file_path.exists()
    return file_path
```

### 2. API Request Step

```python
from httpx import AsyncClient

@when('I upload the photo')
async def upload_photo(
    test_client: AsyncClient,
    context: Dict[str, Any]
) -> None:
    """Upload a photo via API."""
    file_path = context.get("file_path")

    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "image/jpeg")}
        response = await test_client.post(
            "/api/v1/photos/upload",
            files=files
        )

    context.response = response
    context.photo_data = response.json()
```

### 3. Database Assertion Step

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities import Photo

@then('the photo should be stored in the database')
async def assert_photo_persisted(
    context: Dict[str, Any],
    test_db: AsyncSession
) -> None:
    """Verify photo was saved to database."""
    photo_id = context.photo_data["data"]["id"]

    # Query the database
    from sqlalchemy import select
    stmt = select(Photo).where(Photo.id == photo_id)
    result = await test_db.execute(stmt)
    photo = result.scalar_one_or_none()

    assert photo is not None
    assert photo.filename == context.photo_data["data"]["filename"]
```

### 4. API Error Assertion Step

```python
@then(parsers.parse('the upload should be rejected with status {status:d}'))
def assert_upload_failed(status: int, context: Dict[str, Any]) -> None:
    """Verify upload was rejected with specific status."""
    response = context.response

    assert response.status_code == status
    data = response.json()
    assert data.get("success") is False
    assert "error" in data
```

### 5. Search Results Assertion Step

```python
@then('results should be ranked by semantic similarity')
def assert_semantic_ranking(context: Dict[str, Any]) -> None:
    """Verify results are sorted by similarity score."""
    results = context.search_results

    scores = [r.get("similarity_score", 0) for r in results]

    # Check that scores are in descending order
    assert scores == sorted(scores, reverse=True)

    # Check minimum similarity threshold
    if scores:
        assert scores[0] >= 0.7
```

## Testing Database Changes

### Checking Entity Creation

```python
from sqlalchemy import select
from app.domain.entities import Photo

@then('the photo should be stored in the database')
async def verify_photo_created(context, test_db: AsyncSession):
    """Verify photo entity was created."""
    photo_id = context.response.json()["data"]["id"]

    stmt = select(Photo).where(Photo.id == photo_id)
    result = await test_db.execute(stmt)
    photo = result.scalar_one_or_none()

    assert photo is not None
    assert photo.filename == context.expected_filename
    assert photo.storage_path is not None
```

### Checking Entity Properties

```python
@then('the photo should have valid metadata')
async def verify_photo_metadata(context, test_db: AsyncSession):
    """Verify photo metadata was extracted."""
    photo_id = context.response.json()["data"]["id"]

    photo = await test_db.get(Photo, photo_id)

    assert photo.metadata is not None
    assert "camera_make" in photo.metadata
    assert "taken_at" in photo.metadata
```

### Checking Collection Operations

```python
@then('the album should contain {count:d} photos')
async def verify_album_photos(count: int, context, test_db: AsyncSession):
    """Verify album has expected photo count."""
    from app.domain.entities import Album
    from sqlalchemy import select, func

    album_id = context.album_data["id"]
    album = await test_db.get(Album, album_id)

    # Count photos in album
    stmt = select(func.count(Album.photos)).where(Album.id == album_id)
    result = await test_db.execute(stmt)
    photo_count = result.scalar()

    assert photo_count == count
```

## Error Handling Steps

### Asserting Specific Errors

```python
@then('the error message should contain "{text}"')
def assert_error_contains(text: str, context):
    """Verify error message contains expected text."""
    response = context.response

    assert response.status_code >= 400
    data = response.json()

    error_msg = data.get("error", {}).get("message", "")
    assert text.lower() in error_msg.lower(), \
        f"Expected '{text}' in '{error_msg}'"
```

### Asserting No Errors

```python
@then('no errors should be logged')
def assert_no_errors(context, caplog):
    """Verify no errors were logged."""
    assert "ERROR" not in caplog.text
    assert "CRITICAL" not in caplog.text
```

## Async Patterns

### Async Step Definition

```python
@when('I perform async operation')
async def async_operation(test_client: AsyncClient, context):
    """Perform async operation."""
    response = await test_client.post("/api/async-endpoint")
    context.async_result = response.json()
```

### Waiting for Async Completion

```python
import asyncio
import time

@then('the operation should complete within {seconds:d} seconds')
async def wait_for_completion(seconds: int, context):
    """Wait for async operation to complete."""
    start_time = time.time()

    # Poll for completion
    max_attempts = seconds * 10  # Check 10x per second
    for attempt in range(max_attempts):
        status = context.async_result.get("status")

        if status == "completed":
            return

        await asyncio.sleep(0.1)

    elapsed = time.time() - start_time
    assert False, f"Operation did not complete within {seconds}s (took {elapsed}s)"
```

## Performance Testing Steps

### Measuring Response Time

```python
import time

@when('I search for "{query}"')
async def search_with_timing(
    query: str,
    test_client: AsyncClient,
    context
):
    """Perform search and measure timing."""
    start_time = time.time()

    response = await test_client.get(
        "/api/v1/search",
        params={"q": query}
    )

    elapsed_ms = (time.time() - start_time) * 1000

    context.response = response
    context.response_time_ms = elapsed_ms

@then('the search should complete within {ms:d}ms')
def assert_response_time(ms: int, context):
    """Verify search response time."""
    actual_ms = context.response_time_ms

    assert actual_ms <= ms, \
        f"Search took {actual_ms}ms, expected <= {ms}ms"
```

## Mock/Patch Patterns

### Mocking External Services

```python
from unittest.mock import AsyncMock, patch

@given('face detection service is mocked')
def mock_face_detection(monkeypatch):
    """Mock the face detection service."""
    mock_service = AsyncMock()
    mock_service.detect.return_value = [
        {"bbox": [10, 10, 50, 50], "confidence": 0.95}
    ]

    monkeypatch.setattr(
        "app.services.ml.face_detector",
        mock_service
    )

    return mock_service
```

### Verifying Mocks Were Called

```python
@then('face detection should be called with the photo')
def assert_detection_called(context, mock_face_detection):
    """Verify face detection was invoked."""
    mock_face_detection.detect.assert_called_once()

    call_args = mock_face_detection.detect.call_args
    assert context.photo_data in call_args[0]
```

## Common Assertions

### Response Validation

```python
def assert_api_success(response):
    """Verify successful API response."""
    assert response.status_code in [200, 201]
    data = response.json()
    assert data.get("success") is True
    assert "data" in data

def assert_api_error(response, status: int):
    """Verify error API response."""
    assert response.status_code == status
    data = response.json()
    assert data.get("success") is False
    assert "error" in data
```

### Data Validation

```python
def assert_photo_data(photo_data: dict):
    """Verify photo response data structure."""
    required_fields = ["id", "filename", "created_at"]
    for field in required_fields:
        assert field in photo_data, f"Missing field: {field}"
        assert photo_data[field] is not None

def assert_search_results(results: list, min_count: int = 0):
    """Verify search results structure."""
    assert isinstance(results, list)
    assert len(results) >= min_count

    for result in results:
        assert "id" in result
        assert "similarity_score" in result
        assert 0.0 <= result["similarity_score"] <= 1.0
```

## Best Practices

### 1. Descriptive Step Names

```python
# GOOD - Clear intent
@given('I have uploaded 5 photos')
def uploaded_photos(context):
    pass

# AVOID - Vague
@given('photos exist')
def photos(context):
    pass
```

### 2. Single Responsibility

```python
# GOOD - One step per behavior
@given('I have a valid image file "test.jpg"')
def create_image(filename: str, test_fixtures_dir):
    create_test_image(filename, test_fixtures_dir)

@given('the ML service is available')
def ml_service_ready(test_client):
    response = test_client.get("/api/health")
    assert response.status_code == 200

# AVOID - Multiple responsibilities
@given('system is ready with image')
def setup_all(filename, test_fixtures_dir, test_client):
    create_test_image(filename, test_fixtures_dir)
    response = test_client.get("/api/health")
    assert response.status_code == 200
```

### 3. Use Context Efficiently

```python
# Store values for later steps
context.photo_id = response.json()["data"]["id"]
context.search_results = response.json()["data"]["results"]

# Retrieve in later steps
photo_id = context.photo_id
for result in context.search_results:
    assert result["id"] == photo_id or result["id"] != photo_id
```

### 4. Clean Error Messages

```python
# GOOD - Helpful error message
assert photo.filename == expected, \
    f"Photo filename mismatch: got '{photo.filename}', expected '{expected}'"

# AVOID - Cryptic assertion
assert photo.filename == expected
```

### 5. Proper Async Handling

```python
# GOOD - All async operations properly awaited
@when('I upload the photo')
async def upload_photo(test_client, context):
    response = await test_client.post("/api/upload", files=files)
    context.response = response

# AVOID - Mixed sync/async
@when('I upload the photo')
def upload_photo(test_client, context):  # Should be async
    response = await test_client.post("/api/upload")  # Won't work
```

## Debugging Steps

### Enable Verbose Logging

```bash
poetry run pytest tests/features/test_runner.py -vv --tb=short --capture=no
```

### Print Context for Debugging

```python
@when('I upload the photo')
async def upload_photo(test_client, context):
    """Upload with debug output."""
    response = await test_client.post("/api/upload", files=files)

    # Debug output
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body: {response.json()}")

    context.response = response
```

### Inspect Database State

```python
@then('the photo should be stored in the database')
async def debug_photo(context, test_db):
    """Debug database state."""
    photo_id = context.photo_data["data"]["id"]

    photo = await test_db.get(Photo, photo_id)

    # Debug output
    if photo is None:
        print(f"\nPhoto not found: {photo_id}")
        # List all photos in DB
        from sqlalchemy import select
        stmt = select(Photo)
        result = await test_db.execute(stmt)
        all_photos = result.scalars().all()
        print(f"Photos in DB: {[p.id for p in all_photos]}")

    assert photo is not None
```

## Performance Optimization

### Reuse Test Data

```python
# Instead of creating data in every step, use fixtures
@pytest.fixture(scope="function")
async def photo_with_faces(test_db):
    """Create photo with detected faces once per test."""
    photo = Photo.create_with_faces(3)
    test_db.add(photo)
    await test_db.commit()
    return photo

@when('I search for the person')
async def search_person(test_client, context, photo_with_faces):
    """Use pre-created photo."""
    context.photo_id = photo_with_faces.id
```

### Parallel Test Execution

```bash
# Run tests in parallel with pytest-xdist
poetry run pytest tests/features/ -n auto
```

## Troubleshooting

### Step Not Found Error

```
StepError: Step definition is not found for text: ...
```

**Solution**: Check step definition spelling matches exactly (including punctuation and parameters)

### Async Context Manager Error

```
RuntimeError: no running event loop
```

**Solution**: Mark step as `async def` and `await` all async calls

### Database Lock/Deadlock

```
ProgrammingError: another operation is in progress
```

**Solution**: Ensure proper session management, commit after writes

### Import Errors

```
ImportError: cannot import name 'Photo' from 'app.domain.entities'
```

**Solution**: Check import paths match project structure

---

## Related Files

- `conftest.py` - Fixture definitions
- `test_runner.py` - Feature file loader
- `*.feature` - Gherkin feature files
- `steps/*.py` - Step definition implementations

---

**Last Updated**: December 1, 2025
