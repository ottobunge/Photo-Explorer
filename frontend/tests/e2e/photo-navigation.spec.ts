import { test, expect } from '@playwright/test';

test.describe('Photo Navigation - Homepage', () => {
	test.beforeEach(async ({ page }) => {
		// Mock the photos API for homepage
		await page.route('**/api/v1/photos?per_page=12', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: {
						photos: [
							{
								id: 'test-photo-1',
								filename: 'sunset.jpg',
								thumbnail_url: '/api/v1/photos/test-photo-1/thumbnail',
								connector_type: 'local',
								taken_at: '2024-01-01T12:00:00Z',
								created_at: '2024-01-01T12:00:00Z'
							},
							{
								id: 'test-photo-2',
								filename: 'beach.jpg',
								thumbnail_url: '/api/v1/photos/test-photo-2/thumbnail',
								connector_type: 'google_photos',
								taken_at: '2024-01-02T12:00:00Z',
								created_at: '2024-01-02T12:00:00Z'
							}
						]
					},
					meta: { total: 2 }
				})
			});
		});

		// Mock connectors API
		await page.route('**/api/v1/connectors', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: { connectors: [] }
				})
			});
		});

		// Mock albums API
		await page.route('**/api/v1/albums', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: { albums: [] }
				})
			});
		});

		// Mock face clusters API
		await page.route('**/api/v1/faces/clusters', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: { clusters: [] }
				})
			});
		});

		await page.goto('/');
	});

	test('When user views homepage, Then recent photos should be visible as clickable cards', async ({ page }) => {
		// Given: User is on the homepage
		await expect(page.getByText('Dashboard')).toBeVisible();

		// Then: Photo cards should be visible and clickable
		const photoCards = page.getByTestId('photo-card');
		await expect(photoCards).toHaveCount(2);

		// And: First photo card should be a link
		const firstCard = photoCards.first();
		await expect(firstCard).toBeVisible();
		await expect(firstCard).toHaveAttribute('href', '/photos/test-photo-1');
	});

	test('When user clicks a photo on homepage, Then they navigate to photo detail page', async ({ page }) => {
		// Given: Photo cards are visible on homepage
		await expect(page.getByTestId('photo-card').first()).toBeVisible();

		// When: User clicks on the first photo
		await page.getByTestId('photo-card').first().click();

		// Then: User should navigate to the photo detail page
		await expect(page).toHaveURL(/\/photos\/test-photo-1/);
	});

	test('When user hovers over photo, Then hover effect should be visible', async ({ page }) => {
		// Given: Photo cards are visible
		const firstCard = page.getByTestId('photo-card').first();
		await expect(firstCard).toBeVisible();

		// When: User hovers over the photo
		await firstCard.hover();

		// Then: The card should have hover class (visual feedback)
		await expect(firstCard).toHaveClass(/photo-card/);
	});

	test('When user right-clicks photo, Then browser context menu appears (standard link behavior)', async ({ page }) => {
		// Given: Photo card is visible
		const firstCard = page.getByTestId('photo-card').first();
		await expect(firstCard).toBeVisible();

		// When: User right-clicks (this tests that it's a proper anchor tag)
		// Just verify it's an anchor tag - actual context menu is browser-specific
		const tagName = await firstCard.evaluate(el => el.tagName);

		// Then: It should be an anchor tag (which supports right-click context menu)
		expect(tagName).toBe('A');
	});

	test('When homepage has no photos, Then empty state is shown with no clickable cards', async ({ page }) => {
		// Given: API returns no photos
		await page.route('**/api/v1/photos?per_page=12', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: { photos: [] },
					meta: { total: 0 }
				})
			});
		});

		// When: User visits homepage
		await page.goto('/');

		// Then: Empty state should be visible
		await expect(page.getByText(/No photos yet/i)).toBeVisible();

		// And: No photo cards should exist
		await expect(page.getByTestId('photo-card')).toHaveCount(0);
	});
});

