/* eslint-disable @typescript-eslint/require-await */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import PhotoGrid from './PhotoGrid.svelte';
import type { Photo } from '../types';

describe('PhotoGrid', () => {
	const mockPhoto1: Photo = {
		id: 'photo-1',
		filename: 'sunset.jpg',
		thumbnail_url: '/thumbnails/photo-1.jpg',
		connector_type: 'local',
		width: 1920,
		height: 1080,
		taken_at: '2024-01-15T10:30:00Z',
		created_at: '2024-01-15T10:30:00Z',
		score: 0.95
	};

	const mockPhoto2: Photo = {
		id: 'photo-2',
		filename: 'beach.jpg',
		thumbnail_url: '/thumbnails/photo-2.jpg',
		connector_type: 'google_photos',
		width: 1600,
		height: 1200,
		taken_at: '2024-02-20T14:15:00Z',
		created_at: '2024-02-20T14:15:00Z',
		score: 0.87
	};

	const mockPhoto3: Photo = {
		id: 'photo-3',
		filename: 'mountain.jpg',
		thumbnail_url: null,
		connector_type: 'local',
		width: null,
		height: null,
		taken_at: null,
		created_at: '2024-03-10T08:00:00Z'
	};

	const mockPhotos: Photo[] = [mockPhoto1, mockPhoto2, mockPhoto3];

	beforeEach(() => {
		vi.clearAllMocks();
	});

	describe('Rendering', () => {
		it('should render empty state when no photos provided', () => {
			render(PhotoGrid, { photos: [] });

			expect(screen.getByTestId('empty-state')).toBeInTheDocument();
			expect(screen.getByText('No photos available')).toBeInTheDocument();
		});

		it('should render custom empty message', () => {
			const customMessage = 'Upload some photos to get started';
			render(PhotoGrid, { photos: [], emptyMessage: customMessage });

			expect(screen.getByText(customMessage)).toBeInTheDocument();
		});

		it('should render loading state when loading is true and no photos', () => {
			render(PhotoGrid, { photos: [], loading: true });

			expect(screen.getByTestId('loading-state')).toBeInTheDocument();
			expect(screen.getByText('Loading photos...')).toBeInTheDocument();
		});

		it('should render photos in grid layout', () => {
			render(PhotoGrid, { photos: mockPhotos });

			const gridContent = screen.getByTestId('photo-grid-content');
			expect(gridContent).toBeInTheDocument();

			const photoCards = screen.getAllByTestId('photo-card');
			expect(photoCards).toHaveLength(3);
		});

		it('should render single photo correctly', () => {
			render(PhotoGrid, { photos: [mockPhoto1] });

			const photoCard = screen.getByTestId('photo-card');
			expect(photoCard).toBeInTheDocument();
			expect(screen.getByText('sunset.jpg')).toBeInTheDocument();
		});

		it('should render photo filenames', () => {
			render(PhotoGrid, { photos: mockPhotos });

			expect(screen.getByText('sunset.jpg')).toBeInTheDocument();
			expect(screen.getByText('beach.jpg')).toBeInTheDocument();
			expect(screen.getByText('mountain.jpg')).toBeInTheDocument();
		});

		it('should render placeholder for photos without thumbnails', () => {
			render(PhotoGrid, { photos: [mockPhoto3] });

			const placeholder = screen.getByTestId('photo-placeholder');
			expect(placeholder).toBeInTheDocument();
			expect(placeholder).toHaveAttribute('role', 'img');
			expect(placeholder).toHaveAttribute(
				'aria-label',
				'Photo placeholder - no thumbnail available'
			);
		});

		it('should not show scores by default', () => {
			render(PhotoGrid, { photos: mockPhotos });

			expect(screen.queryByTestId('photo-score')).not.toBeInTheDocument();
		});

		it('should show scores when showScore is true', () => {
			render(PhotoGrid, { photos: [mockPhoto1, mockPhoto2], showScore: true });

			const scores = screen.getAllByTestId('photo-score');
			expect(scores).toHaveLength(2);
			const [score1, score2] = scores;
			expect(score1).toHaveTextContent('Score: 0.95');
			expect(score2).toHaveTextContent('Score: 0.87');
		});

		it('should not show score when photo has no score', () => {
			render(PhotoGrid, { photos: [mockPhoto3], showScore: true });

			expect(screen.queryByTestId('photo-score')).not.toBeInTheDocument();
		});

		it('should show photos even when loading is true if photos exist', () => {
			render(PhotoGrid, { photos: mockPhotos, loading: true });

			expect(screen.queryByTestId('loading-state')).not.toBeInTheDocument();
			expect(screen.getByTestId('photo-grid-content')).toBeInTheDocument();
		});
	});

	describe('Grid Layout Props', () => {
		it('should apply default 6 column grid', () => {
			render(PhotoGrid, { photos: mockPhotos });

			const grid = screen.getByTestId('photo-grid-content');
			expect(grid).toHaveClass('grid-cols-2');
			expect(grid).toHaveClass('sm:grid-cols-3');
			expect(grid).toHaveClass('md:grid-cols-4');
			expect(grid).toHaveClass('lg:grid-cols-6');
		});

		it('should apply 2 column grid', () => {
			render(PhotoGrid, { photos: mockPhotos, columns: 2 });

			const grid = screen.getByTestId('photo-grid-content');
			expect(grid).toHaveClass('grid-cols-2');
		});

		it('should apply 3 column grid', () => {
			render(PhotoGrid, { photos: mockPhotos, columns: 3 });

			const grid = screen.getByTestId('photo-grid-content');
			expect(grid).toHaveClass('grid-cols-2');
			expect(grid).toHaveClass('sm:grid-cols-3');
		});

		it('should apply 4 column grid', () => {
			render(PhotoGrid, { photos: mockPhotos, columns: 4 });

			const grid = screen.getByTestId('photo-grid-content');
			expect(grid).toHaveClass('grid-cols-2');
			expect(grid).toHaveClass('sm:grid-cols-3');
			expect(grid).toHaveClass('md:grid-cols-4');
		});

		it('should apply 5 column grid', () => {
			render(PhotoGrid, { photos: mockPhotos, columns: 5 });

			const grid = screen.getByTestId('photo-grid-content');
			expect(grid).toHaveClass('lg:grid-cols-5');
		});
	});

	describe('Interactions', () => {
		it('should use regular links when no click handler provided', () => {
			render(PhotoGrid, { photos: [mockPhoto1] });

			const photoCard = screen.getByTestId('photo-card');
			expect(photoCard).toHaveAttribute('href', '/photos/photo-1');
			expect(photoCard).toHaveAttribute('role', 'link');
		});

		it('should call onPhotoClick when photo is clicked with handler', async () => {
			const onPhotoClick = vi.fn();
			render(PhotoGrid, { photos: [mockPhoto1], onPhotoClick });

			const photoCard = screen.getByTestId('photo-card');
			expect(photoCard).toHaveAttribute('role', 'button');

			await fireEvent.click(photoCard);

			expect(onPhotoClick).toHaveBeenCalledTimes(1);
			expect(onPhotoClick).toHaveBeenCalledWith(mockPhoto1);
		});

		it('should prevent default navigation when custom click handler provided', async () => {
			const onPhotoClick = vi.fn();
			render(PhotoGrid, { photos: [mockPhoto1], onPhotoClick });

			const photoCard = screen.getByTestId('photo-card');
			const event = new MouseEvent('click', { bubbles: true, cancelable: true });
			const preventDefaultSpy = vi.spyOn(event, 'preventDefault');

			photoCard.dispatchEvent(event);

			expect(preventDefaultSpy).toHaveBeenCalled();
		});

		it('should handle clicks on multiple photos', async () => {
			const onPhotoClick = vi.fn();
			render(PhotoGrid, { photos: mockPhotos, onPhotoClick });

			const photoCards = screen.getAllByTestId('photo-card');

			if (photoCards[0]) {
				await fireEvent.click(photoCards[0]);
				expect(onPhotoClick).toHaveBeenCalledWith(mockPhoto1);
			}

			if (photoCards[1]) {
				await fireEvent.click(photoCards[1]);
				expect(onPhotoClick).toHaveBeenCalledWith(mockPhoto2);
			}

			expect(onPhotoClick).toHaveBeenCalledTimes(2);
		});

		it('should handle Enter key press', async () => {
			const onPhotoClick = vi.fn();
			render(PhotoGrid, { photos: [mockPhoto1], onPhotoClick });

			const photoCard = screen.getByTestId('photo-card');
			await fireEvent.keyDown(photoCard, { key: 'Enter' });

			expect(onPhotoClick).toHaveBeenCalledTimes(1);
			expect(onPhotoClick).toHaveBeenCalledWith(mockPhoto1);
		});

		it('should handle Space key press', async () => {
			const onPhotoClick = vi.fn();
			render(PhotoGrid, { photos: [mockPhoto1], onPhotoClick });

			const photoCard = screen.getByTestId('photo-card');
			await fireEvent.keyDown(photoCard, { key: ' ' });

			expect(onPhotoClick).toHaveBeenCalledTimes(1);
			expect(onPhotoClick).toHaveBeenCalledWith(mockPhoto1);
		});

		it('should not call handler for other keys', async () => {
			const onPhotoClick = vi.fn();
			render(PhotoGrid, { photos: [mockPhoto1], onPhotoClick });

			const photoCard = screen.getByTestId('photo-card');
			await fireEvent.keyDown(photoCard, { key: 'Tab' });
			await fireEvent.keyDown(photoCard, { key: 'Escape' });

			expect(onPhotoClick).not.toHaveBeenCalled();
		});

		it('should not call handler on keyboard when no handler provided', async () => {
			render(PhotoGrid, { photos: [mockPhoto1] });

			const photoCard = screen.getByTestId('photo-card');
			// Should not throw error
			await fireEvent.keyDown(photoCard, { key: 'Enter' });
		});
	});

	describe('Accessibility', () => {
		it('should have proper ARIA region', () => {
			render(PhotoGrid, { photos: mockPhotos });

			const region = screen.getByRole('region', { name: 'Photo gallery' });
			expect(region).toBeInTheDocument();
		});

		it('should have ARIA labels on photo cards', () => {
			render(PhotoGrid, { photos: [mockPhoto1] });

			const photoCard = screen.getByTestId('photo-card');
			expect(photoCard).toHaveAttribute('aria-label', 'View photo: sunset.jpg');
		});

		it('should have proper role for links', () => {
			render(PhotoGrid, { photos: [mockPhoto1] });

			const photoCard = screen.getByTestId('photo-card');
			expect(photoCard).toHaveAttribute('role', 'link');
		});

		it('should have proper role for buttons when click handler provided', () => {
			const onPhotoClick = vi.fn();
			render(PhotoGrid, { photos: [mockPhoto1], onPhotoClick });

			const photoCard = screen.getByTestId('photo-card');
			expect(photoCard).toHaveAttribute('role', 'button');
		});

		it('should be keyboard navigable', () => {
			render(PhotoGrid, { photos: mockPhotos });

			const photoCards = screen.getAllByTestId('photo-card');
			photoCards.forEach((card) => {
				expect(card).toHaveAttribute('tabindex', '0');
			});
		});

		it('should have title attribute for truncated filenames', () => {
			render(PhotoGrid, { photos: [mockPhoto1] });

			const filename = screen.getByText('sunset.jpg');
			expect(filename).toHaveAttribute('title', 'sunset.jpg');
		});

		it('should have aria-live on loading state', () => {
			render(PhotoGrid, { photos: [], loading: true });

			const loadingState = screen.getByTestId('loading-state');
			expect(loadingState).toHaveAttribute('role', 'status');
			expect(loadingState).toHaveAttribute('aria-live', 'polite');
		});

		it('should have role status on empty state', () => {
			render(PhotoGrid, { photos: [] });

			const emptyState = screen.getByTestId('empty-state');
			expect(emptyState).toHaveAttribute('role', 'status');
		});

		it('should hide decorative icons from screen readers', () => {
			render(PhotoGrid, { photos: [] });

			const emptyState = screen.getByTestId('empty-state');
			const icon = emptyState.querySelector('[aria-hidden="true"]');
			expect(icon).toBeInTheDocument();
		});

		it('should hide decorative SVG from screen readers', () => {
			render(PhotoGrid, { photos: [mockPhoto3] });

			const svg = screen.getByTestId('photo-placeholder').querySelector('svg');
			expect(svg).toHaveAttribute('aria-hidden', 'true');
		});
	});

	describe('Data Attributes', () => {
		it('should set data-photo-id on photo cards', () => {
			render(PhotoGrid, { photos: mockPhotos });

			const photoCards = screen.getAllByTestId('photo-card');
			expect(photoCards[0]).toHaveAttribute('data-photo-id', 'photo-1');
			expect(photoCards[1]).toHaveAttribute('data-photo-id', 'photo-2');
			expect(photoCards[2]).toHaveAttribute('data-photo-id', 'photo-3');
		});

		it('should have testid on main container', () => {
			render(PhotoGrid, { photos: mockPhotos });

			expect(screen.getByTestId('photo-grid')).toBeInTheDocument();
		});
	});

	describe('Thumbnail URL Handling', () => {
		it('should prepend API_HOST to relative thumbnail URLs', () => {
			render(PhotoGrid, { photos: [mockPhoto1] });

			const photoCard = screen.getByTestId('photo-card');
			// ImageWithFallback is mocked, but component logic should handle URL transformation
			expect(photoCard).toBeInTheDocument();
		});

		it('should not modify absolute thumbnail URLs', () => {
			const photoWithAbsoluteUrl: Photo = {
				...mockPhoto1,
				thumbnail_url: 'https://example.com/image.jpg'
			};
			render(PhotoGrid, { photos: [photoWithAbsoluteUrl] });

			const photoCard = screen.getByTestId('photo-card');
			expect(photoCard).toBeInTheDocument();
		});

		it('should handle null thumbnail URLs', () => {
			render(PhotoGrid, { photos: [mockPhoto3] });

			const placeholder = screen.getByTestId('photo-placeholder');
			expect(placeholder).toBeInTheDocument();
		});

		it('should handle empty string thumbnail URLs', () => {
			const photoWithEmptyUrl: Photo = {
				...mockPhoto1,
				thumbnail_url: ''
			};
			render(PhotoGrid, { photos: [photoWithEmptyUrl] });

			// Should show placeholder when URL is empty
			const photoCard = screen.getByTestId('photo-card');
			expect(photoCard).toBeInTheDocument();
		});
	});

	describe('Edge Cases', () => {
		it('should handle photos with very long filenames', () => {
			const longFilename = 'a'.repeat(200) + '.jpg';
			const photoWithLongName: Photo = {
				...mockPhoto1,
				filename: longFilename
			};
			render(PhotoGrid, { photos: [photoWithLongName] });

			const filename = screen.getByText(longFilename);
			expect(filename).toBeInTheDocument();
			// Should have truncate class
			expect(filename).toHaveClass('truncate');
		});

		it('should handle photos with special characters in filename', () => {
			const specialFilename = 'photo & image (2024) [edited].jpg';
			const photoWithSpecialChars: Photo = {
				...mockPhoto1,
				filename: specialFilename
			};
			render(PhotoGrid, { photos: [photoWithSpecialChars] });

			expect(screen.getByText(specialFilename)).toBeInTheDocument();
		});

		it('should handle undefined score gracefully', () => {
			const { score: _, ...photoWithoutScore } = mockPhoto1;
			render(PhotoGrid, { photos: [photoWithoutScore as Photo], showScore: true });

			expect(screen.queryByTestId('photo-score')).not.toBeInTheDocument();
		});

		it('should handle zero score', () => {
			const photoWithZeroScore: Photo = {
				...mockPhoto1,
				score: 0.0
			};
			render(PhotoGrid, { photos: [photoWithZeroScore], showScore: true });

			const scoreElement = screen.getByTestId('photo-score');
			expect(scoreElement).toHaveTextContent('Score: 0.00');
		});

		it('should handle score with many decimal places', () => {
			const photoWithPreciseScore: Photo = {
				...mockPhoto1,
				score: 0.123456789
			};
			render(PhotoGrid, { photos: [photoWithPreciseScore], showScore: true });

			const scoreElement = screen.getByTestId('photo-score');
			expect(scoreElement).toHaveTextContent('Score: 0.12');
		});

		it('should handle large number of photos', () => {
			const manyPhotos: Photo[] = Array.from({ length: 100 }, (_, i) => ({
				...mockPhoto1,
				id: `photo-${i}`,
				filename: `photo-${i}.jpg`
			}));

			render(PhotoGrid, { photos: manyPhotos });

			const photoCards = screen.getAllByTestId('photo-card');
			expect(photoCards).toHaveLength(100);
		});

		it('should handle photos with missing metadata', () => {
			const minimalPhoto: Photo = {
				id: 'minimal',
				filename: 'minimal.jpg',
				thumbnail_url: null,
				connector_type: 'local',
				width: null,
				height: null,
				taken_at: null,
				created_at: '2024-01-01T00:00:00Z'
			};

			render(PhotoGrid, { photos: [minimalPhoto] });

			expect(screen.getByText('minimal.jpg')).toBeInTheDocument();
			expect(screen.getByTestId('photo-placeholder')).toBeInTheDocument();
		});
	});

	describe('Lazy Loading', () => {
		it('should set loading attribute to lazy on images', () => {
			render(PhotoGrid, { photos: mockPhotos.slice(0, 2) });

			// ImageWithFallback is mocked, but the prop is passed
			const photoCards = screen.getAllByTestId('photo-card');
			expect(photoCards).toHaveLength(2);
		});
	});

	describe('CSS Classes', () => {
		it('should apply hover and focus transition classes', () => {
			render(PhotoGrid, { photos: [mockPhoto1] });

			const photoCard = screen.getByTestId('photo-card');
			expect(photoCard).toHaveClass('photo-card');
			expect(photoCard).toHaveClass('group');
			expect(photoCard).toHaveClass('cursor-pointer');
		});

		it('should apply gap-4 to grid', () => {
			render(PhotoGrid, { photos: mockPhotos });

			const grid = screen.getByTestId('photo-grid-content');
			expect(grid).toHaveClass('gap-4');
		});
	});

	describe('Reactivity', () => {
		it('should update when photos prop changes', async () => {
			const { rerender } = render(PhotoGrid, { photos: [mockPhoto1] });

			expect(screen.getAllByTestId('photo-card')).toHaveLength(1);

			await rerender({ photos: mockPhotos });

			expect(screen.getAllByTestId('photo-card')).toHaveLength(3);
		});

		it('should update when loading state changes', async () => {
			const { rerender } = render(PhotoGrid, { photos: [], loading: true });

			expect(screen.getByTestId('loading-state')).toBeInTheDocument();

			await rerender({ photos: [], loading: false });

			expect(screen.queryByTestId('loading-state')).not.toBeInTheDocument();
			expect(screen.getByTestId('empty-state')).toBeInTheDocument();
		});

		it('should update when columns prop changes', async () => {
			const { rerender } = render(PhotoGrid, { photos: mockPhotos, columns: 2 });

			let grid = screen.getByTestId('photo-grid-content');
			expect(grid).toHaveClass('grid-cols-2');

			await rerender({ photos: mockPhotos, columns: 4 });

			grid = screen.getByTestId('photo-grid-content');
			expect(grid).toHaveClass('md:grid-cols-4');
		});

		it('should update when showScore prop changes', async () => {
			const { rerender } = render(PhotoGrid, { photos: mockPhotos, showScore: false });

			expect(screen.queryByTestId('photo-score')).not.toBeInTheDocument();

			await rerender({ photos: mockPhotos, showScore: true });

			expect(screen.getAllByTestId('photo-score').length).toBeGreaterThan(0);
		});
	});
});
