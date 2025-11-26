# Photo Explorer - Final Implementation Plan

**Created:** 2025-11-26
**Status:** Ready for Execution
**Total Tasks:** 31
**Estimated Effort:** ~29 hours

---

## 🎯 Execution Strategy

Tasks are organized by domain for parallel agent execution:
1. **Backend & Worker** - Core reliability and performance
2. **Frontend** - UI polish and consistency
3. **Architecture** - Production readiness
4. **Testing** - Quality assurance
5. **Documentation** - Production deployment guides

---

## 🔴 CRITICAL (Must Complete First)

### WK-C4: Fix Transaction Boundaries in Photo Processing
**Effort:** 1.5 hours
**File:** `backend/app/adapters/inbound/workers/tasks/photo_processing.py:154-242`

**Problem:** DB commits are mixed with vector store operations, causing data inconsistency on failures.

**Solution:**
- Separate DB commits from vector store operations
- Use try/except blocks with compensating actions
- Pattern: Save to DB → Commit → Try vector store → Rollback DB on vector failure
- Add detailed logging for failure scenarios

**Acceptance:**
- [ ] DB operations complete before vector store operations
- [ ] Vector store failures trigger DB rollback
- [ ] All error cases logged with context
- [ ] No orphaned records in either system

---

## 🟢 BACKEND & WORKER (11 tasks)

### Backend API (4 tasks)

#### BE-M1: Standardize Error Responses
**Effort:** 2 hours

**Implementation:**
- Create domain-specific exceptions in `backend/app/domain/exceptions.py`:
  - `ConnectorNotFoundError`, `TokenExpiredError`, `SyncInProgressError`, etc.
- Create exception middleware in `backend/app/middleware/exception_handler.py`
- Ensure all responses follow: `{success: bool, data?: any, error?: string}`
- Update all route handlers to use domain exceptions

**Files:**
- `backend/app/domain/exceptions.py` (new)
- `backend/app/middleware/exception_handler.py` (new)
- `backend/app/main.py` (add middleware)
- All route files in `backend/app/adapters/inbound/api/routes/`

#### BE-M2: Add ML Model Health Check
**Effort:** 45 min

**Implementation:**
- Create `/health/ml` endpoint in `backend/app/adapters/inbound/api/routes/health.py`
- Check if CLIP model loaded: `ml_services.clip_model is not None`
- Check if face detector loaded: `ml_services.face_detector is not None`
- Return model status, memory usage, and last inference time
- Add to monitoring/health check systems

#### BE-M3: Add Query Performance Logging
**Effort:** 1 hour

**Implementation:**
- Create `backend/app/middleware/query_logger.py`
- Use SQLAlchemy event listeners: `@event.listens_for(Engine, "before_cursor_execute")`
- Log queries taking >100ms with query text and parameters
- Include request context (endpoint, user, request_id)
- Use structured logging for easy parsing

#### BE-M4: Improve Path Validation
**Effort:** 30 min

**Implementation:**
- File: `backend/app/adapters/inbound/api/schemas/connector_schemas.py:116-122`
- Remove redundant Pydantic validation (duplicates service layer)
- Add docstring: "Path validation occurs in ConnectorService"
- Keep basic type validation only

### Worker Optimization (4 tasks)

#### WK-M1: Batch Face Database Operations
**Effort:** 1.5 hours

**Implementation:**
- File: `backend/app/adapters/inbound/workers/tasks/photo_processing.py:389-424`
- Create `save_faces_batch(faces: List[Face])` in `FaceRepository`
- Create `store_face_embeddings_batch(embeddings: List[tuple])` in `QdrantVectorStore`
- Update photo processing task to collect faces and batch save
- Reduces DB round-trips from N to 1 per photo

#### WK-M2: Add Rate Limiting for Google API
**Effort:** 1 hour

**Implementation:**
- File: `backend/app/adapters/inbound/workers/tasks/google_photos_sync.py`
- Use Redis-based sliding window rate limiter
- Limits: 10,000 requests/day, 50 requests/second (Google Photos limits)
- Add sleep/retry logic when rate limit hit
- Log rate limit events for monitoring

**Pattern:**
```python
async def check_rate_limit():
    redis = Redis.from_url(settings.redis_url)
    key = "google_photos:rate_limit"
    count = redis.incr(key)
    if count == 1:
        redis.expire(key, 1)  # 1 second window
    if count > 50:
        await asyncio.sleep(1)
```

#### WK-M3: Add Task Metrics Collection
**Effort:** 2 hours

**Implementation:**
- Library: `prometheus_client`
- Add to `backend/app/adapters/inbound/workers/celery_app.py`
- Metrics to track:
  - Task execution time (histogram)
  - Task failure rate (counter)
  - Queue depth (gauge)
  - Task retry count (counter)
