# Batch Photo Upload Error Handling Examples

This document provides practical examples of how the batch photo upload error handling system works in different scenarios.

## Example 1: Successful Batch Upload

**Request**:
```http
POST /api/v1/photos/upload HTTP/1.1
Content-Type: multipart/form-data

--boundary123
Content-Disposition: form-data; name="files"; filename="vacation1.jpg"
Content-Type: image/jpeg

[binary image data...]
--boundary123
Content-Disposition: form-data; name="files"; filename="vacation2.jpg"
Content-Type: image/jpeg

[binary image data...]
--boundary123--
```

**Response** (201 Created):
```json
{
  "success": true,
  "data": {
    "uploaded": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "filename": "vacation1.jpg",
        "status": "processing"
      },
      {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "filename": "vacation2.jpg",
        "status": "processing"
      }
    ],
    "failed": []
  }
}
```

**Logs**:
```
INFO: Photo uploaded and queued for processing
  photo_id: 550e8400-e29b-41d4-a716-446655440000
  photo_filename: vacation1.jpg
  album_id: null

INFO: Photo uploaded and queued for processing
  photo_id: 550e8400-e29b-41d4-a716-446655440001
  photo_filename: vacation2.jpg
  album_id: null
```

---

## Example 2: Partial Failure (Individual File Errors)

**Request**:
```http
POST /api/v1/photos/upload HTTP/1.1
Content-Type: multipart/form-data

--boundary123
Content-Disposition: form-data; name="files"; filename="photo1.jpg"
Content-Type: image/jpeg

[binary image data...]
--boundary123
Content-Disposition: form-data; name="files"; filename="document.pdf"
Content-Type: application/pdf

[binary PDF data...]
--boundary123
Content-Disposition: form-data; name="files"; filename="photo2.jpg"
Content-Type: image/jpeg

[binary image data...]
--boundary123--
```

**Response** (201 Created - Process continues despite errors):
```json
{
  "success": true,
  "data": {
    "uploaded": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "filename": "photo1.jpg",
        "status": "processing"
      },
      {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "filename": "photo2.jpg",
        "status": "processing"
      }
    ],
    "failed": [
      {
        "filename": "document.pdf",
        "error": "Invalid file type: application/pdf. Allowed: image/bmp, image/gif, image/heic, image/heif, image/jpeg, image/jpg, image/png, image/tiff, image/webp"
      }
    ]
  }
}
```

**Logs**:
```
INFO: Photo uploaded and queued for processing
  photo_id: 550e8400-e29b-41d4-a716-446655440000
  photo_filename: photo1.jpg

ERROR: Failed to upload photo
  photo_filename: document.pdf
  error: Invalid file type: application/pdf...

INFO: Photo uploaded and queued for processing
  photo_id: 550e8400-e29b-41d4-a716-446655440002
  photo_filename: photo2.jpg
```

**Key Point**: Individual file failures don't stop the batch; valid files still get processed.

---

## Example 3: Batch-Level Error with Cleanup

**Scenario**: During upload of the 4th file, the database becomes unavailable after 3 files have already been uploaded.

**Request**:
```http
POST /api/v1/photos/upload HTTP/1.1
Content-Type: multipart/form-data

--boundary123
Content-Disposition: form-data; name="files"; filename="photo1.jpg"
[binary data...]
--boundary123
Content-Disposition: form-data; name="files"; filename="photo2.jpg"
[binary data...]
--boundary123
Content-Disposition: form-data; name="files"; filename="photo3.jpg"
[binary data...]
--boundary123
Content-Disposition: form-data; name="files"; filename="photo4.jpg"
[binary data...]
--boundary123--
```

**What Happens**:
1. photo1.jpg → Uploaded successfully ✓
   - `successfully_uploaded_photo_ids = [550e8400-...]`
2. photo2.jpg → Uploaded successfully ✓
   - `successfully_uploaded_photo_ids = [550e8400-..., 550e8401-...]`
3. photo3.jpg → Uploaded successfully ✓
   - `successfully_uploaded_photo_ids = [550e8400-..., 550e8401-..., 550e8402-...]`
4. photo4.jpg → **Database connection timeout** ✗
   - Batch-level exception caught
   - **Cleanup triggered**: Delete IDs [550e8400-..., 550e8401-..., 550e8402-...]
   - HTTP 500 response returned

