# Testing Guide

This document describes how to run tests for the Photo Explorer application.

## Test Infrastructure

Tests that require database, Qdrant, or Redis automatically start a separate test infrastructure using non-standard ports to avoid conflicts with the main application.

### Test Ports

| Service | Main Port | Test Port |
|---------|-----------|-----------|
| PostgreSQL | 5432 | **5433** |
| Qdrant | 6333 | **6334** |
| Redis | 6379 | **6380** |

### Automatic Test Infrastructure

When you run tests, pytest automatically:
1. Starts test infrastructure (docker-compose.test.yml)
2. Waits for services to be healthy
3. Runs database migrations
4. Executes tests
5. Stops and cleans up test infrastructure

```bash
cd backend
poetry run pytest
```

### Manual Test Infrastructure Management

You can also manage test infrastructure manually:

```bash
# Start test infrastructure
./scripts/test-infra.sh up

# Run migrations
./scripts/test-infra.sh migrate

# Show status
./scripts/test-infra.sh status

# View logs
./scripts/test-infra.sh logs

# Stop test infrastructure
./scripts/test-infra.sh down

# Clean all test data
./scripts/test-infra.sh clean
```

## Running Tests

### Backend Tests

```bash
cd backend

# Run all tests (automatically starts test infrastructure)
poetry run pytest

# Run only unit tests (fast, no infrastructure needed)
poetry run pytest tests/unit/

# Run integration tests
poetry run pytest tests/integration/

# Run e2e tests
poetry run pytest tests/e2e/

# Run specific test file
poetry run pytest tests/unit/domain/test_photo.py

# Run with verbose output
poetry run pytest -v

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run in parallel (faster)
poetry run pytest -n auto
```

### Frontend Tests

```bash
cd frontend

# Run all tests
pnpm test

# Run in watch mode
pnpm test:watch

# Run with coverage
pnpm test:coverage

# Type check
pnpm run check
```

## Test Configuration

### Backend Test Environment

Test configuration is in `backend/.env.test`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/photo_explorer_test

# Qdrant
QDRANT_URL=http://localhost:6334

# Redis
CELERY_BROKER_URL=redis://localhost:6380/0

# Storage (temporary directories)
STORAGE_BASE_PATH=/tmp/photo-explorer-test/storage

# Test mode flag
TEST_MODE=true
```

### Pytest Configuration

Configuration in `backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

## Test Organization

### Backend Tests Structure

```
tests/
├── conftest.py              # Shared fixtures (auto-starts infrastructure)
├── unit/                    # Unit tests (no infrastructure)
│   ├── domain/              # Domain entity tests
│   ├── application/         # Service tests
│   └── adapters/            # Adapter tests
├── integration/             # Integration tests (needs infrastructure)
│   ├── api/                 # API endpoint tests
│   └── repositories/        # Repository tests
└── e2e/                     # End-to-end tests (full workflow)
    ├── conftest.py          # E2E specific fixtures
    └── test_*.py            # E2E test files
```

### Frontend Tests Structure

```
frontend/src/
├── lib/
│   ├── api/
│   │   └── client.test.ts   # API client tests
│   ├── components/
│   │   └── *.test.ts        # Component tests
│   └── features/
│       └── */stores/*.test.ts  # Store tests
```

## Continuous Integration

Tests run automatically in CI/CD:

1. Test infrastructure starts
2. Backend tests run
3. Frontend tests run
4. Test infrastructure cleans up

## Troubleshooting

### Port Conflicts

If you get "port already in use" errors:

```bash
# Stop test infrastructure
./scripts/test-infra.sh down

# Or stop main infrastructure
docker compose down
```

### Database Connection Errors

```bash
# Check test infrastructure status
./scripts/test-infra.sh status

# Restart test infrastructure
./scripts/test-infra.sh restart

# Check logs
./scripts/test-infra.sh logs postgres-test
```

### Migration Errors

```bash
# Run migrations manually
./scripts/test-infra.sh migrate

# Or reset test database
./scripts/test-infra.sh clean
./scripts/test-infra.sh up
./scripts/test-infra.sh migrate
```

### Qdrant Connection Errors

```bash
# Check if Qdrant is running
curl http://localhost:6334/health

# View Qdrant logs
./scripts/test-infra.sh logs qdrant-test
```

## Test Best Practices

### Writing Tests

1. **Unit tests should not require infrastructure**
   - Use mocks and fakes
   - Test business logic in isolation

2. **Integration tests can use real infrastructure**
   - Test adapter integrations
   - Test API endpoints
   - Test repository operations

3. **E2E tests should test complete workflows**
   - Test user scenarios
   - Test cross-cutting concerns
   - Use real test data

### Test Data Management

1. **Use fixtures for test data**
   - Create reusable fixtures in conftest.py
   - Use factories for complex objects

2. **Clean up after tests**
   - Tests should be independent
   - Use database transactions that rollback
   - Clean up file system changes

3. **Use meaningful test data**
   - Use descriptive names
   - Use realistic scenarios
   - Document test data setup

### Performance

1. **Run unit tests frequently** (fast, no infrastructure)
2. **Run integration tests before committing** (moderate speed)
3. **Run e2e tests before merging** (slower, comprehensive)

## Coverage Goals

- **Unit tests:** 90%+ coverage
- **Integration tests:** Cover all API endpoints
- **E2E tests:** Cover critical user workflows

## Debugging Tests

```bash
# Run with verbose output
poetry run pytest -v -s

# Run specific test with debugging
poetry run pytest tests/unit/test_foo.py::test_bar -v -s

# Run with pdb on failure
poetry run pytest --pdb

# Run last failed tests
poetry run pytest --lf

# Run only failed tests
poetry run pytest --failed-first
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Vitest Documentation](https://vitest.dev/)
- [Testing Best Practices](https://testingjavascript.com/)
