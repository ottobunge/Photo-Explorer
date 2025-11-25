# Testing Guide for Photo Explorer Frontend

## Overview

This project uses **Playwright** for end-to-end (E2E) testing of the Svelte 5 frontend application. We adopted Playwright as our primary testing strategy due to compatibility issues with component-level unit testing libraries and Svelte 5.

### Why Playwright E2E Tests?

- **Svelte 5 Compatibility**: @testing-library/svelte has incomplete Svelte 5 support
- **Confidence**: Tests real user interactions in actual browsers
- **Behavior-Driven**: Focuses on user behavior rather than implementation details
- **Maintainability**: Less brittle than unit tests that depend on component internals

## Test Infrastructure

### Directory Structure

```
frontend/
├── tests/
│   ├── e2e/                    # E2E test files
│   │   ├── photo-navigation.spec.ts
│   │   ├── search.spec.ts
│   │   ├── settings.spec.ts
│   │   └── upload.spec.ts
│   ├── fixtures/               # Reusable test data factories
│   │   ├── photos.ts
│   │   ├── connectors.ts
│   │   └── albums.ts
│   └── helpers/                # Test utilities
│       └── api-mocks.ts        # API mocking helpers
└── playwright.config.ts
```

### Test Fixtures

Fixtures are factory functions that create consistent, reusable mock data for tests.

#### Photos Fixture (`tests/fixtures/photos.ts`)

```typescript
import { createMockPhoto, createMockPhotos } from '../fixtures/photos';

// Create a single photo with custom properties
const photo = createMockPhoto({
  id: 'test-photo-1',
  filename: 'sunset.jpg',
  connector_type: 'local',
  taken_at: '2024-01-01T12:00:00Z'
});

// Create multiple photos
const photos = createMockPhotos(5, (index) => ({
  filename: `photo-${index}.jpg`
}));

// Use pre-built scenarios
import { diversePhotos, photoWithoutThumbnail } from '../fixtures/photos';
```

**Available pre-built scenarios:**
- `completePhoto` - Photo with all fields populated
- `photoWithoutThumbnail` - Photo without thumbnail (shows placeholder)
- `googlePhoto` - Google Photos connector photo
- `localPhoto` - Local connector photo
- `uploadPhoto` - Upload connector photo
- `diversePhotos` - Collection of diverse photos

#### Search Results Fixture

```typescript
import { createMockSearchResult, createMockSearchResults } from '../fixtures/photos';

// Create a search result with score
const result = createMockSearchResult(
  { score: 0.95 },
  { filename: 'sunset.jpg' }
);

// Create multiple results
const results = createMockSearchResults(3, (index) => ({
  score: 0.9 - (index * 0.1),
  photo: { filename: `result-${index}.jpg` }
}));
```

#### Connectors Fixture (`tests/fixtures/connectors.ts`)

```typescript
import { createMockConnector } from '../fixtures/connectors';

const connector = createMockConnector({
  type: 'local',
  name: 'My Photos',
  enabled: true
});

// Pre-built scenarios
import { localConnector, googlePhotosConnector, uploadConnector } from '../fixtures/connectors';
```

#### Albums Fixture (`tests/fixtures/albums.ts`)

```typescript
import { createMockAlbum, createMockAlbums } from '../fixtures/albums';

const album = createMockAlbum({
  name: 'Summer Vacation',
  photo_count: 50
});

// Pre-built scenarios
import { diverseAlbums, emptyAlbum } from '../fixtures/albums';
```

### API Mock Helpers

API mock helpers provide consistent, reusable patterns for mocking API responses using Playwright's `page.route()`.

#### Photos API Mocks

```typescript
import { mockPhotosAPI } from '../helpers/api-mocks';

// Mock photos for homepage (per_page=12)
await mockPhotosAPI.forHomepage(page, [photo1, photo2]);

// Mock photos for search/browse page
await mockPhotosAPI.withPhotos(page, photos, { page: 1, perPage: 24, total: 100 });

// Mock empty photos response
await mockPhotosAPI.withEmpty(page);

// Mock error response
await mockPhotosAPI.withError(page, 500, 'Server Error');

// Mock loading state (delayed response)
await mockPhotosAPI.withLoading(page, photos, 2000); // 2 second delay
```

#### Search API Mocks

