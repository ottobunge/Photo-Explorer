/**
 * Application-wide constants for timeouts, intervals, and other magic numbers.
 * Centralizing these values makes them easier to maintain and adjust.
 */

// API and Network Timeouts
/** Default timeout for API requests in milliseconds */
export const API_DEFAULT_TIMEOUT = 30000;

// UI Timeouts and Delays
/** Duration to show success/info messages before auto-dismissing (milliseconds) */
export const MESSAGE_DISMISS_TIMEOUT = 5000;

/** Duration to show temporary status messages (milliseconds) */
export const STATUS_MESSAGE_TIMEOUT = 3000;

/** Delay before triggering import after picker popup closes (milliseconds) */
export const PICKER_CLOSE_DELAY = 2000;

// Polling Intervals
/** Default polling interval for picker session status (milliseconds) */
export const PICKER_POLL_INTERVAL_DEFAULT = 3000;

/** Fallback polling interval if not specified by server (seconds) */
export const PICKER_POLL_INTERVAL_FALLBACK = 3;

// Image and Media Sizes
/** Default thumbnail quality (0-100) */
export const DEFAULT_THUMBNAIL_QUALITY = 85;

// Picker Window Dimensions
/** Width of Google Photos picker popup window (pixels) */
export const PICKER_WINDOW_WIDTH = 900;

/** Height of Google Photos picker popup window (pixels) */
export const PICKER_WINDOW_HEIGHT = 700;

// Retry and Rate Limiting
/** Default number of retry attempts for failed operations */
export const DEFAULT_RETRY_ATTEMPTS = 3;

/** Delay between retry attempts (milliseconds) */
export const RETRY_DELAY = 1000;

// Pagination
export const PAGINATION = {
	DEFAULT_PAGE_SIZE: 24,
	SEARCH_PAGE_SIZE: 24,
	FACES_PAGE_SIZE: 30,
	ALBUMS_PAGE_SIZE: 20,
	MAX_PAGE_SIZE: 100,
} as const;

// Similarity thresholds for search
export const THRESHOLDS = {
	DEFAULT_SIMILARITY: 0.18,
	MIN_SIMILARITY: 0.0,
	MAX_SIMILARITY: 1.0,
	SIMILARITY_STEP: 0.01,
} as const;

// Face graph visualization
export const GRAPH_CONFIG = {
	DEFAULT_RADIUS: 200,
	MIN_NODE_SIZE: 40,
	MAX_NODE_SIZE: 100,
	NODE_SIZE_MULTIPLIER: 2,
	ANIMATION_DURATION: 500,
	FORCE_RERENDER_DELAY: 2000,
	WHEEL_SENSITIVITY: 0.2,
	ZOOM_FACTOR: 1.2,
} as const;

// Upload configuration
export const UPLOAD_CONFIG = {
	MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
	ACCEPTED_TYPES: 'image/*',
	MAX_CONCURRENT_UPLOADS: 3,
	CHUNK_SIZE: 1024 * 1024, // 1MB chunks
} as const;

// UI configuration
export const UI_CONFIG = {
	DEBOUNCE_DELAY: 300,
	TOAST_DURATION: 5000,
	MODAL_ANIMATION_DURATION: 200,
	INFINITE_SCROLL_THRESHOLD: 100,
	POLL_INTERVAL: 5000, // For status polling
} as const;

// Connector configuration
export const CONNECTOR_CONFIG = {
	SYNC_POLL_INTERVAL: 5000,
	REPROCESS_DELAY: 1000,
	DELETE_CONFIRMATION_DELAY: 3000,
	PHOTOS_RELOAD_DELAY: 5000, // Delay after import before reloading photos
} as const;

// Type guards for const assertions
export type PaginationKey = keyof typeof PAGINATION;
export type ThresholdKey = keyof typeof THRESHOLDS;
export type GraphConfigKey = keyof typeof GRAPH_CONFIG;
export type UploadConfigKey = keyof typeof UPLOAD_CONFIG;
export type UiConfigKey = keyof typeof UI_CONFIG;
