# Photo Explorer - API Specification

## Base URL

Development: `http://localhost:8000/api/v1`

## Authentication

v1: No authentication (single-user local deployment)

## Common Response Format

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 100
  }
}
```

## Error Response Format

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid file type",
    "details": { ... }
  }
}
```

---

## Photos API

### Upload Photos

```http
POST /photos/upload
Content-Type: multipart/form-data
```

**Request:**
- `files`: File[] - One or more image files
- `album_id`: UUID (optional) - Album to add photos to

**Response:**
```json
{
  "success": true,
  "data": {
    "uploaded": [
      {
        "id": "uuid",
        "filename": "beach.jpg",
        "status": "processing"
      }
    ],
    "failed": []
  }
}
```

### Get Photo

```http
GET /photos/{photo_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "filename": "beach.jpg",
    "original_path": null,
    "storage_path": "/storage/photos/uuid.jpg",
    "thumbnail_path": "/storage/thumbnails/uuid.jpg",
    "mime_type": "image/jpeg",
    "file_size": 2048000,
    "width": 4000,
    "height": 3000,
    "taken_at": "2024-06-15T14:30:00Z",
    "exif_data": {
      "camera": "Canon EOS R5",
      "lens": "RF 24-70mm",
      "iso": 400,
      "aperture": "f/2.8",
      "shutter_speed": "1/500",
      "gps": { "lat": 34.0195, "lng": -118.4912 }
    },
    "description": "A sunny beach with palm trees and blue water",
    "scene_type": "beach",
    "is_indoor": false,
    "detected_objects": ["palm tree", "ocean", "sand", "sky"],
    "faces": [
      {
        "id": "uuid",
        "cluster_id": "uuid",
        "cluster_name": "John",
        "bbox": { "x": 100, "y": 150, "width": 80, "height": 100 }
      }
    ],
    "albums": [
      { "id": "uuid", "name": "Summer 2024" }
    ],
    "processing_status": "completed",
    "created_at": "2024-06-15T14:35:00Z"
  }
}
```

### List Photos

```http
GET /photos
```

**Query Parameters:**
- `page`: int (default: 1)
- `per_page`: int (default: 20, max: 100)
- `album_id`: UUID (optional)
- `start_date`: ISO date (optional)
- `end_date`: ISO date (optional)
- `has_faces`: bool (optional)
- `is_indoor`: bool (optional)

**Response:**
```json
{
  "success": true,
  "data": {
    "photos": [ ... ]
  },
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 1500
  }
}
```

### Delete Photo

```http
DELETE /photos/{photo_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "deleted": true
  }
}
```

### Get Photo File

```http
GET /photos/{photo_id}/file
GET /photos/{photo_id}/thumbnail
```

Returns the actual image file.

---

## Albums API

### Create Album

```http
POST /albums
Content-Type: application/json
```

**Request:**
```json
{
  "name": "Summer Vacation 2024",
  "description": "Trip to California"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "Summer Vacation 2024",
    "description": "Trip to California",
    "cover_photo_id": null,
    "photo_count": 0,
    "created_at": "2024-06-15T14:35:00Z"
  }
}
```

### List Albums

```http
GET /albums
```

### Get Album

```http
GET /albums/{album_id}
```

### Update Album

```http
PATCH /albums/{album_id}
```

### Delete Album

```http
DELETE /albums/{album_id}
```

### Add Photos to Album

```http
POST /albums/{album_id}/photos
Content-Type: application/json
```

**Request:**
```json
{
  "photo_ids": ["uuid1", "uuid2", "uuid3"]
}
```

### Remove Photos from Album

```http
DELETE /albums/{album_id}/photos
Content-Type: application/json
```

**Request:**
```json
{
  "photo_ids": ["uuid1", "uuid2"]
}
```

---

## Search API

### Semantic Search

```http
POST /search
Content-Type: application/json
```

**Request:**
```json
{
  "query": "sunset at the beach with palm trees",
  "filters": {
    "album_ids": ["uuid"],
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "has_faces": true,
    "face_cluster_ids": ["uuid"],
    "is_indoor": false
  },
  "limit": 20,
  "offset": 0
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "photo": { ... },
        "score": 0.89,
        "highlights": ["beach", "sunset"]
      }
    ],
    "query_embedding_time_ms": 45,
    "search_time_ms": 12
  },
  "meta": {
    "total": 150,
    "limit": 20,
    "offset": 0
  }
}
```

### Similar Photos

```http
GET /photos/{photo_id}/similar
```

**Query Parameters:**
- `limit`: int (default: 10)

---

## Faces API

### List Face Clusters

```http
GET /faces/clusters
```

**Query Parameters:**
- `named_only`: bool (default: false)
- `unnamed_only`: bool (default: false)

**Response:**
```json
{
  "success": true,
  "data": {
    "clusters": [
      {
        "id": "uuid",
        "name": "John Doe",
        "face_count": 45,
        "photo_count": 38,
        "representative_face": {
          "id": "uuid",
          "crop_url": "/faces/uuid/crop"
        }
      }
    ]
  }
}
```

