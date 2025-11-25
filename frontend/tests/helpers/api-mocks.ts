/**
 * API Mock Helpers for Playwright E2E Tests
 *
 * These helpers provide reusable, consistent API mocking patterns for E2E tests.
 * They standardize how we mock API responses using Playwright's `page.route()`.
 *
 * @example
 * // In a test:
 * await mockPhotosAPI.withPhotos(page, [photo1, photo2]);
 * await page.goto('/');
 * // Page will receive mocked photo data
 */

import type { Page } from '@playwright/test';
import type { MockPhoto, MockSearchResult } from '../fixtures/photos';
import type { MockConnector } from '../fixtures/connectors';
import type { MockAlbum } from '../fixtures/albums';

// ===== Photos API Mocks =====

export const mockPhotosAPI = {
	/**
	 * Mock GET /api/v1/photos endpoint with photo list
	 *
	 * @example
	 * await mockPhotosAPI.withPhotos(page, diversePhotos);
	 */
	async withPhotos(
		page: Page,
		photos: MockPhoto[],
		options: { page?: number; perPage?: number; total?: number } = {}
	): Promise<void> {
		const { page: pageNum = 1, perPage = 24, total } = options;
		const queryPattern = `**/api/v1/photos?page=${pageNum}&per_page=${perPage}*`;

		await page.route(queryPattern, async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: { photos },
					meta: { total: total !== undefined ? total : photos.length, page: pageNum, per_page: perPage }
				})
			});
		});
	},

	/**
	 * Mock GET /api/v1/photos for homepage (per_page=12)
	 *
	 * @example
	 * await mockPhotosAPI.forHomepage(page, recentPhotos);
	 */
	async forHomepage(page: Page, photos: MockPhoto[]): Promise<void> {
		await page.route('**/api/v1/photos?per_page=12', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: { photos },
					meta: { total: photos.length }
				})
			});
		});
	},

	/**
	 * Mock GET /api/v1/photos with error response
	 *
	 * @example
	 * await mockPhotosAPI.withError(page, 500, 'Internal Server Error');
	 */
	async withError(page: Page, status: number = 500, message: string = 'Server Error'): Promise<void> {
		await page.route('**/api/v1/photos*', async (route) => {
			await route.fulfill({
				status,
				contentType: 'application/json',
				body: JSON.stringify({
					success: false,
					error: message
				})
			});
		});
	},

	/**
	 * Mock GET /api/v1/photos with delayed response (for testing loading states)
	 *
	 * @example
	 * await mockPhotosAPI.withLoading(page, [], 2000); // 2 second delay
	 */
	async withLoading(page: Page, photos: MockPhoto[], delay: number): Promise<void> {
		await page.route('**/api/v1/photos*', async (route) => {
			await new Promise((resolve) => setTimeout(resolve, delay));
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: { photos },
					meta: { total: photos.length }
				})
			});
		});
	},

	/**
	 * Mock empty photos response
	 *
	 * @example
	 * await mockPhotosAPI.withEmpty(page);
	 */
	async withEmpty(page: Page): Promise<void> {
		await page.route('**/api/v1/photos*', async (route) => {
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
	}
};

// ===== Search API Mocks =====

export const mockSearchAPI = {
	/**
	 * Mock GET /api/v1/search endpoint with search results
	 *
	 * @example
	 * await mockSearchAPI.withResults(page, 'sunset', searchResults);
	 */
	async withResults(
		page: Page,
		query: string,
		results: MockSearchResult[],
		options: { limit?: number; offset?: number } = {}
	): Promise<void> {
		const { limit = 20, offset = 0 } = options;
		const encodedQuery = encodeURIComponent(query);
		const queryPattern = `**/api/v1/search?q=${encodedQuery}*`;

		await page.route(queryPattern, async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: {
						results,
						query_embedding_time_ms: 10,
						search_time_ms: 5
					},
					meta: { total: results.length, limit, offset }
				})
			});
		});
	},

	/**
	 * Mock empty search results
	 *
	 * @example
	 * await mockSearchAPI.withEmpty(page, 'nonexistent');
	 */
	async withEmpty(page: Page, query: string): Promise<void> {
		const encodedQuery = encodeURIComponent(query);
		await page.route(`**/api/v1/search?q=${encodedQuery}*`, async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: {
						results: [],
						query_embedding_time_ms: 10,
						search_time_ms: 5
					},
					meta: { total: 0, limit: 20, offset: 0 }
				})
			});
		});
	},

	/**
	 * Mock search API error
	 *
	 * @example
	 * await mockSearchAPI.withError(page, 'sunset', 500);
	 */
	async withError(page: Page, query: string, status: number = 500): Promise<void> {
		const encodedQuery = encodeURIComponent(query);
		await page.route(`**/api/v1/search?q=${encodedQuery}*`, async (route) => {
			await route.fulfill({
				status,
				contentType: 'application/json',
				body: JSON.stringify({
					success: false,
					error: 'Search failed'
				})
			});
		});
	}
};

