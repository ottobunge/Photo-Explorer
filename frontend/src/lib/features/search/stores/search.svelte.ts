// Search store using Svelte 5 runes

import { client, ApiError } from '$lib/api/client';
import type { SearchFilters, SearchResult } from '../types';

/**
 * Store for managing search state and results.
 * Uses Svelte 5 runes for reactive state management.
 */
class SearchStore {
	// State properties
	query: string = $state('');
	results: SearchResult[] = $state([]);
	filters: SearchFilters = $state({});
	loading: boolean = $state(false);
	error: string | null = $state(null);

	// Derived state
	hasResults: boolean = $derived(this.results.length > 0);
	resultCount: number = $derived(this.results.length);
	hasQuery: boolean = $derived(this.query.trim().length > 0);

	/**
	 * Set the search query
	 */
	setQuery(query: string): void {
		this.query = query;
	}

	/**
	 * Set search filters
	 */
	setFilters(filters: SearchFilters): void {
		this.filters = filters;
	}

	/**
	 * Perform a search with the given query and filters
	 */
	async search(query: string, filters?: SearchFilters): Promise<void> {
		this.query = query;
		if (filters !== undefined) {
			this.filters = filters;
		}
		this.loading = true;
		this.error = null;

		try {
			const result = await client.post<{ results: SearchResult[] }>('/search', {
				query,
				filters: filters ?? this.filters
			});

			if (result.success) {
				this.results = result.data.results;
			}
		} catch (err) {
			const message = err instanceof ApiError ? err.message : 'Search failed';
			this.error = message;
			console.error('Search failed:', err);
		} finally {
			this.loading = false;
		}
	}

	/**
	 * Clear search results and reset to initial state
	 */
	clear(): void {
		this.query = '';
		this.results = [];
		this.filters = {};
		this.loading = false;
		this.error = null;
	}

	/**
	 * Reset the store to initial state
	 */
	reset(): void {
		this.clear();
	}
}

// Export singleton instance
export const searchStore = new SearchStore();
