# E2E Test Coverage

This directory contains comprehensive end-to-end tests for the Photo Explorer frontend. All tests use the **REAL backend** - no mocks or fixtures.

## Coverage Overview

### Complete Page Coverage

| Page | Test File | Status | Coverage |
|------|-----------|--------|----------|
| **Homepage** (`/`) | `critical-flows.spec.ts` | ✅ | Navigation, initial load |
| **Search** (`/search`) | `search.spec.ts`, `similarity-threshold.spec.ts`, `search-page-integration.spec.ts` | ✅ | Search, filters, threshold, pagination |
| **Photo Detail** (`/photos/[id]`) | `photo-detail.spec.ts`, `photo-navigation.spec.ts` | ✅ | Details, thumbnails, navigation, metadata |
| **Upload** (`/upload`) | `upload.spec.ts` | ✅ | File selection, upload flow, validation |
| **Connectors** (`/connectors`, `/connectors/[id]`) | `connectors.spec.ts` | ✅ | List, create, detail, sync |
| **Settings** (`/settings`) | `settings.spec.ts` | ✅ | Settings page, folders, configuration |
| **Albums** (`/albums`) | `albums.spec.ts` | ✅ | List, create, detail, navigation |
| **Faces** (`/faces`, `/faces/[id]`) | `faces.spec.ts` | ✅ | Face clusters, detail, naming |

### Test Files

#### Core Functionality

**`critical-flows.spec.ts`**
- Critical user journeys end-to-end
- Homepage navigation
- Photo browsing flow
- Connector setup flow

**`search.spec.ts`**
- Search functionality
- Filter toggling
- Empty states

**`similarity-threshold.spec.ts`**
- Similarity threshold slider
- URL parameter synchronization
- Description updates
- Debouncing behavior
- Persistence across navigation

**`search-page-integration.spec.ts`**
- Search integration tests
- Filter combinations
- URL state management

#### Photo Management

**`photo-detail.spec.ts`** (NEW)
- Photo detail page loads without 500 errors
- Thumbnail display (local and Google Photos)
- Metadata display
- Navigation (back button)
- Processing status badges
- Connector type badges
- 404 error handling
- Thumbnail endpoint validation

**`photo-navigation.spec.ts`**
- Photo card clicks
- Navigation between photos
- Breadcrumbs

**`upload.spec.ts`**
- File selection
- File validation
- Upload button states
- Clear all functionality

#### Connectors

**`connectors.spec.ts`**
- Connectors list page
- Add connector flow
- Connector cards display
- Status indicators
- Detail view
- Photo listings per connector

**Note on Google Photos:**
- Google Photos tests are included in `photo-detail.spec.ts`
- Tests automatically skip if no Google Photos are available
- Uses `test.skip()` for optional Google Photos testing

#### Settings & Organization

**`settings.spec.ts`**
- Settings page display
- Google Photos section
- Local Folders section
- Add Folder modal
- Settings navigation

**`albums.spec.ts`** (NEW)
- Albums list page loads
- Create album button
- Create album modal (open/close)
- Albums grid display
- Album cards structure
- Navigate to album detail
- Pagination support
- Navigation from sidebar

**`faces.spec.ts`** (NEW)
- Faces list page loads
- Face clusters display
- Thumbnail images
- Click to view details
- Face detail page
- Photos of person
- Back navigation
- Person naming feature
- Navigation from sidebar

## BDD with Gherkin (NEW)

This project now supports **Behavior-Driven Development (BDD)** using Gherkin feature files via `playwright-bdd`.

### Directory Structure

```
tests/e2e/
├── features/              # Gherkin feature files
│   ├── photo-search.feature
│   └── photo-upload.feature
├── steps/                 # Step definitions
│   ├── search.steps.ts
│   └── common.steps.ts
├── fixtures.ts            # Custom Playwright fixtures
└── *.spec.ts             # Legacy Playwright tests
```

### Writing Feature Files

Feature files use plain English to describe user behaviors:

