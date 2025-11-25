// Search store

import { writable } from 'svelte/store';
import { client, ApiError } from '$lib/api/client';
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
				const result = await client.post<{ results: any[] }>('/search', { query, filters });
				update((state) => ({
					...state,
					results: result.data.results,
					loading: false
				}));
			} catch (error) {
				const message = error instanceof ApiError ? error.message : 'Search failed';
				update((state) => ({
					...state,
					error: message,
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
