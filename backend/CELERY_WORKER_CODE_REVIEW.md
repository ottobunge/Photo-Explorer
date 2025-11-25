# Celery Worker Code Review - Photo Explorer Backend

**Review Date:** 2025-11-25
**Reviewer:** Code Review Agent
**Scope:** All Celery worker components, task definitions, configuration, error handling, and integration points

## Executive Summary

The Celery worker implementation demonstrates solid architectural patterns with well-structured error handling and retry logic. However, there are several critical issues that need immediate attention, particularly around resource management, idempotency, transaction boundaries, and missing batch operation task definitions.

### Overall Assessment
- **Architecture:** Good separation of concerns with custom task classes and exception hierarchy
- **Error Handling:** Strong - custom exception hierarchy with transient/permanent classification
- **Retry Logic:** Well-implemented with exponential backoff and jitter
- **Resource Management:** Needs improvement - potential memory leaks and connection issues
- **Testing:** Basic coverage present but needs expansion
- **Documentation:** Good inline documentation exists

---

## CRITICAL ISSUES (Must Fix Immediately)

### 1. Missing Batch Operations Task Definition
**File:** `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/celery_app.py`
**Lines:** 133-135

**Issue:**
```python
beat_schedule={
    "cleanup-orphaned-files": {
        "task": "app.adapters.inbound.workers.tasks.batch_operations.cleanup_orphans_task",
        "schedule": 86400.0,  # Daily
    },
},
```

The celery_app.py references a scheduled task `batch_operations.cleanup_orphans_task` but this module/task does not exist in the codebase.

**Impact:**
- Celery Beat will fail to start or log errors continuously
- Periodic cleanup won't execute
- May cause the entire worker to fail during initialization

**Recommendation:**
Either create the missing batch_operations module with the cleanup_orphans_task, or remove this schedule entry from the configuration.

---

### 2. Resource Cleanup Issues in Worker Sessions
**File:** `/home/otto/repos/personal/photo-explorer/backend/app/adapters/outbound/persistence/postgres/database.py`
**Lines:** 107-143

**Issue:**
The `get_worker_session_context` creates a new engine for every session but only disposes it in the finally block. However, ML services and vector store are initialized as singletons that persist across tasks.

**Problematic Pattern:**
```python
async def _process_photo_async(photo_id: str) -> dict:
    # Creates new singletons each time
    ml_services = get_ml_services()  # Singleton - never cleaned up
    vector_store = QdrantVectorStore()  # Singleton - connection never closed
    file_storage = LocalFileStorage()

    async with get_worker_session_context() as session:  # Creates new engine each time
        # ... work ...
```

**Impact:**
- Memory leaks from ML models being loaded multiple times
- Qdrant connections accumulating over time
- Database engine creation overhead on every task
- Potential connection pool exhaustion

**Recommendation:**
1. Initialize ML services once at worker startup in `worker_lifecycle.py`
2. Implement proper cleanup in `cleanup_worker_resources()`
3. Use dependency injection to pass services to tasks
4. Add proper connection lifecycle management for Qdrant

---

### 3. Transaction Boundary Issues in Sync Operations
**File:** `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/tasks/connector_sync.py`
**Lines:** 163-175

**Issue:**
The deleted file check rescans the entire folder, creating a second iteration that's not transaction-safe:

```python
# First scan - creates photos in DB
async for metadata in scanner.scan():
    # ... process files ...

# Second scan - checks for deletions
current_paths = set()
async for metadata in scanner.scan():  # PROBLEM: Second full scan!
    current_paths.add(metadata["source_path"])
```

**Impact:**
- Double I/O overhead scanning filesystem twice
- Race condition if files are added/deleted between scans
- Not atomic - transaction could commit partial state
- Performance degradation on large folders

**Recommendation:**
Collect paths during the first scan instead of rescanning:

