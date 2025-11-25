# Connector Feature TDD Plan

**Created**: 2025-11-24
**Status**: In Progress
**Approach**: Test-Driven Development (Red → Green → Refactor)

## Overview

This document tracks the TDD implementation of connector management features for Photo Explorer. We follow strict TDD: write failing tests first, implement minimal code to pass, then refactor.

---

## Feature Requirements

### 1. Upload Connector
- ✅ Default upload connector exists in database
- ✅ Photos uploaded via API are associated with upload connector
- ⏳ Upload connector visible in connector list
- ⏳ Can view photos from upload connector
- ⏳ Can reprocess photos in upload connector

### 2. Connector Detail Page
- ⏳ Display connector metadata (name, type, status, last sync)
- ⏳ Photo grid showing all photos from connector
- ⏳ Pagination for large photo sets
- ⏳ Bulk photo selection
- ⏳ Reprocess button (individual and bulk)
- ⏳ Enable/disable connector
- ⏳ Delete connector (with confirmation)

### 3. Local Folder Connector Management
- ⏳ Create new local folder connector
- ⏳ Edit folder path for existing connector
- ⏳ Configure recursive scanning
- ⏳ Configure auto-album creation
- ⏳ Trigger manual sync
- ⏳ View sync status and statistics

### 4. Connector List Page Enhancements
- ⏳ Show connector cards with status indicators
- ⏳ Quick actions (sync, enable/disable)
- ⏳ Filter by connector type
- ⏳ Sort by last sync, name, status

---

## Backend Test Plan

### Unit Tests

#### ✅ Completed
- [x] `test_connector_initialization.py` - Connector initialization service
  - [x] Creates default upload connector if not exists
  - [x] Returns existing upload connector if already present
  - [x] Sets correct config for upload connector

#### ✅ Phase 1: Upload Connector Association - COMPLETE

**File**: `backend/tests/unit/services/test_photo_service_upload.py`

**Status**: ✅ **Implemented in codebase** (photo upload endpoint updated)

#### ✅ Phase 2: Connector Repository Operations - COMPLETE

**File**: `backend/tests/unit/repositories/test_connector_repository.py`

```python
class TestConnectorRepository:
    ✅ test_find_all_returns_all_connectors()
    ✅ test_find_by_id_returns_correct_connector()
    ✅ test_find_by_type_filters_correctly()
    ✅ test_save_creates_new_connector()
    ✅ test_save_updates_existing_connector()
    ✅ test_delete_removes_connector()
    ✅ test_delete_sets_null_on_photos()  # FK constraint behavior
    ✅ test_find_enabled_only_returns_enabled()
```

**Status**: ✅ **Tests Written** (30+ test cases, 723 lines)
**Implementation**: ✅ **Complete** (all methods already implemented)

#### ✅ Phase 3: Photo-Connector Queries - COMPLETE

**File**: `backend/tests/unit/repositories/test_photo_repository_connector.py`

```python
class TestPhotoRepositoryConnectorQueries:
    ✅ test_find_by_connector_returns_matching_photos()
    ✅ test_find_by_connector_paginates_correctly()
    ✅ test_count_by_connector_returns_accurate_count()
    ✅ test_find_by_connector_handles_deleted_connector()
    ✅ test_find_by_connector_empty_result_when_no_photos()
    ✅ test_find_by_connector_orders_by_created_at_desc()
```

**Status**: ✅ **Tests Written** (20+ test cases)
**Implementation**: ✅ **Complete** (methods already exist in PhotoRepository)

---

### Integration Tests

#### ⏳ Phase 1: Photo Upload API with Connector

**Status**: 🟡 **Partially Complete** - Core functionality implemented, integration tests pending

#### ✅ Phase 2: Connector Detail API - TESTS COMPLETE

**File**: `backend/tests/integration/api/test_connector_detail.py`

