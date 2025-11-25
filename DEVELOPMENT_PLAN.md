# Photo Explorer Development Plan

**Created**: 2025-11-25
**Last Updated**: 2025-11-25
**Status**: Active

---

## 🎯 Project Status

### Current State
- **Backend**: B+ (7.7/10) - Production-ready with critical fixes needed
- **Frontend**: B+ (7.4/10) - Good architecture, needs SSR and accessibility
- **Worker**: B (7.5/10) - Solid foundation, needs monitoring
- **Test Coverage**: 80% for connector APIs (20/25 tests passing)

### Migration Status
- ✅ Fixed enum creation issue in migrations
- ✅ All migrations now run successfully
- ✅ Database schema up to date

---

## 🔴 CRITICAL FIXES (Sprint 1 - Week 1)

**Estimated**: 3-4 days
**Must complete before any new features**

### Backend (6 items)

#### 1. Fix Path Traversal Vulnerability ⚠️ SECURITY
**File**: `backend/app/adapters/inbound/api/routes/connectors.py:725-737`
**Priority**: CRITICAL
**Effort**: 2 hours

```python
# Current: Users can add ANY directory as photo source
path = Path(request.path)
if not path.exists():
    raise HTTPException(status_code=400, ...)

# Fix: Validate against allowed base paths
ALLOWED_BASE_PATHS = [
    Path.home() / "Pictures",
    Path("/media"),
    Path("/mnt"),
]

def is_path_allowed(path: Path) -> bool:
    path = path.resolve()  # Resolve symlinks
    return any(path.is_relative_to(base) for base in ALLOWED_BASE_PATHS)

if not is_path_allowed(path):
    raise HTTPException(status_code=403, detail="Path outside allowed directories")
```

**Test**: Create test attempting to add `/etc/passwd` as connector

---

#### 2. Fix Domain Model Violations
**File**: `backend/app/adapters/inbound/api/routes/connectors.py:164-176`
**Priority**: HIGH
**Effort**: 2 hours

**Problem**: Direct entity mutation bypasses business logic
```python
# ❌ Current
if request.enabled is not None:
    connector.enabled = request.enabled  # Bypasses domain methods
connector.updated_at = datetime.utcnow()  # Manual timestamp

# ✅ Fix
if request.enabled is not None:
    if request.enabled:
        connector.enable()
    else:
        connector.disable()
# connector._touch() called automatically by domain methods
```

**Also update**: Lines 740-756 in same file

---

#### 3. Add Transaction Management
**File**: `backend/app/adapters/inbound/api/routes/connectors.py:215-220`
**Priority**: HIGH
**Effort**: 1 hour

**Problem**: Multi-step delete without rollback
```python
# ❌ Current
if delete_photos:
    photos = await photo_repo.find_by_connector(connector_id, limit=10000, offset=0)
    for photo in photos:
        await photo_repo.delete(photo.id.value)
deleted = await connector_repo.delete(connector_id)

# ✅ Fix
from app.dependencies import get_db

async with session.begin():
    if delete_photos:
        # Batch delete with proper transaction
        offset = 0
        batch_size = 100
        while True:
            photos = await photo_repo.find_by_connector(connector_id, batch_size, offset)
            if not photos:
                break
            for photo in photos:
                await photo_repo.delete(photo.id.value)
            offset += batch_size
    deleted = await connector_repo.delete(connector_id)
```

---

#### 4. Add `find_by_path` to Repository Interface
**File**: `backend/app/application/ports/outbound/connector_repository.py`
**Priority**: MEDIUM
**Effort**: 30 minutes

```python
@abstractmethod
async def find_by_path(self, path: str) -> Optional[Connector]:
    """Find a local connector by its absolute path."""
    pass
```

**Reason**: Currently implemented in concrete class but not in interface (contract violation)

---

#### 5. Standardize API Response Format
**Files**: All `backend/app/adapters/inbound/api/routes/*.py`
**Priority**: MEDIUM
**Effort**: 2 hours

**Issue**: snake_case vs camelCase mixed in responses

