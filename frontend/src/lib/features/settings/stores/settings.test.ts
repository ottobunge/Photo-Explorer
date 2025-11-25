import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { settingsStore, connectors, googlePhotosConnectors, localConnectors } from './settings';

// Mock the API client
vi.mock('$lib/api/client', () => ({
	client: {
		get: vi.fn(),
		post: vi.fn(),
		patch: vi.fn(),
		delete: vi.fn()
	}
}));

import { client } from '$lib/api/client';

const mockGooglePhotosConnector = {
	id: 'gp-123',
	type: 'google_photos' as const,
	name: 'Google Photos',
	enabled: true,
	status: 'connected' as const,
	config: {},
	lastSync: '2024-01-15T10:00:00Z',
	errorMessage: null,
	createdAt: '2024-01-01T00:00:00Z',
	updatedAt: '2024-01-15T10:00:00Z'
};

const mockLocalConnector = {
	id: 'local-456',
	type: 'local' as const,
	name: 'My Photos',
	enabled: true,
	status: 'connected' as const,
	config: { path: '/home/user/Photos', recursive: true, watch: true },
	lastSync: '2024-01-14T08:00:00Z',
	errorMessage: null,
	createdAt: '2024-01-01T00:00:00Z',
	updatedAt: null
};

describe('settingsStore', () => {
	beforeEach(() => {
		settingsStore.reset();
		vi.clearAllMocks();
	});

	describe('loadConnectors', () => {
		it('should load connectors from the API', async () => {
			vi.mocked(client.get).mockResolvedValueOnce({
				success: true,
				data: { connectors: [mockGooglePhotosConnector, mockLocalConnector] }
			});

			await settingsStore.loadConnectors();

			const state = get(settingsStore);
			expect(state.connectors).toHaveLength(2);
			expect(state.loading).toBe(false);
			expect(state.error).toBeNull();
		});

		it('should handle errors when loading connectors', async () => {
			vi.mocked(client.get).mockRejectedValueOnce(new Error('Network error'));

			await settingsStore.loadConnectors();

			const state = get(settingsStore);
			expect(state.error).toBe('Network error');
			expect(state.loading).toBe(false);
		});
	});

	describe('addLocalFolder', () => {
		it('should add a local folder connector', async () => {
			vi.mocked(client.post).mockResolvedValueOnce({
				success: true,
				data: mockLocalConnector
			});

			const result = await settingsStore.addLocalFolder({
				path: '/home/user/Photos',
				recursive: true,
				watch: true,
				autoAlbum: false
			});

			expect(result).toEqual(mockLocalConnector);
			expect(get(connectors)).toContainEqual(mockLocalConnector);
		});
	});

	describe('removeConnector', () => {
		it('should remove a connector from the list', async () => {
			// First add some connectors
			vi.mocked(client.get).mockResolvedValueOnce({
				success: true,
				data: { connectors: [mockGooglePhotosConnector, mockLocalConnector] }
			});
			await settingsStore.loadConnectors();

			vi.mocked(client.delete).mockResolvedValueOnce({ success: true, data: {} });

			await settingsStore.removeConnector('local-456');

			const state = get(settingsStore);
			expect(state.connectors).toHaveLength(1);
			expect(state.connectors[0].id).toBe('gp-123');
		});
	});

	describe('toggleConnector', () => {
		it('should toggle connector enabled state', async () => {
			vi.mocked(client.get).mockResolvedValueOnce({
				success: true,
				data: { connectors: [mockLocalConnector] }
			});
			await settingsStore.loadConnectors();

			vi.mocked(client.patch).mockResolvedValueOnce({
				success: true,
				data: { ...mockLocalConnector, enabled: false }
			});

			await settingsStore.toggleConnector('local-456', false);

			const state = get(settingsStore);
			expect(state.connectors[0].enabled).toBe(false);
		});
	});

	describe('derived stores', () => {
		it('should filter google photos connectors', async () => {
			vi.mocked(client.get).mockResolvedValueOnce({
				success: true,
				data: { connectors: [mockGooglePhotosConnector, mockLocalConnector] }
			});
			await settingsStore.loadConnectors();

			expect(get(googlePhotosConnectors)).toHaveLength(1);
			expect(get(googlePhotosConnectors)[0].type).toBe('google_photos');
		});

		it('should filter local connectors', async () => {
			vi.mocked(client.get).mockResolvedValueOnce({
				success: true,
				data: { connectors: [mockGooglePhotosConnector, mockLocalConnector] }
			});
			await settingsStore.loadConnectors();

			expect(get(localConnectors)).toHaveLength(1);
			expect(get(localConnectors)[0].type).toBe('local');
		});
	});

	describe('loadSettings', () => {
		it('should load app settings from API', async () => {
			vi.mocked(client.get).mockResolvedValueOnce({
				success: true,
				data: {
					thumbnailQuality: 90,
					clipModel: 'ViT-L/14',
					faceDetectionEnabled: true,
					autoIndexNewPhotos: false
				}
			});

			await settingsStore.loadSettings();

			const state = get(settingsStore);
			expect(state.appSettings?.thumbnailQuality).toBe(90);
			expect(state.appSettings?.clipModel).toBe('ViT-L/14');
		});

		it('should use defaults when settings API fails', async () => {
			vi.mocked(client.get).mockRejectedValueOnce(new Error('Not found'));

			await settingsStore.loadSettings();

			const state = get(settingsStore);
			expect(state.appSettings?.thumbnailQuality).toBe(85);
			expect(state.appSettings?.clipModel).toBe('ViT-B/32');
		});
	});
});