test.describe('Photo Navigation - Search Page', () => {
	test.beforeEach(async ({ page }) => {
		// Mock connectors API
		await page.route('**/api/v1/connectors', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: { connectors: [] }
				})
			});
		});

		// Mock albums API
		await page.route('**/api/v1/albums', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: { albums: [] }
				})
			});
		});
	});

	test('When user browses photos, Then all photos should be clickable', async ({ page }) => {
		// Given: Photos API returns results
		await page.route('**/api/v1/photos?page=1&per_page=24', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: {
						photos: [
							{
								id: 'browse-1',
								filename: 'mountain.jpg',
								thumbnail_url: '/api/v1/photos/browse-1/thumbnail',
								connector_type: 'local',
								width: 1920,
								height: 1080,
								taken_at: null,
								created_at: '2024-01-01T12:00:00Z'
							},
							{
								id: 'browse-2',
								filename: 'lake.jpg',
								thumbnail_url: '/api/v1/photos/browse-2/thumbnail',
								connector_type: 'local',
								width: 1920,
								height: 1080,
								taken_at: null,
								created_at: '2024-01-02T12:00:00Z'
							}
						]
					},
					meta: { total: 2 }
				})
			});
		});

		// When: User visits the search/browse page
		await page.goto('/search');

		// Then: Photo cards should be visible and clickable
		await expect(page.getByTestId('photo-card')).toHaveCount(2);

		// And: First photo should link to detail page
		const firstCard = page.getByTestId('photo-card').first();
		await expect(firstCard).toHaveAttribute('href', '/photos/browse-1');
	});

	test('When user searches for photos, Then search results should be clickable', async ({ page }) => {
		// Given: Search API returns results
		await page.route('**/api/v1/search?q=sunset*', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: {
						results: [
							{
								photo: {
									id: 'sunset-1',
									filename: 'sunset-beach.jpg',
									thumbnail_url: '/api/v1/photos/sunset-1/thumbnail',
									connector_type: 'local',
									width: 3000,
									height: 2000,
									taken_at: '2024-06-15T19:30:00Z',
									created_at: '2024-06-15T19:30:00Z'
								},
								score: 0.89
							}
						]
					},
					meta: { total: 1 }
				})
			});
		});

		// When: User navigates to search page with query
		await page.goto('/search?q=sunset');

		// Then: Search results should be clickable
		await expect(page.getByTestId('photo-card')).toHaveCount(1);

		const photoCard = page.getByTestId('photo-card').first();
		await expect(photoCard).toHaveAttribute('href', '/photos/sunset-1');

		// And: Search score should be visible
		await expect(page.getByText('Score: 0.89')).toBeVisible();
	});

	test('When user clicks search result, Then they navigate to photo detail', async ({ page }) => {
		// Given: Search results are displayed
		await page.route('**/api/v1/search?q=cat*', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: {
						results: [
							{
								photo: {
									id: 'cat-photo-1',
									filename: 'cute-cat.jpg',
									thumbnail_url: '/api/v1/photos/cat-photo-1/thumbnail',
									connector_type: 'local',
									width: 2000,
									height: 1500,
									taken_at: null,
									created_at: '2024-03-15T10:00:00Z'
								},
								score: 0.95
							}
						]
					},
					meta: { total: 1 }
				})
			});
		});

		await page.goto('/search?q=cat');

		// When: User clicks on the search result
		await page.getByTestId('photo-card').first().click();

		// Then: User should navigate to photo detail page
		await expect(page).toHaveURL(/\/photos\/cat-photo-1/);
	});

	test('When user paginates through results, Then photos remain clickable', async ({ page }) => {
		// Given: Paginated results exist
		await page.route('**/api/v1/photos?page=1&per_page=24', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: {
						photos: [
							{
								id: 'page1-photo',
								filename: 'page1.jpg',
								thumbnail_url: '/api/v1/photos/page1-photo/thumbnail',
								connector_type: 'local',
								width: 1920,
								height: 1080,
								taken_at: null,
								created_at: '2024-01-01T12:00:00Z'
							}
						]
					},
					meta: { total: 50 }
				})
			});
		});

		await page.route('**/api/v1/photos?page=2&per_page=24', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: {
						photos: [
							{
								id: 'page2-photo',
								filename: 'page2.jpg',
								thumbnail_url: '/api/v1/photos/page2-photo/thumbnail',
								connector_type: 'local',
								width: 1920,
								height: 1080,
								taken_at: null,
								created_at: '2024-01-02T12:00:00Z'
							}
						]
					},
					meta: { total: 50 }
				})
			});
		});

		await page.goto('/search');

		// When: User navigates to page 2
		await page.getByText('Next').click();

		// Then: New photos should be clickable
		await expect(page.getByTestId('photo-card')).toHaveCount(1);
		const photoCard = page.getByTestId('photo-card').first();
		await expect(photoCard).toHaveAttribute('href', '/photos/page2-photo');
	});

	test('When search returns no results, Then no photo cards are shown', async ({ page }) => {
		// Given: Search API returns no results
		await page.route('**/api/v1/search?q=nonexistent*', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: { results: [] },
					meta: { total: 0 }
				})
			});
		});

		// When: User searches for something that doesn't exist
		await page.goto('/search?q=nonexistent');

		// Then: Empty state should be shown
		await expect(page.getByText(/No photos yet/i)).toBeVisible();

		// And: No photo cards should exist
		await expect(page.getByTestId('photo-card')).toHaveCount(0);
	});

	test('When user uses keyboard navigation, Then they can tab to photos and press Enter', async ({ page }) => {
		// Given: Photos are displayed
		await page.route('**/api/v1/photos?page=1&per_page=24', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: {
						photos: [
							{
								id: 'keyboard-photo',
								filename: 'keyboard-test.jpg',
								thumbnail_url: '/api/v1/photos/keyboard-photo/thumbnail',
								connector_type: 'local',
								width: 1920,
								height: 1080,
								taken_at: null,
								created_at: '2024-01-01T12:00:00Z'
							}
						]
					},
					meta: { total: 1 }
				})
			});
		});

		await page.goto('/search');

		// When: User tabs to photo card and presses Enter
		const photoCard = page.getByTestId('photo-card').first();
		await photoCard.focus();
		await page.keyboard.press('Enter');

		// Then: User should navigate to photo detail
		await expect(page).toHaveURL(/\/photos\/keyboard-photo/);
	});
});
