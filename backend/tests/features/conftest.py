"""Pytest configuration for BDD tests."""

import asyncio
from pathlib import Path
from typing import AsyncGenerator, Dict, Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.config import get_settings, Settings
from app.adapters.outbound.persistence.postgres.database import Base
from app.dependencies import get_db, get_settings as get_settings_dep


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Override settings for testing."""
    settings = get_settings()
    settings.testing = True
    settings.database_url = "postgresql+asyncpg://test:test@localhost:5432/photo_test"
    settings.face_detection_enabled = True
    return settings


@pytest_asyncio.fixture(scope="function")
async def test_db(test_settings) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    # Create test engine
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def test_client(test_db: AsyncSession, test_settings: Settings) -> AsyncClient:
    """Create test client with dependency overrides."""

    async def override_get_db():
        yield test_db

    def override_get_settings():
        return test_settings

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings_dep] = override_get_settings

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def test_fixtures_dir(tmp_path: Path) -> Path:
    """Create temporary fixtures directory."""
    fixtures_dir = tmp_path / "fixtures"
    (fixtures_dir / "images").mkdir(parents=True, exist_ok=True)
    (fixtures_dir / "files").mkdir(parents=True, exist_ok=True)
    return fixtures_dir


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Provide test authentication headers."""
    # In a real implementation, this would generate a valid JWT
    return {
        "Authorization": "Bearer test-token-123",
        "X-User-ID": "test-user-id",
    }


@pytest.fixture
def context() -> Dict[str, Any]:
    """Provide context dictionary for sharing data between steps."""
    return {}


@pytest.fixture
def sample_photos(test_fixtures_dir: Path) -> Dict[str, Path]:
    """Create sample photo files for testing."""
    from PIL import Image

    photos = {}
    photo_configs = [
        ("beach.jpg", (255, 200, 100)),     # Orange/beach colors
        ("mountain.jpg", (100, 100, 255)),   # Blue/mountain colors
        ("forest.jpg", (0, 255, 0)),         # Green/forest colors
        ("city.jpg", (128, 128, 128)),      # Gray/urban colors
        ("sunset.jpg", (255, 100, 0)),      # Sunset colors
    ]

    for filename, color in photo_configs:
        img = Image.new("RGB", (200, 200), color=color)
        path = test_fixtures_dir / "images" / filename
        img.save(path, "JPEG")
        photos[filename] = path

    return photos


@pytest.fixture
def mock_ml_services(monkeypatch):
    """Mock ML services for testing."""

    class MockMLService:
        async def generate_embedding(self, image_bytes: bytes):
            """Generate fake embedding."""
            import numpy as np
            return np.random.rand(512).tolist()

        async def detect_faces(self, image_bytes: bytes):
            """Return fake face detections."""
            return [
                {
                    "bbox": [10, 10, 50, 50],
                    "confidence": 0.95,
                    "embedding": [0.1] * 512,
                }
            ]

        async def extract_text(self, image_bytes: bytes):
            """Return fake OCR results."""
            return ""

    monkeypatch.setattr("app.ml_services.ml_service", MockMLService())


@pytest.fixture
def mock_vector_store(monkeypatch):
    """Mock vector store for testing."""

    class MockVectorStore:
        def __init__(self):
            self.embeddings = []

        async def add_embedding(self, photo_id: str, embedding: list):
            """Store embedding."""
            self.embeddings.append({
                "id": photo_id,
                "embedding": embedding
            })

        async def search(self, query_embedding: list, limit: int = 10):
            """Return mock search results."""
            # Return all stored embeddings as results
            return [
                {"id": e["id"], "score": 0.9 - i * 0.1}
                for i, e in enumerate(self.embeddings[:limit])
            ]

        async def delete_embedding(self, photo_id: str):
            """Remove embedding."""
            self.embeddings = [
                e for e in self.embeddings if e["id"] != photo_id
            ]

    monkeypatch.setattr("app.vector_store.vector_store", MockVectorStore())


# Pytest-BDD configuration
def pytest_bdd_step_error(
    request, feature, scenario, step, step_func, step_func_args, exception
):
    """Enhanced error reporting for BDD steps."""
    print(f"\n{'=' * 60}")
    print(f"Step failed: {step}")
    print(f"Scenario: {scenario.name}")
    print(f"Feature: {feature.name}")
    print(f"Error: {exception}")
    print(f"{'=' * 60}\n")