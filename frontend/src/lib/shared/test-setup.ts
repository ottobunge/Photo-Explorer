// Test setup for Vitest

import '@testing-library/svelte';
import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

/**
 * Helper to create a proper mock Response object with all required properties
 */
function createMockResponse(options: {
	ok: boolean;
	status?: number;
	statusText?: string;
	headers?: Headers;
	json?: () => Promise<unknown>;
	text?: () => Promise<string>;
}): Response {
	return {
		ok: options.ok,
		status: options.status ?? (options.ok ? 200 : 500),
		statusText: options.statusText ?? (options.ok ? 'OK' : 'Internal Server Error'),
		headers: options.headers ?? new Headers({ 'content-type': 'application/json' }),
		json: options.json ?? (async () => ({})),
		text: options.text ?? (async () => ''),
		redirected: false,
		type: 'basic',
		url: '',
		clone: () => createMockResponse(options),
		body: null,
		bodyUsed: false,
		arrayBuffer: async () => new ArrayBuffer(0),
		blob: async () => new Blob(),
		formData: async () => new FormData(),
		bytes: async () => new Uint8Array()
	} as Response;
}

// Configure jsdom for Svelte 5
// This ensures proper DOM environment for Svelte component rendering
if (typeof window !== 'undefined') {
	// Set up custom element registry if not already present
	// In test environment (jsdom), customElements might not be defined
	if (typeof (window as any).customElements === 'undefined') {
		(window as any).customElements = {
			// eslint-disable-next-line @typescript-eslint/no-empty-function
			define: (): void => {},
			get: (): undefined => undefined,
			whenDefined: (): Promise<void> => Promise.resolve()
		};
	}

	// Mock Web Animations API for Svelte transitions
	if (!Element.prototype.animate) {
		Element.prototype.animate = function (): any {
			return {
				finished: Promise.resolve(),
				cancel: (): void => {},
				play: (): void => {},
				pause: (): void => {},
				reverse: (): void => {},
				finish: (): void => {},
				onfinish: null,
				oncancel: null,
				currentTime: 0,
				playbackRate: 1,
				startTime: null,
				effect: null,
				id: '',
				playState: 'finished' as AnimationPlayState,
				replaceState: 'active' as AnimationReplaceState,
				pending: false,
				ready: Promise.resolve(this),
				timeline: null,
				addEventListener: (): void => {},
				removeEventListener: (): void => {},
				dispatchEvent: (): boolean => true,
				commitStyles: (): void => {},
				persist: (): void => {},
				updatePlaybackRate: (): void => {}
			} as Animation;
		};
	}
}

// Mock fetch globally with proper Response object factory
global.fetch = vi.fn(async () =>
	createMockResponse({
		ok: true,
		status: 200,
		json: async () => ({ success: true, data: {} })
	})
);

// Reset mocks between tests
beforeEach(() => {
	vi.clearAllMocks();
});
