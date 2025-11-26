"""Database connection and session management."""

import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import get_settings

# Global engine instance (for FastAPI)
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None

# Thread-local storage for worker engines to prevent memory leaks
_worker_engine_cache = threading.local()


def get_engine(use_pool: bool = True) -> AsyncEngine:
    """Get or create the async database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI to get an async database session.

    Usage:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_async_session)):
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for getting a database session outside of FastAPI.

    Usage:
        async with get_session_context() as session:
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize database - create tables if they don't exist."""
    from app.adapters.outbound.persistence.postgres.models import Base

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


async def cleanup_worker_engine() -> None:
    """
    Cleanup the thread-local worker engine.

    This should be called during worker shutdown to properly dispose
    of the cached engine and prevent memory leaks.
    """
    if hasattr(_worker_engine_cache, "engine"):
        engine = _worker_engine_cache.engine
        await engine.dispose()
        delattr(_worker_engine_cache, "engine")


@asynccontextmanager
async def get_worker_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for getting a database session in Celery workers.

    Uses a thread-local cached engine to avoid creating new engines for every task.
    The engine uses NullPool to create new connections each time, avoiding
    event loop issues with forked processes.

    Usage:
        async with get_worker_session_context() as session:
            ...
    """
    # Check if this thread already has a cached engine
    if not hasattr(_worker_engine_cache, "engine"):
        settings = get_settings()
        # Create and cache engine without pooling for workers
        _worker_engine_cache.engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            poolclass=NullPool,
        )

    engine = _worker_engine_cache.engine

    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
