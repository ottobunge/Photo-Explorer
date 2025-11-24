# Photo Explorer - Testing Strategy

## Test-Driven Development (TDD) Workflow

### The Red-Green-Refactor Cycle

1. **Red**: Write a failing test that defines expected behavior
2. **Green**: Write minimal code to make the test pass
3. **Refactor**: Clean up code while keeping tests green

### Behavior-Focused Testing

Tests should describe **what** the system does, not **how** it does it:

```python
# Bad: Implementation-focused
def test_photo_service_calls_qdrant_insert():
    # Tests internal implementation details
    pass

# Good: Behavior-focused
def test_uploaded_photo_becomes_searchable():
    # Tests observable behavior from user perspective
    pass
```

---

## Backend Testing Stack

### Tools

- **pytest**: Test runner and assertions
- **pytest-bdd**: Behavior-driven testing with Gherkin syntax
- **pytest-asyncio**: Async test support
- **httpx**: Async HTTP client for API testing
- **testcontainers**: Docker containers for integration tests
- **factory-boy**: Test data factories
- **faker**: Realistic fake data generation
- **pytest-cov**: Coverage reporting

### Test Structure

```
backend/
├── tests/
│   ├── conftest.py           # Shared fixtures
│   ├── factories.py          # Test data factories
│   ├── unit/                 # Unit tests
│   │   ├── test_photo_service.py
│   │   ├── test_search_service.py
│   │   ├── test_face_service.py
│   │   └── test_utils.py
│   ├── integration/          # Integration tests
│   │   ├── test_photo_api.py
│   │   ├── test_search_api.py
│   │   ├── test_face_api.py
│   │   └── test_album_api.py
│   └── features/             # BDD tests
│       ├── photo_upload.feature
│       ├── semantic_search.feature
│       ├── face_detection.feature
│       └── steps/
│           ├── photo_steps.py
│           ├── search_steps.py
│           └── face_steps.py
```

### Unit Test Example

```python
# tests/unit/test_photo_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from app.services.photo_service import PhotoService

class TestPhotoService:
    """Behavior tests for PhotoService."""

    @pytest.fixture
    def photo_service(self, mock_db, mock_storage, mock_queue):
        return PhotoService(
            db=mock_db,
            storage=mock_storage,
            queue=mock_queue
        )

    async def test_uploading_photo_stores_file_and_queues_processing(
        self, photo_service, sample_image
    ):
        """When a photo is uploaded, it should be stored and queued."""
        # Arrange
        file = sample_image("beach.jpg")

        # Act
        result = await photo_service.upload(file)

        # Assert
        assert result.id is not None
        assert result.status == "processing"
        photo_service.storage.save.assert_called_once()
        photo_service.queue.enqueue.assert_called_once()

    async def test_uploading_invalid_file_raises_error(
        self, photo_service
    ):
        """When an invalid file is uploaded, it should raise ValidationError."""
        # Arrange
        file = Mock(content_type="application/pdf")

        # Act & Assert
        with pytest.raises(ValidationError) as exc:
            await photo_service.upload(file)
        assert "Invalid file type" in str(exc.value)
```

### Integration Test Example

```python
# tests/integration/test_photo_api.py
import pytest
from httpx import AsyncClient
from testcontainers.postgres import PostgresContainer
from testcontainers.core.generic import DockerContainer

@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:15") as pg:
        yield pg

@pytest.fixture(scope="session")
def qdrant():
    with DockerContainer("qdrant/qdrant:latest").with_exposed_ports(6333) as q:
        yield q

@pytest.fixture
async def client(postgres, qdrant, app):
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

class TestPhotoUploadAPI:
    """Integration tests for photo upload endpoints."""

    async def test_upload_single_photo_returns_201(self, client, sample_jpeg):
        """POST /photos/upload with valid image returns 201."""
        response = await client.post(
            "/api/v1/photos/upload",
            files={"files": ("test.jpg", sample_jpeg, "image/jpeg")}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["uploaded"]) == 1

    async def test_upload_to_album_associates_photo(
        self, client, sample_jpeg, created_album
    ):
        """Uploading to album should associate photo with album."""
        response = await client.post(
            "/api/v1/photos/upload",
            files={"files": ("test.jpg", sample_jpeg, "image/jpeg")},
            data={"album_id": str(created_album.id)}
        )

        assert response.status_code == 201
        photo_id = response.json()["data"]["uploaded"][0]["id"]

        # Verify association
        album_response = await client.get(
            f"/api/v1/albums/{created_album.id}"
        )
        photo_ids = [p["id"] for p in album_response.json()["data"]["photos"]]
        assert photo_id in photo_ids
```

### BDD Test Example

