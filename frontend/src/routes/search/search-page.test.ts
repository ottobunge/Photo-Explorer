import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import SearchPage from './+page.svelte';
import * as clientModule from '$lib/api/client';
import { page } from '$app/stores';
import { goto } from '$app/navigation';

// Mock dependencies
vi.mock('$lib/api/client', () => ({
	client: {
		get: vi.fn()
	},
	API_HOST: 'http://localhost:8000'
}));

vi.mock('$app/stores', () => ({
	page: {
		subscribe: vi.fn((cb) => {
			cb({
				url: new URL('http://localhost:5173/search')
			});
			return () => {};
		})
	}
}));

vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

describe('Search Page - Photo Clickability', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('should render clickable photo cards in browse mode', async () => {
		// Given: The API returns photos for browsing
		const mockPhotos = [
			{
				id: 'browse-photo-1',
				filename: 'nature.jpg',
				thumbnail_url: '/api/v1/photos/browse-photo-1/thumbnail',
				connector_type: 'local',
				width: 1920,
				height: 1080,
				taken_at: '2024-01-01T12:00:00Z',
				created_at: '2024-01-01T12:00:00Z'
			},
			{
				id: 'browse-photo-2',
				filename: 'city.jpg',
				thumbnail_url: '/api/v1/photos/browse-photo-2/thumbnail',
				connector_type: 'google_photos',
				width: 1920,
				height: 1080,
				taken_at: '2024-01-02T12:00:00Z',
				created_at: '2024-01-02T12:00:00Z'
			}
		];

		vi.mocked(clientModule.client.get).mockResolvedValue({
			success: true,
			data: { photos: mockPhotos },
			meta: { total: 2 }
		});

		// When: The search page is rendered in browse mode
		render(SearchPage);

		// Then: Photo cards should be clickable links
		await waitFor(() => {
			const photoCards = screen.getAllByTestId('photo-card');
			expect(photoCards).toHaveLength(2);

			// Verify photos are links with correct hrefs
			expect(photoCards[0]).toHaveAttribute('href', '/photos/browse-photo-1');
			expect(photoCards[0].tagName.toLowerCase()).toBe('a');

			expect(photoCards[1]).toHaveAttribute('href', '/photos/browse-photo-2');
			expect(photoCards[1].tagName.toLowerCase()).toBe('a');
		});
	});

	it('should render clickable photo cards in search mode with scores', async () => {
		// Given: The page URL has a search query
		vi.mocked(page.subscribe).mockImplementation((cb) => {
			cb({
				url: new URL('http://localhost:5173/search?q=sunset')
			});
			return () => {};
		});

		// And: The API returns search results
		const mockSearchResults = [
			{
				photo: {
					id: 'search-photo-1',
					filename: 'sunset-beach.jpg',
					thumbnail_url: '/api/v1/photos/search-photo-1/thumbnail',
					connector_type: 'local',
					width: 3000,
					height: 2000,
					taken_at: '2024-06-15T19:30:00Z',
					created_at: '2024-06-15T19:30:00Z'
				},
				score: 0.89
			},
			{
				photo: {
					id: 'search-photo-2',
					filename: 'golden-hour.jpg',
					thumbnail_url: '/api/v1/photos/search-photo-2/thumbnail',
					connector_type: 'google_photos',
					width: 4000,
					height: 3000,
					taken_at: '2024-07-20T20:00:00Z',
					created_at: '2024-07-20T20:00:00Z'
				},
				score: 0.75
			}
		];

		vi.mocked(clientModule.client.get).mockImplementation(async (url) => {
			if (url.includes('/search?q=')) {
				return {
					success: true,
					data: { results: mockSearchResults },
					meta: { total: 2 }
				};
			}
			// For connectors and albums endpoints
			return {
				success: true,
				data: { connectors: [], albums: [] }
			};
		});

		// When: The search page is rendered with a query
		render(SearchPage);

		// Then: Photo cards should be clickable and show search scores
		await waitFor(() => {
			const photoCards = screen.getAllByTestId('photo-card');
			expect(photoCards).toHaveLength(2);

			// Verify first result
			expect(photoCards[0]).toHaveAttribute('href', '/photos/search-photo-1');
			expect(screen.getByText('sunset-beach.jpg')).toBeInTheDocument();
			expect(screen.getByText('Score: 0.89')).toBeInTheDocument();

			// Verify second result
			expect(photoCards[1]).toHaveAttribute('href', '/photos/search-photo-2');
			expect(screen.getByText('golden-hour.jpg')).toBeInTheDocument();
			expect(screen.getByText('Score: 0.75')).toBeInTheDocument();
		});
	});

	it('should show empty state when no photos match search', async () => {
		// Given: The page URL has a search query
		vi.mocked(page.subscribe).mockImplementation((cb) => {
			cb({
				url: new URL('http://localhost:5173/search?q=unicorn')
			});
			return () => {};
		});

		// And: The API returns no results
		vi.mocked(clientModule.client.get).mockImplementation(async (url) => {
			if (url.includes('/search?q=')) {
				return {
					success: true,
					data: { results: [] },
					meta: { total: 0 }
				};
			}
			return {
				success: true,
				data: { connectors: [], albums: [] }
			};
		});

		// When: The search page is rendered
		render(SearchPage);

		// Then: Should show empty state with no photo cards
		await waitFor(() => {
			expect(screen.getByText(/No photos yet/i)).toBeInTheDocument();
			expect(screen.queryByTestId('photo-card')).not.toBeInTheDocument();
		});
	});

	it('should maintain clickability when paginating through results', async () => {
		// Given: The API returns paginated photos
		const page1Photos = [
			{
				id: 'page1-photo-1',
				filename: 'p1-1.jpg',
				thumbnail_url: '/api/v1/photos/page1-photo-1/thumbnail',
				connector_type: 'local',
				width: 1920,
				height: 1080,
				taken_at: null,
				created_at: '2024-01-01T12:00:00Z'
			}
		];

		const page2Photos = [
			{
				id: 'page2-photo-1',
				filename: 'p2-1.jpg',
				thumbnail_url: '/api/v1/photos/page2-photo-1/thumbnail',
				connector_type: 'local',
				width: 1920,
				height: 1080,
				taken_at: null,
				created_at: '2024-01-02T12:00:00Z'
			}
		];

		let callCount = 0;
		vi.mocked(clientModule.client.get).mockImplementation(async (url) => {
			callCount++;
			if (url.includes('page=2')) {
				return {
					success: true,
					data: { photos: page2Photos },
					meta: { total: 50 }
				};
			}
			return {
				success: true,
				data: { photos: callCount === 1 ? page1Photos : [] },
				meta: { total: 50 }
			};
		});

		// When: The search page is rendered and user navigates to page 2
		const { container } = render(SearchPage);

		// Wait for initial render
		await waitFor(() => {
			expect(screen.getByTestId('photo-card')).toBeInTheDocument();
		});

		// Find and click the "Next" button
		const nextButton = screen.getByText('Next');
		await fireEvent.click(nextButton);

		// Then: New photos should be clickable
		await waitFor(() => {
			const photoCard = screen.getByTestId('photo-card');
			expect(photoCard).toHaveAttribute('href', '/photos/page2-photo-1');
			expect(screen.getByText('p2-1.jpg')).toBeInTheDocument();
		});
	});

	it('should apply hover effects to photo cards', async () => {
		// Given: The API returns photos
		const mockPhotos = [
			{
				id: 'hover-photo',
				filename: 'hover-test.jpg',
				thumbnail_url: '/api/v1/photos/hover-photo/thumbnail',
				connector_type: 'local',
				width: 1920,
				height: 1080,
				taken_at: null,
				created_at: '2024-01-01T12:00:00Z'
			}
		];

		vi.mocked(clientModule.client.get).mockResolvedValue({
			success: true,
			data: { photos: mockPhotos },
			meta: { total: 1 }
		});

		// When: The search page is rendered
		render(SearchPage);

		// Then: Photo card should have hover class
		await waitFor(() => {
			const photoCard = screen.getByTestId('photo-card');
			expect(photoCard).toHaveClass('photo-card');
			expect(photoCard).toHaveClass('group');
			expect(photoCard).toHaveClass('cursor-pointer');
		});
	});

	it('should show loading state while searching', async () => {
		// Given: The API is slow to respond
		vi.mocked(clientModule.client.get).mockImplementation(
			() => new Promise((resolve) => setTimeout(() => resolve({
				success: true,
				data: { photos: [] },
				meta: { total: 0 }
			}), 100))
		);

		// When: The search page is rendered
		render(SearchPage);

		// Then: Should show loading state initially
		expect(screen.getByText(/Loading photos/i)).toBeInTheDocument();

		// Wait for loading to complete
		await waitFor(() => {
			expect(screen.queryByText(/Loading photos/i)).not.toBeInTheDocument();
		}, { timeout: 2000 });
	});

	it('should render photo cards with placeholder when thumbnail is missing', async () => {
		// Given: The API returns a photo without thumbnail
		const mockPhotos = [
			{
				id: 'no-thumb-search',
				filename: 'missing-thumb.jpg',
				thumbnail_url: null,
				connector_type: 'local',
				width: 1920,
				height: 1080,
				taken_at: null,
				created_at: '2024-01-01T12:00:00Z'
			}
		];

		vi.mocked(clientModule.client.get).mockResolvedValue({
			success: true,
			data: { photos: mockPhotos },
			meta: { total: 1 }
		});

		// When: The search page is rendered
		render(SearchPage);

		// Then: The photo card should still be clickable with placeholder icon
		await waitFor(() => {
			const photoCard = screen.getByTestId('photo-card');
			expect(photoCard).toHaveAttribute('href', '/photos/no-thumb-search');

			// Should show placeholder icon
			const placeholder = photoCard.querySelector('.bg-gray-100');
			expect(placeholder).toBeInTheDocument();
		});
	});
});
