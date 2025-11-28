#!/usr/bin/env bash
set -euo pipefail

# E2E Test Runner for Photo Explorer
# This script sets up test infrastructure, seeds data, and runs E2E tests against real services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker/Podman is available
check_container_runtime() {
    if command -v docker &> /dev/null; then
        CONTAINER_CMD="docker"
        COMPOSE_CMD="docker compose"
    elif command -v podman &> /dev/null; then
        CONTAINER_CMD="podman"
        COMPOSE_CMD="podman-compose"
    else
        log_error "Neither docker nor podman found. Please install one of them."
        exit 1
    fi
    log_info "Using container runtime: $CONTAINER_CMD"
}

# Check if test infrastructure is running
check_infra_running() {
    log_info "Checking if test infrastructure is running..."

    # Check if postgres, qdrant, and redis are running
    if $COMPOSE_CMD -f docker-compose.test.yml ps | grep -q "Up"; then
        log_success "Test infrastructure is already running"
        return 0
    else
        log_warning "Test infrastructure is not running"
        return 1
    fi
}

# Start test infrastructure
start_test_infra() {
    log_info "Starting test infrastructure..."

    $COMPOSE_CMD -f docker-compose.test.yml up -d

    # Wait for services to be healthy
    log_info "Waiting for services to be ready..."
    sleep 5

    # Check PostgreSQL
    local max_attempts=30
    local attempt=1
    while ! $CONTAINER_CMD exec photo-explorer-postgres-test pg_isready -U photoexplorer &> /dev/null; do
        if [ $attempt -ge $max_attempts ]; then
            log_error "PostgreSQL failed to start after $max_attempts attempts"
            exit 1
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done
    echo ""
    log_success "PostgreSQL is ready"

    # Check Qdrant
    attempt=1
    while ! curl -s http://localhost:6334/health &> /dev/null; do
        if [ $attempt -ge $max_attempts ]; then
            log_error "Qdrant failed to start after $max_attempts attempts"
            exit 1
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done
    echo ""
    log_success "Qdrant is ready"

    log_success "Test infrastructure is running"
}

# Check if backend is running
check_backend_running() {
    if curl -s http://localhost:8000/api/v1/health &> /dev/null; then
        log_success "Backend API is running"
        return 0
    else
        log_warning "Backend API is not running"
        return 1
    fi
}

# Start backend services
start_backend() {
    log_info "Starting backend API and worker..."

    cd backend

    # Run migrations
    log_info "Running database migrations..."
    poetry run alembic upgrade head

    # Start API in background
    log_info "Starting API server..."
    poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    API_PID=$!

    # Start worker in background
    log_info "Starting Celery worker..."
    poetry run celery -A app.infrastructure.celery.app worker --loglevel=info &
    WORKER_PID=$!

    # Wait for API to be ready
    local max_attempts=30
    local attempt=1
    while ! curl -s http://localhost:8000/api/v1/health &> /dev/null; do
        if [ $attempt -ge $max_attempts ]; then
            log_error "Backend API failed to start after $max_attempts attempts"
            kill $API_PID $WORKER_PID 2>/dev/null || true
            exit 1
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done
    echo ""

    cd ..
    log_success "Backend services started (API PID: $API_PID, Worker PID: $WORKER_PID)"
}

