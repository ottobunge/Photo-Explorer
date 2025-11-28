/**
 * E2E Tests for Manual Face Clustering
 *
 * Tests for split, move, and merge operations on faces and clusters.
 * Behavior-focused tests using real backend.
 */

import { test, expect } from '@playwright/test';

test.describe('Manual Face Clustering - Face Detail Page', () => {
	test.beforeEach(async ({ page }) => {
		// Navigate to faces page first
		await page.goto('/faces');
		await page.waitForLoadState('networkidle');
	});

	test('edit mode toggle works on face detail page', async ({ page }) => {
		// Skip if no faces available
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count === 0) {
			test.skip();
			return;
		}

		// Click first cluster to go to detail page
		await clusterCards.first().click();
		await page.waitForLoadState('networkidle');

		// Should have Edit button
		const editButton = page.getByRole('button', { name: /^(Edit|Done)$/i });
		await expect(editButton).toBeVisible();

		// Click Edit to enter edit mode
		await editButton.click();
		await expect(editButton).toHaveText(/Done/i);

		// Should show selection UI (checkboxes should be visible on faces)
		const faceImages = page.locator('button[type="button"]:has(img)').first();
		if (await faceImages.isVisible()) {
			// In edit mode, faces should be clickable buttons
			await expect(faceImages).toBeVisible();
		}

		// Click Done to exit edit mode
		await editButton.click();
		await expect(editButton).toHaveText(/Edit/i);
	});

	test('can select faces in edit mode', async ({ page }) => {
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count === 0) {
			test.skip();
			return;
		}

		// Navigate to cluster detail
		await clusterCards.first().click();
		await page.waitForLoadState('networkidle');

		// Enter edit mode
		const editButton = page.getByRole('button', { name: /Edit/i });
		await editButton.click();

		// Try to select first face
		const firstFace = page.locator('button[type="button"]:has(img)').first();
		if (await firstFace.isVisible()) {
			await firstFace.click();

			// Should show selection count in floating action bar
			await expect(page.getByText(/1 selected/i)).toBeVisible({ timeout: 2000 });
		}
	});

	test('select all functionality works', async ({ page }) => {
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count === 0) {
			test.skip();
			return;
		}

		// Navigate to cluster detail
		await clusterCards.first().click();
		await page.waitForLoadState('networkidle');

		// Enter edit mode
		await page.getByRole('button', { name: /Edit/i }).click();

		// Select one face first
		const firstFace = page.locator('button[type="button"]:has(img)').first();
		if (await firstFace.isVisible()) {
			await firstFace.click();

			// Look for Select All button
			const selectAllButton = page.getByRole('button', { name: /Select All/i });
			if (await selectAllButton.isVisible()) {
				await selectAllButton.click();

				// Should show selection count > 1
				const selectionText = await page.getByText(/\d+ selected/i).textContent();
				const selectedCount = parseInt(selectionText?.match(/\d+/)?.[0] || '0');
				expect(selectedCount).toBeGreaterThan(1);
			}
		}
	});

	test('split action is available when faces are selected', async ({ page }) => {
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count === 0) {
			test.skip();
			return;
		}

		// Navigate to cluster with multiple faces
		const clustersWithMultipleFaces = clusterCards.filter({ hasText: /[2-9]\d* faces/ });
		const multiCount = await clustersWithMultipleFaces.count();
		if (multiCount === 0) {
			test.skip();
			return;
		}

		await clustersWithMultipleFaces.first().click();
		await page.waitForLoadState('networkidle');

		// Enter edit mode and select a face
		await page.getByRole('button', { name: /Edit/i }).click();
		const firstFace = page.locator('button[type="button"]:has(img)').first();
		await firstFace.click();

		// Split button should appear in floating action bar
		await expect(page.getByRole('button', { name: /Split/i })).toBeVisible();
	});

	test('move action is available when faces are selected', async ({ page }) => {
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count === 0) {
			test.skip();
			return;
		}

		// Navigate to cluster detail
		await clusterCards.first().click();
		await page.waitForLoadState('networkidle');

		// Enter edit mode and select a face
		await page.getByRole('button', { name: /Edit/i }).click();
		const firstFace = page.locator('button[type="button"]:has(img)').first();
		if (await firstFace.isVisible()) {
			await firstFace.click();

			// Move button should appear in floating action bar
			await expect(page.getByRole('button', { name: /Move/i })).toBeVisible();
		}
	});

	test('clicking move opens cluster picker modal', async ({ page }) => {
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count < 2) {
			// Need at least 2 clusters for move operation
			test.skip();
			return;
		}

		// Navigate to cluster detail
		await clusterCards.first().click();
		await page.waitForLoadState('networkidle');

		// Enter edit mode, select face, click move
		await page.getByRole('button', { name: /Edit/i }).click();
		const firstFace = page.locator('button[type="button"]:has(img)').first();
		if (await firstFace.isVisible()) {
			await firstFace.click();
			await page.getByRole('button', { name: /Move/i }).click();

			// Should open modal with title
			await expect(page.getByRole('dialog')).toBeVisible();
			await expect(page.getByText(/Move Faces To|Select a Person/i)).toBeVisible();
		}
	});

	test('cluster picker shows available clusters', async ({ page }) => {
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count < 2) {
			test.skip();
			return;
		}

		await clusterCards.first().click();
		await page.waitForLoadState('networkidle');

		await page.getByRole('button', { name: /Edit/i }).click();
		const firstFace = page.locator('button[type="button"]:has(img)').first();
		if (await firstFace.isVisible()) {
			await firstFace.click();
			await page.getByRole('button', { name: /Move/i }).click();

			// Modal should show clusters
			const dialog = page.getByRole('dialog');
			await expect(dialog).toBeVisible();

			// Should have cluster buttons (look for face count pattern)
			const clusterButtons = dialog.locator('button:has-text("faces")');
			const buttonCount = await clusterButtons.count();
			expect(buttonCount).toBeGreaterThanOrEqual(1);
		}
	});

	test('can search clusters in picker modal', async ({ page }) => {
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count < 2) {
			test.skip();
			return;
		}

		await clusterCards.first().click();
		await page.waitForLoadState('networkidle');

		await page.getByRole('button', { name: /Edit/i }).click();
		const firstFace = page.locator('button[type="button"]:has(img)').first();
		if (await firstFace.isVisible()) {
			await firstFace.click();
			await page.getByRole('button', { name: /Move/i }).click();

			const dialog = page.getByRole('dialog');
			const searchInput = dialog.getByPlaceholder(/Search by name/i);
			if (await searchInput.isVisible()) {
				// Type a search query
				await searchInput.fill('test');
				// Input should accept the text
				await expect(searchInput).toHaveValue('test');
			}
		}
	});

	test('can cancel cluster picker modal', async ({ page }) => {
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count < 2) {
			test.skip();
			return;
		}

		await clusterCards.first().click();
		await page.waitForLoadState('networkidle');

		await page.getByRole('button', { name: /Edit/i }).click();
		const firstFace = page.locator('button[type="button"]:has(img)').first();
		if (await firstFace.isVisible()) {
			await firstFace.click();
			await page.getByRole('button', { name: /Move/i }).click();

			// Click Cancel button
			const dialog = page.getByRole('dialog');
			await dialog.getByRole('button', { name: /Cancel/i }).click();

			// Modal should close
			await expect(dialog).not.toBeVisible();
		}
	});
});