```gherkin
# tests/features/semantic_search.feature
Feature: Semantic Photo Search
  As a user
  I want to search photos using natural language
  So that I can find photos without knowing their filenames

  Background:
    Given the system has processed the following photos:
      | filename      | description                    |
      | beach.jpg     | sunny beach with palm trees    |
      | mountain.jpg  | snowy mountain peak            |
      | party.jpg     | birthday party with cake       |

  Scenario: Search finds relevant photos
    When I search for "tropical vacation"
    Then I should see "beach.jpg" in the results
    And "beach.jpg" should have higher score than "mountain.jpg"

  Scenario: Search with date filter
    Given "beach.jpg" was taken on "2024-06-15"
    And "mountain.jpg" was taken on "2023-12-01"
    When I search for "outdoor scene"
    And I filter by year "2024"
    Then I should see "beach.jpg" in the results
    And I should not see "mountain.jpg" in the results

  Scenario: Search returns no results gracefully
    When I search for "underwater submarine"
    Then I should see no results
    And I should see message "No matching photos found"
```

```python
# tests/features/steps/search_steps.py
from pytest_bdd import given, when, then, parsers

@given(parsers.parse('the system has processed the following photos:'))
def processed_photos(datatable, photo_factory, processing_service):
    for row in datatable:
        photo = photo_factory.create(
            filename=row["filename"],
            description=row["description"],
            processing_status="completed"
        )
        # Ensure embeddings are generated
        processing_service.generate_embedding(photo)

@when(parsers.parse('I search for "{query}"'))
def search_for(query, search_context, search_service):
    search_context["results"] = search_service.search(query)

@then(parsers.parse('I should see "{filename}" in the results'))
def should_see_in_results(filename, search_context):
    filenames = [r.photo.filename for r in search_context["results"]]
    assert filename in filenames
```

---

## Frontend Testing Stack

### Tools

- **Vitest**: Unit test runner (fast, Vite-native)
- **Testing Library**: Component testing
- **Playwright**: End-to-end testing
- **MSW (Mock Service Worker)**: API mocking

### Test Structure

```
frontend/
├── src/
│   └── lib/
│       ├── components/
│       │   ├── PhotoGrid.svelte
│       │   └── PhotoGrid.test.ts
│       └── stores/
│           ├── photos.ts
│           └── photos.test.ts
├── tests/
│   ├── e2e/
│   │   ├── upload.spec.ts
│   │   ├── search.spec.ts
│   │   └── faces.spec.ts
│   └── fixtures/
│       └── handlers.ts    # MSW handlers
├── vitest.config.ts
└── playwright.config.ts
```

### Component Test Example

```typescript
// src/lib/components/PhotoGrid.test.ts
import { render, screen, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import PhotoGrid from './PhotoGrid.svelte';

describe('PhotoGrid', () => {
  const mockPhotos = [
    { id: '1', filename: 'beach.jpg', thumbnailUrl: '/thumb/1.jpg' },
    { id: '2', filename: 'mountain.jpg', thumbnailUrl: '/thumb/2.jpg' },
  ];

  it('displays all provided photos', () => {
    render(PhotoGrid, { props: { photos: mockPhotos } });

    expect(screen.getByAltText('beach.jpg')).toBeInTheDocument();
    expect(screen.getByAltText('mountain.jpg')).toBeInTheDocument();
  });

  it('calls onSelect when photo is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();

    render(PhotoGrid, { props: { photos: mockPhotos, onSelect } });

    await user.click(screen.getByAltText('beach.jpg'));

    expect(onSelect).toHaveBeenCalledWith(mockPhotos[0]);
  });

  it('shows empty state when no photos', () => {
    render(PhotoGrid, { props: { photos: [] } });

    expect(screen.getByText('No photos to display')).toBeInTheDocument();
  });

  it('supports keyboard navigation', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();

    render(PhotoGrid, { props: { photos: mockPhotos, onSelect } });

    const firstPhoto = screen.getByAltText('beach.jpg').closest('[role="button"]');
    firstPhoto?.focus();

    await user.keyboard('{Enter}');

    expect(onSelect).toHaveBeenCalledWith(mockPhotos[0]);
  });
});
```

### Store Test Example

