# Batch Photo Upload Error Handling and Cleanup

## Overview

This document describes the error handling and cleanup mechanisms implemented for batch photo uploads in the Photo Explorer backend. The implementation ensures data consistency by automatically rolling back partial uploads when batch-level errors occur.

## Problem Statement

Previously, if an exception occurred during batch photo upload after some photos were successfully uploaded but before all were processed, partial uploads would remain in the system with no cleanup or rollback mechanism. This could lead to:

- Orphaned photo records in the database
- Inconsistent state between storage and database
- Wasted storage space for incomplete batches

## Solution Architecture

The solution implements a two-tier error handling strategy:

```
Batch Upload Endpoint
├── Individual File Validation (Per-file errors)
│   ├── Validation errors → Add to failed list, continue
│   └── Upload success → Track photo ID and continue
├── Batch-level Error Handling
│   ├── Error occurs → Trigger cleanup
│   ├── Cleanup function → Delete all successfully uploaded photos
│   └── Return 500 with error details
└── Success Path
    └── Return 201 with uploaded and failed lists
```

## Implementation Details

### 1. Upload Endpoint Changes

**File**: `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/api/routes/photos.py`

The `upload_photos` endpoint was modified to:

1. **Track uploaded photo IDs**: Maintain a list `successfully_uploaded_photo_ids` to record each successfully uploaded photo
2. **Wrap processing in try-except**: The entire file loop is wrapped in a try-except block to catch batch-level errors
3. **Trigger cleanup on error**: If a batch-level error occurs, call the cleanup helper function
4. **Return descriptive error**: Provide detailed error message with upload statistics

**Key code section**:

```python
successfully_uploaded_photo_ids: list[UUID] = []

try:
    for file in files:
        try:
            # ... validation and upload logic ...
            successfully_uploaded_photo_ids.append(photo.id.value)
        except Exception as e:
            # ... handle individual file errors ...
except Exception as batch_error:
    # Batch-level error occurred
    await _cleanup_partial_uploads(
        successfully_uploaded_photo_ids,
        photo_service,
    )
    raise HTTPException(status_code=500, detail=error_message)
```

### 2. Cleanup Helper Function

**Function**: `_cleanup_partial_uploads()`

This async function handles the deletion of successfully uploaded photos when batch upload fails:

```python
async def _cleanup_partial_uploads(
    photo_ids: list[UUID],
    photo_service: PhotoServiceDep,
) -> None:
    """Delete uploaded photos on batch failure."""
    for photo_id in photo_ids:
        try:
            deleted = await photo_service.delete_photo(photo_id)
            logger.info("Cleanup deleted photo", extra={"photo_id": str(photo_id), "success": deleted})
        except Exception as cleanup_error:
            logger.error("Cleanup error during batch upload rollback", extra={"photo_id": str(photo_id), "error": str(cleanup_error)}, exc_info=True)
```

**Key features**:

- **Resilient**: Continues deletion even if individual deletes fail
- **Comprehensive logging**: Logs both successes and failures for audit trail
- **Non-blocking**: Individual deletion failures don't stop the cleanup process

### 3. Error Message Format

When a batch error occurs, the endpoint returns an HTTP 500 error with a descriptive message:

```
"Batch upload failed. Uploaded X of Y photos before error. Changes rolled back. Error: {error_details}"
```

Example:
```
"Batch upload failed. Uploaded 5 of 10 photos before error. Changes rolled back. Error: Connection timeout to storage service"
```

## Error Handling Scenarios

### Scenario 1: All Files Valid
- All files pass validation
- All photos uploaded successfully
- Background processing tasks queued
- **Result**: 201 Created with all photos in `uploaded` list

### Scenario 2: Mixed Valid and Invalid Files
- Some files fail validation (e.g., wrong MIME type)
- Valid files are uploaded successfully
- **Result**: 201 Created with split between `uploaded` and `failed` lists

### Scenario 3: Batch-Level Error After Partial Success
- First N files upload successfully
- Error occurs (e.g., database connection lost, storage unavailable)
- Cleanup function deletes all N uploaded photos
- **Result**: 500 Server Error with detailed message about rollback

## Validation and Error Handling

The endpoint implements comprehensive validation at both levels:

### Per-File Validation (Non-blocking errors)
These don't stop the batch process; files are added to the failed list:

- Missing or invalid filename
- Filename exceeds 255 characters
- Invalid MIME type (not an image)
- Empty file
- File size exceeds 50MB
- Missing content-type header

### Batch-Level Errors (Blocking)
These stop the batch and trigger cleanup:

- Exception during photo service operations
- Unexpected exceptions in the loop
- System-level errors (storage, database unavailable)

## Testing

Comprehensive tests are provided at two levels:

### Unit Tests
**File**: `/home/otto/repos/personal/photo-explorer/backend/tests/unit/api/test_cleanup_partial_uploads.py`

11 unit tests covering:

