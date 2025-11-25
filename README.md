# Photo Explorer

AI-powered photo organization and semantic search application.

## Features

- **Semantic Photo Search**: Search photos using natural language (powered by CLIP embeddings)
- **Face Recognition & Tagging**: Automatically detect, cluster, and manage faces (merge, split, move)
- **Multi-Source Connectors**: Index photos from Google Photos, local folders, or manual uploads
- **Album Management**: Full CRUD operations for organizing photos into albums
- **AI Analysis**: Vision LLM descriptions, object detection, scene classification
- **AI Model Management**: Download and configure AI models from Hugging Face
- **Production-Ready**: 92% test coverage, comprehensive OpenAPI docs, transaction-safe operations

## Tech Stack

- **Backend**: Python FastAPI with hexagonal architecture
- **Frontend**: SvelteKit with feature-based architecture
- **Vector DB**: Qdrant for CLIP and face embeddings
- **Database**: PostgreSQL for metadata
- **ML**: CLIP for image embeddings, InsightFace for face detection
- **Task Queue**: Celery with Redis
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

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Qdrant Dashboard: http://localhost:6333/dashboard

### Quick Demo with Example Photos 🎬

Want to try out the app immediately with sample photos?

**Option 1: Docker Mode (Full Stack)**
```bash
nix-shell -p go-task --run "task setup:example:docker"
```
- ✨ Starts all services in Docker (backend, frontend, worker, databases)
- 📸 Downloads 20 example animal photos from Unsplash
- 🔌 Creates "Example Photos" connector with Docker container path
- 🔍 Indexes photos for semantic search
- ⚡ Takes 2-3 minutes total
- Perfect for: Quick testing, demos, CI/CD

**Option 2: Local Dev Mode (Hybrid)**
```bash
# First, start local development (in a separate terminal)
task dev:local

# Then run the setup (in another terminal)
nix-shell -p go-task --run "task setup:example:local"
```
- 🚀 Uses local dev services (faster iteration, hot reload)
- 📸 Downloads 20 example animal photos
- 🔌 Creates connector with local filesystem path
- 🔍 Indexes photos via local worker
- ⚡ Takes 1-2 minutes (infrastructure already running)
- Perfect for: Active development, debugging, testing local changes

After completion, visit the frontend and try searching for:
- "cute cat"
- "dog playing"
- "raccoon"

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
**Total Tests**: 160+ tests across unit, integration, and E2E suites

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
- Connector APIs: 45/45 tests passing (100%)
- Search API: 21/21 tests passing (100%)
- Service Layer: 20 unit tests
- Repository Layer: 30+ unit tests
- Security: Path traversal prevention tests

### Frontend Tests

```bash
cd frontend
task test             # Unit and component tests
task test:e2e         # End-to-end tests (Playwright)
task test:coverage    # With coverage report
```

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

## License

MIT
