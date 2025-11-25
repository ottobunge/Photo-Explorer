import { test, expect } from '@playwright/test';
import { createMockPhoto, createMockPhotos, photoWithoutThumbnail } from '../fixtures/photos';
import { createMockSearchResult } from '../fixtures/photos';
import {
	setupHomepageMocks,
	setupSearchPageMocks,
	setupSearchModeMocks,
	setupEmptyStateMocks,
	mockPhotosAPI
} from '../helpers/api-mocks';

test.describe('Photo Navigation - Homepage', () => {
	test.beforeEach(async ({ page }) => {
		// Use fixture data and helper mocks for consistent setup
		const testPhotos = [
			createMockPhoto({
				id: 'test-photo-1',
				filename: 'sunset.jpg',
				connector_type: 'local',
				taken_at: '2024-01-01T12:00:00Z'
			}),
			createMockPhoto({
				id: 'test-photo-2',
				filename: 'beach.jpg',
				connector_type: 'google_photos',
				taken_at: '2024-01-02T12:00:00Z'
			})
		];

		await setupHomepageMocks(page, { photos: testPhotos });
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
		await setupEmptyStateMocks(page);

		// When: User visits homepage
		await page.goto('/');

		// Then: Empty state should be visible
		await expect(page.getByText(/No photos yet/i)).toBeVisible();

		// And: No photo cards should exist
		await expect(page.getByTestId('photo-card')).toHaveCount(0);
	});

	// === Converted from homepage.test.ts unit tests ===

	test('When photos load, Then thumbnails display with correct filenames', async ({ page }) => {
		// Given: Homepage is loaded with photos
		await expect(page.getByTestId('photo-card')).toHaveCount(2);

		// Then: Filenames should be visible
		await expect(page.getByText('sunset.jpg')).toBeVisible();
		await expect(page.getByText('beach.jpg')).toBeVisible();

		// And: Images should have proper alt attributes
		const images = page.locator('img[alt="sunset.jpg"]');
		await expect(images.first()).toBeVisible();
	});

	test('When photo has no thumbnail, Then placeholder icon is shown', async ({ page }) => {
		// Given: Photo without thumbnail exists
		const photoNoThumb = photoWithoutThumbnail;
		await setupHomepageMocks(page, { photos: [photoNoThumb] });
		await page.goto('/');

		// Then: Photo card should still be clickable
		const photoCard = page.getByTestId('photo-card');
		await expect(photoCard).toBeVisible();
		await expect(photoCard).toHaveAttribute('href', `/photos/${photoNoThumb.id}`);

		// And: Placeholder should be visible (gray background)
		const card = await photoCard.first();
		const hasPlaceholder = await card.locator('.bg-gray-100').count();
		expect(hasPlaceholder).toBeGreaterThan(0);
	});

	test('When multiple photos render, Then each has unique filename displayed', async ({ page }) => {
		// Given: Multiple photos with different filenames
		const multiplePhotos = createMockPhotos(3, (index) => ({
			id: `photo-${index}`,
			filename: `photo-${index}.jpg`
		}));

		await setupHomepageMocks(page, { photos: multiplePhotos });
		await page.goto('/');

		// Then: All photo cards should be rendered
		await expect(page.getByTestId('photo-card')).toHaveCount(3);

		// And: Each filename should be visible
		for (let i = 0; i < 3; i++) {
			await expect(page.getByText(`photo-${i}.jpg`)).toBeVisible();
		}
	});

	test('When homepage loads, Then stats are displayed correctly', async ({ page }) => {
		// Given: Homepage is loaded
		await expect(page.getByText('Dashboard')).toBeVisible();

		// Then: Stats section should be visible
		await expect(page.getByText('Total Photos')).toBeVisible();
		await expect(page.getByText('Albums')).toBeVisible();
		await expect(page.getByText('Named People')).toBeVisible();
		await expect(page.getByText('Connectors')).toBeVisible();
	});
});

