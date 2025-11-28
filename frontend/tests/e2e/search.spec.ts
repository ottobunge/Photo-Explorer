/**
 * E2E Tests for Search Page
 *
 * Behavior-focused tests using real backend.
 */

import { test, expect } from '@playwright/test';

test.describe('Photo Search', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/search');
	});

	test('search page loads without errors', async ({ page }) => {
		// Should have search input and button
		await expect(page.getByTestId('search-input')).toBeVisible();
		await expect(page.getByTestId('search-button')).toBeVisible();

		// Should not show server errors
		await expect(page.getByText(/500/i)).not.toBeVisible();
		await expect(page.getByText(/server error/i)).not.toBeVisible();
	});

	test('search button is disabled when input is empty', async ({ page }) => {
		const searchButton = page.getByTestId('search-button');
		await expect(searchButton).toBeDisabled();
	});

	test('search button is enabled when input has text', async ({ page }) => {
		await page.fill('[data-testid="search-input"]', 'sunset');
		const searchButton = page.getByTestId('search-button');
		await expect(searchButton).toBeEnabled();
	});

	test('filter toggle shows and hides filter options', async ({ page }) => {
		const filterToggle = page.getByTestId('filter-toggle');

		// Initially filters might be hidden or shown (depends on state)
		// Just test that toggle works
		const initiallyVisible = await page
			.getByTestId('date-from')
			.isVisible()
			.catch(() => false);

		// Click to toggle
		await filterToggle.click();
		const afterFirstClick = await page
			.getByTestId('date-from')
			.isVisible()
			.catch(() => false);

		// State should have changed
		expect(afterFirstClick).not.toBe(initiallyVisible);

		// Click again to toggle back
		await filterToggle.click();
		const afterSecondClick = await page
			.getByTestId('date-from')
			.isVisible()
			.catch(() => false);

		// Should be back to initial state
		expect(afterSecondClick).toBe(initiallyVisible);
	});

	test('search returns results and displays them', async ({ page }) => {
		// Type a search query
		await page.fill('[data-testid="search-input"]', 'photo');
		await page.click('[data-testid="search-button"]');

		// Wait for search to complete
		await page.waitForLoadState('networkidle');

		// Must show either results OR no results message
		const hasResults = (await page.locator('[data-testid="photo-card"]').count()) > 0;
		const hasNoResults = await page.getByTestId('no-results').isVisible().catch(() => false);

		// One of these must be true (can't be blank page)
		expect(hasResults || hasNoResults).toBe(true);

		// Verify no errors occurred
		await expect(page.getByText(/500/i)).not.toBeVisible();
		await expect(page.getByText(/server error/i)).not.toBeVisible();
	});
});
