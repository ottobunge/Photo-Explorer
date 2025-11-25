// Search store

import { writable } from 'svelte/store';
import type { SearchState, SearchFilters } from '../types';

function createSearchStore() {
	const { subscribe, set, update } = writable<SearchState>({
		query: '',
		results: [],
		filters: {},
		loading: false,
		error: null
	});

	return {
		subscribe,

		setQuery(query: string) {
			update((state) => ({ ...state, query }));
		},

		setFilters(filters: SearchFilters) {
			update((state) => ({ ...state, filters }));
		},

		async search(query: string, filters?: SearchFilters) {
			update((state) => ({ ...state, query, loading: true, error: null }));

			try {
				// TODO: Call search API
				const response = await fetch('/api/v1/search', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ query, filters })
				});

				if (!response.ok) throw new Error('Search failed');

				const data = await response.json();
				update((state) => ({
					...state,
					results: data.data.results,
					loading: false
				}));
			} catch (error) {
				update((state) => ({
					...state,
					error: error instanceof Error ? error.message : 'Search failed',
					loading: false
				}));
			}
		},

		clear() {
			set({
				query: '',
				results: [],
				filters: {},
				loading: false,
				error: null
			});
		}
	};
}

export const searchStore = createSearchStore();
