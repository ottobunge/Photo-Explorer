// Settings store for managing connectors and app settings

import { client } from '$lib/api/client';
import type {
	Connector,
	ConnectorType,
	ConnectorStatus,
	GooglePhotosStatus,
	AppSettings,
	AppSettingsApiResponse,
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
	if (settings.thumbnailQuality !== undefined) result['thumbnail_quality'] = settings.thumbnailQuality;
	if (settings.clipModel !== undefined) result['clip_model'] = settings.clipModel;
	if (settings.faceDetectionEnabled !== undefined) result['face_detection_enabled'] = settings.faceDetectionEnabled;
	if (settings.autoIndexNewPhotos !== undefined) result['auto_index_new_photos'] = settings.autoIndexNewPhotos;
	return result;
}

/**
 * Settings store using Svelte 5 runes for state management.
 * Manages connectors, app settings, ML models, and Google Photos integration.
 */
class SettingsStore {
	// State properties
	connectors = $state<Connector[]>([]);
	googlePhotosStatus = $state<GooglePhotosStatus | null>(null);
	appSettings = $state<AppSettings | null>(null);
	activeModels = $state<ActiveModels | null>(null);
	downloadedModels = $state<string[]>([]);
	recommendedModels = $state<Record<string, HFModel[]>>({});
	loading = $state<boolean>(false);
	error = $state<string | null>(null);

	// ==================
	// Connector Management
	// ==================

