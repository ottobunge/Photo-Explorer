/**
 * E2E Tests for Connectors Pages
 *
 * Behavior-focused tests using real backend.
 */

import { test, expect } from '@playwright/test';

test.describe('Connectors - List View', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/connectors');
		await page.waitForLoadState('networkidle');
	});

	test('connectors page loads without errors', async ({ page }) => {
		// Should have connectors heading
		await expect(page.getByRole('heading', { name: /Connectors/i })).toBeVisible();

		// Should not show server errors
		await expect(page.getByText(/500/i)).not.toBeVisible();
		await expect(page.getByText(/server error/i)).not.toBeVisible();
	});

	test('shows connectors or empty state', async ({ page }) => {
		// Either shows connectors OR empty state
		const hasConnectors = (await page.locator('[data-testid="connector-card"]').count()) > 0;
		const hasEmptyState = await page
			.getByText(/No connectors|Add your first/i)
			.isVisible()
			.catch(() => false);

		// Page must show content for user to interact with
		const pageText = await page.textContent('body');
		expect(pageText!.length).toBeGreaterThan(50);

		// One of these should be true (can't have both empty AND connectors)
		expect(hasConnectors || hasEmptyState).toBe(true);
	});

	test('provides way to add connectors', async ({ page }) => {
		// Must have Add Connector button or similar
		const addButton = page.getByRole('button', { name: /Add Connector/i });
		await expect(addButton).toBeVisible();
	});

	test('clicking Add Connector opens modal', async ({ page }) => {
		const addButton = page.getByRole('button', { name: /Add Connector/i });
		await addButton.click();

		// Modal must appear when clicked
		await expect(page.locator('[role="dialog"]')).toBeVisible();
	});
});

test.describe('Connectors - Navigation', () => {
	test('clicking connector navigates to detail page', async ({ page }) => {
		await page.goto('/connectors');
		await page.waitForLoadState('networkidle');

		// Should have at least one connector or skip test
		const connectorCards = page.locator('[data-testid="connector-card"]');
		const count = await connectorCards.count();

		if (count === 0) {
			test.skip();
			return;
		}

		// Click first connector
		await connectorCards.first().click();

		// Must navigate to detail page
		await page.waitForURL(/\/connectors\/[a-f0-9-]+/);

		// Detail page must show some content
		const pageText = await page.textContent('body');
		expect(pageText!.length).toBeGreaterThan(100);
	});

	test('connector detail page shows connector information', async ({ page }) => {
		await page.goto('/connectors');
		await page.waitForLoadState('networkidle');

		const connectorCards = page.locator('[data-testid="connector-card"]');
		const count = await connectorCards.count();

		if (count === 0) {
			test.skip();
			return;
		}

		await connectorCards.first().click();
		await page.waitForURL(/\/connectors\/[a-f0-9-]+/);

		// Must not show server errors
		await expect(page.getByText(/500/i)).not.toBeVisible();
		await expect(page.getByText(/server error/i)).not.toBeVisible();

		// Must show connector photos or empty state
		const hasPhotos = (await page.locator('[data-testid="photo-card"]').count()) > 0;
		const hasEmptyState = await page
			.getByText(/No photos/i)
			.isVisible()
			.catch(() => false);

		expect(hasPhotos || hasEmptyState).toBe(true);
	});

	test('handles 404 for non-existent connector gracefully', async ({ page }) => {
		// Try to access a non-existent connector
		await page.goto('/connectors/00000000-0000-0000-0000-000000000000');
		await page.waitForLoadState('networkidle');

		// Must show error message or redirect
		const hasErrorMessage = await page
			.getByText(/not found|does not exist/i)
			.isVisible()
			.catch(() => false);
		const redirectedToList = page.url().endsWith('/connectors');

		// One of these must be true (can't be blank page)
		expect(hasErrorMessage || redirectedToList).toBe(true);
	});
});

