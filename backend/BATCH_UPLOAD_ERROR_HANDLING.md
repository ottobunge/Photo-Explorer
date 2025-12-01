# Batch Photo Upload Error Handling and Cleanup

## Overview

The batch photo upload endpoint (`POST /api/v1/photos/upload`) implements comprehensive error handling and automatic cleanup to ensure data consistency and prevent orphaned files when upload failures occur.

## Architecture

### Atomicity Guarantee

The batch upload system provides atomicity guarantees:
- **Success Case**: All photos upload successfully, or...
- **Failure Case**: All successfully uploaded photos are automatically deleted, returning the system to its initial state

This prevents orphaned files and database records when batch operations fail partway through.

## Implementation Details

### 1. Tracking Uploaded Photos

During batch processing, successfully uploaded photo IDs are tracked in a list:

```python
successfully_uploaded_photo_ids: list[UUID] = []

for file in files:
    # ... validation ...
    photo = await photo_service.upload_photo(...)
    successfully_uploaded_photo_ids.append(photo.id.value)  # Track for cleanup
    # ... queue background tasks ...
```

**Key Principle**: Only photos that successfully persist to database and file storage are tracked.

### 2. Error Detection and Response

Two levels of error handling:

#### File-Level Errors (Caught and Logged)
Individual file validation failures are collected and returned to the client:
- Invalid MIME type
- Empty file
- File size exceeds limit
- Filename too long
- Missing content type

These **do not** trigger batch cleanup since the photo was never created.

#### Batch-Level Errors (Triggers Cleanup)
System-level errors that occur during batch processing:
- Database connection failure
- File storage failure
- Service layer exceptions
- Unexpected runtime errors

These **trigger automatic cleanup** of all successfully uploaded photos.

### 3. Cleanup Process

The `_cleanup_partial_uploads()` function handles cleanup:

```python
async def _cleanup_partial_uploads(
    photo_ids: list[UUID],
    photo_service: PhotoServiceDep,
) -> None:
    """Delete uploaded photos on batch failure."""
    for photo_id in photo_ids:
        try:
            deleted = await photo_service.delete_photo(photo_id)
            logger.info("Cleanup deleted photo", extra={"photo_id": str(photo_id)})
        except Exception as cleanup_error:
            logger.error(
                "Cleanup error during batch upload rollback",
                extra={"photo_id": str(photo_id), "error": str(cleanup_error)},
                exc_info=True,
            )
```

**Design Principles**:
- **Resilient**: Continues even if individual photo deletion fails
- **Observable**: Logs all cleanup attempts and failures
- **Complete**: Attempts to delete ALL tracked photos, not stopping on first failure

### 4. What Gets Deleted During Cleanup

The `PhotoService.delete_photo()` method handles:
1. **Database Records**: Deletes photo from database (cascades to faces, album associations)
2. **File Storage**: Deletes original photo file from storage
3. **Thumbnail Storage**: Deletes generated thumbnail image
4. **Vector Store**: Removes photo embedding from Qdrant

This ensures complete cleanup across all system layers.

## Cleanup Scenarios

### Scenario 1: File-Level Failure (No Cleanup)
```
Files: photo1.jpg (valid), document.pdf (invalid), photo2.jpg (valid)

Result:
- photo1.jpg: Uploaded
- document.pdf: Failed (invalid MIME type)
- photo2.jpg: Uploaded
- Cleanup: None (photos were created, request succeeded with partial results)
```

### Scenario 2: Batch-Level Failure After Partial Upload (Cleanup Triggered)
```
Files: photo1.jpg, photo2.jpg, photo3.jpg

Process:
- photo1.jpg: Uploaded successfully ✓
- photo2.jpg: Uploaded successfully ✓
- photo3.jpg: Database error while saving ✗

Response: 500 Error
Cleanup: Deletes photo1 and photo2 from storage and database
Result: System returns to initial state (no orphaned files)
```

### Scenario 3: Storage Failure During Cleanup (Resilient)
```
Files: photo1.jpg, photo2.jpg

Process:
- photo1.jpg: Uploaded ✓
- photo2.jpg: Uploaded ✓
- Batch error occurs

Cleanup:
- Delete photo1: Success ✓
- Delete photo2: Storage unavailable ✗ (continues anyway)

Logging: Both attempts logged with success/failure status
Recovery: photo2 orphaned in storage, but database record deleted
          (Orphaned files can be cleaned up by maintenance jobs)
```

## Testing Coverage

### Unit Tests
- `TestCleanupPartialUploads`: Tests the cleanup function in isolation
  - Deletes all photos
  - Continues on individual failures
  - Handles empty lists
  - Handles single photo
  - Handles all failures
  - Handles idempotent delete (already deleted)

### Integration Tests
- `TestBatchUploadCleanupIntegration`: Tests cleanup in full system context
  - Removes files from storage
  - Removes database records
  - Called on service errors
  - Idempotent on already-deleted photos
  - Continues on storage failures
  - Handles vector store failures
  - Maintains atomicity guarantee

### Test Files
- `/home/otto/repos/personal/photo-explorer/backend/tests/integration/api/test_photo_batch_upload_error_handling.py`

**Running Tests**:
```bash
# Run all batch upload tests
pytest tests/integration/api/test_photo_batch_upload_error_handling.py -v

# Run just cleanup tests
pytest tests/integration/api/test_photo_batch_upload_error_handling.py::TestBatchUploadCleanupIntegration -v

# Run just cleanup unit tests
pytest tests/integration/api/test_photo_batch_upload_error_handling.py::TestCleanupPartialUploads -v
```

## Key Guarantees

1. **Atomicity**: Batch operation is atomic from client perspective - either succeeds completely or rolls back
2. **Consistency**: No orphaned database records or files left in storage
3. **Observable**: All cleanup attempts logged for audit trail and debugging
4. **Resilient**: Cleanup continues even if individual operations fail
5. **Idempotent**: Safe to cleanup already-deleted photos

## Configuration

### File Size Limits
- Maximum file size: 50MB per file
- Configured in: `upload_photos()` function

### Batch Size Limits
- Maximum files per request: 100
- Configured in: `upload_photos()` function

### MIME Types Supported
- image/jpeg, image/jpg
- image/png
- image/gif
- image/webp
- image/bmp
- image/tiff
- image/heic, image/heif

## Related Code Files

- **Batch Upload Handler**: `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/api/routes/photos.py`
- **Cleanup Function**: `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/api/routes/photos.py` (_cleanup_partial_uploads function)
- **Photo Service Delete**: `/home/otto/repos/personal/photo-explorer/backend/app/application/services/photo_service.py`
- **Tests**: `/home/otto/repos/personal/photo-explorer/backend/tests/integration/api/test_photo_batch_upload_error_handling.py`

## Summary

The batch photo upload system implements a robust error handling strategy that:
1. Validates each file individually, collecting errors without stopping
2. Tracks successfully created photos for potential cleanup
3. Detects system-level failures that require rollback
4. Automatically deletes all successfully uploaded photos if any batch-level error occurs
5. Logs all cleanup attempts for observability and debugging
6. Continues cleanup despite individual operation failures
7. Provides atomicity guarantees to clients

This design prevents data inconsistency and ensures a clean system state even when failures occur during batch operations.