```python
current_paths = set()
async for metadata in scanner.scan():
    current_paths.add(metadata["source_path"])
    # ... existing processing logic ...

# Then check for deletions using collected paths
for source_path, photo_id in known_files.items():
    if source_path not in current_paths:
        # ... handle deletion ...
```

---

### 4. Non-Idempotent Task Execution
**File:** `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/tasks/photo_processing.py`
**Lines:** 54-94

**Issue:**
Tasks are not idempotent - re-running the same task can create duplicate data or inconsistent state:

```python
def process_photo_task(self, photo_id: str) -> dict:
    # No idempotency key or completion check
    # If task is retried after partial success:
    # - Thumbnail might be regenerated (wasting resources)
    # - Embedding might be stored twice in Qdrant
    # - Photo status might be incorrect
```

**Impact:**
- Task retries after network failures can duplicate work
- Vector store may contain duplicate embeddings
- Wasted compute resources
- Inconsistent state between DB and vector store

**Recommendation:**
1. Add idempotency checks at the start of each task
2. Check photo processing status before starting work
3. Skip already-completed steps (e.g., if thumbnail exists and is recent)
4. Use task result backend to track task execution state

---

### 5. Missing Error Classification
**File:** `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/tasks/google_photos_sync.py`
**Lines:** 254-256, 308-314

**Issue:**
Generic exceptions in critical paths are not properly classified:

```python
except Exception as e:
    logger.error(f"Error indexing {metadata.external_id}: {e}")
    sync_counters["failed"] += 1
    # Continues to next item - but what if it's a transient error like network issue?
```

**Impact:**
- Transient errors (network failures) are treated as permanent failures
- No retry for recoverable errors during sync
- Sync may report failure when it could succeed with retry
- Loss of data that should have been indexed

**Recommendation:**
Classify exceptions properly:
```python
except (NetworkError, httpx.HTTPError, OSError) as e:
    # Transient - could retry this item
    logger.warning(f"Transient error indexing {metadata.external_id}: {e}")
    sync_counters["failed"] += 1
except (InvalidDataError, ValueError) as e:
    # Permanent - skip this item
    logger.error(f"Permanent error indexing {metadata.external_id}: {e}")
    sync_counters["failed"] += 1
```

---

## HIGH PRIORITY ISSUES

### 6. Unbounded Queue Growth for Face Detection
**File:** `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/tasks/connector_sync.py`
**Lines:** 113-114, 156-157

**Issue:**
During connector sync, tasks are queued for every photo without rate limiting:

```python
process_photo_task.delay(str(photo_id))
detect_faces_task.delay(str(photo_id))
# No throttling - could queue 100,000+ tasks instantly
```

**Impact:**
- Memory exhaustion in Redis/broker with large photo collections
- Worker starvation - sync tasks stuck behind processing queue
- No control over processing priority
- Potential broker crash

**Recommendation:**
1. Use Celery's `rate_limit` decorator on processing tasks
2. Implement batching - queue tasks in chunks with delays
3. Use priority queues to separate sync from processing
4. Consider implementing a work queue with bounded size

---

### 7. Hardcoded Limits and Magic Numbers
**File:** Multiple files

**Issue:**
Critical limits are hardcoded throughout the codebase:

```python
# connector_sync.py line 90
existing_photos = await photo_repo.find_by_connector(connector_uuid, limit=100000)

# google_photos_sync.py line 198
existing_photos = await photo_repo.find_by_connector(connector_uuid, limit=100000)

# photo_processing.py line 554
photos = await photo_repo.find_by_connector(connector_uuid, limit=10000)

# face_clustering.py line 70
unclustered_faces = await face_repo.find_unclustered_faces(limit=1000)
```

**Impact:**
- Connectors with more than 100,000 photos will have silent data loss
- Memory issues loading 100k records at once
- Inconsistent behavior across different operations
- Difficult to tune for different environments

**Recommendation:**
1. Move limits to configuration settings
2. Implement pagination for large datasets
3. Use streaming/cursor-based approaches for large collections
4. Add warnings when limits are approached