// ===== Connectors API Mocks =====

export const mockConnectorsAPI = {
	/**
	 * Mock GET /api/v1/connectors endpoint
	 *
	 * @example
	 * await mockConnectorsAPI.withConnectors(page, diverseConnectors);
	 */
	async withConnectors(page: Page, connectors: MockConnector[]): Promise<void> {
		await page.route('**/api/v1/connectors', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: { connectors }
				})
			});
		});
	},

	/**
	 * Mock empty connectors response
	 *
	 * @example
	 * await mockConnectorsAPI.withEmpty(page);
	 */
	async withEmpty(page: Page): Promise<void> {
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
	}
};

// ===== Albums API Mocks =====

export const mockAlbumsAPI = {
	/**
	 * Mock GET /api/v1/albums endpoint
	 *
	 * @example
	 * await mockAlbumsAPI.withAlbums(page, diverseAlbums);
	 */
	async withAlbums(page: Page, albums: MockAlbum[]): Promise<void> {
		await page.route('**/api/v1/albums', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: { albums }
				})
			});
		});
	},

	/**
	 * Mock empty albums response
	 *
	 * @example
	 * await mockAlbumsAPI.withEmpty(page);
	 */
	async withEmpty(page: Page): Promise<void> {
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
	}
};

// ===== Face Clusters API Mocks =====

export const mockFaceClustersAPI = {
	/**
	 * Mock GET /api/v1/faces/clusters endpoint
	 *
	 * @example
	 * await mockFaceClustersAPI.withClusters(page, []);
	 */
	async withClusters(page: Page, clusters: any[]): Promise<void> {
		await page.route('**/api/v1/faces/clusters', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					success: true,
					data: { clusters }
				})
			});
		});
	},

	/**
	 * Mock empty face clusters response
	 *
	 * @example
	 * await mockFaceClustersAPI.withEmpty(page);
	 */
	async withEmpty(page: Page): Promise<void> {
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
	}
};

// ===== Composite Mocks (Common Scenarios) =====

/**
 * Set up all common API mocks for homepage
 * Mocks photos, connectors, albums, and face clusters
 *
 * @example
 * await setupHomepageMocks(page, { photos: recentPhotos });
 */
export async function setupHomepageMocks(
	page: Page,
	data: {
		photos?: MockPhoto[];
		connectors?: MockConnector[];
		albums?: MockAlbum[];
		clusters?: any[];
	} = {}
): Promise<void> {
	const {
		photos = [],
		connectors = [],
		albums = [],
		clusters = []
	} = data;

	await mockPhotosAPI.forHomepage(page, photos);
	await mockConnectorsAPI.withConnectors(page, connectors);
	await mockAlbumsAPI.withAlbums(page, albums);
	await mockFaceClustersAPI.withClusters(page, clusters);
}

/**
 * Set up all common API mocks for search page (browse mode)
 * Mocks photos, connectors, and albums
 *
 * @example
 * await setupSearchPageMocks(page, { photos: allPhotos });
 */
export async function setupSearchPageMocks(
	page: Page,
	data: {
		photos?: MockPhoto[];
		connectors?: MockConnector[];
		albums?: MockAlbum[];
	} = {}
): Promise<void> {
	const {
		photos = [],
		connectors = [],
		albums = []
	} = data;

	await mockPhotosAPI.withPhotos(page, photos);
	await mockConnectorsAPI.withConnectors(page, connectors);
	await mockAlbumsAPI.withAlbums(page, albums);
}

/**
 * Set up mocks for search mode (with query)
 *
 * @example
 * await setupSearchModeMocks(page, 'sunset', { results: searchResults });
 */
export async function setupSearchModeMocks(
	page: Page,
	query: string,
	data: {
		results?: MockSearchResult[];
		connectors?: MockConnector[];
		albums?: MockAlbum[];
	} = {}
): Promise<void> {
	const {
		results = [],
		connectors = [],
		albums = []
	} = data;

	await mockSearchAPI.withResults(page, query, results);
	await mockConnectorsAPI.withConnectors(page, connectors);
	await mockAlbumsAPI.withAlbums(page, albums);
}

/**
 * Set up mocks for empty state (no content)
 *
 * @example
 * await setupEmptyStateMocks(page);
 */
export async function setupEmptyStateMocks(page: Page): Promise<void> {
	await mockPhotosAPI.withEmpty(page);
	await mockConnectorsAPI.withEmpty(page);
	await mockAlbumsAPI.withEmpty(page);
	await mockFaceClustersAPI.withEmpty(page);
}