```typescript
import { mockSearchAPI } from '../helpers/api-mocks';

// Mock search results
await mockSearchAPI.withResults(page, 'sunset', searchResults);

// Mock empty search results
await mockSearchAPI.withEmpty(page, 'nonexistent');

// Mock search error
await mockSearchAPI.withError(page, 'sunset', 500);
```

#### Composite Mocks (Common Scenarios)

For common page scenarios, use composite mock functions that set up all required APIs:

```typescript
import {
  setupHomepageMocks,
  setupSearchPageMocks,
  setupSearchModeMocks,
  setupEmptyStateMocks
} from '../helpers/api-mocks';

// Homepage: mocks photos, connectors, albums, face clusters
await setupHomepageMocks(page, {
  photos: testPhotos,
  connectors: [localConnector],
  albums: diverseAlbums
});

// Search page (browse mode): mocks photos, connectors, albums
await setupSearchPageMocks(page, { photos: browsePhotos });

// Search page (with query): mocks search results, connectors, albums
await setupSearchModeMocks(page, 'sunset', { results: searchResults });

// Empty state: mocks all APIs with empty responses
await setupEmptyStateMocks(page);
```

## Writing E2E Tests

### Test Structure

Use the **Given-When-Then** pattern with behavior-driven test names:

```typescript
test('When user clicks photo, Then they navigate to detail page', async ({ page }) => {
  // Given: Photo cards are visible on homepage
  await expect(page.getByTestId('photo-card').first()).toBeVisible();

  // When: User clicks on the first photo
  await page.getByTestId('photo-card').first().click();

  // Then: User should navigate to the photo detail page
  await expect(page).toHaveURL(/\/photos\/test-photo-1/);
});
```

### Test Naming Convention

Format: `When [action/condition], Then [expected result]`

**Good examples:**
- `When user clicks photo, Then they navigate to detail page`
- `When photos load, Then thumbnails display with correct filenames`
- `When search returns no results, Then empty state is shown`

**Bad examples:**
- `should navigate to detail page` (not behavior-driven)
- `test photo click` (too vague)
- `clicking works` (not descriptive)

### Complete Test Example

```typescript
import { test, expect } from '@playwright/test';
import { createMockPhoto } from '../fixtures/photos';
import { setupHomepageMocks } from '../helpers/api-mocks';

test.describe('Photo Navigation - Homepage', () => {
  test.beforeEach(async ({ page }) => {
    // Set up test data using fixtures
    const testPhotos = [
      createMockPhoto({
        id: 'test-photo-1',
        filename: 'sunset.jpg',
        connector_type: 'local',
        taken_at: '2024-01-01T12:00:00Z'
      }),
      createMockPhoto({
        id: 'test-photo-2',
        filename: 'beach.jpg',
        connector_type: 'google_photos',
        taken_at: '2024-01-02T12:00:00Z'
      })
    ];

    // Mock all required APIs
    await setupHomepageMocks(page, { photos: testPhotos });

    // Navigate to page
    await page.goto('/');
  });

  test('When user views homepage, Then recent photos should be visible as clickable cards', async ({ page }) => {
    // Given: User is on the homepage
    await expect(page.getByText('Dashboard')).toBeVisible();

    // Then: Photo cards should be visible and clickable
    const photoCards = page.getByTestId('photo-card');
    await expect(photoCards).toHaveCount(2);

    // And: First photo card should be a link
    const firstCard = photoCards.first();
    await expect(firstCard).toBeVisible();
    await expect(firstCard).toHaveAttribute('href', '/photos/test-photo-1');
  });

  test('When user clicks a photo, Then they navigate to photo detail page', async ({ page }) => {
    // Given: Photo cards are visible
    await expect(page.getByTestId('photo-card').first()).toBeVisible();

    // When: User clicks on the first photo
    await page.getByTestId('photo-card').first().click();

    // Then: User should navigate to the photo detail page
    await expect(page).toHaveURL(/\/photos\/test-photo-1/);
  });
});
```

### Testing Pagination

```typescript
test('When user paginates through results, Then photos remain clickable', async ({ page }) => {
  // Given: Paginated results exist
  const page1Photo = createMockPhoto({ id: 'page1-photo', filename: 'page1.jpg' });
  const page2Photo = createMockPhoto({ id: 'page2-photo', filename: 'page2.jpg' });

  // Mock page 1
  await mockPhotosAPI.withPhotos(page, [page1Photo], { page: 1, perPage: 24, total: 50 });

  // Mock page 2
  await mockPhotosAPI.withPhotos(page, [page2Photo], { page: 2, perPage: 24, total: 50 });

  await page.goto('/search');

  // When: User navigates to page 2
  await page.getByText('Next').click();

  // Then: New photos should be clickable
  await expect(page.getByTestId('photo-card')).toHaveCount(1);
  const photoCard = page.getByTestId('photo-card').first();
  await expect(photoCard).toHaveAttribute('href', '/photos/page2-photo');
});
```

