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
