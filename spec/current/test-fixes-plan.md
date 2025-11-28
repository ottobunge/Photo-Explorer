# Test Fixes Implementation Plan

**Date**: 2025-11-27
**Goal**: Fix all 99 failing tests (35 failed + 64 errors)
**Current Status**: 365/464 passing (78.7%)
**Target**: 100% passing or documented skips for infrastructure-dependent tests

---

## Test Failure Analysis

### Our New Code (2 failures) - HIGH PRIORITY
1. `test_detect_faces_success` - Mock configuration issue
2. `test_filter_by_isolated_person_returns_single_node` - Logic bug in SocialGraph

### Pre-existing Tests (97 failures/errors) - MEDIUM PRIORITY
1. Input validation tests (~9) - Pydantic v2 error message format
2. ML services tests (~10) - Infrastructure dependencies
3. Repository tests (~8) - Various query/logic issues
4. Infrastructure tests (~6) - Config/model/worker tests
5. Test errors (~64) - Import errors, fixture issues, etc.

---

## Implementation Phases

### Phase 1: Fix New Code Tests (2 tests)

#### 1.1 Fix `test_detect_faces_success` Mock Issue

**File**: `backend/tests/unit/application/services/test_photo_processing_service.py:307`

**Problem**:
- Mock `store_face_embedding` is silently failing
- Exception caught at line 504 in photo_processing_service.py
- Test expects `faces_in_vector_store == 1` but gets `0`

**Root Cause**:
- The mock setup on line 340 creates a new AsyncMock that may not be properly configured
- Need to verify the mock is called and doesn't raise exceptions

**Solution**:
```python
# Remove line 340 (redundant mock override)
# The fixture already sets up AsyncMock on line 64
# Just verify it's being called correctly

# OR: Add explicit side_effect=None to prevent exceptions
mock_vector_store.store_face_embedding = AsyncMock(return_value=None, side_effect=None)

# Add assertion to verify it was called
mock_vector_store.store_face_embedding.assert_called_once()
```

**Expected Result**: Test passes with `faces_in_vector_store == 1`

---

#### 1.2 Fix `test_filter_by_isolated_person_returns_single_node` Logic Bug

**File**: `backend/app/domain/value_objects/social_graph.py:42`

**Problem**:
- `filter_by_person()` only includes nodes that appear in edges
- Isolated nodes (no connections) are excluded
- Test expects Bob (isolated) to appear, but gets empty graph

**Root Cause**:
Lines 63-72 build `connected_person_ids` from edges only:
```python
connected_person_ids: set[UUID] = set()
for edge in relevant_edges:
    connected_person_ids.add(edge.person_a_id)
    connected_person_ids.add(edge.person_b_id)
```

If `relevant_edges` is empty, `connected_person_ids` is empty, so no nodes are included.

**Solution**:
```python
def filter_by_person(self, person_id: UUID) -> "SocialGraph":
    # Find all edges involving this person
    relevant_edges = [
        edge for edge in self.edges
        if edge.involves(person_id)
    ]

    # Find all people connected via these edges
    connected_person_ids: set[UUID] = {person_id}  # Always include target person
    for edge in relevant_edges:
        connected_person_ids.add(edge.person_a_id)
        connected_person_ids.add(edge.person_b_id)

    # Filter nodes to only those in the connected set
    filtered_nodes = [
        node for node in self.nodes
        if node.id.value in connected_person_ids
    ]

    # Include all edges between nodes in the filtered set
    filtered_edges = [
        edge for edge in self.edges
        if edge.person_a_id in connected_person_ids
        and edge.person_b_id in connected_person_ids
    ]

    return SocialGraph(nodes=filtered_nodes, edges=filtered_edges)
```

**Expected Result**: Test passes with Bob appearing as isolated node

---

### Phase 2: Fix Pydantic v2 Validation Tests (~9 tests)

**Files**: `backend/tests/unit/api/test_input_validation.py`

**Problem**:
Tests check for custom error messages like:
- "Album name cannot be empty"
- "Path traversal detected"

But Pydantic v2 returns generic messages:
- "String should have at least 1 character"

**Solution Options**:

