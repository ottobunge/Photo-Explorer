# Photo Explorer - Architecture Specification

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Frontend (SvelteKit)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Upload  │  │  Search  │  │  Albums  │  │  Dataset │  │   Face   │  │
│  │   View   │  │   View   │  │   View   │  │   View   │  │ Explorer │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           API Gateway (FastAPI)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ Photo Routes │  │ Album Routes │  │ Search Routes│  │ Face Routes │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌──────────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐
│   Services Layer     │ │  Task Queue     │ │      ML Services            │
│  ┌────────────────┐  │ │  (Celery/Redis) │ │  ┌─────────────────────┐   │
│  │ PhotoService   │  │ │                 │ │  │   CLIP Encoder      │   │
│  │ AlbumService   │  │ │  ┌───────────┐  │ │  │   (Image + Text)    │   │
│  │ SearchService  │  │ │  │ Process   │  │ │  └─────────────────────┘   │
│  │ FaceService    │  │ │  │ Photo Job │  │ │  ┌─────────────────────┐   │
│  │ FolderService  │  │ │  └───────────┘  │ │  │   Vision LLM        │   │
│  └────────────────┘  │ │  ┌───────────┐  │ │  │   (Descriptions)    │   │
│                      │ │  │ Scan      │  │ │  └─────────────────────┘   │
│                      │ │  │ Folder Job│  │ │  ┌─────────────────────┐   │
│                      │ │  └───────────┘  │ │  │   Face Detector     │   │
│                      │ │                 │ │  │   (InsightFace)     │   │
└──────────────────────┘ └─────────────────┘ │  └─────────────────────┘   │
                                             └─────────────────────────────┘
                    │               │               │
                    ▼               ▼               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                            Data Layer                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐ │
│  │     PostgreSQL      │  │       Qdrant        │  │   File Storage   │ │
│  │  - Photos metadata  │  │  - Image embeddings │  │  - Original imgs │ │
│  │  - Albums           │  │  - Face embeddings  │  │  - Thumbnails    │ │
│  │  - Face tags        │  │  - Text embeddings  │  │  - Processed     │ │
│  │  - Folder configs   │  │                     │  │                  │ │
│  └─────────────────────┘  └─────────────────────┘  └──────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Frontend Components

#### Upload View
- Drag-and-drop file upload
- Album selection/creation
- Progress tracking for uploads
- Folder path configuration for local scanning

#### Search View
- Text input for natural language queries
- Real-time search results
- Filter by date, album, faces
- Grid/list view toggle

#### Albums View
- Album grid display
- Album CRUD operations
- Bulk photo operations

#### Dataset View
- Detailed photo information
- EXIF metadata display
- AI-generated descriptions
- Scene classification (indoor/outdoor)
- Detected objects and faces
- Edit/correct AI predictions

#### Face Explorer View
- Face cluster display
- Drag-and-drop for merging clusters
- Name assignment to clusters
- Search by person name
- View all photos of a person

### Backend Services

#### PhotoService
- Photo CRUD operations
- Metadata extraction (EXIF)
- Thumbnail generation
- Coordinate with ML processing

#### AlbumService
- Album CRUD operations
- Photo-album associations
- Smart album generation

#### SearchService
- Text-to-embedding conversion
- Qdrant vector search
- Result ranking and filtering
- Multi-modal search (text + face + date)

#### FaceService
- Face detection coordination
- Face embedding storage
- Cluster management
- Name-to-cluster mapping

#### FolderService
- Folder registration
- Filesystem watching
- Incremental sync
- Conflict resolution

### ML Services

#### CLIP Encoder
- Image embedding generation (ViT-L/14 or similar)
- Text embedding generation
- Batch processing support

#### Vision LLM
- Detailed image descriptions
- Object detection listing
- Scene classification
- Indoor/outdoor detection

#### Face Detector
- Face detection in images
- Face embedding generation
- Quality scoring for face crops

## Data Models

### PostgreSQL Schema

```sql
-- Photos table
CREATE TABLE photos (
    id UUID PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_path TEXT,
    storage_path TEXT NOT NULL,
    thumbnail_path TEXT,
    mime_type VARCHAR(50),
    file_size BIGINT,
    width INTEGER,
    height INTEGER,
    taken_at TIMESTAMP,
    exif_data JSONB,
    description TEXT,
    scene_type VARCHAR(50),
    is_indoor BOOLEAN,
    detected_objects JSONB,
    processing_status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Albums table
CREATE TABLE albums (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    cover_photo_id UUID REFERENCES photos(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Photo-Album association
CREATE TABLE album_photos (
    album_id UUID REFERENCES albums(id),
    photo_id UUID REFERENCES photos(id),
    position INTEGER,
    PRIMARY KEY (album_id, photo_id)
);

-- Face clusters
CREATE TABLE face_clusters (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    representative_face_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Detected faces
CREATE TABLE faces (
    id UUID PRIMARY KEY,
    photo_id UUID REFERENCES photos(id),
    cluster_id UUID REFERENCES face_clusters(id),
    bbox_x INTEGER,
    bbox_y INTEGER,
    bbox_width INTEGER,
    bbox_height INTEGER,
    quality_score FLOAT,
    crop_path TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Watched folders
CREATE TABLE watched_folders (
    id UUID PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    name VARCHAR(255),
    recursive BOOLEAN DEFAULT TRUE,
    auto_album BOOLEAN DEFAULT FALSE,
    last_scanned_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Qdrant Collections

```python
# Image embeddings collection
{
    "name": "photo_embeddings",
    "vectors": {
        "size": 768,  # CLIP ViT-L/14
        "distance": "Cosine"
    },
    "payload_schema": {
        "photo_id": "uuid",
        "album_ids": "keyword[]"
    }
}

# Face embeddings collection
{
    "name": "face_embeddings",
    "vectors": {
        "size": 512,  # InsightFace
        "distance": "Cosine"
    },
    "payload_schema": {
        "face_id": "uuid",
        "photo_id": "uuid",
        "cluster_id": "uuid"
    }
}
```

## Testing Strategy

### Test-Driven Development (TDD)

All development follows TDD principles with behavior-focused tests:

1. **Write failing test first** - Define expected behavior
2. **Implement minimal code** - Make test pass
3. **Refactor** - Clean up while tests pass

### Backend Testing

#### Unit Tests (pytest)
- Service layer logic
- Data transformations
- Utility functions

#### Integration Tests (pytest + testcontainers)
- API endpoint behavior
- Database operations
- Queue job processing

#### Behavior Tests (pytest-bdd)
```gherkin
Feature: Photo Search
  Scenario: User searches for beach photos
    Given I have uploaded photos including beach scenes
    When I search for "sunny beach"
    Then I should see photos matching beach scenes
    And results should be ordered by relevance
```

### Frontend Testing

#### Unit Tests (Vitest)
- Component logic
- Store behavior
- Utility functions

#### Component Tests (Testing Library)
- Component rendering
- User interactions
- Accessibility

#### E2E Tests (Playwright)
```typescript
test('user can search photos by text', async ({ page }) => {
  await page.goto('/search');
  await page.fill('[data-testid="search-input"]', 'sunset');
  await page.click('[data-testid="search-button"]');
  await expect(page.locator('[data-testid="search-results"]')).toBeVisible();
});
```

## Security Considerations

- File upload validation (type, size)
- Path traversal prevention for folder scanning
- Rate limiting on API endpoints
- Input sanitization
- CORS configuration
