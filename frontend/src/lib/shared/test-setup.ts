// Test setup for Vitest

import '@testing-library/svelte';
import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

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

// Mock fetch globally
global.fetch = vi.fn();

// Reset mocks between tests
beforeEach(() => {
	vi.clearAllMocks();
});
