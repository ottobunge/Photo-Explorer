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

# Wait for infrastructure to be ready
echo "⏳ Waiting for infrastructure services..."
sleep 2

# Run database migrations
echo "📊 Running database migrations..."
if poetry run alembic upgrade head; then
    echo "✅ Database migrations completed"
else
    echo "⚠️  Database migrations failed, but continuing..."
fi

# Create Qdrant collections if they don't exist
echo "🔍 Creating Qdrant collections (if missing)..."
poetry run python -c "
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
        print(f'⚠️  Qdrant collection setup warning: {e}')
    finally:
        if hasattr(vector_store, '_client'):
            await vector_store._client.close()

asyncio.run(create_collections())
" || echo "⚠️  Qdrant setup warning, but continuing..."

echo ""
echo "✅ Startup tasks completed!"
echo ""
