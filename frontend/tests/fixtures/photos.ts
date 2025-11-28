/**
 * Test fixtures for photo mock data
 *
 * These fixtures provide reusable, realistic mock data for photos
 * to be used across unit and E2E tests.
 */

export interface MockPhoto {
	id: string;
	filename: string;
	thumbnail_url: string | null;
	connector_type: 'local' | 'google_photos' | 'upload';
	width: number | null;
	height: number | null;
	taken_at: string | null;
	created_at: string;
	score?: number;
}

export interface MockSearchResult {
	photo: MockPhoto;
	score: number;
}

/**
 * Create a mock photo with default values that can be overridden
 *
 * @example
 * const photo = createMockPhoto({ filename: 'sunset.jpg', id: 'photo-123' });
 */
export function createMockPhoto(overrides: Partial<MockPhoto> = {}): MockPhoto {
	const id = overrides.id || `photo-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

	return {
		id,
		filename: overrides.filename || 'default-photo.jpg',
		thumbnail_url: overrides.thumbnail_url !== undefined
			? overrides.thumbnail_url
			: `/api/v1/photos/${id}/thumbnail`,
		connector_type: overrides.connector_type || 'local',
		width: overrides.width !== undefined ? overrides.width : 1920,
		height: overrides.height !== undefined ? overrides.height : 1080,
		taken_at: overrides.taken_at !== undefined ? overrides.taken_at : null,
		created_at: overrides.created_at || new Date().toISOString(),
		...(overrides.score !== undefined && { score: overrides.score })
	};
}

/**
 * Create a mock search result with photo and score
 *
 * @example
 * const result = createMockSearchResult({ score: 0.95 }, { filename: 'sunset.jpg' });
 */
export function createMockSearchResult(
	scoreOverrides: { score?: number } = {},
	photoOverrides: Partial<MockPhoto> = {}
): MockSearchResult {
	return {
		photo: createMockPhoto(photoOverrides),
		score: scoreOverrides.score !== undefined ? scoreOverrides.score : 0.85
	};
}

/**
 * Create multiple mock photos at once
 *
 * @example
 * const photos = createMockPhotos(3, (index) => ({ filename: `photo-${index}.jpg` }));
 */
export function createMockPhotos(
	count: number,
	overridesFn?: (index: number) => Partial<MockPhoto>
): MockPhoto[] {
	return Array.from({ length: count }, (_, index) =>
		createMockPhoto(overridesFn ? overridesFn(index) : {})
	);
}

/**
 * Create multiple mock search results at once
 *
 * @example
 * const results = createMockSearchResults(3, (index) => ({
 *   score: 0.9 - (index * 0.1),
 *   photo: { filename: `result-${index}.jpg` }
 * }));
 */
export function createMockSearchResults(
	count: number,
	overridesFn?: (index: number) => { score?: number; photo?: Partial<MockPhoto> }
): MockSearchResult[] {
	return Array.from({ length: count }, (_, index) => {
		const overrides = overridesFn ? overridesFn(index) : {};
		return createMockSearchResult(
			overrides.score !== undefined ? { score: overrides.score } : {},
			overrides.photo || {}
		);
	});
}

// Common test scenarios

/**
 * Photo with all fields populated
 */
export const completePhoto = createMockPhoto({
	id: 'complete-photo-id',
	filename: 'complete-photo.jpg',
	thumbnail_url: '/api/v1/photos/complete-photo-id/thumbnail',
	connector_type: 'local',
	width: 3000,
	height: 2000,
	taken_at: '2024-06-15T14:30:00Z',
	created_at: '2024-06-15T14:30:00Z'
});

/**
 * Photo without thumbnail (needs placeholder)
 */
export const photoWithoutThumbnail = createMockPhoto({
	id: 'no-thumbnail-id',
	filename: 'no-thumbnail.jpg',
	thumbnail_url: null
});

/**
 * Google Photos connector photo
 */
export const googlePhoto = createMockPhoto({
	id: 'google-photo-id',
	filename: 'google-photo.jpg',
	connector_type: 'google_photos',
	taken_at: '2024-01-01T12:00:00Z'
});

/**
 * Local connector photo
 */
export const localPhoto = createMockPhoto({
	id: 'local-photo-id',
	filename: 'local-photo.jpg',
	connector_type: 'local'
});

/**
 * Upload connector photo
 */
export const uploadPhoto = createMockPhoto({
	id: 'upload-photo-id',
	filename: 'upload-photo.jpg',
	connector_type: 'upload'
});

/**
 * Collection of diverse test photos
 */
export const diversePhotos = [
	createMockPhoto({
		id: 'photo-1',
		filename: 'sunset.jpg',
		connector_type: 'local',
		width: 4000,
		height: 3000,
		taken_at: '2024-06-15T19:30:00Z'
	}),
	createMockPhoto({
		id: 'photo-2',
		filename: 'mountain.jpg',
		connector_type: 'google_photos',
		width: 3000,
		height: 2000,
		taken_at: '2024-07-20T10:00:00Z'
	}),
	createMockPhoto({
		id: 'photo-3',
		filename: 'beach.jpg',
		connector_type: 'upload',
		width: 2400,
		height: 1600,
		taken_at: null
	})
];

/**
 * Collection of search results with varying scores
 */
export const searchResults = [
	createMockSearchResult(
		{ score: 0.95 },
		{ id: 'result-1', filename: 'high-score.jpg' }
	),
	createMockSearchResult(
		{ score: 0.75 },
		{ id: 'result-2', filename: 'medium-score.jpg' }
	),
	createMockSearchResult(
		{ score: 0.55 },
		{ id: 'result-3', filename: 'low-score.jpg' }
	)
];
