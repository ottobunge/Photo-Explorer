# Photo Explorer

[![Demo Video](https://img.youtube.com/vi/f4SCR1Lbo6k/0.jpg)](https://www.youtube.com/watch?v=f4SCR1Lbo6k)

AI-powered photo organization and semantic search application.

## Features

### Core Functionality
- **Semantic Photo Search**: Search photos using natural language (powered by CLIP embeddings)
- **Face Recognition & Tagging**: Automatically detect, cluster, and manage faces (merge, split, move)
- **Multi-Source Connectors**: Index photos from Google Photos, local folders, or manual uploads
  - Google Photos Picker API for selective photo import
  - Automatic sync with change detection
  - Reference-based storage (no file duplication)
- **Album Management**: Full CRUD operations for organizing photos into albums
- **AI Analysis**: Vision LLM descriptions, object detection, scene classification
- **AI Model Management**: Download and configure AI models from Hugging Face

### Production Features
- **Self-Hosted Monitoring**: Prometheus metrics + Grafana dashboards (no external dependencies)
- **Health Checks**: Comprehensive health monitoring for all services
- **Error Handling**: Standardized error responses with domain-specific exceptions
- **Rate Limiting**: Configurable per-endpoint rate limits (100 req/min default, stricter for expensive operations)
- **Transaction Safety**: ACID-compliant operations with compensating actions
- **Batch Processing**: Optimized database operations (50% fewer round-trips)
- **Query Logging**: Automatic slow query detection (>100ms threshold)
- **Resource Management**: Memory and CPU limits for all Docker services
- **Test Coverage**: 92% API coverage, 25+ automated tests (unit, integration, E2E)
- **Security**: Token encryption, path validation, production config validation

## Tech Stack

- **Backend**: Python FastAPI with hexagonal architecture
- **Frontend**: SvelteKit 5 with Svelte Runes and feature-based architecture
- **Vector DB**: Qdrant for CLIP and face embeddings
- **Database**: PostgreSQL for metadata
- **ML**: CLIP for image embeddings, InsightFace for face detection
- **Task Queue**: Celery with Redis
- **Monitoring**: Prometheus (metrics) + Grafana (dashboards) - fully self-hosted
- **Package Manager**: Poetry (Python), pnpm (Node.js)

## Quick Start

### Prerequisites

- NixOS or Nix package manager
- Docker and Docker Compose

### Fastest Way to Start Developing (Recommended) ⭐

```bash
# Enter the development shell
nix-shell

# Install dependencies (first time only)
task setup

# Start local development mode
# - Infrastructure (Postgres, Qdrant, Redis) runs in Docker
# - Backend, Frontend, Worker run locally with hot-reload
# - All logs in one terminal, color-coded
task dev:local
```

**Press Ctrl+C to stop everything**

This is the recommended mode for active development because:
- ⚡ Instant code changes (no Docker rebuild needed)
- 🔍 Easy debugging with native tools
- 📊 All logs visible in one terminal
- 💾 Low memory usage (~1-2GB)

See [DEV_WORKFLOW.md](./DEV_WORKFLOW.md) for detailed development guide.

### Alternative: Full Docker Mode

```bash
# Start all services in Docker
task docker:up

# Or in detached mode
task docker:up:detached

# Rebuild services after code changes (smart rebuild - checks base image)
task docker:rebuild

# Force rebuild base image (only when dependencies change in pyproject.toml)
task docker:rebuild:base
```

Use this for testing Docker builds or production-like environment.

**Note on rebuilds**: The `docker:rebuild` task automatically checks if the base image exists. If not found, it builds the base image first (~10-15 minutes, includes all ML dependencies), then builds the application services (~30-60 seconds). Subsequent rebuilds only rebuild the application services since the base image is cached.

### Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (interactive Swagger UI)
- **API Reference**: See [docs/API.md](./docs/API.md) for complete documentation
- **Metrics**: http://localhost:8000/metrics (Prometheus format)
- **Health Check**: http://localhost:8000/health (overall) | http://localhost:8000/health/ml (ML models)
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **Prometheus**: http://localhost:9090 (metrics database)
- **Grafana**: http://localhost:3001 (dashboards - default login: admin/admin)

### Quick Demo with Example Photos 🎬

Want to try out the app immediately with sample photos?

**Option 1: Docker Mode (Full Stack)**
```bash
nix-shell -p go-task --run "task setup:example:docker"
```
- ✨ Starts all services in Docker (backend, frontend, worker, databases)
- 📸 Downloads 50 diverse example photos to `backend/data/example-photos/`
- 🔌 Creates "Example Photos" connector pointing to `/app/data/example-photos` (mounted from host)
- 🔍 Indexes photos for semantic search
- ⚡ Takes 3-5 minutes total (including AI processing)
- Perfect for: Quick testing, demos, CI/CD

**Option 2: Local Dev Mode (Hybrid)**
```bash
# First, start local development (in a separate terminal)
task dev:local

# Then run the setup (in another terminal)
nix-shell -p go-task --run "task setup:example:local"
```
- 🚀 Uses local dev services (faster iteration, hot reload)
- 📸 Downloads 50 diverse example photos to `backend/data/example-photos/`
- 🔌 Creates connector with absolute filesystem path to data directory
- 🔍 Indexes photos via local worker
- ⚡ Takes 2-3 minutes (infrastructure already running)
- Perfect for: Active development, debugging, testing local changes

After completion, visit the frontend and try searching for:
- "cute cat" or "dog playing" (animals)
- "mountain sunset" or "ocean waves" (landscapes)
- "city skyline" or "modern building" (urban)
- "coffee cup" or "laptop computer" (objects)

The photos will be indexed and ready for semantic search, face detection, and other AI features.

## Project Structure

```
photo-explorer/
├── spec/                    # Specification documents
│   ├── 01-overview.md       # Project overview
│   ├── 02-architecture.md   # System architecture
│   ├── 03-api-specification.md
│   ├── 04-features.md       # Feature specifications
│   ├── 05-testing-strategy.md
│   ├── 06-architecture-patterns.md
│   ├── 07-connectors.md     # Connectors (Google Photos, Local)
│   └── 08-models.md         # AI Models management
├── backend/                 # FastAPI backend (hexagonal architecture)
│   ├── app/
│   │   ├── domain/          # Domain layer (entities, value objects)
│   │   ├── application/     # Application layer (use cases, ports)
│   │   ├── adapters/        # Adapters (API, repositories, ML services)
│   │   └── infrastructure/  # Infrastructure (models, config)
│   ├── tests/
│   ├── pyproject.toml       # Poetry dependencies
│   ├── shell.nix
│   └── Taskfile.yml
├── frontend/                # SvelteKit frontend (feature-based)
│   ├── src/
│   │   ├── lib/
│   │   │   ├── features/    # Feature modules (settings, search, etc.)
│   │   │   ├── api/         # API client
│   │   │   └── shared/      # Shared components
│   │   └── routes/          # SvelteKit routes
│   ├── tests/
│   ├── package.json
│   ├── shell.nix
│   └── Taskfile.yml
├── docker-compose.yml
├── shell.nix
└── Taskfile.yml
```

## Available Tasks

```bash
# Root level tasks
task dev              # Start all services in dev mode
task setup            # Install all dependencies
task test             # Run all tests
task lint             # Run linters
task docker:up        # Start with Docker

# Backend tasks (use Poetry)
task backend:dev      # Start backend server
task backend:test     # Run backend tests
task backend:lint     # Lint backend code

# Frontend tasks
task frontend:dev     # Start frontend server
task frontend:test    # Run frontend tests
task frontend:lint    # Lint frontend code

# Model management
task models:setup     # Download all recommended models
task models:search    # Search Hugging Face models
task models:list      # List downloaded models
```

## AI Models

Photo Explorer uses AI models for:

1. **CLIP Models**: Generate semantic embeddings for photos and text queries
2. **InsightFace Models**: Face detection and recognition

### Managing Models

Models can be managed via:

- **Settings UI**: Navigate to Settings > AI Models
- **Command Line**: `task models:setup`, `task models:search`
- **API**: `/api/v1/models/*` endpoints

### Default Models

| Task | Model | Size |
|------|-------|------|
| Image Embeddings | ViT-B-32 (LAION) | ~350MB |
| Face Detection | buffalo_l | ~100MB |

See `spec/08-models.md` for detailed model documentation.

## Connectors

Photo Explorer indexes photos from multiple sources without copying original files:

### Google Photos

- OAuth 2.0 authentication
- Index photos with metadata and embeddings
- On-demand image loading (no local storage)
- Automatic sync

### Local Folders

- Watch directories for changes
- Recursive folder scanning
- Auto-create albums from folder structure
- File system watcher for real-time updates

See `spec/07-connectors.md` for detailed connector documentation.

## Testing

The project follows Test-Driven Development (TDD) with behavior-focused tests.

**Backend Test Coverage**: 92% for API integration tests
**Total Tests**: 185+ tests across unit, integration, and E2E suites

### Backend Tests

```bash
cd backend
task test             # All tests
task test:unit        # Unit tests only
task test:integration # Integration tests
task test:bdd         # BDD feature tests
task test:coverage    # With coverage report
```

**Test Highlights:**
- **Connector APIs**: 45/45 tests passing (100%)
- **Search API**: 21/21 tests passing (100%)
- **Critical Fixes**: 11/11 tests passing (race conditions, locks, transactions)
- **Picker Flow**: 2/2 integration tests passing
- **Service Layer**: 20 unit tests
- **Repository Layer**: 30+ unit tests
- **Security**: Path traversal prevention tests

### Frontend Tests

```bash
cd frontend
task test             # Unit and component tests
task test:e2e         # End-to-end tests (Playwright)
task test:coverage    # With coverage report
```

**Test Highlights:**
- **Critical User Flows**: 12 Playwright E2E tests
- **Accessibility**: WCAG compliance tests
- **Responsive Design**: Mobile viewport testing

## Architecture

### Backend: Hexagonal Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Adapters Layer                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   REST API  │  │ Repositories│  │   ML Services       │ │
│  │  (FastAPI)  │  │ (PostgreSQL)│  │ (CLIP, InsightFace) │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
├─────────┼────────────────┼────────────────────┼─────────────┤
│         │        Application Layer            │             │
│         ▼                ▼                    ▼             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Use Cases / Application Services           ││
│  │         (SearchPhotos, ProcessPhoto, etc.)              ││
│  └──────────────────────┬──────────────────────────────────┘│
├─────────────────────────┼───────────────────────────────────┤
│                   Domain Layer                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │     Entities, Value Objects, Domain Services            ││
│  │        (Photo, Face, Album, Embedding)                  ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Frontend: Feature-Based Architecture

- **Features**: Self-contained modules (settings, search, albums, faces)
- **Shared**: Common components and utilities
- **API**: Centralized API client

## Development Guidelines

1. **TDD**: Write tests first, then implementation
2. **Behavior-focused tests**: Test what the system does, not how
3. **Poetry for Python**: All Python commands use `poetry run`
4. **No backwards-compatibility hacks**: Delete unused code
5. **Security**: Validate inputs, prevent path traversal

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/photo_explorer

# Vector DB
QDRANT_URL=http://localhost:6333

# Redis
REDIS_URL=redis://localhost:6379

# Models
PHOTO_EXPLORER_MODELS_DIR=~/.cache/photo-explorer/models

# Google Photos (optional)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

### Token Encryption Key Setup

Photo Explorer encrypts OAuth tokens (Google Photos, etc.) at rest using Fernet symmetric encryption. This ensures that even if someone gains access to your database or token storage, they cannot use the tokens without the encryption key.

#### Generating an Encryption Key

Generate a secure encryption key using Python:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

This will output a base64-encoded 32-byte key, for example:
```
xK8vN2QzPmR5TnJ9YXZlcnlzZWN1cmVrZXkxMjM0NTY3ODkwMTIzNDU2Nzg5MDEy
```

#### Setting the Encryption Key

Add the generated key to your `.env` file:

```bash
TOKEN_ENCRYPTION_KEY=xK8vN2QzPmR5TnJ9YXZlcnlzZWN1cmVrZXkxMjM0NTY3ODkwMTIzNDU2Nzg5MDEy
```

For production deployments, set this as an environment variable:

```bash
export TOKEN_ENCRYPTION_KEY="your-generated-key-here"
```

#### Key Rotation Procedure

If you need to rotate your encryption key (e.g., due to security breach, periodic rotation policy):

1. **Generate a new key** using the command above
2. **Back up your database** before proceeding
3. **Update all encrypted tokens** with the new key:
   ```bash
   # This is a manual process - tokens must be re-encrypted
   # If you have active Google Photos connections, users will need to re-authenticate
   ```
4. **Update the environment variable** with the new key
5. **Restart all services** (backend, worker)
6. **Users must reconnect** their Google Photos accounts

Note: Currently, key rotation requires users to re-authenticate their connectors. Future versions may support automatic re-encryption.

#### Security Best Practices

1. **Never commit keys to version control**
   - Add `.env` to `.gitignore` (already done)
   - Use `.env.example` as a template only
   - Store production keys in secure secrets management (e.g., HashiCorp Vault, AWS Secrets Manager, Docker secrets)

2. **Use different keys for different environments**
   - Development: One key (can be shared in team)
   - Staging: Different key (restricted access)
   - Production: Unique key (highest security, minimal access)

3. **Secure key storage**
   - Production: Use environment variables or secrets management
   - Never store keys in config files or code
   - Limit access to production keys to authorized personnel only

4. **Key backup**
   - Keep secure backups of production keys
   - Store backups separately from the application
   - Document key recovery procedures

5. **Monitor key usage**
   - Check application logs for encryption/decryption failures
   - Failed decryption may indicate key mismatch or tampering
   - Alert on repeated failures

### Configuration Files

```
~/.config/photo-explorer/
├── config.yaml              # Main configuration
├── connectors/
│   ├── google-photos.yaml   # Google Photos settings
│   └── local-folders.yaml   # Local folder settings
└── tokens/
    └── google-photos.enc    # OAuth tokens (encrypted)
```

## Monitoring & Observability

Photo Explorer includes a fully self-hosted monitoring stack with zero external dependencies.

### Prometheus Metrics

The backend and worker expose Prometheus metrics at `/metrics`:

**Worker Metrics:**
- `celery_task_duration_seconds` - Task execution time (histogram with p50, p95, p99)
- `celery_task_failures_total` - Task failure counter by task name and exception type
- `celery_task_success_total` - Task success counter
- `celery_task_retries_total` - Task retry counter
- `celery_active_tasks` - Currently executing tasks (gauge)

**API Metrics:**
- Request rates by endpoint
- Response times (percentiles)
- Error rates by status code

### Grafana Dashboards

Pre-configured dashboards are automatically provisioned on startup:

1. **Worker Metrics Dashboard**
   - Task duration trends
   - Failure rates by task type
   - Queue depth monitoring
   - Retry patterns

2. **API Metrics Dashboard**
   - Request rates and response times
   - Error rate tracking
   - Endpoint performance analysis

**Access Grafana**: http://localhost:3001 (default: admin/admin)

### Health Checks

All services include health monitoring:

- **Overall Health**: `GET /health` - Database, Redis, Qdrant connectivity
- **ML Models**: `GET /health/ml` - Model loading status and memory usage
- **Docker Health Checks**: All containers (postgres, redis, qdrant, backend, worker, prometheus, grafana)

### Query Performance

Slow queries (>100ms) are automatically logged with:
- Full query text and parameters
- Execution duration
- Request context (endpoint, request_id)
- Structured JSON logging for easy parsing

## Documentation

- [API Reference](./docs/API.md) - Complete API documentation with examples
- [Deployment Guide](./docs/deployment.md) - Production deployment instructions
- [Development Workflow](./DEV_WORKFLOW.md) - Local development setup
- Interactive API Docs: http://localhost:8000/docs (when running)

## License

MIT
