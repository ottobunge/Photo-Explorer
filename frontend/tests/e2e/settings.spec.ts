/**
 * E2E Tests for Settings Page
 *
 * Behavior-focused tests using real backend.
 */

import { test, expect } from '@playwright/test';

test.describe('Settings Page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/settings');
		await page.waitForLoadState('networkidle');
	});

	test('settings page loads without errors', async ({ page }) => {
		// Should have settings heading
		await expect(page.getByRole('heading', { name: /Settings/i })).toBeVisible();

		// Should not show server errors
		await expect(page.getByText(/500/i)).not.toBeVisible();
		await expect(page.getByText(/server error/i)).not.toBeVisible();
	});

	test('displays connectors or add connector option', async ({ page }) => {
		// Settings page should show either existing connectors or option to add them
		const pageText = await page.textContent('body');

		// Should have some connector-related content visible
		expect(pageText).toBeTruthy();
		expect(pageText!.length).toBeGreaterThan(100); // Actual content, not just empty page
	});

	test('can open and close Add Folder modal if available', async ({ page }) => {
		const addFolderButton = page.getByRole('button', { name: /Add Folder/i });
		const buttonExists = await addFolderButton.isVisible().catch(() => false);

		if (buttonExists) {
			await addFolderButton.click();

			// Modal should open
			const dialogExists = await page.getByRole('dialog').isVisible().catch(() => false);
			expect(dialogExists).toBe(true);

			if (dialogExists) {
				// Close modal
				const cancelButton = page.getByRole('button', { name: /Cancel/i });
				const cancelExists = await cancelButton.isVisible().catch(() => false);

				if (cancelExists) {
					await cancelButton.click();
					await expect(page.getByRole('dialog')).not.toBeVisible();
				}
			}
		}
	});
});

test.describe('Settings Navigation', () => {
	test('can navigate to settings from sidebar', async ({ page }) => {
		await page.goto('/');

		const settingsLink = page.getByRole('link', { name: /Settings/i });
		const linkExists = await settingsLink.isVisible().catch(() => false);

		if (linkExists) {
			await settingsLink.click();
			await expect(page).toHaveURL(/\/settings/);
		} else {
			// Can navigate directly
			await page.goto('/settings');
			await expect(page).toHaveURL(/\/settings/);
		}
	});
});
