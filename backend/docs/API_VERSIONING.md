# API Versioning Strategy

**Document Version:** 1.0
**Last Updated:** 2025-11-24
**Status:** Active

## Overview

This document defines the versioning strategy for the Photo Explorer REST API. It establishes guidelines for managing API evolution, deprecation, and backward compatibility to ensure a stable and predictable developer experience.

## Current Version

- **Active Version:** `v1`
- **Base URL:** `/api/v1`
- **Status:** Stable
- **Introduced:** 2024-01-01

## Versioning Approach

### URL-Based Versioning

Photo Explorer uses **URL path versioning** for its REST API. The version identifier is included in the URL path:

```
https://api.example.com/api/v1/photos
https://api.example.com/api/v1/albums
https://api.example.com/api/v1/search
```

**Rationale:**
- Clear and explicit version identification
- Easy to route and cache
- Browser-friendly (works with browser testing)
- Standard practice for REST APIs
- No special headers or content negotiation required

### Version Format

- **Format:** `v{MAJOR}`
- **Example:** `v1`, `v2`, `v3`
- Only major versions are exposed in the URL
- Minor and patch changes are transparent to clients

## Semantic Versioning

Photo Explorer follows [Semantic Versioning 2.0.0](https://semver.org/) principles:

### MAJOR Version (v1 → v2)

Increment when making **incompatible** API changes:

- Removing endpoints
- Removing request/response fields
- Changing field types (string → integer)
- Changing authentication mechanisms
- Modifying core business logic that changes behavior
- Renaming endpoints or resources
- Changing URL structure significantly

**Example:**
```
v1: GET /api/v1/photos/{id}
v2: GET /api/v2/media/{id}  # Renamed resource
```

### MINOR Version (v1.1, v1.2)

Increment when adding **backward-compatible** functionality:

- Adding new endpoints
- Adding optional request parameters
- Adding new fields to responses
- Adding new HTTP methods to existing endpoints
- Enhancing functionality without breaking existing behavior

**Impact:** Transparent to clients (no URL change)

### PATCH Version (v1.1.1, v1.1.2)

Increment for **backward-compatible** bug fixes:

- Fixing incorrect behavior
- Performance improvements
- Documentation updates
- Internal refactoring

**Impact:** Transparent to clients (no URL change)

## Breaking vs Non-Breaking Changes

### Breaking Changes (Require Major Version Bump)

1. **Removing Fields**
   ```json
   // v1
   {"id": "123", "name": "Photo", "deprecated_field": "value"}

   // v2 - BREAKING: field removed
   {"id": "123", "name": "Photo"}
   ```

2. **Changing Field Types**
   ```json
   // v1
   {"photo_count": "150"}

   // v2 - BREAKING: type changed
   {"photo_count": 150}
   ```

3. **Renaming Fields**
   ```json
   // v1
   {"photo_url": "/photos/123.jpg"}

   // v2 - BREAKING: field renamed
   {"image_url": "/photos/123.jpg"}
   ```

4. **Changing Endpoint Paths**
   ```
   v1: POST /api/v1/photos/upload
   v2: POST /api/v2/photos  # BREAKING: path changed
   ```

5. **Modifying Authentication**
   ```
   v1: API Key in query parameter (?api_key=xxx)
   v2: OAuth 2.0 Bearer token  # BREAKING: auth method changed
   ```

6. **Changing Required Fields**
   ```json
   // v1: name is optional
   POST /api/v1/albums {"description": "..."}

   // v2: name is required - BREAKING
   POST /api/v2/albums {"name": "Required", "description": "..."}
   ```

### Non-Breaking Changes (Safe to Add)

1. **Adding Optional Fields to Requests**
   ```json
   // v1
   POST /api/v1/photos {"filename": "test.jpg"}

   // v1.1 - Safe: new optional field
   POST /api/v1/photos {"filename": "test.jpg", "tags": ["vacation"]}
   ```

2. **Adding Fields to Responses**
   ```json
   // v1
   {"id": "123", "name": "Photo"}

   // v1.1 - Safe: clients should ignore unknown fields
   {"id": "123", "name": "Photo", "ai_generated_caption": "..."}
   ```

3. **Adding New Endpoints**
   ```
   // v1.1 - Safe: new endpoint added
   GET /api/v1/photos/{id}/similar
   ```

4. **Adding New HTTP Methods**
   ```
   // v1: Only GET supported
   GET /api/v1/photos/{id}

   // v1.1: PATCH added - Safe
   PATCH /api/v1/photos/{id}
   ```

5. **Relaxing Validation Rules**
   ```
   // v1: name must be 3-50 characters
   // v1.1: name can be 1-100 characters - Safe (more permissive)
   ```

## Deprecation Policy

### Deprecation Timeline

1. **Announcement Phase** (Day 0)
   - Announce deprecation in release notes
   - Update API documentation
   - Add `Deprecation` header to responses
   - Add warning to OpenAPI spec

2. **Support Period** (Minimum 12 months)
   - Old version continues to function normally
   - Bug fixes and security patches provided
   - No new features added to deprecated version
   - Migration guide provided

3. **Sunset Period** (Final 3 months)
   - Warning headers become more prominent
   - Documentation shows deprecation notices
   - Migration assistance available
   - Countdown to end-of-life

4. **End-of-Life** (After 12+ months)
   - API version removed
   - Requests return HTTP 410 Gone
   - Redirect to new version (if possible)

### Deprecation Communication

#### HTTP Headers

Deprecated endpoints include headers:

```http
HTTP/1.1 200 OK
Deprecation: true
Sunset: Sat, 31 Dec 2025 23:59:59 GMT
Link: </api/v2/photos>; rel="successor-version"
Warning: 299 - "API v1 is deprecated and will be removed on 2025-12-31"
```

#### API Response

```json
{
  "success": true,
  "data": {...},
  "deprecation": {
    "deprecated": true,
    "sunset_date": "2025-12-31",
    "message": "This endpoint is deprecated. Use /api/v2/photos instead.",
    "migration_guide": "https://docs.example.com/migration/v1-to-v2"
  }
}
```

#### Documentation

- Strike-through text in API docs
- Prominent warning banners
- Link to migration guide
- Side-by-side comparison with new version

### Example Deprecation Notice

```markdown
## ⚠️ DEPRECATED: GET /api/v1/photos/{id}/metadata

**Deprecated:** 2025-01-15
**Sunset Date:** 2026-01-15
**Replacement:** GET /api/v2/photos/{id} (includes metadata)

This endpoint is deprecated and will be removed on 2026-01-15.
Please migrate to the new unified endpoint.

### Migration
- Old: GET /api/v1/photos/{id}/metadata
- New: GET /api/v2/photos/{id}

The new endpoint includes all metadata in the main response.
```

## Version Support Matrix

| Version | Status | Released | End-of-Life | Support Level |
|---------|--------|----------|-------------|---------------|
| v1      | Active | 2024-01  | TBD         | Full support  |
| v2      | Planned| TBD      | TBD         | Not released  |

### Support Levels

- **Full Support**: All features, bug fixes, security patches, new features
- **Maintenance**: Bug fixes and security patches only, no new features
- **Deprecated**: Security patches only, end-of-life announced
- **End-of-Life**: No support, API returns HTTP 410 Gone

## API Evolution Guidelines

### Adding New Functionality

**DO:**
- Add new optional fields to requests
- Add new fields to responses
- Add new endpoints
- Add new query parameters (optional)
- Make validation rules more permissive

**DON'T:**
- Remove existing fields
- Change field types
- Make optional fields required
- Rename fields or endpoints
- Change error response structure

### When to Create v2

Create a new major version when:

1. **Accumulation of Technical Debt**
   - Multiple deprecated features need removal
   - Inconsistent naming conventions need fixing
   - Core data models need restructuring

2. **Fundamental Changes**
   - New authentication mechanism
   - Different resource hierarchy
   - Major architectural changes

3. **Developer Feedback**
   - Common pain points need addressing
   - API usability improvements
   - Performance optimizations requiring changes

4. **Business Requirements**
   - New product direction
   - Compliance requirements
   - Major feature additions

## Migration Strategy

### v1 to v2 Migration (Future)

When v2 is released:

1. **Preparation Phase**
   - Publish comprehensive migration guide
   - Provide migration tools/scripts
   - Offer migration assistance
   - Create comparison documentation

2. **Dual Support Phase**
   - Both v1 and v2 available
   - v1 enters maintenance mode
   - No new features for v1
   - All new features in v2

3. **Transition Phase**
   - Active encouragement to migrate
   - Case studies and success stories
   - Direct support for migration
   - Monitoring v1 usage metrics

4. **Sunset Phase**
   - Final warnings issued
   - v1 marked as deprecated
   - 12-month countdown begins
   - Migration deadline announced

### Migration Checklist

- [ ] Review migration guide
- [ ] Update base URL from `/api/v1` to `/api/v2`
- [ ] Test all API calls
- [ ] Update error handling (if changed)
- [ ] Verify authentication flow
- [ ] Check new fields in responses
- [ ] Test backward compatibility layers
- [ ] Update API client libraries
- [ ] Deploy and monitor

## Version Detection

### Client Version Indication

Clients can optionally specify their expected version in requests:

```http
GET /api/v1/photos
Accept: application/json
X-API-Version: 1.0.0
User-Agent: PhotoExplorerClient/2.1.0
```

### Server Version Response

Server includes version information in responses:

```http
HTTP/1.1 200 OK
X-API-Version: 1.2.3
Content-Type: application/json
```

```json
{
  "success": true,
  "data": {...},
  "meta": {
    "api_version": "1.2.3",
    "requested_version": "1.0.0"
  }
}
```

## Backward Compatibility Guarantees

### Within Major Version (v1.x)

**Guaranteed:**
- Existing endpoints continue to work
- Required fields remain required
- Response field types don't change
- Authentication mechanisms stay the same
- Error codes remain consistent

**Not Guaranteed:**
- New optional fields may appear
- New endpoints may be added
- Performance characteristics
- Internal implementation details
- Third-party service availability

### Client Responsibilities

Clients must:
- Ignore unknown fields in responses (forward compatibility)
- Handle new error codes gracefully
- Not depend on field order
- Not depend on whitespace in responses
- Validate data types defensively
- Use semantic versioning for client libraries

## Testing Strategy

### Compatibility Testing

1. **Contract Tests**
   - Verify API contracts don't break
   - Test all v1 endpoints
   - Validate response schemas

2. **Version Tests**
   - Test v1 and v2 side-by-side
   - Verify deprecation headers
   - Test sunset behavior

3. **Client Tests**
   - Test with various client versions
   - Verify backward compatibility
   - Test migration scenarios

## FAQ

### Q: Can I request features for deprecated versions?

**A:** No. Deprecated versions receive only security patches. All new features go into the latest stable version.

### Q: How long will v1 be supported?

**A:** v1 will be supported with full features until v2 is released. After v2 release, v1 enters a 12-month deprecation period with maintenance-only support.

### Q: What happens if I call a removed endpoint?

**A:** You'll receive HTTP 410 Gone with a message directing you to the replacement:

```http
HTTP/1.1 410 Gone
Content-Type: application/json

{
  "error": {
    "code": "ENDPOINT_REMOVED",
    "message": "This endpoint was removed in v2. Use GET /api/v2/photos instead.",
    "sunset_date": "2025-12-31",
    "replacement": "/api/v2/photos"
  }
}
```

### Q: Will my v1 API keys work with v2?

**A:** Yes, API keys and OAuth tokens are version-independent and work across all API versions.

### Q: How do I report issues with the API?

**A:** Report issues via GitHub Issues: https://github.com/example/photo-explorer/issues

## References

- [Semantic Versioning 2.0.0](https://semver.org/)
- [RFC 8594 - Sunset HTTP Header](https://tools.ietf.org/html/rfc8594)
- [RFC 7234 - HTTP Caching](https://tools.ietf.org/html/rfc7234)
- [OpenAPI Specification](https://spec.openapis.org/)

## Version History

| Version | Date       | Changes |
|---------|------------|---------|
| 1.0     | 2025-11-24 | Initial versioning strategy document |

## Contact

For questions about API versioning:
- Documentation: https://docs.example.com
- GitHub Issues: https://github.com/example/photo-explorer/issues
- Email: api-support@example.com
