// Folders store

import { writable } from 'svelte/store';
import { client, ApiError } from '$lib/api/client';
import type { FoldersState, WatchedFolder } from '../types';

interface FoldersStore {
	subscribe: (run: (value: FoldersState) => void) => () => void;
	load: () => Promise<void>;
	add: (path: string, options?: { name?: string; recursive?: boolean; autoAlbum?: boolean }) => Promise<WatchedFolder>;
	triggerScan: (folderId: string) => Promise<void>;
	remove: (folderId: string, deletePhotos?: boolean) => Promise<void>;
}

function createFoldersStore(): FoldersStore {
	const { subscribe, update } = writable<FoldersState>({
		folders: [],
		loading: false,
		error: null
	});

	return {
		subscribe,

		async load(): Promise<void> {
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

		async add(path: string, options?: { name?: string; recursive?: boolean; autoAlbum?: boolean }): Promise<WatchedFolder> {
			const result = await client.post<WatchedFolder>('/folders', {
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

		async triggerScan(folderId: string): Promise<void> {
			await client.post(`/folders/${folderId}/scan`);
		},

		async remove(folderId: string, deletePhotos: boolean = false): Promise<void> {
			await client.delete(`/folders/${folderId}?delete_photos=${deletePhotos}`);
			update((state) => ({
				...state,
				folders: state.folders.filter((f) => f.id !== folderId)
			}));
		}
	};
}

export const foldersStore = createFoldersStore();
