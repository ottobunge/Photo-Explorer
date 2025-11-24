# syntax=docker/dockerfile:1
# ===================================================================================
# Main Backend Dockerfile - Extends from Dockerfile.base
# ===================================================================================
#
# This Dockerfile extends photo-explorer-base:latest which contains:
# - NVIDIA CUDA 12.1 + cuDNN 8
# - Python 3.12 + Poetry 1.7.1
# - ALL dependencies from pyproject.toml pre-installed (heavy + lightweight)
# - Pre-downloaded models (CLIP ViT-B-32, InsightFace buffalo_l)
#
# Since all dependencies are in the base image, `poetry install` will be instant.
# This Dockerfile only copies application code and configures the runtime.
#
# To build the base image first:
#   docker build -f Dockerfile.base -t photo-explorer-base:latest .
# ===================================================================================

# ===================
# Base stage
# ===================
FROM photo-explorer-base:latest as base

# Base image already has everything:
# - Python 3.12
# - Poetry 1.7.1
# - All dependencies from pyproject.toml installed globally
# - System dependencies (PostgreSQL client, CUDA, build tools, etc.)
# - Environment variables configured

WORKDIR /app

# ===================
# Development stage
# ===================
FROM base as development

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Copy source code (needed for editable install)
COPY app/ ./app/

# Install app in editable mode (this will be nearly instant since deps are already installed)
# Poetry will just create the editable link to the app package
RUN poetry install --no-root && poetry install

# Copy remaining files (tests, alembic, etc.)
COPY . .

# Create storage directory
RUN mkdir -p /app/storage

# Copy and set up entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Entrypoint runs migrations before main command
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command with hot-reload for development
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ===================
# Production stage
# ===================
FROM base as production

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Copy source code
COPY app/ ./app/

# Install app (instant since deps are already in base)
RUN poetry install --no-root --only main && poetry install --only main

# Copy remaining files
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Create non-root user
RUN useradd --create-home appuser && \
    chown -R appuser:appuser /app

USER appuser

# Create storage directory
RUN mkdir -p /app/storage

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')"

# Entrypoint runs migrations before main command
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command for production
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
