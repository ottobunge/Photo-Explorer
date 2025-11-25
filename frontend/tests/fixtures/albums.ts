/**
 * Test fixtures for album mock data
 *
 * These fixtures provide reusable, realistic mock data for albums
 * to be used across unit and E2E tests.
 */

export interface MockAlbum {
	id: string;
	name: string;
	description?: string | null;
	cover_photo_id?: string | null;
	photo_count?: number;
	created_at?: string;
	updated_at?: string;
}

/**
 * Create a mock album with default values that can be overridden
 *
 * @example
 * const album = createMockAlbum({ name: 'Summer Vacation', photo_count: 50 });
 */
export function createMockAlbum(overrides: Partial<MockAlbum> = {}): MockAlbum {
	const id = overrides.id || `album-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

	return {
		id,
		name: overrides.name || 'My Album',
		description: overrides.description !== undefined ? overrides.description : null,
		cover_photo_id: overrides.cover_photo_id !== undefined ? overrides.cover_photo_id : null,
		photo_count: overrides.photo_count !== undefined ? overrides.photo_count : 0,
		created_at: overrides.created_at || new Date().toISOString(),
		updated_at: overrides.updated_at || new Date().toISOString()
	};
}

/**
 * Create multiple mock albums at once
 *
 * @example
 * const albums = createMockAlbums(3, (index) => ({
 *   name: `Album ${index + 1}`,
 *   photo_count: index * 10
 * }));
 */
export function createMockAlbums(
	count: number,
	overridesFn?: (index: number) => Partial<MockAlbum>
): MockAlbum[] {
	return Array.from({ length: count }, (_, index) =>
		createMockAlbum(overridesFn ? overridesFn(index) : {})
	);
}

// Common test scenarios

/**
 * Album with all fields populated
 */
export const completeAlbum = createMockAlbum({
	id: 'complete-album-id',
	name: 'Complete Album',
	description: 'An album with all fields populated',
	cover_photo_id: 'cover-photo-id',
	photo_count: 25,
	created_at: '2024-01-01T10:00:00Z',
	updated_at: '2024-01-15T14:30:00Z'
});

/**
 * Empty album (no photos)
 */
export const emptyAlbum = createMockAlbum({
	id: 'empty-album-id',
	name: 'Empty Album',
	photo_count: 0
});

/**
 * Album without description
 */
export const albumWithoutDescription = createMockAlbum({
	id: 'no-desc-album-id',
	name: 'Album Without Description',
	description: null,
	photo_count: 10
});

/**
 * Album without cover photo
 */
export const albumWithoutCover = createMockAlbum({
	id: 'no-cover-album-id',
	name: 'Album Without Cover',
	cover_photo_id: null,
	photo_count: 15
});

/**
 * Collection of diverse albums
 */
export const diverseAlbums = [
	createMockAlbum({
		id: 'album-1',
		name: 'Summer Vacation 2024',
		description: 'Photos from our summer trip',
		photo_count: 50,
		cover_photo_id: 'summer-cover-id'
	}),
	createMockAlbum({
		id: 'album-2',
		name: 'Family Events',
		description: 'Birthday parties, gatherings, and celebrations',
		photo_count: 30,
		cover_photo_id: 'family-cover-id'
	}),
	createMockAlbum({
		id: 'album-3',
		name: 'Nature Photography',
		photo_count: 100
	})
];

/**
 * Albums ordered by photo count
 */
export const albumsBySize = [
	createMockAlbum({
		id: 'large-album',
		name: 'Large Album',
		photo_count: 500
	}),
	createMockAlbum({
		id: 'medium-album',
		name: 'Medium Album',
		photo_count: 100
	}),
	createMockAlbum({
		id: 'small-album',
		name: 'Small Album',
		photo_count: 10
	}),
	createMockAlbum({
		id: 'tiny-album',
		name: 'Tiny Album',
		photo_count: 1
	})
];

/**
 * Recently created albums
 */
export const recentAlbums = createMockAlbums(5, (index) => ({
	name: `Recent Album ${index + 1}`,
	photo_count: (index + 1) * 10,
	created_at: new Date(Date.now() - index * 86400000).toISOString() // Each day older
}));