### Testing Empty States

```typescript
test('When homepage has no photos, Then empty state is shown', async ({ page }) => {
  // Given: API returns no photos
  await setupEmptyStateMocks(page);

  // When: User visits homepage
  await page.goto('/');

  // Then: Empty state should be visible
  await expect(page.getByText(/No photos yet/i)).toBeVisible();

  // And: No photo cards should exist
  await expect(page.getByTestId('photo-card')).toHaveCount(0);
});
```

### Testing Drag and Drop

```typescript
test('When files are dragged over zone, Then drag over state is shown', async ({ page }) => {
  // Given: Upload zone is visible
  const uploadZone = page.getByTestId('upload-zone');
  await expect(uploadZone).toBeVisible();
  await expect(page.getByText('Drag & drop photos here')).toBeVisible();

  // When: User drags files over the zone
  await uploadZone.dispatchEvent('dragenter');
  await uploadZone.dispatchEvent('dragover');

  // Then: Drag over state should be displayed
  await expect(page.getByText('Drop photos here')).toBeVisible();
});
```

### Testing File Upload

```typescript
test('shows selected files after selection', async ({ page }) => {
  // Create a test file
  const buffer = Buffer.from('fake image content');

  // Use file chooser
  const [fileChooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    page.getByTestId('upload-zone').click()
  ]);

  await fileChooser.setFiles({
    name: 'test-photo.jpg',
    mimeType: 'image/jpeg',
    buffer
  });

  // File should appear in the list
  await expect(page.getByText('test-photo.jpg')).toBeVisible();
});
```

## Running Tests

### All Tests

```bash
npm run test:e2e
```

### Headed Mode (see browser)

```bash
npm run test:e2e -- --headed
```

### Specific Test File

```bash
npm run test:e2e tests/e2e/photo-navigation.spec.ts
```

### Debug Mode

```bash
npm run test:e2e -- --debug
```

### UI Mode (interactive test runner)

```bash
npx playwright test --ui
```

## Best Practices

### 1. Use Fixtures and Helpers

**Bad:**
```typescript
// Manual API mocking (duplicated everywhere)
await page.route('**/api/v1/photos?per_page=12', async (route) => {
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      success: true,
      data: { photos: [{ id: '1', filename: 'test.jpg', ... }] },
      meta: { total: 1 }
    })
  });
});
```

**Good:**
```typescript
// Using fixtures and helpers (DRY, consistent, maintainable)
const testPhoto = createMockPhoto({ filename: 'test.jpg' });
await mockPhotosAPI.forHomepage(page, [testPhoto]);
```

### 2. Test User Behavior, Not Implementation

**Bad:**
```typescript
test('component renders correctly', async ({ page }) => {
  // Testing implementation details
  const component = page.locator('.photo-card-component');
  expect(component).toBeTruthy();
});
```

**Good:**
```typescript
test('When user views homepage, Then photos are visible and clickable', async ({ page }) => {
  // Testing user-facing behavior
  await expect(page.getByTestId('photo-card')).toBeVisible();
  await page.getByTestId('photo-card').first().click();
  await expect(page).toHaveURL(/\/photos\//);
});
```

### 3. Use Descriptive Test IDs

Add `data-testid` attributes to important elements in components:

```svelte
<!-- PhotoCard.svelte -->
<a href="/photos/{photo.id}" data-testid="photo-card">
  <img src={photo.thumbnail_url} alt={photo.filename} />
  <p>{photo.filename}</p>
</a>
```

Then in tests:
```typescript
await page.getByTestId('photo-card').click();
```

### 4. Organize Tests by Feature

Group related tests in `test.describe` blocks:

```typescript
test.describe('Photo Navigation - Homepage', () => {
  // All homepage navigation tests
});

test.describe('Photo Navigation - Search Page', () => {
  // All search page navigation tests
});
```

### 5. Use beforeEach for Common Setup

```typescript
test.describe('Photo Search', () => {
  test.beforeEach(async ({ page }) => {
    // Common setup for all tests in this describe block
    await setupSearchPageMocks(page);
    await page.goto('/search');
  });

  test('test 1', async ({ page }) => { /* ... */ });
  test('test 2', async ({ page }) => { /* ... */ });
});
```

