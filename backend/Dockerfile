# syntax=docker/dockerfile:1

# ===================
# Base stage
# ===================
FROM python:3.12-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ===================
# Development stage
# ===================
FROM base as development

# Install development tools
RUN pip install --upgrade pip

# Copy dependency files and source code (needed for editable install)
COPY pyproject.toml ./
COPY app/ ./app/

# Install dependencies (including dev) in editable mode
RUN pip install -e ".[dev]"

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

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ===================
# Production stage
# ===================
FROM base as production

# Copy dependency files and source code
COPY pyproject.toml ./
COPY app/ ./app/

# Install production dependencies
RUN pip install .

# Copy remaining files
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY docker-entrypoint.sh /docker-entrypoint.sh

# Create non-root user
RUN useradd --create-home appuser && \
    chown -R appuser:appuser /app && \
    chmod +x /docker-entrypoint.sh
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

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
