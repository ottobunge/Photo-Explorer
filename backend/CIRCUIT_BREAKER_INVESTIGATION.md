# Circuit Breaker Investigation Report

**Date**: 2025-11-28
**Component**: Qdrant Vector Store
**Library**: circuitbreaker v2.0.0+

---

## Current Implementation Analysis

### Location
`app/adapters/outbound/persistence/qdrant/vector_store.py`

### Decorated Methods (4 total)

1. **store_photo_embedding** (line 85-106)
   - Configuration: `@circuit(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)`
   - Purpose: Store CLIP embeddings for photos
   - Critical: Yes - photo search depends on this

2. **search_photos** (line 108-151)
   - Configuration: `@circuit(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)`
   - Purpose: Semantic search for photos
   - Critical: Yes - core search feature

3. **store_face_embedding** (line 187-208)
   - Configuration: `@circuit(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)`
   - Purpose: Store face embeddings
   - Critical: Yes - face clustering depends on this

4. **find_similar_faces** (line 252-298)
   - Configuration: `@circuit(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)`
   - Purpose: Find similar faces for clustering
   - Critical: Yes - automatic face clustering

---

## Configuration Details

```python
@circuit(
    failure_threshold=5,      # Opens after 5 consecutive failures
    recovery_timeout=60,      # Stays open for 60 seconds
    expected_exception=Exception  # Catches all exceptions
)
```

### What This Means

- **Failure Threshold**: After 5 consecutive failures, circuit opens
- **Recovery Timeout**: Circuit stays open for 60 seconds before attempting to recover
- **Expected Exception**: All exceptions trigger circuit (very broad)
- **Half-Open State**: After timeout, circuit tries one request to test if service recovered

---

## Missing Features

### 1. ❌ No Logging When Circuit Opens/Closes

**Current State**: No visibility into circuit state changes

**Impact**: Impossible to monitor circuit breaker health in production

**Recommendation**:
```python
from circuitbreaker import circuit, CircuitBreakerError

# Add custom listener
class CircuitBreakerListener:
    """Monitor circuit breaker state changes."""
    
    def on_circuit_open(self, breaker):
        logger.error(
            f"Circuit breaker opened for {breaker.name}",
            extra={
                "failure_count": breaker.failure_count,
                "threshold": breaker.failure_threshold,
                "recovery_timeout": breaker.recovery_timeout,
            }
        )
        # Send alert to monitoring system
        
    def on_circuit_close(self, breaker):
        logger.info(
            f"Circuit breaker closed for {breaker.name}",
            extra={"downtime_seconds": breaker.opened_at}
        )
        
    def on_circuit_half_open(self, breaker):
        logger.warning(
            f"Circuit breaker entering half-open state for {breaker.name}"
        )
```

---

### 2. ❌ No Fallback Behavior

**Current State**: When circuit opens, exceptions propagate up

**Impact**: Features completely break when Qdrant is down

**Scenarios**:

#### Photo Upload (store_photo_embedding)
- **Current**: Upload fails completely
- **Better**: Upload succeeds, embedding queued for later

#### Photo Search (search_photos)
- **Current**: Search returns error
- **Better**: Return cached results or graceful error message

#### Face Clustering (store_face_embedding, find_similar_faces)
- **Current**: Clustering fails completely
- **Better**: Queue for retry when Qdrant recovers

**Recommendation**:
```python
from circuitbreaker import circuit, CircuitBreakerError

@circuit(failure_threshold=5, recovery_timeout=60)
async def store_photo_embedding(
    self,
    photo_id: UUID,
    embedding: Embedding,
    payload: Optional[dict] = None,
) -> None:
    """Store with circuit breaker protection."""
    try:
        # Original implementation
        point = qdrant_models.PointStruct(...)
        await self._client.upsert(...)
        logger.debug(f"Stored embedding for photo {photo_id}")
    except CircuitBreakerError:
        # Circuit is open - Qdrant is down
        logger.warning(
            f"Circuit breaker open, queueing embedding for photo {photo_id}",
            extra={"photo_id": str(photo_id)}
        )
        # Queue for later processing
        await self._queue_embedding_for_retry(photo_id, embedding, payload)
        # Don't fail the upload - photo still saved to DB
```

---

### 3. ❌ No Metrics/Monitoring

**Current State**: No metrics exposed

**Impact**: Can't track:
- Circuit breaker state over time
- Failure rate trends
- Recovery success rate
- Impact on user experience

