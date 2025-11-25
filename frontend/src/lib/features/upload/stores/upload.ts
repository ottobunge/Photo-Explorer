// Upload store

import { writable } from 'svelte/store';
import type { UploadState } from '../types';

function createUploadStore() {
	const { subscribe, set, update } = writable<UploadState>({
		items: [],
		uploading: false
	});

	return {
		subscribe,

		addFiles(files: File[]) {
			update((state) => ({
				...state,
				items: [
					...state.items,
					...files.map((file) => ({
						id: crypto.randomUUID(),
						file,
						progress: 0,
						status: 'pending' as const
					}))
				]
			}));
		},

		removeItem(id: string) {
			update((state) => ({
				...state,
				items: state.items.filter((item) => item.id !== id)
			}));
		},

		updateProgress(id: string, progress: number) {
			update((state) => ({
				...state,
				items: state.items.map((item) =>
					item.id === id ? { ...item, progress, status: 'uploading' as const } : item
				)
			}));
		},

		setCompleted(id: string) {
			update((state) => ({
				...state,
				items: state.items.map((item) =>
					item.id === id ? { ...item, progress: 100, status: 'completed' as const } : item
				)
			}));
		},

		setFailed(id: string, error: string) {
			update((state) => ({
				...state,
				items: state.items.map((item) =>
					item.id === id ? { ...item, status: 'failed' as const, error } : item
				)
			}));
		},

		clear() {
			set({ items: [], uploading: false });
		},

		setUploading(uploading: boolean) {
			update((state) => ({ ...state, uploading }));
		}
	};
}

export const uploadStore = createUploadStore();