---

### 8. No Task Timeout Handling
**Files:** All task files

**Issue:**
While soft/hard time limits are configured globally (3600/3900 seconds), tasks don't handle `SoftTimeLimitExceeded`:

```python
# celery_app.py lines 108-109
task_soft_time_limit=3600,  # 1 hour soft limit (raises SoftTimeLimitExceeded)
task_time_limit=3900,  # 1 hour 5 minutes hard limit (kills task)
```

But no task catches `SoftTimeLimitExceeded` to save partial progress.

**Impact:**
- Long-running tasks (large folder sync, face clustering) get killed without saving progress
- Need to restart from beginning after timeout
- Wasted work
- User frustration with "stuck" syncs

**Recommendation:**
Add timeout handling to long-running tasks:
```python
from celery.exceptions import SoftTimeLimitExceeded

try:
    async for metadata in scanner.scan():
        # ... process ...
except SoftTimeLimitExceeded:
    # Save progress and re-queue continuation task
    logger.warning(f"Task timeout - processed {indexed} items")
    return {"status": "timeout", "indexed": indexed, "resume_token": last_id}
```

---

### 9. Missing Distributed Lock for Concurrent Syncs
**File:** `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/tasks/connector_sync.py`
**Lines:** 83-84, `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/tasks/google_photos_sync.py` Lines 185-186

**Issue:**
Multiple workers could sync the same connector simultaneously:

```python
# Mark as syncing
connector.set_syncing()
await connector_repo.save(connector)
# No distributed lock - another worker could start syncing the same connector
```

**Impact:**
- Duplicate photo entries in database
- Race conditions updating connector status
- Wasted resources processing the same files twice
- Data integrity issues

**Recommendation:**
Use Redis-based distributed locks:
```python
from celery.utils.log import get_task_logger
# Or use redis-py with Redis locks

@celery_app.task(bind=True)
def sync_local_folder_task(self, connector_id: str) -> dict:
    lock_key = f"sync_lock:{connector_id}"

    # Try to acquire lock with task_id as value
    if not redis_client.set(lock_key, self.request.id, nx=True, ex=3600):
        return {"status": "locked", "message": "Sync already in progress"}

    try:
        return run_async(_sync_local_folder_async(connector_id))
    finally:
        redis_client.delete(lock_key)
```

---

### 10. Token Refresh Race Conditions
**File:** `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/tasks/google_photos_sync.py`
**Lines:** 258-269

**Issue:**
Multiple concurrent tasks could refresh and save OAuth tokens simultaneously:

```python
# If tokens were refreshed, save them
if client._access_token != tokens.access_token:
    # RACE CONDITION: Multiple tasks could save tokens concurrently
    await token_storage.save_tokens(f"google_photos_{connector_id}", new_tokens)
```

**Impact:**
- Last-write-wins could save stale tokens
- Token refresh failures if multiple workers refresh simultaneously
- Authentication errors for users
- Potential data loss during sync

**Recommendation:**
1. Centralize token refresh in a dedicated task
2. Use optimistic locking for token updates
3. Implement token refresh mutex
4. Consider using a token refresh queue

---

## MEDIUM PRIORITY ISSUES

### 11. Memory-Inefficient Bulk Operations
**File:** `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/tasks/photo_processing.py`
**Lines:** 554, 558-562

**Issue:**
Loading all photos into memory before queueing:

```python
# Get all photos for this connector
photos = await photo_repo.find_by_connector(connector_uuid, limit=10000)

queued = 0
for photo in photos:  # All 10k in memory
    if photo.thumbnail_path:
        generate_embedding_from_thumbnail_task.delay(str(photo.id.value))
```

**Impact:**
- High memory usage for large connectors
- Potential OOM on resource-constrained workers
- Slow task startup

**Recommendation:**
Use streaming/pagination:
```python
offset = 0
batch_size = 100
while True:
    photos = await photo_repo.find_by_connector(
        connector_uuid, limit=batch_size, offset=offset
    )
    if not photos:
        break

    for photo in photos:
        # Queue task

    offset += batch_size
```