	/**
	 * Load all connectors from the API.
	 * Sets loading state and handles errors.
	 */
	async loadConnectors(): Promise<void> {
		this.loading = true;
		this.error = null;

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
			this.connectors = response.data.connectors.map((c) => ({
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
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to load connectors';
			this.error = errorMessage;
			console.error('Failed to load connectors:', err);
		} finally {
			this.loading = false;
		}
	}

	/**
	 * Get Google Photos auth URL for OAuth flow.
	 * @returns The authorization URL to redirect the user to
	 */
	async connectGooglePhotos(): Promise<string> {
		this.error = null;

		try {
			const redirectUri = `${window.location.origin}/connectors/google-photos/callback`;
			const response = await client.get<{ auth_url: string }>('/connectors/google-photos/auth-url', {
				redirect_uri: redirectUri
			});
			return response.data.auth_url;
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to get auth URL';
			this.error = errorMessage;
			console.error('Failed to connect Google Photos:', err);
			throw err;
		}
	}

	/**
	 * Handle Google Photos OAuth callback.
	 * Exchanges authorization code for tokens and refreshes connectors list.
	 */
	async handleGooglePhotosCallback(code: string): Promise<{ connected: boolean; connectorId: string }> {
		this.error = null;

		try {
			const redirectUri = `${window.location.origin}/connectors/google-photos/callback`;
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
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to complete OAuth callback';
			this.error = errorMessage;
			console.error('Failed to handle Google Photos callback:', err);
			throw err;
		}
	}

	/**
	 * Get Google Photos connection status.
	 * Sets status to default disconnected state on error.
	 */
	async getGooglePhotosStatus(): Promise<void> {
		this.error = null;

		try {
			const response = await client.get<GooglePhotosStatus>('/connectors/google-photos/status');
			this.googlePhotosStatus = response.data;
		} catch (err) {
			// Default to disconnected state if status can't be retrieved
			this.googlePhotosStatus = { connected: false, email: null, photosIndexed: 0, lastSync: null };
			console.error('Failed to get Google Photos status:', err);
		}
	}

	/**
	 * Disconnect Google Photos and remove from connectors list.
	 */
	async disconnectGooglePhotos(): Promise<void> {
		this.error = null;

		try {
			await client.delete('/connectors/google-photos');
			this.connectors = this.connectors.filter((c) => c.type !== 'google_photos');
			this.googlePhotosStatus = { connected: false, email: null, photosIndexed: 0, lastSync: null };
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to disconnect Google Photos';
			this.error = errorMessage;
			console.error('Failed to disconnect Google Photos:', err);
			throw err;
		}
	}

	/**
	 * Add a local folder connector.
	 * @returns The created connector
	 */
	async addLocalFolder(config: LocalFolderConfig): Promise<Connector> {
		this.error = null;

		try {
			const response = await client.post<Connector>('/connectors/local', config);
			this.connectors = [...this.connectors, response.data];
			return response.data;
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to add local folder';
			this.error = errorMessage;
			console.error('Failed to add local folder:', err);
			throw err;
		}
	}

	/**
	 * Remove a connector by ID.
	 */
	async removeConnector(id: string): Promise<void> {
		this.error = null;

		try {
			await client.delete(`/connectors/${id}`);
			this.connectors = this.connectors.filter((c) => c.id !== id);
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to remove connector';
			this.error = errorMessage;
			console.error('Failed to remove connector:', err);
			throw err;
		}
	}

	/**
	 * Toggle connector enabled state.
	 */
	async toggleConnector(id: string, enabled: boolean): Promise<void> {
		this.error = null;

		try {
			await client.patch<Connector>(`/connectors/${id}`, { enabled });
			this.connectors = this.connectors.map((c) => (c.id === id ? { ...c, enabled } : c));
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to toggle connector';
			this.error = errorMessage;
			console.error('Failed to toggle connector:', err);
			throw err;
		}
	}

	/**
	 * Trigger sync for a connector.
	 * Updates connector status optimistically, reverts on error.
	 */
	async triggerSync(id: string): Promise<void> {
		this.error = null;

		// Optimistically set status to syncing
		this.connectors = this.connectors.map((c) =>
			c.id === id ? { ...c, status: 'syncing' as const } : c
		);

		try {
			await client.post(`/connectors/${id}/sync`);
		} catch (err) {
			// Revert to error status on failure
			this.connectors = this.connectors.map((c) =>
				c.id === id ? { ...c, status: 'error' as const } : c
			);
			const errorMessage = err instanceof Error ? err.message : 'Failed to trigger sync';
			this.error = errorMessage;
			console.error('Failed to trigger sync:', err);
			throw err;
		}
	}

	/**
	 * Get sync status for a connector.
	 * @returns Current sync status including progress information
	 */
	async getSyncStatus(id: string): Promise<SyncStatus> {
		this.error = null;

		try {
			const response = await client.get<SyncStatus>(`/connectors/${id}/sync/status`);
			return response.data;
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to get sync status';
			this.error = errorMessage;
			console.error('Failed to get sync status:', err);
			throw err;
		}
	}

	// ==================
	// App Settings
	// ==================

	/**
	 * Load app settings from the API.
	 * Uses default values if settings don't exist yet.
	 */
	async loadSettings(): Promise<void> {
		this.error = null;

		try {
			const response = await client.get<AppSettingsApiResponse>('/settings');
			this.appSettings = mapApiSettingsToAppSettings(response.data);
		} catch (err) {
			// Use defaults if settings don't exist yet
			this.appSettings = {
				thumbnailQuality: 85,
				clipModel: 'ViT-B/32',
				faceDetectionEnabled: true,
				autoIndexNewPhotos: true
			};
			console.warn('Failed to load settings, using defaults:', err);
		}
	}

	/**
	 * Update app settings.
	 * @param settings Partial settings object to update
	 */
	async updateSettings(settings: Partial<AppSettings>): Promise<void> {
		this.error = null;

		try {
			const apiPayload = mapAppSettingsToApi(settings);
			const response = await client.patch<AppSettingsApiResponse>('/settings', apiPayload);
			this.appSettings = mapApiSettingsToAppSettings(response.data);
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to update settings';
			this.error = errorMessage;
			console.error('Failed to update settings:', err);
			throw err;
		}
	}

	// ==================
	// Model Management
	// ==================

	/**
	 * Load active models configuration.
	 * Silently fails if models are not configured yet.
	 */
	async loadActiveModels(): Promise<void> {
		this.error = null;

		try {
			const response = await client.get<ActiveModels>('/models/active');
			this.activeModels = response.data;
		} catch (err) {
			// Models may not be configured yet, don't set error state
			this.activeModels = null;
			console.warn('Models not configured yet:', err);
		}
	}

	/**
	 * Load downloaded models list.
	 */
	async loadDownloadedModels(): Promise<void> {
		this.error = null;

		try {
			const response = await client.get<{ models: string[] }>('/models/downloaded');
			this.downloadedModels = response.data.models;
		} catch (err) {
			this.downloadedModels = [];
			const errorMessage = err instanceof Error ? err.message : 'Failed to load downloaded models';
			console.error('Failed to load downloaded models:', err);
			this.error = errorMessage;
		}
	}

	/**
	 * Load recommended models for different tasks.
	 */
	async loadRecommendedModels(): Promise<void> {
		this.error = null;

		try {
			const response = await client.get<{ recommendations: Record<string, HFModel[]> }>('/models/recommended');
			this.recommendedModels = response.data.recommendations;
		} catch (err) {
			this.recommendedModels = {};
			const errorMessage = err instanceof Error ? err.message : 'Failed to load recommended models';
			console.error('Failed to load recommended models:', err);
			this.error = errorMessage;
		}
	}

	/**
	 * Search for models on Hugging Face.
	 * @param query Search query string
	 * @param task Optional task filter (e.g., 'image-classification')
	 * @returns List of matching models
	 */
	async searchModels(query: string, task?: string): Promise<HFModel[]> {
		this.error = null;

		try {
			const params: Record<string, string> = { query };
			if (task) params['task'] = task;

			const response = await client.get<{ models: HFModel[] }>('/models/search', params);
			return response.data.models;
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to search models';
			this.error = errorMessage;
			console.error('Failed to search models:', err);
			throw err;
		}
	}

	/**
	 * Get detailed information about a model.
	 * @param modelId The Hugging Face model ID
	 * @returns Model information or null if not found
	 */
	async getModelInfo(modelId: string): Promise<HFModel | null> {
		this.error = null;

		try {
			const response = await client.get<HFModel>(`/models/info/${modelId}`);
			return response.data;
		} catch (err) {
			console.error('Failed to get model info:', err);
			return null;
		}
	}

	/**
	 * Download a model from Hugging Face.
	 * @param modelId The Hugging Face model ID
	 * @returns Download progress information
	 */
	async downloadModel(modelId: string): Promise<DownloadProgress> {
		this.error = null;

		try {
			const response = await client.post<DownloadProgress>('/models/download', { model_id: modelId });
			return response.data;
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to download model';
			this.error = errorMessage;
			console.error('Failed to download model:', err);
			throw err;
		}
	}

	/**
	 * Get download progress for a model.
	 * @param modelId The Hugging Face model ID
	 * @returns Current download progress
	 */
	async getDownloadProgress(modelId: string): Promise<DownloadProgress> {
		this.error = null;

		try {
			const response = await client.get<DownloadProgress>(`/models/download/${modelId}/progress`);
			return response.data;
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to get download progress';
			this.error = errorMessage;
			console.error('Failed to get download progress:', err);
			throw err;
		}
	}

	/**
	 * Delete a downloaded model.
	 * @param modelId The Hugging Face model ID
	 */
	async deleteModel(modelId: string): Promise<void> {
		this.error = null;

		try {
			await client.delete(`/models/download/${modelId}`);
			this.downloadedModels = this.downloadedModels.filter((m) => m !== modelId);
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to delete model';
			this.error = errorMessage;
			console.error('Failed to delete model:', err);
			throw err;
		}
	}

	/**
	 * Set active model for a task.
	 * @param task The task name (e.g., 'clip', 'face')
	 * @param modelId The Hugging Face model ID
	 */
	async setActiveModel(task: string, modelId: string): Promise<void> {
		this.error = null;

		try {
			await client.post('/models/active', { task, model_id: modelId });
			await this.loadActiveModels();
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to set active model';
			this.error = errorMessage;
			console.error('Failed to set active model:', err);
			throw err;
		}
	}

	// ==================
	// Google Photos Picker
	// ==================

	/**
	 * Create a new picker session for selective photo import.
	 * @param connectorId The Google Photos connector ID
	 * @returns Picker session information including URI to open
	 */
	async createPickerSession(connectorId: string): Promise<PickerSession> {
		this.error = null;

		try {
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
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to create picker session';
			this.error = errorMessage;
			console.error('Failed to create picker session:', err);
			throw err;
		}
	}

	/**
	 * Get picker session status to check if media items have been selected.
	 * @param connectorId The Google Photos connector ID
	 * @param sessionId The picker session ID
	 * @returns Session status including whether media items are ready
	 */
	async getPickerSessionStatus(connectorId: string, sessionId: string): Promise<PickerSessionStatus> {
		this.error = null;

		try {
			interface PickerStatusApiResponse {
				session_id: string;
				media_items_set: boolean;
				poll_interval_seconds: number;
				expire_time: string | null;
			}

			const response = await client.get<PickerStatusApiResponse>(
				`/connectors/${connectorId}/picker/session/${sessionId}`
			);

			return {
				sessionId: response.data.session_id,
				mediaItemsSet: response.data.media_items_set,
				pollIntervalSeconds: response.data.poll_interval_seconds,
				expireTime: response.data.expire_time
			};
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to get picker session status';
			this.error = errorMessage;
			console.error('Failed to get picker session status:', err);
			throw err;
		}
	}

	/**
	 * Import photos from picker session.
	 * @param connectorId The Google Photos connector ID
	 * @param sessionId The picker session ID
	 * @returns Import task information
	 */
	async importPickerPhotos(connectorId: string, sessionId: string): Promise<PickerImportResult> {
		this.error = null;

		try {
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
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to import picker photos';
			this.error = errorMessage;
			console.error('Failed to import picker photos:', err);
			throw err;
		}
	}

	/**
	 * Delete picker session to clean up resources.
	 * @param connectorId The Google Photos connector ID
	 * @param sessionId The picker session ID
	 */
	async deletePickerSession(connectorId: string, sessionId: string): Promise<void> {
		this.error = null;

		try {
			await client.delete(`/connectors/${connectorId}/picker/session/${sessionId}`);
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to delete picker session';
			this.error = errorMessage;
			console.error('Failed to delete picker session:', err);
			throw err;
		}
	}

	// ==================
	// Photo Reprocessing
	// ==================

	/**
	 * Trigger reprocessing of all photos for a connector.
	 * Regenerates embeddings and other ML-derived data.
	 * @param connectorId The connector ID
	 * @returns Task information
	 */
	async reprocessConnector(connectorId: string): Promise<{ taskId: string; message: string }> {
		this.error = null;

		try {
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
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'Failed to trigger reprocessing';
			this.error = errorMessage;
			console.error('Failed to trigger reprocessing:', err);
			throw err;
		}
	}

	// ==================
	// Utility Methods
	// ==================

	/**
	 * Clear error state.
	 */
	clearError(): void {
		this.error = null;
	}

	/**
	 * Reset store to initial state.
	 */
	reset(): void {
		this.connectors = [];
		this.googlePhotosStatus = null;
		this.appSettings = null;
		this.activeModels = null;
		this.downloadedModels = [];
		this.recommendedModels = {};
		this.loading = false;
		this.error = null;
	}
}

// Export singleton instance
export const settingsStore = new SettingsStore();