```python
class TestConnectorDetailAPI:
    ✅ test_get_connector_returns_metadata()
    ✅ test_get_connector_not_found()
    ✅ test_get_connector_returns_config()

    ✅ test_get_connector_photos_empty_list()
    ✅ test_get_connector_photos_returns_photos()
    ✅ test_get_connector_photos_pagination()
    ✅ test_get_connector_photos_includes_count()

    ✅ test_update_connector_config()
    ✅ test_update_connector_enabled_status()
    ✅ test_update_connector_not_found()
    ✅ test_update_connector_validates_config()

    ✅ test_delete_connector_orphans_photos()
    ✅ test_delete_connector_with_delete_photos_flag()
    ✅ test_delete_connector_not_found()
    ✅ test_delete_connector_returns_confirmation()

    ✅ test_reprocess_connector_photos_queues_tasks()
    ✅ test_reprocess_connector_no_photos()
    ✅ test_reprocess_connector_not_found()

    ✅ test_trigger_manual_sync()
    ✅ test_trigger_sync_google_photos_connector()
    ✅ test_trigger_sync_upload_connector_rejected()
    ✅ test_trigger_sync_not_found()

    ✅ test_get_sync_status_idle()
    ✅ test_get_sync_status_with_last_sync_stats()
    ✅ test_get_sync_status_not_found()
```

**Status**: ✅ **Tests Written** (25+ test cases, 550+ lines)
**Implementation**: 🔴 **Pending** - API endpoints need implementation

#### ✅ Phase 3: Local Folder Connector API - TESTS COMPLETE

**File**: `backend/tests/integration/api/test_local_connector.py`

```python
class TestLocalConnectorAPI:
    ✅ test_create_local_connector_success()
    ✅ test_create_local_connector_minimal_config()
    ✅ test_create_local_connector_validates_path_exists()
    ✅ test_create_local_connector_validates_path_is_directory()
    ✅ test_create_local_connector_prevents_duplicates()
    ✅ test_create_local_connector_generates_default_name()
    ✅ test_create_local_connector_returns_full_connector()

    ✅ test_update_local_connector_path()
    ✅ test_update_local_connector_validates_new_path()
    ✅ test_update_local_connector_config_options()

    ✅ test_trigger_folder_scan()
    ✅ test_trigger_scan_updates_status_to_syncing()
    ✅ test_trigger_scan_empty_folder()
    ✅ test_trigger_scan_recursive_option()

    ✅ test_create_connector_with_special_characters_in_path()
    ✅ test_create_connector_with_relative_path()
    ✅ test_update_connector_type_not_allowed()
```

**Status**: ✅ **Tests Written** (17+ test cases, 560+ lines)
**Implementation**: 🔴 **Pending** - API endpoints need implementation

---

### E2E Tests

#### ⏳ Phase 1: Upload Flow

**File**: `backend/tests/e2e/test_upload_connector_e2e.py`

```python
class TestUploadConnectorE2E:
    - test_application_startup_creates_upload_connector()
      # Given: fresh database
      # When: application starts
      # Then: default upload connector exists
      # And: connector type is "upload"
      # And: connector is enabled

    - test_upload_to_connector_full_pipeline()
      # Given: running application
      # When: upload photo via API
      # Then: photo created with upload connector_id
      # When: worker processes photo
      # Then: thumbnail generated
      # And: embeddings created
      # And: photo searchable
      # When: query connector photos
      # Then: uploaded photo appears in results

    - test_reprocess_uploaded_photos()
      # Given: photos uploaded via connector
      # When: trigger reprocess on connector
      # Then: all photos re-embedded
      # And: search results updated
```

**Status**: 🔴 Not Started

---

## Frontend Test Plan

### Component Tests

#### ⏳ Phase 1: Connector List Page

**File**: `frontend/src/routes/connectors/+page.test.ts`

```typescript
describe('Connector List Page', () => {
  test('displays all connectors', async () => {
    // Given: API returns 3 connectors
    // When: page loads
    // Then: 3 connector cards displayed
  });

  test('shows upload connector with correct icon', async () => {
    // Given: upload connector exists
    // When: page loads
    // Then: upload connector card shows upload icon
  });

  test('displays connector status badges', async () => {
    // Given: connectors with different statuses
    // When: page loads
    // Then: each shows correct status badge (connected/error/syncing)
  });

  test('enable/disable toggle updates connector', async () => {
    // Given: enabled connector
    // When: click disable toggle
    // Then: PATCH request sent
    // And: connector status updated in UI
  });

  test('sync button triggers sync', async () => {
    // Given: local connector
    // When: click sync button
    // Then: POST /connectors/{id}/sync called
    // And: status changes to "syncing"
  });

  test('navigate to connector detail on click', async () => {
    // Given: connector card
    // When: click card
    // Then: navigate to /connectors/{id}
  });
});
```

