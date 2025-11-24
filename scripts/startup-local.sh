#!/usr/bin/env bash
# Startup script for local development
# Runs database migrations and creates Qdrant collections if needed

set -e

echo "🚀 Running startup tasks for local development..."

# Check if we're in the backend directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Must be run from backend directory"
    exit 1
fi

# Wait for Postgres to be ready
echo "⏳ Waiting for Postgres to be ready..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if poetry run python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import get_settings

async def check_db():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(__import__('sqlalchemy').text('SELECT 1'))
        await engine.dispose()
        return True
    except Exception:
        await engine.dispose()
        return False

exit(0 if asyncio.run(check_db()) else 1)
" 2>/dev/null; then
        echo "✅ Postgres is ready"
        break
    fi
    attempt=$((attempt + 1))
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ Postgres failed to become ready after ${max_attempts} attempts"
        exit 1
    fi
    sleep 1
done

# Wait for Qdrant to be ready
echo "⏳ Waiting for Qdrant to be ready..."
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if poetry run python -c "
import asyncio
from qdrant_client import AsyncQdrantClient
from app.config import get_settings

async def check_qdrant():
    settings = get_settings()
    client = AsyncQdrantClient(url=settings.qdrant_url)
    try:
        await client.get_collections()
        await client.close()
        return True
    except Exception:
        await client.close()
        return False

exit(0 if asyncio.run(check_qdrant()) else 1)
" 2>/dev/null; then
        echo "✅ Qdrant is ready"
        break
    fi
    attempt=$((attempt + 1))
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ Qdrant failed to become ready after ${max_attempts} attempts"
        exit 1
    fi
    sleep 1
done

# Run database migrations
echo "📊 Running database migrations..."
if poetry run alembic upgrade head; then
    echo "✅ Database migrations completed"
else
    echo "❌ Database migrations failed"
    exit 1
fi

# Create Qdrant collections if they don't exist
echo "🔍 Creating Qdrant collections (if missing)..."
if poetry run python -c "
import asyncio
from app.config import get_settings
from app.adapters.outbound.vector_store import QdrantVectorStore

async def create_collections():
    settings = get_settings()
    vector_store = QdrantVectorStore(
        url=settings.qdrant_url,
        embedding_dim=512  # CLIP ViT-B-32 dimension
    )

    try:
        # This will create collections if they don't exist
        # QdrantVectorStore.__init__ handles collection creation
        print('✅ Qdrant collections verified/created')
    except Exception as e:
        print(f'❌ Qdrant collection setup failed: {e}')
        raise

asyncio.run(create_collections())
"; then
    echo "✅ Qdrant collections ready"
else
    echo "❌ Qdrant collection setup failed"
    exit 1
fi

echo ""
echo "✅ Startup tasks completed!"
echo ""
