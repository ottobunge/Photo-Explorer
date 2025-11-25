"""Shared pytest fixtures for all tests."""

import os
import subprocess
import time
from pathlib import Path

import pytest
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.adapters.outbound.persistence.postgres.models import Base
from app.config import get_settings
from app.main import app

# Load test environment variables
env_test_path = Path(__file__).parent.parent / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path, override=True)


@pytest.fixture(scope="session", autouse=True)
def test_infrastructure():
    """Start test infrastructure before tests and stop after.

    This fixture:
    1. Starts docker compose test services (postgres, qdrant, redis) on non-standard ports
    2. Waits for services to be healthy
    3. Runs all tests
    4. Stops and cleans up test infrastructure
    """
    project_root = Path(__file__).parent.parent.parent
    compose_file = project_root / "docker-compose.test.yml"

    if not compose_file.exists():
        pytest.skip("docker-compose.test.yml not found - skipping infrastructure-dependent tests")
        return

    print("\n🚀 Starting test infrastructure (postgres:5433, qdrant:6334, redis:6380)...")

    # Start test infrastructure
    result = subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "up", "-d"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"⚠️  Failed to start test infrastructure: {result.stderr}")
        pytest.skip("Could not start test infrastructure")
        return

    # Wait for services to be healthy (max 30 seconds)
    print("⏳ Waiting for services to be healthy...")
    max_attempts = 30
    for attempt in range(max_attempts):
        health_check = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "ps", "--format", "json"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        if health_check.returncode == 0:
            # Check if all services are healthy
            time.sleep(1)
            if attempt > 5:  # Give at least 5 seconds for startup
                break

        if attempt == max_attempts - 1:
            print("⚠️  Timeout waiting for services to be healthy")
            pytest.skip("Test infrastructure did not become healthy")
            return

    print("✅ Test infrastructure ready!")

    # Run database migrations
    print("📦 Running database migrations...")
    migration_result = subprocess.run(
        ["poetry", "run", "alembic", "upgrade", "head"],
        cwd=project_root / "backend",
        capture_output=True,
        text=True,
    )

    if migration_result.returncode != 0:
        print(f"⚠️  Migration failed: {migration_result.stderr}")
        # Don't skip - migrations might already be applied
    else:
        print("✅ Database migrations applied")

    yield

    # Cleanup: Stop test infrastructure
    print("\n🧹 Stopping test infrastructure...")
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "down", "-v"],
        cwd=project_root,
        capture_output=True,
    )
    print("✅ Test infrastructure stopped")


@pytest.fixture(scope="session", autouse=True)
def configure_test_settings():
    """Configure settings for test environment.

    Overrides allowed_local_connector_paths to allow both user home
    and /tmp directory for tests.
    """
    # Clear the cache and get fresh settings
    get_settings.cache_clear()
    settings = get_settings()

    # Allow both home directory and /tmp for tests
    # This override persists for the session since settings is cached
    test_allowed_paths = [str(Path.home()), "/tmp"]
    settings.allowed_local_connector_paths = test_allowed_paths

    yield

    # Cleanup: restore cache
    get_settings.cache_clear()


