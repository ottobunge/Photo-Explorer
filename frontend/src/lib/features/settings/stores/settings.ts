// Settings store for managing connectors and app settings

import { writable, derived } from 'svelte/store';
import { client } from '$lib/api/client';
import type {
	Connector,
	ConnectorType,
	ConnectorStatus,
	GooglePhotosStatus,
	AppSettings,
	AppSettingsApiResponse,
	SettingsState,
	LocalFolderConfig,
	SyncStatus,
	HFModel,
	DownloadProgress,
	ActiveModels,
	PickerSession,
	PickerSessionStatus,
	PickerImportResult
} from '../types';

// Helper to convert snake_case API response to camelCase
function mapApiSettingsToAppSettings(api: AppSettingsApiResponse): AppSettings {
	return {
		thumbnailQuality: api.thumbnail_quality,
		clipModel: api.clip_model,
		faceDetectionEnabled: api.face_detection_enabled,
		autoIndexNewPhotos: api.auto_index_new_photos
	};
}

// Helper to convert camelCase settings to snake_case for API
function mapAppSettingsToApi(settings: Partial<AppSettings>): Record<string, unknown> {
	const result: Record<string, unknown> = {};
	if (settings.thumbnailQuality !== undefined) result.thumbnail_quality = settings.thumbnailQuality;
	if (settings.clipModel !== undefined) result.clip_model = settings.clipModel;
	if (settings.faceDetectionEnabled !== undefined) result.face_detection_enabled = settings.faceDetectionEnabled;
	if (settings.autoIndexNewPhotos !== undefined) result.auto_index_new_photos = settings.autoIndexNewPhotos;
	return result;
}

const initialState: SettingsState = {
	connectors: [],
	googlePhotosStatus: null,
	appSettings: null,
	activeModels: null,
	downloadedModels: [],
	recommendedModels: {},
	loading: false,
	error: null
};

