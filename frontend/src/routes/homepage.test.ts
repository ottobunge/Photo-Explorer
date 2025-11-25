import { render, screen, waitFor } from '@testing-library/svelte';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import HomePage from './+page.svelte';
import * as clientModule from '$lib/api/client';

// Mock the API client
vi.mock('$lib/api/client', () => ({
	client: {
		get: vi.fn()
	},
	API_HOST: 'http://localhost:8000'
}));

describe('Homepage - Photo Clickability', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('should render clickable photo cards when photos are loaded', async () => {
		// Given: The API returns recent photos
		const mockPhotos = [
			{
				id: 'photo-1',
				filename: 'sunset.jpg',
				thumbnail_url: '/api/v1/photos/photo-1/thumbnail',
				connector_type: 'local',
				taken_at: '2024-01-01T12:00:00Z',
				created_at: '2024-01-01T12:00:00Z'
			},
			{
				id: 'photo-2',
				filename: 'beach.jpg',
				thumbnail_url: '/api/v1/photos/photo-2/thumbnail',
				connector_type: 'google_photos',
				taken_at: '2024-01-02T12:00:00Z',
				created_at: '2024-01-02T12:00:00Z'
			}
		];

		vi.mocked(clientModule.client.get).mockResolvedValue({
			success: true,
			data: { photos: mockPhotos },
			meta: { total: 2 }
		});

		// When: The homepage is rendered
		render(HomePage);

		// Then: Photo cards should be clickable links
		await waitFor(() => {
			const photoCards = screen.getAllByTestId('photo-card');
			expect(photoCards).toHaveLength(2);

			// Verify first photo is a link with correct href
			expect(photoCards[0]).toHaveAttribute('href', '/photos/photo-1');
			expect(photoCards[0].tagName.toLowerCase()).toBe('a');

			// Verify second photo is a link with correct href
			expect(photoCards[1]).toHaveAttribute('href', '/photos/photo-2');
			expect(photoCards[1].tagName.toLowerCase()).toBe('a');
		});
	});

	it('should display photo thumbnails with correct alt text', async () => {
		// Given: The API returns a photo with thumbnail
		const mockPhotos = [
			{
				id: 'photo-123',
				filename: 'mountain.jpg',
				thumbnail_url: '/api/v1/photos/photo-123/thumbnail',
				connector_type: 'local',
				taken_at: null,
				created_at: '2024-01-01T12:00:00Z'
			}
		];

		vi.mocked(clientModule.client.get).mockResolvedValue({
			success: true,
			data: { photos: mockPhotos },
			meta: { total: 1 }
		});

		// When: The homepage is rendered
		render(HomePage);

		// Then: The thumbnail image should have correct alt text
		await waitFor(() => {
			const img = screen.getByAlt('mountain.jpg');
			expect(img).toBeInTheDocument();
			expect(img).toHaveAttribute('src', 'http://localhost:8000/api/v1/photos/photo-123/thumbnail');
		});
	});

	it('should show placeholder icon when photo has no thumbnail', async () => {
		// Given: The API returns a photo without thumbnail
		const mockPhotos = [
			{
				id: 'photo-no-thumb',
				filename: 'no-thumbnail.jpg',
				thumbnail_url: null,
				connector_type: 'local',
				taken_at: null,
				created_at: '2024-01-01T12:00:00Z'
			}
		];

		vi.mocked(clientModule.client.get).mockResolvedValue({
			success: true,
			data: { photos: mockPhotos },
			meta: { total: 1 }
		});

		// When: The homepage is rendered
		render(HomePage);

		// Then: The photo card should still be clickable with placeholder
		await waitFor(() => {
			const photoCard = screen.getByTestId('photo-card');
			expect(photoCard).toHaveAttribute('href', '/photos/photo-no-thumb');

			// Should contain placeholder div
			const placeholder = photoCard.querySelector('.bg-gray-100');
			expect(placeholder).toBeInTheDocument();
		});
	});

	it('should show empty state when no photos exist', async () => {
		// Given: The API returns no photos
		vi.mocked(clientModule.client.get).mockResolvedValue({
			success: true,
			data: { photos: [] },
			meta: { total: 0 }
		});

		// When: The homepage is rendered
		render(HomePage);

		// Then: Should show empty state message
		await waitFor(() => {
			expect(screen.getByText(/No photos yet/i)).toBeInTheDocument();
			expect(screen.queryByTestId('photo-card')).not.toBeInTheDocument();
		});
	});

	it('should show loading state while fetching photos', async () => {
		// Given: The API is slow to respond
		vi.mocked(clientModule.client.get).mockImplementation(
			() => new Promise((resolve) => setTimeout(() => resolve({
				success: true,
				data: { photos: [] },
				meta: { total: 0 }
			}), 100))
		);

		// When: The homepage is rendered
		render(HomePage);

		// Then: Should show loading state initially
		expect(screen.getByText('Loading...')).toBeInTheDocument();
		expect(screen.queryByTestId('photo-card')).not.toBeInTheDocument();

		// Wait for loading to complete
		await waitFor(() => {
			expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
		});
	});

	it('should render multiple photo cards with unique keys', async () => {
		// Given: The API returns multiple photos
		const mockPhotos = [
			{
				id: 'photo-a',
				filename: 'a.jpg',
				thumbnail_url: '/api/v1/photos/photo-a/thumbnail',
				connector_type: 'local',
				taken_at: null,
				created_at: '2024-01-01T12:00:00Z'
			},
			{
				id: 'photo-b',
				filename: 'b.jpg',
				thumbnail_url: '/api/v1/photos/photo-b/thumbnail',
				connector_type: 'local',
				taken_at: null,
				created_at: '2024-01-02T12:00:00Z'
			},
			{
				id: 'photo-c',
				filename: 'c.jpg',
				thumbnail_url: '/api/v1/photos/photo-c/thumbnail',
				connector_type: 'google_photos',
				taken_at: null,
				created_at: '2024-01-03T12:00:00Z'
			}
		];

		vi.mocked(clientModule.client.get).mockResolvedValue({
			success: true,
			data: { photos: mockPhotos },
			meta: { total: 3 }
		});

		// When: The homepage is rendered
		render(HomePage);

		// Then: All photos should be rendered as clickable cards
		await waitFor(() => {
			const photoCards = screen.getAllByTestId('photo-card');
			expect(photoCards).toHaveLength(3);

			// Verify each card has the correct href
			expect(photoCards[0]).toHaveAttribute('href', '/photos/photo-a');
			expect(photoCards[1]).toHaveAttribute('href', '/photos/photo-b');
			expect(photoCards[2]).toHaveAttribute('href', '/photos/photo-c');

			// Verify filenames are displayed
			expect(screen.getByText('a.jpg')).toBeInTheDocument();
			expect(screen.getByText('b.jpg')).toBeInTheDocument();
			expect(screen.getByText('c.jpg')).toBeInTheDocument();
		});
	});
});
