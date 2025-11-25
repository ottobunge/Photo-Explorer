#!/usr/bin/env bash
# Test Infrastructure Management Script
# Manages docker compose test services on non-standard ports

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.test.yml"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

function print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

function print_error() {
    echo -e "${RED}✗${NC} $1"
}

function show_help() {
    cat << EOF
Test Infrastructure Management

Usage: $0 [command]

Commands:
    up          Start test infrastructure (postgres:5433, qdrant:6334, redis:6380)
    down        Stop test infrastructure
    restart     Restart test infrastructure
    clean       Stop and remove all test data (volumes)
    status      Show status of test services
    logs        Show logs from test services
    migrate     Run database migrations on test database
    help        Show this help message

Test Services:
    postgres-test    Port 5433 (main: 5432)
    qdrant-test      Port 6334 (main: 6333)
    redis-test       Port 6380 (main: 6379)

Environment:
    Test environment variables are loaded from backend/.env.test

Examples:
    $0 up              # Start test infrastructure
    $0 migrate         # Run migrations
    $0 logs postgres   # Show postgres logs
    $0 clean           # Remove all test data
EOF
}

function start_infrastructure() {
    print_status "Starting test infrastructure..."
    docker compose -f "$COMPOSE_FILE" up -d

    print_status "Waiting for services to be healthy..."
    sleep 5

    # Check health
    docker compose -f "$COMPOSE_FILE" ps

    print_status "Test infrastructure started!"
    echo ""
    echo "Services running on:"
    echo "  PostgreSQL: localhost:5433"
    echo "  Qdrant:     localhost:6334"
    echo "  Redis:      localhost:6380"
    echo ""
    echo "Run '$0 migrate' to apply database migrations"
}

function stop_infrastructure() {
    print_status "Stopping test infrastructure..."
    docker compose -f "$COMPOSE_FILE" down
    print_status "Test infrastructure stopped"
}

function clean_infrastructure() {
    print_warning "This will remove all test data (volumes)"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Cleaning test infrastructure..."
        docker compose -f "$COMPOSE_FILE" down -v
        print_status "Test infrastructure cleaned"
    else
        print_warning "Cancelled"
    fi
}

function restart_infrastructure() {
    stop_infrastructure
    sleep 2
    start_infrastructure
}

function show_status() {
    print_status "Test infrastructure status:"
    docker compose -f "$COMPOSE_FILE" ps
}

function show_logs() {
    if [ -z "$2" ]; then
        docker compose -f "$COMPOSE_FILE" logs -f
    else
        docker compose -f "$COMPOSE_FILE" logs -f "$2"
    fi
}

function run_migrations() {
    print_status "Running database migrations..."
    cd "$PROJECT_ROOT/backend"

    # Load test environment
    if [ -f ".env.test" ]; then
        export $(grep -v '^#' .env.test | xargs)
    fi

    poetry run alembic upgrade head
    print_status "Migrations complete"
}

# Main command handling
case "${1:-help}" in
    up|start)
        start_infrastructure
        ;;
    down|stop)
        stop_infrastructure
        ;;
    restart)
        restart_infrastructure
        ;;
    clean)
        clean_infrastructure
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$@"
        ;;
    migrate)
        run_migrations
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