---

### 12. Inconsistent Error Return Types
**File:** Multiple task files

**Issue:**
Some tasks raise exceptions, others return error dicts:

```python
# photo_processing.py - raises exceptions
raise PermanentError(f"Unexpected error: {e!s}", {"photo_id": photo_id})

# photo_analysis.py line 69 - returns error dict
return {"status": "error", "message": "Photo not found"}

# face_clustering.py line 147 - returns error dict
return {"status": "error", "message": str(e)}
```

**Impact:**
- Inconsistent error handling for task callers
- Some errors won't trigger retries (dict returns)
- Difficult to distinguish transient vs permanent errors
- Poor observability

**Recommendation:**
Standardize on exception-based error handling:
- Always raise custom exceptions from task functions
- Let Celery's retry mechanism handle retries
- Return success dicts only
- Use result backend for error details

---

### 13. No Progress Tracking for Long Operations
**Files:** All sync and clustering tasks

**Issue:**
Long-running tasks provide no progress updates:

```python
# Could run for hours on large libraries
async for metadata in scanner.scan():
    # No progress updates
```

**Impact:**
- Users don't know if sync is stuck or progressing
- No visibility into task health
- Can't estimate completion time
- Difficult to debug slow operations

**Recommendation:**
Implement progress tracking:
```python
@celery_app.task(bind=True)
def sync_local_folder_task(self, connector_id: str) -> dict:
    # Update progress periodically
    for i, metadata in enumerate(scanner.scan()):
        if i % 100 == 0:
            self.update_state(
                state='PROGRESS',
                meta={'current': i, 'total': estimated_total}
            )
```

---

### 14. Face Clustering N+1 Query Problem
**File:** `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/tasks/face_clustering.py`
**Lines:** 114-128

**Issue:**
Database queries inside loops:

```python
for face_id in all_cluster_face_ids:
    face_entity = await face_repo.find_face_by_id(face_id)  # N+1 query!
    if face_entity:
        face_entity.assign_to_cluster(cluster.id.value)
        await face_repo.save_face(face_entity)  # Another query!
```

**Impact:**
- Hundreds or thousands of database queries
- Slow clustering performance
- Database connection exhaustion
- High latency

**Recommendation:**
Use bulk operations:
```python
# Fetch all faces at once
faces = await face_repo.find_faces_by_ids(all_cluster_face_ids)

# Update in memory
for face in faces:
    face.assign_to_cluster(cluster.id.value)

# Bulk save
await face_repo.bulk_save(faces)
```

---

### 15. No Circuit Breaker for External Services
**Files:** Tasks calling external APIs (Google Photos, Qdrant, ML services)

**Issue:**
No circuit breaker pattern when calling external services:

```python
# If Qdrant is down, tasks will keep failing and retrying
await vector_store.store_photo_embedding(...)
```

**Impact:**
- Cascading failures when services are down
- Resource waste retrying known-bad endpoints
- Slow failure detection
- Poor user experience

**Recommendation:**
Implement circuit breaker pattern:
```python
from pybreaker import CircuitBreaker

qdrant_breaker = CircuitBreaker(fail_max=5, timeout_duration=60)

@qdrant_breaker
async def store_embedding_safe(vector_store, *args, **kwargs):
    return await vector_store.store_photo_embedding(*args, **kwargs)
```

---

### 16. Missing Input Validation
**File:** `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/tasks/face_clustering.py`
**Lines:** 41-42

**Issue:**
similarity_threshold parameter not validated:

```python
def cluster_faces_task(self, similarity_threshold: float = 0.6) -> dict:
    # No validation - could be negative, > 1, or invalid
    return run_async(_cluster_faces_async(similarity_threshold))
```

**Impact:**
- Invalid thresholds could cause incorrect clustering
- Negative values could break vector similarity search
- No clear error message for users