**Response** (500 Internal Server Error):
```json
{
  "detail": "Batch upload failed. Uploaded 3 of 4 photos before error. Changes rolled back. Error: Connection timeout: unable to connect to PostgreSQL server"
}
```

**Logs**:
```
INFO: Photo uploaded and queued for processing
  photo_id: 550e8400-e29b-41d4-a716-446655440000
  photo_filename: photo1.jpg

INFO: Photo uploaded and queued for processing
  photo_id: 550e8400-e29b-41d4-a716-446655440001
  photo_filename: photo2.jpg

INFO: Photo uploaded and queued for processing
  photo_id: 550e8400-e29b-41d4-a716-446655440002
  photo_filename: photo3.jpg

ERROR: Batch upload failed with error
  error: Connection timeout: unable to connect to PostgreSQL server
  uploaded_count: 3

INFO: Cleanup deleted photo
  photo_id: 550e8400-e29b-41d4-a716-446655440000
  success: true

INFO: Cleanup deleted photo
  photo_id: 550e8400-e29b-41d4-a716-446655440001
  success: true

INFO: Cleanup deleted photo
  photo_id: 550e8400-e29b-41d4-a716-446655440002
  success: true
```

**Database State After Response**: All 3 photos deleted. System is clean.

---

## Example 4: Cleanup Error During Rollback

**Scenario**: Batch error occurs, cleanup starts but encounters issues deleting some photos.

**What Happens**:
1. photo1.jpg through photo5.jpg → Uploaded successfully
2. photo6.jpg → **Storage service error** → Batch-level exception
3. Cleanup triggered:
   - photo1 → Deleted ✓
   - photo2 → Deleted ✓
   - photo3 → **Not found** (already deleted) ✗
   - photo4 → Deleted ✓
   - photo5 → **Permission denied** ✗
4. Cleanup continues despite errors
5. HTTP 500 response returned

**Response** (500 Internal Server Error):
```json
{
  "detail": "Batch upload failed. Uploaded 5 of 6 photos before error. Changes rolled back. Error: Storage service unavailable"
}
```

**Logs**:
```
INFO: Photo uploaded and queued for processing
  photo_id: 550e8400-e29b-41d4-a716-446655440000
  photo_filename: photo1.jpg

INFO: Photo uploaded and queued for processing
  photo_id: 550e8400-e29b-41d4-a716-446655440001
  photo_filename: photo2.jpg

[... 3 more successful uploads ...]

ERROR: Batch upload failed with error
  error: Storage service unavailable
  uploaded_count: 5

INFO: Cleanup deleted photo
  photo_id: 550e8400-e29b-41d4-a716-446655440000
  success: true

INFO: Cleanup deleted photo
  photo_id: 550e8400-e29b-41d4-a716-446655440001
  success: true

ERROR: Cleanup error during batch upload rollback
  photo_id: 550e8400-e29b-41d4-a716-446655440002
  error: Record not found (already deleted)

INFO: Cleanup deleted photo
  photo_id: 550e8400-e29b-41d4-a716-446655440003
  success: true

ERROR: Cleanup error during batch upload rollback
  photo_id: 550e8400-e29b-41d4-a716-446655440004
  error: Permission denied when deleting /storage/photos/...
```

**Database State**: Most photos cleaned up, but some errors logged for manual intervention.

---

## Example 5: Empty File Rejection

**Request**:
```http
POST /api/v1/photos/upload HTTP/1.1
Content-Type: multipart/form-data

--boundary123
Content-Disposition: form-data; name="files"; filename="photo.jpg"
Content-Type: image/jpeg

--boundary123--
```

**Response** (201 Created - This is not a batch-level error):
```json
{
  "success": true,
  "data": {
    "uploaded": [],
    "failed": [
      {
        "filename": "photo.jpg",
        "error": "Empty file"
      }
    ]
  }
}
```

**Key Point**: Per-file validation errors don't trigger cleanup because the file never made it to the service layer.

---

## Example 6: Too Many Files

**Request**: 101 files in single batch

**Response** (400 Bad Request - Pre-validation):
```json
{
  "detail": "Cannot upload more than 100 files at once"
}
```

**Key Point**: This is checked before entering the main loop, so no cleanup is needed.

