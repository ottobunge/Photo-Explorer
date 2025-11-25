// Folders store

import { writable } from 'svelte/store';
import type { FoldersState, WatchedFolder } from '../types';

function createFoldersStore() {
	const { subscribe, set, update } = writable<FoldersState>({
		folders: [],
		loading: false,
		error: null
	});

	return {
		subscribe,

		async load() {
			update((state) => ({ ...state, loading: true, error: null }));

			try {
				const response = await fetch('/api/v1/folders');
				if (!response.ok) throw new Error('Failed to load folders');

				const data = await response.json();
				update((state) => ({
					...state,
					folders: data.data.folders,
					loading: false
				}));
			} catch (error) {
				update((state) => ({
					...state,
					error: error instanceof Error ? error.message : 'Failed to load folders',
					loading: false
				}));
			}
		},

		async add(path: string, options?: { name?: string; recursive?: boolean; autoAlbum?: boolean }) {
			const response = await fetch('/api/v1/folders', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					path,
					name: options?.name,
					recursive: options?.recursive ?? true,
					auto_album: options?.autoAlbum ?? false
				})
			});

			if (!response.ok) throw new Error('Failed to add folder');

			const data = await response.json();
			update((state) => ({
				...state,
				folders: [...state.folders, data.data]
			}));

			return data.data;
		},

		async triggerScan(folderId: string) {
			const response = await fetch(`/api/v1/folders/${folderId}/scan`, {
				method: 'POST'
			});

			if (!response.ok) throw new Error('Failed to trigger scan');
		},

		async remove(folderId: string, deletePhotos = false) {
			const response = await fetch(`/api/v1/folders/${folderId}?delete_photos=${deletePhotos}`, {
				method: 'DELETE'
			});

			if (!response.ok) throw new Error('Failed to remove folder');

			update((state) => ({
				...state,
				folders: state.folders.filter((f) => f.id !== folderId)
			}));
		}
	};
}

export const foldersStore = createFoldersStore();