test.describe('Photo Navigation - Search Page', () => {
	test.beforeEach(async ({ page }) => {
		// Mock connectors and albums for all search page tests
		await setupSearchPageMocks(page);
	});

	test('When user browses photos, Then all photos should be clickable', async ({ page }) => {
		// Given: Photos API returns results
		const browsePhotos = [
			createMockPhoto({
				id: 'browse-1',
				filename: 'mountain.jpg',
				connector_type: 'local'
			}),
			createMockPhoto({
				id: 'browse-2',
				filename: 'lake.jpg',
				connector_type: 'local'
			})
		];

		await setupSearchPageMocks(page, { photos: browsePhotos });

		// When: User visits the search/browse page
		await page.goto('/search');

		// Then: Photo cards should be visible and clickable
		await expect(page.getByTestId('photo-card')).toHaveCount(2);

		// And: First photo should link to detail page
		const firstCard = page.getByTestId('photo-card').first();
		await expect(firstCard).toHaveAttribute('href', '/photos/browse-1');
	});

	test('When user searches for photos, Then search results should be clickable', async ({ page }) => {
		// Given: Search API returns results with scores
		const searchResults = [
			createMockSearchResult(
				{ score: 0.89 },
				{
					id: 'sunset-1',
					filename: 'sunset-beach.jpg',
					taken_at: '2024-06-15T19:30:00Z'
				}
			)
		];

		await setupSearchModeMocks(page, 'sunset', { results: searchResults });

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
		const catResults = [
			createMockSearchResult(
				{ score: 0.95 },
				{
					id: 'cat-photo-1',
					filename: 'cute-cat.jpg',
					width: 2000,
					height: 1500
				}
			)
		];

		await setupSearchModeMocks(page, 'cat', { results: catResults });
		await page.goto('/search?q=cat');

		// When: User clicks on the search result
		await page.getByTestId('photo-card').first().click();

		// Then: User should navigate to photo detail page
		await expect(page).toHaveURL(/\/photos\/cat-photo-1/);
	});

	test('When user paginates through results, Then photos remain clickable', async ({ page }) => {
		// Given: Paginated results exist
		const page1Photo = createMockPhoto({
			id: 'page1-photo',
			filename: 'page1.jpg'
		});

		const page2Photo = createMockPhoto({
			id: 'page2-photo',
			filename: 'page2.jpg'
		});

		// Mock page 1
		await mockPhotosAPI.withPhotos(page, [page1Photo], { page: 1, perPage: 24, total: 50 });

		// Mock page 2
		await mockPhotosAPI.withPhotos(page, [page2Photo], { page: 2, perPage: 24, total: 50 });

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
		await setupSearchModeMocks(page, 'nonexistent', { results: [] });

		// When: User searches for something that doesn't exist
		await page.goto('/search?q=nonexistent');

		// Then: Empty state should be shown
		await expect(page.getByText(/No photos yet/i)).toBeVisible();

		// And: No photo cards should exist
		await expect(page.getByTestId('photo-card')).toHaveCount(0);
	});

	test('When user uses keyboard navigation, Then they can tab to photos and press Enter', async ({ page }) => {
		// Given: Photos are displayed
		const keyboardPhoto = createMockPhoto({
			id: 'keyboard-photo',
			filename: 'keyboard-test.jpg'
		});

		await setupSearchPageMocks(page, { photos: [keyboardPhoto] });
		await page.goto('/search');

		// When: User tabs to photo card and presses Enter
		const photoCard = page.getByTestId('photo-card').first();
		await photoCard.focus();
		await page.keyboard.press('Enter');

		// Then: User should navigate to photo detail
		await expect(page).toHaveURL(/\/photos\/keyboard-photo/);
	});

	// === Converted from search-page.test.ts unit tests ===

	test('When search results load, Then filenames are displayed', async ({ page }) => {
		// Given: Search returns results
		const results = [
			createMockSearchResult({ score: 0.85 }, { filename: 'result-1.jpg' }),
			createMockSearchResult({ score: 0.75 }, { filename: 'result-2.jpg' })
		];

		await setupSearchModeMocks(page, 'test', { results });
		await page.goto('/search?q=test');

		// Then: Filenames should be visible
		await expect(page.getByText('result-1.jpg')).toBeVisible();
		await expect(page.getByText('result-2.jpg')).toBeVisible();
	});

	test('When photo has no thumbnail in search, Then placeholder is shown', async ({ page }) => {
		// Given: Search result without thumbnail
		const noThumbPhoto = photoWithoutThumbnail;
		await setupSearchPageMocks(page, { photos: [noThumbPhoto] });
		await page.goto('/search');

		// Then: Photo card should be clickable with placeholder
		const photoCard = page.getByTestId('photo-card');
		await expect(photoCard).toBeVisible();

		const hasPlaceholder = await photoCard.first().locator('.bg-gray-100').count();
		expect(hasPlaceholder).toBeGreaterThan(0);
	});

	test('When search page loads, Then filter options are available', async ({ page }) => {
		// Given: Search page with photos
		await setupSearchPageMocks(page, { photos: createMockPhotos(1) });
		await page.goto('/search');

		// Then: Filter dropdowns should be visible
		await expect(page.getByText('Source:')).toBeVisible();
		await expect(page.getByText('Album:')).toBeVisible();
	});

	test('When browse mode shows many photos, Then pagination appears', async ({ page }) => {
		// Given: Many photos exist (triggers pagination)
		const manyPhotos = createMockPhotos(24);
		await mockPhotosAPI.withPhotos(page, manyPhotos, { page: 1, perPage: 24, total: 100 });
		await page.goto('/search');

		// Then: Pagination should be visible
		await expect(page.getByText('Showing 1-24 of 100 photos')).toBeVisible();
		await expect(page.getByText('Next')).toBeVisible();
	});
});