```python
# Decision: Use snake_case everywhere (Python convention)
{
    "id": "...",
    "thumbnail_url": "...",  # NOT thumbnailUrl
    "created_at": "...",     # NOT createdAt
    "connector_id": "...",   # NOT connectorId
}
```

**Update**:
- `GET /connectors/{id}/photos` - Change camelCase to snake_case
- All connector responses
- Frontend API types to match

---

#### 6. Implement Structured Logging
**Files**: All worker tasks, API routes
**Priority**: HIGH (replaces Prometheus/Grafana recommendation)
**Effort**: 4 hours

**Setup**: Use `structlog` for JSON-structured logs

```bash
poetry add structlog python-json-logger
```

**Configuration** (`backend/app/core/logging.py`):
```python
import structlog
import logging
from pythonjsonlogger import jsonlogger

def setup_logging():
    """Configure structured logging for production."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

# Usage in routes
logger = structlog.get_logger()
logger.info("connector_created",
    connector_id=str(connector.id.value),
    connector_type=connector.type.value,
    path=request.path,
    request_id=request_id
)
```

**Add to**:
- All API endpoints (request/response logging)
- Worker tasks (task start/end, retries, errors)
- Service layer operations
- Database operations (slow query logging)

**Monitoring queries**:
```bash
# Count errors by endpoint
cat app.log | jq -r 'select(.level=="error") | .endpoint' | sort | uniq -c

# Find slow database queries
cat app.log | jq -r 'select(.query_time > 1000) | {query, time: .query_time}'

# Track connector sync success rate
cat app.log | jq -r 'select(.event=="connector_sync_complete") | .connector_id' | wc -l
```

---

### Frontend (3 items)

#### 7. Implement SvelteKit Load Functions
**Files**: All route `+page.svelte` files
**Priority**: HIGH
**Effort**: 6 hours

**Replace**: `onMount()` data fetching
**With**: `+page.ts` load functions

```typescript
// routes/connectors/+page.ts
import type { PageLoad } from './$types';
import { client } from '$lib/api/client';

export const load: PageLoad = async () => {
  const response = await client.get('/connectors');
  return {
    connectors: response.data.connectors
  };
};

// routes/connectors/+page.svelte
<script lang="ts">
  import type { PageData } from './$types';

  export let data: PageData;
  $: ({ connectors } = data);
</script>
```

**Update**:
- `routes/+page.svelte` (dashboard)
- `routes/connectors/+page.svelte`
- `routes/connectors/[id]/+page.svelte`
- `routes/search/+page.svelte`
- `routes/albums/+page.svelte`

**Benefits**: SSR, better SEO, faster perceived load

---

#### 8. Standardize API Client Usage
**Files**: All feature stores
**Priority**: HIGH
**Effort**: 2 hours

**Problem**: 4 stores use raw `fetch` instead of typed client

**Fix**:
- `lib/features/folders/stores/folders.ts` - Replace `fetch` with `client.get`
- `lib/features/faces/stores/faces.ts` - Replace `fetch` with `client.get`
- `lib/features/search/stores/search.ts` - Replace `fetch` with `client.post`
- `lib/features/albums/stores/albums.ts` - Replace `fetch` with `client.get`

**Example**:
```typescript
// ❌ Before
const response = await fetch('/api/v1/folders');
const data = await response.json();

// ✅ After
const response = await client.get<{ folders: Folder[] }>('/folders');
const folders = response.data.folders;
```

---

#### 9. Add Basic Accessibility (ARIA)
**Files**: Key components
**Priority**: HIGH (legal/ethical requirement)
**Effort**: 3 hours

**Add to**:
- Navigation links (`routes/+layout.svelte`): `aria-current`, `aria-label`
- Icon buttons: `aria-label` for screen readers
- Modals: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`
- Form inputs: `aria-required`, `aria-invalid`, `aria-describedby`
- Loading states: `aria-live="polite"`

**Example**:
```svelte
<!-- Navigation -->
<a
  href="/photos"
  aria-label="Photos"
  aria-current={$page.url.pathname === '/photos' ? 'page' : undefined}
>
  <span aria-hidden="true">📷</span>
  Photos
</a>

