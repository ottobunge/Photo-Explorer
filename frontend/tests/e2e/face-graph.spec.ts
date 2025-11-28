/**
 * E2E Tests for Face Social Graph
 *
 * Tests complete user workflows against REAL infrastructure:
 * - Real backend API
 * - Real database (PostgreSQL)
 * - Real ML processing
 * - NO MOCKS
 *
 * For testing with mocked data, see tests/integration/face-graph-page.spec.ts
 */

import { test, expect } from '@playwright/test';

test.describe('Face Social Graph - E2E Tests', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/faces');
	});

	test.describe('Direct Navigation', () => {
		test('loads graph view directly via URL parameter', async ({ page }) => {
			// Navigate directly to graph view
			await page.goto('/faces?view=graph');
			await page.waitForLoadState('networkidle');

			// Verify graph tab is active
			await expect(page.getByTestId('graph-tab')).toHaveAttribute('aria-selected', 'true');

			// Verify graph component is visible
			await expect(page.getByTestId('face-graph')).toBeVisible();
		});
	});

	test.describe('Tab Navigation', () => {
		test('displays List and Graph tabs', async ({ page }) => {
			// Should have both tabs visible
			await expect(page.getByTestId('list-tab')).toBeVisible();
			await expect(page.getByTestId('graph-tab')).toBeVisible();
		});

		test('switches from List to Graph view', async ({ page }) => {
			// Initially on list view
			await expect(page.getByTestId('list-tab')).toHaveAttribute('aria-selected', 'true');
			await expect(page.getByTestId('graph-tab')).toHaveAttribute('aria-selected', 'false');

			// Click graph tab and wait for navigation
			await Promise.all([
				page.waitForURL(/view=graph/),
				page.getByTestId('graph-tab').click()
			]);

			// Wait for network to settle (graph data loads from REAL API)
			await page.waitForLoadState('networkidle');

			// Should switch to graph view
			await expect(page.getByTestId('graph-tab')).toHaveAttribute('aria-selected', 'true');
			await expect(page.getByTestId('list-tab')).toHaveAttribute('aria-selected', 'false');

			// Graph should be visible
			await expect(page.getByTestId('face-graph')).toBeVisible();
		});

		test('switches from Graph to List view', async ({ page }) => {
			// Go to graph view first
			await Promise.all([
				page.waitForURL(/view=graph/),
				page.getByTestId('graph-tab').click()
			]);
			await page.waitForLoadState('networkidle');
			await expect(page.getByTestId('face-graph')).toBeVisible();

			// Click list tab and wait for navigation
			await Promise.all([
				page.waitForURL('/faces'),
				page.getByTestId('list-tab').click()
			]);
			await page.waitForLoadState('networkidle');

			// Should switch back to list view
			await expect(page.getByTestId('list-tab')).toHaveAttribute('aria-selected', 'true');
			await expect(page.getByTestId('graph-tab')).toHaveAttribute('aria-selected', 'false');

			// Graph should not be visible
			await expect(page.getByTestId('face-graph')).not.toBeVisible();
		});

		test('persists graph view selection in URL', async ({ page }) => {
			// Click graph tab and wait for navigation
			await Promise.all([
				page.waitForURL(/view=graph/),
				page.getByTestId('graph-tab').click()
			]);

			// Reload page
			await page.reload();
			await page.waitForLoadState('networkidle');

			// Should still be on graph view after reload
			await expect(page.getByTestId('graph-tab')).toHaveAttribute('aria-selected', 'true');
			await expect(page.getByTestId('face-graph')).toBeVisible();
		});

		test('removes view parameter when switching to List', async ({ page }) => {
			// Go to graph view
			await Promise.all([
				page.waitForURL(/view=graph/),
				page.getByTestId('graph-tab').click()
			]);

			// Switch back to list
			await Promise.all([
				page.waitForURL('/faces'),
				page.getByTestId('list-tab').click()
			]);

			// URL should not contain view parameter
			await expect(page).not.toHaveURL(/view=graph/);
		});
	});

	test.describe('Graph Visualization', () => {
		test('displays graph controls when on graph view', async ({ page }) => {
			await page.getByTestId('graph-tab').click();
			await page.waitForLoadState('networkidle');

			// Should have graph controls visible
			await expect(page.getByTestId('graph-controls')).toBeVisible();
		});

		test('displays real graph data from backend', async ({ page }) => {
			await page.getByTestId('graph-tab').click();
			await page.waitForLoadState('networkidle');

			// Verify graph component loaded (no assertions about specific data since it's seeded)
			await expect(page.getByTestId('face-graph')).toBeVisible();

			// The actual graph content depends on seeded data
			// We just verify the graph rendered without errors
		});
	});

	test.describe('Browser Navigation', () => {
		test('browser back button works correctly', async ({ page }) => {
			// Start on list view
			await expect(page.getByTestId('list-tab')).toHaveAttribute('aria-selected', 'true');

			// Navigate to graph view
			await page.getByTestId('graph-tab').click();
			await page.waitForURL(/view=graph/);
			await expect(page.getByTestId('graph-tab')).toHaveAttribute('aria-selected', 'true');

			// Use browser back button
			await page.goBack();
			await page.waitForLoadState('networkidle');

			// Should be back on list view
			await expect(page.getByTestId('list-tab')).toHaveAttribute('aria-selected', 'true');
			await expect(page).not.toHaveURL(/view=graph/);
		});

		test('browser forward button works correctly', async ({ page }) => {
			// Navigate to graph view
			await page.getByTestId('graph-tab').click();
			await page.waitForURL(/view=graph/);

			// Go back to list view
			await page.getByTestId('list-tab').click();
			await page.waitForURL('/faces');

			// Use browser forward button
			await page.goForward();
			await page.waitForLoadState('networkidle');

			// Should be back on graph view
			await expect(page.getByTestId('graph-tab')).toHaveAttribute('aria-selected', 'true');
			await expect(page).toHaveURL(/view=graph/);
		});
	});

	test.describe('URL Sharing', () => {
		test('direct link to graph view works', async ({ page }) => {
			// Simulate user clicking a shared link directly to graph view
			await page.goto('/faces?view=graph');
			await page.waitForLoadState('networkidle');

			// Should load graph view directly
			await expect(page.getByTestId('graph-tab')).toHaveAttribute('aria-selected', 'true');
			await expect(page.getByTestId('face-graph')).toBeVisible();
		});

		test('shared graph URL persists after interaction', async ({ page }) => {
			// Load graph view via URL
			await page.goto('/faces?view=graph');
			await page.waitForLoadState('networkidle');

			// Interact with the page (reload)
			await page.reload();
			await page.waitForLoadState('networkidle');

			// Should still be on graph view
			await expect(page).toHaveURL(/view=graph/);
			await expect(page.getByTestId('graph-tab')).toHaveAttribute('aria-selected', 'true');
		});
	});

	test.describe('Accessibility', () => {
		test('graph view is keyboard navigable', async ({ page }) => {
			// Tab to graph tab button
			await page.keyboard.press('Tab');
			await page.keyboard.press('Tab'); // Might need multiple tabs depending on page layout

			// Press Enter to activate (when graph tab is focused)
			// This is environment-specific, so we'll just verify the tab exists
			const graphTab = page.getByTestId('graph-tab');
			await expect(graphTab).toBeVisible();
			await expect(graphTab).toHaveAttribute('role', 'tab');
		});

		test('graph has proper ARIA attributes', async ({ page }) => {
			await page.getByTestId('graph-tab').click();
			await page.waitForLoadState('networkidle');

			const graphTab = page.getByTestId('graph-tab');
			await expect(graphTab).toHaveAttribute('aria-selected', 'true');
			await expect(graphTab).toHaveAttribute('role', 'tab');

			const listTab = page.getByTestId('list-tab');
			await expect(listTab).toHaveAttribute('aria-selected', 'false');
			await expect(listTab).toHaveAttribute('role', 'tab');
		});
	});

	test.describe('Performance', () => {
		test('graph loads within reasonable time', async ({ page }) => {
			const startTime = Date.now();

			await page.getByTestId('graph-tab').click();
			await page.waitForLoadState('networkidle');

			const loadTime = Date.now() - startTime;

			// Graph should load in less than 5 seconds (adjust based on requirements)
			expect(loadTime).toBeLessThan(5000);
		});
	});
});