**Recommendation**: Add Prometheus metrics
```python
from prometheus_client import Counter, Gauge, Histogram

# Metrics
circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Current circuit breaker state (0=closed, 1=half_open, 2=open)',
    ['service', 'method']
)

circuit_breaker_failures = Counter(
    'circuit_breaker_failures_total',
    'Total number of circuit breaker failures',
    ['service', 'method']
)

circuit_breaker_opens = Counter(
    'circuit_breaker_opens_total',
    'Total number of times circuit opened',
    ['service', 'method']
)

qdrant_operation_duration = Histogram(
    'qdrant_operation_duration_seconds',
    'Qdrant operation duration',
    ['operation']
)
```

---

### 4. ❌ Methods Without Circuit Breakers

**Unprotected Methods**:
- `delete_photo_embedding` (line 153)
- `get_photo_embedding` (line 168)
- `search_faces` (line 210)
- `delete_face_embedding` (line 237)
- `get_face_embedding` (line 300)
- `store_photo_embeddings_batch` (line 319)
- `store_face_embeddings_batch` (line 341)
- `update_face_payload` (line 363)

**Impact**: Inconsistent protection - some operations fail fast, others block

**Recommendation**: Either:
1. Add circuit breakers to all methods, OR
2. Document why certain methods don't need protection

---

### 5. ❌ No Graceful Degradation Strategy

**Current State**: When Qdrant is down, application breaks

**Better Strategy**:

```python
class VectorStoreWithFallback:
    """Vector store with graceful degradation."""
    
    def __init__(self):
        self._qdrant = QdrantVectorStore()
        self._queue = EmbeddingQueue()  # Redis or database queue
        
    async def store_photo_embedding(
        self,
        photo_id: UUID,
        embedding: Embedding,
        payload: Optional[dict] = None,
    ) -> None:
        """Store embedding with fallback to queue."""
        try:
            await self._qdrant.store_photo_embedding(photo_id, embedding, payload)
        except CircuitBreakerError:
            # Qdrant is down - queue for later
            await self._queue.enqueue({
                'operation': 'store_photo_embedding',
                'photo_id': photo_id,
                'embedding': embedding.to_list(),
                'payload': payload,
                'timestamp': datetime.now(timezone.utc),
            })
            logger.info(f"Queued embedding for photo {photo_id}")
            
    async def search_photos(
        self,
        query_embedding: Embedding,
        limit: int = 20,
        **kwargs
    ) -> list[VectorSearchResult]:
        """Search with fallback to empty results."""
        try:
            return await self._qdrant.search_photos(query_embedding, limit, **kwargs)
        except CircuitBreakerError:
            logger.warning("Circuit breaker open, returning empty search results")
            # Return empty results with clear message
            # Frontend should show "Search temporarily unavailable"
            return []
```

---

## Circuit Breaker Library Behavior

### Library: circuitbreaker v2.0.0

**States**:
1. **CLOSED** (normal): All requests pass through
2. **OPEN** (broken): All requests fail immediately with `CircuitBreakerError`
3. **HALF_OPEN** (testing): One request allowed to test recovery

**State Transitions**:
```
CLOSED --[5 failures]--> OPEN --[60 seconds]--> HALF_OPEN --[success]--> CLOSED
                                                         |--[failure]--> OPEN
```

**Behavior**:
- When OPEN, raises `CircuitBreakerError` without calling the function
- When HALF_OPEN, allows one request to test service health
- If test succeeds, transitions to CLOSED
- If test fails, returns to OPEN for another 60 seconds

---

## Current Issues

### Issue 1: No Visibility
**Problem**: Can't see when circuits open/close
**Impact**: No operational awareness
**Severity**: HIGH

### Issue 2: No Fallback
**Problem**: Features completely break when Qdrant is down
**Impact**: Poor user experience
**Severity**: HIGH

### Issue 3: Inconsistent Protection
**Problem**: Only 4 of 12 methods protected
**Impact**: Unpredictable failure modes
**Severity**: MEDIUM

### Issue 4: Too Broad Exception Catching
**Problem**: `expected_exception=Exception` catches everything
**Impact**: Circuit opens for transient network issues that might self-recover
**Severity**: MEDIUM

### Issue 5: No Retry Queue
**Problem**: Failed embeddings are lost
**Impact**: Photos become unsearchable
**Severity**: HIGH

---

## Recommended Improvements

### Priority 1: Add Logging & Monitoring (4 hours)