@pytest.fixture
async def client(db_session):
    """Async HTTP client for API testing with database override."""
    from app.dependencies import get_db

    # Override the database dependency to use test database
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    # Clean up dependency overrides
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def db_engine():
    """Create a test database engine."""
    settings = get_settings()
    # Use test database URL or fall back to in-memory SQLite
    test_db_url = getattr(settings, "test_database_url", None) or settings.database_url

    engine = create_async_engine(
        test_db_url,
        echo=False,
        poolclass=NullPool,
    )

    # Create enum types and tables
    async with engine.begin() as conn:

        def create_enums_and_tables(connection):
            # Create PostgreSQL enum types that models need
            connector_type_enum = postgresql.ENUM(
                "google_photos", "local", "upload", name="connectortype", create_type=False
            )
            connector_status_enum = postgresql.ENUM(
                "disconnected",
                "connected",
                "syncing",
                "error",
                name="connectorstatus",
                create_type=False,
            )

            # Create enums if they don't exist
            connector_type_enum.create(connection, checkfirst=True)
            connector_status_enum.create(connection, checkfirst=True)

            # Create all tables
            Base.metadata.create_all(connection)

        await conn.run_sync(create_enums_and_tables)

    yield engine

    # Drop all tables and enums
    async with engine.begin() as conn:

        def drop_all(connection):
            Base.metadata.drop_all(connection)
            # Drop enums
            connection.execute(text("DROP TYPE IF EXISTS connectortype CASCADE"))
            connection.execute(text("DROP TYPE IF EXISTS connectorstatus CASCADE"))

        await conn.run_sync(drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine):
    """Create a test database session."""
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def sample_image_bytes():
    """Create minimal valid JPEG bytes for testing."""
    # Minimal valid JPEG (1x1 red pixel)
    return bytes(
        [
            0xFF,
            0xD8,
            0xFF,
            0xE0,
            0x00,
            0x10,
            0x4A,
            0x46,
            0x49,
            0x46,
            0x00,
            0x01,
            0x01,
            0x00,
            0x00,
            0x01,
            0x00,
            0x01,
            0x00,
            0x00,
            0xFF,
            0xDB,
            0x00,
            0x43,
            0x00,
            0x08,
            0x06,
            0x06,
            0x07,
            0x06,
            0x05,
            0x08,
            0x07,
            0x07,
            0x07,
            0x09,
            0x09,
            0x08,
            0x0A,
            0x0C,
            0x14,
            0x0D,
            0x0C,
            0x0B,
            0x0B,
            0x0C,
            0x19,
            0x12,
            0x13,
            0x0F,
            0x14,
            0x1D,
            0x1A,
            0x1F,
            0x1E,
            0x1D,
            0x1A,
            0x1C,
            0x1C,
            0x20,
            0x24,
            0x2E,
            0x27,
            0x20,
            0x22,
            0x2C,
            0x23,
            0x1C,
            0x1C,
            0x28,
            0x37,
            0x29,
            0x2C,
            0x30,
            0x31,
            0x34,
            0x34,
            0x34,
            0x1F,
            0x27,
            0x39,
            0x3D,
            0x38,
            0x32,
            0x3C,
            0x2E,
            0x33,
            0x34,
            0x32,
            0xFF,
            0xC0,
            0x00,
            0x0B,
            0x08,
            0x00,
            0x01,
            0x00,
            0x01,
            0x01,
            0x01,
            0x11,
            0x00,
            0xFF,
            0xC4,
            0x00,
            0x1F,
            0x00,
            0x00,
            0x01,
            0x05,
            0x01,
            0x01,
            0x01,
            0x01,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x01,
            0x02,
            0x03,
            0x04,
            0x05,
            0x06,
            0x07,
            0x08,
            0x09,
            0x0A,
            0x0B,
            0xFF,
            0xC4,
            0x00,
            0xB5,
            0x10,
            0x00,
            0x02,
            0x01,
            0x03,
            0x03,
            0x02,
            0x04,
            0x03,
            0x05,
            0x05,
            0x04,
            0x04,
            0x00,
            0x00,
            0x01,
            0x7D,
            0x01,
            0x02,
            0x03,
            0x00,
            0x04,
            0x11,
            0x05,
            0x12,
            0x21,
            0x31,
            0x41,
            0x06,
            0x13,
            0x51,
            0x61,
            0x07,
            0x22,
            0x71,
            0x14,
            0x32,
            0x81,
            0x91,
            0xA1,
            0x08,
            0x23,
            0x42,
            0xB1,
            0xC1,
            0x15,
            0x52,
            0xD1,
            0xF0,
            0x24,
            0x33,
            0x62,
            0x72,
            0x82,
            0x09,
            0x0A,
            0x16,
            0x17,
            0x18,
            0x19,
            0x1A,
            0x25,
            0x26,
            0x27,
            0x28,
            0x29,
            0x2A,
            0x34,
            0x35,
            0x36,
            0x37,
            0x38,
            0x39,
            0x3A,
            0x43,
            0x44,
            0x45,
            0x46,
            0x47,
            0x48,
            0x49,
            0x4A,
            0x53,
            0x54,
            0x55,
            0x56,
            0x57,
            0x58,
            0x59,
            0x5A,
            0x63,
            0x64,
            0x65,
            0x66,
            0x67,
            0x68,
            0x69,
            0x6A,
            0x73,
            0x74,
            0x75,
            0x76,
            0x77,
            0x78,
            0x79,
            0x7A,
            0x83,
            0x84,
            0x85,
            0x86,
            0x87,
            0x88,
            0x89,
            0x8A,
            0x92,
            0x93,
            0x94,
            0x95,
            0x96,
            0x97,
            0x98,
            0x99,
            0x9A,
            0xA2,
            0xA3,
            0xA4,
            0xA5,
            0xA6,
            0xA7,
            0xA8,
            0xA9,
            0xAA,
            0xB2,
            0xB3,
            0xB4,
            0xB5,
            0xB6,
            0xB7,
            0xB8,
            0xB9,
            0xBA,
            0xC2,
            0xC3,
            0xC4,
            0xC5,
            0xC6,
            0xC7,
            0xC8,
            0xC9,
            0xCA,
            0xD2,
            0xD3,
            0xD4,
            0xD5,
            0xD6,
            0xD7,
            0xD8,
            0xD9,
            0xDA,
            0xE1,
            0xE2,
            0xE3,
            0xE4,
            0xE5,
            0xE6,
            0xE7,
            0xE8,
            0xE9,
            0xEA,
            0xF1,
            0xF2,
            0xF3,
            0xF4,
            0xF5,
            0xF6,
            0xF7,
            0xF8,
            0xF9,
            0xFA,
            0xFF,
            0xDA,
            0x00,
            0x08,
            0x01,
            0x01,
            0x00,
            0x00,
            0x3F,
            0x00,
            0xFB,
            0xD5,
            0xDB,
            0x20,
            0xA8,
            0xF1,
            0x4F,
            0xFF,
            0xD9,
        ]
    )
