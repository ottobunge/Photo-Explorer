# API Documentation Guide

**Document Version:** 1.0
**Last Updated:** 2025-11-24

## Overview

This guide defines standards and best practices for documenting the Photo Explorer API. Consistent, comprehensive documentation ensures a great developer experience and reduces support burden.

## Documentation Philosophy

### Principles

1. **Developer-First**: Documentation is written for API consumers, not implementers
2. **Examples-Driven**: Every endpoint includes real-world examples
3. **Complete**: Cover happy paths, edge cases, and error scenarios
4. **Current**: Documentation is part of the code and updated with changes
5. **Discoverable**: Use OpenAPI/Swagger for automatic documentation generation

### Documentation Layers

1. **OpenAPI Specification**: Machine-readable API contract
2. **Inline Docstrings**: Python docstrings in route handlers
3. **External Guides**: This document and API_VERSIONING.md
4. **Interactive Docs**: Swagger UI at `/docs` and ReDoc at `/redoc`
5. **Code Examples**: Sample clients and integration code

## OpenAPI/Swagger Configuration

### Main Application Setup

The FastAPI application is configured with comprehensive OpenAPI metadata:

```python
# backend/app/main.py

app = FastAPI(
    title="Photo Explorer API",
    description="AI-powered photo organization and semantic search platform",
    version="1.2.3",  # Semantic version
    terms_of_service="https://example.com/terms",
    contact={
        "name": "API Support",
        "url": "https://github.com/example/photo-explorer",
        "email": "api-support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
    openapi_tags=[
        {
            "name": "Photos",
            "description": "Operations for managing photos",
        },
        {
            "name": "Albums",
            "description": "Photo album management",
        },
        # ... more tags
    ],
)
```

### Router Tags

Each router is assigned to a logical tag for grouping:

```python
app.include_router(
    photos.router,
    prefix=f"{api_prefix}/photos",
    tags=["Photos"],
)
```

## Endpoint Documentation Standards

### Required Elements

Every endpoint must have:

1. **Summary**: Short (3-5 words) description
2. **Description**: Detailed explanation (1-3 sentences)
3. **Response Description**: What the response contains
4. **Docstring**: Comprehensive documentation with examples
5. **Parameter Descriptions**: Every parameter documented
6. **Status Codes**: All possible HTTP status codes
7. **Example Requests/Responses**: Real-world examples

### Template

```python
@router.post(
    "/endpoint",
    response_model=ResponseSchema,
    status_code=201,
    summary="Brief action description",
    description="Detailed explanation of what this endpoint does",
    response_description="What the response contains",
    responses={
        201: {"description": "Resource created successfully"},
        400: {"description": "Invalid request data"},
        401: {"description": "Authentication required"},
        404: {"description": "Resource not found"},
        500: {"description": "Server error"},
    },
    tags=["Resource"],
)
async def endpoint_name(
    resource_id: Annotated[UUID, "Resource identifier"],
    param: Annotated[str, Query(description="Parameter description")] = "default",
    dependency: DependencyType = Depends(get_dependency),
) -> ResponseSchema:
    """
    One-line summary of the endpoint.

    Detailed description of what the endpoint does, how it works,
    and what developers need to know. Include:
    - Main functionality
    - Important behavior
    - Side effects
    - Rate limits
    - Caching

    Args:
        resource_id: Description of the resource ID parameter
        param: Description of the query parameter
        dependency: Injected dependency (auto-documented)

    Returns:
        ResponseSchema containing:
        - field1: Description of field
        - field2: Description of field

    Example Request:
        ```
        POST /api/v1/endpoint?param=value
        Content-Type: application/json

        {
            "field": "value"
        }
        ```

    Example Response:
        ```json
        {
            "success": true,
            "data": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "field": "value"
            }
        }
        ```

    Error Response Example:
        ```json
        {
            "success": false,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid field value",
                "details": {
                    "field": "Value must be non-empty"
                }
            }
        }
        ```

    Status Codes:
        201: Resource created successfully
        400: Invalid request data (validation failed)
        401: Authentication required
        404: Resource not found
        500: Server error

    Rate Limits:
        - 100 requests per minute per user
        - 1000 requests per hour per user

    Notes:
        - Additional important information
        - Caching behavior
        - Asynchronous processing details
        - Related endpoints
    """
    # Implementation
    pass
```

### Documentation Best Practices

#### 1. Use Type Hints and Annotations

```python
# Good
async def get_photo(
    photo_id: Annotated[UUID, "Photo UUID"],
    include_exif: Annotated[bool, Query(description="Include EXIF data")] = False,
) -> PhotoResponse:
    pass

# Bad
async def get_photo(photo_id, include_exif=False):
    pass
```

