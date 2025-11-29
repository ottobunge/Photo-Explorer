import { describe, it, expect, beforeEach, vi } from 'vitest';
import { albumsStore } from './albums.svelte';
import { client } from '$lib/api/client';

vi.mock('$lib/api/client');

describe('albumsStore', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		albumsStore.reset();
	});

	describe('initial state', () => {
		it('should initialize with empty albums', () => {
			expect(albumsStore.albums).toEqual([]);
		});

		it('should initialize with loading false', () => {
			expect(albumsStore.loading).toBe(false);
		});

		it('should initialize with error null', () => {
			expect(albumsStore.error).toBeNull();
		});
	});

	describe('derived state', () => {
		it('should compute count correctly', () => {
			albumsStore.albums = [
				{ id: '1', name: 'Summer', description: '' },
				{ id: '2', name: 'Winter', description: '' }
			];
			expect(albumsStore.count).toBe(2);
		});

		it('should compute hasAlbums as false when empty', () => {
			albumsStore.albums = [];
			expect(albumsStore.hasAlbums).toBe(false);
		});

		it('should compute hasAlbums as true when has albums', () => {
			albumsStore.albums = [{ id: '1', name: 'Summer', description: '' }];
			expect(albumsStore.hasAlbums).toBe(true);
		});
	});

	describe('load()', () => {
		it('should load albums from API', async () => {
			const mockAlbums = [
				{ id: '1', name: 'Summer', description: 'Summer photos' },
				{ id: '2', name: 'Winter', description: 'Winter photos' }
			];

			vi.mocked(client.get).mockResolvedValue({
				success: true,
				data: { albums: mockAlbums }
			});

			await albumsStore.load();

			expect(albumsStore.albums).toEqual(mockAlbums);
			expect(albumsStore.loading).toBe(false);
			expect(albumsStore.error).toBeNull();
		});

		it('should set loading state during fetch', async () => {
			const loadPromise = (async () => {
				vi.mocked(client.get).mockImplementation(async () => {
					expect(albumsStore.loading).toBe(true);
					return { success: true, data: { albums: [] } };
				});

				await albumsStore.load();
			})();

			await loadPromise;
		});

		it('should handle API errors gracefully', async () => {
			const error = new Error('Failed to load albums');
			vi.mocked(client.get).mockRejectedValue(error);

			await albumsStore.load();

			expect(albumsStore.error).toBe('Failed to load albums');
			expect(albumsStore.albums).toEqual([]);
			expect(albumsStore.loading).toBe(false);
		});

		it('should handle generic errors', async () => {
			vi.mocked(client.get).mockRejectedValue(new Error('Network error'));

			await albumsStore.load();

			expect(albumsStore.error).toBe('Failed to load albums');
			expect(albumsStore.loading).toBe(false);
		});
	});

	describe('create()', () => {
		it('should create a new album', async () => {
			const newAlbum = { id: '1', name: 'Summer', description: 'Summer photos' };

			vi.mocked(client.post).mockResolvedValue({
				success: true,
				data: newAlbum
			});

			const result = await albumsStore.create('Summer', 'Summer photos');

			expect(result).toEqual(newAlbum);
			expect(albumsStore.albums).toContainEqual(newAlbum);
			expect(client.post).toHaveBeenCalledWith('/albums', {
				name: 'Summer',
				description: 'Summer photos'
			});
		});

		it('should create album without description', async () => {
			const newAlbum = { id: '1', name: 'Summer', description: '' };

			vi.mocked(client.post).mockResolvedValue({
				success: true,
				data: newAlbum
			});

			const result = await albumsStore.create('Summer');

			expect(result).toEqual(newAlbum);
			expect(client.post).toHaveBeenCalledWith('/albums', {
				name: 'Summer',
				description: undefined
			});
		});

		it('should add new album to existing albums', async () => {
			const existing = { id: '1', name: 'Summer', description: '' };
			const newAlbum = { id: '2', name: 'Winter', description: '' };

			albumsStore.albums = [existing];

			vi.mocked(client.post).mockResolvedValue({
				success: true,
				data: newAlbum
			});

			await albumsStore.create('Winter');

			expect(albumsStore.albums).toEqual([existing, newAlbum]);
		});

		it('should handle API errors during creation', async () => {
			vi.mocked(client.post).mockRejectedValue(
				new Error('Album already exists')
			);

			await expect(albumsStore.create('Summer')).rejects.toThrow();
			expect(albumsStore.error).toBe('Failed to create album');
		});

		it('should handle failed response', async () => {
			vi.mocked(client.post).mockResolvedValue({
				success: false,
				data: undefined
			});

			await expect(albumsStore.create('Summer')).rejects.toThrow(
				'Failed to create album'
			);
		});
	});

	describe('delete()', () => {
		beforeEach(() => {
			albumsStore.albums = [
				{ id: '1', name: 'Summer', description: '' },
				{ id: '2', name: 'Winter', description: '' },
				{ id: '3', name: 'Spring', description: '' }
			];
		});

		it('should delete an album by ID', async () => {
			vi.mocked(client.delete).mockResolvedValue({
				success: true,
				data: undefined
			});

			await albumsStore.delete('2');

			expect(albumsStore.albums).toEqual([
				{ id: '1', name: 'Summer', description: '' },
				{ id: '3', name: 'Spring', description: '' }
			]);
			expect(client.delete).toHaveBeenCalledWith('/albums/2');
		});

		it('should handle API errors during deletion', async () => {
			vi.mocked(client.delete).mockRejectedValue(
				new Error('Album not found')
			);

			await expect(albumsStore.delete('999')).rejects.toThrow();
			expect(albumsStore.error).toBe('Failed to delete album');
		});

		it('should not modify albums on error', async () => {
			const originalAlbums = [...albumsStore.albums];

			vi.mocked(client.delete).mockRejectedValue(
				new Error('Delete failed')
			);

			await expect(albumsStore.delete('1')).rejects.toThrow();
			expect(albumsStore.albums).toEqual(originalAlbums);
		});
	});

	describe('reset()', () => {
		it('should reset all state', () => {
			albumsStore.albums = [{ id: '1', name: 'Summer', description: '' }];
			albumsStore.loading = true;
			albumsStore.error = 'Some error';

			albumsStore.reset();

			expect(albumsStore.albums).toEqual([]);
			expect(albumsStore.loading).toBe(false);
			expect(albumsStore.error).toBeNull();
		});
	});

	describe('state reactivity', () => {
		it('should update count when albums change', () => {
			albumsStore.albums = [];
			expect(albumsStore.count).toBe(0);

			albumsStore.albums = [{ id: '1', name: 'Summer', description: '' }];
			expect(albumsStore.count).toBe(1);

			albumsStore.albums = [
				{ id: '1', name: 'Summer', description: '' },
				{ id: '2', name: 'Winter', description: '' }
			];
			expect(albumsStore.count).toBe(2);
		});

		it('should update hasAlbums reactively', () => {
			albumsStore.albums = [];
			expect(albumsStore.hasAlbums).toBe(false);

			albumsStore.albums = [{ id: '1', name: 'Summer', description: '' }];
			expect(albumsStore.hasAlbums).toBe(true);

			albumsStore.albums = [];
			expect(albumsStore.hasAlbums).toBe(false);
		});
	});
});
