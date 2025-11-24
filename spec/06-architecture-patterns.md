# Photo Explorer - Architecture Patterns

## Backend: Domain-Driven Hexagonal Architecture

### Overview

The backend follows hexagonal architecture (also known as ports & adapters), combined with Domain-Driven Design principles. This architecture isolates the domain logic from external concerns, making the system more testable, maintainable, and flexible.

### Hexagonal Architecture Layers

```
                    ┌──────────────────────────────────────────────────┐
                    │                  Adapters (In)                    │
                    │  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
                    │  │   REST   │  │   CLI    │  │   Message    │    │
                    │  │   API    │  │          │  │   Consumer   │    │
                    │  └────┬─────┘  └────┬─────┘  └──────┬───────┘    │
                    └───────┼─────────────┼───────────────┼────────────┘
                            │             │               │
                            ▼             ▼               ▼
                    ┌──────────────────────────────────────────────────┐
                    │                  Ports (In)                       │
                    │  ┌──────────────────────────────────────────┐    │
                    │  │  PhotoUseCases  │  SearchUseCases  │ ... │    │
                    │  └──────────────────────────────────────────┘    │
                    └──────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Application Layer                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ PhotoAppService │  │SearchAppService │  │ FaceAppService  │                  │
│  │  (Orchestrator) │  │  (Orchestrator) │  │  (Orchestrator) │                  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘                  │
│           │                    │                    │                            │
│           ▼                    ▼                    ▼                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         Domain Layer                                     │    │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────────────────┐ │    │
│  │  │   Photo   │  │   Album   │  │   Face    │  │   Domain Services     │ │    │
│  │  │  Entity   │  │  Entity   │  │  Entity   │  │  (FaceClusterer, etc) │ │    │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────────────────┘ │    │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │    │
│  │  │                      Value Objects                                 │  │    │
│  │  │  PhotoId, Embedding, BoundingBox, ExifData, FilePath, etc.        │  │    │
│  │  └───────────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
                    ┌──────────────────────────────────────────────────┐
                    │                  Ports (Out)                      │
                    │  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  │
                    │  │ PhotoRepo   │  │ VectorStore │  │ Storage  │  │
                    │  │ (interface) │  │ (interface) │  │ (interf) │  │
                    │  └─────────────┘  └─────────────┘  └──────────┘  │
                    └──────────────────────────────────────────────────┘
                                          │
                                          ▼
                    ┌──────────────────────────────────────────────────┐
                    │                Adapters (Out)                     │
                    │  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
                    │  │PostgreSQL│  │  Qdrant  │  │ FileSystem   │    │
                    │  │ Adapter  │  │  Adapter │  │   Adapter    │    │
                    │  └──────────┘  └──────────┘  └──────────────┘    │
                    └──────────────────────────────────────────────────┘
```

### Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app entry point
│   ├── config.py                    # Configuration
│   │
│   ├── domain/                      # Domain Layer (Pure Python, no dependencies)
│   │   ├── __init__.py
│   │   ├── entities/                # Domain Entities
│   │   │   ├── __init__.py
│   │   │   ├── photo.py             # Photo aggregate root
│   │   │   ├── album.py             # Album aggregate root
│   │   │   ├── face.py              # Face entity
│   │   │   └── face_cluster.py      # FaceCluster aggregate root
│   │   │
│   │   ├── value_objects/           # Value Objects (immutable)
│   │   │   ├── __init__.py
│   │   │   ├── photo_id.py
│   │   │   ├── embedding.py
│   │   │   ├── bounding_box.py
│   │   │   ├── exif_data.py
│   │   │   ├── file_path.py
│   │   │   └── scene_classification.py
│   │   │
│   │   ├── services/                # Domain Services
│   │   │   ├── __init__.py
│   │   │   ├── face_clustering.py
│   │   │   └── similarity_scorer.py
│   │   │
│   │   ├── events/                  # Domain Events
│   │   │   ├── __init__.py
│   │   │   ├── photo_events.py
│   │   │   └── face_events.py
│   │   │
│   │   └── exceptions.py            # Domain Exceptions
│   │
│   ├── application/                 # Application Layer
│   │   ├── __init__.py
│   │   ├── ports/                   # Port Interfaces
│   │   │   ├── __init__.py
│   │   │   ├── inbound/             # Inbound Ports (Use Cases)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── photo_use_cases.py
│   │   │   │   ├── album_use_cases.py
│   │   │   │   ├── search_use_cases.py
│   │   │   │   └── face_use_cases.py
│   │   │   │
│   │   │   └── outbound/            # Outbound Ports (Repository interfaces)
│   │   │       ├── __init__.py
│   │   │       ├── photo_repository.py
│   │   │       ├── album_repository.py
│   │   │       ├── face_repository.py
│   │   │       ├── vector_store.py
│   │   │       ├── file_storage.py
│   │   │       └── ml_services.py
│   │   │
│   │   ├── services/                # Application Services (Use Case Implementations)
│   │   │   ├── __init__.py
│   │   │   ├── photo_service.py
│   │   │   ├── album_service.py
│   │   │   ├── search_service.py
│   │   │   └── face_service.py
│   │   │
│   │   ├── commands/                # Command DTOs
│   │   │   ├── __init__.py
│   │   │   ├── photo_commands.py
│   │   │   └── face_commands.py
│   │   │
│   │   └── queries/                 # Query DTOs
│   │       ├── __init__.py
│   │       ├── photo_queries.py
│   │       └── search_queries.py
│   │
│   └── adapters/                    # Adapters Layer
│       ├── __init__.py
│       ├── inbound/                 # Inbound Adapters
│       │   ├── __init__.py
│       │   ├── api/                 # REST API Adapter
│       │   │   ├── __init__.py
│       │   │   ├── routes/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── photos.py
│       │   │   │   ├── albums.py
│       │   │   │   ├── search.py
│       │   │   │   └── faces.py
│       │   │   ├── schemas/         # Pydantic schemas (API DTOs)
│       │   │   │   ├── __init__.py
│       │   │   │   ├── photo_schemas.py
│       │   │   │   ├── album_schemas.py
│       │   │   │   └── face_schemas.py
│       │   │   ├── mappers/         # DTO <-> Domain mappers
│       │   │   │   ├── __init__.py
│       │   │   │   └── photo_mapper.py
│       │   │   └── dependencies.py
│       │   │
│       │   └── workers/             # Background job handlers
│       │       ├── __init__.py
│       │       ├── photo_processor.py
│       │       └── folder_scanner.py
│       │
│       └── outbound/                # Outbound Adapters
│           ├── __init__.py
│           ├── persistence/
│           │   ├── __init__.py
│           │   ├── postgres/
│           │   │   ├── __init__.py
│           │   │   ├── models.py    # SQLAlchemy models
│           │   │   ├── photo_repo.py
│           │   │   ├── album_repo.py
│           │   │   └── face_repo.py
│           │   └── qdrant/
│           │       ├── __init__.py
│           │       └── vector_store.py
│           │
│           ├── storage/
│           │   ├── __init__.py
│           │   └── filesystem.py
│           │
│           └── ml/
│               ├── __init__.py
│               ├── clip_encoder.py
│               ├── vision_llm.py
│               └── face_detector.py
│
└── tests/
    ├── conftest.py
    ├── unit/
    │   ├── domain/                  # Test domain logic in isolation
    │   │   ├── test_photo.py
    │   │   └── test_face_clustering.py
    │   └── application/             # Test use cases with mocked ports
    │       ├── test_photo_service.py
    │       └── test_search_service.py
    ├── integration/                  # Test adapters against real dependencies
    │   ├── test_photo_api.py
    │   ├── test_postgres_repo.py
    │   └── test_qdrant_store.py
    └── features/                     # BDD tests
        ├── photo_upload.feature
        └── steps/
```

### Key Principles

#### 1. Dependency Rule

Dependencies always point inward. The domain layer has NO external dependencies.

```python
# GOOD: Domain entity has no infrastructure imports
# domain/entities/photo.py
from dataclasses import dataclass
from datetime import datetime
from ..value_objects import PhotoId, ExifData