#### 2. Document Query Parameters

```python
# Good
@router.get("/photos")
async def list_photos(
    page: Annotated[int, Query(ge=1, le=1000, description="Page number (1-indexed)")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    sort_by: Annotated[str, Query(description="Sort field: 'taken_at', 'created_at', 'filename'")] = "taken_at",
    order: Annotated[str, Query(description="Sort order: 'asc' or 'desc'")] = "desc",
):
    pass
```

#### 3. Provide Real Examples

```python
"""
Example Request:
    ```bash
    curl -X POST https://api.example.com/api/v1/photos/upload \
      -H "Authorization: Bearer YOUR_TOKEN" \
      -F "file=@photo.jpg" \
      -F "album_id=550e8400-e29b-41d4-a716-446655440000"
    ```

Example Response:
    ```json
    {
        "success": true,
        "data": {
            "uploaded": [
                {
                    "id": "650e8400-e29b-41d4-a716-446655440001",
                    "filename": "photo.jpg",
                    "status": "processing"
                }
            ],
            "failed": []
        }
    }
    ```
"""
```

#### 4. Document All Error Cases

```python
"""
Status Codes:
    200: Success
    400: Invalid request
        - Missing required fields
        - Invalid field format
        - Invalid enum value
    401: Unauthorized
        - Missing authentication token
        - Invalid or expired token
    403: Forbidden
        - Insufficient permissions
        - Resource access denied
    404: Not found
        - Resource doesn't exist
        - Parent resource not found
    409: Conflict
        - Resource already exists
        - Concurrent modification
    413: Payload too large
        - File size exceeds limit
    429: Too many requests
        - Rate limit exceeded
    500: Server error
        - Internal server failure
        - Database connection failed
        - External service unavailable
"""
```

#### 5. Document Asynchronous Operations

```python
"""
Upload one or more photos to the library.

Photos are queued for background processing after upload.
Processing includes:
- Thumbnail generation (~5 seconds)
- EXIF extraction (~1 second)
- AI analysis (~10 seconds)
- Face detection (~15 seconds)
- Embedding generation (~5 seconds)

Total processing time: 30-45 seconds per photo.

To check processing status:
1. Poll GET /api/v1/photos/{id}
2. Check the `processing_status` field
3. Possible values: "pending", "processing", "completed", "failed"

Or use webhooks (if configured) to receive notifications.
"""
```

#### 6. Document Rate Limits

```python
"""
Rate Limits:
    - Authenticated: 100 requests/minute, 5000 requests/hour
    - Unauthenticated: 20 requests/minute, 500 requests/hour
    - Upload: 50 files/hour per user
    - Search: 100 queries/minute per user

Rate limit headers:
    X-RateLimit-Limit: 100
    X-RateLimit-Remaining: 95
    X-RateLimit-Reset: 1640000000

When rate limited, returns HTTP 429:
    ```json
    {
        "error": {
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Rate limit exceeded",
            "retry_after": 60
        }
    }
    ```
"""
```

## Schema Documentation

### Pydantic Model Examples

Add examples to Pydantic schemas using `Config`:

```python
from pydantic import BaseModel, Field

class PhotoData(BaseModel):
    """Photo metadata and information."""

    id: UUID = Field(..., description="Unique photo identifier")
    filename: str = Field(..., description="Original filename", example="IMG_1234.jpg")
    width: int = Field(..., description="Image width in pixels", ge=1, example=4032)
    height: int = Field(..., description="Image height in pixels", ge=1, example=3024)
    taken_at: Optional[datetime] = Field(None, description="When photo was taken", example="2024-01-15T14:30:00Z")
    scene_type: Optional[str] = Field(None, description="Scene classification", example="outdoor")
    detected_objects: list[str] = Field(default_factory=list, description="AI-detected objects", example=["person", "tree", "sky"])

    class Config:
        json_schema_extra = {
            "example": {
                "id": "650e8400-e29b-41d4-a716-446655440001",
                "filename": "IMG_1234.jpg",
                "width": 4032,
                "height": 3024,
                "taken_at": "2024-01-15T14:30:00Z",
                "scene_type": "outdoor",
                "detected_objects": ["person", "tree", "sky"],
            }
        }
```

### Enum Documentation

```python
from enum import Enum

class ProcessingStatus(str, Enum):
    """Photo processing status."""

    PENDING = "pending"  # Queued for processing
    PROCESSING = "processing"  # Currently being processed
    COMPLETED = "completed"  # Processing complete
    FAILED = "failed"  # Processing failed
```

## Error Response Standards

### Standard Error Schema

All errors follow this structure:

