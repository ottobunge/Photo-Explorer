// Upload store

import { writable } from 'svelte/store';
import type { UploadState } from '../types';

interface UploadStore {
	subscribe: (run: (value: UploadState) => void) => () => void;
	addFiles: (files: File[]) => void;
	removeItem: (id: string) => void;
	updateProgress: (id: string, progress: number) => void;
	setCompleted: (id: string) => void;
	setFailed: (id: string, error: string) => void;
	clear: () => void;
	setUploading: (uploading: boolean) => void;
}

function createUploadStore(): UploadStore {
	const { subscribe, set, update } = writable<UploadState>({
		items: [],
		uploading: false
	});

	return {
		subscribe,

		addFiles(files: File[]): void {
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

		removeItem(id: string): void {
			update((state) => ({
				...state,
				items: state.items.filter((item) => item.id !== id)
			}));
		},

		updateProgress(id: string, progress: number): void {
			update((state) => ({
				...state,
				items: state.items.map((item) =>
					item.id === id ? { ...item, progress, status: 'uploading' as const } : item
				)
			}));
		},

		setCompleted(id: string): void {
			update((state) => ({
				...state,
				items: state.items.map((item) =>
					item.id === id ? { ...item, progress: 100, status: 'completed' as const } : item
				)
			}));
		},

		setFailed(id: string, error: string): void {
			update((state) => ({
				...state,
				items: state.items.map((item) =>
					item.id === id ? { ...item, status: 'failed' as const, error } : item
				)
			}));
		},

		clear(): void {
			set({ items: [], uploading: false });
		},

		setUploading(uploading: boolean): void {
			update((state) => ({ ...state, uploading }));
		}
	};
}

export const uploadStore = createUploadStore();
