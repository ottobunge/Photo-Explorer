import { test, expect } from '@playwright/test';

test.describe('Settings Page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/settings');
	});

	test('displays settings page with title', async ({ page }) => {
		await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
		await expect(page.getByText('Configure your photo sources')).toBeVisible();
	});

	test('displays Photo Sources section', async ({ page }) => {
		await expect(page.getByRole('heading', { name: 'Photo Sources' })).toBeVisible();
	});

	test('displays Google Photos section', async ({ page }) => {
		await expect(page.getByRole('heading', { name: /Google Photos/ })).toBeVisible();
		await expect(page.getByText('Connect your Google Photos library')).toBeVisible();
	});

	test('displays Local Folders section', async ({ page }) => {
		await expect(page.getByRole('heading', { name: /Local Folders/ })).toBeVisible();
		await expect(page.getByText('Add local folders to index')).toBeVisible();
	});

	test('displays Application Settings section', async ({ page }) => {
		await expect(page.getByRole('heading', { name: /Application Settings/ })).toBeVisible();
	});

	test('shows Connect Google Photos button when not connected', async ({ page }) => {
		await expect(page.getByRole('button', { name: /Connect Google Photos/i })).toBeVisible();
	});

	test('shows Add Folder button', async ({ page }) => {
		await expect(page.getByRole('button', { name: /Add Folder/i })).toBeVisible();
	});

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

	test('displays thumbnail quality slider', async ({ page }) => {
		await expect(page.getByLabel('Thumbnail Quality')).toBeVisible();
	});

	test('displays CLIP model selector', async ({ page }) => {
		await expect(page.getByLabel('CLIP Model')).toBeVisible();
	});

	test('displays face detection toggle', async ({ page }) => {
		await expect(page.getByText('Enable Face Detection')).toBeVisible();
	});

	test('displays auto-index toggle', async ({ page }) => {
		await expect(page.getByText('Auto-index New Photos')).toBeVisible();
	});

	test('Save Changes button is disabled when no changes made', async ({ page }) => {
		// Wait for settings to load
		await page.waitForTimeout(500);

		const saveButton = page.getByRole('button', { name: 'Save Changes' });
		await expect(saveButton).toBeDisabled();
	});
});

test.describe('Settings Navigation', () => {
	test('can navigate to settings from sidebar', async ({ page }) => {
		await page.goto('/');

		await page.getByRole('link', { name: 'Settings' }).click();

		await expect(page).toHaveURL('/settings');
		await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
	});
});