**Recommendation:**
Add input validation:
```python
def cluster_faces_task(self, similarity_threshold: float = 0.6) -> dict:
    if not 0.0 <= similarity_threshold <= 1.0:
        raise InvalidDataError(
            f"similarity_threshold must be between 0 and 1, got {similarity_threshold}"
        )
    return run_async(_cluster_faces_async(similarity_threshold))
```

---

### 17. Async Event Loop Management Issues
**Files:** All task files using `run_async` helper

**Issue:**
Creating new event loop for every async task call:

```python
def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
```

**Impact:**
- Event loop creation overhead on every task
- Cannot share connection pools across tasks in same worker
- Potential resource leaks if loop.close() fails
- Performance degradation

**Recommendation:**
Consider using Celery's async task support (requires Celery 5.2+):
```python
@celery_app.task
async def process_photo_task(photo_id: str) -> dict:
    # Native async task - no event loop juggling needed
    return await _process_photo_async(photo_id)
```

Or maintain worker-level event loop in worker_lifecycle.py.

---

## LOW PRIORITY ISSUES

### 18. Hardcoded Queue Names
**File:** `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/celery_app.py`
**Lines:** 123-127

**Issue:**
Queue names are hardcoded in configuration:

```python
task_routes={
    "app.adapters.inbound.workers.tasks.photo_processing.*": {"queue": "processing"},
    "app.adapters.inbound.workers.tasks.face_clustering.*": {"queue": "clustering"},
    "app.adapters.inbound.workers.tasks.connector_sync.*": {"queue": "sync"},
},
```

**Recommendation:**
Move to environment variables or configuration file for easier deployment customization.

---

### 19. Insufficient Logging Context
**Files:** All task files

**Issue:**
Logs lack structured context for distributed tracing:

```python
logger.info(f"Detected {len(face_ids)} faces in photo {photo_id}")
# Missing: connector_id, user_id, task_id, worker_id
```

**Recommendation:**
Add structured logging with context:
```python
logger.info(
    "Detected faces in photo",
    extra={
        "photo_id": photo_id,
        "connector_id": str(connector_id),
        "face_count": len(face_ids),
        "task_id": self.request.id,
        "worker_hostname": self.request.hostname,
    }
)
```

---

### 20. Missing Metrics Collection
**Files:** All task files

**Issue:**
No metrics emitted for monitoring:

```python
# Should emit metrics like:
# - celery.task.duration
# - celery.task.success_count
# - celery.sync.photos_indexed
# - celery.ml.embedding_generation_time
```

**Recommendation:**
Add metrics collection:
```python
from prometheus_client import Counter, Histogram

task_duration = Histogram('celery_task_duration_seconds', 'Task duration', ['task_name'])
photos_indexed = Counter('photos_indexed_total', 'Photos indexed', ['connector_type'])

with task_duration.labels(task_name=self.name).time():
    # Execute task
    photos_indexed.labels(connector_type='google_photos').inc(indexed)
```

---

### 21. No Dead Letter Queue Handling
**Configuration:** Missing DLQ configuration

**Issue:**
Failed tasks after max retries have no special handling:

```python
task_max_retries=5,  # After 5 retries, task is lost
```

**Recommendation:**
Configure dead letter queue:
```python
# In celery_app.py
task_reject_on_worker_lost = True
task_acks_late = True  # Already configured

# Add DLQ routing
task_routes={
    'app.adapters.inbound.workers.tasks.*': {
        'queue': 'default',
        'routing_key': 'default',
        'exchange': 'default',
        'dead_letter_exchange': 'dlx',
        'dead_letter_routing_key': 'failed',
    }
}
```

---

### 22. Inconsistent Naming Conventions
**Files:** Task naming across modules

**Issue:**
Some tasks end with `_task`, others don't:

```python
process_photo_task  # Has _task suffix
analyze_pending_photos  # No _task suffix
schedule_google_photos_sync  # No _task suffix
```