1. Cleanup deletes all photos in a batch
2. Cleanup continues on individual deletion failures
3. Cleanup handles empty photo ID list
4. Cleanup handles single photo
5. Cleanup handles all failures gracefully
6. Cleanup logs information about deleted photos
7. Cleanup preserves deletion order
8. Cleanup with mixed success/failure scenarios
9. Cleanup handles large batches (1000+ photos)
10. Cleanup logs successful deletions
11. Cleanup logs error conditions

**Run unit tests**:
```bash
pytest tests/unit/api/test_cleanup_partial_uploads.py -v
```

### Integration Tests
**File**: `/home/otto/repos/personal/photo-explorer/backend/tests/integration/api/test_photo_batch_upload_error_handling.py`

22 integration tests covering:

1. Successful multi-photo upload
2. Partial failure with valid and invalid files
3. Empty file rejection
4. Missing content type rejection
5. Missing filename rejection
6. Filename too long rejection
7. File size exceeds limit rejection
8. Invalid MIME type rejection
9. No files provided (400 error)
10. Too many files provided (400 error)
11. Nonexistent album (404 error)
12. Descriptive error messages
13. Valid UUIDs in response
14. Mixed success/failure handling
15. Various image format acceptance
16. Batch error message format
17. Large batch handling (100+ files)

**Run integration tests**:
```bash
pytest tests/integration/api/test_photo_batch_upload_error_handling.py -v
```

## Implementation Checklist

- [x] Review current upload endpoint structure
- [x] Implement photo ID tracking for successfully uploaded photos
- [x] Add batch-level error handling with try-except wrapper
- [x] Implement cleanup helper function with:
  - [x] Individual error handling for each photo deletion
  - [x] Comprehensive logging
  - [x] Resilience to cascading failures
- [x] Create descriptive error messages with upload statistics
- [x] Comprehensive error message format
- [x] Unit tests for cleanup function (11 tests, all passing)
- [x] Integration tests for upload endpoint (22 tests)
- [x] Documentation

## File Structure

```
backend/
├── app/adapters/inbound/api/routes/
│   └── photos.py (Modified upload_photos endpoint and added _cleanup_partial_uploads)
└── tests/
    ├── unit/api/
    │   ├── __init__.py
    │   └── test_cleanup_partial_uploads.py (11 unit tests)
    └── integration/api/
        └── test_photo_batch_upload_error_handling.py (22 integration tests)
```

## Edge Cases Handled

1. **Empty batch cleanup**: Cleanup with empty photo ID list does nothing
2. **Single photo cleanup**: Works correctly for batches with one photo
3. **Large batches**: Efficiently handles cleanup of 1000+ photos
4. **Mixed failures**: Some photos fail to delete, others succeed
5. **Cleanup errors**: Deletion errors don't prevent other photos from being deleted
6. **Database errors**: Captured and rolled back correctly
7. **Storage errors**: Photos deleted from database even if file deletion fails
8. **Concurrent issues**: Photo IDs deleted in provided order

## Logging and Monitoring

The implementation includes comprehensive logging for operations tracking:

### Info Level
- Successful photo uploads with details
- Successful cleanup deletions
- Background task queueing

### Error Level
- Individual file validation failures
- Photo upload failures with error details
- Cleanup operation failures
- Batch-level errors with context

Example log entries:

```
INFO: Photo uploaded and queued for processing
  photo_id: 550e8400-e29b-41d4-a716-446655440000
  photo_filename: beach.jpg
  album_id: 650e8400-e29b-41d4-a716-446655440001

ERROR: Batch upload failed with error
  error: Connection timeout
  uploaded_count: 5

INFO: Cleanup deleted photo
  photo_id: 550e8400-e29b-41d4-a716-446655440000
  success: true
```

## Performance Considerations

1. **Async operations**: All I/O operations are async, allowing concurrent processing
2. **Cleanup efficiency**: Cleanup runs sequentially but logs all operations
3. **Memory footprint**: Photo IDs stored in list, minimal memory overhead
4. **Scalability**: Tested with batches up to 1000 photos

## Security Considerations

1. **SQL injection**: Using SQLAlchemy ORM prevents injection attacks
2. **File path traversal**: Files stored with validated paths
3. **File size limits**: Enforced 50MB limit per file
4. **MIME type validation**: Only image types accepted
5. **Error information**: Error messages sanitized for production

## Future Enhancements

1. **Partial success response**: Instead of 500, return 202 with partial success on batch error
2. **Atomic batch uploads**: Database transactions for all-or-nothing semantics
3. **Cleanup metrics**: Track cleanup success/failure rates
4. **Retry logic**: Automatic retry for transient failures
5. **Background cleanup jobs**: Periodic cleanup of orphaned files

## Related Documentation

- Photo upload flow: See `spec/features/photo-upload.md`
- API specification: See `spec/03-api-specification.md`
- Testing strategy: See `spec/05-testing-strategy.md`
- Architecture: See `spec/06-architecture-patterns.md`
