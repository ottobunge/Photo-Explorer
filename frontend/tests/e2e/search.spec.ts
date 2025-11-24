import { test, expect } from '@playwright/test';

test.describe('Photo Search', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/search');
	});

	test('displays search page with input and button', async ({ page }) => {
		await expect(page.getByTestId('search-input')).toBeVisible();
		await expect(page.getByTestId('search-button')).toBeVisible();
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

	test('shows no results message when search returns empty', async ({ page }) => {
		// Mock empty API response
		await page.route('**/api/v1/search', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: { results: [], query_embedding_time_ms: 10, search_time_ms: 5 },
					meta: { total: 0, limit: 20, offset: 0 }
				})
			});
		});

		await page.fill('[data-testid="search-input"]', 'nonexistent');
		await page.click('[data-testid="search-button"]');

		await expect(page.getByTestId('no-results')).toBeVisible();
		await expect(page.getByText('No matching photos')).toBeVisible();
	});

	test('filter toggle shows and hides filter options', async ({ page }) => {
		const filterToggle = page.getByTestId('filter-toggle');

		// Initially filters are hidden
		await expect(page.getByTestId('date-from')).not.toBeVisible();

		// Click to show filters
		await filterToggle.click();
		await expect(page.getByTestId('date-from')).toBeVisible();
		await expect(page.getByTestId('date-to')).toBeVisible();

		// Click to hide filters
		await filterToggle.click();
		await expect(page.getByTestId('date-from')).not.toBeVisible();
	});
});
