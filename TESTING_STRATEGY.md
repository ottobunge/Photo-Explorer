# Testing Strategy

Photo Explorer follows a comprehensive testing pyramid approach with three distinct layers of tests.

## Testing Pyramid

```
        /\
       /  \     E2E Tests (Playwright)
      /____\    ↑ Real infrastructure, real data
     /      \   Integration Tests (Playwright/Vitest)
    /________\  ↑ Real components, mocked API
   /__________\ Unit Tests (Vitest)
                ↑ Isolated components, full mocks
```

## Test Layers

### 1. Unit Tests (Component Level)

**Location**: Co-located with components (e.g., `SearchBar.test.ts` next to `SearchBar.svelte`)

**Purpose**: Test individual components in isolation

**Characteristics**:
- ✅ Use mocks for all external dependencies
- ✅ Fast execution (milliseconds)
- ✅ Test component logic, state management, event handling
- ✅ High code coverage target: 80%

**Tools**: Vitest + Testing Library

**Example**:
```typescript
// src/lib/features/search/components/SearchBar.test.ts
import { render, fireEvent } from '@testing-library/svelte';
import SearchBar from './SearchBar.svelte';

test('calls onSearch when search button clicked', async () => {
  const onSearch = vi.fn();
  const { getByTestId } = render(SearchBar, { onSearch });

  await fireEvent.click(getByTestId('search-button'));

  expect(onSearch).toHaveBeenCalled();
});
```

**Run**:
```bash
cd frontend
npm test
```

### 2. Integration Tests (Page Level)

**Location**: `frontend/tests/integration/`

**Purpose**: Test page-level interactions with mocked API responses

**Characteristics**:
- ✅ Use real components
- ✅ Mock API responses (route interception)
- ✅ Test user workflows within a page
- ✅ Medium execution time (seconds)
- ✅ Coverage target: 70%

**Tools**: Playwright with route mocking

**Example**:
```typescript
// frontend/tests/integration/search-page.spec.ts
test('search page shows results', async ({ page }) => {
  // Mock API response
  await page.route('/api/v1/search*', route => {
    route.fulfill({
      json: {
        success: true,
        data: { results: [/* mock data */] }
      }
    });
  });

  await page.goto('/search');
  await page.fill('[data-testid="search-input"]', 'sunset');
  await page.click('[data-testid="search-button"]');

  // Verify UI shows mocked results
  await expect(page.getByText('sunset.jpg')).toBeVisible();
});
```

**Run**:
```bash
cd frontend
npm run test:integration
```

### 3. E2E Tests (Full System)

**Location**: `frontend/tests/e2e/`

**Purpose**: Test complete user workflows against real infrastructure

**Characteristics**:
- ✅ Real backend API
- ✅ Real database (PostgreSQL)
- ✅ Real vector store (Qdrant)
- ✅ Real ML workers (Celery)
- ✅ Real data (seeded from fixtures)
- ❌ No mocks
- ⏱️  Slow execution (minutes)
- 🎯 Coverage target: 100% of critical user flows

**Tools**: Playwright against real services

**Example**:
```typescript
// frontend/tests/e2e/search-flow.spec.ts
test('user can search for photos by semantic query', async ({ page }) => {
  // This hits the REAL backend API
  await page.goto('/search');
  await page.fill('[data-testid="search-input"]', 'sunset on beach');
  await page.click('[data-testid="search-button"]');

  // Verify REAL search results from Qdrant
  await expect(page.locator('.photo-card').first()).toBeVisible();

  // Verify search result has similarity score
  const score = await page.locator('.photo-card').first().getAttribute('data-score');
  expect(parseFloat(score)).toBeGreaterThan(0);
});
```

**Run**:
```bash
# From project root
./run-e2e-tests.sh
```

## E2E Test Infrastructure

### Prerequisites

The E2E test script (`run-e2e-tests.sh`) automatically handles:

1. **Test Infrastructure Setup**
   - Starts PostgreSQL (test database)
   - Starts Qdrant (test vector store)
   - Starts Redis (test task queue)
   - Runs database migrations

2. **Backend Services**
   - Starts FastAPI backend
   - Starts Celery worker
   - Waits for services to be healthy

3. **Test Data Seeding**
   - Registers example connector
   - Seeds test photos
   - Waits for ML processing to complete

4. **Frontend Dev Server**
   - Starts Vite dev server
   - Waits for server to be ready

### Smart Execution

The script checks each step before executing:
- ✅ Infrastructure already running? → Skip startup
- ✅ Backend already running? → Skip startup
- ✅ Data already seeded? → Skip seeding
- ✅ Frontend already running? → Skip startup

This makes re-runs fast when infrastructure is already up.

### Manual Control

You can also run each step manually:

