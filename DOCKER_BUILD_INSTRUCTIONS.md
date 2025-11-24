# Docker Build Instructions

This project uses a multi-stage Docker build strategy to optimize build times and image sizes.

## Architecture

### Base Image (`Dockerfile.base`)
Contains heavy, rarely-changing ML dependencies:
- NVIDIA CUDA 12.1.0 + cuDNN 8
- Python 3.12
- PyTorch 2.1.0 (with CUDA support)
- Transformers 4.37.0
- OpenCLIP 2.24.0
- ONNX Runtime 1.16.0 (GPU-enabled)
- InsightFace 0.7.3
- Pre-downloaded models (CLIP ViT-B-32, InsightFace buffalo_l)

**Size**: ~8-10 GB (includes CUDA runtime and ML libraries)

### Main Backend Image (`Dockerfile`)
Extends from base image and adds:
- Lightweight app dependencies (FastAPI, SQLAlchemy, Celery, etc.)
- Application code
- Development vs Production stages

**Size**: Base + ~500 MB (app code and lightweight dependencies)

## Build Process

### 1. Build Base Image (One-time or when ML deps change)

```bash
cd /home/otto/repos/personal/photo-explorer/backend

# Build the base image
docker build -f Dockerfile.base -t photo-explorer-base:latest .

# Optional: Tag and push to registry for team/CI use
docker tag photo-explorer-base:latest ghcr.io/ottobunge/photo-explorer-base:latest
docker push ghcr.io/ottobunge/photo-explorer-base:latest
```

**Build time**: ~15-30 minutes (downloads ~8 GB of dependencies)

**When to rebuild**:
- ML library version upgrades (PyTorch, ONNX, etc.)
- Python version change
- CUDA version change
- Initial setup

### 2. Build Main Backend Image (Frequent, fast builds)

```bash
cd /home/otto/repos/personal/photo-explorer

# Build using docker-compose (recommended)
docker-compose build backend

# Or build directly
cd backend
docker build -t photo-explorer-backend:latest .
```

**Build time**: ~2-5 minutes (only installs app dependencies)

**When to rebuild**:
- Code changes
- App dependency changes (FastAPI, Celery, etc.)
- Configuration changes

### 3. Build Worker Image

The worker also extends from the base image:

```bash
# Worker uses the same Dockerfile with different target
docker-compose build worker
```

## Using Pre-built Base Image

If you have access to a pre-built base image from a registry:

```bash
# Pull the base image
docker pull ghcr.io/ottobunge/photo-explorer-base:latest

# Tag it locally
docker tag ghcr.io/ottobunge/photo-explorer-base:latest photo-explorer-base:latest

# Now build the main image (will use cached base)
docker-compose build backend worker
```

## Development Workflow

### Quick Iteration (Code Changes Only)

```bash
# Use docker-compose for hot-reload development
docker-compose up backend

# Code changes are reflected immediately via volume mounts
# No rebuild needed for Python code changes
```

### Dependency Changes

```bash
# If you added/updated app dependencies in pyproject.toml
docker-compose build backend worker

# Then restart services
docker-compose up -d backend worker
```

### ML Dependency Changes (Rare)

```bash
# Update Dockerfile.base with new versions
# Rebuild base image
docker build -f backend/Dockerfile.base -t photo-explorer-base:latest backend/

# Rebuild dependent images
docker-compose build backend worker

# Restart everything
docker-compose up -d
```

## CI/CD Considerations

### GitHub Actions Strategy

```yaml
# .github/workflows/build.yml
jobs:
  build:
    steps:
      # Pull pre-built base image
      - name: Pull base image
        run: docker pull ghcr.io/ottobunge/photo-explorer-base:latest

      # Tag it locally
      - name: Tag base image
        run: docker tag ghcr.io/ottobunge/photo-explorer-base:latest photo-explorer-base:latest

      # Build main image (fast, uses cached base)
      - name: Build backend
        run: docker-compose build backend worker
```

### Manual Base Image Updates

Only rebuild and push base image when ML dependencies change:

```bash
# Update Dockerfile.base
# Build and push
docker build -f backend/Dockerfile.base -t ghcr.io/ottobunge/photo-explorer-base:latest backend/
docker push ghcr.io/ottobunge/photo-explorer-base:latest

# Notify team to pull new base image
```

## Troubleshooting

### Base Image Not Found

```
ERROR: failed to solve: photo-explorer-base:latest: not found
```

**Solution**: Build the base image first:
```bash
docker build -f backend/Dockerfile.base -t photo-explorer-base:latest backend/
```

### CUDA Not Available in Container

```
RuntimeError: CUDA not available
```

**Solution**: Ensure Docker has GPU access:
```bash
# Check nvidia-docker runtime is installed
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

# Update docker-compose.yml to use GPU runtime
services:
  worker:
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
```

### Out of Disk Space

Base image is large (~10 GB). Clean up old images:

```bash
# Remove dangling images
docker image prune

# Remove unused images
docker image prune -a

# Check disk usage
docker system df
```

## Performance Comparison

### Without Base Image (Old Approach)
- **Cold build**: 25-30 minutes
- **Dependency change**: 25-30 minutes (rebuilds everything)
- **Code change**: 2-5 minutes

### With Base Image (New Approach)
- **Initial base build**: 25-30 minutes (one-time)
- **Cold build**: 2-5 minutes (uses cached base)
- **Dependency change**: 2-5 minutes (only app deps)
- **Code change**: 2-5 minutes

**Result**: ~80% faster iteration time for developers

## Image Tags

### Local Development
- `photo-explorer-base:latest` - Base ML image
- `photo-explorer-backend:latest` - Backend API
- `photo-explorer-backend:dev` - Development variant

### Production Registry
- `ghcr.io/ottobunge/photo-explorer-base:latest` - Latest base
- `ghcr.io/ottobunge/photo-explorer-base:v1.0.0` - Versioned base
- `ghcr.io/ottobunge/photo-explorer-backend:latest` - Latest backend
- `ghcr.io/ottobunge/photo-explorer-backend:sha-abc123` - Git SHA tagged

## Summary

The two-stage Docker architecture provides:
- ✅ **Fast iteration** - App changes rebuild in 2-5 minutes
- ✅ **Cached dependencies** - Heavy ML libs downloaded once
- ✅ **CI/CD friendly** - Pre-built base images speed up pipelines
- ✅ **Team consistency** - Everyone uses same ML dependency versions
- ✅ **Easy updates** - Only rebuild base when ML deps change (rare)

For questions or issues, see `TESTING_AND_DEPLOYMENT_PLAN.md`.
