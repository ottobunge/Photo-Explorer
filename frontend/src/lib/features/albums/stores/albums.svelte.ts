// Albums store using Svelte 5 runes

import { client, ApiError } from '$lib/api/client';
import type { Album } from '../types';

/**
 * Store for managing albums.
 * Uses Svelte 5 runes for reactive state management.
 */
class AlbumsStore {
	// State properties
	albums: Album[] = $state([]);
	loading: boolean = $state(false);
	error: string | null = $state(null);

	// Derived state
	count: number = $derived(this.albums.length);
	hasAlbums: boolean = $derived(this.albums.length > 0);

	/**
	 * Load all albums from the API
	 */
	async load(): Promise<void> {
		this.loading = true;
		this.error = null;

		try {
			const result = await client.get<{ albums: Album[] }>('/albums');
			if (result.success) {
				this.albums = result.data.albums;
			}
		} catch (err) {
			const message = err instanceof ApiError ? err.message : 'Failed to load albums';
			this.error = message;
			console.error('Failed to load albums:', err);
		} finally {
			this.loading = false;
		}
	}

	/**
	 * Create a new album
	 */
	async create(name: string, description?: string): Promise<Album> {
		try {
			const result = await client.post<Album>('/albums', { name, description });
			if (result.success) {
				this.albums = [...this.albums, result.data];
				return result.data;
			}
			throw new Error('Failed to create album');
		} catch (err) {
			const message = err instanceof ApiError ? err.message : 'Failed to create album';
			this.error = message;
			console.error('Failed to create album:', err);
			throw err;
		}
	}

	/**
	 * Delete an album by ID
	 */
	async delete(albumId: string): Promise<void> {
		try {
			await client.delete(`/albums/${albumId}`);
			this.albums = this.albums.filter((a) => a.id !== albumId);
		} catch (err) {
			const message = err instanceof ApiError ? err.message : 'Failed to delete album';
			this.error = message;
			console.error('Failed to delete album:', err);
			throw err;
		}
	}

	/**
	 * Reset the store to initial state
	 */
	reset(): void {
		this.albums = [];
		this.loading = false;
		this.error = null;
	}
}

// Export singleton instance
export const albumsStore = new AlbumsStore();
