import { test, expect } from '@playwright/test';

test.describe('Similarity Threshold Slider', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/search');
	});

	test('similarity threshold slider is hidden by default', async ({ page }) => {
		await expect(page.getByTestId('similarity-slider-container')).not.toBeVisible();
	});

	test('clicking toggle shows similarity threshold slider', async ({ page }) => {
		const toggle = page.getByTestId('similarity-toggle');
		await toggle.click();

		await expect(page.getByTestId('similarity-slider-container')).toBeVisible();
		await expect(page.getByTestId('similarity-slider')).toBeVisible();
	});

	test('shows default value of 50% when enabled', async ({ page }) => {
		await page.getByTestId('similarity-toggle').click();

		const valueDisplay = page.getByTestId('similarity-value');
		await expect(valueDisplay).toContainText('50%');
	});

	test('slider updates percentage value when changed', async ({ page }) => {
		await page.getByTestId('similarity-toggle').click();

		const slider = page.getByTestId('similarity-slider');
		await slider.fill('0.8');

		const valueDisplay = page.getByTestId('similarity-value');
		await expect(valueDisplay).toContainText('80%');
	});

	test('toggling off hides the slider', async ({ page }) => {
		const toggle = page.getByTestId('similarity-toggle');

		// Enable
		await toggle.click();
		await expect(page.getByTestId('similarity-slider-container')).toBeVisible();

		// Disable
		await toggle.click();
		await expect(page.getByTestId('similarity-slider-container')).not.toBeVisible();
	});

	test('search includes similarity_threshold parameter when enabled', async ({ page }) => {
		// Enable similarity threshold
		await page.getByTestId('similarity-toggle').click();
		await page.getByTestId('similarity-slider').fill('0.75');

		// Set up network listener
		const requestPromise = page.waitForRequest((request) => {
			return request.url().includes('/search?');
		});

		// Perform search
		await page.fill('[data-testid="search-input"]', 'sunset');
		await page.click('[data-testid="search-button"]');

		const request = await requestPromise;
		const url = new URL(request.url());
		expect(url.searchParams.get('similarity_threshold')).toBe('0.75');
	});

	test('search excludes similarity_threshold when disabled', async ({ page }) => {
		// Set up network listener
		const requestPromise = page.waitForRequest((request) => {
			return request.url().includes('/search?');
		});

		// Perform search without enabling similarity threshold
		await page.fill('[data-testid="search-input"]', 'sunset');
		await page.click('[data-testid="search-button"]');

		const request = await requestPromise;
		const url = new URL(request.url());
		expect(url.searchParams.has('similarity_threshold')).toBe(false);
	});

	test('maintains threshold value when toggling on/off', async ({ page }) => {
		const toggle = page.getByTestId('similarity-toggle');
		const slider = page.getByTestId('similarity-slider');

		// Enable and set to 80%
		await toggle.click();
		await slider.fill('0.8');

		// Disable
		await toggle.click();

		// Re-enable and verify value is preserved
		await toggle.click();
		const sliderValue = await slider.inputValue();
		expect(sliderValue).toBe('0.8');
	});

	test('slider shows min/max labels', async ({ page }) => {
		await page.getByTestId('similarity-toggle').click();

		const container = page.getByTestId('similarity-slider-container');
		await expect(container.getByText('0%')).toBeVisible();
		await expect(container.getByText('100%')).toBeVisible();
	});

	test('shows description text when enabled', async ({ page }) => {
		await page.getByTestId('similarity-toggle').click();

		await expect(page.getByText(/Only show results with similarity/i)).toBeVisible();
	});
});