- Expose metrics on `/metrics` endpoint
- Use `@task_prerun` and `@task_postrun` signals

#### WK-M4: Optimize Connector Sync File Scanning
**Effort:** 1 hour

**Implementation:**
- File: `backend/app/adapters/inbound/workers/tasks/connector_sync.py:163-175`
- Combine two separate directory scans into one
- Build both "files to index" and "files to delete" in single pass
- Use `os.scandir()` instead of `os.listdir()` for performance
- Reduces I/O operations by ~50%

---

## 🎨 FRONTEND (5 tasks)

### FE-M1: Add Missing Loading States
**Effort:** 1 hour

**Implementation:**
- File: `frontend/src/lib/features/settings/components/GooglePhotosSection.svelte`
- Add `connecting` state to settingsStore
- Show loading spinner before OAuth redirect
- Add error boundary for OAuth failures
- Disable "Connect" button while loading

### FE-M2: Extract to Shared Components
**Effort:** 2 hours

**Implementation:**
- Create `frontend/src/lib/shared/components/`:
  - `Card.svelte` - Reusable card container
  - `StatusBadge.svelte` - Status indicators (connected, error, syncing)
  - `ImageWithFallback.svelte` - Image with error handling
  - `EmptyState.svelte` - Empty state placeholder
- Update existing components to use shared components
- Add TypeScript types for component props

### FE-M3: Add Image Error Handling
**Effort:** 30 min

**Implementation:**
- Find all `<img>` tags in photo display components
- Add `on:error` handlers
- Show placeholder image on load failure
- Log errors for debugging
- Consider lazy loading optimization

**Pattern:**
```svelte
<img
  src={photoUrl}
  alt={photo.description}
  on:error={(e) => {
    e.currentTarget.src = '/placeholder.svg';
    console.error('Failed to load photo:', photo.id);
  }}
/>
```

### FE-M4: Create More Specific Types
**Effort:** 1 hour

**Implementation:**
- File: `frontend/src/lib/features/settings/types.ts`
- Create discriminated union for ConnectorConfig:
```typescript
type ConnectorConfig =
  | { type: 'google_photos'; client_id: string; scopes: string[] }
  | { type: 'local'; paths: string[]; recursive: boolean }
  | { type: 'upload' }
```
- Remove all `Record<string, unknown>` usage
- Add type guards for config validation

### FE-M5: Extract Constants
**Effort:** 30 min

**Implementation:**
- Create `frontend/src/lib/constants.ts`
- Extract magic numbers:
  - Timeout durations (2000ms polling, etc.)
  - Polling intervals
  - Retry attempts
  - Image sizes
- Export as named constants with documentation
- Update all files to import constants

---

## 🏗️ ARCHITECTURE (3 tasks)

### ARCH-M1: Add Observability
**Effort:** 3 hours

**Requirement:** Completely self-hosted via Docker - no paid external dependencies

**Implementation:**

1. **Add Prometheus to `docker-compose.yml`:**
```yaml
prometheus:
  image: prom/prometheus:latest
  container_name: photo-explorer-prometheus
  volumes:
    - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    - prometheus_data:/prometheus
  ports:
    - "9090:9090"
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    - '--storage.tsdb.path=/prometheus'
  networks:
    - photo-explorer
```

2. **Add Grafana to `docker-compose.yml`:**
```yaml
grafana:
  image: grafana/grafana:latest
  container_name: photo-explorer-grafana
  volumes:
    - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
    - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    - grafana_data:/var/lib/grafana
  ports:
    - "3001:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
    - GF_USERS_ALLOW_SIGN_UP=false
  networks:
    - photo-explorer
```

3. **Create `monitoring/prometheus.yml`:**
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:8000']

  - job_name: 'worker'
    static_configs:
      - targets: ['worker:8000']
```

4. **Add prometheus_client to backend/workers:**
- Install: `poetry add prometheus-client`
- Expose `/metrics` endpoint
- Track: request duration, error rates, queue depth

5. **Create Grafana dashboards** (JSON configs in `monitoring/grafana/dashboards/`)

### ARCH-M2: Add Health Checks to Docker Services
**Effort:** 1 hour

**Implementation:**
- File: `docker-compose.yml`
- Add healthcheck to all services:
```yaml
backend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
  deploy:
    resources:
      limits:
        memory: 2G
        cpus: '2'
