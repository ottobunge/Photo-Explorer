# Service Tests - Quick Reference

## Test Files

- **FaceService Tests**: `tests/unit/application/services/test_face_service.py` (23 tests)
- **SearchService Tests**: `tests/unit/application/services/test_search_service.py` (22 tests)

## Running Tests

```bash
# All service tests
poetry run pytest tests/unit/application/services/test_face_service.py tests/unit/application/services/test_search_service.py -v

# With coverage
poetry run pytest tests/unit/application/services/ --cov=app.application.services --cov-report=term-missing

# Specific test class
poetry run pytest tests/unit/application/services/test_search_service.py::TestSemanticSearch -v

# Single test
poetry run pytest tests/unit/application/services/test_face_service.py::TestMergeClustersAtomic::test_merge_clusters_success -xvs
```

## Test Coverage

| Service | Coverage | Tests | Status |
|---------|----------|-------|--------|
| FaceService | 73% | 23 | PASSING |
| SearchService | 86% | 22 | PASSING |
| **Total** | **79%** | **45** | **PASSING** |

## FaceService Tests (23 tests)

### Merge Clusters (7 tests)
- Successful merge with atomic updates
- Missing target/source handling
- Self-merge prevention
- Vector store failure compensation
- Compensation failure logging

### Edge Cases (2 tests)
- Empty source list handling
- Bulk operations (100+ faces)

### Cluster Operations (6 tests)
- List clusters with filters
- Get/find clusters
- Name clusters
- Error handling

### Split Face (4 tests)
- Create new cluster with single face
- Remove from old cluster
- Delete empty old cluster
- Not found handling

### Move Face (4 tests)
- Update cluster assignment
- Target/source validation
- Empty cluster cleanup
- Error handling

## SearchService Tests (22 tests)

### Semantic Search (8 tests)
- Text query encoding and search
- Limit and offset pagination
- Album filtering
- Date range filtering
- Face filtering
- Indoor/outdoor filtering
- Empty results
- Missing photos in DB

### Find Similar (3 tests)
- Similar photo finding
- Limit respecting
- Missing embedding handling

### Search by Face (3 tests)
- Face detection and search
- No faces detected
- Photo deduplication

### Filtering Helpers (4 tests)
- Description filtering
- Processing status filtering
- Album ID filter building
- Connector ID filter building

### Combined Search (4 tests)
- Query delegation
- Filter-only search
- Date sorting
- Limit/offset application

## Test Patterns

### Setup Mocks
```python
@pytest.fixture
def mock_face_repo(self) -> Mock:
    repo = Mock(spec=FaceRepository)
    repo.find_cluster_by_id = AsyncMock()
    return repo
```

### Create Service
```python
@pytest.fixture
def service(self, mock_face_repo, mock_vector_store, mock_file_storage):
    return FaceService(mock_face_repo, mock_file_storage, mock_vector_store)
```

### Arrange-Act-Assert
```python
async def test_operation(self, service, mocks):
    # Arrange - setup test data
    mock_repo.return_value = expected_result

    # Act - execute operation
    result = await service.operation(args)

    # Assert - verify behavior
    assert result.property == expected_value
    mock_repo.assert_called_once()
```

### Error Testing
```python
with pytest.raises(EntityNotFoundException) as exc:
    await service.operation(invalid_id)
assert "Entity" in str(exc.value)
```

## Key Test Data Factory

```python
@staticmethod
def create_sample_photo(
    photo_id: UUID | None = None,
    is_indoor: bool | None = None,
    has_faces: bool = False,
    taken_at: datetime | None = None,
) -> Photo:
    """Create test photo with customizable properties."""
```

## Mock Objects Used

- **FaceRepository**: find_cluster_by_id, find_face_by_id, save_cluster, save_face, delete_cluster, etc.
- **VectorStore**: search_photos, search_faces, update_face_payload, update_face_payloads_batch, etc.
- **MLServices**: encode_text, detect_faces
- **PhotoRepository**: find_by_id, find_all

## Test Organization

- **Test Class**: Groups related tests for one operation or feature
- **Test Method**: Tests one specific behavior with descriptive name
- **Test Fixture**: Provides mocked dependencies and test data
- **Base Class**: Shares common fixtures across test classes

## Debugging

```python
# Run with output
poetry run pytest test_file.py -xvs

# Stop on first failure
poetry run pytest test_file.py -x

# Show print statements
poetry run pytest test_file.py -s

# Run with logging
poetry run pytest test_file.py --log-cli-level=DEBUG
```

## Common Assertions

```python
# Mock was called
mock.assert_called_once()

# Mock called with specific args
mock.assert_called_once_with(arg1, arg2)

# Mock called N times
assert mock.call_count == 3

# Get call arguments
args, kwargs = mock.call_args
first_call_args = mock.call_args_list[0]

# Verify exception
with pytest.raises(ExpectedException) as exc:
    await service.operation()
assert "expected message" in str(exc.value)
```

## Test Execution Results

```
============================= test session starts ==============================
collected 45 items

tests/unit/application/services/test_face_service.py ................. [ 42%]
tests/unit/application/services/test_search_service.py ................. [ 88%]
.....                                                                   [100%]

============================== 45 passed in 0.20s ==============================
```

## Notes

- All tests use AsyncMock for async operations
- No real database or external services are called
- Tests focus on business logic, not implementation
- Mocks verify correct delegation to dependencies
- Coverage targets: 80%+ for critical services
- Tests serve as living documentation