```typescript
// src/lib/stores/photos.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { get } from 'svelte/store';
import { createPhotosStore } from './photos';

describe('photos store', () => {
  let store: ReturnType<typeof createPhotosStore>;
  let mockApi: any;

  beforeEach(() => {
    mockApi = {
      fetchPhotos: vi.fn(),
      uploadPhotos: vi.fn(),
    };
    store = createPhotosStore(mockApi);
  });

  it('loads photos from API', async () => {
    mockApi.fetchPhotos.mockResolvedValue([
      { id: '1', filename: 'test.jpg' }
    ]);

    await store.load();

    expect(get(store.photos)).toHaveLength(1);
    expect(get(store.loading)).toBe(false);
  });

  it('sets loading state during fetch', async () => {
    mockApi.fetchPhotos.mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );

    const loadPromise = store.load();

    expect(get(store.loading)).toBe(true);

    await loadPromise;

    expect(get(store.loading)).toBe(false);
  });

  it('handles upload and adds new photos', async () => {
    const files = [new File([''], 'test.jpg', { type: 'image/jpeg' })];
    mockApi.uploadPhotos.mockResolvedValue([{ id: '1', filename: 'test.jpg' }]);

    await store.upload(files);

    expect(mockApi.uploadPhotos).toHaveBeenCalledWith(files);
    expect(get(store.photos)).toHaveLength(1);
  });
});
```

### E2E Test Example

```typescript
// tests/e2e/search.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Photo Search', () => {
  test.beforeEach(async ({ page }) => {
    // Seed test data
    await page.goto('/');
  });

  test('user can search photos by text', async ({ page }) => {
    await page.goto('/search');

    // Enter search query
    await page.fill('[data-testid="search-input"]', 'beach sunset');
    await page.click('[data-testid="search-button"]');

    // Wait for results
    await expect(page.locator('[data-testid="search-results"]')).toBeVisible();

    // Verify results contain relevant photos
    const results = page.locator('[data-testid="photo-card"]');
    await expect(results).toHaveCount.greaterThan(0);
  });

  test('user can filter search by date', async ({ page }) => {
    await page.goto('/search');

    await page.fill('[data-testid="search-input"]', 'vacation');

    // Open date filter
    await page.click('[data-testid="filter-toggle"]');
    await page.fill('[data-testid="date-from"]', '2024-01-01');
    await page.fill('[data-testid="date-to"]', '2024-12-31');

    await page.click('[data-testid="search-button"]');

    // All results should be from 2024
    const dates = await page.locator('[data-testid="photo-date"]').allTextContents();
    for (const date of dates) {
      expect(date).toContain('2024');
    }
  });

  test('empty search shows helpful message', async ({ page }) => {
    await page.goto('/search');

    await page.fill('[data-testid="search-input"]', 'xyznonexistent123');
    await page.click('[data-testid="search-button"]');

    await expect(page.locator('[data-testid="no-results"]')).toBeVisible();
    await expect(page.locator('[data-testid="no-results"]')).toContainText('No matching photos');
  });
});
```

---

## Test Data Management

### Factories (Backend)

```python
# tests/factories.py
import factory
from factory.alchemy import SQLAlchemyModelFactory
from app.models import Photo, Album, Face, FaceCluster

class PhotoFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Photo
        sqlalchemy_session_persistence = "commit"

    id = factory.Faker('uuid4')
    filename = factory.Faker('file_name', extension='jpg')
    storage_path = factory.LazyAttribute(lambda o: f'/storage/{o.id}.jpg')
    processing_status = 'completed'
    created_at = factory.Faker('date_time_this_year')

class AlbumFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Album

    id = factory.Faker('uuid4')
    name = factory.Faker('sentence', nb_words=3)

class FaceClusterFactory(SQLAlchemyModelFactory):
    class Meta:
        model = FaceCluster

    id = factory.Faker('uuid4')
    name = factory.Faker('first_name')
```

### Fixtures (Frontend)

```typescript
// tests/fixtures/photos.ts
export const mockPhotos = [
  {
    id: '1',
    filename: 'beach.jpg',
    thumbnailUrl: '/api/photos/1/thumbnail',
    description: 'Sunny beach with palm trees',
    takenAt: '2024-06-15T10:30:00Z',
    faces: [],
  },
  // ... more fixtures
];

export const mockSearchResults = {
  results: mockPhotos.map(p => ({ photo: p, score: 0.85 })),
  total: mockPhotos.length,
};
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
      qdrant:
        image: qdrant/qdrant
        ports:
          - 6333:6333

    steps:
      - uses: actions/checkout@v4
      - uses: cachix/install-nix-action@v24
      - run: cd backend && nix-shell --run "pytest --cov=app --cov-report=xml"
      - uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: cachix/install-nix-action@v24
      - run: cd frontend && nix-shell --run "npm test"
      - run: cd frontend && nix-shell --run "npx playwright test"
```

---

## Coverage Requirements

| Component | Minimum Coverage |
|-----------|-----------------|
| Backend Services | 80% |
| Backend API Routes | 90% |
| Frontend Stores | 80% |
| Frontend Components | 70% |
| E2E Critical Paths | 100% |

### Critical Paths (Must Have 100% E2E Coverage)

1. Photo upload flow
2. Semantic search flow
3. Face tagging flow
4. Album creation and management
5. Folder registration and sync
