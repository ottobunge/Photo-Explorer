# Production Deployment Guide

This guide covers deploying Photo Explorer to production using Docker Compose.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Environment Configuration](#environment-configuration)
- [Starting the Services](#starting-the-services)
- [Monitoring](#monitoring)
- [Backup Procedures](#backup-procedures)
- [Upgrading and Updating](#upgrading-and-updating)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

**Minimum:**
- 4 CPU cores
- 8 GB RAM
- 50 GB available disk space
- Ubuntu 20.04 LTS or later (or equivalent Linux distribution)

**Recommended:**
- 8 CPU cores
- 16 GB RAM
- 100+ GB SSD storage
- NVIDIA GPU with 6GB+ VRAM (for ML model inference)

### Required Software

1. **Docker** (version 20.10 or later)
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh

   # Add your user to docker group
   sudo usermod -aG docker $USER

   # Log out and back in for group changes to take effect
   ```

2. **Docker Compose** (version 2.0 or later)
   ```bash
   # Verify installation
   docker compose version
   ```

3. **Git** (for cloning the repository)
   ```bash
   sudo apt-get update
   sudo apt-get install -y git
   ```

### Optional: GPU Support

If using NVIDIA GPU for ML inference:

```bash
# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

## Initial Setup

### 1. Clone the Repository

```bash
# Clone to your preferred location
git clone https://github.com/yourusername/photo-explorer.git
cd photo-explorer

# Checkout the latest stable release (recommended for production)
git checkout v1.0.0  # Replace with latest stable tag

# Or use main branch (bleeding edge)
git checkout main
```

### 2. Create Production Environment File

```bash
# Copy the example environment file
cp .env.example .env.production

# Edit with your preferred editor
nano .env.production
```

## Environment Configuration

### Required Variables

Edit `.env.production` and set these required variables:

```bash
# =============================================================================
# Security - CRITICAL: Generate and set these before deployment
# =============================================================================

# Token encryption key (generate with command below)
# NEVER use the example value in production!
TOKEN_ENCRYPTION_KEY=your-generated-key-here

# PostgreSQL password (use strong password in production)
POSTGRES_PASSWORD=change-this-to-strong-password

# Grafana admin password (for monitoring dashboard)
GRAFANA_PASSWORD=change-this-to-strong-password
```

### Generate Encryption Key

Generate a secure encryption key for OAuth token storage:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output and set it as `TOKEN_ENCRYPTION_KEY` in `.env.production`.

### Database Configuration

```bash
# PostgreSQL credentials
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-strong-password-here
POSTGRES_DB=photo_explorer

# Connection URL (auto-constructed in docker-compose, but can override)
DATABASE_URL=postgresql+asyncpg://postgres:your-password@postgres:5432/photo_explorer
```

### Google Photos Integration (Optional)

If you want to support Google Photos connector:

```bash
# Web client for frontend OAuth
GOOGLE_OAUTH_WEB_CLIENT_ID=your-web-client-id.apps.googleusercontent.com

# Desktop client for backend token refresh
GOOGLE_API_CLIENT_ID=your-desktop-client-id.apps.googleusercontent.com
GOOGLE_API_CLIENT_SECRET=your-client-secret
```

**How to get Google OAuth credentials:**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable "Google Photos Library API"
4. Go to "Credentials" > "Create Credentials" > "OAuth 2.0 Client ID"
5. Create two OAuth clients:
   - **Web application**: For frontend OAuth flow (no secret needed)
   - **Desktop application**: For backend token refresh (has secret)
6. Add authorized redirect URIs:
   - `http://your-domain.com/api/v1/settings/connectors/google-photos/callback`
   - `http://localhost:5173/settings` (for local development)

### ML Model Configuration

```bash
# CLIP model for semantic search
CLIP_MODEL=ViT-B-32
CLIP_PRETRAINED=openai

# Vision model for photo descriptions
VISION_MODEL=blip2

# HuggingFace token (required for some gated models)
HF_TOKEN=your-huggingface-token
```

### Storage Configuration

```bash
# Base directory for file storage (inside container)
DATA_DIR=/app/storage

# These are managed by Docker volumes, no need to change
STORAGE_PATH=/app/storage
```

### Infrastructure URLs

```bash
# Redis for task queue
REDIS_URL=redis://redis:6379/0

# Qdrant vector database
QDRANT_URL=http://qdrant:6333

# These use service names from docker-compose.yml
# No need to change unless you customize the stack
```

## Starting the Services

### Production Deployment

1. **Create a production docker-compose override** (optional but recommended):

```bash
# Create docker-compose.production.yml
cat > docker-compose.production.yml << 'EOF'
services:
  backend:
    build:
      target: production
    environment:
      - DEBUG=false
      - RELOAD=false
    restart: unless-stopped

  frontend:
    build:
      target: production
    restart: unless-stopped

  worker:
    build:
      target: production
    environment:
      - DEBUG=false
    restart: unless-stopped

  postgres:
    restart: unless-stopped

  qdrant:
    restart: unless-stopped

  redis:
    restart: unless-stopped
EOF
```

2. **Start the services**:

```bash
# Using production environment file
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml up -d

# Or set environment variable
export COMPOSE_FILE=docker-compose.yml:docker-compose.production.yml
docker compose --env-file .env.production up -d
```

3. **Verify all services are running**:

```bash
docker compose ps

# Expected output: All services should show "Up" status
# NAME                     STATUS
# photo-explorer-backend   Up 30 seconds
# photo-explorer-frontend  Up 30 seconds
# photo-explorer-worker    Up 30 seconds
# photo-explorer-postgres  Up 30 seconds (healthy)
# photo-explorer-qdrant    Up 30 seconds (healthy)
# photo-explorer-redis     Up 30 seconds (healthy)
```

4. **Check service health**:

```bash
# Backend health check
curl http://localhost:8000/health

# Expected: {"status":"healthy","timestamp":"2025-11-26T...","version":"0.1.0"}

# Readiness check (includes database, Redis, Qdrant)
curl http://localhost:8000/health/ready

# ML model health check
curl http://localhost:8000/health/ml
```

5. **View logs**:

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f worker

# Last 100 lines
docker compose logs --tail=100 backend
```

### First-Time Initialization

After starting services for the first time:

1. **Database migrations** (automatic on startup):
   ```bash
   # Migrations run automatically when backend starts
   # Check logs to verify
   docker compose logs backend | grep migration
   ```

2. **Download ML models** (optional, can be done via UI):
   ```bash
   # Access the frontend
   # Navigate to Settings > AI Models
   # Click "Download Default Models"

   # Or use CLI (if you have shell access)
   docker compose exec worker poetry run python -m app.cli.download_models
   ```

3. **Create first user/connector**:
   - Access the frontend at `http://your-domain.com`
   - Navigate to Settings > Connectors
   - Add your first photo source (Google Photos or Local Folder)

## Monitoring

Photo Explorer includes built-in monitoring with Prometheus and Grafana (if configured).

### Metrics Endpoint

Application metrics are exposed at:

```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# Sample metrics:
# - celery_task_duration_seconds: Task execution time
# - celery_task_failures_total: Task failures
# - celery_task_success_total: Task successes
# - celery_task_retries_total: Task retries
# - celery_active_tasks: Currently running tasks
```

### Prometheus (Optional)

If you've set up Prometheus in your docker-compose.yml:

```yaml
# Add to docker-compose.production.yml
services:
  prometheus:
    image: prom/prometheus:latest
    container_name: photo-explorer-prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    restart: unless-stopped

volumes:
  prometheus-data:
```

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'photo-explorer-backend'
    static_configs:
      - targets: ['backend:8000']

  - job_name: 'photo-explorer-worker'
    static_configs:
      - targets: ['worker:8000']
```

Access Prometheus at: `http://localhost:9090`

### Grafana (Optional)

Add Grafana for visualization:

```yaml
# Add to docker-compose.production.yml
services:
  grafana:
    image: grafana/grafana:latest
    container_name: photo-explorer-grafana
    volumes:
      - grafana-data:/var/lib/grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
    restart: unless-stopped

volumes:
  grafana-data:
```

Access Grafana at: `http://localhost:3001`
- Default user: `admin`
- Password: Set via `GRAFANA_PASSWORD` in `.env.production`

Configure Prometheus as a data source:
- URL: `http://prometheus:9090`
- Access: Server (default)

### Application Logs

```bash
# View real-time logs
docker compose logs -f

# Search for errors
docker compose logs | grep -i error

# Export logs to file
docker compose logs --since 24h > logs_$(date +%Y%m%d).txt
```

### Health Checks

Automated health checks are configured in docker-compose.yml:

```bash
# Check container health status
docker compose ps

# Healthy services show (healthy) in status column
# Unhealthy services will show (unhealthy) and may restart automatically
```

## Backup Procedures

### Database Backup

**PostgreSQL data:**

```bash
# Create backup directory
mkdir -p backups

# Backup database
docker compose exec postgres pg_dump -U postgres photo_explorer > backups/db_$(date +%Y%m%d_%H%M%S).sql

# Backup with compression
docker compose exec postgres pg_dump -U postgres photo_explorer | gzip > backups/db_$(date +%Y%m%d_%H%M%S).sql.gz
```

**Restore from backup:**

```bash
# Restore uncompressed backup
docker compose exec -T postgres psql -U postgres photo_explorer < backups/db_20251126_120000.sql

# Restore compressed backup
gunzip < backups/db_20251126_120000.sql.gz | docker compose exec -T postgres psql -U postgres photo_explorer
```

### Vector Store Backup

**Qdrant data:**

```bash
# Create snapshot via API
curl -X POST http://localhost:6333/collections/photo_embeddings/snapshots
curl -X POST http://localhost:6333/collections/face_embeddings/snapshots

# Backup the volume
docker run --rm \
  -v photo-explorer_qdrant-data:/qdrant \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/qdrant_$(date +%Y%m%d_%H%M%S).tar.gz /qdrant
```

**Restore Qdrant:**

```bash
# Restore volume from backup
docker run --rm \
  -v photo-explorer_qdrant-data:/qdrant \
  -v $(pwd)/backups:/backup \
  alpine sh -c "cd / && tar xzf /backup/qdrant_20251126_120000.tar.gz"
```

### Token Storage Backup

**Encrypted tokens** (stored in PostgreSQL or filesystem):

```bash
# If using file-based token storage
docker run --rm \
  -v photo-explorer_photo-storage:/storage \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/tokens_$(date +%Y%m%d_%H%M%S).tar.gz /storage/tokens

# Tokens are encrypted with TOKEN_ENCRYPTION_KEY
# Ensure you backup the encryption key separately and securely!
```

### Automated Backup Script

Create `scripts/backup.sh`:

```bash
#!/usr/bin/env bash
set -e

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "Starting backup at $DATE..."

# Database backup
echo "Backing up PostgreSQL..."
docker compose exec postgres pg_dump -U postgres photo_explorer | \
  gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Qdrant backup
echo "Backing up Qdrant..."
docker run --rm \
  -v photo-explorer_qdrant-data:/qdrant \
  -v "$(pwd)/$BACKUP_DIR":/backup \
  alpine tar czf "/backup/qdrant_$DATE.tar.gz" /qdrant

echo "Backup complete!"
echo "Files created:"
echo "  - $BACKUP_DIR/db_$DATE.sql.gz"
echo "  - $BACKUP_DIR/qdrant_$DATE.tar.gz"

# Optional: Clean up old backups (keep last 7 days)
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +7 -delete
find "$BACKUP_DIR" -name "qdrant_*.tar.gz" -mtime +7 -delete
```

Make executable and run:

```bash
chmod +x scripts/backup.sh
./scripts/backup.sh
```

Set up cron for automated backups:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/photo-explorer && ./scripts/backup.sh >> logs/backup.log 2>&1
```

## Upgrading and Updating

### Update to Latest Version

```bash
# Navigate to project directory
cd photo-explorer

# Backup first! (see Backup Procedures above)
./scripts/backup.sh

# Pull latest code
git fetch origin
git checkout main  # or specific version tag
git pull

# Rebuild images
docker compose --env-file .env.production build

# Stop services
docker compose down

# Start with new images
docker compose --env-file .env.production up -d

# Check logs for any migration or startup issues
docker compose logs -f
```

### Update Specific Service

```bash
# Rebuild single service
docker compose build backend

# Restart just that service
docker compose up -d backend

# View logs
docker compose logs -f backend
```

### Database Migrations

Migrations run automatically on backend startup. To manually trigger:

```bash
# Check current migration status
docker compose exec backend poetry run alembic current

# Run migrations manually
docker compose exec backend poetry run alembic upgrade head

# Rollback to specific revision
docker compose exec backend poetry run alembic downgrade <revision>
```

### Zero-Downtime Updates

For production systems requiring minimal downtime:

1. **Use Blue-Green deployment**:
   - Set up second instance with updated code
   - Switch load balancer/reverse proxy to new instance
   - Verify new instance is healthy
   - Shut down old instance

2. **Use rolling updates** (if running multiple replicas):
   ```bash
   # Scale up
   docker compose up -d --scale backend=2 --scale worker=2

   # Update images
   docker compose build

   # Force recreate one at a time
   # This ensures at least one instance is always running
   ```

## Troubleshooting

### Common Issues

#### 1. Services Won't Start

**Symptom:** Container exits immediately after start

```bash
# Check logs for error messages
docker compose logs backend

# Common causes:
# - Missing TOKEN_ENCRYPTION_KEY
# - Database connection failed
# - Port already in use
```

**Solution:**

```bash
# Verify environment variables
docker compose config

# Check if ports are available
sudo netstat -tlnp | grep -E ':(8000|5173|5432|6333|6379)'

# Ensure volumes have correct permissions
sudo chown -R 1000:1000 /var/lib/docker/volumes/photo-explorer_*
```

#### 2. Database Connection Errors

**Symptom:** Backend logs show "could not connect to server"

```bash
# Check PostgreSQL health
docker compose ps postgres

# Check PostgreSQL logs
docker compose logs postgres

# Verify PostgreSQL is accepting connections
docker compose exec postgres pg_isready -U postgres
```

**Solution:**

```bash
# Restart PostgreSQL
docker compose restart postgres

# Wait for health check
sleep 10

# Restart backend
docker compose restart backend
```

#### 3. Token Encryption Errors

**Symptom:** "Invalid token encryption key" or "Fernet key must be 32 url-safe base64-encoded bytes"

**Solution:**

```bash
# Generate new key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Update .env.production
# Restart services
docker compose restart
```

#### 4. Out of Memory

**Symptom:** Worker or backend killed by OOM (Out of Memory)

```bash
# Check memory usage
docker stats

# Check system memory
free -h
```

**Solution:**

```bash
# Reduce worker concurrency in docker-compose.yml
# Change: --concurrency=2
# To: --concurrency=1

# Or add memory limits to docker-compose.production.yml
services:
  worker:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
```

#### 5. Slow ML Inference

**Symptom:** Photo processing takes very long

**Solution:**

```bash
# Check if GPU is being used (if available)
docker compose exec worker nvidia-smi

# Use smaller CLIP model
# In .env.production:
# CLIP_MODEL=ViT-B-32  (faster, less accurate)
# Instead of: ViT-L-14  (slower, more accurate)

# Reduce batch size or use CPU-optimized models
```

#### 6. Vector Search Returns No Results

**Symptom:** Semantic search doesn't find photos

```bash
# Check if embeddings exist
curl http://localhost:6333/collections/photo_embeddings

# Check if collection has points
# Look for: "points_count": <number>
```

**Solution:**

```bash
# Re-index photos
# Via UI: Settings > Connectors > [Your Connector] > Sync Now

# Or trigger sync via API
curl -X POST http://localhost:8000/api/v1/connectors/{connector_id}/sync

# Check worker logs
docker compose logs -f worker
```

#### 7. Google Photos Connector Fails

**Symptom:** "Invalid OAuth credentials" or "Token expired"

**Solution:**

```bash
# Verify credentials in .env.production
# GOOGLE_OAUTH_WEB_CLIENT_ID
# GOOGLE_API_CLIENT_ID
# GOOGLE_API_CLIENT_SECRET

# Delete and re-add connector in UI
# Users will need to re-authenticate

# Check backend logs for detailed OAuth errors
docker compose logs backend | grep -i oauth
```

### Performance Tuning

#### Database Optimization

```bash
# Increase PostgreSQL shared buffers for better performance
# Create postgresql.conf.custom
cat > postgresql.conf.custom << EOF
shared_buffers = 512MB
effective_cache_size = 2GB
work_mem = 16MB
maintenance_work_mem = 256MB
EOF

# Mount in docker-compose.production.yml
services:
  postgres:
    volumes:
      - ./postgresql.conf.custom:/etc/postgresql/postgresql.conf
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
```

#### Worker Optimization

```bash
# Increase concurrency for multi-core systems
# Edit docker-compose.production.yml
services:
  worker:
    command: ["celery", "-A", "app.adapters.inbound.workers", "worker", "--loglevel=info", "--concurrency=4", "--pool=solo"]
```

#### Qdrant Optimization

```bash
# Enable memory-mapping for better performance
# Edit docker-compose.production.yml
services:
  qdrant:
    environment:
      - QDRANT__STORAGE__PERFORMANCE__OPTIMIZERS_CONFIG__MEMMAP_THRESHOLD=20000
```

### Getting Help

If you encounter issues not covered here:

1. Check application logs for detailed error messages
2. Review the [GitHub Issues](https://github.com/yourusername/photo-explorer/issues)
3. Search or create a new issue with:
   - Docker compose version (`docker compose version`)
   - Service logs (`docker compose logs`)
   - Environment (OS, Docker version, hardware)
   - Steps to reproduce

### Debugging Tips

```bash
# Enter container shell for debugging
docker compose exec backend bash
docker compose exec worker bash

# Check Python dependencies
docker compose exec backend poetry show

# Test database connection manually
docker compose exec backend poetry run python -c "from app.config import get_settings; print(get_settings().database_url)"

# Test Qdrant connection
curl http://localhost:6333/collections

# Check Redis
docker compose exec redis redis-cli ping
```

## Security Hardening

### Production Checklist

- [ ] Generate unique `TOKEN_ENCRYPTION_KEY` (never use example value)
- [ ] Use strong `POSTGRES_PASSWORD` (16+ characters, mixed case, numbers, symbols)
- [ ] Set `GRAFANA_PASSWORD` (if using Grafana)
- [ ] Never commit `.env.production` to version control
- [ ] Use HTTPS (set up reverse proxy with SSL/TLS)
- [ ] Enable firewall (allow only necessary ports)
- [ ] Regular backups (automated, tested restore procedures)
- [ ] Keep Docker and system packages updated
- [ ] Monitor logs for suspicious activity
- [ ] Restrict SSH access (key-based auth only, non-standard port)
- [ ] Set up fail2ban or similar intrusion prevention
- [ ] Regular security audits

### Reverse Proxy with HTTPS

Recommended: Use nginx or Caddy as reverse proxy:

**nginx example:**

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Caddy example** (automatic HTTPS):

```
your-domain.com {
    reverse_proxy /api/* localhost:8000
    reverse_proxy localhost:5173
}
```

## Next Steps

After successful deployment:

1. Set up monitoring and alerting
2. Configure automated backups
3. Set up log rotation
4. Plan disaster recovery procedures
5. Document your specific deployment configuration
6. Train your team on operational procedures

For development workflows, see [DEV_WORKFLOW.md](../DEV_WORKFLOW.md).
For API documentation, see [API.md](./API.md) or visit `http://your-domain.com:8000/docs`.
