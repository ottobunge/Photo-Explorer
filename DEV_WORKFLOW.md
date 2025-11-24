# Development Workflow Guide

This guide explains the different ways to run Photo Explorer for development.

## Quick Start

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

## Development Modes

### 1. Local Development Mode (Recommended) ⭐

**Best for:** Active development with fast iteration

```bash
task dev:local
```

**What runs where:**
- 📦 **Docker:** Postgres, Qdrant, Redis (infrastructure only)
- 💻 **Local:** Backend API, Frontend UI, ML Worker (with hot-reload)

**Advantages:**
- ⚡ Instant code changes (no Docker rebuild)
- 🔍 Easy debugging (native Python/Node debuggers work)
- 🚀 Fast startup (no image builds)
- 📊 All logs in one terminal, color-coded
- 💾 Low memory usage (~1-2GB for infra only)

**How it works:**
- Uses [Overmind](https://github.com/DarthSim/overmind) process manager
- Runs commands from `Procfile.dev`
- Backend uses Poetry virtualenv (`.venv/`)
- Frontend uses pnpm (`node_modules/`)
- All services connect to Dockerized infrastructure

**Accessing services:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Logs:**
- 🔵 **backend** - FastAPI with uvicorn hot-reload
- 🟢 **frontend** - Svelte/Vite dev server
- 🟡 **worker** - Celery background tasks

**To stop:**
- Press **Ctrl+C** once (graceful shutdown)
- Or type `q` in overmind

---

### 2. Full Docker Mode

**Best for:** Testing Docker builds, production-like environment

```bash
# Start everything in Docker
task docker:up

# Or in background
task docker:up:detached

# View logs
task docker:logs

# Stop
task docker:down
```

**What runs where:**
- 📦 **Docker:** Everything (Postgres, Qdrant, Redis, Backend, Frontend, Worker)

**Advantages:**
- 🏭 Production-like environment
- 🔒 Isolated from host system
- 🧪 Test Docker builds
- 🌍 Easy to share exact environment

**Disadvantages:**
- ⏱️ Slower iteration (needs rebuild for code changes)
- 🐛 Harder to debug
- 💾 Higher memory usage (~4-6GB)

---

### 3. Mixed Mode (Infrastructure Only)

**Best for:** Custom development setups

```bash
# Start only infrastructure
task services:up

# Then manually run services
cd backend && poetry run uvicorn app.main:app --reload
cd frontend && pnpm dev

# Stop infrastructure
task services:down
```

---

## Prerequisites

### NixOS Shell Setup

Enter the Nix shell to get all required dependencies:

```bash
nix-shell
```

This provides:
- Python 3.12 + Poetry
- Node.js 20 + pnpm
- Docker + docker-compose
- Task runner
- Overmind + tmux
- PostgreSQL client tools

### First-Time Setup

```bash
# Install dependencies
task setup

# Download AI models (optional, will download on first use)
task models:setup

# Create .env file (copy from .env.example)
cp .env.example .env

# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Add to .env as TOKEN_ENCRYPTION_KEY
```

### Environment Variables

Required in `.env`:

```bash
# Required
TOKEN_ENCRYPTION_KEY=<generate-with-command-above>

# Optional (defaults work for local dev)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=photo_explorer
```

---

## Common Tasks

### Run Tests

```bash
# All tests
task test

# Backend only
task backend:test

# Frontend only
task frontend:test

# E2E tests (requires running services)
task test:e2e

# Watch mode
task test:watch
```

### Code Quality

```bash
# Lint all code
task lint

# Format all code
task format

# Type check
task backend:typecheck
task frontend:typecheck

# Run all checks
task check
```

### Database Operations

```bash
# Run migrations
task db:migrate

# Seed with test data
task db:seed

# Reset database
task db:reset

# Create new migration (in backend dir)
cd backend
poetry run alembic revision --autogenerate -m "description"
```

### AI Models

```bash
# Check model status
task models:status

# Download all models
task models:download

# List available models
task models:list
```

---

## Troubleshooting

### Infrastructure not starting

```bash
# Check if services are healthy
./scripts/check-infra.sh

# View infrastructure logs
task services:logs

# Clean and restart
task services:clean
task services:up
```

### Backend fails to start

```bash
# Check if dependencies are installed
cd backend
poetry install

# Check if .env exists
cat .env | grep TOKEN_ENCRYPTION_KEY

# Check database connection
cd backend
poetry run python -c "from app.config import get_settings; print(get_settings())"

# Run migrations
task db:migrate
```

### Frontend fails to start

```bash
# Reinstall dependencies
cd frontend
pnpm install

# Clear cache
rm -rf node_modules/.vite
pnpm dev
```

### Worker fails to start

```bash
# Check if Redis is running
docker ps | grep redis

# Check Celery configuration
cd backend
poetry run celery -A app.infrastructure.tasks.worker inspect ping
```

### Port already in use

```bash
# Find what's using the port
lsof -i :8000  # Backend
lsof -i :5173  # Frontend
lsof -i :5432  # Postgres

# Kill the process or change port in .env
```

### Overmind not found

```bash
# Re-enter nix shell
exit
nix-shell

# Or install manually (NixOS)
nix-env -iA nixpkgs.overmind
```

---

## Advanced Usage

### Running individual services

```bash
# Backend only (after task services:up)
cd backend
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend only
cd frontend
pnpm dev

# Worker only (after task services:up)
cd backend
poetry run celery -A app.infrastructure.tasks.worker worker --loglevel=info
```

### Debugging

**Backend (Python):**
```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use debugpy for VS Code
# Install: poetry add --group dev debugpy
# Run: poetry run python -m debugpy --listen 5678 --wait-for-client -m uvicorn app.main:app --reload
```

**Frontend (JavaScript):**
```javascript
// Add debugger statement in code
debugger;

// Or use browser DevTools (Chrome/Firefox)
// Open DevTools → Sources → Set breakpoints
```

### Custom Overmind Configuration

Edit `Procfile.dev` to customize services:

```bash
# Add a new service
api: cd backend && poetry run uvicorn app.main:app --reload

# Change ports
frontend: cd frontend && pnpm dev --port 3000

# Add environment variables
worker: cd backend && CELERY_LOGLEVEL=debug poetry run celery worker
```

### Using tmux directly (without Overmind)

If you prefer tmux:

```bash
# Start infrastructure
task services:up

# Create tmux session with 3 panes
tmux new-session -s photoexplorer \; \
  send-keys 'cd backend && poetry run uvicorn app.main:app --reload' C-m \; \
  split-window -h \; \
  send-keys 'cd frontend && pnpm dev' C-m \; \
  split-window -v \; \
  send-keys 'cd backend && poetry run celery -A app.infrastructure.tasks.worker worker --loglevel=info' C-m \; \
  select-layout tiled

# Attach to session
tmux attach -t photoexplorer

# Detach: Ctrl+B then D
# Kill: Ctrl+B then :kill-session
```

---

## Performance Tips

### Local Development Mode
- **First start:** 5-10 seconds (wait for infrastructure health checks)
- **Code changes:** Instant (hot-reload)
- **Dependency changes:** 2-5 seconds (`poetry install` or `pnpm install`)
- **Memory usage:** ~1-2GB (infrastructure only in Docker)

### Full Docker Mode
- **First build:** 15-30 minutes (if building base image)
- **Subsequent builds:** 2-5 minutes (using cached base)
- **Code changes:** 30-60 seconds (Docker rebuild + restart)
- **Memory usage:** ~4-6GB (all services in Docker)

**Recommendation:** Use `dev:local` for 90% of development work. Use full Docker only when:
- Testing Docker builds
- Preparing for deployment
- Debugging Docker-specific issues
- Sharing environment with team

---

## Visual Guide

### Local Development Mode

```
┌─────────────────────────────────────────────────────────┐
│                     Your Terminal                       │
├─────────────────────────────────────────────────────────┤
│  $ task dev:local                                       │
│                                                          │
│  🚀 Starting Photo Explorer in local development mode   │
│  📦 Infrastructure running in Docker                    │
│  💻 Backend, Frontend, Worker running locally          │
│                                                          │
│  📊 View logs below (color-coded by service):          │
│     🔵 backend  - http://localhost:8000                │
│     🟢 frontend - http://localhost:5173                │
│     🟡 worker   - Background tasks                     │
│                                                          │
│  ⌨️  Press Ctrl+C to stop                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                          │
│  backend  | INFO: Uvicorn running on 0.0.0.0:8000     │
│  frontend | VITE v5.0.0 ready in 234 ms                │
│  worker   | celery@worker ready.                       │
│  backend  | INFO: Application startup complete         │
│  frontend | ➜ Local: http://localhost:5173/           │
└─────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Docker     │    │   Docker     │    │   Docker     │
│  Postgres    │    │   Qdrant     │    │    Redis     │
│  :5432       │    │   :6333      │    │   :6379      │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
┌──────▼───────┐    ┌──────▼───────┐    ┌──────▼───────┐
│    Local     │    │    Local     │    │    Local     │
│   Backend    │    │  Frontend    │    │   Worker     │
│  :8000       │    │   :5173      │    │  (Celery)    │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## Summary

- **For daily development:** `task dev:local` (fast, easy, debuggable)
- **For testing Docker:** `task docker:up` (production-like)
- **For running tests:** `task test` (includes all test types)
- **For code quality:** `task check` (lint + typecheck + test)

**Pro tip:** Keep infrastructure running between sessions:
```bash
# Start infrastructure once
task services:up

# During the day, start/stop app services as needed
task dev:local  # Start
Ctrl+C          # Stop

# At end of day
task services:down
```

This keeps the infrastructure containers warm and makes subsequent starts even faster!