```
- Services: backend, worker, postgres, redis, qdrant, prometheus, grafana
- Set appropriate resource limits based on workload

### ARCH-M3: Create Production Environment Config
**Effort:** 45 min

**Implementation:**
- Create `.env.production.example` with all required variables
- Separate required vs optional variables
- Add validation in `backend/app/config.py`:
```python
@field_validator('encryption_key')
def validate_encryption_key_in_production(cls, v):
    if settings.environment == 'production' and not v:
        raise ValueError("ENCRYPTION_KEY required in production")
    return v
```
- Document in README

---

## 📝 TESTING (3 tasks)

### TEST-1: Add Tests for Critical Fixes
**Effort:** 2 hours

**Implementation:**
- File: `backend/tests/test_critical_fixes.py`
- Test token storage race conditions (concurrent access)
- Test face clustering lock behavior (multiple workers)
- Test transaction boundary handling (WK-C4 fix)
- Use pytest-asyncio and pytest-mock

### TEST-2: Add Picker Flow Integration Tests
**Effort:** 1.5 hours

**Implementation:**
- File: `backend/tests/integration/test_picker_flow.py`
- Mock Google Photos Picker API
- Test full picker workflow end-to-end
- Test session expiration handling
- Test error recovery (network failures, invalid sessions)

### TEST-3: Add Component Tests
**Effort:** 2 hours

**Implementation:**
- Use Playwright for frontend testing
- Test critical user flows:
  - Connect Google Photos
  - Browse photos
  - Search functionality
  - Face clustering
- Test error states and edge cases
- Test accessibility (a11y)

---

## 📚 DOCUMENTATION (3 tasks)

### DOC-1: Document Token Encryption Key Setup
**Effort:** 30 min

**Implementation:**
- Update README with token encryption section
- Add key generation instructions:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
- Document rotation procedure
- Security best practices

### DOC-2: Document Production Deployment
**Effort:** 1 hour

**Implementation:**
- Create `docs/deployment.md`
- Sections:
  - Prerequisites (Docker, Docker Compose)
  - Environment setup
  - Initial configuration
  - Running the stack
  - Monitoring (Prometheus/Grafana)
  - Backup procedures
  - Troubleshooting common issues

### DOC-3: Update API Documentation
**Effort:** 30 min

**Implementation:**
- Document new `/health/ml` endpoint
- Document rate limits on all endpoints
- Update error response format documentation
- Add OpenAPI/Swagger annotations if missing

---

## 📊 Progress Tracking

Agents should update this section as tasks are completed:

### Critical
- [ ] WK-C4: Transaction Boundaries

### Backend & Worker
- [x] BE-M1: Standardize Error Responses
- [x] BE-M2: ML Model Health Check
- [x] BE-M3: Query Performance Logging
- [x] BE-M4: Improve Path Validation
- [ ] WK-M1: Batch Face Operations
- [ ] WK-M2: Google API Rate Limiting
- [ ] WK-M3: Task Metrics Collection
- [ ] WK-M4: Optimize File Scanning

### Frontend
- [ ] FE-M1: Missing Loading States
- [ ] FE-M2: Shared Components
- [ ] FE-M3: Image Error Handling
- [ ] FE-M4: Specific Types
- [ ] FE-M5: Extract Constants

### Architecture
- [ ] ARCH-M1: Observability (self-hosted Prometheus + Grafana)
- [ ] ARCH-M2: Docker Health Checks
- [ ] ARCH-M3: Production Config

### Testing
- [ ] TEST-1: Critical Fixes Tests
- [ ] TEST-2: Picker Flow Tests
- [ ] TEST-3: Component Tests

### Documentation
- [ ] DOC-1: Token Encryption Key
- [ ] DOC-2: Production Deployment
- [ ] DOC-3: API Documentation

---

## 🚀 Agent Execution Plan

### Phase 1: Critical (Sequential)
1. Agent: Fix transaction boundaries (WK-C4)

### Phase 2: Core Features (Parallel)
1. **Backend Agent**: BE-M1, BE-M2, BE-M3, BE-M4
2. **Worker Agent**: WK-M1, WK-M2, WK-M3, WK-M4
3. **Frontend Agent**: FE-M1, FE-M2, FE-M3, FE-M4, FE-M5

### Phase 3: Infrastructure (Parallel)
1. **Architecture Agent**: ARCH-M1, ARCH-M2, ARCH-M3

### Phase 4: Quality (Parallel)
1. **Testing Agent**: TEST-1, TEST-2, TEST-3
2. **Documentation Agent**: DOC-1, DOC-2, DOC-3

---

## ✅ Success Criteria

- [ ] All 31 tasks completed
- [ ] All tests passing
- [ ] No linting errors
- [ ] Documentation complete
- [ ] Production-ready deployment guide
- [ ] Self-hosted monitoring operational
- [ ] Zero external service dependencies
