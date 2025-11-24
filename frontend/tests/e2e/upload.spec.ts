import { test, expect } from '@playwright/test';

test.describe('Photo Upload', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/upload');
	});

	test('displays upload page with drop zone', async ({ page }) => {
		await expect(page.getByTestId('upload-zone')).toBeVisible();
		await expect(page.getByText('Drag & drop photos here')).toBeVisible();
	});

	test('upload zone accepts keyboard interaction', async ({ page }) => {
		const uploadZone = page.getByTestId('upload-zone');
		await uploadZone.focus();

		// Should be focusable
		await expect(uploadZone).toBeFocused();
	});

	test('shows selected files after selection', async ({ page }) => {
		// Create a test file
		const buffer = Buffer.from('fake image content');

		// Use file chooser
		const [fileChooser] = await Promise.all([
			page.waitForEvent('filechooser'),
			page.getByTestId('upload-zone').click()
		]);

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

		const [fileChooser] = await Promise.all([
			page.waitForEvent('filechooser'),
			page.getByTestId('upload-zone').click()
		]);

		await fileChooser.setFiles({
			name: 'test-photo.jpg',
			mimeType: 'image/jpeg',
			buffer
		});

		await expect(page.getByRole('button', { name: /Upload 1 Photos/i })).toBeVisible();
	});

	test('clear all button removes selected files', async ({ page }) => {
		const buffer = Buffer.from('fake image content');

		const [fileChooser] = await Promise.all([
			page.waitForEvent('filechooser'),
			page.getByTestId('upload-zone').click()
		]);

		await fileChooser.setFiles({
			name: 'test-photo.jpg',
			mimeType: 'image/jpeg',
			buffer
		});

		await expect(page.getByText('test-photo.jpg')).toBeVisible();

		await page.getByRole('button', { name: 'Clear All' }).click();

		await expect(page.getByText('test-photo.jpg')).not.toBeVisible();
	});
});
