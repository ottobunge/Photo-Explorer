// Search store

import { writable } from 'svelte/store';
import { client, ApiError } from '$lib/api/client';
import type { SearchState, SearchFilters, SearchResult } from '../types';

interface SearchStore {
	subscribe: (run: (value: SearchState) => void) => () => void;
	setQuery: (query: string) => void;
	setFilters: (filters: SearchFilters) => void;
	search: (query: string, filters?: SearchFilters) => Promise<void>;
	clear: () => void;
}

function createSearchStore(): SearchStore {
	const { subscribe, set, update } = writable<SearchState>({
		query: '',
		results: [],
		filters: {},
		loading: false,
		error: null
	});

	return {
		subscribe,

		setQuery(query: string): void {
			update((state) => ({ ...state, query }));
		},

		setFilters(filters: SearchFilters): void {
			update((state) => ({ ...state, filters }));
		},

		async search(query: string, filters?: SearchFilters): Promise<void> {
			update((state) => ({ ...state, query, loading: true, error: null }));

			try {
				const result = await client.post<{ results: SearchResult[] }>('/search', { query, filters });
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

		clear(): void {
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
