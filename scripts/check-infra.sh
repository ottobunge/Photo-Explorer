#!/usr/bin/env bash
# Check if infrastructure services (Postgres, Qdrant, Redis) are healthy

set -e

DOCKER_COMPOSE="${DOCKER_COMPOSE:-podman-compose}"

echo "🔍 Checking infrastructure services..."

# Check if Docker Compose is running
if ! $DOCKER_COMPOSE ps >/dev/null 2>&1; then
    echo "❌ Docker Compose is not running"
    exit 1
fi

# Check each service
services=("postgres" "qdrant" "redis")
all_healthy=true

for service in "${services[@]}"; do
    # Check if service is running
    if ! $DOCKER_COMPOSE ps --services --filter "status=running" | grep -q "^${service}$"; then
        echo "❌ ${service} is not running"
        all_healthy=false
    else
        # Check health status
        health=$($DOCKER_COMPOSE ps --format json | jq -r ".[] | select(.Service == \"${service}\") | .Health")
        if [ "$health" = "healthy" ]; then
            echo "✅ ${service} is healthy"
        else
            echo "⚠️  ${service} is running but not healthy yet (status: ${health})"
            all_healthy=false
        fi
    fi
done

if [ "$all_healthy" = true ]; then
    echo ""
    echo "✅ All infrastructure services are ready!"
    exit 0
else
    echo ""
    echo "❌ Some services are not ready. Please run: task services:up"
    exit 1
fi
