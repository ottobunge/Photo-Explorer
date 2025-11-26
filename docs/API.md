# Photo Explorer API Documentation

Complete API reference for Photo Explorer backend endpoints.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Health & Monitoring](#health--monitoring)
- [Photo Management](#photo-management)
- [Semantic Search](#semantic-search)
- [Face Recognition](#face-recognition)
- [Albums](#albums)
- [Connectors](#connectors)
- [Settings](#settings)
- [ML Models](#ml-models)

## Overview

**Base URL:** `http://localhost:8000`
**API Version:** `v1`
**API Prefix:** `/api/v1`

The Photo Explorer API provides endpoints for AI-powered photo management, semantic search, and face recognition.

### Interactive Documentation

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI Schema:** `http://localhost:8000/api/v1/openapi.json`

## Authentication

Currently, the API operates in single-user mode with no authentication required. Multi-user support with OAuth 2.0 is planned for future releases.

## Rate Limiting

All API endpoints are rate-limited to prevent abuse and ensure fair resource allocation.

### Default Limits

- **100 requests per minute** per IP address

### Rate Limit Headers

Responses include rate limit information in headers:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1638360000
```

### Rate Limit Exceeded Response

When rate limit is exceeded, you'll receive a 429 status code:

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "details": {
      "limit": "100 per 1 minute"
    }
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

The response includes a `Retry-After` header indicating when to retry (in seconds).

## Response Format

All API responses follow a standardized format for consistency.

### Success Response

Successful responses return a 2xx status code with this structure:

```json
{
  "success": true,
  "data": {
    // Response payload
  }
}
```

For endpoints that return lists:

```json
{
  "success": true,
  "data": {
    "items": [/* array of items */],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

### Error Response

Error responses return appropriate HTTP status codes with this structure:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      // Optional additional context
    }
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Error Handling

### Error Response Schema

All errors follow the standardized format above. The `request_id` can be used for debugging and support.

### Common Error Codes

#### Client Errors (4xx)

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `BAD_REQUEST` | 400 | Invalid request parameters |
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Authentication required |
| `TOKEN_EXPIRED` | 401 | OAuth token expired, re-authentication needed |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `ENTITY_NOT_FOUND` | 404 | Specific entity not found |
| `CONNECTOR_NOT_FOUND` | 404 | Connector not found |
| `PHOTO_NOT_FOUND` | 404 | Photo not found |
| `ALBUM_NOT_FOUND` | 404 | Album not found |
| `FACE_NOT_FOUND` | 404 | Face not found |
| `FACE_CLUSTER_NOT_FOUND` | 404 | Face cluster not found |
| `FILE_NOT_FOUND` | 404 | File not found on storage |
| `TOKEN_NOT_FOUND` | 404 | OAuth token not found |
| `CONFLICT` | 409 | Resource conflict |
| `CONNECTOR_ALREADY_EXISTS` | 409 | Connector with same config exists |
| `PHOTO_ALREADY_EXISTS` | 409 | Photo already indexed |
| `SYNC_IN_PROGRESS` | 409 | Connector sync already running |
| `CLUSTERING_IN_PROGRESS` | 409 | Face clustering operation in progress |
| `INVALID_OPERATION` | 409 | Operation not allowed in current state |
| `UNPROCESSABLE_ENTITY` | 422 | Request syntax valid but semantically invalid |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |

#### Server Errors (5xx)

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected server error |
| `STORAGE_ERROR` | 500 | File storage operation failed |
| `MODEL_INFERENCE_ERROR` | 500 | ML model inference failed |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |
| `MODEL_NOT_LOADED` | 503 | Required ML model not loaded |
| `INSUFFICIENT_STORAGE` | 507 | Not enough disk space |

### Validation Error Format

Validation errors (422) include detailed field-level errors:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "validation_errors": [
        {
          "field": "body -> name",
          "message": "field required",
          "type": "value_error.missing"
        }
      ],
      "error_count": 1
    }
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Health & Monitoring

### Liveness Check

Check if the application is running.

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-26T12:00:00.000Z",
  "version": "0.1.0"
}
```

**Status Codes:**
- `200 OK` - Application is alive

**Use Case:** Kubernetes/Docker liveness probe

---

### Readiness Check

Check if the application is ready to serve traffic (includes dependency health).

**Endpoint:** `GET /health/ready`

**Response:**
```json
{
  "status": "ready",
  "timestamp": "2025-11-26T12:00:00.000Z",
  "version": "0.1.0",
  "dependencies": [
    {
      "name": "postgresql",
      "status": "healthy",
      "response_time_ms": 5.23,
      "details": {
        "database": "connected",
        "pool_size": 5
      }
    },
    {
      "name": "redis",
      "status": "healthy",
      "response_time_ms": 2.15,
      "details": {
        "connected": true,
        "version": "7.0.12"
      }
    },
    {
      "name": "qdrant",
      "status": "healthy",
      "response_time_ms": 12.45,
      "details": {
        "connected": true,
        "collections": {
          "photos": {
            "name": "photo_embeddings",
            "points": 1523
          },
          "faces": {
            "name": "face_embeddings",
            "points": 342
          }
        }
      }
    }
  ]
}
```

**Status Codes:**
- `200 OK` - All dependencies healthy
- `503 Service Unavailable` - One or more dependencies unhealthy

**Use Case:** Kubernetes/Docker readiness probe, load balancer health checks

---

### ML Model Health Check

**NEW ENDPOINT** - Check ML model status and health.

**Endpoint:** `GET /health/ml`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-26T12:00:00.000Z",
  "models": [
    {
      "name": "ViT-B-32/openai",
      "loaded": true,
      "type": "clip"
    },
    {
      "name": "buffalo_l",
      "loaded": true,
      "type": "face_detector"
    },
    {
      "name": "vision_llm",
      "loaded": false,
      "type": "vision"
    },
    {
      "name": "object_detector",
      "loaded": false,
      "type": "object_detector"
    },
    {
      "name": "scene_classifier",
      "loaded": false,
      "type": "scene_classifier"
    }
  ],
  "details": {
    "clip_embedding_dim": 512,
    "face_embedding_dim": 512
  }
}
```

**Model Types:**
- `clip` - Semantic search embeddings (CRITICAL - must be loaded)
- `face_detector` - Face detection and recognition (CRITICAL - must be loaded)
- `vision` - Photo descriptions (lazy-loaded on demand)
- `object_detector` - Object detection (lazy-loaded on demand)
- `scene_classifier` - Scene classification (lazy-loaded on demand)

**Status Codes:**
- `200 OK` - All critical models loaded and healthy
- `503 Service Unavailable` - Critical models not loaded

**Use Case:** Monitor ML model availability, diagnose inference failures

---

### Metrics

**NEW ENDPOINT** - Prometheus metrics for monitoring.

**Endpoint:** `GET /metrics`

**Response:** Prometheus text exposition format

**Sample Metrics:**

```
# HELP celery_task_duration_seconds Task execution time
# TYPE celery_task_duration_seconds histogram
celery_task_duration_seconds_bucket{task="process_photo",le="0.5"} 145
celery_task_duration_seconds_bucket{task="process_photo",le="1.0"} 312
celery_task_duration_seconds_bucket{task="process_photo",le="5.0"} 523
celery_task_duration_seconds_count{task="process_photo"} 550
celery_task_duration_seconds_sum{task="process_photo"} 1234.56

# HELP celery_task_failures_total Number of task failures
# TYPE celery_task_failures_total counter
celery_task_failures_total{task="process_photo"} 12

# HELP celery_task_success_total Number of successful tasks
# TYPE celery_task_success_total counter
celery_task_success_total{task="process_photo"} 538

# HELP celery_task_retries_total Number of task retries
# TYPE celery_task_retries_total counter
celery_task_retries_total{task="process_photo"} 15

# HELP celery_active_tasks Currently executing tasks
# TYPE celery_active_tasks gauge
celery_active_tasks{task="process_photo"} 2
```

**Available Metrics:**
- `celery_task_duration_seconds` - Histogram of task execution times
- `celery_task_failures_total` - Counter of task failures by task type
- `celery_task_success_total` - Counter of successful tasks by task type
- `celery_task_retries_total` - Counter of task retries by task type
- `celery_active_tasks` - Gauge of currently running tasks by task type

**Status Codes:**
- `200 OK` - Metrics available

**Use Case:** Prometheus scraping, Grafana dashboards, performance monitoring

**Rate Limit:** Same as other endpoints (100 req/min)

---

## Photo Management

### Upload Photo

Upload a single photo for processing.

**Endpoint:** `POST /api/v1/photos/upload`

**Content-Type:** `multipart/form-data`

**Request:**
```
file: <binary file data>
connector_id: "uuid-of-upload-connector" (optional)
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "photo-uuid",
    "filename": "IMG_1234.jpg",
    "status": "processing",
    "connector_id": "connector-uuid",
    "uploaded_at": "2025-11-26T12:00:00.000Z"
  }
}
```

**Status Codes:**
- `201 Created` - Photo uploaded and queued for processing
- `400 Bad Request` - Invalid file or missing required fields
- `507 Insufficient Storage` - Not enough disk space

**Rate Limit:** 100 requests/minute

---

### Get Photo Details

Retrieve detailed information about a photo.

**Endpoint:** `GET /api/v1/photos/{photo_id}`

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "photo-uuid",
    "filename": "IMG_1234.jpg",
    "connector_id": "connector-uuid",
    "file_path": "/path/to/photo.jpg",
    "thumbnail_path": "/path/to/thumbnail.jpg",
    "width": 4032,
    "height": 3024,
    "taken_at": "2025-11-25T14:30:00.000Z",
    "created_at": "2025-11-26T12:00:00.000Z",
    "exif": {
      "make": "Apple",
      "model": "iPhone 13 Pro",
      "iso": 100,
      "aperture": 1.8,
      "shutter_speed": "1/120"
    },
    "ai_analysis": {
      "description": "A sunset over mountains with orange and purple sky",
      "objects": ["mountain", "sky", "clouds"],
      "scene": "outdoor_landscape"
    },
    "faces": [
      {
        "id": "face-uuid",
        "cluster_id": "cluster-uuid",
        "cluster_name": "John Doe",
        "confidence": 0.95
      }
    ]
  }
}
```

**Status Codes:**
- `200 OK` - Photo found
- `404 Not Found` - Photo not found

**Rate Limit:** 100 requests/minute

---

## Semantic Search

### Search Photos

Search photos using natural language queries.

**Endpoint:** `POST /api/v1/search`

**Request:**
```json
{
  "query": "sunset over mountains",
  "limit": 20,
  "connector_ids": ["connector-uuid"],  // Optional filter
  "album_ids": ["album-uuid"]           // Optional filter
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "query": "sunset over mountains",
    "results": [
      {
        "photo_id": "photo-uuid",
        "similarity": 0.92,
        "filename": "IMG_1234.jpg",
        "thumbnail_url": "/api/v1/photos/photo-uuid/thumbnail",
        "taken_at": "2025-11-25T14:30:00.000Z"
      }
    ],
    "total": 15,
    "performance": {
      "embedding_time_ms": 45.2,
      "search_time_ms": 12.3,
      "total_time_ms": 57.5
    }
  }
}
```

**Query Examples:**
- "cute cat playing with yarn"
- "people at a beach during sunset"
- "mountain landscape with snow"
- "coffee cup on wooden table"
- "modern building architecture"

**Status Codes:**
- `200 OK` - Search completed successfully
- `400 Bad Request` - Invalid query parameters
- `503 Service Unavailable` - CLIP model not loaded

**Rate Limit:** 100 requests/minute

**Notes:**
- Uses OpenAI CLIP model for semantic understanding
- Results sorted by similarity score (0.0 - 1.0)
- Supports multi-language queries
- Case-insensitive

---

## Face Recognition

### List Face Clusters

Get all face clusters (groups of the same person).

**Endpoint:** `GET /api/v1/faces/clusters`

**Query Parameters:**
- `named_only` (boolean, optional) - Only return clusters with names
- `min_faces` (integer, optional) - Minimum faces per cluster

**Response:**
```json
{
  "success": true,
  "data": {
    "clusters": [
      {
        "id": "cluster-uuid",
        "name": "John Doe",
        "face_count": 42,
        "representative_face_id": "face-uuid",
        "created_at": "2025-11-20T10:00:00.000Z",
        "updated_at": "2025-11-26T12:00:00.000Z"
      }
    ],
    "total": 12
  }
}
```

**Status Codes:**
- `200 OK` - Clusters retrieved
- `400 Bad Request` - Invalid query parameters

**Rate Limit:** 100 requests/minute

---

### Name Face Cluster

Assign a name to a face cluster.

**Endpoint:** `PATCH /api/v1/faces/clusters/{cluster_id}`

**Request:**
```json
{
  "name": "John Doe"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "cluster-uuid",
    "name": "John Doe",
    "face_count": 42,
    "updated_at": "2025-11-26T12:00:00.000Z"
  }
}
```

**Status Codes:**
- `200 OK` - Cluster updated
- `404 Not Found` - Cluster not found
- `400 Bad Request` - Invalid name

**Rate Limit:** 100 requests/minute

---

### Merge Face Clusters

Merge multiple clusters into one (same person misidentified as different people).

**Endpoint:** `POST /api/v1/faces/clusters/merge`

**Request:**
```json
{
  "cluster_ids": ["cluster-uuid-1", "cluster-uuid-2"],
  "target_cluster_id": "cluster-uuid-1",  // Optional, keeps this cluster's name
  "name": "John Doe"  // Optional, new name for merged cluster
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "merged-cluster-uuid",
    "name": "John Doe",
    "face_count": 68,
    "merged_from": ["cluster-uuid-1", "cluster-uuid-2"]
  }
}
```

**Status Codes:**
- `200 OK` - Clusters merged successfully
- `404 Not Found` - One or more clusters not found
- `400 Bad Request` - Invalid cluster IDs

**Rate Limit:** 100 requests/minute

---

### Search Photos by Face

Find all photos containing a specific person.

**Endpoint:** `POST /api/v1/faces/search`

**Request:**
```json
{
  "cluster_id": "cluster-uuid",
  "limit": 50,
  "min_confidence": 0.7  // Optional, default 0.6
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "cluster_id": "cluster-uuid",
    "cluster_name": "John Doe",
    "photos": [
      {
        "photo_id": "photo-uuid",
        "face_id": "face-uuid",
        "confidence": 0.95,
        "thumbnail_url": "/api/v1/photos/photo-uuid/thumbnail",
        "taken_at": "2025-11-25T14:30:00.000Z"
      }
    ],
    "total": 42
  }
}
```

**Status Codes:**
- `200 OK` - Search completed
- `404 Not Found` - Cluster not found

**Rate Limit:** 100 requests/minute

---

## Albums

### Create Album

Create a new photo album.

**Endpoint:** `POST /api/v1/albums`

**Request:**
```json
{
  "name": "Summer Vacation 2025",
  "description": "Photos from our trip to Hawaii",
  "cover_photo_id": "photo-uuid"  // Optional
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "album-uuid",
    "name": "Summer Vacation 2025",
    "description": "Photos from our trip to Hawaii",
    "cover_photo_id": "photo-uuid",
    "photo_count": 0,
    "created_at": "2025-11-26T12:00:00.000Z"
  }
}
```

**Status Codes:**
- `201 Created` - Album created
- `400 Bad Request` - Invalid album data

**Rate Limit:** 100 requests/minute

---

### Add Photos to Album

Add one or more photos to an album.

**Endpoint:** `POST /api/v1/albums/{album_id}/photos`

**Request:**
```json
{
  "photo_ids": ["photo-uuid-1", "photo-uuid-2", "photo-uuid-3"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "album_id": "album-uuid",
    "added_count": 3,
    "photo_count": 45
  }
}
```

**Status Codes:**
- `200 OK` - Photos added
- `404 Not Found` - Album or photos not found
- `400 Bad Request` - Invalid photo IDs

**Rate Limit:** 100 requests/minute

---

## Connectors

### List Connectors

Get all configured photo connectors.

**Endpoint:** `GET /api/v1/connectors`

**Response:**
```json
{
  "success": true,
  "data": {
    "connectors": [
      {
        "id": "connector-uuid",
        "name": "My Google Photos",
        "type": "google_photos",
        "status": "connected",
        "last_sync": "2025-11-26T10:00:00.000Z",
        "photo_count": 1523,
        "config": {
          "auto_sync": true
        }
      },
      {
        "id": "connector-uuid-2",
        "name": "Local Photos",
        "type": "local",
        "status": "active",
        "last_sync": "2025-11-26T11:00:00.000Z",
        "photo_count": 342,
        "config": {
          "path": "/home/user/Photos",
          "recursive": true
        }
      }
    ],
    "total": 2
  }
}
```

**Status Codes:**
- `200 OK` - Connectors retrieved

**Rate Limit:** 100 requests/minute

---

### Create Connector

Create a new photo source connector.

**Endpoint:** `POST /api/v1/connectors`

**Request (Google Photos):**
```json
{
  "name": "My Google Photos",
  "type": "google_photos",
  "config": {
    "auto_sync": true
  }
}
```

**Request (Local Folder):**
```json
{
  "name": "Local Photos",
  "type": "local",
  "config": {
    "path": "/home/user/Photos",
    "recursive": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "connector-uuid",
    "name": "My Google Photos",
    "type": "google_photos",
    "status": "pending_auth",
    "oauth_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
  }
}
```

**Status Codes:**
- `201 Created` - Connector created
- `400 Bad Request` - Invalid configuration
- `409 Conflict` - Connector already exists

**Rate Limit:** 100 requests/minute

---

### Trigger Connector Sync

Manually trigger a sync for a connector.

**Endpoint:** `POST /api/v1/connectors/{connector_id}/sync`

**Response:**
```json
{
  "success": true,
  "data": {
    "connector_id": "connector-uuid",
    "sync_id": "sync-task-uuid",
    "status": "running",
    "started_at": "2025-11-26T12:00:00.000Z"
  }
}
```

**Status Codes:**
- `202 Accepted` - Sync started
- `404 Not Found` - Connector not found
- `409 Conflict` - Sync already in progress

**Rate Limit:** 100 requests/minute

---

## Settings

### Get Application Settings

Retrieve current application settings.

**Endpoint:** `GET /api/v1/settings`

**Response:**
```json
{
  "success": true,
  "data": {
    "app_name": "Photo Explorer",
    "version": "1.0.0",
    "storage": {
      "base_path": "/app/storage",
      "thumbnails_path": "/app/storage/thumbnails"
    },
    "ml_models": {
      "clip_model": "ViT-B-32",
      "clip_pretrained": "openai"
    },
    "allowed_paths": [
      "/home/user"
    ]
  }
}
```

**Status Codes:**
- `200 OK` - Settings retrieved

**Rate Limit:** 100 requests/minute

---

### Get Storage Statistics

Retrieve storage usage statistics.

**Endpoint:** `GET /api/v1/settings/storage`

**Response:**
```json
{
  "success": true,
  "data": {
    "total_bytes": 107374182400,
    "used_bytes": 53687091200,
    "available_bytes": 53687091200,
    "usage_percent": 50.0,
    "photos_count": 1523,
    "photos_size_bytes": 42949672960,
    "thumbnails_size_bytes": 1073741824
  }
}
```

**Status Codes:**
- `200 OK` - Statistics retrieved

**Rate Limit:** 100 requests/minute

---

## ML Models

### List Available Models

Get list of available ML models and their status.

**Endpoint:** `GET /api/v1/models`

**Response:**
```json
{
  "success": true,
  "data": {
    "models": [
      {
        "name": "ViT-B-32/openai",
        "type": "clip",
        "status": "loaded",
        "size_mb": 350,
        "embedding_dim": 512
      },
      {
        "name": "buffalo_l",
        "type": "face_detector",
        "status": "loaded",
        "size_mb": 100,
        "embedding_dim": 512
      }
    ]
  }
}
```

**Status Codes:**
- `200 OK` - Models retrieved

**Rate Limit:** 100 requests/minute

---

## Request Tracing

All responses include a unique `X-Request-ID` header for request tracing and debugging:

```http
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

Use this ID when reporting issues or searching logs.

## Best Practices

### Error Handling

Always check the `success` field in responses:

```javascript
const response = await fetch('/api/v1/photos/123');
const data = await response.json();

if (data.success) {
  // Handle success
  console.log(data.data);
} else {
  // Handle error
  console.error(`Error ${data.error.code}: ${data.error.message}`);
  if (data.error.details) {
    console.error('Details:', data.error.details);
  }
}
```

### Rate Limit Handling

Respect rate limits and implement exponential backoff:

```javascript
async function apiRequest(url, options = {}) {
  const response = await fetch(url, options);

  if (response.status === 429) {
    const retryAfter = response.headers.get('Retry-After');
    await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
    return apiRequest(url, options); // Retry
  }

  return response.json();
}
```

### Pagination

For endpoints returning lists, use pagination parameters:

```
GET /api/v1/photos?page=2&page_size=50
```

### Filtering

Many list endpoints support filtering:

```
GET /api/v1/photos?connector_id=uuid&taken_after=2025-01-01
```

## Further Reading

- [Deployment Guide](./deployment.md) - Production deployment instructions
- [Development Workflow](../DEV_WORKFLOW.md) - Local development setup
- Interactive API Docs at `http://localhost:8000/docs`