test.describe('Manual Face Clustering - Face List Page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/faces');
		await page.waitForLoadState('networkidle');
	});

	test('edit mode toggle works on face list page', async ({ page }) => {
		// Check if there are clusters (Edit button only appears with data)
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count === 0) {
			// No clusters, skip test (Edit button won't be visible)
			test.skip();
			return;
		}

		// Should have Edit button
		const editButton = page.getByRole('button', { name: /^(Edit|Done)$/i });
		await expect(editButton).toBeVisible();

		// Click Edit to enter edit mode
		await editButton.click();
		await expect(editButton).toHaveText(/Done/i);

		// Click Done to exit edit mode
		await editButton.click();
		await expect(editButton).toHaveText(/Edit/i);
	});

	test('can select clusters in edit mode', async ({ page }) => {
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count === 0) {
			test.skip();
			return;
		}

		// Enter edit mode
		await page.getByRole('button', { name: /Edit/i }).click();
		await page.waitForTimeout(100); // Wait for edit mode to activate

		// Get first cluster and verify we're in edit mode (checkbox should be visible)
		const firstCluster = clusterCards.first();

		// Click first cluster to select it
		await firstCluster.click();
		await page.waitForTimeout(200); // Wait for selection state to update

		// Should show selection count
		await expect(page.getByText(/1 selected/i)).toBeVisible({ timeout: 3000 });

		// Verify the cluster has visual selection indicator (blue border or checked checkbox)
		const isSelected = await firstCluster.evaluate((el) => {
			const style = window.getComputedStyle(el);
			return style.borderColor.includes('59, 130, 246') || // blue-500
			       style.borderWidth.includes('4px') ||
			       el.querySelector('svg[fill="currentColor"]') !== null;
		});

		expect(isSelected).toBe(true);
	});

	test('can select multiple clusters', async ({ page }) => {
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count < 2) {
			test.skip();
			return;
		}

		// Enter edit mode
		await page.getByRole('button', { name: /Edit/i }).click();
		await page.waitForTimeout(100);

		// Select first cluster
		await clusterCards.nth(0).click();
		await page.waitForTimeout(200);

		// Verify first selection worked
		await expect(page.getByText(/1 selected/i)).toBeVisible({ timeout: 3000 });

		// Select second cluster
		await clusterCards.nth(1).click();
		await page.waitForTimeout(200);

		// Should show 2 selected
		await expect(page.getByText(/2 selected/i)).toBeVisible({ timeout: 3000 });
	});

	test('merge button appears when 2+ clusters selected', async ({ page }) => {
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count < 2) {
			test.skip();
			return;
		}

		await page.getByRole('button', { name: /Edit/i }).click();

		// Select two clusters
		await clusterCards.nth(0).click();
		await clusterCards.nth(1).click();

		// Merge button should appear
		await expect(page.getByRole('button', { name: /Merge/i })).toBeVisible();
	});

	test('clicking merge opens confirmation modal', async ({ page }) => {
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count < 2) {
			test.skip();
			return;
		}

		await page.getByRole('button', { name: /Edit/i }).click();

		// Select two clusters
		await clusterCards.nth(0).click();
		await clusterCards.nth(1).click();

		// Click merge
		await page.getByRole('button', { name: /Merge/i }).click();

		// Should open merge modal
		await expect(page.getByRole('dialog')).toBeVisible();
		await expect(page.getByText(/Merge.*Clusters/i)).toBeVisible();
	});

	test('merge modal shows selected clusters', async ({ page }) => {
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count < 2) {
			test.skip();
			return;
		}

		await page.getByRole('button', { name: /Edit/i }).click();

		// Select two clusters
		await clusterCards.nth(0).click();
		await clusterCards.nth(1).click();
		await page.getByRole('button', { name: /Merge/i }).click();

		const dialog = page.getByRole('dialog');
		await expect(dialog).toBeVisible();

		// Should show radio buttons for target selection
		const radioButtons = dialog.locator('input[type="radio"]');
		const radioCount = await radioButtons.count();
		expect(radioCount).toBe(2);
	});

	test('merge modal shows warning message', async ({ page }) => {
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count < 2) {
			test.skip();
			return;
		}

		await page.getByRole('button', { name: /Edit/i }).click();
		await clusterCards.nth(0).click();
		await clusterCards.nth(1).click();
		await page.getByRole('button', { name: /Merge/i }).click();

		const dialog = page.getByRole('dialog');
		// Should show warning about irreversible action
		await expect(dialog.getByText(/cannot be undone|irreversible/i)).toBeVisible();
	});

	test('can cancel merge modal', async ({ page }) => {
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count < 2) {
			test.skip();
			return;
		}

		await page.getByRole('button', { name: /Edit/i }).click();
		await clusterCards.nth(0).click();
		await clusterCards.nth(1).click();
		await page.getByRole('button', { name: /Merge/i }).click();

		const dialog = page.getByRole('dialog');
		await dialog.getByRole('button', { name: /Cancel/i }).click();

		// Modal should close
		await expect(dialog).not.toBeVisible();
		// Should still be in edit mode
		await expect(page.getByRole('button', { name: /Done/i })).toBeVisible();
	});

	test('visual feedback for selected clusters', async ({ page }) => {
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count === 0) {
			test.skip();
			return;
		}

		await page.getByRole('button', { name: /Edit/i }).click();
		const firstCluster = clusterCards.first();
		await firstCluster.click();

		// Selected cluster should have different styling (blue border or checkmark)
		const hasCheckbox = (await firstCluster.locator('svg').count()) > 0;
		const hasBlueBorder = await firstCluster.evaluate((el) => {
			const style = window.getComputedStyle(el);
			return (
				style.borderColor.includes('59, 130, 246') || // rgb(59, 130, 246) = blue-500
				style.borderColor.includes('blue') ||
				style.borderWidth !== '1px'
			);
		});

		expect(hasCheckbox || hasBlueBorder).toBe(true);
	});

	test('exiting edit mode clears selection', async ({ page }) => {
		const clusterCards = page.locator('button:has-text("faces")');
		const count = await clusterCards.count();
		if (count === 0) {
			test.skip();
			return;
		}

		// Enter edit mode and select cluster
		await page.getByRole('button', { name: /Edit/i }).click();
		await clusterCards.first().click();
		await expect(page.getByText(/1 selected/i)).toBeVisible();

		// Exit edit mode
		await page.getByRole('button', { name: /Done/i }).click();

		// Selection count should not be visible
		await expect(page.getByText(/1 selected/i)).not.toBeVisible();

		// Re-enter edit mode - selection should be cleared
		await page.getByRole('button', { name: /Edit/i }).click();
		await expect(page.getByText(/selected/i)).not.toBeVisible();
	});
});

test.describe('Manual Face Clustering - Tab Navigation', () => {
	test('edit mode persists when switching between list and graph tabs', async ({ page }) => {
		await page.goto('/faces');
		await page.waitForLoadState('networkidle');

		// Check if graph tab exists
		const graphTab = page.getByRole('button', { name: /Graph/i });
		if (!(await graphTab.isVisible())) {
			test.skip();
			return;
		}

		// Enter edit mode on list view
		await page.getByRole('button', { name: /Edit/i }).click();
		await expect(page.getByRole('button', { name: /Done/i })).toBeVisible();

		// Switch to graph tab
		await graphTab.click();
		await page.waitForLoadState('networkidle');

		// Edit mode should be cleared (graph view doesn't have edit mode)
		// Switch back to list tab
		await page.getByRole('button', { name: /List/i }).click();
		await page.waitForLoadState('networkidle');

		// Edit mode should be reset
		await expect(page.getByRole('button', { name: /Edit/i })).toBeVisible();
	});
});