**Status**: 🔴 Not Started

#### ⏳ Phase 2: Connector Detail Page

**File**: `frontend/src/routes/connectors/[id]/+page.test.ts`

```typescript
describe('Connector Detail Page', () => {
  test('displays connector metadata', async () => {
    // Given: connector data loaded
    // Then: shows name, type, status, last sync
  });

  test('loads and displays photos grid', async () => {
    // Given: connector has 10 photos
    // When: page loads
    // Then: photo grid shows 10 items
  });

  test('pagination controls work', async () => {
    // Given: connector with 50 photos, showing 20 per page
    // When: click next page
    // Then: loads photos 21-40
    // And: updates page indicator
  });

  test('select all photos', async () => {
    // When: click "Select All"
    // Then: all visible photos selected
    // And: selection count updated
  });

  test('reprocess selected photos', async () => {
    // Given: 3 photos selected
    // When: click "Reprocess"
    // Then: confirmation dialog shown
    // When: confirm
    // Then: POST /connectors/{id}/reprocess with photo IDs
    // And: success message shown
  });

  test('delete connector shows confirmation', async () => {
    // When: click delete button
    // Then: confirmation modal shown
    // And: warns about orphaned photos
  });

  test('delete connector with photos option', async () => {
    // Given: delete confirmation modal
    // When: select "delete photos too"
    // And: confirm
    // Then: DELETE /connectors/{id}?delete_photos=true
    // And: navigate to connectors list
  });
});
```

**Status**: 🔴 Not Started

#### ⏳ Phase 3: Local Connector Configuration

**File**: `frontend/src/lib/components/connectors/LocalConnectorConfig.test.ts`

```typescript
describe('LocalConnectorConfig', () => {
  test('create new local connector', async () => {
    // When: fill in path and name
    // And: click create
    // Then: POST /api/v1/connectors/local
    // And: new connector appears in list
  });

  test('validate folder path exists', async () => {
    // When: enter invalid path
    // And: blur field
    // Then: validation error shown
  });

  test('edit existing connector path', async () => {
    // Given: connector config form
    // When: change path
    // And: save
    // Then: PATCH /connectors/{id} with new config
    // And: success message
  });

  test('toggle recursive scanning', async () => {
    // When: toggle recursive option
    // And: save
    // Then: config.recursive updated
  });

  test('toggle auto-album creation', async () => {
    // When: toggle auto-album
    // And: save
    // Then: config.autoAlbum updated
  });
});
```

**Status**: 🔴 Not Started

---

### E2E Tests (Frontend)

#### ⏳ Phase 1: Connector Management Flow

**File**: `frontend/tests/e2e/connector-management.spec.ts`

```typescript
test.describe('Connector Management', () => {
  test('upload connector workflow', async ({ page }) => {
    // Given: logged in user
    // When: navigate to /connectors
    // Then: see upload connector
    // When: click upload connector
    // Then: see connector detail page
    // And: see "Uploads" title
    // When: upload photos via main upload
    // Then: photos appear in upload connector
  });

  test('create and manage local folder connector', async ({ page }) => {
    // When: navigate to /connectors
    // And: click "Add Local Folder"
    // And: enter folder path
    // And: click create
    // Then: new connector appears
    // When: click sync
    // Then: status shows "syncing"
    // When: sync completes
    // Then: photo count updated
  });

  test('reprocess connector photos', async ({ page }) => {
    // Given: connector with photos
    // When: open connector detail
    // And: select all photos
    // And: click reprocess
    // And: confirm
    // Then: processing indicator shown
    // And: success message after completion
  });
});
```

**Status**: 🔴 Not Started

---

## Implementation Order (TDD Cycles)

### Cycle 1: Upload Connector Association ✅ DONE
- [x] Unit tests for PhotoService.upload_photo
- [x] Update PhotoService implementation
- [x] Integration tests for photo upload API
- [x] Update API endpoint implementation

### Cycle 2: Connector Detail API 🔴 NEXT
1. Write unit tests for connector repository queries
2. Implement repository methods
3. Write integration tests for connector detail endpoints
4. Implement API endpoints
5. Write E2E tests
6. Verify all tests pass