**Recommendation:**
Standardize on either including or excluding `_task` suffix consistently.

---

### 23. Missing Type Hints for Return Values
**Files:** All async implementation functions

**Issue:**
Async implementation functions lack return type hints:

```python
async def _process_photo_async(photo_id: str):  # Missing -> dict
    ...
```

**Recommendation:**
Add return type hints for better IDE support and type checking:
```python
async def _process_photo_async(photo_id: str) -> dict[str, Any]:
    ...
```

---

### 24. Google Photos Picker - Inline Photo Fetching
**File:** `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/tasks/google_photos_sync.py`
**Lines:** 695-741

**Issue:**
Picker import task fetches and processes photos inline during sync:

```python
# Inside sync loop - blocking
image_url = f"{item.base_url}=w512-h512"
response = await http_client.get(image_url, headers=headers, timeout=30.0)
# Generate thumbnail
thumbnail_path = await file_storage.save_thumbnail(...)
# Generate embedding
embedding = await ml_services.encode_image(image_data)
```

**Impact:**
- Sync task becomes very slow (network I/O + ML processing)
- Task could timeout on large imports
- No parallelization of ML processing
- Sync task doing too much

**Recommendation:**
Queue separate processing tasks:
```python
# Save photo reference only
photo = await photo_repo.save(photo)

# Queue processing tasks for parallel execution
fetch_google_photo_bytes_task.delay(str(photo.id.value))
generate_embedding_from_thumbnail_task.delay(str(photo.id.value))
```

---

## POSITIVE OBSERVATIONS

### Strengths

1. **Well-Structured Exception Hierarchy**
   - Clear separation between transient and permanent errors
   - Specific exception types for different failure modes
   - Good foundation for retry logic

2. **Custom Task Class with Logging**
   - LoggingTask class provides excellent observability
   - Automatic logging of failures, retries, and successes
   - Structured log fields for filtering

3. **Worker Lifecycle Management**
   - Proper signal handling for graceful shutdown
   - Resource cleanup on shutdown
   - Initialization hooks

4. **Retry Configuration**
   - Exponential backoff configured
   - Jitter to prevent thundering herd
   - Reasonable retry limits

5. **Worker Session Context**
   - Separate database session management for workers
   - NullPool to avoid fork issues
   - Proper transaction management

6. **Queue Separation**
   - Different queues for different task types
   - Allows independent scaling
   - Prevents processing tasks from blocking sync

---

## RECOMMENDATIONS BY CATEGORY

### Immediate Actions (Within 1 Week)