# Check if test data is seeded
check_data_seeded() {
    log_info "Checking if test data is seeded..."

    # Check if example connector exists
    local response=$(curl -s http://localhost:8000/api/v1/connectors)

    if echo "$response" | grep -q "example-photos"; then
        log_success "Test data is already seeded"
        return 0
    else
        log_warning "Test data not found"
        return 1
    fi
}

# Seed test data
seed_test_data() {
    log_info "Seeding test data..."

    cd backend

    # Register example connector (using the script or API)
    log_info "Registering example connector..."
    poetry run python -c "
from app.adapters.inbound.api.schemas.connector_schemas import RegisterConnectorRequest
from app.adapters.outbound.persistence.postgres.repositories import ConnectorRepositoryPostgres
from app.infrastructure.database.session import get_session_context
import asyncio

async def seed():
    async with get_session_context() as session:
        repo = ConnectorRepositoryPostgres(session)
        # Register local filesystem connector pointing to example photos
        connector = await repo.create({
            'name': 'example-photos',
            'connector_type': 'local_filesystem',
            'config': {
                'path': '/app/tests/fixtures/example_photos'
            }
        })
        print(f'Registered connector: {connector.id}')
        await session.commit()

asyncio.run(seed())
"

    cd ..
    log_success "Test data seeded"
}

# Wait for worker to process all photos
wait_for_processing() {
    log_info "Waiting for worker to process all photos..."

    local max_wait=300  # 5 minutes max
    local elapsed=0
    local check_interval=5

    while [ $elapsed -lt $max_wait ]; do
        # Check if there are any pending tasks
        local pending=$(curl -s http://localhost:8000/api/v1/photos?processing_status=pending | jq -r '.meta.total // 0')

        if [ "$pending" -eq 0 ]; then
            log_success "All photos processed"
            return 0
        fi

        log_info "Still processing... ($pending photos pending)"
        sleep $check_interval
        ((elapsed += check_interval))
    done

    log_warning "Timeout waiting for photo processing (some photos may still be pending)"
}

# Check if frontend dev server is running
check_frontend_running() {
    if curl -s http://localhost:5173 &> /dev/null; then
        log_success "Frontend dev server is running"
        return 0
    else
        log_warning "Frontend dev server is not running"
        return 1
    fi
}

# Start frontend dev server
start_frontend() {
    log_info "Starting frontend dev server..."

    cd frontend

    # Start dev server in background
    npm run dev &
    FRONTEND_PID=$!

    # Wait for server to be ready
    local max_attempts=30
    local attempt=1
    while ! curl -s http://localhost:5173 &> /dev/null; do
        if [ $attempt -ge $max_attempts ]; then
            log_error "Frontend dev server failed to start after $max_attempts attempts"
            kill $FRONTEND_PID 2>/dev/null || true
            exit 1
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done
    echo ""

    cd ..
    log_success "Frontend dev server started (PID: $FRONTEND_PID)"
}

# Run E2E tests
run_e2e_tests() {
    log_info "Running E2E tests..."

    cd frontend

    # Run Playwright E2E tests
    if nix-shell --run "npm run test:e2e"; then
        log_success "E2E tests passed!"
        exit_code=0
    else
        log_error "E2E tests failed"
        exit_code=1
    fi

    cd ..
    return $exit_code
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."

    # Kill background processes if they were started
    if [ -n "${API_PID:-}" ]; then
        log_info "Stopping API server (PID: $API_PID)"
        kill $API_PID 2>/dev/null || true
    fi

    if [ -n "${WORKER_PID:-}" ]; then
        log_info "Stopping Celery worker (PID: $WORKER_PID)"
        kill $WORKER_PID 2>/dev/null || true
    fi

    if [ -n "${FRONTEND_PID:-}" ]; then
        log_info "Stopping frontend dev server (PID: $FRONTEND_PID)"
        kill $FRONTEND_PID 2>/dev/null || true
    fi
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

# Main execution
main() {
    log_info "Photo Explorer E2E Test Runner"
    log_info "================================"

    # Check prerequisites
    check_container_runtime

    # Step 1: Ensure test infrastructure is running
    if ! check_infra_running; then
        start_test_infra
    fi

    # Step 2: Ensure backend is running
    if ! check_backend_running; then
        start_backend
    fi

    # Step 3: Ensure test data is seeded
    if ! check_data_seeded; then
        seed_test_data
        wait_for_processing
    fi

    # Step 4: Ensure frontend dev server is running
    if ! check_frontend_running; then
        start_frontend
    fi

    # Step 5: Run E2E tests
    run_e2e_tests
}

# Run main function
main "$@"
