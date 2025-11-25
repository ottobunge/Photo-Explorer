// Folders store

import { writable } from 'svelte/store';
import { client, ApiError } from '$lib/api/client';
import type { FoldersState } from '../types';

function createFoldersStore() {
	const { subscribe, update } = writable<FoldersState>({
		folders: [],
		loading: false,
		error: null
	});

	return {
		subscribe,

		async load() {
			update((state) => ({ ...state, loading: true, error: null }));

			try {
				const result = await client.get<{ folders: any[] }>('/folders');
				update((state) => ({
					...state,
					folders: result.data.folders,
					loading: false
				}));
			} catch (error) {
				const message = error instanceof ApiError ? error.message : 'Failed to load folders';
				update((state) => ({
					...state,
					error: message,
					loading: false
				}));
			}
		},

		async add(path: string, options?: { name?: string; recursive?: boolean; autoAlbum?: boolean }) {
			const result = await client.post<any>('/folders', {
				path,
				name: options?.name,
				recursive: options?.recursive ?? true,
				auto_album: options?.autoAlbum ?? false
			});

			update((state) => ({
				...state,
				folders: [...state.folders, result.data]
			}));

			return result.data;
		},

		async triggerScan(folderId: string) {
			await client.post(`/folders/${folderId}/scan`);
		},

		async remove(folderId: string, deletePhotos = false) {
			await client.delete(`/folders/${folderId}?delete_photos=${deletePhotos}`);
			update((state) => ({
				...state,
				folders: state.folders.filter((f) => f.id !== folderId)
			}));
		}
	};
}

export const foldersStore = createFoldersStore();