### 6. Wait for Elements, Don't Use Timeouts

**Bad:**
```typescript
await page.waitForTimeout(1000); // Arbitrary wait
await expect(element).toBeVisible();
```

**Good:**
```typescript
await expect(element).toBeVisible(); // Built-in waiting
```

### 7. Test Error States

Don't just test happy paths:

```typescript
test('When search API fails, Then error message is shown', async ({ page }) => {
  await mockSearchAPI.withError(page, 'sunset', 500);
  await page.goto('/search?q=sunset');
  await expect(page.getByText(/Something went wrong/i)).toBeVisible();
});
```

## Common Patterns

### Testing Modal Dialogs

```typescript
test('opens Add Folder modal when clicking Add Folder', async ({ page }) => {
  await page.getByRole('button', { name: /Add Folder/i }).click();

  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByText('Add Local Folder')).toBeVisible();
  await expect(page.getByLabel('Folder Path')).toBeVisible();
});

test('can close Add Folder modal', async ({ page }) => {
  await page.getByRole('button', { name: /Add Folder/i }).click();
  await expect(page.getByRole('dialog')).toBeVisible();

  await page.getByRole('button', { name: 'Cancel' }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
});
```

### Testing Form Interactions

```typescript
test('search button is disabled when input is empty', async ({ page }) => {
  const searchButton = page.getByTestId('search-button');
  await expect(searchButton).toBeDisabled();
});

test('search button is enabled when input has text', async ({ page }) => {
  await page.fill('[data-testid="search-input"]', 'sunset');
  const searchButton = page.getByTestId('search-button');
  await expect(searchButton).toBeEnabled();
});
```

### Testing Keyboard Accessibility

```typescript
test('upload zone accepts keyboard interaction', async ({ page }) => {
  const uploadZone = page.getByTestId('upload-zone');
  await uploadZone.focus();

  // Should be focusable
  await expect(uploadZone).toBeFocused();
});

test('user can tab to photos and press Enter', async ({ page }) => {
  const photoCard = page.getByTestId('photo-card').first();
  await photoCard.focus();
  await page.keyboard.press('Enter');

  await expect(page).toHaveURL(/\/photos\//);
});
```

## Troubleshooting

### Tests timing out

- Increase timeout in `playwright.config.ts`
- Check that API mocks are set up before navigation
- Use `await expect(...).toBeVisible()` instead of `waitForTimeout`

### Element not found

- Ensure API mocks return data before `page.goto()`
- Use `await expect(element).toBeVisible()` to wait for element
- Check element selector (test ID, role, text)

### Flaky tests

- Avoid `waitForTimeout()` - use built-in waiting
- Set up API mocks before navigation
- Use more specific selectors
- Check for race conditions in component rendering

### Mock not working

- Ensure mock is set up **before** `page.goto()`
- Check URL pattern matches actual API call
- Verify response structure matches backend API

## Migration Guide

### Converting Unit Tests to E2E

If you have existing unit tests, follow this pattern:

| Unit Test | E2E Test |
|-----------|----------|
| `vi.mocked(client.get)` | `await page.route('**/api/...')` or use helpers |
| `render(Component)` | `await page.goto('/route')` |
| `screen.getByTestId()` | `page.getByTestId()` |
| `expect().toHaveLength()` | `await expect().toHaveCount()` |
| `expect().toBeInTheDocument()` | `await expect().toBeVisible()` |
| `fireEvent.click()` | `await element.click()` |
| `component.$on('event', handler)` | Test the result of the event in the UI |

**Example conversion:**

Unit test:
```typescript
it('shows photo count', () => {
  vi.mocked(client.get).mockResolvedValue({ data: { photos: [photo1, photo2] } });
  render(HomePage);
  expect(screen.getByText('2 photos')).toBeInTheDocument();
});
```

E2E test:
```typescript
test('When homepage loads, Then photo count is displayed', async ({ page }) => {
  await setupHomepageMocks(page, { photos: [photo1, photo2] });
  await page.goto('/');
  await expect(page.getByText('2 photos')).toBeVisible();
});
```

## Resources

- [Playwright Documentation](https://playwright.dev/)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Test Fixtures Pattern](https://playwright.dev/docs/test-fixtures)
- [Behavior-Driven Testing](https://cucumber.io/docs/bdd/)