@dataclass
class Photo:
    id: PhotoId
    filename: str
    exif: ExifData
    created_at: datetime

# BAD: Domain entity imports SQLAlchemy
from sqlalchemy.orm import relationship  # ❌ NEVER DO THIS
```

#### 2. Ports Define Contracts

Ports are interfaces that define what the application needs, not how it's implemented.

```python
# application/ports/outbound/photo_repository.py
from abc import ABC, abstractmethod
from typing import Optional
from app.domain.entities import Photo
from app.domain.value_objects import PhotoId

class PhotoRepository(ABC):
    """Port for photo persistence operations."""

    @abstractmethod
    async def save(self, photo: Photo) -> Photo:
        """Persist a photo."""
        pass

    @abstractmethod
    async def find_by_id(self, photo_id: PhotoId) -> Optional[Photo]:
        """Find a photo by ID."""
        pass

    @abstractmethod
    async def find_all(self, limit: int, offset: int) -> list[Photo]:
        """Find all photos with pagination."""
        pass
```

#### 3. Adapters Implement Ports

Adapters provide concrete implementations for ports.

```python
# adapters/outbound/persistence/postgres/photo_repo.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.application.ports.outbound import PhotoRepository
from app.domain.entities import Photo
from .models import PhotoModel
from .mappers import PhotoMapper