```bash
# 1. Start test infrastructure
docker compose -f docker-compose.test.yml up -d

# 2. Start backend
cd backend
poetry run alembic upgrade head
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
poetry run celery -A app.infrastructure.celery.app worker &

# 3. Seed test data (if needed)
poetry run python scripts/seed_test_data.py

# 4. Start frontend
cd ../frontend
npm run dev &

# 5. Run E2E tests
nix-shell --run "npm run test:e2e"
```

## Test Configuration

### Playwright Configuration

The Playwright config (`frontend/playwright.config.ts`) is environment-aware:

```typescript
export default defineConfig({
  // Use real backend for E2E tests
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
    apiURL: process.env.E2E_API_URL || 'http://localhost:8000',
  },

  webServer: {
    // Don't start dev server for E2E (run-e2e-tests.sh handles it)
    command: process.env.CI ? 'npm run build && npm run preview' : undefined,
    port: 5173,
    reuseExistingServer: true, // Allow external server
  },
});
```

### Environment Variables

**E2E Tests**:
- `E2E_BASE_URL` - Frontend URL (default: http://localhost:5173)
- `E2E_API_URL` - Backend API URL (default: http://localhost:8000)

**Integration Tests**:
- `MOCK_API=true` - Enable API mocking

## Critical User Flows (E2E Coverage Required)

These workflows MUST have 100% E2E test coverage:

1. ✅ **Photo Upload & Processing**
   - Upload photo
   - Verify ML processing (CLIP embedding, face detection)
   - Verify photo appears in gallery

2. ✅ **Semantic Search**
   - Search with text query
   - Verify vector search results
   - Verify similarity scores
   - Apply similarity threshold filter

3. ✅ **Face Recognition Flow**
   - Face detection on uploaded photo
   - Face clustering
   - Name assignment
   - Search by person name

4. ✅ **Album Management**
   - Create album
   - Add photos to album
   - View album
   - Search within album

5. ✅ **Connector Management**
   - Register connector (local/Google Photos)
   - Sync photos from connector
   - Monitor sync progress

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up test infrastructure
        run: docker compose -f docker-compose.test.yml up -d

      - name: Run E2E tests
        run: ./run-e2e-tests.sh

      - name: Upload test results
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

## Best Practices

### Unit Tests

✅ **DO**:
- Test component behavior, not implementation
- Use descriptive test names: `test('shows error when query is empty')`
- Mock all external dependencies
- Test edge cases and error states

❌ **DON'T**:
- Test internal implementation details
- Make tests depend on each other
- Use real API calls
- Test framework internals

### Integration Tests

✅ **DO**:
- Test realistic user workflows
- Mock API responses with realistic data
- Test loading states and error handling
- Use route interception for API mocking

❌ **DON'T**:
- Test individual component logic (that's unit tests)
- Use real backend (that's E2E)
- Test every possible combination (focus on common paths)

### E2E Tests

✅ **DO**:
- Test complete user journeys
- Use real data that matches production scenarios
- Test critical business flows
- Verify actual backend responses
- Test error scenarios (500 errors, network failures)

❌ **DON'T**:
- Test every UI variation (that's integration tests)
- Use mocks or fixtures
- Test implementation details
- Make tests flaky (use proper waits)

## Debugging Tests

### Unit Tests
```bash
npm test -- --ui  # Interactive UI mode
```

### Integration Tests
```bash
npm run test:integration -- --headed  # See browser
npm run test:integration -- --debug   # Debug mode
```

### E2E Tests
```bash
npm run test:e2e -- --headed          # See browser
npm run test:e2e -- --debug            # Debug mode
npm run test:e2e:ui                    # Playwright UI mode
```

## Test Data Management

### Fixtures

Test fixtures are stored in:
- `backend/tests/fixtures/` - Backend test data
- `frontend/tests/fixtures/` - Frontend test data

Example photos for E2E tests:
- `backend/tests/fixtures/example_photos/` - Sample images
- Each photo has metadata (EXIF, location, etc.)
- Includes various scenarios (faces, landscapes, objects)

### Seeding

The E2E test script automatically seeds:
1. Example connector pointing to fixture photos
2. Triggers ML processing (CLIP embeddings, face detection)
3. Waits for processing to complete

## NixOS Considerations

### Playwright in NixOS

The project uses NixOS-compatible Playwright setup:

```nix
# frontend/shell.nix
{
  buildInputs = [ playwright-driver.browsers ];

  shellHook = ''
    export PLAYWRIGHT_BROWSERS_PATH="${pkgs.playwright-driver.browsers}"
    export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
  '';
}
```

**Important**: Playwright version in `package.json` must match nixpkgs version:
```json
{
  "devDependencies": {
    "@playwright/test": "1.52.0"  // Must match nixpkgs playwright-driver version
  }
}
```

## Summary

- **Unit Tests**: Fast, isolated, mocked dependencies
- **Integration Tests**: Medium speed, real components, mocked API
- **E2E Tests**: Slow, full system, real infrastructure, NO MOCKS

This ensures:
- Fast feedback loop (unit tests)
- Confidence in component integration (integration tests)
- Verification of real system behavior (E2E tests)
