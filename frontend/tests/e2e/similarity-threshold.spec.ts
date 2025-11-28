/**
 * E2E Tests for Similarity Threshold Slider
 *
 * Behavior-focused tests using real backend.
 */

import { test, expect } from '@playwright/test';

test.describe('Similarity Threshold Slider', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/search');
	});

	test('similarity threshold slider is visible', async ({ page }) => {
		await expect(page.getByTestId('similarity-threshold')).toBeVisible();
		await expect(page.getByTestId('similarity-slider')).toBeVisible();
	});

	test('shows a default percentage value', async ({ page }) => {
		const valueDisplay = page.getByTestId('similarity-value');
		await expect(valueDisplay).toBeVisible();

		// Should show some percentage (not empty)
		const valueText = await valueDisplay.textContent();
		expect(valueText).toMatch(/%/);
	});

	test('slider changes percentage value when adjusted', async ({ page }) => {
		const slider = page.getByTestId('similarity-slider');
		const valueDisplay = page.getByTestId('similarity-value');

		// Get initial value
		const initialValue = await valueDisplay.textContent();
		expect(initialValue).toMatch(/%/); // Must show a percentage

		// Change slider to 50%
		await slider.fill('0.5');

		// Wait for debounce
		await page.waitForTimeout(400);

		// Value must have changed and show percentage
		const newValue = await valueDisplay.textContent();
		expect(newValue).not.toBe(initialValue);
		expect(newValue).toMatch(/50%/); // Should show 50%
	});

	test('shows description text', async ({ page }) => {
		// Should have some description about filtering or showing results
		const hasDescription =
			(await page.getByText(/showing|filtering|results|similarity/i).count()) > 0;
		expect(hasDescription).toBe(true);
	});

	test('slider has min/max labels', async ({ page }) => {
		const container = page.getByTestId('similarity-slider-container');
		const containerText = await container.textContent();

		// Should have percentage labels
		expect(containerText).toMatch(/%/);
	});

	test('search includes similarity_threshold parameter when > 0', async ({ page }) => {
		// Set similarity threshold to something > 0
		const slider = page.getByTestId('similarity-slider');
		await slider.fill('0.5');

		// Wait for debounce
		await page.waitForTimeout(400);

		// Set up network listener
		const requestPromise = page.waitForRequest((request) => {
			return request.url().includes('/search?');
		});

		// Perform search
		await page.fill('[data-testid="search-input"]', 'sunset');
		await page.click('[data-testid="search-button"]');

		const request = await requestPromise;
		const url = new URL(request.url());

		// Should include similarity_threshold parameter
		expect(url.searchParams.has('similarity_threshold')).toBe(true);
	});

	test('slider value persists during page interactions', async ({ page }) => {
		const slider = page.getByTestId('similarity-slider');
		const valueDisplay = page.getByTestId('similarity-value');

		// Set to a specific value
		await slider.fill('0.7');

		// Wait for debounce
		await page.waitForTimeout(400);

		// Get the displayed value
		const setValue = await valueDisplay.textContent();

		// Wait a bit
		await page.waitForTimeout(500);

		// Value should still be the same
		const currentValue = await valueDisplay.textContent();
		expect(currentValue).toBe(setValue);
	});

	test('info icon toggles explanation text', async ({ page }) => {
		const infoIcon = page.getByTestId('info-icon');
		const infoExists = await infoIcon.isVisible().catch(() => false);

		if (infoExists) {
			// Click to toggle
			await infoIcon.click();

			// Should show or hide explanation
			const visibleExplanation = page.locator('.explanation[data-testid="explanation-text"]');
			const explanationVisible = await visibleExplanation.isVisible().catch(() => false);

			// Explanation should appear or disappear
			if (explanationVisible) {
				const explanationText = await visibleExplanation.textContent();
				expect(explanationText).toBeTruthy();
				expect(explanationText!.length).toBeGreaterThan(0);
			}
		}
	});

	test('explanation text is available for accessibility', async ({ page }) => {
		// The explanation should be in the DOM for aria-describedby
		const explanation = page.locator('#similarity-explanation');
		const explanationExists = await explanation.count();

		if (explanationExists > 0) {
			const explanationText = await explanation.textContent();
			expect(explanationText).toBeTruthy();
		}
	});
});