### Get Cluster Details

```http
GET /faces/clusters/{cluster_id}
```

### Name a Cluster

```http
PATCH /faces/clusters/{cluster_id}
Content-Type: application/json
```

**Request:**
```json
{
  "name": "John Doe"
}
```

### Merge Clusters

```http
POST /faces/clusters/merge
Content-Type: application/json
```

**Request:**
```json
{
  "source_cluster_ids": ["uuid1", "uuid2"],
  "target_cluster_id": "uuid3"
}
```

### Split Face from Cluster

```http
POST /faces/{face_id}/split
```

Creates a new cluster with just this face.

### Move Face to Cluster

```http
POST /faces/{face_id}/move
Content-Type: application/json
```

**Request:**
```json
{
  "target_cluster_id": "uuid"
}
```

### Get Face Crop Image

```http
GET /faces/{face_id}/crop
```

### Search by Face

```http
POST /faces/search
Content-Type: multipart/form-data
```

**Request:**
- `image`: File - Image containing a face to search for

**Response:** List of matching photos with that face.

---

## Folders API

### Register Watched Folder

```http
POST /folders
Content-Type: application/json
```

**Request:**
```json
{
  "path": "/home/user/Pictures/Vacation",
  "name": "Vacation Photos",
  "recursive": true,
  "auto_album": true
}
```

### List Watched Folders

```http
GET /folders
```

### Get Folder Status

```http
GET /folders/{folder_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "path": "/home/user/Pictures/Vacation",
    "name": "Vacation Photos",
    "recursive": true,
    "auto_album": true,
    "stats": {
      "total_files": 500,
      "processed": 485,
      "pending": 10,
      "failed": 5
    },
    "last_scanned_at": "2024-06-15T10:00:00Z"
  }
}
```

### Trigger Folder Scan

```http
POST /folders/{folder_id}/scan
```

### Remove Watched Folder

```http
DELETE /folders/{folder_id}
```

**Query Parameters:**
- `delete_photos`: bool (default: false) - Also delete imported photos

---

## Processing Status API

### Get Processing Queue Status

```http
GET /processing/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "queue_length": 25,
    "processing": 2,
    "completed_today": 150,
    "failed_today": 3,
    "workers": {
      "clip": { "status": "running", "gpu_memory": "2.1GB" },
      "vision": { "status": "running", "gpu_memory": "4.5GB" },
      "face": { "status": "running", "gpu_memory": "1.2GB" }
    }
  }
}
```

### Get Photo Processing Status

```http
GET /photos/{photo_id}/processing
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "processing",
    "steps": {
      "metadata": { "status": "completed", "completed_at": "..." },
      "thumbnail": { "status": "completed", "completed_at": "..." },
      "clip_embedding": { "status": "processing", "started_at": "..." },
      "vision_description": { "status": "pending" },
      "face_detection": { "status": "pending" }
    }
  }
}
```

---

## Stats API

### Get Collection Stats

```http
GET /stats
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_photos": 15000,
    "total_albums": 45,
    "total_faces": 3200,
    "named_people": 28,
    "storage_used_bytes": 52428800000,
    "photos_by_year": {
      "2024": 2500,
      "2023": 4000,
      "2022": 3500
    },
    "photos_by_scene": {
      "outdoor": 8000,
      "indoor": 5000,
      "unknown": 2000
    }
  }
}
```

---

## Connectors API

### List Connectors

```http
GET /connectors
```

**Response:**
```json
{
  "success": true,
  "data": {
    "connectors": [
      {
        "id": "uuid",
        "type": "google_photos",
        "name": "My Google Photos",
        "enabled": true,
        "status": "connected",
        "config": {},
        "last_sync": "2024-06-15T10:00:00Z",
        "created_at": "2024-06-01T00:00:00Z"
      }
    ]
  }
}
```

### Get Connector

```http
GET /connectors/{connector_id}
```

### Update Connector

```http
PATCH /connectors/{connector_id}
```

**Request:**
```json
{
  "name": "Updated Name",
  "enabled": false,
  "config": {}
}
```

### Delete Connector

```http
DELETE /connectors/{connector_id}
```

### Trigger Connector Sync

```http
POST /connectors/{connector_id}/sync
```

### Get Sync Status

```http
GET /connectors/{connector_id}/sync/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "syncing": false,
    "last_sync": "2024-06-15T10:00:00Z",
    "stats": {
      "total_items": 5000,
      "indexed": 4950,
      "skipped": 45,
      "failed": 5,
      "duration_seconds": 120.5
    }
  }
}
```

### Google Photos - Get Auth URL

```http
GET /connectors/google-photos/auth-url?redirect_uri={uri}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
  }
}
```

### Google Photos - OAuth Callback

```http
GET /connectors/google-photos/callback?code={code}&state={state}
```

Redirects to `/settings?connected=google-photos` on success.

### Google Photos - Disconnect

```http
POST /connectors/google-photos/disconnect
```

### Google Photos - Status

