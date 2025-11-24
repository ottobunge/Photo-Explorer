# Input Validation Implementation

**Status:** Completed
**Date:** 2025-11-24
**Issue:** HIGH-2 - Missing Input Validation

## Overview

Comprehensive input validation has been implemented across all API endpoints to prevent security vulnerabilities and ensure data integrity. This includes both Pydantic field validators in request schemas and FastAPI Query validators in route handlers.

## Validation Categories

### 1. Pydantic Field Validators

All request schemas now include field-level validators that run during request deserialization:

#### Album Schemas (`album_schemas.py`)
- **Name validation**: 1-255 characters, no whitespace-only strings
- **Description validation**: 0-2000 characters, optional
- **Photo IDs validation**: 1-1000 IDs, no duplicates, at least one required

#### Connector Schemas (`connector_schemas.py`)
- **Type validation**: Whitelist of allowed types (local, google_photos, dropbox, onedrive)
- **Path validation**: Path traversal prevention, max 4096 characters
- **OAuth validation**: Code and URI length limits, protocol validation (http/https)
- **Name validation**: 1-255 characters, no whitespace-only strings

#### Search Schemas (`search_schemas.py`)
- **Query validation**: 1-500 characters, SQL injection pattern detection
- **Filter validation**: Album/connector/face cluster IDs with duplicate prevention
- **Date range validation**: Logical date ranges, no future dates beyond 1 day
- **Limit/offset validation**: limit 1-100, offset 0-10000

#### Face Schemas (`face_schemas.py`)
- **Cluster name validation**: 1-255 characters, no whitespace-only strings
- **Merge validation**: 1-100 clusters, no duplicates, target not in sources

#### Folder Schemas (`folder_schemas.py`)
- **Path validation**: No path traversal patterns, max 4096 characters
- **Name validation**: 1-255 characters, optional

#### Settings Schemas (`settings_schemas.py`)
- **Thumbnail quality**: 1-100 range validation
- **CLIP model**: Whitelist of valid models (ViT-B/32, ViT-B/16, etc.)
- **Cache hours**: 1-8760 range (1 hour to 1 year)
- **Batch size**: 1-1000 range
- **Workers**: 1-32 range

#### Model Schemas (`model_schemas.py`)
- **Model ID format**: Must be "author/model-name" format
- **Revision validation**: No command injection characters
- **Task validation**: Whitelist of allowed tasks (clip, face, text, image)

### 2. FastAPI Query Validators

All route handlers now use typed Query parameters with validation constraints:

#### Pagination Parameters
Applied to all paginated endpoints (photos, albums, connectors, faces, models):
- **page**: 1-1000 range with clear description
- **per_page**: 1-100 range with clear description

#### Search Parameters
- **query (q)**: 1-500 characters
- **limit**: 1-100 range
- **offset**: 0-10000 range
- **connector_id/album_id**: Optional UUID filters

#### File Upload Parameters
- **files**: List of UploadFile with max 100 files
- **album_id**: Optional UUID via Form
- File validation: MIME type, size (50MB max), filename length

#### OAuth Parameters
- **code**: 1-2048 characters
- **redirect_uri**: 1-2048 characters, http/https protocol validation
- **state**: Optional, max 256 characters

## Security Features

### SQL Injection Prevention
Search queries are validated for suspicious patterns:
- `UNION ... SELECT`
- `DROP ... TABLE`
- `DELETE ... FROM`
- Comment patterns (`--`, `/*`, `*/`)
- Stored procedure calls (`xp_`, `sp_`)

### Path Traversal Prevention
Folder and file paths are validated to prevent:
- `..` patterns
- Absolute path manipulation
- Suspicious characters in paths