```gherkin
Feature: Photo Search
  As a user
  I want to search for photos using text queries
  So that I can quickly find relevant photos in my collection

  Background:
    Given I am on the search page

  Scenario: Search returns matching photos
    When I enter "sunset" in the search field
    And I click the search button
    And I wait for the search to complete
    Then I should see either photo results or a no results message
    And I should not see any server errors
```

### Implementing Step Definitions

Steps are implemented in TypeScript using `@cucumber/cucumber`:

```typescript
import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';

Given('I am on the search page', async ({ page }) => {
  await page.goto('/search');
});

When('I enter {string} in the search field', async ({ page }, query: string) => {
  await page.fill('[data-testid="search-input"]', query);
});

Then('I should see either photo results or a no results message', async ({ page }) => {
  const hasResults = (await page.locator('[data-testid="photo-card"]').count()) > 0;
  const hasNoResults = await page.getByTestId('no-results').isVisible().catch(() => false);
  expect(hasResults || hasNoResults).toBe(true);
});
```

### Reusing Common Steps

Create reusable steps in `common.steps.ts`:

```typescript
import { Given, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';

Then('I should not see any server errors', async ({ page }) => {
  await expect(page.getByText(/500/i)).not.toBeVisible();
  await expect(page.getByText(/server error/i)).not.toBeVisible();
});
```

Use these steps in multiple feature files.

## Running Tests

### Run All E2E Tests (including BDD)
```bash
npm run test:e2e
# or
npx playwright test
```

### Run Only BDD Feature Files
```bash
npx playwright test tests/e2e/features/
```

### Run Specific Feature File
```bash
npx playwright test tests/e2e/features/photo-search.feature
```

### Run Specific Test File
```bash
npx playwright test tests/e2e/photo-detail.spec.ts
```

### Run in UI Mode (Interactive)
```bash
npx playwright test --ui
```

### Run with Reporter
```bash
npx playwright test --reporter=html
```

### Run Only Chromium
```bash
npx playwright test --project=chromium
```

## Test Principles

### 1. Real Backend Only
- **NO mocks or fixtures**
- Tests catch actual backend errors (500, 404, etc.)
- Validates real API contracts
- Tests real data flows

### 2. Behavior-Focused
Tests verify **WHAT** the system does and **WHAT the user sees**, not **HOW** it works internally:
```typescript
// ✅ GOOD - Tests actual behavior and outcome
test('photo detail page shows photo information', async ({ page }) => {
  await page.goto('/photos/123');
  await expect(page.getByText(/500/i)).not.toBeVisible();
  // Verify actual content is shown
  await expect(page.locator('h1')).toBeVisible();
  await expect(page.getByText('Metadata')).toBeVisible();
});

// ❌ BAD - Too vague, doesn't verify actual content
test('photo detail page loads', async ({ page }) => {
  await page.goto('/photos/123');
  const hasContent = (await page.locator('div').count()) > 0;
  expect(hasContent).toBe(true); // Just checks "something" exists
});

// ❌ BAD - Tests implementation details
test('photo service calls API with correct headers', async ({ page }) => {
  // Testing internal implementation details
});
```

**Key Principle**: If a user would notice it's broken, the test should catch it. Tests should verify the **outcome** of behaviors, not just that code ran without errors.

### 3. Robust Selectors
- Prefer `getByRole()` and `getByTestId()`
- Avoid fragile CSS selectors
- Use semantic HTML where possible

### 4. Error Handling
Every test checks for:
- 500 errors
- Failed to load messages
- Timeout handling
- Empty states

### 5. Skip When Appropriate
Tests skip gracefully when:
- No data exists (e.g., no albums, no faces)
- Optional features not available (e.g., Google Photos)

Example:
```typescript
if (count === 0) {
  test.skip();
  return;
}
```

## Test Statistics

