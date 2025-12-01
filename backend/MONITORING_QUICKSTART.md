# Circuit Breaker Monitoring - Quick Start

## What Was Added

This guide covers the new comprehensive monitoring and logging infrastructure for circuit breaker implementations in Qdrant vector store operations.

## Key Components

### 1. Correlation IDs for Distributed Tracing

Enable end-to-end request tracing across services.

```python
from app.infrastructure.monitoring import (
    get_correlation_id,
    set_correlation_id,
    generate_correlation_id,
)

# Automatically set by middleware from X-Correlation-ID header
correlation_id = get_correlation_id()

# Or set manually
set_correlation_id("my-trace-123")

# Or generate a new one
set_correlation_id(generate_correlation_id())
```

### 2. Circuit Breaker State Tracking

Track detailed state transitions and metrics.

```python
from app.infrastructure.monitoring import (
    CircuitBreakerStateTracker,
    CircuitBreakerStateEnum,
)

tracker = CircuitBreakerStateTracker(
    operation_name="store_photo",
    service_name="QdrantVectorStore",
    method_name="store_photo_embedding",
)

# Record state changes
event = tracker.record_state_change(
    new_state=CircuitBreakerStateEnum.OPEN,
    error_type="ConnectionError",
    failure_count=5,
    failure_threshold=5,
)

# Get metrics
time_open = tracker.get_time_open()  # Seconds circuit has been open
recovery_attempts = tracker.recovery_attempts
```

### 3. Prometheus Metrics

Four new metrics for monitoring:

```
circuit_breaker_state           # Current state (0=closed, 1=half_open, 2=open)
circuit_breaker_failures_total  # Total failures by error type
circuit_breaker_opens_total     # Circuit breaker open events
circuit_breaker_recoveries_total # Recovery attempt events
qdrant_operation_duration_seconds # Operation latency distribution
```

### 4. Structured Logging

All events logged with full context:

```json
{
  "timestamp": "2024-01-01T12:00:00+00:00",
  "level": "ERROR",
  "message": "Circuit breaker open: QdrantVectorStore.store_photo_embedding",
  "context": {
    "operation": "store_photo",
    "service": "QdrantVectorStore",
    "method": "store_photo_embedding",
    "state": "open",
    "error_type": "ConnectionError",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "duration_seconds": 0.001
  }
}
```

## Usage Examples

### Basic Monitoring (Already in Place)

All Qdrant vector store methods are already decorated:

```python
class QdrantVectorStore(VectorStore):
    @log_circuit_breaker_events
    @monitor_circuit_breaker("store_photo")
    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)
    async def store_photo_embedding(
        self,
        photo_id: UUID,
        embedding: Embedding,
        payload: Optional[dict] = None,
    ) -> None:
        """Store a photo's CLIP embedding."""
        # Automatically monitored!
```

### Adding Monitoring to New Methods

To add monitoring to a new circuit-protected method:

```python
from app.infrastructure.monitoring import (
    log_circuit_breaker_events,
    monitor_circuit_breaker,
)
from circuitbreaker import circuit

@log_circuit_breaker_events
@monitor_circuit_breaker("your_operation")
@circuit(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)
async def your_method(self):
    """Your method description."""
    pass
```

### Querying Prometheus Metrics

```promql
# Check circuit breaker health
circuit_breaker_state{service="QdrantVectorStore"}

# Get failure rate
rate(circuit_breaker_failures_total[5m])

# P95 operation latency
histogram_quantile(0.95, qdrant_operation_duration_seconds_bucket)

# Circuit breaker availability
100 * (1 - avg by (service) (circuit_breaker_state / 2))
```

### Debugging with Correlation IDs

```bash
# Find all logs for a specific request
grep '"correlation_id": "550e8400-e29b-41d4-a716-446655440000"' logs/*.jsonl | jq .

# Timeline of events for a request
grep '"correlation_id": "550e8400-e29b-41d4-a716-446655440000"' logs/*.jsonl \
  | jq '[.timestamp, .level, .message]'
```

## Sending Requests with Correlation IDs

### REST API

```bash
curl -X POST http://api.example.com/api/photos \
  -H "X-Correlation-ID: my-trace-123" \
  -F "file=@photo.jpg"
```

### Python Client

```python
import httpx
from app.infrastructure.monitoring import generate_correlation_id

correlation_id = generate_correlation_id()

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://api.example.com/api/photos",
        headers={"X-Correlation-ID": correlation_id},
        files={"file": open("photo.jpg", "rb")},
    )
```

### Request Propagation

Middleware automatically:
1. Captures `X-Correlation-ID` header from request
2. Generates one if not provided
3. Sets it in context for all circuit breaker operations
4. Includes it in response headers

## Monitoring Key Metrics

### Circuit Breaker State Changes

Create alerts for:
- Circuit breaker open (state = 2)
- Multiple circuits open simultaneously
- Circuit flapping (opens/closes rapidly)

```yaml
alert: CircuitBreakerOpen
expr: circuit_breaker_state == 2
for: 1m
```

### Error Rates

Monitor most common failure types:

```promql
topk(5, sum by (error_type) (rate(circuit_breaker_failures_total[5m])))
```

### Operation Latency

Alert on slow operations:

```promql
histogram_quantile(0.95, qdrant_operation_duration_seconds_bucket) > 5
```

## Troubleshooting

### Circuit Breaker Won't Close

1. Check Qdrant health: `curl http://qdrant:6333/health`
2. View recent errors: `grep '"state": "open"' logs/*.jsonl | tail -20`
3. Check network: `ping qdrant` and `telnet qdrant 6333`

### Missing Correlation IDs

1. Ensure middleware is installed
2. Check request headers include `X-Correlation-ID`
3. Verify logging is at DEBUG level or above

### Metrics Not Updating

1. Check Prometheus is scraping `/metrics` endpoint
2. Verify circuit breaker is actually being triggered
3. Check logs for errors during metric recording

## Files Modified

- `app/infrastructure/monitoring/circuit_breaker.py` - Enhanced monitoring module
- `app/infrastructure/monitoring/__init__.py` - Exported new utilities
- `app/middleware.py` - Added correlation ID propagation
- `tests/unit/infrastructure/test_circuit_breaker_monitoring.py` - 23 comprehensive tests
- `MONITORING_GUIDE.md` - Full documentation
- `MONITORING_QUICKSTART.md` - This file

## Testing

Run the comprehensive test suite:

```bash
pytest tests/unit/infrastructure/test_circuit_breaker_monitoring.py -v
```

All 23 tests pass, covering:
- Correlation ID management
- Circuit breaker state transitions
- Event creation and logging
- Prometheus metric updates
- Integration scenarios

## Next Steps

1. **Deploy and Monitor**: Deploy changes and watch metrics in Prometheus
2. **Create Alerts**: Set up Prometheus alerts based on your SLOs
3. **Add Dashboard**: Create Grafana dashboard for circuit breaker health
4. **Train Team**: Educate team on using correlation IDs for debugging

## See Also

- Full documentation: `MONITORING_GUIDE.md`
- Circuit breaker implementations: `app/adapters/outbound/persistence/qdrant/vector_store.py`
- Configuration: `pyproject.toml` and `app/logging_config.py`