### Command Injection Prevention
Model revisions and system inputs are validated to prevent:
- Shell metacharacters (`;`, `|`, `&`, `` ` ``, `$`)
- Command substitution patterns
- Parentheses and braces in unexpected contexts

### Input Sanitization
All text inputs undergo sanitization:
- **Whitespace trimming**: Leading and trailing whitespace removed
- **Empty string detection**: Reject whitespace-only strings
- **Length constraints**: Enforce maximum lengths for all fields
- **Duplicate detection**: Prevent duplicate IDs in batch operations

## Validation Rules Summary

### String Lengths
- Names (album, connector, folder): 1-255 characters
- Descriptions: 0-2000 characters
- Search queries: 1-500 characters
- File paths: 1-4096 characters
- OAuth codes/URIs: 1-2048 characters
- Model IDs: 1-256 characters

### Numeric Ranges
- Page number: 1-1000
- Per page: 1-100
- Search limit: 1-100
- Search offset: 0-10000
- Thumbnail quality: 1-100
- Cache hours: 1-8760
- Batch size: 1-1000
- Parallel workers: 1-32

### List Constraints
- Photo IDs: 1-1000 items, no duplicates
- Album filter IDs: 0-100 items, no duplicates
- Connector filter IDs: 0-50 items, no duplicates
- Face cluster IDs: 0-100 items, no duplicates
- Cluster merge sources: 1-100 items, no duplicates
- File uploads: 1-100 files

### File Upload Constraints
- **Maximum files**: 100 per request
- **Maximum file size**: 50MB per file
- **Allowed MIME types**:
  - image/jpeg, image/jpg, image/png
  - image/gif, image/webp, image/bmp
  - image/tiff, image/heic, image/heif
- **Filename length**: 1-255 characters

## Error Messages

Validation failures return clear, actionable error messages:

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "name"],
      "msg": "Album name cannot be empty or whitespace only",
      "input": "   ",
      "ctx": {"error": "validation error"}
    }
  ]
}
```

## Testing

Comprehensive test suite at `backend/tests/unit/api/test_input_validation.py`:
- 50+ test cases covering all validation scenarios
- Security-focused tests for injection attacks
- Edge case testing (empty strings, max lengths, duplicates)
- Positive and negative test cases

### Test Coverage
- Valid inputs accepted
- Invalid inputs rejected with appropriate errors
- SQL injection patterns detected
- Path traversal attempts blocked
- Command injection attempts blocked
- Duplicate detection working
- Length constraints enforced
- Range constraints enforced

## Files Modified

### Schema Files
1. `/backend/app/adapters/inbound/api/schemas/album_schemas.py`
2. `/backend/app/adapters/inbound/api/schemas/connector_schemas.py`
3. `/backend/app/adapters/inbound/api/schemas/search_schemas.py`
4. `/backend/app/adapters/inbound/api/schemas/face_schemas.py`
5. `/backend/app/adapters/inbound/api/schemas/folder_schemas.py`
6. `/backend/app/adapters/inbound/api/schemas/settings_schemas.py`
7. `/backend/app/adapters/inbound/api/schemas/model_schemas.py`

### Route Files
1. `/backend/app/adapters/inbound/api/routes/albums.py`
2. `/backend/app/adapters/inbound/api/routes/connectors.py`
3. `/backend/app/adapters/inbound/api/routes/photos.py`
4. `/backend/app/adapters/inbound/api/routes/search.py`
5. `/backend/app/adapters/inbound/api/routes/faces.py`
6. `/backend/app/adapters/inbound/api/routes/folders.py`
7. `/backend/app/adapters/inbound/api/routes/models.py`

### Test Files
1. `/backend/tests/unit/api/test_input_validation.py` (new)

## Usage Examples

### Valid Requests

```python
# Album creation
AlbumCreateRequest(name="My Photos", description="Summer 2024")

# Search request
SearchRequest(query="sunset beach", limit=20, offset=0)

# Connector creation
ConnectorCreateRequest(type="local", name="My Photos Folder")
```

### Invalid Requests

```python
# Empty name - rejected
AlbumCreateRequest(name="")  # ValidationError

# SQL injection - rejected
SearchRequest(query="'; DROP TABLE photos; --")  # ValidationError

# Path traversal - rejected
LocalFolderCreateRequest(path="../../../etc/passwd")  # ValidationError

# Too many items - rejected
AlbumPhotosRequest(photo_ids=[uuid4() for _ in range(1001)])  # ValidationError
```

## Benefits

1. **Security**: Prevents injection attacks and malicious inputs
2. **Data Integrity**: Ensures data meets business rules and constraints
3. **User Experience**: Clear error messages help users correct mistakes
4. **Maintainability**: Centralized validation logic easy to update
5. **Documentation**: Validation rules serve as API documentation
6. **Type Safety**: Pydantic ensures type correctness at runtime

## Future Enhancements

- Add rate limiting per IP/user to prevent abuse
- Implement content-based validation (e.g., actual image verification)
- Add custom validators for specific business rules
- Expand test coverage for edge cases
- Add performance benchmarks for validation overhead
- Consider adding request ID tracking for debugging

## References

- [Pydantic Validators Documentation](https://docs.pydantic.dev/latest/concepts/validators/)
- [FastAPI Query Parameters](https://fastapi.tiangolo.com/tutorial/query-params/)
- [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