All E2E tests have been simplified to focus on **behavior over implementation**:
- **52 behavior-focused tests** across 8 test files
- Tests verify WHAT the system does, not HOW it does it
- All tests use the **real backend** - no mocks or fixtures
- Tests are resilient to UI changes and focus on user-visible behavior

## Coverage Gaps

Currently all major pages are covered. Additional tests could be added for:
- Album detail page interactions
- Face merging/splitting
- Batch operations
- Advanced search filters
- Settings persistence

## Adding New Tests

When adding new pages or features:

1. Create a new `*.spec.ts` file in `tests/e2e/`
2. Follow the existing patterns:
   - Use `test.describe()` to group related tests
   - Use `test.beforeEach()` for common setup
   - Check for errors in every test
   - Use semantic selectors
   - Skip when appropriate

3. Test structure template:
```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/feature');
  });

  test('feature loads without errors', async ({ page }) => {
    await expect(page.getByRole('heading')).toBeVisible();
    await expect(page.getByText(/500/i)).not.toBeVisible();
  });

  // More tests...
});
```

## CI/CD Integration

Tests are designed to run in CI:
- Use `PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS` for NixOS
- Tests are stateless and can run in parallel
- Each test cleans up after itself (when applicable)

## Debugging Failed Tests

1. **Run with UI mode**: `npx playwright test --ui`
2. **View test artifacts**: Check `test-results/` for screenshots
3. **Use headed mode**: `npx playwright test --headed`
4. **Debug specific test**: `npx playwright test -g "test name" --debug`

## Google Photos Testing

Google Photos integration tests are **optional**:

- Located in `photo-detail.spec.ts`
- Automatically skip if no Google Photos connectors exist
- Test validates thumbnails load correctly for remote photos
- Uses real backend (no OAuth mocking required)

To enable Google Photos tests:
1. Set up a Google Photos connector in the app
2. Sync some photos
3. Run tests normally - they'll detect Google Photos and test them

## Best Practices

### General Testing

✅ **DO**:
- Test user-visible behavior
- Use real backend
- Check for errors
- Skip when data doesn't exist
- Use semantic selectors
- Test critical paths thoroughly

❌ **DON'T**:
- Mock API responses (use real backend)
- Test implementation details
- Use fragile CSS selectors
- Make tests dependent on specific data
- Skip error checking
- Test non-critical UI details

### BDD/Gherkin Best Practices

✅ **DO**:
- Write scenarios from the user's perspective
- Use business language, not technical jargon
- Keep scenarios focused on one behavior
- Reuse step definitions across features
- Use Background for common setup
- Use Examples/Scenario Outline for data-driven tests

**Example - Good Scenario**:
```gherkin
Scenario: User searches for beach photos
  Given I am on the search page
  When I enter "beach sunset" in the search field
  And I click the search button
  Then I should see photos related to beaches
  And I should not see any errors
```

❌ **DON'T**:
- Write technical implementation details in scenarios
- Make scenarios too long (split into multiple scenarios)
- Duplicate step definitions
- Test internal state or implementation
- Use technical terms users wouldn't understand

**Example - Bad Scenario**:
```gherkin
# BAD - Too technical, tests implementation
Scenario: API returns 200 with photo array
  Given the search API is available
  When I POST to /api/search with {"query": "beach"}
  Then the response status should be 200
  And the response body should contain an array
  And each array item should have id, filename, url
```

### When to Use BDD vs Regular Playwright Tests

**Use BDD/Gherkin (.feature files) for**:
- Critical user flows that need stakeholder visibility
- Features that change frequently (living documentation)
- User acceptance criteria
- Cross-functional team communication

**Use Regular Playwright (.spec.ts files) for**:
- Technical edge cases
- Error handling and validation
- UI component behavior
- Performance testing
- When tests don't need non-technical readability

## Maintenance

Tests should be updated when:
- New pages are added
- Critical user flows change
- API contracts change
- UI structure significantly changes

Keep tests:
- Simple and readable
- Focused on one behavior each
- Independent (no test dependencies)
- Fast (avoid unnecessary waits)
