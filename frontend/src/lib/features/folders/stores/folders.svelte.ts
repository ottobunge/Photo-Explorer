// Folders store using Svelte 5 runes

import { client, ApiError } from '$lib/api/client';
import type { WatchedFolder } from '../types';

interface AddFolderOptions {
	name?: string;
	recursive?: boolean;
	autoAlbum?: boolean;
}

/**
 * Store for managing watched folders.
 * Uses Svelte 5 runes for reactive state management.
 */
class FoldersStore {
	// State properties
	folders: WatchedFolder[] = $state([]);
	loading: boolean = $state(false);
	error: string | null = $state(null);

	// Derived state
	count: number = $derived(this.folders.length);
	hasFolders: boolean = $derived(this.folders.length > 0);

	/**
	 * Load all watched folders from the API
	 */
	async load(): Promise<void> {
		this.loading = true;
		this.error = null;

		try {
			const result = await client.get<{ folders: WatchedFolder[] }>('/folders');
			if (result.success) {
				this.folders = result.data.folders;
			}
		} catch (err) {
			const message = err instanceof ApiError ? err.message : 'Failed to load folders';
			this.error = message;
			console.error('Failed to load folders:', err);
		} finally {
			this.loading = false;
		}
	}

	/**
	 * Add a new watched folder
	 */
	async add(path: string, options?: AddFolderOptions): Promise<WatchedFolder> {
		try {
			const result = await client.post<WatchedFolder>('/folders', {
				path,
				name: options?.name,
				recursive: options?.recursive ?? true,
				auto_album: options?.autoAlbum ?? false
			});

			if (result.success) {
				this.folders = [...this.folders, result.data];
				return result.data;
			}
			throw new Error('Failed to add folder');
		} catch (err) {
			const message = err instanceof ApiError ? err.message : 'Failed to add folder';
			this.error = message;
			console.error('Failed to add folder:', err);
			throw err;
		}
	}

	/**
	 * Trigger a manual scan of a watched folder
	 */
	async triggerScan(folderId: string): Promise<void> {
		try {
			await client.post(`/folders/${folderId}/scan`);
		} catch (err) {
			const message = err instanceof ApiError ? err.message : 'Failed to trigger scan';
			this.error = message;
			console.error('Failed to trigger scan:', err);
			throw err;
		}
	}

	/**
	 * Remove a watched folder
	 */
	async remove(folderId: string, deletePhotos: boolean): Promise<void> {
		try {
			await client.delete(`/folders/${folderId}?delete_photos=${deletePhotos}`);
			this.folders = this.folders.filter((f) => f.id !== folderId);
		} catch (err) {
			const message = err instanceof ApiError ? err.message : 'Failed to remove folder';
			this.error = message;
			console.error('Failed to remove folder:', err);
			throw err;
		}
	}

	/**
	 * Reset the store to initial state
	 */
	reset(): void {
		this.folders = [];
		this.loading = false;
		this.error = null;
	}
}

// Export singleton instance
export const foldersStore = new FoldersStore();
