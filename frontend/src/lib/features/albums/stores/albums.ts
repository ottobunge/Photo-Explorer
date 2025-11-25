// Albums store

import { writable } from 'svelte/store';
import type { AlbumsState } from '../types';

function createAlbumsStore() {
	const { subscribe, update } = writable<AlbumsState>({
		albums: [],
		loading: false,
		error: null
	});

	return {
		subscribe,

		async load() {
			update((state) => ({ ...state, loading: true, error: null }));

			try {
				const response = await fetch('/api/v1/albums');
				if (!response.ok) throw new Error('Failed to load albums');

				const data = await response.json();
				update((state) => ({
					...state,
					albums: data.data.albums,
					loading: false
				}));
			} catch (error) {
				update((state) => ({
					...state,
					error: error instanceof Error ? error.message : 'Failed to load albums',
					loading: false
				}));
			}
		},

		async create(name: string, description?: string) {
			const response = await fetch('/api/v1/albums', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name, description })
			});

			if (!response.ok) throw new Error('Failed to create album');

			const data = await response.json();
			update((state) => ({
				...state,
				albums: [...state.albums, data.data]
			}));

			return data.data;
		},

		async delete(albumId: string) {
			const response = await fetch(`/api/v1/albums/${albumId}`, {
				method: 'DELETE'
			});

			if (!response.ok) throw new Error('Failed to delete album');

			update((state) => ({
				...state,
				albums: state.albums.filter((a) => a.id !== albumId)
			}));
		}
	};
}

export const albumsStore = createAlbumsStore();