```http
GET /connectors/google-photos/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "connected": true,
    "email": "user@gmail.com",
    "photos_indexed": 5000,
    "last_sync": "2024-06-15T10:00:00Z"
  }
}
```

### Create Local Folder Connector

```http
POST /connectors/local
```

**Request:**
```json
{
  "path": "/home/user/Photos",
  "name": "My Photos",
  "recursive": true,
  "watch": true,
  "auto_album": false
}
```

---

## Settings API

### Get Settings

```http
GET /settings
```

**Response:**
```json
{
  "success": true,
  "data": {
    "config_dir": "~/.config/photo-explorer",
    "data_dir": "~/.local/share/photo-explorer",
    "cache_dir": "~/.cache/photo-explorer",
    "thumbnail_quality": 85,
    "clip_model": "ViT-B-32",
    "face_detection_enabled": true,
    "auto_index_new_photos": true,
    "thumbnail_cache_hours": 24,
    "indexing_batch_size": 100,
    "indexing_parallel_workers": 4,
    "default_sync_interval_hours": 6
  }
}
```

### Update Settings

```http
PATCH /settings
```

**Request:**
```json
{
  "thumbnail_quality": 90,
  "clip_model": "ViT-L-14",
  "face_detection_enabled": true
}
```

### Get Storage Stats

```http
GET /settings/storage
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_photos": 15000,
    "local_photos": 10000,
    "remote_photos": 5000,
    "storage_used_bytes": 52428800000,
    "thumbnails_cached": 14500,
    "cache_size_bytes": 1073741824
  }
}
```

---

## Models API

### Search Models on Hugging Face

```http
GET /models/search?query={query}&task={task}&limit={limit}
```

**Query Parameters:**
- `query`: string - Search query
- `task`: string (optional) - Filter by task (image-embedding, face-detection, etc.)
- `limit`: int (default: 20, max: 100)

**Response:**
```json
{
  "success": true,
  "data": {
    "models": [
      {
        "model_id": "openai/clip-vit-base-patch32",
        "author": "openai",
        "model_name": "clip-vit-base-patch32",
        "pipeline_tag": "zero-shot-image-classification",
        "tags": ["clip", "vision", "transformers"],
        "downloads": 5000000,
        "likes": 1200,
        "library_name": "transformers",
        "size_mb": 350.5,
        "is_downloaded": false
      }
    ]
  }
}
```

### Get Model Info

```http
GET /models/info/{author}/{model_name}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "model_id": "openai/clip-vit-base-patch32",
    "author": "openai",
    "model_name": "clip-vit-base-patch32",
    "pipeline_tag": "zero-shot-image-classification",
    "tags": ["clip", "vision"],
    "downloads": 5000000,
    "likes": 1200,
    "library_name": "transformers",
    "size_mb": 350.5,
    "files": ["config.json", "pytorch_model.bin", "tokenizer.json"],
    "is_downloaded": true
  }
}
```

### Download Model

```http
POST /models/download
```

**Request:**
```json
{
  "model_id": "openai/clip-vit-base-patch32",
  "revision": "main"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "model_id": "openai/clip-vit-base-patch32",
    "status": "downloading",
    "progress": 0.0
  }
}
```

### Get Download Progress

```http
GET /models/download/{author}/{model_name}/progress
```

**Response:**
```json
{
  "success": true,
  "data": {
    "model_id": "openai/clip-vit-base-patch32",
    "status": "downloading",
    "progress": 0.45,
    "downloaded_bytes": 157286400,
    "total_bytes": 349525333,
    "current_file": "pytorch_model.bin"
  }
}
```

### Delete Downloaded Model

```http
DELETE /models/download/{author}/{model_name}
```

### List Downloaded Models

```http
GET /models/downloaded
```

**Response:**
```json
{
  "success": true,
  "data": {
    "models": [
      "openai/clip-vit-base-patch32",
      "deepinsight/buffalo_l"
    ]
  }
}
```

### Get Recommended Models

```http
GET /models/recommended?task={task}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "recommendations": {
      "image-embedding": [
        {
          "model_id": "openai/clip-vit-base-patch32",
          "is_downloaded": true
        }
      ],
      "face-detection": [
        {
          "model_id": "deepinsight/buffalo_l",
          "is_downloaded": false
        }
      ]
    }
  }
}
```

### Get Active Models

```http
GET /models/active
```

**Response:**
```json
{
  "success": true,
  "data": {
    "clip_model": "ViT-B-32",
    "clip_status": "downloaded",
    "face_model": "buffalo_l",
    "face_status": "not_downloaded"
  }
}
```

### Set Active Model

```http
POST /models/active
```

**Request:**
```json
{
  "task": "clip",
  "model_id": "openai/clip-vit-large-patch14"
}
```

### List Model Tasks

```http
GET /models/tasks
```

**Response:**
```json
{
  "success": true,
  "data": {
    "tasks": [
      {"id": "image-embedding", "name": "Image Embedding"},
      {"id": "face-detection", "name": "Face Detection"},
      {"id": "zero-shot-image-classification", "name": "Zero Shot Image Classification"}
    ]
  }
}
```