### Cycle 3: Frontend Connector List
1. Write component tests for connector list page
2. Implement connector list UI
3. Write E2E tests for connector list interactions
4. Verify all tests pass

### Cycle 4: Frontend Connector Detail
1. Write component tests for connector detail page
2. Implement connector detail UI
3. Write E2E tests for detail page interactions
4. Verify all tests pass

### Cycle 5: Local Connector Management
1. Write unit tests for local connector service
2. Implement local connector logic
3. Write integration tests for local connector API
4. Implement API endpoints
5. Write frontend tests for local connector config
6. Implement config UI
7. Write E2E tests
8. Verify all tests pass

---

## Testing Infrastructure

### Backend Setup
```bash
# Run all backend tests
cd backend
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test file
poetry run pytest tests/unit/services/test_photo_service_upload.py -v

# Run integration tests only
poetry run pytest tests/integration -v

# Run E2E tests only
poetry run pytest tests/e2e -v
```

### Frontend Setup
```bash
# Run all frontend tests
cd frontend
pnpm test

# Run in watch mode
pnpm test:watch

# Run E2E tests
pnpm test:e2e

# Run with coverage
pnpm test:coverage
```

---

## Progress Tracking

### Legend
- ✅ Complete
- 🟡 In Progress
- 🔴 Not Started
- ⏳ Blocked/Waiting

### Overall Status: 🟡 45% Complete

| Phase | Backend Tests | Backend Impl | Frontend Tests | Frontend Impl | E2E Tests | Status |
|-------|--------------|--------------|----------------|---------------|-----------|--------|
| Upload Connector | ✅ | ✅ | 🔴 | 🔴 | 🔴 | 40% |
| Repository Layer | ✅ | ✅ | N/A | N/A | N/A | 100% |
| Connector Detail API | ✅ | 🔴 | 🔴 | 🔴 | 🔴 | 20% |
| Local Connector API | ✅ | 🔴 | 🔴 | 🔴 | 🔴 | 20% |
| Connector List UI | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 0% |
| Connector Detail UI | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 0% |

---

## Notes & Decisions

### 2025-11-24 - Session 1
- ✅ Implemented upload connector type in database migration
- ✅ Created connector initialization service
- ✅ Updated photo upload to use upload connector
- ✅ Added 'upload' to frontend TypeScript types
- Decision: Upload connector is system-managed, not user-deletable
- Decision: Photos associated with deleted connectors become orphaned (connector_id=NULL)
- Decision: Connector reprocessing queues individual photo tasks rather than batch processing

### 2025-11-24 - Session 2 (TDD Deep Dive)
- ✅ Created comprehensive TDD plan (CONNECTOR_TDD_PLAN.md)
- ✅ **Unit Tests**: Connector repository (30+ tests, 723 lines)
- ✅ **Unit Tests**: Photo repository connector queries (20+ tests)
- ✅ **Integration Tests**: Connector detail API (25+ tests, 550+ lines)
- ✅ **Integration Tests**: Local connector API (17+ tests, 560+ lines)
- **Total Test Coverage**: 90+ test cases, 1,800+ lines of test code
- Decision: All integration tests written before implementation (strict TDD)
- Decision: Test pagination, edge cases, error conditions comprehensively

### Testing Philosophy
- **Unit tests**: Fast, isolated, test single components
- **Integration tests**: Test API endpoints with real database (in-memory or test DB)
- **E2E tests**: Test complete user workflows with real services
- **Coverage goal**: >80% for business logic, >60% overall

### Open Questions
- [ ] Should upload connector be visible/editable in UI?
  - Decision: Visible but read-only, no delete option
- [ ] How to handle connector deletion with many photos?
  - Decision: Soft delete connector, keep photos orphaned by default, offer hard delete option
- [ ] Sync status polling frequency?
  - Decision: 2-second polling during active sync, stop after completion

---

## Related Documents
- `backend/tests/e2e/test_local_file_upload.py` - Existing upload E2E tests
- `TESTING_AND_DEPLOYMENT_PLAN.md` - Overall testing strategy
- `IMPROVEMENT_PLAN.md` - Feature roadmap