```python
import logging
from circuitbreaker import circuit, CircuitBreakerError

logger = logging.getLogger(__name__)

def log_circuit_state(func):
    """Decorator to log circuit breaker state changes."""
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except CircuitBreakerError as e:
            logger.error(
                f"Circuit breaker open for {func.__name__}",
                extra={
                    "method": func.__name__,
                    "service": "qdrant",
                    "threshold": 5,
                    "recovery_timeout": 60,
                },
                exc_info=True
            )
            raise
    return wrapper

# Apply to all circuit-protected methods
@circuit(failure_threshold=5, recovery_timeout=60)
@log_circuit_state
async def store_photo_embedding(...):
    ...
```

---

### Priority 2: Implement Fallback Strategy (8 hours)

**Option A**: Queue-based fallback
- Failed embeddings go to Redis queue
- Background worker processes queue when Qdrant recovers
- Photo uploads succeed even when Qdrant is down

**Option B**: Graceful degradation
- Search returns empty results with clear message
- Frontend shows "Search temporarily unavailable"
- Embeddings queued for later

---

### Priority 3: Add Metrics (4 hours)

```python
from prometheus_client import Counter, Gauge

circuit_state = Gauge('qdrant_circuit_state', 'Circuit breaker state', ['method'])
circuit_failures = Counter('qdrant_circuit_failures', 'Failures', ['method'])
circuit_opens = Counter('qdrant_circuit_opens', 'Opens', ['method'])
```

---

### Priority 4: Protect All Methods (2 hours)

Add circuit breakers to remaining 8 methods, or document why they don't need protection.

---

### Priority 5: Refine Exception Handling (2 hours)

```python
from qdrant_client.http.exceptions import UnexpectedResponse, ResponseHandlingException

@circuit(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=(UnexpectedResponse, ResponseHandlingException, TimeoutError)
)
async def store_photo_embedding(...):
    # More specific exception handling
    ...
```

---

## Testing Recommendations

### Test Circuit Breaker Behavior

```python
@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_5_failures(vector_store):
    """Test circuit opens after threshold."""
    # Mock Qdrant to always fail
    with patch.object(vector_store._client, 'upsert', side_effect=Exception("Qdrant down")):
        # Trigger 5 failures
        for i in range(5):
            with pytest.raises(Exception):
                await vector_store.store_photo_embedding(uuid4(), mock_embedding)
        
        # 6th attempt should raise CircuitBreakerError (circuit is open)
        with pytest.raises(CircuitBreakerError):
            await vector_store.store_photo_embedding(uuid4(), mock_embedding)

@pytest.mark.asyncio
async def test_circuit_breaker_recovers_after_timeout(vector_store):
    """Test circuit recovers after timeout."""
    # Open circuit
    # ... (open circuit)
    
    # Wait for recovery timeout
    await asyncio.sleep(61)
    
    # Next request should be attempted (half-open state)
    # If it succeeds, circuit closes
```

---

## Monitoring Dashboard Recommendations

**Metrics to Track**:
1. Circuit breaker state per method (gauge)
2. Failure count per method (counter)
3. Time circuit has been open (gauge)
4. Queue length for failed embeddings (gauge)
5. Recovery success rate (counter)

**Alerts**:
1. Alert when circuit opens (immediate)
2. Alert when circuit open > 5 minutes (critical)
3. Alert when queue length > 1000 (warning)

---

## Production Deployment Checklist

- [ ] Add circuit breaker state logging
- [ ] Implement fallback/queue mechanism
- [ ] Add Prometheus metrics
- [ ] Set up Grafana dashboard
- [ ] Configure PagerDuty alerts
- [ ] Test circuit breaker in staging
- [ ] Document runbook for Qdrant outage
- [ ] Add health check endpoint that includes circuit state
- [ ] Load test with simulated Qdrant failures

---

## Example Runbook

### When Circuit Breaker Opens

**Detection**: Alert fires "Qdrant circuit breaker open"

**Investigation**:
1. Check Qdrant health: `curl http://qdrant:6333/health`
2. Check Grafana dashboard for circuit state
3. Check logs for error patterns

**Resolution**:
1. If Qdrant is down, restart Qdrant service
2. If network issue, investigate connectivity
3. If circuit opened due to transient spike, wait for recovery
4. Monitor queue length for backlog

**Recovery**:
1. Circuit will auto-recover after 60 seconds
2. Monitor success rate in half-open state
3. If recovering slowly, consider manual intervention
4. Process queued embeddings once stable

---

**Status**: NEEDS IMPROVEMENT
**Priority**: HIGH (production resilience critical)
**Estimated Effort**: 20 hours for full implementation
