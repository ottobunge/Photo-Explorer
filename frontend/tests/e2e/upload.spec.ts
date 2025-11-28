/**
 * E2E Tests for Upload Page
 *
 * Behavior-focused tests using real backend.
 */

import { test, expect } from '@playwright/test';

test.describe('Photo Upload', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/upload');
		await page.waitForLoadState('networkidle');
	});

	test('upload page loads without errors', async ({ page }) => {
		// Should have upload zone
		await expect(page.getByTestId('upload-zone')).toBeVisible();

		// Should not show server errors
		await expect(page.getByText(/500/i)).not.toBeVisible();
		await expect(page.getByText(/server error/i)).not.toBeVisible();
	});

	test('displays upload instructions', async ({ page }) => {
		const uploadZone = page.getByTestId('upload-zone');
		const zoneText = await uploadZone.textContent();

		// Should have some upload-related text
		expect(zoneText).toBeTruthy();
		expect(zoneText!.toLowerCase()).toMatch(/drag|drop|upload|photo|select/i);
	});

	test('upload zone is focusable', async ({ page }) => {
		const uploadZone = page.getByTestId('upload-zone');
		await uploadZone.focus();

		// Should be focusable
		await expect(uploadZone).toBeFocused();
	});

	test('shows selected files after selection', async ({ page }) => {
		// Create a test file
		const buffer = Buffer.from('fake image content');

		// Click upload zone to trigger file chooser
		const fileChooserPromise = page.waitForEvent('filechooser');

		// Try clicking the upload zone
		const uploadZone = page.getByTestId('upload-zone');
		await uploadZone.click();

		const fileChooser = await fileChooserPromise;
		await fileChooser.setFiles({
			name: 'test-photo.jpg',
			mimeType: 'image/jpeg',
			buffer
		});

		// File should appear in the list
		await expect(page.getByText('test-photo.jpg')).toBeVisible();
	});

	test('shows upload button when files are selected', async ({ page }) => {
		const buffer = Buffer.from('fake image content');

		const fileChooserPromise = page.waitForEvent('filechooser');
		const uploadZone = page.getByTestId('upload-zone');
		await uploadZone.click();

		const fileChooser = await fileChooserPromise;
		await fileChooser.setFiles({
			name: 'test-photo.jpg',
			mimeType: 'image/jpeg',
			buffer
		});

		// Should show upload button with count
		const uploadButton = page.getByRole('button', { name: /Upload.*Photos?/i });
		await expect(uploadButton).toBeVisible();
	});

	test('clear all button removes selected files', async ({ page }) => {
		const buffer = Buffer.from('fake image content');

		const fileChooserPromise = page.waitForEvent('filechooser');
		const uploadZone = page.getByTestId('upload-zone');
		await uploadZone.click();

		const fileChooser = await fileChooserPromise;
		await fileChooser.setFiles({
			name: 'test-photo.jpg',
			mimeType: 'image/jpeg',
			buffer
		});

		await expect(page.getByText('test-photo.jpg')).toBeVisible();

		// Clear all
		await page.getByRole('button', { name: /Clear All/i }).click();

		// File should be removed
		await expect(page.getByText('test-photo.jpg')).not.toBeVisible();
	});
});
