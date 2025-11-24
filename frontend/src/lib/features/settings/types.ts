// Types for settings and connectors

export type ConnectorType = 'google_photos' | 'local' | 'upload';

export type ConnectorStatus = 'disconnected' | 'connected' | 'syncing' | 'error';

export interface Connector {
	id: string;
	type: ConnectorType;
	name: string;
	enabled: boolean;
	status: ConnectorStatus;
	config: Record<string, unknown>;
	lastSync: string | null;
	errorMessage: string | null;
	createdAt: string;
	updatedAt: string | null;
}

export interface SyncStats {
	totalItems: number;
	indexed: number;
	skipped: number;
	failed: number;
	durationSeconds: number | null;
}

export interface SyncStatus {
	syncing: boolean;
	lastSync: string | null;
	stats: SyncStats | null;
}

export interface GooglePhotosStatus {
	connected: boolean;
	email: string | null;
	photosIndexed: number;
	lastSync: string | null;
}

export interface LocalFolderConfig {
	path: string;
	name?: string;
	recursive: boolean;
	watch: boolean;
	autoAlbum: boolean;
}

export interface AppSettings {
	thumbnailQuality: number;
	clipModel: string;
	faceDetectionEnabled: boolean;
	autoIndexNewPhotos: boolean;
}

// API response format (snake_case)
export interface AppSettingsApiResponse {
	config_dir: string;
	data_dir: string;
	cache_dir: string;
	thumbnail_quality: number;
	clip_model: string;
	face_detection_enabled: boolean;
	auto_index_new_photos: boolean;
	thumbnail_cache_hours: number;
	indexing_batch_size: number;
	indexing_parallel_workers: number;
	default_sync_interval_hours: number;
}

// Hugging Face Model Types
export interface HFModel {
	model_id: string;
	author: string;
	model_name: string;
	pipeline_tag: string | null;
	tags: string[];
	downloads: number;
	likes: number;
	last_modified: string | null;
	library_name: string | null;
	size_mb: number | null;
	private: boolean;
	gated: boolean;
	files: string[];
	is_downloaded: boolean;
}

export interface DownloadProgress {
	model_id: string;
	status: 'pending' | 'downloading' | 'completed' | 'failed' | 'not_started';
	progress: number;
	downloaded_bytes: number;
	total_bytes: number;
	current_file: string | null;
	error: string | null;
}

export interface ActiveModels {
	clip_model: string;
	clip_status: string;
	face_model: string;
	face_status: string;
}

export interface ModelTask {
	id: string;
	name: string;
}

export interface SettingsState {
	connectors: Connector[];
	googlePhotosStatus: GooglePhotosStatus | null;
	appSettings: AppSettings | null;
	activeModels: ActiveModels | null;
	downloadedModels: string[];
	recommendedModels: Record<string, HFModel[]>;
	loading: boolean;
	error: string | null;
}

// Google Photos Picker API Types
export interface PickerSession {
	sessionId: string;
	pickerUri: string;
	pollIntervalSeconds: number;
	expireTime: string | null;
}

export interface PickerSessionStatus {
	sessionId: string;
	mediaItemsSet: boolean;
	pollIntervalSeconds: number;
}

export interface PickerImportResult {
	taskId: string;
	message: string;
}
