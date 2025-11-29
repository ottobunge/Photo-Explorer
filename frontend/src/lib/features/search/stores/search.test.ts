import { describe, it, expect, beforeEach, vi } from 'vitest';
import { searchStore } from './search.svelte';
import { client } from '$lib/api/client';

vi.mock('$lib/api/client');

describe('searchStore', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		searchStore.reset();
	});

	describe('initial state', () => {
		it('should initialize with empty query', () => {
			expect(searchStore.query).toBe('');
		});

		it('should initialize with empty results', () => {
			expect(searchStore.results).toEqual([]);
		});

		it('should initialize with empty filters', () => {
			expect(searchStore.filters).toEqual({});
		});

		it('should initialize with loading false', () => {
			expect(searchStore.loading).toBe(false);
		});

		it('should initialize with error null', () => {
			expect(searchStore.error).toBeNull();
		});
	});

	describe('derived state', () => {
		it('should compute hasResults correctly', () => {
			searchStore.results = [];
			expect(searchStore.hasResults).toBe(false);

			searchStore.results = [{ id: '1', filename: 'photo.jpg', score: 0.95 }];
			expect(searchStore.hasResults).toBe(true);
		});

		it('should compute resultCount correctly', () => {
			searchStore.results = [];
			expect(searchStore.resultCount).toBe(0);

			searchStore.results = [
				{ id: '1', filename: 'photo1.jpg', score: 0.95 },
				{ id: '2', filename: 'photo2.jpg', score: 0.87 }
			];
			expect(searchStore.resultCount).toBe(2);
		});

		it('should compute hasQuery correctly', () => {
			searchStore.query = '';
			expect(searchStore.hasQuery).toBe(false);

			searchStore.query = '   ';
			expect(searchStore.hasQuery).toBe(false);

			searchStore.query = 'sunset';
			expect(searchStore.hasQuery).toBe(true);
		});
	});

	describe('setQuery()', () => {
		it('should set query string', () => {
			searchStore.setQuery('beach sunset');

			expect(searchStore.query).toBe('beach sunset');
		});

		it('should clear query', () => {
			searchStore.query = 'old query';

			searchStore.setQuery('');

			expect(searchStore.query).toBe('');
		});
	});

	describe('setFilters()', () => {
		it('should set filters object', () => {
			const filters = { date: '2024-01', color: 'blue' };

			searchStore.setFilters(filters);

			expect(searchStore.filters).toEqual(filters);
		});

		it('should replace previous filters', () => {
			searchStore.filters = { date: '2024-01' };

			searchStore.setFilters({ color: 'blue' });

			expect(searchStore.filters).toEqual({ color: 'blue' });
		});
	});

	describe('search()', () => {
		it('should search with query only', async () => {
			const mockResults = [
				{ id: '1', filename: 'photo1.jpg', score: 0.95 },
				{ id: '2', filename: 'photo2.jpg', score: 0.87 }
			];

			vi.mocked(client.post).mockResolvedValue({
				success: true,
				data: { results: mockResults }
			});

			await searchStore.search('sunset');

			expect(searchStore.query).toBe('sunset');
			expect(searchStore.results).toEqual(mockResults);
			expect(searchStore.loading).toBe(false);
			expect(searchStore.error).toBeNull();
			expect(client.post).toHaveBeenCalledWith('/search', {
				query: 'sunset',
				filters: {}
			});
		});

		it('should search with query and filters', async () => {
			const mockResults = [{ id: '1', filename: 'photo.jpg', score: 0.95 }];
			const filters = { color: 'blue' };

			vi.mocked(client.post).mockResolvedValue({
				success: true,
				data: { results: mockResults }
			});

			await searchStore.search('sunset', filters);

			expect(searchStore.query).toBe('sunset');
			expect(searchStore.filters).toEqual(filters);
			expect(searchStore.results).toEqual(mockResults);
			expect(client.post).toHaveBeenCalledWith('/search', {
				query: 'sunset',
				filters: filters
			});
		});

		it('should use existing filters if not provided', async () => {
			searchStore.filters = { color: 'blue' };

			vi.mocked(client.post).mockResolvedValue({
				success: true,
				data: { results: [] }
			});

			await searchStore.search('sunset');

			expect(client.post).toHaveBeenCalledWith('/search', {
				query: 'sunset',
				filters: { color: 'blue' }
			});
		});

		it('should set loading state during search', async () => {
			const states: { loading: boolean }[] = [];

			vi.mocked(client.post).mockImplementation(async () => {
				states.push({ loading: searchStore.loading });
				return { success: true, data: { results: [] } };
			});

			await searchStore.search('sunset');

			expect(states[0].loading).toBe(true);
			expect(searchStore.loading).toBe(false);
		});

		it('should clear error on successful search', async () => {
			searchStore.error = 'Previous error';

			vi.mocked(client.post).mockResolvedValue({
				success: true,
				data: { results: [] }
			});

			await searchStore.search('sunset');

			expect(searchStore.error).toBeNull();
		});

		it('should handle API errors', async () => {
			vi.mocked(client.post).mockRejectedValue(
				new Error('Search service unavailable')
			);

			await searchStore.search('sunset');

			expect(searchStore.error).toBe('Search failed');
			expect(searchStore.results).toEqual([]);
			expect(searchStore.loading).toBe(false);
		});

		it('should handle generic errors', async () => {
			vi.mocked(client.post).mockRejectedValue(new Error('Network error'));

			await searchStore.search('sunset');

			expect(searchStore.error).toBe('Search failed');
			expect(searchStore.loading).toBe(false);
		});
	});

	describe('clear()', () => {
		beforeEach(() => {
			searchStore.query = 'sunset';
			searchStore.results = [{ id: '1', filename: 'photo.jpg', score: 0.95 }];
			searchStore.filters = { color: 'blue' };
			searchStore.loading = true;
			searchStore.error = 'Some error';
		});

		it('should reset all state', () => {
			searchStore.clear();

			expect(searchStore.query).toBe('');
			expect(searchStore.results).toEqual([]);
			expect(searchStore.filters).toEqual({});
			expect(searchStore.loading).toBe(false);
			expect(searchStore.error).toBeNull();
		});

		it('should reset derived state', () => {
			searchStore.clear();

			expect(searchStore.hasResults).toBe(false);
			expect(searchStore.resultCount).toBe(0);
			expect(searchStore.hasQuery).toBe(false);
		});
	});

	describe('reset()', () => {
		it('should reset all state', () => {
			searchStore.query = 'sunset';
			searchStore.results = [{ id: '1', filename: 'photo.jpg', score: 0.95 }];

			searchStore.reset();

			expect(searchStore.query).toBe('');
			expect(searchStore.results).toEqual([]);
			expect(searchStore.filters).toEqual({});
			expect(searchStore.loading).toBe(false);
			expect(searchStore.error).toBeNull();
		});
	});

	describe('state reactivity', () => {
		it('should update hasResults when results change', () => {
			searchStore.results = [];
			expect(searchStore.hasResults).toBe(false);

			searchStore.results = [{ id: '1', filename: 'photo.jpg', score: 0.95 }];
			expect(searchStore.hasResults).toBe(true);

			searchStore.results = [];
			expect(searchStore.hasResults).toBe(false);
		});

		it('should update resultCount reactively', () => {
			searchStore.results = [];
			expect(searchStore.resultCount).toBe(0);

			searchStore.results = [
				{ id: '1', filename: 'photo.jpg', score: 0.95 }
			];
			expect(searchStore.resultCount).toBe(1);

			searchStore.results = [
				{ id: '1', filename: 'photo.jpg', score: 0.95 },
				{ id: '2', filename: 'photo2.jpg', score: 0.87 }
			];
			expect(searchStore.resultCount).toBe(2);
		});

		it('should update hasQuery reactively', () => {
			searchStore.query = '';
			expect(searchStore.hasQuery).toBe(false);

			searchStore.query = 'sunset';
			expect(searchStore.hasQuery).toBe(true);

			searchStore.query = '   ';
			expect(searchStore.hasQuery).toBe(false);
		});
	});

	describe('concurrent operations', () => {
		it('should handle multiple search requests', async () => {
			const results1 = [{ id: '1', filename: 'photo1.jpg', score: 0.95 }];
			const results2 = [{ id: '2', filename: 'photo2.jpg', score: 0.87 }];

			vi.mocked(client.post)
				.mockResolvedValueOnce({ success: true, data: { results: results1 } })
				.mockResolvedValueOnce({ success: true, data: { results: results2 } });

			await searchStore.search('beach');
			await searchStore.search('sunset');

			expect(searchStore.query).toBe('sunset');
			expect(searchStore.results).toEqual(results2);
		});
	});
});
