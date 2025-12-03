# Backend Enhancements - Future Work

**Status**: Backlog (not required for production)
**Priority**: Medium
**Estimated Effort**: 31 hours

---

## Overview

These are quality-of-life improvements and optimizations that can be added after production launch. The system is fully functional without these enhancements.

---

## Enhancement Items

### M1: Circuit Breaker Metrics Dashboard
**Effort**: 6 hours
**Value**: Visual monitoring of circuit breaker states

- Create Grafana dashboard
- Circuit state over time graphs
- Failure rate trends
- Queue length visualization
- Recovery success rate metrics

---

### M2: Fix Time-Based Test Dependencies
**Effort**: 2 hours
**Value**: More reliable tests

Replace `time.sleep()` with controlled time injection using `freezegun`:
```python
@pytest.fixture
def mock_now():
    with freeze_time("2025-01-15 12:00:00") as frozen:
        yield frozen
```

---

### M3: Centralize Test Fixtures
**Effort**: 1 hour
**Value**: DRY test code

- Move `sample_image_bytes` fixture to root conftest.py
- Remove duplicates across test files
- Create shared test data factory

---

### M4: Integration Tests for Over-Mocked Units
**Effort**: 4 hours
**Value**: Better test coverage

- Add real filesystem tests for ConnectorService
- Complement existing unit tests with integration tests
- Test actual file operations

---

### M5: Negative Test Coverage
**Effort**: 4 hours
**Value**: Better error handling validation

Add tests for error scenarios:
- Database connection failures
- Qdrant unavailability (already partially covered)
- Storage service outages
- ML model failures
- Partial batch failures

---

### M6: Centralize Repository Mappers
**Effort**: 3 hours
**Value**: Cleaner code, less duplication

- Create central mapper utilities
- Entity ↔ Model conversion helpers
- Reduce boilerplate in repositories

---

### M7: Async Task Monitoring
**Effort**: 4 hours
**Value**: Better visibility into background jobs

- Celery task success/failure rates
- Queue depth monitoring
- Task duration metrics
- Dead letter queue monitoring

---

### M8: Performance Benchmarks
**Effort**: 4 hours
**Value**: Performance regression prevention

- Document baseline performance metrics
- Create benchmark test suite
- API response time benchmarks
- Database query performance tests
- Vector search performance tests

---

### M9: Resource Pool Management
**Effort**: 3 hours
**Value**: Better resource utilization

- PostgreSQL connection pooling optimization
- Qdrant connection management
- Redis connection pooling
- Memory usage optimization

---

### API Rate Limiting
**Effort**: 8-10 hours
**Value**: Protection against abuse

**Implementation Strategy**: Token bucket algorithm with Redis

```python
RATE_LIMITS = {
    "search": "10/second, 100/minute",
    "upload": "5/second, 50/minute",
    "read": "100/second, 1000/minute",
    "write": "20/second, 200/minute",
}
```

Components:
- Redis token buckets per user/IP
- FastAPI middleware
- Rate limit headers in responses
- Optional request queuing

---

## Implementation Notes

All these enhancements can be added without breaking changes:
- No API changes required
- No database schema changes
- Configuration backward compatible
- Can be deployed independently

---

## Priority Order (if implementing)

1. **M1**: Metrics Dashboard - Most valuable for operations
2. **API Rate Limiting** - Important for public-facing APIs
3. **M7**: Async Task Monitoring - Good for debugging
4. **M8**: Performance Benchmarks - Prevents regressions
5. **M5**: Negative Test Coverage - Improves reliability
6. Others as time permits

---

## Decision

These items are **deferred** because:
- System is fully functional without them
- Can be added incrementally post-production
- No security or stability risks without them
- Resources better spent on frontend/features

They remain documented here for future sprints when optimization becomes a priority.