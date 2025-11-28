/**
 * Integration Tests for Face Graph Page
 *
 * Tests page-level interactions with mocked API responses.
 * These tests verify UI behavior and state management with controlled data.
 */

import { test, expect } from '@playwright/test';

test.describe('Face Graph Page - Integration Tests', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/faces');
	});

	test.describe('Graph State Management', () => {
		test('displays empty state when no faces exist', async ({ page }) => {
			// Mock empty response
			await page.route('**/api/v1/faces/graph', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						success: true,
						data: {
							nodes: [],
							edges: [],
							node_count: 0,
							edge_count: 0,
							is_empty: true,
							has_connections: false
						}
					})
				});
			});

			await page.getByTestId('graph-tab').click();
			await page.waitForLoadState('networkidle');

			// Should show empty state
			await expect(page.getByText(/No people found/i)).toBeVisible();
		});

		test('displays graph with nodes only', async ({ page }) => {
			// Mock graph with nodes but no edges
			await page.route('**/api/v1/faces/graph', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						success: true,
						data: {
							nodes: [
								{
									id: '1',
									name: 'Alice',
									photo_count: 10,
									face_count: 15,
									representative_face_id: 'face-1'
								},
								{
									id: '2',
									name: 'Bob',
									photo_count: 8,
									face_count: 12,
									representative_face_id: 'face-2'
								}
							],
							edges: [],
							node_count: 2,
							edge_count: 0,
							is_empty: false,
							has_connections: false
						}
					})
				});
			});

			await page.getByTestId('graph-tab').click();
			await page.waitForLoadState('networkidle');

			// Should show graph statistics
			await expect(page.getByText(/2 people/i)).toBeVisible();
			await expect(page.getByText(/0 relationship/i)).toBeVisible();
		});

		test('displays graph with nodes and edges', async ({ page }) => {
			// Mock graph with relationships
			await page.route('**/api/v1/faces/graph', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						success: true,
						data: {
							nodes: [
								{
									id: '1',
									name: 'Alice',
									photo_count: 10,
									face_count: 15,
									representative_face_id: 'face-1'
								},
								{
									id: '2',
									name: 'Bob',
									photo_count: 8,
									face_count: 12,
									representative_face_id: 'face-2'
								},
								{
									id: '3',
									name: 'Charlie',
									photo_count: 6,
									face_count: 9,
									representative_face_id: 'face-3'
								}
							],
							edges: [
								{
									person_a_id: '1',
									person_b_id: '2',
									shared_photo_count: 5,
									sample_photo_ids: ['photo-1', 'photo-2']
								},
								{
									person_a_id: '2',
									person_b_id: '3',
									shared_photo_count: 3,
									sample_photo_ids: ['photo-3', 'photo-4']
								}
							],
							node_count: 3,
							edge_count: 2,
							is_empty: false,
							has_connections: true
						}
					})
				});
			});

			await page.getByTestId('graph-tab').click();
			await page.waitForLoadState('networkidle');

			// Should show graph statistics
			await expect(page.getByText(/3 people/i)).toBeVisible();
			await expect(page.getByText(/2 relationship/i)).toBeVisible();
		});
	});

	test.describe('Loading and Error States', () => {
		test('handles loading state', async ({ page }) => {
			// Mock slow API response
			await page.route('**/api/v1/faces/graph', async (route) => {
				// Delay response to see loading state
				await new Promise((resolve) => setTimeout(resolve, 500));
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						success: true,
						data: {
							nodes: [],
							edges: [],
							node_count: 0,
							edge_count: 0,
							is_empty: true,
							has_connections: false
						}
					})
				});
			});

			await page.getByTestId('graph-tab').click();

			// Should show loading indicator initially
			await expect(page.getByText(/Loading/i).or(page.locator('.loading-spinner'))).toBeVisible();

			// Wait for data to load
			await page.waitForLoadState('networkidle');

			// Loading should disappear
			await expect(page.getByText(/Loading/i)).not.toBeVisible();
		});

		test('handles API error gracefully', async ({ page }) => {
			// Mock error response
			await page.route('**/api/v1/faces/graph', async (route) => {
				await route.fulfill({
					status: 500,
					contentType: 'application/json',
					body: JSON.stringify({
						success: false,
						error: {
							code: 'INTERNAL_ERROR',
							message: 'Failed to load graph data'
						}
					})
				});
			});

			await page.getByTestId('graph-tab').click();
			await page.waitForLoadState('networkidle');

			// Should show error message
			await expect(
				page.getByText(/Failed to load/i).or(page.getByText(/error/i))
			).toBeVisible();
		});

		test('handles network timeout', async ({ page }) => {
			// Mock timeout (no response)
			await page.route('**/api/v1/faces/graph', async (_route) => {
				// Simulate timeout by never fulfilling
				await new Promise((resolve) => setTimeout(resolve, 30000));
			});

			await page.getByTestId('graph-tab').click();

			// Should show loading state
			await expect(page.getByText(/Loading/i).or(page.locator('.loading-spinner'))).toBeVisible();

			// In real app, should eventually show timeout error
			// (timeout handling depends on implementation)
		});
	});

	test.describe('Graph Filtering', () => {
		test('filters graph by person', async ({ page }) => {
			// Mock full graph
			await page.route('**/api/v1/faces/graph', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						success: true,
						data: {
							nodes: [
								{
									id: '1',
									name: 'Alice',
									photo_count: 10,
									face_count: 15,
									representative_face_id: 'face-1'
								},
								{
									id: '2',
									name: 'Bob',
									photo_count: 8,
									face_count: 12,
									representative_face_id: 'face-2'
								}
							],
							edges: [
								{
									person_a_id: '1',
									person_b_id: '2',
									shared_photo_count: 5,
									sample_photo_ids: []
								}
							],
							node_count: 2,
							edge_count: 1,
							is_empty: false,
							has_connections: true
						}
					})
				});
			});

			await page.getByTestId('graph-tab').click();
			await page.waitForLoadState('networkidle');

			// Should show full graph initially
			await expect(page.getByText(/2 people/i)).toBeVisible();

			// Filter would be tested here if implemented
			// This is a placeholder for future filtering functionality
		});
	});

	test.describe('Edge Cases', () => {
		test('handles single person (no relationships)', async ({ page }) => {
			await page.route('**/api/v1/faces/graph', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						success: true,
						data: {
							nodes: [
								{
									id: '1',
									name: 'Lonely Person',
									photo_count: 5,
									face_count: 7,
									representative_face_id: 'face-1'
								}
							],
							edges: [],
							node_count: 1,
							edge_count: 0,
							is_empty: false,
							has_connections: false
						}
					})
				});
			});

			await page.getByTestId('graph-tab').click();
			await page.waitForLoadState('networkidle');

			await expect(page.getByText(/1 person/i)).toBeVisible();
			await expect(page.getByText(/0 relationship/i)).toBeVisible();
		});

		test('handles large graph (many nodes and edges)', async ({ page }) => {
			// Create mock data for large graph
			const nodes = Array.from({ length: 20 }, (_, i) => ({
				id: `${i + 1}`,
				name: `Person ${i + 1}`,
				photo_count: Math.floor(Math.random() * 20) + 1,
				face_count: Math.floor(Math.random() * 30) + 1,
				representative_face_id: `face-${i + 1}`
			}));

			const edges: Array<{
				person_a_id: string;
				person_b_id: string;
				shared_photo_count: number;
				sample_photo_ids: string[];
			}> = [];
			for (let i = 0; i < 15; i++) {
				const a = Math.floor(Math.random() * 20) + 1;
				let b = Math.floor(Math.random() * 20) + 1;
				while (b === a) b = Math.floor(Math.random() * 20) + 1;

				edges.push({
					person_a_id: `${Math.min(a, b)}`,
					person_b_id: `${Math.max(a, b)}`,
					shared_photo_count: Math.floor(Math.random() * 10) + 1,
					sample_photo_ids: []
				});
			}

			await page.route('**/api/v1/faces/graph', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						success: true,
						data: {
							nodes,
							edges,
							node_count: nodes.length,
							edge_count: edges.length,
							is_empty: false,
							has_connections: true
						}
					})
				});
			});

			await page.getByTestId('graph-tab').click();
			await page.waitForLoadState('networkidle');

			// Should handle large graph
			await expect(page.getByText(/20 people/i)).toBeVisible();
			await expect(page.getByTestId('face-graph')).toBeVisible();
		});

		test('handles unnamed persons', async ({ page }) => {
			await page.route('**/api/v1/faces/graph', async (route) => {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						success: true,
						data: {
							nodes: [
								{
									id: '1',
									name: null,
									photo_count: 3,
									face_count: 5,
									representative_face_id: 'face-1'
								},
								{
									id: '2',
									name: 'Named Person',
									photo_count: 4,
									face_count: 6,
									representative_face_id: 'face-2'
								}
							],
							edges: [],
							node_count: 2,
							edge_count: 0,
							is_empty: false,
							has_connections: false
						}
					})
				});
			});

			await page.getByTestId('graph-tab').click();
			await page.waitForLoadState('networkidle');

			// Should show graph with unnamed person
			await expect(page.getByText(/2 people/i)).toBeVisible();
		});
	});
});
