# Circuit Breaker Quick Reference

## All Protected Methods (15 total)

### Photo Embeddings (4)
| Method | Return Type | Fallback Behavior |
|--------|-------------|-------------------|
| `store_photo_embedding(photo_id, embedding, payload)` | `None` | Raises exception (caller handles) |
| `search_photos(query, limit, filters, threshold)` | `list[VectorSearchResult]` | Returns `[]` |
| `delete_photo_embedding(photo_id)` | `bool` | Returns `False` |
| `get_photo_embedding(photo_id)` | `Optional[Embedding]` | Returns `None` |

### Face Embeddings (4)
| Method | Return Type | Fallback Behavior |
|--------|-------------|-------------------|
| `store_face_embedding(face_id, embedding, payload)` | `None` | Raises exception (caller handles) |
| `search_faces(query, limit, filters)` | `list[VectorSearchResult]` | Returns `[]` |
| `delete_face_embedding(face_id)` | `bool` | Returns `False` |
| `get_face_embedding(face_id)` | `Optional[Embedding]` | Returns `None` |

### Face Clustering (1)
| Method | Return Type | Fallback Behavior |
|--------|-------------|-------------------|
| `find_similar_faces(face_id, threshold, limit)` | `list[VectorSearchResult]` | Returns `[]` |

### Batch Operations (3)
| Method | Return Type | Fallback Behavior |
|--------|-------------|-------------------|
| `store_photo_embeddings_batch(embeddings)` | `None` | Raises exception (caller handles) |
| `store_face_embeddings_batch(embeddings)` | `None` | Raises exception (caller handles) |
| `update_face_payloads_batch(updates)` | `None` | Raises exception (caller handles) |

### Payload Updates (1)
| Method | Return Type | Fallback Behavior |
|--------|-------------|-------------------|
| `update_face_payload(face_id, payload)` | `None` | Raises exception (caller handles) |

### Monitoring (2)
| Method | Return Type | Fallback Behavior |
|--------|-------------|-------------------|
| `get_collection_info(collection_name)` | `dict` | Raises exception |
| `health_check()` | `bool` | Returns `False` |

## Circuit Configuration

```python
QDRANT_CIRCUIT_EXCEPTIONS = (
    UnexpectedResponse,      # Qdrant HTTP errors
    ResponseHandlingException,  # Response parsing failures
    TimeoutError,            # Request timeout
    ConnectionError,         # Network connection failure
    OSError,                 # System network errors
)

@circuit(
    failure_threshold=5,     # Opens after 5 consecutive failures
    recovery_timeout=60,     # Stays open for 60 seconds
    expected_exception=QDRANT_CIRCUIT_EXCEPTIONS,
)
```

## Understanding Fallback Behavior

### Read Operations (get, search, retrieve)
When circuit is open, these methods return safe defaults:
- **Search methods**: Return empty `[]` instead of failing
- **Get methods**: Return `None` instead of failing
- **Advantage**: Frontend can show "no results" or "temporarily unavailable"

### Write Operations (store, delete, update)
When circuit is open, these methods raise `CircuitBreakerError`:
- **Database stays consistent**: Data never lost
- **Async queue not implemented yet**: Future enhancement
- **Caller must handle**: Service layer can log and retry

### Monitoring Methods
- **health_check()**: Returns `False` (circuit open = unavailable)
- **get_collection_info()**: Raises exception (diagnostic only)

## When Does Circuit Open?

Circuit opens after **5 consecutive failures** from Qdrant for these exceptions:
- Network timeouts
- Connection refused
- HTTP 5xx errors from Qdrant
- Invalid responses from Qdrant

**Does NOT open for**:
- Invalid input (ValueError)
- Schema validation errors
- Not found responses (handled as normal case)
- Client-side errors (4xx)

## How to Monitor Circuit Health

### Using Prometheus Metrics

```python
# Check current circuit state (0=closed, 1=half_open, 2=open)
circuit_breaker_state{service="QdrantVectorStore", method="search_photos"}

# Count of total failures
circuit_breaker_failures_total{service="QdrantVectorStore", method="search_photos", error_type="TimeoutError"}

# Count of circuit opens
circuit_breaker_opens_total{service="QdrantVectorStore", method="search_photos"}

# Operation duration in seconds
qdrant_operation_duration_seconds_bucket{operation="search_photos"}
```

### Using Health Check

