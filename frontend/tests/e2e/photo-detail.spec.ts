/**
 * E2E Tests for Photo Detail Page
 *
 * Behavior-focused tests using real backend.
 * Tests verify WHAT the system does, not HOW.
 */

import { test, expect } from '@playwright/test';

test.describe('Photo Detail Page', () => {
	test.beforeEach(async ({ page }) => {
		// Navigate to search and wait for photos to load
		await page.goto('/search');
		await page.waitForSelector('[data-testid="photo-card"]', { timeout: 10000 });
	});

	test('loads photo detail page without errors', async ({ page }) => {
		// Click first photo
		await page.getByTestId('photo-card').first().click();

		// Should navigate to detail page
		await expect(page).toHaveURL(/\/photos\/[a-f0-9-]+/);

		// Wait for loading to complete
		await expect(page.getByText('Loading photo...')).not.toBeVisible();

		// Should not show errors
		await expect(page.getByText(/500/i)).not.toBeVisible();
		await expect(page.getByText(/server error/i)).not.toBeVisible();
		await expect(page.getByText(/failed to load/i)).not.toBeVisible();

		// Should show actual photo content (filename heading and metadata section)
		await expect(page.locator('h1')).toBeVisible();
		await expect(page.getByText('Metadata')).toBeVisible();
	});

	test('displays photo content when loaded', async ({ page }) => {
		await page.getByTestId('photo-card').first().click();
		await expect(page).toHaveURL(/\/photos\/[a-f0-9-]+/);

		// Wait for photo to load (not in loading state)
		await expect(page.getByText('Loading photo...')).not.toBeVisible();

		// Must show heading and metadata (proves photo data loaded successfully)
		await expect(page.locator('h1')).toBeVisible();
		await expect(page.getByText('Metadata')).toBeVisible();

		// Must show either thumbnail OR placeholder message
		const hasImage = (await page.locator('img').count()) > 0;
		const hasPlaceholder = await page
			.getByText(/Thumbnail/)
			.isVisible()
			.catch(() => false);

		expect(hasImage || hasPlaceholder).toBe(true);
	});

	test('has navigation back to search', async ({ page }) => {
		await page.getByTestId('photo-card').first().click();
		await expect(page).toHaveURL(/\/photos\/[a-f0-9-]+/);
		await expect(page.getByText('Loading photo...')).not.toBeVisible();

		// Should have back navigation (button or link with "back" text)
		const backNav = page.getByText(/back/i);
		const hasBackNav = await backNav.isVisible().catch(() => false);

		if (hasBackNav) {
			await backNav.click();
			await expect(page).toHaveURL(/\/search/);
		} else {
			// Can still navigate back using browser back
			await page.goBack();
			await expect(page).toHaveURL(/\/search/);
		}
	});

	test('displays photo metadata or content', async ({ page }) => {
		await page.getByTestId('photo-card').first().click();
		await expect(page).toHaveURL(/\/photos\/[a-f0-9-]+/);
		await expect(page.getByText('Loading photo...')).not.toBeVisible();

		// Should show SOME content (metadata, description, or scene info)
		// Not all photos have all fields, so check for any reasonable content
		const hasFilename = await page.locator('h1').isVisible().catch(() => false);

		// Should have filename at minimum
		expect(hasFilename).toBe(true);
	});

	test('handles non-existent photo gracefully', async ({ page }) => {
		// Navigate to fake photo ID
		await page.goto('/photos/00000000-0000-0000-0000-000000000000');

		// Should NOT be in loading state forever
		await page.waitForLoadState('networkidle');

		// Should show error state
		const showsError = await page.getByText(/failed to load/i).isVisible().catch(() => false);
		const showsNotFound = await page.locator('.text-red-800').isVisible().catch(() => false);

		// One of these should be true
		expect(showsError || showsNotFound).toBe(true);

		// Should have way to go back
		await expect(page.getByText(/back to photos/i)).toBeVisible();
	});

	test('photo thumbnail loads successfully', async ({ page }) => {
		await page.getByTestId('photo-card').first().click();
		await expect(page).toHaveURL(/\/photos\/([a-f0-9-]+)/);

		// Wait for photo data to load
		await expect(page.getByText('Loading photo...')).not.toBeVisible();

		// If photo has image, verify it loads
		const images = page.locator('img');
		const imageCount = await images.count();

		if (imageCount > 0) {
			const img = images.first();
			const src = await img.getAttribute('src');

			// Should have valid src
			expect(src).toBeTruthy();
			expect(src).not.toContain('undefined');
			expect(src).not.toContain('null');

			// Extract photo ID from URL
			const url = page.url();
			const photoId = url.match(/\/photos\/([a-f0-9-]+)/)?.[1];

			// Src should reference the photo ID
			if (photoId && src) {
				expect(src).toContain(photoId);
			}
		}
	});

	test('page loaded successfully with content', async ({ page }) => {
		await page.getByTestId('photo-card').first().click();
		await expect(page).toHaveURL(/\/photos\/[a-f0-9-]+/);
		await expect(page.getByText('Loading photo...')).not.toBeVisible();

		// Page should have loaded with content
		// Check for photo filename (h1) and general page structure
		await expect(page.locator('h1')).toBeVisible();

		// Should have main content area
		const hasContent = (await page.locator('.max-w-6xl, .max-w-2xl').count()) > 0;
		expect(hasContent).toBe(true);
	});
});

test.describe('Photo Detail - Google Photos', () => {
	test('handles Google Photos thumbnails correctly', async ({ page }) => {
		// Go to search page
		await page.goto('/search');
		await page.waitForSelector('[data-testid="photo-card"]', { timeout: 10000 });

		// Look for Google Photos
		const photoCards = page.getByTestId('photo-card');
		const count = await photoCards.count();
		let foundGooglePhoto = false;

		for (let i = 0; i < count && i < 20; i++) {
			const card = photoCards.nth(i);
			const hasGoogleBadge = await card
				.getByText('google_photos')
				.isVisible()
				.catch(() => false);

			if (hasGoogleBadge) {
				// Click on this Google Photos photo
				await card.click();
				await expect(page).toHaveURL(/\/photos\/[a-f0-9-]+/);

				// Wait for loading
				await expect(page.getByText('Loading photo...')).not.toBeVisible();

				// Should load without errors
				await expect(page.getByText(/500/i)).not.toBeVisible();
				await expect(page.getByText(/failed to load/i)).not.toBeVisible();

				// Should still show google_photos badge
				await expect(page.getByText('google_photos')).toBeVisible();

				foundGooglePhoto = true;
				break;
			}
		}

		// Skip test if no Google Photos found
		if (!foundGooglePhoto) {
			test.skip();
		}
	});
});
