// Albums store

import { writable } from 'svelte/store';
import { client, ApiError } from '$lib/api/client';
import type { AlbumsState, Album } from '../types';

interface AlbumsStore {
	subscribe: (run: (value: AlbumsState) => void) => () => void;
	load: () => Promise<void>;
	create: (name: string, description?: string) => Promise<Album>;
	delete: (albumId: string) => Promise<void>;
}

function createAlbumsStore(): AlbumsStore {
	const { subscribe, update } = writable<AlbumsState>({
		albums: [],
		loading: false,
		error: null
	});

	return {
		subscribe,

		async load(): Promise<void> {
			update((state) => ({ ...state, loading: true, error: null }));

			try {
				const result = await client.get<{ albums: Album[] }>('/albums');
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

		async create(name: string, description?: string): Promise<Album> {
			const result = await client.post<Album>('/albums', { name, description });
			update((state) => ({
				...state,
				albums: [...state.albums, result.data]
			}));
			return result.data;
		},

		async delete(albumId: string): Promise<void> {
			await client.delete(`/albums/${albumId}`);
			update((state) => ({
				...state,
				albums: state.albums.filter((a) => a.id !== albumId)
			}));
		}
	};
}

export const albumsStore = createAlbumsStore();
