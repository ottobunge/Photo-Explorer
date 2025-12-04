# Development Guides - Consolidated Reference

**Status**: Reference Documentation
**Last Updated**: 2024-12-01

---

## Development Workflow

### Quick Start

The fastest way to start developing:

```bash
# Enter nix shell (loads all dependencies)
nix-shell

# Start infrastructure + local dev mode
task dev:local
```

This will:
1. Start infrastructure (Postgres, Qdrant, Redis) in Docker
2. Run backend, frontend, and worker locally with hot-reload
3. Show color-coded logs for all services in one terminal
4. Press **Ctrl+C** to stop everything

### Development Modes

#### 1. Local Development Mode (Recommended) ⭐

**Best for:** Active development with fast iteration

```bash
task dev:local
```

- Infrastructure in Docker (Postgres, Qdrant, Redis)
- Backend, frontend, worker run locally
- Hot-reload enabled
- All logs in one terminal

#### 2. Full Docker Mode

**Best for:** Testing production-like setup

```bash
task dev:docker
```

- Everything runs in Docker containers
- Requires rebuild for code changes
- Good for final testing

#### 3. Hybrid Mode

**Best for:** Backend development with stable frontend

```bash
# Terminal 1: Infrastructure + Frontend
task dev:hybrid

# Terminal 2: Backend development
cd backend && poetry run uvicorn app.main:app --reload

# Terminal 3: Worker development
cd backend && poetry run celery -A app.worker worker --loglevel=info
```

---

## Docker Build Instructions

### Prerequisites

- Docker 24.0+ with Buildx support
- 8GB RAM minimum
- 20GB free disk space

### Building Images

```bash
# Build all images (uses docker-compose)
task docker:build

# Build individual services
docker compose build backend
docker compose build frontend
docker compose build worker
```

### Build Arguments

The build supports several arguments:

```bash
# Production build with optimizations
docker compose build --build-arg NODE_ENV=production frontend

# Development build with debug symbols
docker compose build --build-arg PYTHON_ENV=development backend
```

### Multi-platform Builds

```bash
# Build for multiple architectures
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t photo-explorer:latest \
  -f docker/backend.dockerfile \
  backend/
```

---

## Testing Guidelines

### Backend Testing

```bash
cd backend

# Run all tests
task test

# Unit tests only
task test:unit

# Integration tests
task test:integration

# E2E tests (requires infrastructure)
task test:e2e

# With coverage
task test:coverage
```

### Frontend Testing

```bash
cd frontend

# Unit tests
npm test

# E2E tests with Playwright
npm run test:e2e

# Interactive mode
npm run test:e2e:ui
```

### Test Database

Tests use isolated database instances:
- Each test gets a fresh database
- Automatic cleanup after tests
- No interference between tests

---

## Test Dataset

A comprehensive test dataset is available in `data/test-dataset/`:

- **50 sample photos** with various characteristics
- **Metadata CSV** with photo information
- **Expected outputs** for validation

### Using Test Dataset

```python
# In tests
TEST_DATASET_PATH = Path(__file__).parent.parent / "data" / "test-dataset"

def test_with_real_photos():
    photos = list(TEST_DATASET_PATH.glob("*.jpg"))
    # Use photos for testing
```

---

## Infrastructure Management

### Starting Services

```bash
# Start all infrastructure
task infra:up

# Start specific services
docker compose up -d postgres qdrant redis

# Check status
task infra:status
```

### Database Management

```bash
# Run migrations
task db:migrate

# Create fresh database
task db:reset

# Backup database
task db:backup

# Restore from backup
task db:restore backup.sql
```

### Monitoring

- **Backend API**: http://localhost:8000/docs
- **Frontend**: http://localhost:5173
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **Redis Commander**: http://localhost:8081 (if enabled)

---

## Useful Commands

### Backend

```bash
# Format code
task backend:format

# Lint
task backend:lint

# Type checking
task backend:mypy

# Security scan
task backend:security
```

### Frontend

```bash
# Format code
task frontend:format

# Lint
task frontend:lint

# Type checking
task frontend:check

# Build for production
task frontend:build
```

### General

```bash
# Clean all generated files
task clean

# Full project setup
task setup

# Run everything
task dev:all
```

---

## Environment Variables

Key environment variables:

```bash
# Backend
DATABASE_URL=postgresql://user:pass@localhost/photo_explorer
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379

# Frontend
PUBLIC_API_URL=http://localhost:8000
PUBLIC_WS_URL=ws://localhost:8000

# ML Models (optional)
CLIP_MODEL=openai/clip-vit-base-patch32
FACE_MODEL=buffalo_l
```

---

## Troubleshooting

### Common Issues

1. **Port conflicts**: Check if ports 8000, 5173, 5432, 6333, 6379 are free
2. **Memory issues**: Increase Docker memory limit to 8GB
3. **Model download fails**: Check internet connection, models are ~2GB
4. **Database connection**: Ensure PostgreSQL is running and migrations applied
5. **Vector store**: Qdrant needs initialization on first run

### Logs

```bash
# View all logs
task logs

# Specific service
docker compose logs -f backend
docker compose logs -f worker

# Backend logs (local)
tail -f backend/logs/app.log
```

---

## Production Deployment

See `/spec/backlog/deployment-guide.md` for production deployment instructions.