<!-- Icon button -->
<button aria-label="Delete connector" on:click={handleDelete}>
  <TrashIcon aria-hidden="true" />
</button>

<!-- Loading state -->
<div aria-live="polite" aria-busy={loading}>
  {#if loading}Loading connectors...{/if}
</div>
```

---

### Worker (2 items)

#### 10. Apply Retry Patterns to All Tasks
**Files**: Worker task modules
**Priority**: HIGH
**Effort**: 2 hours

**Fix**:
- `app/adapters/inbound/workers/tasks/photo_analysis.py` - Add retry decorators
- `app/adapters/inbound/workers/tasks/face_clustering.py` - Add retry decorators
- `app/adapters/inbound/workers/tasks/connector_sync.py` - Complete retry implementation

**Change from returning errors to raising exceptions**:
```python
# ❌ Current (photo_analysis.py)
def analyze_photo(photo_id):
    try:
        # ... analysis
    except Exception as e:
        return {"status": "error", "message": str(e)}  # Bad

# ✅ Fixed
@shared_task(bind=True, base=LoggingTask, max_retries=3)
def analyze_photo(self, photo_id):
    try:
        # ... analysis
    except ApiRateLimitError as e:
        raise TransientError(f"Rate limited: {e}") from e  # Retry
    except InvalidPhotoError as e:
        raise PermanentError(f"Invalid photo: {e}") from e  # Don't retry
```

---

#### 11. Add Task Timeouts
**File**: `backend/app/adapters/inbound/workers/celery_app.py`
**Priority**: MEDIUM
**Effort**: 30 minutes

```python
# Add timeouts to prevent infinite execution
CELERY_CONFIG = {
    # ... existing config
    'task_soft_time_limit': 600,  # 10 minutes warning
    'task_time_limit': 900,       # 15 minutes hard limit
    'task_track_started': True,   # Track when task actually starts
}

# Per-task overrides in task definitions
@shared_task(
    bind=True,
    base=LoggingTask,
    max_retries=3,
    soft_time_limit=1800,  # 30 min for ML tasks
    time_limit=2100         # 35 min hard limit
)
def process_photo(self, photo_id):
    ...
```

---

## 🟠 HIGH PRIORITY (Sprint 2 - Week 2)

**Estimated**: 5-6 days

### Backend (6 items)

#### 12. Create ConnectorService Layer
**File**: New `backend/app/application/services/connector_service.py`
**Effort**: 4 hours

Move business logic from API routes to service layer:

```python
class ConnectorService:
    """Application service for connector operations."""

    def __init__(
        self,
        connector_repo: ConnectorRepository,
        photo_repo: PhotoRepository,
    ):
        self._connector_repo = connector_repo
        self._photo_repo = photo_repo

    async def create_local_connector(
        self,
        path: str,
        name: Optional[str] = None,
        recursive: bool = True,
        watch: bool = False,
        auto_album: bool = False,
    ) -> Connector:
        """Create local folder connector with full validation."""
        # Path validation
        validated_path = self._validate_local_path(path)

        # Check for duplicates
        existing = await self._connector_repo.find_by_path(str(validated_path))
        if existing:
            raise ValueError(f"Connector already exists for: {path}")

        # Generate name
        connector_name = name or validated_path.name or "Local Folder"

        # Create via domain factory
        connector = Connector.create_local(
            path=str(validated_path),
            name=connector_name,
            recursive=recursive,
            watch=watch,
            auto_album=auto_album,
        )

        return await self._connector_repo.save(connector)

    async def update_connector(
        self,
        connector_id: UUID,
        name: Optional[str] = None,
        enabled: Optional[bool] = None,
        config: Optional[dict] = None,
    ) -> Connector:
        """Update connector with domain method enforcement."""
        connector = await self._connector_repo.find_by_id(connector_id)
        if not connector:
            raise ValueError("Connector not found")

        if name is not None:
            connector.name = name

        if enabled is not None:
            if enabled:
                connector.enable()
            else:
                connector.disable()

        if config is not None:
            connector.update_config(config)

        return await self._connector_repo.save(connector)
```

**Update routes to use service**:
```python
@router.post("/local")
async def create_local_connector(
    request: LocalFolderCreateRequest,
    connector_service: ConnectorServiceDep,  # Inject service
) -> ConnectorResponse:
    connector = await connector_service.create_local_connector(
        path=request.path,
        name=request.name,
        recursive=request.recursive,
        watch=request.watch,
        auto_album=request.auto_album,
    )
    # ... format response
```

---

#### 13. Fix N+1 Query in Album Associations
**File**: `backend/app/adapters/outbound/persistence/postgres/repositories/photo_repository.py:56-67`
**Effort**: 1 hour

```python
# ❌ Current
for album_id in album_ids:
    album = await self._session.get(AlbumModel, album_id)  # N+1 query!
    if album:
        model.albums.append(album)

# ✅ Fixed
if album_ids:
    stmt = select(AlbumModel).where(AlbumModel.id.in_(album_ids))
    result = await self._session.execute(stmt)
    albums = result.scalars().all()

    for album in albums:
        model.albums.append(album)
```

---

#### 14. Add Database Index for JSON Path Queries
**File**: New migration
**Effort**: 30 minutes

```python
# alembic revision -m "add_connector_path_index"
def upgrade():
    op.execute("""
        CREATE INDEX ix_connectors_config_path
        ON connectors
        USING btree ((config->>'path'))
    """)

def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_connectors_config_path")
```

**Test performance**:
```sql
EXPLAIN ANALYZE
SELECT * FROM connectors
WHERE config->>'path' = '/home/user/photos';
```

---

#### 15. Implement Bulk Photo Delete
**File**: `backend/app/adapters/outbound/persistence/postgres/repositories/photo_repository.py`
**Effort**: 1 hour

```python
async def delete_many(self, photo_ids: list[UUID]) -> int:
    """Delete multiple photos efficiently."""
    if not photo_ids:
        return 0

    stmt = delete(PhotoModel).where(PhotoModel.id.in_(photo_ids))
    result = await self._session.execute(stmt)
    await self._session.flush()
    return result.rowcount
```

**Use in connector deletion**:
```python
if delete_photos:
    photos = await photo_repo.find_by_connector(connector_id, limit=10000, offset=0)
    photo_ids = [photo.id.value for photo in photos]
    deleted_count = await photo_repo.delete_many(photo_ids)
```

---

#### 16. Complete Async Endpoint Status Codes
**Files**: `backend/app/adapters/inbound/api/routes/connectors.py`
**Effort**: 2 hours

Update endpoints to return 202 Accepted for async operations:

```python
@router.post("/{connector_id}/reprocess", status_code=202)
async def reprocess_photos(connector_id: UUID) -> dict:
    """Queue photos for reprocessing."""
    # ... validation

    # Queue background task
    from app.adapters.inbound.workers.tasks.photo_processing import process_photo
    for photo in photos:
        process_photo.delay(str(photo.id.value))

    return {
        "status": "accepted",
        "message": f"Queued {len(photos)} photos for reprocessing",
        "task_count": len(photos)
    }

@router.post("/{connector_id}/sync", status_code=202)
async def trigger_sync(connector_id: UUID) -> dict:
    """Trigger connector sync."""
    # ... validation

    # Queue sync task
    from app.adapters.inbound.workers.tasks.connector_sync import sync_connector
    task = sync_connector.delay(str(connector_id))

    return {
        "status": "accepted",
        "message": "Sync started",
        "task_id": task.id
    }
```

**Update tests** to expect 202 instead of 200.

---

#### 17. Implement SyncStats Response
**File**: New `backend/app/domain/value_objects/sync_stats.py`
**Effort**: 1 hour

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class SyncStats:
    """Statistics from a connector sync operation."""

    photos_found: int
    photos_added: int
    photos_updated: int
    photos_deleted: int
    errors: int
    started_at: datetime
    completed_at: datetime

    @property
    def duration_seconds(self) -> float:
        """Sync duration in seconds."""
        return (self.completed_at - self.started_at).total_seconds()
```

**Add to Connector entity**:
```python
class Connector:
    # ...
    last_sync_stats: Optional[SyncStats] = None
```

**Use in sync status endpoint**:
```python
@router.get("/{connector_id}/sync/status")
async def get_sync_status(connector_id: UUID) -> dict:
    connector = await connector_repo.find_by_id(connector_id)

    return {
        "syncing": connector.status == ConnectorStatus.SYNCING,
        "last_sync": connector.last_sync.isoformat() if connector.last_sync else None,
        "stats": {
            "photos_added": connector.last_sync_stats.photos_added if connector.last_sync_stats else 0,
            "photos_updated": connector.last_sync_stats.photos_updated if connector.last_sync_stats else 0,
            # ...
        } if connector.last_sync_stats else None
    }
```

---

### Frontend (4 items)

#### 18. Split Large Settings Store
**Files**: `lib/features/settings/stores/`
**Effort**: 3 hours

Split 453-line `settings.ts` into focused stores:

```
settings/stores/
├── connectors.ts      # Connector CRUD operations
├── models.ts          # ML model management
├── google-photos.ts   # OAuth flow, picker
└── app-settings.ts    # App configuration
```

**Example** (`connectors.ts`):
```typescript
import { writable, derived } from 'svelte/store';
import { client } from '$lib/api/client';

interface ConnectorsState {
  connectors: Connector[];
  loading: boolean;
  error: string | null;
}

function createConnectorsStore() {
  const { subscribe, set, update } = writable<ConnectorsState>({
    connectors: [],
    loading: false,
    error: null
  });

  return {
    subscribe,

    async load() {
      update(s => ({ ...s, loading: true, error: null }));
      try {
        const response = await client.get<{ connectors: Connector[] }>('/connectors');
        update(s => ({ ...s, connectors: response.data.connectors, loading: false }));
      } catch (error) {
        update(s => ({ ...s, error: error.message, loading: false }));
      }
    },

    async toggle(id: string, enabled: boolean) {
      const response = await client.patch<Connector>(`/connectors/${id}`, { enabled });
      update(s => ({
        ...s,
        connectors: s.connectors.map(c =>
          c.id === id ? response.data : c
        )
      }));
      return response.data;
    }
  };
}

export const connectorsStore = createConnectorsStore();
export const googlePhotosConnectors = derived(
  connectorsStore,
  $store => $store.connectors.filter(c => c.type === 'google_photos')
);
```

---

#### 19. Add Request Caching
**File**: New `lib/api/cache.ts`
**Effort**: 2 hours

```typescript
interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

class ApiCache {
  private cache = new Map<string, CacheEntry<any>>();
  private readonly TTL = 5 * 60 * 1000; // 5 minutes

  get<T>(key: string): T | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    if (Date.now() - entry.timestamp > this.TTL) {
      this.cache.delete(key);
      return null;
    }

    return entry.data;
  }

  set<T>(key: string, data: T): void {
    this.cache.set(key, { data, timestamp: Date.now() });
  }

  invalidate(pattern: string): void {
    for (const key of this.cache.keys()) {
      if (key.includes(pattern)) {
        this.cache.delete(key);
      }
    }
  }
}

export const apiCache = new ApiCache();
```

**Use in API client**:
```typescript
async get<T>(path: string, useCache = true): Promise<ApiResponse<T>> {
  const cacheKey = `GET:${path}`;

  if (useCache) {
    const cached = apiCache.get<T>(cacheKey);
    if (cached) return { data: cached, success: true };
  }

  const response = await fetch(...);
  const data = await response.json();

  if (useCache) {
    apiCache.set(cacheKey, data);
  }

  return { data, success: true };
}
```

---

#### 20. Add Shared Type Definitions
**Files**: `lib/shared/types/`
**Effort**: 1 hour

Create shared types to eliminate duplication:

```typescript
// lib/shared/types/photo.ts
export interface Photo {
  id: string;
  filename: string;
  thumbnail_url: string | null;
  connector_id: string | null;
  connector_type: string;
  width: number | null;
  height: number | null;
  taken_at: string | null;
  processing_status: string;
  created_at: string;
}

// lib/shared/types/connector.ts
export interface Connector {
  id: string;
  type: 'google_photos' | 'local' | 'upload';
  name: string;
  enabled: boolean;
  status: 'disconnected' | 'connected' | 'syncing' | 'error';
  config: Record<string, any>;
  last_sync: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string | null;
}

// lib/shared/types/index.ts
export * from './photo';
export * from './connector';
export * from './album';
```

**Use everywhere**:
```typescript
import type { Photo, Connector } from '$shared/types';
```

---

#### 21. Implement Form Validation UI
**File**: New `lib/shared/components/FormField.svelte`
**Effort**: 2 hours

```svelte
<script lang="ts">
  export let label: string;
  export let name: string;
  export let value: string;
  export let error: string | null = null;
  export let required = false;
  export let type = 'text';
</script>

<div class="form-field">
  <label for={name}>
    {label}
    {#if required}<span class="required" aria-label="required">*</span>{/if}
  </label>

  <input
    id={name}
    {name}
    {type}
    bind:value
    aria-required={required}
    aria-invalid={!!error}
    aria-describedby={error ? `${name}-error` : undefined}
    class:error={!!error}
  />

  {#if error}
    <span id="{name}-error" class="error-message" role="alert">
      {error}
    </span>
  {/if}
</div>
```

**Use in forms**:
```svelte
<FormField
  label="Connector Name"
  name="name"
  bind:value={name}
  error={errors.name}
  required
/>
```

---

### Worker (3 items)

#### 22. Add Structured Logging to Workers
**Files**: All worker tasks
**Effort**: 2 hours

```python
import structlog

logger = structlog.get_logger()

@shared_task(bind=True, base=LoggingTask)
def process_photo(self, photo_id: str):
    logger.info(
        "photo_processing_started",
        photo_id=photo_id,
        task_id=self.request.id,
        worker=self.request.hostname
    )

    try:
        # ... processing
        logger.info(
            "photo_processing_complete",
            photo_id=photo_id,
            processing_time_ms=elapsed_ms,
            faces_detected=face_count
        )
    except Exception as e:
        logger.error(
            "photo_processing_failed",
            photo_id=photo_id,
            error=str(e),
            exc_info=True
        )
        raise
```

---

#### 23. Deploy Flower Dashboard
**File**: `docker-compose.yml`
**Effort**: 1 hour

```yaml
services:
  flower:
    image: mher/flower:2.0
    command: celery --broker=redis://redis:6379/0 flower --port=5555
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - FLOWER_BASIC_AUTH=admin:changeme
    depends_on:
      - redis
```

Access at `http://localhost:5555`

---

#### 24. Write Integration Tests for Retry Behavior
**File**: New `backend/tests/integration/workers/test_task_retries.py`
**Effort**: 3 hours

```python
import pytest
from app.adapters.inbound.workers.tasks.photo_processing import process_photo
from app.adapters.inbound.workers.exceptions import TransientError, PermanentError

class TestTaskRetryBehavior:
    def test_transient_error_triggers_retry(self, celery_worker, mocker):
        """Transient errors should retry with exponential backoff."""
        mock_clip = mocker.patch('app.infrastructure.models.clip.CLIPModelLoader')
        mock_clip.return_value.encode_image.side_effect = [
            TransientError("API rate limited"),  # First attempt
            TransientError("API rate limited"),  # Retry 1
            {"embedding": [0.1, 0.2]}           # Retry 2 - success
        ]

        result = process_photo.apply(args=[str(photo_id)])

        assert result.successful()
        assert mock_clip.call_count == 3

    def test_permanent_error_does_not_retry(self, celery_worker, mocker):
        """Permanent errors should fail immediately without retry."""
        mock_photo_repo = mocker.patch('app.adapters.outbound.persistence...')
        mock_photo_repo.find_by_id.return_value = None  # Photo doesn't exist

        result = process_photo.apply(args=["nonexistent-id"])

        assert result.failed()
        assert isinstance(result.result, PermanentError)
        # Task was only called once (no retries)
```

---

## 🟡 MEDIUM PRIORITY (Sprint 3 - Weeks 3-4)

**Estimated**: 2 weeks

### Backend TDD Features (From Original Plan)

#### 25. Frontend: Connector Detail Page
**Effort**: 2 days

Create `/frontend/src/routes/connectors/[id]/+page.svelte`:
- Display connector metadata
- Photo grid with pagination
- Bulk selection UI
- Reprocess button (individual & bulk)
- Enable/disable toggle
- Delete button with confirmation modal
- Sync status indicator

**Load function**:
```typescript
export const load: PageLoad = async ({ params }) => {
  const [connector, photos] = await Promise.all([
    client.get(`/connectors/${params.id}`),
    client.get(`/connectors/${params.id}/photos?per_page=24`)
  ]);

  return {
    connector: connector.data,
    photos: photos.data.photos,
    totalPhotos: photos.data.total
  };
};
```

---

#### 26. Frontend: Local Connector Configuration UI
**Effort**: 1 day

Add to connector detail page:
- Path editor (with validation)
- Recursive scanning toggle
- Auto-album toggle
- Watch mode toggle
- Manual sync button
- Configuration saved indicator

---

#### 27. Frontend: Connector Filters & Sorting
**Effort**: 1 day

Add to connector list page:
- Filter by type (dropdown)
- Sort by: last sync, name, status
- Search by name
- Status indicators (color-coded badges)

---

#### 28. Backend: Complete TODO Implementations
**Effort**: 2 days

Review and implement marked TODOs:
- Album management endpoints
- Settings endpoints
- Folder management
- Face merging

**OR** remove from API if not planned.

---

#### 29. Expand Test Coverage to 90%
**Effort**: 2 days

**Current**: 80% for connector APIs, unknown overall

**Add tests for**:
- Remaining connector endpoints (5 failing tests)
- Local connector API (12 failing tests)
- Service layer methods
- Edge cases and error paths
- Worker tasks

**Run coverage**:
```bash
poetry run pytest --cov=app --cov-report=html
open htmlcov/index.html
```

---

#### 30. Add Comprehensive OpenAPI Documentation
**Effort**: 1 day

Enhance all endpoints with:
- Detailed descriptions
- Request/response examples
- Error response documentation
- Authentication requirements
- Rate limit information

```python
@router.patch(
    "/{connector_id}",
    response_model=ConnectorResponse,
    summary="Update connector configuration",
    description="""
    Update a connector's configuration, including:
    - Name
    - Enabled/disabled status
    - Type-specific configuration

    All fields are optional. Only provided fields are updated.
    """,
    responses={
        200: {
            "description": "Connector updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": true,
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "name": "My Photos",
                            "enabled": true,
                            # ...
                        }
                    }
                }
            }
        },
        404: {"description": "Connector not found"},
        400: {"description": "Invalid configuration"}
    }
)
async def update_connector(...):
    ...
```

---

### Frontend Quality Improvements

#### 31. Expand Component Test Coverage
**Effort**: 2 days

**Current**: 2 component tests
**Target**: 20+ component tests

**Priority components**:
- Modal (accessibility critical)
- Button variants
- FormField
- ConnectorCard
- PhotoGrid
- SearchBar
- All settings components

---

#### 32. Add Visual Regression Tests
**Effort**: 1 day

```bash
npm install -D @playwright/test
```

```typescript
// tests/visual/components.spec.ts
import { test, expect } from '@playwright/test';

test('connector card variants', async ({ page }) => {
  await page.goto('/visual-test/connector-card');
  await expect(page).toHaveScreenshot('connector-card-enabled.png');

  await page.click('[data-testid="toggle-enabled"]');
  await expect(page).toHaveScreenshot('connector-card-disabled.png');
});
```

---

#### 33. Implement Optimistic Updates
**Effort**: 1 day

```typescript
async function handleToggleConnector(connector: Connector) {
  const previousState = connector.enabled;

  // Optimistic update
  connectorsStore.optimisticUpdate(connector.id, { enabled: !previousState });

  try {
    await connectorsStore.toggle(connector.id, !previousState);
  } catch (error) {
    // Rollback on error
    connectorsStore.optimisticUpdate(connector.id, { enabled: previousState });
    toast.error('Failed to toggle connector');
  }
}
```

---

#### 34. Break Down Large Components
**Effort**: 1 day

**ConnectorCard.svelte** (726 lines) → Split into:
- `ConnectorHeader.svelte` (status, name, type)
- `ConnectorActions.svelte` (sync, toggle, delete buttons)
- `ConnectorStats.svelte` (photo count, last sync)
- `GooglePhotosImporter.svelte` (picker UI)

---

### Worker Improvements

#### 35. Load Testing & Benchmarks (MARKED DO NOT IMPLEMENT)
**Effort**: 1 day

```python
# tests/load/test_worker_throughput.py
import pytest
from locust import User, task, between

class PhotoProcessingUser(User):
    wait_time = between(1, 3)

    @task
    def process_photo(self):
        """Simulate photo upload and processing."""
        # Queue 1000 photos
        # Measure:
        # - Time to complete all
        # - Peak memory usage
        # - Error rate
        # - Queue depth over time
```

**Target metrics**:
- 100 photos/minute throughput
- <2GB memory per worker
- <1% error rate
- Queue depth returns to 0 within 30 min

---

#### 36. Circuit Breaker for External APIs (MARKED DO NOT IMPLEMENT)
**Effort**: 1 day

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_google_photos_api(endpoint, **kwargs):
    """Call Google Photos API with circuit breaker."""
    response = await httpx.get(endpoint, **kwargs)
    if response.status_code >= 500:
        raise Exception("Server error")
    return response.json()
```

**Behavior**:
- After 5 failures → circuit opens (stop calling API)
- Wait 60 seconds
- Try 1 request (half-open state)
- If succeeds → circuit closes
- If fails → wait another 60 seconds

---

#### 37. Performance Tuning (MARKED DO NOT IMPLEMENT)
**Effort**: 1 day

**Profile tasks**:
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Task execution

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

**Optimize**:
- Database query batching
- ML model caching
- Vector store bulk inserts
- Image preprocessing pipeline

---

## 🔵 LOW PRIORITY (Backlog)

### Code Quality
- Extract magic numbers to configuration
- Improve logging consistency
- Add more specific exception types
- Document architectural decisions
- Set up pre-commit hooks for linting

### Developer Experience
- Add development troubleshooting guide
- Create architecture diagrams
- Record video walkthroughs
- Improve error messages
- Add code examples to README

### Infrastructure
- Multi-region deployment docs
- Automated dependency updates (Dependabot)
- Security scanning (Snyk, Safety)
- Performance monitoring setup
- Backup and disaster recovery plan

---

## 📊 Progress Tracking

### Sprint 1 Progress
- [ ] 1. Path traversal fix
- [ ] 2. Domain model violations
- [ ] 3. Transaction management
- [ ] 4. Repository interface fix
- [ ] 5. API response standardization
- [ ] 6. Structured logging
- [ ] 7. SvelteKit load functions
- [ ] 8. API client standardization
- [ ] 9. ARIA accessibility
- [ ] 10. Worker retry patterns
- [ ] 11. Task timeouts

### Sprint 2 Progress
- [ ] 12-24 (High priority items)

### Sprint 3 Progress
- [ ] 25-37 (Medium priority items)

---

## 📝 Notes

### Migration Fixed
✅ Fixed `connectortype` enum creation issue in migration `b9337dd07fed`
✅ All migrations now run successfully
✅ Database schema is current

### Monitoring Approach
**Decision**: Use structured logging instead of Prometheus/Grafana
- Simpler for current scale
- JSON logs easily parsable
- Can query with `jq`, ELK stack, or CloudWatch
- Easier to deploy and maintain

### Test Philosophy
- Maintain TDD for new features
- Aim for 90% coverage
- Integration tests for critical paths
- E2E tests for user journeys
- Visual regression for UI stability

---

## 🎯 Definition of Done

**For each item**:
- [ ] Implementation complete
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] Deployed to staging
- [ ] Smoke tested

**For each sprint**:
- [ ] All sprint items complete
- [ ] No critical bugs
- [ ] Performance benchmarks met
- [ ] Security review passed
- [ ] User acceptance testing complete

---

**Last Updated**: 2025-11-25
**Next Review**: Start of Sprint 2
