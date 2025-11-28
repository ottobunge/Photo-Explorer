#!/usr/bin/env bash
# Script to run integration tests with proper infrastructure setup
# This ensures test infrastructure is running before executing tests

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if docker-compose is available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

# Start test infrastructure
print_info "Starting test infrastructure (postgres:5433, qdrant:6334, redis:6380)..."
docker compose -f docker-compose.test.yml up -d

# Wait for services to be healthy
print_info "Waiting for services to be healthy..."
sleep 5

# Check if services are running
if ! docker compose -f docker-compose.test.yml ps | grep -q "Up"; then
    print_error "Test infrastructure failed to start"
    docker compose -f docker-compose.test.yml logs
    exit 1
fi

print_info "Test infrastructure is ready!"

# Determine which tests to run
TEST_CATEGORY="${1:-all}"

cd backend

case "$TEST_CATEGORY" in
    workflows)
        print_info "Running workflow integration tests..."
        poetry run pytest tests/integration/workflows/ -v --tb=short
        ;;
    connectors)
        print_info "Running connector integration tests..."
        poetry run pytest tests/integration/connectors/ -v --tb=short
        ;;
    repositories)
        print_info "Running repository integration tests..."
        poetry run pytest tests/integration/repositories/ -v --tb=short
        ;;
    workers)
        print_info "Running worker integration tests..."
        poetry run pytest tests/integration/workers/ -v --tb=short
        ;;
    performance)
        print_info "Running performance tests only..."
        poetry run pytest tests/integration/ -v --tb=short -k "performance"
        ;;
    all)
        print_info "Running all integration tests..."
        poetry run pytest tests/integration/ -v --tb=short -m integration
        ;;
    coverage)
        print_info "Running all integration tests with coverage..."
        poetry run pytest tests/integration/ -v --tb=short --cov=app --cov-report=html --cov-report=term-missing
        ;;
    *)
        print_error "Unknown test category: $TEST_CATEGORY"
        echo "Usage: $0 [workflows|connectors|repositories|workers|performance|all|coverage]"
        exit 1
        ;;
esac

TEST_EXIT_CODE=$?

# Cleanup
if [ "${KEEP_INFRASTRUCTURE:-}" != "1" ]; then
    print_info "Stopping test infrastructure..."
    docker compose -f docker-compose.test.yml down -v
    print_info "Test infrastructure stopped"
else
    print_warn "Keeping test infrastructure running (KEEP_INFRASTRUCTURE=1)"
    print_info "To stop manually: docker compose -f docker-compose.test.yml down -v"
fi

if [ $TEST_EXIT_CODE -eq 0 ]; then
    print_info "✓ All tests passed!"
else
    print_error "✗ Some tests failed (exit code: $TEST_EXIT_CODE)"
fi

exit $TEST_EXIT_CODE