---

## Example 7: Invalid Album

**Request**:
```http
POST /api/v1/photos/upload HTTP/1.1
Content-Type: multipart/form-data

album_id: 00000000-0000-0000-0000-000000000000

--boundary123
Content-Disposition: form-data; name="files"; filename="photo.jpg"
[binary data...]
--boundary123--
```

**Response** (404 Not Found - Pre-processing):
```json
{
  "detail": "Album 00000000-0000-0000-0000-000000000000 not found"
}
```

**Key Point**: Album validation happens before uploads, so no cleanup is needed.

---

## Error Handling Flow Diagram

```
START: Upload Request
  |
  +---> Check no files provided? → 400 Bad Request
  |
  +---> Check > 100 files? → 400 Bad Request
  |
  +---> Check album exists? → 404 Not Found
  |
  +---> For each file:
  |      |
  |      +---> Filename validation?
  |      |      NO → Add to failed, continue
  |      |
  |      +---> Content-type validation?
  |      |      NO → Add to failed, continue
  |      |
  |      +---> File size validation?
  |      |      NO → Add to failed, continue
  |      |
  |      +---> Upload to service?
  |      |      NO → Add to failed, continue
  |      |      YES → Add to successfully_uploaded_photo_ids
  |      |
  |      +---> Queue background tasks?
  |      |      NO → Add to failed, continue
  |      |      YES → Add to uploaded
  |
  +---> Batch-level exception?
         YES → Cleanup all successfully_uploaded_photo_ids → 500 Error
         NO → Return 201 with results
```

---

## Testing the Error Handling

### Unit Tests
```bash
# Test the cleanup helper function directly
pytest tests/unit/api/test_cleanup_partial_uploads.py -v

# Example output:
# test_cleanup_deletes_all_photos PASSED
# test_cleanup_continues_on_individual_delete_failure PASSED
# test_cleanup_with_empty_list PASSED
# ... etc (11 tests total)
```

### Integration Tests
```bash
# Test the full upload endpoint with errors
pytest tests/integration/api/test_photo_batch_upload_error_handling.py -v

# Example scenarios tested:
# test_successful_multi_photo_upload PASSED
# test_partial_failure_with_valid_and_invalid_files PASSED
# test_empty_file_rejection PASSED
# test_file_size_exceeds_limit_rejection PASSED
# ... etc (22 tests total)
```

---

## Monitoring and Debugging

### Log Queries
Find cleanup operations:
```bash
# Find all cleanup operations
grep "Cleanup deleted photo" logs/*.log

# Find cleanup errors
grep "Cleanup error during batch upload" logs/*.log

# Find batch-level upload failures
grep "Batch upload failed with error" logs/*.log
```

### Metrics to Track
1. **Upload success rate**: Successful uploads / Total upload requests
2. **Error rate**: Failed uploads / Total uploads
3. **Batch error rate**: Requests triggering cleanup / Total batch requests
4. **Cleanup success rate**: Successful cleanups / Total cleanup operations

### Recovery Procedures
If cleanup itself fails:
1. Check logs for specific errors
2. Verify database and storage availability
3. Run manual cleanup if needed:
   ```sql
   -- Find orphaned photos (if cleanup partially failed)
   SELECT id, filename FROM photos
   WHERE created_at > now() - interval '1 hour'
   AND filename LIKE '%partial_batch%';
   ```

---

## Best Practices

1. **Batch Size**: Upload 20-50 files per request for best performance
2. **Timeout Configuration**: Ensure client has sufficient timeout (> 60s for large batches)
3. **Error Handling**: Client should catch HTTP 500 and inform user with error message
4. **Retry Strategy**: For transient errors (network, temporary unavailability), implement exponential backoff
5. **Monitoring**: Set up alerts for high cleanup error rates

---

## Related Files

- Implementation: `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/api/routes/photos.py`
- Unit tests: `/home/otto/repos/personal/photo-explorer/backend/tests/unit/api/test_cleanup_partial_uploads.py`
- Integration tests: `/home/otto/repos/personal/photo-explorer/backend/tests/integration/api/test_photo_batch_upload_error_handling.py`
- Documentation: `/home/otto/repos/personal/photo-explorer/backend/BATCH_UPLOAD_ERROR_HANDLING.md`