function createSettingsStore() {
	const { subscribe, set, update } = writable<SettingsState>(initialState);

	return {
		subscribe,

		// Load all connectors
		async loadConnectors(): Promise<void> {
			update((state) => ({ ...state, loading: true, error: null }));

			try {
				interface ConnectorApiResponse {
					id: string;
					type: string;
					name: string;
					enabled: boolean;
					status: string;
					config: Record<string, unknown>;
					last_sync: string | null;
					error_message: string | null;
					created_at: string;
					updated_at: string | null;
				}

				const response = await client.get<{ connectors: ConnectorApiResponse[] }>('/connectors');

				// Transform snake_case to camelCase
				const connectors: Connector[] = response.data.connectors.map((c) => ({
					id: c.id,
					type: c.type as ConnectorType,
					name: c.name,
					enabled: c.enabled,
					status: c.status as ConnectorStatus,
					config: c.config,
					lastSync: c.last_sync,
					errorMessage: c.error_message,
					createdAt: c.created_at,
					updatedAt: c.updated_at
				}));

				update((state) => ({
					...state,
					connectors,
					loading: false
				}));
			} catch (err) {
				update((state) => ({
					...state,
					loading: false,
					error: err instanceof Error ? err.message : 'Failed to load connectors'
				}));
			}
		},

		// Get Google Photos auth URL and redirect
		async connectGooglePhotos(): Promise<string> {
			const redirectUri = `${window.location.origin}/settings/google-photos/callback`;
			const response = await client.get<{ auth_url: string }>('/connectors/google-photos/auth-url', {
				redirect_uri: redirectUri
			});
			return response.data.auth_url;
		},

		// Handle Google Photos OAuth callback
		async handleGooglePhotosCallback(code: string): Promise<{ connected: boolean; connectorId: string }> {
			const redirectUri = `${window.location.origin}/settings/google-photos/callback`;
			const response = await client.post<{ connected: boolean; connector_id: string }>('/connectors/google-photos/callback', {
				code,
				redirect_uri: redirectUri
			});

			// Refresh connectors list after successful connection
			await this.loadConnectors();

			return {
				connected: response.data.connected,
				connectorId: response.data.connector_id
			};
		},

		// Get Google Photos connection status
		async getGooglePhotosStatus(): Promise<void> {
			try {
				const response = await client.get<GooglePhotosStatus>('/connectors/google-photos/status');
				update((state) => ({
					...state,
					googlePhotosStatus: response.data
				}));
			} catch {
				update((state) => ({
					...state,
					googlePhotosStatus: { connected: false, email: null, photosIndexed: 0, lastSync: null }
				}));
			}
		},

		// Disconnect Google Photos
		async disconnectGooglePhotos(): Promise<void> {
			await client.delete('/connectors/google-photos');
			update((state) => ({
				...state,
				connectors: state.connectors.filter((c) => c.type !== 'google_photos'),
				googlePhotosStatus: { connected: false, email: null, photosIndexed: 0, lastSync: null }
			}));
		},

		// Add a local folder connector
		async addLocalFolder(config: LocalFolderConfig): Promise<Connector> {
			const response = await client.post<Connector>('/connectors/local', config);

			update((state) => ({
				...state,
				connectors: [...state.connectors, response.data]
			}));

			return response.data;
		},

		// Remove a connector
		async removeConnector(id: string): Promise<void> {
			await client.delete(`/connectors/${id}`);
			update((state) => ({
				...state,
				connectors: state.connectors.filter((c) => c.id !== id)
			}));
		},

		// Toggle connector enabled state
		async toggleConnector(id: string, enabled: boolean): Promise<void> {
			await client.patch<Connector>(`/connectors/${id}`, { enabled });
			update((state) => ({
				...state,
				connectors: state.connectors.map((c) => (c.id === id ? { ...c, enabled } : c))
			}));
		},

		// Trigger sync for a connector
		async triggerSync(id: string): Promise<void> {
			update((state) => ({
				...state,
				connectors: state.connectors.map((c) =>
					c.id === id ? { ...c, status: 'syncing' as const } : c
				)
			}));

			try {
				await client.post(`/connectors/${id}/sync`);
			} catch (err) {
				update((state) => ({
					...state,
					connectors: state.connectors.map((c) =>
						c.id === id ? { ...c, status: 'error' as const } : c
					)
				}));
				throw err;
			}
		},

		// Get sync status for a connector
		async getSyncStatus(id: string): Promise<SyncStatus> {
			const response = await client.get<SyncStatus>(`/connectors/${id}/sync/status`);
			return response.data;
		},

		// Load app settings
		async loadSettings(): Promise<void> {
			try {
				const response = await client.get<AppSettingsApiResponse>('/settings');
				update((state) => ({
					...state,
					appSettings: mapApiSettingsToAppSettings(response.data)
				}));
			} catch {
				// Use defaults if settings don't exist yet
				update((state) => ({
					...state,
					appSettings: {
						thumbnailQuality: 85,
						clipModel: 'ViT-B/32',
						faceDetectionEnabled: true,
						autoIndexNewPhotos: true
					}
				}));
			}
		},

		// Update app settings
		async updateSettings(settings: Partial<AppSettings>): Promise<void> {
			const apiPayload = mapAppSettingsToApi(settings);
			const response = await client.patch<AppSettingsApiResponse>('/settings', apiPayload);
			update((state) => ({
				...state,
				appSettings: mapApiSettingsToAppSettings(response.data)
			}));
		},

		// Clear error
		clearError(): void {
			update((state) => ({ ...state, error: null }));
		},

		// Reset store
		reset(): void {
			set(initialState);
		},

		// ==================
		// Model Management
		// ==================

		// Load active models configuration
		async loadActiveModels(): Promise<void> {
			try {
				const response = await client.get<ActiveModels>('/models/active');
				update((state) => ({
					...state,
					activeModels: response.data
				}));
			} catch {
				// Ignore errors, models may not be configured yet
			}
		},

		// Load downloaded models
		async loadDownloadedModels(): Promise<void> {
			try {
				const response = await client.get<{ models: string[] }>('/models/downloaded');
				update((state) => ({
					...state,
					downloadedModels: response.data.models
				}));
			} catch {
				// Ignore errors
			}
		},

		// Load recommended models
		async loadRecommendedModels(): Promise<void> {
			try {
				const response = await client.get<{ recommendations: Record<string, HFModel[]> }>('/models/recommended');
				update((state) => ({
					...state,
					recommendedModels: response.data.recommendations
				}));
			} catch {
				// Ignore errors
			}
		},

		// Search for models on Hugging Face
		async searchModels(query: string, task?: string): Promise<HFModel[]> {
			const params: Record<string, string> = { query };
			if (task) params.task = task;

			const response = await client.get<{ models: HFModel[] }>('/models/search', params);
			return response.data.models;
		},

		// Get model info
		async getModelInfo(modelId: string): Promise<HFModel | null> {
			try {
				const response = await client.get<HFModel>(`/models/info/${modelId}`);
				return response.data;
			} catch {
				return null;
			}
		},

		// Download a model
		async downloadModel(modelId: string): Promise<DownloadProgress> {
			const response = await client.post<DownloadProgress>('/models/download', { model_id: modelId });
			return response.data;
		},

		// Get download progress
		async getDownloadProgress(modelId: string): Promise<DownloadProgress> {
			const response = await client.get<DownloadProgress>(`/models/download/${modelId}/progress`);
			return response.data;
		},

		// Delete a downloaded model
		async deleteModel(modelId: string): Promise<void> {
			await client.delete(`/models/download/${modelId}`);
			update((state) => ({
				...state,
				downloadedModels: state.downloadedModels.filter((m) => m !== modelId)
			}));
		},

		// Set active model for a task
		async setActiveModel(task: string, modelId: string): Promise<void> {
			await client.post('/models/active', { task, model_id: modelId });
			await this.loadActiveModels();
		},

		// ==================
		// Google Photos Picker
		// ==================

		// Create a new picker session
		async createPickerSession(connectorId: string): Promise<PickerSession> {
			interface PickerSessionApiResponse {
				session_id: string;
				picker_uri: string;
				poll_interval_seconds: number;
				expire_time: string | null;
			}

			const response = await client.post<PickerSessionApiResponse>(
				`/connectors/${connectorId}/picker/session`
			);

			return {
				sessionId: response.data.session_id,
				pickerUri: response.data.picker_uri,
				pollIntervalSeconds: response.data.poll_interval_seconds,
				expireTime: response.data.expire_time
			};
		},

		// Get picker session status
		async getPickerSessionStatus(connectorId: string, sessionId: string): Promise<PickerSessionStatus> {
			interface PickerStatusApiResponse {
				session_id: string;
				media_items_set: boolean;
				poll_interval_seconds: number;
			}

			const response = await client.get<PickerStatusApiResponse>(
				`/connectors/${connectorId}/picker/session/${sessionId}`
			);

			return {
				sessionId: response.data.session_id,
				mediaItemsSet: response.data.media_items_set,
				pollIntervalSeconds: response.data.poll_interval_seconds
			};
		},

		// Import photos from picker session
		async importPickerPhotos(connectorId: string, sessionId: string): Promise<PickerImportResult> {
			interface ImportApiResponse {
				task_id: string;
				message: string;
			}

			const response = await client.post<ImportApiResponse>(
				`/connectors/${connectorId}/picker/session/${sessionId}/import`
			);

			return {
				taskId: response.data.task_id,
				message: response.data.message
			};
		},

		// Delete picker session
		async deletePickerSession(connectorId: string, sessionId: string): Promise<void> {
			await client.delete(`/connectors/${connectorId}/picker/session/${sessionId}`);
		},

		// ==================
		// Photo Reprocessing
		// ==================

		// Trigger reprocessing of all photos for a connector (generate embeddings)
		async reprocessConnector(connectorId: string): Promise<{ taskId: string; message: string }> {
			interface ReprocessApiResponse {
				reprocess_triggered: boolean;
				task_id: string;
				message: string;
			}

			const response = await client.post<ReprocessApiResponse>(
				`/connectors/${connectorId}/reprocess`
			);

			return {
				taskId: response.data.task_id,
				message: response.data.message
			};
		}
	};
}

export const settingsStore = createSettingsStore();

// Derived stores for convenience
export const connectors = derived(settingsStore, ($store) => $store.connectors);
export const googlePhotosConnectors = derived(settingsStore, ($store) =>
	$store.connectors.filter((c) => c.type === 'google_photos')
);
export const localConnectors = derived(settingsStore, ($store) =>
	$store.connectors.filter((c) => c.type === 'local')
);
export const isLoading = derived(settingsStore, ($store) => $store.loading);
export const settingsError = derived(settingsStore, ($store) => $store.error);
export const activeModels = derived(settingsStore, ($store) => $store.activeModels);
export const downloadedModels = derived(settingsStore, ($store) => $store.downloadedModels);
export const recommendedModels = derived(settingsStore, ($store) => $store.recommendedModels);
