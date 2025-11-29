import { describe, it, expect, beforeEach, vi } from 'vitest';
import { foldersStore } from './folders.svelte';
import { client } from '$lib/api/client';

vi.mock('$lib/api/client');

describe('foldersStore', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		foldersStore.reset();
	});

	describe('initial state', () => {
		it('should initialize with empty folders', () => {
			expect(foldersStore.folders).toEqual([]);
		});

		it('should initialize with loading false', () => {
			expect(foldersStore.loading).toBe(false);
		});

		it('should initialize with error null', () => {
			expect(foldersStore.error).toBeNull();
		});
	});

	describe('derived state', () => {
		it('should compute count correctly', () => {
			foldersStore.folders = [
				{ id: '1', path: '/home/photos', name: 'Photos', recursive: true },
				{ id: '2', path: '/home/videos', name: 'Videos', recursive: false }
			];
			expect(foldersStore.count).toBe(2);
		});

		it('should compute hasFolders as false when empty', () => {
			foldersStore.folders = [];
			expect(foldersStore.hasFolders).toBe(false);
		});

		it('should compute hasFolders as true when has folders', () => {
			foldersStore.folders = [
				{ id: '1', path: '/home/photos', name: 'Photos', recursive: true }
			];
			expect(foldersStore.hasFolders).toBe(true);
		});
	});

	describe('load()', () => {
		it('should load folders from API', async () => {
			const mockFolders = [
				{ id: '1', path: '/home/photos', name: 'Photos', recursive: true },
				{ id: '2', path: '/home/videos', name: 'Videos', recursive: false }
			];

			vi.mocked(client.get).mockResolvedValue({
				success: true,
				data: { folders: mockFolders }
			});

			await foldersStore.load();

			expect(foldersStore.folders).toEqual(mockFolders);
			expect(foldersStore.loading).toBe(false);
			expect(foldersStore.error).toBeNull();
		});

		it('should set loading state during fetch', async () => {
			const states: boolean[] = [];

			vi.mocked(client.get).mockImplementation(async () => {
				states.push(foldersStore.loading);
				return { success: true, data: { folders: [] } };
			});

			await foldersStore.load();

			expect(states[0]).toBe(true);
			expect(foldersStore.loading).toBe(false);
		});

		it('should handle API errors gracefully', async () => {
			vi.mocked(client.get).mockRejectedValue(
				new Error('Failed to fetch folders')
			);

			await foldersStore.load();

			expect(foldersStore.error).toBe('Failed to load folders');
			expect(foldersStore.folders).toEqual([]);
			expect(foldersStore.loading).toBe(false);
		});

		it('should handle generic errors', async () => {
			vi.mocked(client.get).mockRejectedValue(new Error('Network error'));

			await foldersStore.load();

			expect(foldersStore.error).toBe('Failed to load folders');
			expect(foldersStore.loading).toBe(false);
		});
	});

	describe('add()', () => {
		it('should add a new folder with defaults', async () => {
			const newFolder = {
				id: '1',
				path: '/home/photos',
				name: 'Photos',
				recursive: true
			};

			vi.mocked(client.post).mockResolvedValue({
				success: true,
				data: newFolder
			});

			const result = await foldersStore.add('/home/photos');

			expect(result).toEqual(newFolder);
			expect(foldersStore.folders).toContainEqual(newFolder);
			expect(client.post).toHaveBeenCalledWith('/folders', {
				path: '/home/photos',
				name: undefined,
				recursive: true,
				auto_album: false
			});
		});

		it('should add a new folder with custom options', async () => {
			const newFolder = {
				id: '1',
				path: '/home/photos',
				name: 'My Photos',
				recursive: false
			};

			vi.mocked(client.post).mockResolvedValue({
				success: true,
				data: newFolder
			});

			const result = await foldersStore.add('/home/photos', {
				name: 'My Photos',
				recursive: false,
				autoAlbum: true
			});

			expect(result).toEqual(newFolder);
			expect(client.post).toHaveBeenCalledWith('/folders', {
				path: '/home/photos',
				name: 'My Photos',
				recursive: false,
				auto_album: true
			});
		});

		it('should append folder to existing folders', async () => {
			const existing = { id: '1', path: '/home/photos', name: 'Photos', recursive: true };
			const newFolder = { id: '2', path: '/home/videos', name: 'Videos', recursive: false };

			foldersStore.folders = [existing];

			vi.mocked(client.post).mockResolvedValue({
				success: true,
				data: newFolder
			});

			await foldersStore.add('/home/videos');

			expect(foldersStore.folders).toEqual([existing, newFolder]);
		});

		it('should handle API errors during add', async () => {
			vi.mocked(client.post).mockRejectedValue(
				new Error('Path is already monitored')
			);

			await expect(foldersStore.add('/home/photos')).rejects.toThrow();
			expect(foldersStore.error).toBe('Failed to add folder');
		});

		it('should handle failed response', async () => {
			vi.mocked(client.post).mockResolvedValue({
				success: false,
				data: undefined
			});

			await expect(foldersStore.add('/home/photos')).rejects.toThrow(
				'Failed to add folder'
			);
		});
	});

	describe('triggerScan()', () => {
		it('should trigger a manual folder scan', async () => {
			vi.mocked(client.post).mockResolvedValue({
				success: true,
				data: undefined
			});

			await foldersStore.triggerScan('folder-1');

			expect(client.post).toHaveBeenCalledWith('/folders/folder-1/scan');
		});

		it('should handle API errors during scan', async () => {
			vi.mocked(client.post).mockRejectedValue(
				new Error('Folder not found')
			);

			await expect(foldersStore.triggerScan('invalid')).rejects.toThrow();
			expect(foldersStore.error).toBe('Failed to trigger scan');
		});
	});

	describe('remove()', () => {
		beforeEach(() => {
			foldersStore.folders = [
				{ id: '1', path: '/home/photos', name: 'Photos', recursive: true },
				{ id: '2', path: '/home/videos', name: 'Videos', recursive: false },
				{ id: '3', path: '/home/music', name: 'Music', recursive: true }
			];
		});

		it('should remove a folder without deleting photos', async () => {
			vi.mocked(client.delete).mockResolvedValue({
				success: true,
				data: undefined
			});

			await foldersStore.remove('2', false);

			expect(foldersStore.folders).toEqual([
				{ id: '1', path: '/home/photos', name: 'Photos', recursive: true },
				{ id: '3', path: '/home/music', name: 'Music', recursive: true }
			]);
			expect(client.delete).toHaveBeenCalledWith('/folders/2?delete_photos=false');
		});

		it('should remove a folder and delete photos', async () => {
			vi.mocked(client.delete).mockResolvedValue({
				success: true,
				data: undefined
			});

			await foldersStore.remove('1', true);

			expect(foldersStore.folders).toEqual([
				{ id: '2', path: '/home/videos', name: 'Videos', recursive: false },
				{ id: '3', path: '/home/music', name: 'Music', recursive: true }
			]);
			expect(client.delete).toHaveBeenCalledWith('/folders/1?delete_photos=true');
		});

		it('should handle API errors during removal', async () => {
			const originalFolders = [...foldersStore.folders];

			vi.mocked(client.delete).mockRejectedValue(
				new Error('Cannot delete folder')
			);

			await expect(foldersStore.remove('1', false)).rejects.toThrow();
			expect(foldersStore.error).toBe('Failed to remove folder');
			expect(foldersStore.folders).toEqual(originalFolders);
		});

		it('should not modify folders on error', async () => {
			const originalFolders = [...foldersStore.folders];

			vi.mocked(client.delete).mockRejectedValue(
				new Error('Error')
			);

			await expect(foldersStore.remove('999', false)).rejects.toThrow();
			expect(foldersStore.folders).toEqual(originalFolders);
		});
	});

	describe('reset()', () => {
		it('should reset all state', () => {
			foldersStore.folders = [
				{ id: '1', path: '/home/photos', name: 'Photos', recursive: true }
			];
			foldersStore.loading = true;
			foldersStore.error = 'Some error';

			foldersStore.reset();

			expect(foldersStore.folders).toEqual([]);
			expect(foldersStore.loading).toBe(false);
			expect(foldersStore.error).toBeNull();
		});
	});

	describe('state reactivity', () => {
		it('should update count when folders change', () => {
			foldersStore.folders = [];
			expect(foldersStore.count).toBe(0);

			foldersStore.folders = [
				{ id: '1', path: '/home/photos', name: 'Photos', recursive: true }
			];
			expect(foldersStore.count).toBe(1);

			foldersStore.folders = [
				{ id: '1', path: '/home/photos', name: 'Photos', recursive: true },
				{ id: '2', path: '/home/videos', name: 'Videos', recursive: false }
			];
			expect(foldersStore.count).toBe(2);
		});

		it('should update hasFolders reactively', () => {
			foldersStore.folders = [];
			expect(foldersStore.hasFolders).toBe(false);

			foldersStore.folders = [
				{ id: '1', path: '/home/photos', name: 'Photos', recursive: true }
			];
			expect(foldersStore.hasFolders).toBe(true);

			foldersStore.folders = [];
			expect(foldersStore.hasFolders).toBe(false);
		});
	});

	describe('error handling', () => {
		it('should clear error on successful operation', async () => {
			foldersStore.error = 'Previous error';

			vi.mocked(client.get).mockResolvedValue({
				success: true,
				data: { folders: [] }
			});

			await foldersStore.load();

			expect(foldersStore.error).toBeNull();
		});

		it('should update error on next error', async () => {
			foldersStore.error = null;

			vi.mocked(client.get).mockRejectedValue(
				new Error('First error')
			);

			await foldersStore.load();

			const firstError = foldersStore.error;
			expect(firstError).toBe('Failed to load folders');

			vi.mocked(client.get).mockRejectedValue(
				new Error('Second error')
			);

			await foldersStore.load();

			expect(foldersStore.error).toBe('Failed to load folders');
			expect(foldersStore.error).toBe(firstError);
		});
	});
});
