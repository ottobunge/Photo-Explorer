"""FastAPI application entry point.

This module initializes the FastAPI application with:
- Request ID tracing middleware
- Rate limiting middleware
- Standardized error handlers
- CORS configuration
- Graceful shutdown handling
- API route registration
"""

import asyncio
import logging
import signal
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.inbound.api.routes import (
    albums,
    connectors,
    faces,
    folders,
    health,
    models,
    photos,
    search,
    settings,
)
from app.config import get_settings
from app.logging_config import setup_logging
from app.middleware import RequestIDMiddleware, setup_rate_limiting
from app.middleware.error_handlers import setup_error_handlers

# Keep backward compatibility with existing RequestTracingMiddleware if it exists
try:
    from app.middleware import RequestTracingMiddleware
    USE_REQUEST_TRACING = True
except ImportError:
    USE_REQUEST_TRACING = False

logger = logging.getLogger(__name__)

# Graceful shutdown state
shutdown_event = asyncio.Event()


async def shutdown_handler() -> None:
    """Handle graceful shutdown of the application."""
    logger.info("Shutdown signal received, starting graceful shutdown...")

    # Set shutdown event
    shutdown_event.set()

    # Cleanup resources
    try:
        # Close database connections
        from app.adapters.outbound.persistence.postgres.database import close_db

        logger.info("Closing database connections...")
        await close_db()

        # Cleanup ML services
        from app.adapters.outbound.ml import cleanup_ml_services

        logger.info("Cleaning up ML services...")
        cleanup_ml_services()

        # Cleanup vector store
        from app.adapters.outbound.persistence.qdrant.vector_store import (
            cleanup_vector_store,
        )

        logger.info("Cleaning up vector store connections...")
        await cleanup_vector_store()

        logger.info("Graceful shutdown completed successfully")

    except Exception as e:
        logger.error(f"Error during graceful shutdown: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    app_settings = get_settings()

    # Configure logging
    setup_logging(
        level="DEBUG" if app_settings.debug else "INFO",
        json_logs=not app_settings.debug,
        debug=app_settings.debug,
    )

    logger.info("Starting Photo Explorer application...")

    # Startup
    logger.info("Creating required directories...")
    app_settings.ensure_directories()

    # Initialize database connection pool (lazy initialization)
    logger.info("Database connection pool will be initialized on first use")

    # Initialize Qdrant client (lazy initialization)
    logger.info("Qdrant client will be initialized on first use")

    # Initialize default connectors
    try:
        from app.adapters.outbound.persistence.postgres.repositories.connector_repository import (
            ConnectorRepositoryPostgres,
        )
        from app.adapters.outbound.persistence.postgres import get_async_session
        from app.application.services.connector_initialization import (
            ensure_default_upload_connector,
        )

        logger.info("Initializing default connectors...")

        # Get a database session
        async for session in get_async_session():
            try:
                connector_repo = ConnectorRepositoryPostgres(session)
                uploads_path = app_settings.storage_path / "uploads"
                uploads_path.mkdir(parents=True, exist_ok=True)

                await ensure_default_upload_connector(connector_repo, uploads_path)
                await session.commit()
                logger.info("Default connectors initialized")
            finally:
                await session.close()
            break  # Only need one iteration
    except Exception as e:
        logger.warning(f"Failed to initialize default connectors: {e}", exc_info=True)
        # Don't fail startup if connector initialization fails
        # The app can still function, uploads just won't be associated with a connector

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Application shutdown initiated...")
    await shutdown_handler()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Sets up:
    1. FastAPI app with OpenAPI docs
    2. Request ID tracing middleware
    3. Rate limiting middleware
    4. CORS middleware
    5. Standardized error handlers
    6. API route registration

    Returns:
        Configured FastAPI application instance
    """
    app_settings = get_settings()

    # OpenAPI tags for organizing endpoints
    tags_metadata = [
        {"name": "Health", "description": "Health check endpoints for monitoring application status"},
        {"name": "Photos", "description": "Photo management: upload, retrieve, delete. AI processing includes scene classification, object detection, and face recognition."},
        {"name": "Albums", "description": "Album management: create albums, add/remove photos, set cover photos"},
        {"name": "Search", "description": "Semantic search using natural language queries powered by CLIP embeddings"},
        {"name": "Faces", "description": "Face detection and recognition: view clusters, assign names, search by person"},
        {"name": "Connectors", "description": "Photo source connectors: Google Photos, local folders, and other sources"},
        {"name": "Folders", "description": "Local folder management: watch folders and auto-import photos"},
        {"name": "Settings", "description": "Application settings and configuration management"},
        {"name": "Models", "description": "ML model management: check status and download AI models"},
    ]

    app = FastAPI(
        title=app_settings.app_name,
        description="AI-powered photo organization and semantic search. Features include semantic search, face recognition, scene classification, multi-source photo sync, and album management. See /docs for interactive API documentation.",
        version="1.0.0",
        terms_of_service="https://github.com/example/photo-explorer/blob/main/TERMS.md",
        contact={
            "name": "Photo Explorer API Support",
            "url": "https://github.com/example/photo-explorer",
            "email": "support@example.com",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        openapi_tags=tags_metadata,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{app_settings.api_v1_prefix}/openapi.json",
    )

    # ==================== MIDDLEWARE ====================
    # Order matters: middleware is applied in reverse order
    # (last added = first executed on request, last executed on response)

    # 1. CORS middleware (outermost layer)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )
    logger.info("CORS middleware registered")

    # 2. Request ID middleware (for tracing and correlation)
    if USE_REQUEST_TRACING:
        # Use existing RequestTracingMiddleware if available
        app.add_middleware(RequestTracingMiddleware)
        logger.info("RequestTracingMiddleware registered (existing)")
    else:
        # Use new RequestIDMiddleware
        app.add_middleware(RequestIDMiddleware)
        logger.info("RequestIDMiddleware registered (new)")

    # 3. Rate limiting middleware (protects endpoints from abuse)
    limiter = setup_rate_limiting(app)
    logger.info("Rate limiting middleware registered (100 req/min default)")

    # ==================== ERROR HANDLERS ====================
    setup_error_handlers(app)
    logger.info("Standardized error handlers registered")

    # ==================== ROUTERS ====================
    # Include health check router
    app.include_router(health.router, tags=["Health"])

    # Include API routers
    api_prefix = app_settings.api_v1_prefix

    app.include_router(photos.router, prefix=f"{api_prefix}/photos", tags=["Photos"])
    app.include_router(albums.router, prefix=f"{api_prefix}/albums", tags=["Albums"])
    app.include_router(search.router, prefix=f"{api_prefix}/search", tags=["Search"])
    app.include_router(faces.router, prefix=f"{api_prefix}/faces", tags=["Faces"])
    app.include_router(folders.router, prefix=f"{api_prefix}/folders", tags=["Folders"])
    app.include_router(
        connectors.router, prefix=f"{api_prefix}/connectors", tags=["Connectors"]
    )
    app.include_router(
        settings.router, prefix=f"{api_prefix}/settings", tags=["Settings"]
    )
    app.include_router(
        models.router, prefix=f"{api_prefix}/models", tags=["Models"]
    )

    logger.info("API routes registered")

    return app


# Create the application instance
app = create_app()


# Signal handlers for graceful shutdown
def handle_sigterm(signum: int, frame) -> None:
    """Handle SIGTERM signal."""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()


def handle_sigint(signum: int, frame) -> None:
    """Handle SIGINT signal (Ctrl+C)."""
    logger.info(f"Received signal {signum} (SIGINT), initiating graceful shutdown...")
    shutdown_event.set()


# Register signal handlers
signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigint)