1. **Remove or implement the missing batch_operations task** (Critical Issue #1)
2. **Fix double filesystem scan in connector sync** (Critical Issue #3)
3. **Add distributed locks to sync tasks** (High Priority Issue #9)
4. **Implement resource cleanup for ML services and vector store** (Critical Issue #2)

### Short-term Improvements (Within 1 Month)

1. Implement idempotency checks in all tasks
2. Add proper error classification in sync operations
3. Implement rate limiting for bulk task queuing
4. Add progress tracking to long-running tasks
5. Fix N+1 query issues in face clustering
6. Move hardcoded limits to configuration

### Medium-term Enhancements (1-3 Months)

1. Implement circuit breaker pattern for external services
2. Add comprehensive metrics collection
3. Implement dead letter queue handling
4. Add timeout handling with partial progress saving
5. Implement token refresh coordination
6. Add distributed tracing

### Long-term Architectural Improvements

1. Consider migrating to native async Celery tasks (Celery 5.2+)
2. Implement work queue abstraction layer
3. Add comprehensive monitoring dashboard
4. Implement automatic task retry analysis
5. Add capacity planning metrics

---

## TESTING RECOMMENDATIONS

### Missing Test Coverage

1. **Integration tests for:**
   - Long-running task timeout scenarios
   - Concurrent sync with distributed locks
   - Token refresh race conditions
   - Resource cleanup on worker shutdown

2. **Load tests for:**
   - Large connector syncs (100k+ photos)
   - Concurrent task execution
   - Memory usage under load
   - Queue depth monitoring

3. **Chaos engineering:**
   - Network failures during sync
   - Database connection loss
   - Qdrant unavailability
   - Worker crashes

---

## CONFIGURATION RECOMMENDATIONS

### Suggested Configuration Changes

```python
# Add to celery_app.py or settings

# Rate limiting
task_annotations = {
    'app.adapters.inbound.workers.tasks.photo_processing.process_photo_task': {
        'rate_limit': '100/m'  # 100 per minute
    },
    'app.adapters.inbound.workers.tasks.photo_processing.detect_faces_task': {
        'rate_limit': '50/m'  # Face detection is slower
    },
}

# Task time limits per task type
task_time_limits = {
    'app.adapters.inbound.workers.tasks.connector_sync.*': {
        'soft_time_limit': 7200,  # 2 hours for sync
        'time_limit': 7500,
    },
    'app.adapters.inbound.workers.tasks.photo_processing.*': {
        'soft_time_limit': 300,  # 5 minutes for processing
        'time_limit': 360,
    },
}

# Priority queues
task_routes = {
    # High priority - user-initiated
    'app.adapters.inbound.workers.tasks.photo_analysis.answer_question_task': {
        'queue': 'high_priority'
    },
    # Medium priority - automatic
    'app.adapters.inbound.workers.tasks.photo_processing.*': {
        'queue': 'processing'
    },
    # Low priority - background
    'app.adapters.inbound.workers.tasks.connector_sync.*': {
        'queue': 'sync'
    },
}
```

---

## MONITORING CHECKLIST

### Metrics to Track

- [ ] Task execution time (p50, p95, p99)
- [ ] Task failure rate by task type
- [ ] Queue depth by queue
- [ ] Worker memory usage
- [ ] Database connection pool utilization
- [ ] Qdrant request latency
- [ ] ML model inference time
- [ ] Photos processed per hour
- [ ] Sync duration by connector type
- [ ] Retry count distribution

### Alerts to Configure

- [ ] Task failure rate > 5%
- [ ] Queue depth > 10,000
- [ ] Worker memory > 80%
- [ ] Task duration > 2x p95
- [ ] Dead letter queue not empty
- [ ] Sync task timeout
- [ ] Database connection errors
- [ ] Qdrant connection errors

---

## CONCLUSION

The Celery worker implementation is well-architected with good separation of concerns and error handling patterns. However, there are critical issues around resource management, idempotency, and transaction safety that need immediate attention.

The most critical issues to address first:
1. Missing batch operations task definition (will break Celery Beat)
2. Resource cleanup for ML services and vector store (memory leaks)
3. Double filesystem scanning (performance and correctness)
4. Missing distributed locks (data integrity)
5. Non-idempotent tasks (correctness)

After addressing these critical issues, focus on the high-priority items around rate limiting, error classification, and proper timeout handling.

### Risk Assessment
- **Current Risk Level:** HIGH
- **Primary Risks:** Data integrity issues, memory leaks, resource exhaustion
- **Recommended Action:** Address Critical Issues #1-5 before production deployment

---

**Files Reviewed:**
- `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/celery_app.py`
- `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/worker_lifecycle.py`
- `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/exceptions.py`
- `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/tasks/__init__.py`
- `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/tasks/photo_processing.py`
- `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/tasks/photo_analysis.py`
- `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/tasks/face_clustering.py`
- `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/tasks/connector_sync.py`
- `/home/otto/repos/personal/photo-explorer/backend/app/adapters/inbound/workers/tasks/google_photos_sync.py`
- `/home/otto/repos/personal/photo-explorer/backend/app/adapters/outbound/persistence/postgres/database.py`
- `/home/otto/repos/personal/photo-explorer/backend/app/config.py`

**Total Issues Found:** 24
- Critical: 5
- High Priority: 5
- Medium Priority: 7
- Low Priority: 7