class PostgresPhotoRepository(PhotoRepository):
    """PostgreSQL implementation of PhotoRepository port."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._mapper = PhotoMapper()

    async def save(self, photo: Photo) -> Photo:
        model = self._mapper.to_model(photo)
        self._session.add(model)
        await self._session.commit()
        return self._mapper.to_entity(model)

    async def find_by_id(self, photo_id: PhotoId) -> Optional[Photo]:
        model = await self._session.get(PhotoModel, str(photo_id))
        return self._mapper.to_entity(model) if model else None
```

#### 4. Application Services Orchestrate

Application services coordinate between domain objects and ports.

```python
# application/services/photo_service.py
from app.application.ports.inbound import PhotoUseCases
from app.application.ports.outbound import PhotoRepository, FileStorage, VectorStore
from app.application.commands import UploadPhotoCommand
from app.domain.entities import Photo

class PhotoService(PhotoUseCases):
    """Application service implementing photo use cases."""

    def __init__(
        self,
        photo_repo: PhotoRepository,
        file_storage: FileStorage,
        vector_store: VectorStore,
        event_bus: EventBus,
    ):
        self._photo_repo = photo_repo
        self._file_storage = file_storage
        self._vector_store = vector_store
        self._event_bus = event_bus

    async def upload_photo(self, command: UploadPhotoCommand) -> Photo:
        # Store file
        storage_path = await self._file_storage.save(
            command.file_content,
            command.filename
        )

        # Create domain entity
        photo = Photo.create(
            filename=command.filename,
            storage_path=storage_path,
            album_id=command.album_id
        )

        # Persist
        saved_photo = await self._photo_repo.save(photo)

        # Publish domain event
        await self._event_bus.publish(
            PhotoUploaded(photo_id=saved_photo.id)
        )

        return saved_photo
```

---

## Frontend: Feature-Based Architecture

### Overview

The frontend uses a feature-based architecture where code is organized by feature/domain rather than by technical layer. This co-locates related components, stores, and utilities together.

### Directory Structure

```
frontend/
├── src/
│   ├── app.html
│   ├── app.css
│   │
│   ├── lib/
│   │   ├── api/                     # API client layer
│   │   │   ├── index.ts
│   │   │   ├── client.ts            # Base HTTP client
│   │   │   ├── photos.ts            # Photo API calls
│   │   │   ├── albums.ts            # Album API calls
│   │   │   ├── search.ts            # Search API calls
│   │   │   └── faces.ts             # Face API calls
│   │   │
│   │   ├── features/                # Feature modules
│   │   │   ├── upload/
│   │   │   │   ├── index.ts         # Public exports
│   │   │   │   ├── components/
│   │   │   │   │   ├── UploadZone.svelte
│   │   │   │   │   ├── UploadProgress.svelte
│   │   │   │   │   └── AlbumSelector.svelte
│   │   │   │   ├── stores/
│   │   │   │   │   └── upload.ts
│   │   │   │   ├── types.ts
│   │   │   │   └── utils.ts
│   │   │   │
│   │   │   ├── search/
│   │   │   │   ├── index.ts
│   │   │   │   ├── components/
│   │   │   │   │   ├── SearchBar.svelte
│   │   │   │   │   ├── SearchResults.svelte
│   │   │   │   │   ├── SearchFilters.svelte
│   │   │   │   │   └── PhotoCard.svelte
│   │   │   │   ├── stores/
│   │   │   │   │   ├── search.ts
│   │   │   │   │   └── filters.ts
│   │   │   │   └── types.ts
│   │   │   │
│   │   │   ├── albums/
│   │   │   │   ├── index.ts
│   │   │   │   ├── components/
│   │   │   │   │   ├── AlbumGrid.svelte
│   │   │   │   │   ├── AlbumCard.svelte
│   │   │   │   │   ├── AlbumDetail.svelte
│   │   │   │   │   └── CreateAlbumModal.svelte
│   │   │   │   ├── stores/
│   │   │   │   │   └── albums.ts
│   │   │   │   └── types.ts
│   │   │   │
│   │   │   ├── photos/
│   │   │   │   ├── index.ts
│   │   │   │   ├── components/
│   │   │   │   │   ├── PhotoGrid.svelte
│   │   │   │   │   ├── PhotoDetail.svelte
│   │   │   │   │   ├── PhotoMetadata.svelte
│   │   │   │   │   └── PhotoActions.svelte
│   │   │   │   ├── stores/
│   │   │   │   │   └── photos.ts
│   │   │   │   └── types.ts
│   │   │   │
│   │   │   ├── faces/
│   │   │   │   ├── index.ts
│   │   │   │   ├── components/
│   │   │   │   │   ├── FaceClusterGrid.svelte
│   │   │   │   │   ├── FaceCluster.svelte
│   │   │   │   │   ├── FaceTagModal.svelte
│   │   │   │   │   └── FaceMergeDropzone.svelte
│   │   │   │   ├── stores/
│   │   │   │   │   └── faces.ts
│   │   │   │   └── types.ts
│   │   │   │
│   │   │   └── folders/
│   │   │       ├── index.ts
│   │   │       ├── components/
│   │   │       │   ├── FolderList.svelte
│   │   │       │   ├── FolderCard.svelte
│   │   │       │   └── AddFolderModal.svelte
│   │   │       ├── stores/
│   │   │       │   └── folders.ts
│   │   │       └── types.ts
│   │   │
│   │   ├── shared/                   # Shared components and utilities
│   │   │   ├── components/
│   │   │   │   ├── Button.svelte
│   │   │   │   ├── Modal.svelte
│   │   │   │   ├── LoadingSpinner.svelte
│   │   │   │   ├── Toast.svelte
│   │   │   │   ├── VirtualList.svelte
│   │   │   │   └── ImageLazy.svelte
│   │   │   ├── stores/
│   │   │   │   ├── toast.ts
│   │   │   │   └── theme.ts
│   │   │   ├── utils/
│   │   │   │   ├── format.ts
│   │   │   │   ├── debounce.ts
│   │   │   │   └── validation.ts
│   │   │   └── types/
│   │   │       └── common.ts
│   │   │
│   │   └── index.ts                  # Lib barrel export
│   │
│   └── routes/                       # SvelteKit routes
│       ├── +layout.svelte
│       ├── +layout.ts
│       ├── +page.svelte              # Home/Dashboard
│       ├── upload/
│       │   └── +page.svelte
│       ├── search/
│       │   └── +page.svelte
│       ├── albums/
│       │   ├── +page.svelte
│       │   └── [id]/
│       │       └── +page.svelte
│       ├── photos/
│       │   └── [id]/
│       │       └── +page.svelte
│       ├── faces/
│       │   ├── +page.svelte          # Face Explorer
│       │   └── [clusterId]/
│       │       └── +page.svelte
│       └── settings/
│           ├── +page.svelte
│           └── folders/
│               └── +page.svelte
│
├── tests/
│   ├── e2e/
│   │   ├── upload.spec.ts
│   │   ├── search.spec.ts
│   │   └── faces.spec.ts
│   └── fixtures/
│       └── handlers.ts
│
├── static/
├── svelte.config.js
├── vite.config.ts
├── vitest.config.ts
└── playwright.config.ts
```

### Feature Module Pattern

Each feature is self-contained with its own:
- Components (presentation)
- Stores (state management)
- Types (TypeScript interfaces)
- Utils (feature-specific utilities)

```typescript
// lib/features/search/index.ts
// Public exports for the search feature

export { default as SearchBar } from './components/SearchBar.svelte';
export { default as SearchResults } from './components/SearchResults.svelte';
export { default as SearchFilters } from './components/SearchFilters.svelte';
export { searchStore, filterStore } from './stores';
export type { SearchResult, SearchFilters } from './types';
```

### Store Pattern

Feature stores encapsulate state and behavior:

```typescript
// lib/features/search/stores/search.ts
import { writable, derived } from 'svelte/store';
import { searchApi } from '$lib/api';
import type { SearchResult, SearchQuery } from '../types';

function createSearchStore() {
  const results = writable<SearchResult[]>([]);
  const loading = writable(false);
  const error = writable<string | null>(null);
  const query = writable<SearchQuery>({ text: '' });

  async function search(searchQuery: SearchQuery) {
    loading.set(true);
    error.set(null);
    query.set(searchQuery);

    try {
      const data = await searchApi.search(searchQuery);
      results.set(data.results);
    } catch (e) {
      error.set(e instanceof Error ? e.message : 'Search failed');
    } finally {
      loading.set(false);
    }
  }

  function clear() {
    results.set([]);
    query.set({ text: '' });
  }

  return {
    results: { subscribe: results.subscribe },
    loading: { subscribe: loading.subscribe },
    error: { subscribe: error.subscribe },
    query: { subscribe: query.subscribe },
    search,
    clear,
  };
}

export const searchStore = createSearchStore();
```

### API Layer Pattern

API calls are isolated in the api directory:

```typescript
// lib/api/search.ts
import { client } from './client';
import type { SearchQuery, SearchResponse } from '$lib/features/search/types';

export const searchApi = {
  async search(query: SearchQuery): Promise<SearchResponse> {
    const response = await client.post('/api/v1/search', query);
    return response.data;
  },

  async findSimilar(photoId: string, limit = 10): Promise<SearchResponse> {
    const response = await client.get(`/api/v1/photos/${photoId}/similar`, {
      params: { limit },
    });
    return response.data;
  },
};
```

### Component Composition

Route pages compose feature components:

```svelte
<!-- routes/search/+page.svelte -->
<script lang="ts">
  import { SearchBar, SearchResults, SearchFilters, searchStore } from '$lib/features/search';
  import { PhotoDetail } from '$lib/features/photos';

  let selectedPhoto: Photo | null = null;
</script>

<div class="search-page">
  <header>
    <SearchBar on:search={(e) => searchStore.search(e.detail)} />
    <SearchFilters />
  </header>

  <main>
    <SearchResults
      on:select={(e) => selectedPhoto = e.detail}
    />
  </main>

  {#if selectedPhoto}
    <PhotoDetail
      photo={selectedPhoto}
      on:close={() => selectedPhoto = null}
    />
  {/if}
</div>
```

### Testing Feature Modules

Each feature has co-located tests:

```
lib/features/search/
├── components/
│   ├── SearchBar.svelte
│   └── SearchBar.test.ts    # Component tests next to component
├── stores/
│   ├── search.ts
│   └── search.test.ts       # Store tests next to store
```

This organization makes it easy to:
1. Find all code related to a feature
2. Add/modify features without affecting others
3. Extract features into separate packages if needed
4. Test features in isolation