```python
# Endpoint: GET /api/health/qdrant
async def check_qdrant_health(vector_store: VectorStore):
    is_healthy = await vector_store.health_check()
    # Returns True if Qdrant is accessible
    # Returns False if circuit is open or Qdrant is unreachable
```

### Using Logs

Circuit breaker events are logged at ERROR level when:
- Circuit opens (5 failures reached)
- Circuit half-open (testing recovery)
- Requests fail with CircuitBreakerError

Search logs for: `Circuit breaker open` or `CircuitBreakerError`

## Recovery Timeline

```
Time 0s:   Request 1 fails → failure_count=1
Time 1s:   Request 2 fails → failure_count=2
Time 2s:   Request 3 fails → failure_count=3
Time 3s:   Request 4 fails → failure_count=4
Time 4s:   Request 5 fails → failure_count=5 → CIRCUIT OPENS
Time 5s-59s: All requests fail immediately with CircuitBreakerError (no Qdrant calls)
Time 60s:  Circuit transitions to HALF_OPEN, test request allowed
Time 61s:  If test succeeds → CLOSED (normal operation resumes)
           If test fails → OPEN (wait another 60 seconds)
```

## Common Patterns in Application Code

### Handling Read Operation Fallback

```python
# search_photos returns [] when circuit is open
results = await vector_store.search_photos(query_embedding)
if not results:
    # Could be "no results found" or "Qdrant temporarily unavailable"
    return {"results": [], "message": "Search temporarily unavailable"}
```

### Handling Write Operation Fallback

```python
# store_photo_embedding raises CircuitBreakerError when circuit is open
try:
    await vector_store.store_photo_embedding(photo_id, embedding)
except CircuitBreakerError:
    # Qdrant is down, but photo was already saved to database
    # Consider implementing a retry queue here
    logger.warning(f"Failed to store embedding for {photo_id}, will retry later")
```

### Checking Qdrant Health

```python
# health_check returns False when circuit is open
is_healthy = await vector_store.health_check()
if not is_healthy:
    # Qdrant is unavailable
    # Disable search UI, show "Search temporarily unavailable"
    return {"qdrant_available": False}
```

## Tuning the Circuit Breaker

### If circuit opens too often (too sensitive)
Increase the failure threshold:
```python
@circuit(failure_threshold=10, recovery_timeout=60)  # Open after 10 failures instead of 5
```

### If circuit is slow to open (too lenient)
Decrease the failure threshold:
```python
@circuit(failure_threshold=3, recovery_timeout=60)   # Open after 3 failures instead of 5
```

### If circuit recovers too fast
Increase the recovery timeout:
```python
@circuit(failure_threshold=5, recovery_timeout=120)  # Wait 2 minutes before retry
```

### If circuit recovers too slowly
Decrease the recovery timeout:
```python
@circuit(failure_threshold=5, recovery_timeout=30)   # Retry after 30 seconds
```

## Troubleshooting

### Circuit is stuck OPEN
**Cause**: Qdrant is still unavailable after recovery timeout
**Fix**: Check Qdrant service health:
```bash
curl http://qdrant:6333/health
docker ps | grep qdrant
```

### Circuit opens too frequently
**Cause**: Network issues, timeouts, or Qdrant overloaded
**Fix**:
- Check network connectivity between app and Qdrant
- Verify Qdrant resource limits (memory, CPU)
- Increase failure threshold (less sensitive)
- Increase recovery timeout (longer recovery period)

### Search returns empty results instead of error
**Cause**: This is expected fallback behavior when circuit is open
**Fix**: Check Qdrant health, it should recover automatically after 60 seconds

### Circuit breaker has no effect
**Cause**: Exception type not in QDRANT_CIRCUIT_EXCEPTIONS
**Fix**: Add exception to the tuple:
```python
QDRANT_CIRCUIT_EXCEPTIONS = (
    UnexpectedResponse,
    ResponseHandlingException,
    TimeoutError,
    ConnectionError,
    OSError,
    MyNewQdrantError,  # Add here
)
```

## Related Files

- Implementation: `/backend/app/adapters/outbound/persistence/qdrant/vector_store.py`
- Monitoring: `/backend/app/infrastructure/monitoring/circuit_breaker.py`
- Test example: `/backend/tests/unit/infrastructure/test_circuit_breaker_monitoring.py`
- Full details: `/backend/CIRCUIT_BREAKER_IMPROVEMENTS.md`