**Option A**: Update test assertions to match Pydantic v2 messages
```python
# Before
assert "Album name cannot be empty" in str(exc_info.value)

# After
assert "String should have at least 1 character" in str(exc_info.value)
```

**Option B**: Add custom validators to Pydantic schemas
```python
from pydantic import field_validator

class AlbumCreateRequest(BaseModel):
    name: str

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Album name cannot be empty')
        return v
```

**Recommendation**: Option B - Keep meaningful error messages for better UX

**Tests to Fix**:
1. `test_album_create_empty_name_fails`
2. `test_album_photos_request_empty_list_fails`
3. `test_album_photos_request_too_many_fails`
4. `test_local_folder_create_path_traversal_fails`
5. `test_local_folder_create_empty_path_fails`
6. `test_search_request_empty_query_fails`
7. `test_cluster_name_request_empty_fails`
8. `test_sql_injection_patterns_rejected`
9. `test_path_traversal_patterns_rejected`

---

### Phase 3: Investigate Test Errors (~64 errors)

**Problem**: 64 tests have ERROR status (not FAILED)
- Usually means import errors, fixture problems, or setup issues

**Actions**:
1. Run tests with `-v` to see specific error messages
2. Check for:
   - Missing fixtures
   - Import errors
   - Database/infrastructure dependencies
   - Async fixture issues

**Example Investigation**:
```bash
poetry run pytest tests/unit/repositories/test_photo_repository_connector.py -v --tb=short
```

---

### Phase 4: Fix Repository Tests (~8 failures)

**Files**:
- `tests/unit/repositories/test_photo_repository_performance.py` (3 tests)
- `tests/unit/workers/tasks/test_connector_sync.py` (1 test)
- Others TBD after investigation

**Actions**:
1. Review each failing test
2. Check if they conflict with our batch operation changes
3. Update mocks if repository interfaces changed
4. Fix query logic if needed

---

### Phase 5: ML Services Tests (~10 failures)

**File**: `tests/unit/adapters/outbound/ml/test_ml_services.py`

**Problem**: Likely need actual ML models or heavy mocking

**Action**:
1. Check if tests require model files
2. Add `@pytest.mark.skip` if infrastructure-dependent
3. Or mock the underlying model calls properly

---

### Phase 6: Infrastructure Tests (~6 failures)

**Files**:
- `tests/unit/infrastructure/test_models.py` (2 tests)
- `tests/unit/critical_fixes/test_critical_fixes.py` (3 tests)
- Others TBD

**Actions**:
1. Review each test
2. Update for current implementation
3. Fix or document as infrastructure-dependent

---

## Implementation Order

1. ✅ **Phase 1.1**: Fix `test_detect_faces_success` mock (5 min)
2. ✅ **Phase 1.2**: Fix `filter_by_person` logic bug (10 min)
3. ✅ **Phase 2**: Fix Pydantic v2 validation tests (30 min)
4. ✅ **Phase 3**: Investigate and categorize test errors (20 min)
5. ✅ **Phase 4**: Fix repository tests (30 min)
6. ⏭️ **Phase 5**: Handle ML services tests (skip if infra-dependent) (15 min)
7. ⏭️ **Phase 6**: Fix infrastructure tests (20 min)

**Estimated Total Time**: 2-3 hours

---

## Success Criteria

- [ ] Our 2 new tests passing (100%)
- [ ] Pydantic validation tests passing (9 tests)
- [ ] Test errors reduced to 0 (64 → 0)
- [ ] Repository tests passing or documented (8 tests)
- [ ] ML/Infrastructure tests passing or properly skipped
- [ ] **Overall**: >95% tests passing, remaining documented as infra-dependent

---

## Testing Commands

```bash
# Run all unit tests
poetry run pytest tests/unit/ -v --tb=short

# Run specific failing tests
poetry run pytest tests/unit/application/services/test_photo_processing_service.py::TestDetectFaces::test_detect_faces_success -v

# Run with coverage
poetry run pytest tests/unit/ --cov=app --cov-report=term-missing

# Quick check of our fixes
poetry run pytest tests/unit/application/services/ tests/unit/domain/value_objects/ -v
```

---

## Post-Implementation

1. Run full test suite and capture results
2. Document any tests marked as skip with rationale
3. Update test coverage report
4. Commit all fixes with detailed message
