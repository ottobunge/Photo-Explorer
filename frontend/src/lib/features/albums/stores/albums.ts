// Albums store

import { writable } from 'svelte/store';
import { client, ApiError } from '$lib/api/client';
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
				const result = await client.get<{ albums: any[] }>('/albums');
				update((state) => ({
					...state,
					albums: result.data.albums,
					loading: false
				}));
			} catch (error) {
				const message = error instanceof ApiError ? error.message : 'Failed to load albums';
				update((state) => ({
					...state,
					error: message,
					loading: false
				}));
			}
		},

		async create(name: string, description?: string) {
			const result = await client.post<any>('/albums', { name, description });
			update((state) => ({
				...state,
				albums: [...state.albums, result.data]
			}));
			return result.data;
		},

		async delete(albumId: string) {
			await client.delete(`/albums/${albumId}`);
			update((state) => ({
				...state,
				albums: state.albums.filter((a) => a.id !== albumId)
			}));
		}
	};
}

export const albumsStore = createAlbumsStore();