```json
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable error message",
        "details": {
            "field": "Specific error details"
        }
    }
}
```

### Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `AUTHENTICATION_REQUIRED` | 401 | No auth token provided |
| `INVALID_TOKEN` | 401 | Token is invalid or expired |
| `INSUFFICIENT_PERMISSIONS` | 403 | User lacks required permissions |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource doesn't exist |
| `RESOURCE_ALREADY_EXISTS` | 409 | Duplicate resource |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
| `SERVICE_UNAVAILABLE` | 503 | External service down |

### Document Common Errors

```python
"""
Common Errors:

VALIDATION_ERROR (400):
    ```json
    {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {
                "filename": "Field required",
                "album_id": "Invalid UUID format"
            }
        }
    }
    ```

AUTHENTICATION_REQUIRED (401):
    ```json
    {
        "error": {
            "code": "AUTHENTICATION_REQUIRED",
            "message": "Authentication required"
        }
    }
    ```

RESOURCE_NOT_FOUND (404):
    ```json
    {
        "error": {
            "code": "RESOURCE_NOT_FOUND",
            "message": "Photo not found",
            "details": {
                "photo_id": "650e8400-e29b-41d4-a716-446655440001"
            }
        }
    }
    ```
"""
```

## Interactive Documentation

### Swagger UI (`/docs`)

- Automatically generated from OpenAPI spec
- Try-it-out functionality for testing
- Schema visualization
- Authentication support

### ReDoc (`/redoc`)

- Clean, three-panel design
- Better for reading and reference
- Responsive design
- Search functionality

### Accessing Documentation

```bash
# Development
http://localhost:8000/docs
http://localhost:8000/redoc

# Production
https://api.example.com/docs
https://api.example.com/redoc

# OpenAPI JSON
https://api.example.com/api/v1/openapi.json
```

## Code Examples

### Python Client Example

```python
import requests

# Authentication
headers = {
    "Authorization": "Bearer YOUR_TOKEN"
}

# Upload photo
with open("photo.jpg", "rb") as f:
    files = {"file": f}
    data = {"album_id": "550e8400-e29b-41d4-a716-446655440000"}
    response = requests.post(
        "https://api.example.com/api/v1/photos/upload",
        headers=headers,
        files=files,
        data=data,
    )

print(response.json())
```

### JavaScript Client Example

```javascript
// Upload photo
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('album_id', '550e8400-e29b-41d4-a716-446655440000');

const response = await fetch('https://api.example.com/api/v1/photos/upload', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer YOUR_TOKEN'
    },
    body: formData
});

const result = await response.json();
console.log(result);
```

### cURL Examples

```bash
# List photos
curl -X GET "https://api.example.com/api/v1/photos?page=1&per_page=20" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Upload photo
curl -X POST "https://api.example.com/api/v1/photos/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@photo.jpg"

# Search photos
curl -X POST "https://api.example.com/api/v1/search" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "sunset over mountains", "limit": 10}'
```

## Documentation Checklist

When adding a new endpoint:

- [ ] Add `summary` parameter to decorator
- [ ] Add `description` parameter to decorator
- [ ] Add `response_description` parameter
- [ ] Define `responses` dict with all status codes
- [ ] Write comprehensive docstring with:
  - [ ] Overview paragraph
  - [ ] Args section
  - [ ] Returns section
  - [ ] Example request
  - [ ] Example response
  - [ ] Error examples
  - [ ] Status codes list
  - [ ] Notes/caveats
- [ ] Add parameter descriptions with `Annotated`
- [ ] Add examples to Pydantic schemas
- [ ] Test in Swagger UI
- [ ] Review in ReDoc
- [ ] Add integration tests

## Maintenance

### Keeping Documentation Current

1. **Code Reviews**: Check documentation in PRs
2. **Automated Tests**: Test examples actually work
3. **Version Updates**: Update version in examples
4. **Deprecation**: Mark deprecated endpoints clearly
5. **Changelog**: Maintain API changelog

### Documentation Testing

```python
# Test that docstrings are present
def test_endpoint_has_docstring():
    from app.adapters.inbound.api.routes import photos
    assert photos.upload_photos.__doc__ is not None
    assert len(photos.upload_photos.__doc__) > 50

# Test that examples are valid
def test_example_requests_valid():
    # Extract example from docstring
    # Validate JSON syntax
    # Test against schema
    pass
```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAPI Specification](https://spec.openapis.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Google API Design Guide](https://cloud.google.com/apis/design)
- [Microsoft REST API Guidelines](https://github.com/microsoft/api-guidelines)

## Version History

| Version | Date       | Changes |
|---------|------------|---------|
| 1.0     | 2025-11-24 | Initial API documentation guide |
